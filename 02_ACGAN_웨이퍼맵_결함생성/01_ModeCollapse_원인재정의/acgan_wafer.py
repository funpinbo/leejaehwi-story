"""합성 웨이퍼맵으로 학습하는 작은 ACGAN.

핵심은 판별자가 두 개의 출력을 가진다는 것이다.
  - adv  : 진짜/가짜 (L_s)
  - aux  : 결함 클래스 (L_c)
Generator는 '진짜처럼 보이면서 요청한 클래스로 분류되도록' 학습되므로
한두 개 패턴으로 수렴(Mode Collapse)하면 L_c가 커진다.
"""

import numpy as np
import torch
from torch import nn

torch.manual_seed(0)
RNG = np.random.default_rng(0)

SIZE = 32
CLASSES = ["Center", "Edge-Ring", "Scratch"]
N_CLASS = len(CLASSES)
LATENT = 32


# ---------- 합성 웨이퍼맵 ----------
yy, xx = np.mgrid[:SIZE, :SIZE]
r = np.hypot(yy - SIZE / 2 + 0.5, xx - SIZE / 2 + 0.5)
WAFER = r < SIZE / 2 - 1


def make_map(cls: int) -> np.ndarray:
    m = (RNG.random((SIZE, SIZE)) < 0.03) & WAFER  # 배경 랜덤 불량 다이
    if cls == 0:  # Center: 중앙 원형 군집
        m |= r < RNG.uniform(4, 7)
    elif cls == 1:  # Edge-Ring: 가장자리 고리
        m |= (r > SIZE / 2 - RNG.uniform(3, 5)) & WAFER
    else:  # Scratch: 임의 방향의 선
        angle = RNG.uniform(0, np.pi)
        c = RNG.uniform(-6, 6)
        dist = np.abs(np.cos(angle) * (xx - SIZE / 2) + np.sin(angle) * (yy - SIZE / 2) - c)
        m |= (dist < 1.0) & (r < SIZE / 2 - 4)
    img = np.where(WAFER, np.where(m, 1.0, 0.0), -1.0)  # 웨이퍼 밖=-1, 정상=0, 불량=1
    return img.astype(np.float32)


def make_dataset(n_per_class: int = 600):
    xs, ys = [], []
    for c in range(N_CLASS):
        xs += [make_map(c) for _ in range(n_per_class)]
        ys += [c] * n_per_class
    return torch.tensor(np.stack(xs)).unsqueeze(1), torch.tensor(ys)


# ---------- 모델 ----------
class Generator(nn.Module):
    def __init__(self):
        super().__init__()
        self.embed = nn.Embedding(N_CLASS, LATENT)
        self.fc = nn.Linear(LATENT, 64 * 8 * 8)
        self.net = nn.Sequential(
            nn.BatchNorm2d(64), nn.ReLU(),
            nn.ConvTranspose2d(64, 32, 4, 2, 1), nn.BatchNorm2d(32), nn.ReLU(),  # 16x16
            nn.ConvTranspose2d(32, 1, 4, 2, 1), nn.Tanh(),                       # 32x32
        )

    def forward(self, z, y):
        h = self.fc(z * self.embed(y))  # 노이즈에 클래스 정보를 곱해 조건을 준다
        return self.net(h.view(-1, 64, 8, 8))


class Discriminator(nn.Module):
    def __init__(self):
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv2d(1, 32, 4, 2, 1), nn.LeakyReLU(0.2),                    # 16x16
            nn.Conv2d(32, 64, 4, 2, 1), nn.BatchNorm2d(64), nn.LeakyReLU(0.2),  # 8x8
            nn.Flatten(),
        )
        self.adv = nn.Linear(64 * 8 * 8, 1)        # 진짜/가짜 → L_s
        self.aux = nn.Linear(64 * 8 * 8, N_CLASS)  # 클래스 → L_c

    def forward(self, x):
        h = self.features(x)
        return self.adv(h), self.aux(h)


def main() -> None:
    x_real, y_real = make_dataset()
    G, D = Generator(), Discriminator()
    opt_g = torch.optim.Adam(G.parameters(), lr=2e-4, betas=(0.5, 0.999))
    opt_d = torch.optim.Adam(D.parameters(), lr=2e-4, betas=(0.5, 0.999))
    bce, ce = nn.BCEWithLogitsLoss(), nn.CrossEntropyLoss()
    batch = 64

    for epoch in range(1, 16):
        perm = torch.randperm(len(x_real))
        for i in range(0, len(perm), batch):
            idx = perm[i : i + batch]
            real, y = x_real[idx], y_real[idx]
            n = len(idx)
            z = torch.randn(n, LATENT)
            y_fake = torch.randint(0, N_CLASS, (n,))
            fake = G(z, y_fake)

            # --- Discriminator: L_s + L_c ---
            adv_r, aux_r = D(real)
            adv_f, aux_f = D(fake.detach())
            loss_s = bce(adv_r, torch.full_like(adv_r, 0.9)) + bce(adv_f, torch.zeros_like(adv_f))
            loss_c = ce(aux_r, y) + ce(aux_f, y_fake)
            opt_d.zero_grad()
            (loss_s + loss_c).backward()
            opt_d.step()

            # --- Generator: 진짜처럼 + 요청한 클래스로 분류되도록 ---
            adv_f, aux_f = D(fake)
            loss_g = bce(adv_f, torch.ones_like(adv_f)) + ce(aux_f, y_fake)
            opt_g.zero_grad()
            loss_g.backward()
            opt_g.step()

        if epoch % 5 == 0:
            print(f"epoch {epoch:>2}  D(L_s+L_c) {(loss_s + loss_c).item():.3f}  G {loss_g.item():.3f}")

    # 생성 이미지가 '요청한 클래스'로 분류되는지 = 클래스별로 구별되는 이미지를 만드는지
    G.eval(); D.eval()
    with torch.no_grad():
        y_test = torch.arange(N_CLASS).repeat_interleave(200)
        fake = G(torch.randn(len(y_test), LATENT), y_test)
        pred = D(fake)[1].argmax(1)
        print("\n클래스별 생성 이미지 분류 일치율 (Mode Collapse면 일부 클래스가 0%에 가까워짐)")
        for c, name in enumerate(CLASSES):
            acc = (pred[y_test == c] == c).float().mean().item()
            print(f"  {name:<10} {acc:6.1%}")
        # 같은 클래스 내 다양성: 생성 이미지 간 평균 픽셀 차이
        for c, name in enumerate(CLASSES):
            imgs = fake[y_test == c].flatten(1)
            div = torch.cdist(imgs[:50], imgs[:50]).mean().item()
            print(f"  {name:<10} 클래스 내 다양성(평균 L2 거리) {div:.2f}")


if __name__ == "__main__":
    main()
