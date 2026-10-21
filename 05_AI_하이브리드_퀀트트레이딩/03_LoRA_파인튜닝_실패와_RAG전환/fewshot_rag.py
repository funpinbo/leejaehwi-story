"""매매 판단 이력 few-shot RAG + 출력 스키마 검증.

1) 과거 판단 이력(특징 벡터)에서 현재 상황과 가장 비슷한 k건을 찾아 few-shot 예시로 넣는다.
2) LLM 출력은 Pydantic 스키마로 검증한다. 설명문이 붙은 경우 JSON 부분만 추출한다.
LLM 출력은 실제 모델 대신 예시 문자열을 사용한다.
"""

import json
import re
from typing import Literal

import numpy as np
from pydantic import BaseModel, Field, ValidationError

RNG = np.random.default_rng(0)


class Decision(BaseModel):
    decision: Literal["BUY", "HOLD", "SELL"]
    confidence: float = Field(ge=0, le=1)
    reason: str = Field(min_length=5)


# ---------- 1. 과거 판단 이력 (특징: 예측수익률, 뉴스점수, 거래량비, 변동성) ----------
FEATURES = ["pred_ret", "news", "vol_ratio", "volatility"]
history = [
    {"code": f"{RNG.integers(1, 999999):06d}", "x": RNG.normal(0, 1, 4).round(2),
     "decision": d, "result": r}
    for d, r in [("BUY", "+3.1%"), ("HOLD", "+0.2%"), ("SELL", "-2.4%"), ("BUY", "-1.0%"),
                 ("BUY", "+2.2%"), ("SELL", "+0.5%"), ("HOLD", "-0.3%"), ("BUY", "+4.0%")]
]


def retrieve(x: np.ndarray, k: int = 3) -> list[dict]:
    X = np.stack([h["x"] for h in history])
    sims = (X @ x) / (np.linalg.norm(X, axis=1) * np.linalg.norm(x))
    return [history[i] for i in np.argsort(-sims)[:k]]


def build_prompt(code: str, x: np.ndarray) -> str:
    shots = "\n".join(
        f"- 상황 {dict(zip(FEATURES, h['x'].tolist()))} → 판단 {h['decision']} (이후 결과 {h['result']})"
        for h in retrieve(x)
    )
    return (
        "너는 반도체 후공정 종목의 매매 판단 에이전트다.\n"
        f"[비슷한 과거 판단 사례]\n{shots}\n\n"
        f"[현재 상황] 종목 {code}: {dict(zip(FEATURES, x.round(2).tolist()))}\n"
        'JSON 한 개만 출력하라: {"decision": "BUY|HOLD|SELL", "confidence": 0~1, "reason": "..."}'
    )


# ---------- 2. 출력 검증 ----------
def parse(output: str) -> Decision | None:
    for candidate in (output, *re.findall(r"\{.*?\}", output, re.S)):
        try:
            return Decision.model_validate(json.loads(candidate))
        except (json.JSONDecodeError, ValidationError):
            continue
    return None


LORA_OUTPUTS = [  # 소량 데이터 LoRA 모델에서 자주 보던 형태 (예시)
    "판단: 매수. 이유는 뉴스가 긍정적이기 때문입니다.",
    '{"decision": "매수", "confidence": "높음"}',
    '{"action": "BUY", "score": 0.8}',
    '결론적으로 {"decision": "BUY", "confidence": 0.7, "reason": "HBM 수요 증가"',
    '{"decision": "HOLD", "confidence": 0.5, "reason": "방향성 불명확"}',
]
BASE_OUTPUTS = [  # 파인튜닝 없는 베이스 모델 (예시)
    '{"decision": "BUY", "confidence": 0.72, "reason": "HBM 후공정 수요 증가 보도"}',
    '분석 결과입니다.\n{"decision": "HOLD", "confidence": 0.55, "reason": "뉴스 방향성 혼재"}',
    '{"decision": "SELL", "confidence": 0.61, "reason": "실적 하회 우려와 거래량 감소"}',
    '{"decision": "BUY", "confidence": 0.66, "reason": "고객사 증설 뉴스"}',
    '{"decision": "HOLD", "confidence": 0.5, "reason": "특이사항 없음"}',
]


def main() -> None:
    print("=== few-shot 프롬프트 ===")
    print(build_prompt("036540", np.array([0.8, 1.2, 0.3, -0.2])))

    print("\n=== 파싱 성공률 ===")
    for name, outputs in [("LoRA 파인튜닝 모델", LORA_OUTPUTS), ("베이스 모델(파인튜닝 없음)", BASE_OUTPUTS)]:
        parsed = [parse(o) for o in outputs]
        ok = sum(p is not None for p in parsed)
        print(f"{name:<22} {ok}/{len(outputs)} = {ok / len(outputs):.0%}")


if __name__ == "__main__":
    main()
