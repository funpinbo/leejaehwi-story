"""근거 상한(MAX_TOTAL_EVIDENCE) 적용: 가짜 score=1.0 vs '점수 없음 = 키 없음'.

근거 데이터는 예시다. relevant=True는 사람이 보기에 질문에 가장 중요한 근거.
"""

MAX_TOTAL_EVIDENCE = 3

EVIDENCE = [
    {"id": "vec-ESCC3009-4.3", "source_type": "vector", "score": 0.86, "relevant": True},
    {"id": "vec-ESCC3009-001", "source_type": "vector", "score": 0.81, "relevant": True},
    {"id": "vec-ECSS-Q60-5.2", "source_type": "vector", "score": 0.62, "relevant": False},
    {"id": "sql-code-table", "source_type": "sql", "relevant": False},
    {"id": "web-blog-post", "source_type": "web", "relevant": False},
    {"id": "graph-spec-edge", "source_type": "graph", "relevant": False},
    {"id": "task-screening", "source_type": "vector", "score": 0.55, "task_name": "screening", "relevant": True},
]


def cap_old(evidence: list[dict]) -> list[dict]:
    """이전: 점수 없는 근거에 1.0을 찍고 전체를 점수순 정렬."""
    filled = [{**ev, "score": ev.get("score", 1.0)} for ev in evidence]
    return sorted(filled, key=lambda ev: -ev["score"])[:MAX_TOTAL_EVIDENCE]


def cap_new(evidence: list[dict]) -> list[dict]:
    """수정: 태그 근거·점수 없는 근거는 상한 밖에서 보존, 점수 있는 근거만 상한."""
    tagged = [ev for ev in evidence if ev.get("task_name")]
    rest = [ev for ev in evidence if not ev.get("task_name")]
    scored = sorted((ev for ev in rest if "score" in ev), key=lambda ev: -ev["score"])
    unscored = [ev for ev in rest if "score" not in ev]
    return [*tagged, *unscored, *scored[:MAX_TOTAL_EVIDENCE]]


def report(name: str, kept: list[dict]) -> None:
    ids = {ev["id"] for ev in kept}
    lost = [ev["id"] for ev in EVIDENCE if ev["relevant"] and ev["id"] not in ids]
    print(f"[{name}] 남은 근거 {len(kept)}개")
    for ev in kept:
        score = f"{ev['score']:.2f}" if "score" in ev else "없음"
        print(f"   {ev['id']:<20} score={score:<5} {'★ 핵심' if ev['relevant'] else ''}")
    print(f"   → 잘린 핵심 근거: {lost or '없음 ✅'}\n")


if __name__ == "__main__":
    report("이전: 없는 점수를 1.0으로", cap_old(EVIDENCE))
    report("수정: 없는 점수는 키 없음", cap_new(EVIDENCE))
