"""체크포인터의 턴 간 state 누수 재현.

체크포인터 동작: 노드가 반환한 키만 덮어쓰고, 이번 턴에 아무도 안 쓴 키는 이전 턴 값을 유지한다.
누수 필드: part_identity(부품 식별), variant_warning(변형 경고) — 기술 경로에서만 갱신된다.
--bug    : 턴 시작 리셋 없음 → 사내 정책 질문 답변에 이전 부품 정보가 남는다
기본 실행 : TURN_SCOPED_FIELDS를 턴 시작에 명시적으로 초기화
"""

import sys

TURN_SCOPED_FIELDS = {"query_domain": None, "part_identity": None, "variant_warning": None, "evidence": []}
RESET_AT_TURN_START = "--bug" not in sys.argv


class Checkpointer:
    def __init__(self):
        self.saved: dict = {"history": []}

    def run_turn(self, graph, question: str) -> dict:
        state = dict(self.saved)  # 지난 턴 state를 이어받는다
        state["question"] = question
        for node in graph(state):
            state.update(node(state))  # reducer 없음: 반환한 키만 덮어씀
        self.saved = state
        return state


# ---------- 노드 ----------
def turn_start(state):
    return dict(TURN_SCOPED_FIELDS) if RESET_AT_TURN_START else {}


def user_intent(state):
    domain = "technical" if "커패시터" in state["question"] else "company_policy"
    return {"query_domain": domain}


def classify_part(state):  # 기술 경로에서만 실행
    return {"part_identity": {"part_number": "PN-2026-0412", "family": "Capacitor"},
            "variant_warning": "변형 접미사 '/883' 감지 — 등급 확인 필요"}


def policy_research(state):
    return {"evidence": [{"source": "사내 규정 3.2", "snippet": "해외 출장은 7일 전 신청"}]}


def answer(state):
    meta = {"part": state.get("part_identity")}
    prompt = f"질문: {state['question']}"
    if state.get("variant_warning"):  # 경고가 있으면 무조건 덧붙이던 코드
        prompt += f"\n[주의] {state['variant_warning']}"
    return {"answer_meta": meta, "answer_prompt": prompt,
            "history": state["history"] + [state["question"]]}


def graph(state):
    yield turn_start
    yield user_intent
    if state.get("query_domain") == "technical" or "커패시터" in state["question"]:
        yield classify_part
    else:
        yield policy_research
    yield answer


def main() -> None:
    print(f"RESET_AT_TURN_START = {RESET_AT_TURN_START}  (--bug 옵션으로 누수 재현)\n")
    cp = Checkpointer()
    for q in ["세라믹 커패시터 PN-2026-0412의 적용 규격은?", "해외 출장 신청은 며칠 전에 해야 해?"]:
        s = cp.run_turn(graph, q)
        print(f"Q: {q}")
        print(f"   answer_meta   = {s['answer_meta']}")
        print(f"   answer_prompt = {s['answer_prompt']!r}\n")
    leaked = s["answer_meta"]["part"] is not None or "[주의]" in s["answer_prompt"]
    print("두 번째(사내 정책) 턴:", "⚠ 이전 턴의 부품 정보·경고가 새어 나옴" if leaked else "누수 없음 ✅")
    print("대화 이력(턴을 넘어 유지되어야 하는 필드):", s["history"])


if __name__ == "__main__":
    main()
