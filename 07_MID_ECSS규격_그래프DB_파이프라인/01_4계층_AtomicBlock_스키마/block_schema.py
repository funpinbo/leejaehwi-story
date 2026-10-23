"""4계층(Document → Page → Group → Block) 중 Block 스키마와 추출 예제.

입력 텍스트는 ECSS 원문이 아니라 구조만 흉내 낸 합성 텍스트다.
LLM 추출 대신 규칙 기반 추출을 쓰고, 규칙이 애매한 경우 confidence를 낮추고 requires_review를 켠다.

pip install pydantic
"""

import json
import re
from typing import Literal

from pydantic import BaseModel, Field

REVIEW_THRESHOLD = 0.7
REF = re.compile(r"\b(?:ECSS|ESCC|MIL)-[A-Z0-9-]+\b")


class Source(BaseModel):
    source_region_id: str  # 원본 PDF의 페이지·영역 ID (Layout 분석 단계에서 부여)
    span: tuple[int, int]  # region 텍스트 안의 문자 위치 (evidence span)


class Reference(BaseModel):
    target_doc: str
    target_clause: str | None = None
    resolved: bool  # 참조 대상 조항까지 확정했는가


class Block(BaseModel):
    block_id: str
    meaning_type: Literal["REQUIREMENT", "DEFINITION", "NOTE", "HEADING", "TEXT"]
    atomic_text: str              # 원문 그대로 (불변)
    normalized_text: str          # 검색·LLM용 (가공 가능)
    confidence: float = Field(ge=0, le=1)
    requires_review: bool
    section_path: list[str]
    sources: list[Source]
    references: list[Reference] = []


# 합성 규격 텍스트: (region_id, section, 텍스트)
REGIONS = [
    ("p12-r1", "5.2", "5.2 Procurement requirements"),
    ("p12-r2", "5.2.1", "a. The supplier shall procure EEE parts in conformance with ESCC-3009 clause 4.3."),
    ("p12-r3", "5.2.1", "b. Parts used in Class 1 projects should be screened as specified in the applicable detail specification."),
    ("p12-r4", "5.2.1", "NOTE Additional guidance is provided in MIL-PRF-123."),
    ("p13-r1", "5.2.2", "c. Radiation hardness shall be verified as agreed with the customer, see ECSS-Q-ST-60."),
]


def classify(text: str) -> tuple[str, float]:
    if text.startswith("NOTE"):
        return "NOTE", 0.95
    if re.match(r"^\d+(\.\d+)*\s", text):
        return "HEADING", 0.98
    if re.search(r"\bshall\b", text):
        return "REQUIREMENT", 0.9
    if re.search(r"\bshould\b", text):
        return "REQUIREMENT", 0.75  # 권고 조항 — 요구사항으로 볼지 애매
    return "TEXT", 0.6


def section_path(section: str) -> list[str]:
    """'5.2.1' → ['5', '5.2', '5.2.1']"""
    parts = section.split(".")
    return [".".join(parts[: k + 1]) for k in range(len(parts))]


def extract(doc_id: str) -> list[Block]:
    blocks = []
    for i, (region, section, text) in enumerate(REGIONS):
        meaning, conf = classify(text)
        refs = []
        for m in REF.finditer(text):
            clause = re.search(rf"{re.escape(m.group())} clause (\d+(?:\.\d+)*)", text)
            refs.append(Reference(target_doc=m.group(), target_clause=clause.group(1) if clause else None,
                                  resolved=bool(clause)))
        # 참조 대상 조항이 불명확하거나 "as agreed" 같은 열린 조건이면 신뢰도를 낮춘다
        if any(not r.resolved for r in refs):
            conf -= 0.1
        if "as agreed" in text:
            conf -= 0.15
        conf = round(max(conf, 0.0), 2)
        blocks.append(Block(
            block_id=f"{doc_id}:{section}:{i:03d}",
            meaning_type=meaning,
            atomic_text=text,
            normalized_text=re.sub(r"^[a-z]\.\s*", "", text),
            confidence=conf,
            requires_review=conf < REVIEW_THRESHOLD,
            section_path=section_path(section),
            sources=[Source(source_region_id=region, span=(0, len(text)))],
            references=refs,
        ))
    return blocks


def main() -> None:
    blocks = extract("DEMO-SPEC-01")
    print(json.dumps(blocks[1].model_dump(), ensure_ascii=False, indent=2))
    print("\n=== 추출 요약 ===")
    print(f"{'block_id':<24}{'type':<13}{'conf':>5}  review  refs")
    for b in blocks:
        refs = ", ".join(r.target_doc + (f"§{r.target_clause}" if r.target_clause else "") for r in b.references)
        print(f"{b.block_id:<24}{b.meaning_type:<13}{b.confidence:>5}  {'[!] yes' if b.requires_review else '  no'}   {refs}")
    review = [b for b in blocks if b.requires_review]
    print(f"\n사람 검토 대상 {len(review)}/{len(blocks)}건 — 이것만 보면 된다")


if __name__ == "__main__":
    main()
