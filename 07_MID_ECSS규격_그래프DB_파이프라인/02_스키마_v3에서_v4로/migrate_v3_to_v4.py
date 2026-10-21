"""Block 스키마 v3 → v4(schema_version 1.1) 마이그레이션 예제.

v4 변경점
  1. groups 신설 (LIST / FIGURE / TABLE / CONDITION_SCOPE)
  2. relations 신설 (리드인 → 하위 항목 GOVERNS)
  3. normalized_text에 리드인 주입 (atomic_text는 불변)
  4. normative_type → derived_fields 로 분리
  5. 스키마 메타 선언 (required / deferred / derived_fields)
입력은 구조만 흉내 낸 합성 데이터다.
"""

import json
import re

V3_BLOCKS = [
    {"block_id": "B010", "section": "6.1", "atomic_text": "다음의 경우 공급자는 고객의 사전 승인을 받아야 한다:",
     "normalized_text": "다음의 경우 공급자는 고객의 사전 승인을 받아야 한다:", "normative_type": "MANDATORY"},
    {"block_id": "B011", "section": "6.1", "atomic_text": "a. 제조 공정을 변경하는 경우",
     "normalized_text": "제조 공정을 변경하는 경우", "normative_type": None},
    {"block_id": "B012", "section": "6.1", "atomic_text": "b. 부품을 대체품으로 교체하는 경우",
     "normalized_text": "부품을 대체품으로 교체하는 경우", "normative_type": None},
    {"block_id": "B020", "section": "6.2", "atomic_text": "시험 결과는 보관하는 것이 바람직하다.",
     "normalized_text": "시험 결과는 보관하는 것이 바람직하다.", "normative_type": "RECOMMENDED"},
]

V4_META = {
    "schema_version": "1.1",
    "required": ["block_id", "atomic_text", "normalized_text", "section_path", "sources"],
    "deferred": ["references"],  # 아직 추출하지 않음 — 비어 있어도 오류가 아님
    "derived_fields": ["normative_type"],  # 원문이 아니라 규칙/LLM으로 추론한 값
}

LEAD_IN = re.compile(r"(다음|아래)의?.*[:：]\s*$")
ITEM = re.compile(r"^([a-z])\.\s*")


def infer_normative(text: str) -> str | None:
    if re.search(r"(야 한다|어야 한다)", text):  # 해야·받아야·하여야 한다
        return "MANDATORY"
    if re.search(r"(바람직하다|권장)", text):
        return "RECOMMENDED"
    return None


def migrate(v3: list[dict]) -> dict:
    blocks, groups, relations = [], [], []
    lead_in = None
    for b in v3:
        nb = {
            "block_id": b["block_id"],
            "atomic_text": b["atomic_text"],  # 원문 불변
            "normalized_text": b["normalized_text"],
            "section_path": b["section"],
            "sources": [{"source_region_id": f"demo-{b['block_id']}"}],
            "derived_fields": {},
        }
        if LEAD_IN.search(b["atomic_text"]):
            lead_in = nb
            groups.append({"group_id": f"G-{b['block_id']}", "group_type": "LIST",
                           "lead_in": b["block_id"], "members": []})
        elif ITEM.match(b["atomic_text"]) and lead_in and lead_in["section_path"] == b["section"]:
            groups[-1]["members"].append(b["block_id"])
            relations.append({"type": "GOVERNS", "from": lead_in["block_id"], "to": b["block_id"]})
            # 리드인 주입: 검색·LLM용 텍스트에만 문맥을 보강
            nb["normalized_text"] = f"{lead_in['atomic_text']} {b['normalized_text']}"
        else:
            lead_in = None
        # 추론 값은 derived_fields로 (리드인이 주입된 문맥 기준으로 다시 추론)
        nb["derived_fields"]["normative_type"] = infer_normative(nb["normalized_text"])
        blocks.append(nb)
    return {**V4_META, "groups": groups, "relations": relations, "blocks": blocks}


def validate(doc: dict) -> list[str]:
    errors = []
    for b in doc["blocks"]:
        errors += [f"{b['block_id']}: '{f}' 누락" for f in doc["required"] if not b.get(f)]
        unknown = set(b["derived_fields"]) - set(doc["derived_fields"])
        errors += [f"{b['block_id']}: 선언되지 않은 derived field {unknown}"] if unknown else []
    return errors


def main() -> None:
    v4 = migrate(V3_BLOCKS)
    print("=== v3 → v4: 목록 항목 b의 변화 ===")
    v3_b = V3_BLOCKS[2]
    v4_b = next(b for b in v4["blocks"] if b["block_id"] == "B012")
    print(f"v3 normalized_text : {v3_b['normalized_text']}")
    print(f"v3 normative_type  : {v3_b['normative_type']}")
    print(f"v4 atomic_text     : {v4_b['atomic_text']}   (원문 불변)")
    print(f"v4 normalized_text : {v4_b['normalized_text']}")
    print(f"v4 derived_fields  : {v4_b['derived_fields']}")

    print("\n=== v4 groups / relations ===")
    print(json.dumps({"groups": v4["groups"], "relations": v4["relations"]}, ensure_ascii=False, indent=2))
    errors = validate(v4)
    print(f"\n스키마 검증 (schema_version {v4['schema_version']}): {'통과 ✅' if not errors else errors}")


if __name__ == "__main__":
    main()
