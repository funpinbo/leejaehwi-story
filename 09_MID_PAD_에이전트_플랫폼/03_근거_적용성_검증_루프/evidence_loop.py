"""근거 검색 → 적용성 검증(루프 안쪽) → 충분성 평가 → 추가 검색(최대 2회).

마지막 테스트는 '계산한 적용성이 최종 근거 필드에 실제로 붙었는가'를 검사한다.
JOIN_KEY_BUG=True로 바꾸면 키 불일치로 적용성이 0건 기록되는 실제 버그를 재현한다.
검색 결과·판정은 대역 데이터다.
"""

from dataclasses import dataclass, field

MAX_MORE = 2
MIN_EVIDENCE = 2
JOIN_KEY_BUG = False

SEARCH_ROUNDS = [  # 라운드별로 새로 들어오는 근거
    [{"locator": "ESCC-3009#4.3", "text": "ceramic capacitors shall be screened ..."},
     {"locator": "ESCC-3012#2.1", "text": "tantalum capacitors shall ..."}],
    [{"locator": "ESCC-3009-001#3.2", "text": "detail spec for ceramic chip capacitors ..."}],
    [{"locator": "ECSS-Q-ST-60#5.2", "text": "EEE parts procurement general ..."}],
]


@dataclass
class State:
    part: str
    evidence: list[dict] = field(default_factory=list)
    applicability: dict[str, dict] = field(default_factory=dict)
    rounds: int = 0
    log: list[str] = field(default_factory=list)


def research(state: State) -> None:
    new = SEARCH_ROUNDS[state.rounds] if state.rounds < len(SEARCH_ROUNDS) else []
    state.evidence += new
    state.log.append(f"round {state.rounds}: 근거 {len(new)}건 추가")


def judge(part: str, ev: dict) -> tuple[bool, str]:
    """LLM 판정 대역: 부품 종류와 근거 대상이 같은가."""
    if "tantalum" in ev["text"]:
        return False, "탄탈 커패시터 조항 — 질문 부품(세라믹)에 부적용"
    if "general" in ev["text"]:
        return True, "EEE 부품 공통 조항 — 적용"
    return True, "세라믹 커패시터 조항 — 적용"


def verify_applicability(state: State) -> None:
    keep = []
    for ev in state.evidence:
        ok, reason = judge(state.part, ev)
        key = ev["text"][:10] if JOIN_KEY_BUG else ev["locator"]  # 버그: 다른 키로 저장
        state.applicability[key] = {"applicable": ok, "reason": reason}
        if ok:
            keep.append(ev)
        else:
            state.log.append(f"  제거: {ev['locator']} ({reason})")
    state.evidence = keep  # 표시만 하지 않고 실제로 지운다


def run(part: str) -> State:
    state = State(part)
    research(state)
    while True:
        verify_applicability(state)  # 루프 안쪽: 새로 들어온 근거도 매번 검증
        if len(state.evidence) >= MIN_EVIDENCE + 1 or state.rounds >= MAX_MORE:
            break
        state.rounds += 1
        research(state)
    return state


def final_evidence(state: State) -> list[dict]:
    # 화면이 읽는 필드: 근거마다 locator로 적용성을 붙인다
    return [{**ev, "applicability": state.applicability.get(ev["locator"])} for ev in state.evidence]


def test_applicability_is_attached(evidence: list[dict]) -> None:
    missing = [e["locator"] for e in evidence if e["applicability"] is None]
    assert not missing, f"적용성이 계산됐지만 최종 필드에 연결되지 않음: {missing}"


def main() -> None:
    state = run("세라믹 커패시터 100nF")
    print("\n".join(state.log))
    evidence = final_evidence(state)
    print("\n최종 근거:")
    for e in evidence:
        a = e["applicability"]
        print(f"  {e['locator']:<20} {a['reason'] if a else '[!] 적용성 미기록'}")
    test_applicability_is_attached(evidence)
    print("\n테스트 통과: 모든 최종 근거에 적용성 판정이 연결됨")


if __name__ == "__main__":
    main()
