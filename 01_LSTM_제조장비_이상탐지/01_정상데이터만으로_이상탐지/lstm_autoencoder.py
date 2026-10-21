"""정상 데이터만으로 학습하는 LSTM Autoencoder 이상탐지.

1) 설비 진동을 가정한 더미 시계열 생성 (뒤쪽에 이상 구간 삽입)
2) 정상 구간만으로 학습 (t < 1600)
3) 학습에 쓰지 않은 정상 구간(1600 <= t < 2200)의 Reconstruction Error 99th percentile을 Threshold로 사용
4) 연속 N 윈도우 초과 시에만 알람 (False Positive 억제)
"""

import numpy as np
import torch
from torch import nn

torch.manual_seed(42)
RNG = np.random.default_rng(42)

WINDOW = 50
CONSECUTIVE = 3


def make_signal(n: int = 3000) -> tuple[np.ndarray, np.ndarray]:
    t = np.arange(n)
    x = np.sin(2 * np.pi * t / 50) + 0.5 * np.sin(2 * np.pi * t / 13) + RNG.normal(0, 0.1, n)
    label = np.zeros(n, dtype=bool)
    # 이상 1: 진폭 증가 / 이상 2: 주파수 변화
    x[2300:2400] *= 1.8
    label[2300:2400] = True
    x[2600:2700] = np.sin(2 * np.pi * t[2600:2700] / 7) + RNG.normal(0, 0.1, 100)
    label[2600:2700] = True
    return x.astype(np.float32), label


def to_windows(x: np.ndarray) -> torch.Tensor:
    w = np.lib.stride_tricks.sliding_window_view(x, WINDOW)
    return torch.from_numpy(w.copy()).unsqueeze(-1)  # (N, WINDOW, 1)


class LSTMAutoencoder(nn.Module):
    def __init__(self, hidden: int = 64):
        super().__init__()
        self.encoder = nn.LSTM(1, hidden, batch_first=True)
        self.decoder = nn.LSTM(hidden, hidden, batch_first=True)
        self.head = nn.Linear(hidden, 1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        _, (h, _) = self.encoder(x)                      # 시퀀스를 잠재 벡터 하나로 압축
        z = h[-1].unsqueeze(1).repeat(1, x.size(1), 1)   # 잠재 벡터를 시퀀스 길이만큼 복제
        out, _ = self.decoder(z)
        return self.head(out)


def reconstruction_error(model: nn.Module, windows: torch.Tensor) -> np.ndarray:
    model.eval()
    with torch.no_grad():
        return ((model(windows) - windows) ** 2).mean(dim=(1, 2)).numpy()


def main() -> None:
    x, label = make_signal()
    mean, std = x[:1600].mean(), x[:1600].std()
    x = (x - mean) / std  # 학습 구간 통계로만 정규화 (테스트 정보 누수 방지)

    train = to_windows(x[:1600])       # 정상 구간만 학습
    valid = to_windows(x[1600:2200])   # 학습에 안 쓴 정상 구간 → Threshold 결정용
    test = to_windows(x)

    model = LSTMAutoencoder()
    opt = torch.optim.Adam(model.parameters(), lr=5e-3)
    loss_fn = nn.MSELoss()
    for epoch in range(30):
        model.train()
        perm = torch.randperm(len(train))
        for i in range(0, len(train), 128):
            batch = train[perm[i : i + 128]]
            opt.zero_grad()
            loss = loss_fn(model(batch), batch)
            loss.backward()
            opt.step()
        if epoch % 10 == 9:
            print(f"epoch {epoch + 1:>2}  loss {loss.item():.4f}")

    threshold = np.percentile(reconstruction_error(model, valid), 99)
    err = reconstruction_error(model, test)
    over = err > threshold

    # 연속 CONSECUTIVE 윈도우 이상 초과할 때만 알람
    alarm = np.convolve(over, np.ones(CONSECUTIVE, dtype=int), "valid") == CONSECUTIVE
    alarm_idx = np.where(alarm)[0] + CONSECUTIVE - 1 + WINDOW - 1  # 윈도우 끝 시점 기준
    # 윈도우 안에 이상 시점이 하나라도 있으면 '이상 윈도우'
    window_label = np.array([label[i : i + WINDOW].any() for i in range(len(err))])

    print(f"\nThreshold (정상 99th pct): {threshold:.4f}")
    print(f"단순 초과 윈도우 수: {over.sum()} / 연속 {CONSECUTIVE}회 초과 알람 수: {alarm.sum()}")
    is_true = window_label[alarm_idx - WINDOW + 1]
    print(f"알람 중 실제 이상 윈도우 비율(Precision): {is_true.mean() if len(is_true) else 0:.2%}")
    print(f"정상 구간 오탐 알람 수: {(~is_true).sum()}  (단순 초과 기준이었다면 {(over & ~window_label).sum()})")
    for start, end in [(2300, 2400), (2600, 2700)]:
        caught = alarm_idx[(alarm_idx >= start) & (alarm_idx < end)]
        print(f"이상 구간 t={start}~{end}: {'탐지 (첫 알람 t=' + str(caught[0]) + ')' if len(caught) else '미탐지'}")


if __name__ == "__main__":
    main()
