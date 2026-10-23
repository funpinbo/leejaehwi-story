"""'LLM은 판정하지 않는다' — 분류·코드 확정·규격 계보·품질 등급 단계 축소 재현.

- classify : LLM이 닫힌 선택지 중 하나를 고른다 (밖의 값이면 거부)
- code     : LLM은 후보만, 코드 테이블에 있는 것만 확정
- lineage  : LLM 없음. 근거 문장에서 규격 번호를 정규식으로 뽑고, 승인된 관계만 따라간다
- quality  : LLM 없음. 순수 규칙
모든 결과는 값 + 근거 + 상태를 가진 슬롯으로 남긴다. 코드·규격 값은 예시다.
"""

import json
import re
from dataclasses import asdict, dataclass, field
from typing import Literal

Status = Literal["CONFIRMED", "CANDIDATE", "MISSING"]
CLASSES = {"ELECTRONIC", "MATERIAL", "MECHANICAL"}

CODE_TABLE = {"ELECTRONIC": {"F-CAP-0101": "세라믹 커패시터", "F-RES-0201": "박막 저항"}}
SPEC_EDGES = [  # (child, parent, status) — 사람이 승인한 관계만 판정에 사용
    ("ESCC-3009-001", "ESCC-3009", "approved"),
    ("ESCC-3009", "ESCC-2269000", "approved"),
    ("ESCC-3009", "MIL-PRF-55681", "candidate"),  # 아직 승인 전
]


@dataclass
class Slot:
    field: str
    value: str | None
    status: Status
    decided_by: str
    evidence: list[str] = field(default_factory=list)


# ---------- LLM 대역: 그럴듯하지만 틀린 것도 섞어 낸다 ----------
def llm_classify(text: str) -> str:
    return "ELECTRONIC"


def llm_code_candidates(text: str) -> list[str]:
    return ["F-CAP-0199", "F-CAP-0101"]  # 0199는 테이블에 없는 '만들어낸' 코드


# ---------- STEP ----------
def classify(text: str) -> Slot:
    label = llm_classify(text)
    if label not in CLASSES:
        return Slot("part_class", None, "MISSING", "llm_closed_set", [f"선택지 밖 응답 '{label}' 거부"])
    return Slot("part_class", label, "CONFIRMED", "llm_closed_set", [f"선택지 {sorted(CLASSES)}"])


def code_step(part_class: str, text: str) -> Slot:
    table = CODE_TABLE.get(part_class, {})
    candidates = llm_code_candidates(text)
    rejected = [f"LLM 후보 {c} — 코드 테이블에 없음, 제외" for c in candidates if c not in table]
    for cand in candidates:
        if cand in table:
            return Slot("part_code", cand, "CONFIRMED", "table",
                        rejected + [f"code_table[{part_class}][{cand}]={table[cand]}"])
    return Slot("part_code", None, "MISSING", "table", rejected)


def lineage(evidence_text: str) -> Slot:
    found = re.findall(r"\b(?:ESCC|ECSS|MIL)-[A-Z0-9-]+\b", evidence_text)
    if not found:
        return Slot("spec_lineage", None, "MISSING", "rule", ["근거 문장에서 규격 번호를 찾지 못함"])
    chain, cur = [found[0]], found[0]
    while True:
        parents = [p for c, p, s in SPEC_EDGES if c == cur and s == "approved"]
        if not parents:
            break
        cur = parents[0]
        chain.append(cur)
    skipped = [f"{c}→{p} (status={s})" for c, p, s in SPEC_EDGES if c in chain and s != "approved"]
    ev = [f"근거 문장: '{evidence_text}'"] + [f"미승인 관계 제외: {x}" for x in skipped]
    return Slot("spec_lineage", " > ".join(chain), "CONFIRMED", "rule+approved_edges", ev)


def quality(project_class: int, has_eval: bool) -> Slot:
    if project_class == 1 and not has_eval:
        return Slot("quality_level", None, "MISSING", "rule", ["Class 1인데 평가 시험 이력 없음 → 사람 확인"])
    level = "Q1" if project_class == 1 else "Q2"
    return Slot("quality_level", level, "CONFIRMED", "rule", [f"project_class={project_class}, has_eval={has_eval}"])


def main() -> None:
    text = "부품: 세라믹 커패시터 100nF, 우주급"
    datasheet_evidence = "Procured in accordance with ESCC-3009-001."
    s1 = classify(text)
    slots = [s1, code_step(s1.value, text), lineage(datasheet_evidence),
             quality(project_class=1, has_eval=False)]

    print(json.dumps([asdict(s) for s in slots], ensure_ascii=False, indent=2))
    need = [s.field for s in slots if s.status != "CONFIRMED"]
    print(f"\n사람이 확인할 칸: {need or '없음'}")


if __name__ == "__main__":
    main()
