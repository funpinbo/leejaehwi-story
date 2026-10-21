"""세미나 Part 4 시연: 무엇이 토큰을 쓰는가, 어떻게 줄이는가.

토큰 수는 교육용 근사치다 (한국어 약 1.5자/토큰, 그 외 약 4자/토큰).
실제 값은 모델의 토크나이저마다 다르다.
"""

import re


def approx_tokens(text: str) -> int:
    korean = len(re.findall(r"[가-힣]", text))
    other = len(re.sub(r"[가-힣\s]", "", text))
    return round(korean / 1.5 + other / 4)


SYSTEM = "너는 우주 부품 PAD 검토 전문가다. 부품 종류 판단 → 적용 규격 확인 → Revision 확인 → 프로젝트 Class 확인 → 시험/Qualification 확인 → PAD 항목 작성 순서로 생각하라. " * 2
TURN = "사용자: 이 부품의 적용 규격과 시험 항목을 정리해줘. 어시스턴트: 해당 부품은 세라믹 커패시터로 일반 규격과 상세 규격이 적용되며, 평가 시험과 방사선 시험이 필요합니다. " * 3
RAG_CHUNK = "규격 조항 예시: The supplier shall procure EEE parts in conformance with the applicable generic specification and detail specification. " * 4
TOOL_RESULT = '{"doc": "ESCC-3009", "issues": [4, 5], "title": "Capacitors, fixed, ceramic", "history": [...], "raw": "' + "x" * 1500 + '"}'
QUESTION = "PN-2026-0412 부품의 PAD 5장 시험 항목 초안을 작성해줘."


def budget(history_turns: int, rag_k: int, tool_results: int, summarize: bool, filter_tool: bool) -> dict:
    history = approx_tokens(TURN) * history_turns
    if summarize and history_turns > 3:
        history = approx_tokens(TURN) * 1 + 80  # 오래된 대화는 요약 1개로
    tool = approx_tokens(TOOL_RESULT) * tool_results
    if filter_tool:
        tool = tool_results * 40  # 필요한 필드만 남김
    return {
        "System Prompt": approx_tokens(SYSTEM),
        "Chat History": history,
        "RAG 결과": approx_tokens(RAG_CHUNK) * rag_k,
        "Tool 결과": tool,
        "질문": approx_tokens(QUESTION),
    }


def show(title: str, b: dict) -> int:
    total = sum(b.values())
    print(f"\n[{title}] 합계 약 {total:,} 토큰")
    for k, v in b.items():
        bar = "█" * max(1, round(v / total * 40))
        print(f"  {k:<14}{v:>6,}  {bar}")
    return total


def main() -> None:
    before = show("긴 대화 30턴 · RAG 10개 · Tool 결과 원본 3개",
                  budget(history_turns=30, rag_k=10, tool_results=3, summarize=False, filter_tool=False))
    after = show("이력 요약 · RAG Top-3 · Tool 결과 필드 필터링",
                 budget(history_turns=30, rag_k=3, tool_results=3, summarize=True, filter_tool=True))
    print(f"\n→ 약 {1 - after / before:.0%} 절감. 매 요청마다 반복되므로 대화가 길수록 차이가 커진다.")


if __name__ == "__main__":
    main()
