"""조명 설정값 ↔ GrayValue 관계식 피팅 후, 목표 GrayValue에 맞는 조명값을 역산한다.

당시 Excel(LINEST)로 만든 도구를 Python으로 재현한 예제.
측정값은 실제 장비 데이터가 아닌 예시 값이다.
"""

import numpy as np

# 조명 설정값을 몇 단계로 바꿔가며 측정한 GrayValue (예시)
light_settings = np.array([10, 20, 30, 40, 50, 60, 70], dtype=float)
gray_values = np.array([22, 51, 84, 118, 149, 176, 198], dtype=float)

GRAY_MIN, GRAY_MAX = 0, 255  # 8bit 카메라


def fit(x: np.ndarray, y: np.ndarray, degree: int = 2) -> np.poly1d:
    """Excel LINEST와 같은 최소제곱 다항 피팅."""
    return np.poly1d(np.polyfit(x, y, degree))


def find_light_setting(model: np.poly1d, target_gray: float, lo: float, hi: float) -> float:
    """단조 증가 구간에서 이분 탐색으로 model(x) = target_gray 인 x를 찾는다."""
    if not (model(lo) <= target_gray <= model(hi)):
        raise ValueError(f"목표값 {target_gray}가 측정 구간 밖입니다. 측정 범위를 넓혀주세요.")
    for _ in range(60):
        mid = (lo + hi) / 2
        if model(mid) < target_gray:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def main() -> None:
    model = fit(light_settings, gray_values)
    residual = gray_values - model(light_settings)
    print(f"피팅 계수 (2차): {np.round(model.coefficients, 4)}")
    print(f"측정점 최대 오차: {np.abs(residual).max():.2f} GrayValue")

    # 단조성 확인 — 역산이 유효하려면 측정 구간에서 증가해야 한다
    grid = np.linspace(light_settings.min(), light_settings.max(), 200)
    assert np.all(np.diff(model(grid)) > 0), "측정 구간에서 단조 증가가 아닙니다."

    for target in (60, 120, 180):
        setting = find_light_setting(model, target, light_settings.min(), light_settings.max())
        print(f"목표 GrayValue {target:>3} → 조명 설정값 약 {setting:.1f}")


if __name__ == "__main__":
    main()
