"""LLM 답변의 수치가 Tool 결과(컨텍스트)에 근거하는지 검사한다.

회고에서 도출한 '출력 검증' 단계를 최소 단위로 구현한 예제.
근거 없는 수치가 있으면 재생성을 요청하거나, 사용자에게 '검증되지 않은 수치'로 표시한다.
"""

import re
from dataclasses import dataclass

NUMBER = re.compile(r"[-+]?\d+(?:,\d{3})*(?:\.\d+)?%?")


def parse(token: str) -> float:
    value = float(token.rstrip("%").replace(",", ""))
    return value / 100 if token.endswith("%") else value


def numbers_in(obj) -> list[float]:
    """컨텍스트(dict/list/str/숫자)에 들어 있는 모든 수치를 꺼낸다."""
    if isinstance(obj, (int, float)):
        return [float(obj)]
    if isinstance(obj, str):
        return [parse(t) for t in NUMBER.findall(obj)]
    if isinstance(obj, dict):
        return [n for v in obj.values() for n in numbers_in(v)]
    if isinstance(obj, (list, tuple)):
        return [n for v in obj for n in numbers_in(v)]
    return []


@dataclass
class Claim:
    text: str
    value: float
    grounded: bool


def check(answer: str, context: dict, rel_tol: float = 0.01) -> list[Claim]:
    allowed = numbers_in(context)
    claims = []
    for m in NUMBER.finditer(answer):
        v = parse(m.group())
        ok = any(abs(v - a) <= rel_tol * max(abs(a), 1e-9) for a in allowed)
        claims.append(Claim(m.group(), v, ok))
    return claims


def main() -> None:
    context = {
        "price_api": {"date": "2024-01-12", "close": 78.23, "prev_close": 79.97},
        "db": {"cluster": "공급 차질", "past_car": 0.0234, "n_events": 16},
    }
    answers = {
        "근거 있는 답변": "공급 차질 유형은 과거 16건에서 평균 2.34% 상승했고, 종가는 78.23달러입니다.",
        "Hallucination 포함": "공급 차질 유형은 평균 2.34% 상승했으며, 다음 주 85.5달러까지 오를 확률이 72%입니다.",
    }
    for name, ans in answers.items():
        claims = check(ans, context)
        bad = [c for c in claims if not c.grounded]
        print(f"[{name}]\n  {ans}")
        for c in claims:
            print(f"   {'✅' if c.grounded else '❌'} {c.text}")
        print(f"  → {'통과' if not bad else '재생성 요청: 근거 없는 수치 ' + ', '.join(c.text for c in bad)}\n")


if __name__ == "__main__":
    main()
