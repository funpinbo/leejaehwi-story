"""3-Layer 결합 → 매매 Plan (조기 진입 20% · 조기 청산 60%).

Layer 1: 여러 시계열 모델의 예측 수익률을 가중 결합
Layer 2: 4개 페르소나 에이전트의 뉴스 판단(-1 ~ +1)과 확신도
Layer 3: 메타 가중치 (과거 유사 사건에서 어떤 모델이 잘 맞았는지)
모든 값은 합성 예시이며, LLM 호출은 고정된 응답으로 대체했다.
"""

from dataclasses import dataclass
from typing import Literal

ENTRY_RATIO = 0.20  # 예측 이동폭의 20% 지점에서 진입
EXIT_RATIO = 0.60   # 60% 지점에서 청산
MIN_EDGE = 0.01     # 결합 기대수익률이 1% 미만이면 거래하지 않음


@dataclass
class PersonaView:
    persona: Literal["Global", "Economy", "Industry", "Company"]
    stance: float      # -1(매도) ~ +1(매수)
    confidence: float  # 0 ~ 1
    reason: str


@dataclass
class Plan:
    code: str
    side: Literal["BUY", "SKIP"]
    expected_return: float
    entry: float | None = None
    take_profit: float | None = None
    stop_loss: float | None = None


def layer1_unified_return(preds: dict[str, float], meta_weights: dict[str, float]) -> float:
    """모델별 예측 수익률을 Layer 3 메타 가중치로 결합."""
    total = sum(meta_weights.values())
    return sum(preds[m] * w for m, w in meta_weights.items()) / total


def layer2_agent_score(views: list[PersonaView]) -> float:
    """페르소나별 판단을 확신도로 가중 평균. 실제로는 최대 3라운드 피드백 루프 후의 결과."""
    weight = sum(v.confidence for v in views) or 1
    return sum(v.stance * v.confidence for v in views) / weight


def make_plan(code: str, close: float, preds: dict[str, float], meta: dict[str, float],
              views: list[PersonaView], agent_alpha: float = 0.5) -> Plan:
    base = layer1_unified_return(preds, meta)
    agent = layer2_agent_score(views)
    # LLM 판단은 방향·크기를 조정하는 보정 계수로만 사용 (숫자 예측 자체는 Layer 1)
    expected = base * (1 + agent_alpha * agent)
    if expected < MIN_EDGE:
        return Plan(code, "SKIP", expected)
    move = close * expected
    return Plan(
        code, "BUY", expected,
        entry=round(close + move * ENTRY_RATIO),
        take_profit=round(close + move * EXIT_RATIO),
        stop_loss=round(close - move * 0.5),
    )


def main() -> None:
    meta = {"BSTS": 0.2, "CatBoost": 0.5, "PatchTST": 0.3}  # Layer 3 (예시)
    universe = {
        "036540": (6420, {"BSTS": 0.031, "CatBoost": 0.052, "PatchTST": 0.044}, [
            PersonaView("Global", 0.4, 0.6, "미국 반도체 지수 강세"),
            PersonaView("Economy", 0.1, 0.4, "원/달러 환율 보합"),
            PersonaView("Industry", 0.7, 0.8, "HBM 후공정 수요 증가 보도"),
            PersonaView("Company", 0.5, 0.7, "주요 고객사 증설 뉴스"),
        ]),
        "067310": (24850, {"BSTS": 0.012, "CatBoost": 0.004, "PatchTST": -0.006}, [
            PersonaView("Global", -0.2, 0.5, "글로벌 경기 우려"),
            PersonaView("Economy", 0.0, 0.3, "특이사항 없음"),
            PersonaView("Industry", 0.2, 0.5, "업황 혼조"),
            PersonaView("Company", -0.4, 0.6, "실적 컨센서스 하회 우려"),
        ]),
    }

    print(f"{'종목':<8}{'결정':<6}{'기대수익':>8}{'진입':>9}{'익절':>9}{'손절':>9}")
    for code, (close, preds, views) in universe.items():
        p = make_plan(code, close, preds, meta, views)
        fmt = lambda v: f"{v:>9,}" if v else f"{'-':>9}"
        print(f"{p.code:<8}{p.side:<6}{p.expected_return:>+8.2%}{fmt(p.entry)}{fmt(p.take_profit)}{fmt(p.stop_loss)}")


if __name__ == "__main__":
    main()
