"""LOT별 검사 이미지의 주기 성분을 FFT로 비교해 '특정 LOT에서만' 나타나는 패턴을 찾는다.

광학계 문제라면 모든 LOT에 공통으로 나타나고,
공정 문제라면 특정 LOT에서만 나타난다는 판단 기준을 코드로 옮긴 예제.
이미지는 합성 데이터다.
"""

import numpy as np

RNG = np.random.default_rng(42)
SIZE = 256


def make_image(defect_period: int | None = None) -> np.ndarray:
    """정상 웨이퍼 이미지 + (선택) 기판 표면의 주기적 패턴."""
    img = 120 + RNG.normal(0, 4, (SIZE, SIZE))
    if defect_period:
        rows = np.arange(SIZE)
        img += 6 * np.sin(2 * np.pi * rows / defect_period)[:, None]
    return img


def dominant_period(img: np.ndarray) -> tuple[float, float]:
    """행 방향 평균 밝기 프로파일의 가장 강한 주기와 그 세기를 반환."""
    profile = img.mean(axis=1)
    profile = profile - profile.mean()
    spectrum = np.abs(np.fft.rfft(profile))
    freqs = np.fft.rfftfreq(len(profile))
    k = int(np.argmax(spectrum[1:]) + 1)  # DC 성분 제외
    return 1 / freqs[k], float(spectrum[k])


def main() -> None:
    lots = {
        "LOT-A": [make_image() for _ in range(5)],
        "LOT-B": [make_image() for _ in range(5)],
        "LOT-C": [make_image(defect_period=16) for _ in range(5)],  # 공정 이상 LOT
        "LOT-D": [make_image() for _ in range(5)],
    }

    strength = {
        lot: np.mean([dominant_period(img)[1] for img in imgs]) for lot, imgs in lots.items()
    }

    # 기준선: LOT 간 중앙값과 MAD(이상치에 강한 분산 추정)
    values = np.array(list(strength.values()))
    median = np.median(values)
    mad = np.median(np.abs(values - median)) or 1e-9

    print(f"{'LOT':<7}{'주기(px)':>10}{'세기':>10}{'robust z':>11}  판정")
    for lot, imgs in lots.items():
        period, _ = dominant_period(imgs[0])
        z = (strength[lot] - median) / (1.4826 * mad)
        verdict = "⚠ 이 LOT에서만 주기 패턴 → 공정 의심" if z > 3.5 else "정상"
        print(f"{lot:<7}{period:>10.1f}{strength[lot]:>10.1f}{z:>11.1f}  {verdict}")

    flagged = [lot for lot in lots if (strength[lot] - median) / (1.4826 * mad) > 3.5]
    if len(flagged) == len(lots):
        print("\n모든 LOT에 공통 → 광학계 점검이 우선")
    elif flagged:
        print(f"\n{', '.join(flagged)}에서만 발생 → 타 공정 LOT 비교 테스트 제안")


if __name__ == "__main__":
    main()
