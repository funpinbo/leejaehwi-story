"""세미나 Part 2 시연: 한 줄 질문 vs Persona + CoT 프롬프트.

'지식'은 넣어주고(참고 자료), '생각'은 유도한다(단계별 절차) — 세미나의 두 축을 그대로 프롬프트로 옮겼다.
"""

PAD_STEPS = [
    "부품 종류 판단",
    "적용 규격 확인",
    "규격 Revision 확인",
    "프로젝트 Class 확인",
    "시험 / Qualification 확인",
    "PAD 항목 작성",
]


def naive(question: str) -> str:
    return question


def persona_cot(question: str, references: list[str]) -> str:
    steps = "\n".join(f"{i}. {s}" for i, s in enumerate(PAD_STEPS, 1))
    refs = "\n".join(f"- {r}" for r in references) or "- (없음)"
    return f"""[역할]
너는 우주 부품 PAD(Part Approval Document)를 검토하는 품질 엔지니어다.

[참고 자료]  ← 지식: 모델이 기억에서 꺼내게 하지 말고 넣어준다
{refs}

[절차]  ← 생각: 아래 순서대로 한 단계씩 판단하고, 각 단계의 근거를 적어라
{steps}

[규칙]
- 참고 자료에 없는 규격 번호나 Revision은 만들지 말고 "확인 필요"라고 적어라.
- 마지막에 PAD 항목만 표로 정리하라.

[질문]
{question}"""


def main() -> None:
    q = "PN-2026-0412 세라믹 커패시터의 PAD 시험 항목을 작성해줘."
    refs = ["부품 데이터시트 요약: 세라믹 커패시터, 우주급", "사내 규격 목록: ESCC-3009 (최신 Issue 5, 예시)"]
    print("=== Before: 한 줄 질문 ===")
    print(naive(q))
    print("\n=== After: Persona + 참고 자료 + CoT 절차 ===")
    print(persona_cot(q, refs))


if __name__ == "__main__":
    main()
