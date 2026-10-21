"""Specification List(이슈 단위 행) → 문서 단위 canonical record.

입력 CSV는 형식만 흉내 낸 합성 데이터이며, 문서 번호·제목·Issue는 예시다.
"""

import csv
import io
import json
import re

RAW_CSV = """doc_number,title,issue,date,category
ESCC 3009,"Capacitors, fixed, ceramic, generic specification",4,2015-03,Generic
ESCC3009,"Capacitors, Fixed, Ceramic, Generic Specification",5,2019-11,Generic
ESCC 3009/001,"Capacitors, ceramic, detail specification",2,2018-06,Detail
ESCC 2269000,Evaluation test programme for EEE parts,3,2017-02,Basic
ESCC 2269000,Evaluation test programme for EEE parts,4,2021-09,Basic
ESCC 22900,Total dose steady-state irradiation test method,5,2016-05,Basic
ESCC 25500,Leak testing,2,2014-01,Basic
"""

PAD_KEYWORDS = {"generic": 0.3, "detail": 0.3, "evaluation": 0.3, "irradiation": 0.2, "test": 0.1}
FAMILY = re.compile(r"\b(capacitors?|resistors?|diodes?|transistors?|microcircuits?)\b", re.I)
TEST_METHOD = re.compile(r"\b(irradiation|leak|evaluation|burn-in|vibration)\b", re.I)


def normalize_number(raw: str) -> str:
    """'ESCC3009', 'ESCC 3009' → 'ESCC-3009', 'ESCC 3009/001' → 'ESCC-3009-001'."""
    m = re.match(r"^\s*ESCC\s*(\d+)(?:/(\d+))?\s*$", raw, re.I)
    if not m:
        raise ValueError(f"알 수 없는 번호 형식: {raw}")
    return "ESCC-" + m.group(1) + (f"-{m.group(2)}" if m.group(2) else "")


def pad_score(title: str) -> float:
    t = title.lower()
    return round(min(sum(w for k, w in PAD_KEYWORDS.items() if k in t), 1.0), 2)


def canonicalize(rows: list[dict]) -> list[dict]:
    records: dict[str, dict] = {}
    for row in rows:
        key = normalize_number(row["doc_number"])
        rec = records.setdefault(key, {"doc_number": key, "issues": []})
        rec["issues"].append({"issue": int(row["issue"]), "date": row["date"], "title": row["title"].strip()})

    out = []
    for rec in records.values():
        rec["issues"].sort(key=lambda i: i["issue"])
        latest = rec["issues"][-1]
        title = latest["title"]
        category = next(r["category"] for r in rows if normalize_number(r["doc_number"]) == rec["doc_number"])
        out.append({
            "schema_version": "1.1",
            "doc_number": rec["doc_number"],
            "title": title,
            "category": category,
            "latest_issue": latest["issue"],
            "issues": rec["issues"],
            "search_text": f"{rec['doc_number']} {rec['doc_number'].replace('-', ' ')} {title} {category}".lower(),
            "pad": {"score": pad_score(title), "method": "heuristic:title_keywords"},
            "graph_hints": {
                "component_family": sorted({m.lower().rstrip("s") for m in FAMILY.findall(title)}),
                "test_method": sorted({m.lower() for m in TEST_METHOD.findall(title)}),
                "parent": rec["doc_number"].rsplit("-", 1)[0] if rec["doc_number"].count("-") == 2 else None,
                "supersedes": [f"{rec['doc_number']}@{i['issue']}" for i in rec["issues"][:-1]],
            },
        })
    return out


def main() -> None:
    rows = list(csv.DictReader(io.StringIO(RAW_CSV)))
    records = canonicalize(rows)
    print(f"원본 이슈 행 {len(rows)}건 → canonical record {len(records)}건\n")
    print(f"{'doc_number':<16}{'최신':>4}{'이력':>5}{'pad':>6}  graph_hints")
    for r in records:
        hints = {k: v for k, v in r["graph_hints"].items() if v}
        print(f"{r['doc_number']:<16}{r['latest_issue']:>4}{len(r['issues']):>5}{r['pad']['score']:>6}  {hints}")
    print("\n예시 record:")
    print(json.dumps(records[0], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
