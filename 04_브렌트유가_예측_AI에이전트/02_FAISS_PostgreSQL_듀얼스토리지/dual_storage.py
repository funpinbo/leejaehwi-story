"""Vector DB(의미 검색) + RDB(메타데이터·근거 추적) 듀얼 스토리지.

실제 구성: FAISS + PostgreSQL
예제 구성: numpy 완전 탐색 인덱스(FAISS IndexFlatIP와 동일) + SQLite
"""

import json
import re
import sqlite3
import zlib

import numpy as np


def embed(text: str, dim: int = 256) -> np.ndarray:
    v = np.zeros(dim, dtype=np.float32)
    for w in re.findall(r"\w+", text.lower()):
        for n in (1, 2):  # 단어 단위 + 글자 2gram (표현 차이 완화)
            grams = [w] if n == 1 else [w[i : i + 2] for i in range(len(w) - 1)]
            for g in grams:
                v[zlib.crc32(g.encode()) % dim] += 1
    return v / (np.linalg.norm(v) or 1)


class FlatIndex:
    """FAISS IndexFlatIP 대역: 정규화 벡터의 내적 = 코사인 유사도, 완전 탐색."""

    def __init__(self, dim: int):
        self.vectors = np.empty((0, dim), dtype=np.float32)
        self.ids: list[int] = []

    def add(self, doc_id: int, vec: np.ndarray) -> None:
        self.vectors = np.vstack([self.vectors, vec])
        self.ids.append(doc_id)

    def search(self, q: np.ndarray, k: int) -> list[tuple[int, float]]:
        sims = self.vectors @ q
        top = np.argsort(-sims)[:k]
        return [(self.ids[i], float(sims[i])) for i in top]


NEWS = [
    (1, "2024-01-12", "Reuters", 0, "홍해 송유관 공격으로 원유 공급 차질 우려"),
    (2, "2024-02-03", "Bloomberg", 2, "OPEC 산유국 회의에서 생산량 확대 합의"),
    (3, "2024-03-18", "연합뉴스", 1, "중국 제조업 지표 부진에 원유 수요 둔화 전망"),
    (4, "2024-04-02", "Reuters", 0, "중동 정세 악화로 원유 생산 시설 가동 중단"),
    (5, "2024-05-21", "Bloomberg", 1, "글로벌 경기 둔화로 석유 수요 감소"),
]
CLUSTER_EFFECT = [(0, "공급 차질", +0.0234, 16), (1, "수요 둔화", -0.0111, 14), (2, "OPEC 증산", -0.0197, 15)]


def build() -> tuple[sqlite3.Connection, FlatIndex]:
    db = sqlite3.connect(":memory:")
    db.executescript(
        """
        CREATE TABLE news (doc_id INTEGER PRIMARY KEY, date TEXT, source TEXT, cluster_id INTEGER, text TEXT);
        CREATE TABLE cluster_effect (cluster_id INTEGER PRIMARY KEY, name TEXT, car REAL, n_events INTEGER);
        CREATE TABLE query_log (id INTEGER PRIMARY KEY, question TEXT, doc_ids TEXT, answer TEXT);
        """
    )
    db.executemany("INSERT INTO news VALUES (?,?,?,?,?)", NEWS)
    db.executemany("INSERT INTO cluster_effect VALUES (?,?,?,?)", CLUSTER_EFFECT)

    index = FlatIndex(256)
    for doc_id, *_, text in NEWS:
        index.add(doc_id, embed(text))  # 벡터 DB에는 원문 임베딩과 doc_id만
    return db, index


def db_tool(db: sqlite3.Connection, index: FlatIndex, question: str, k: int = 2) -> list[dict]:
    """에이전트 DB Tool: 의미 검색(VDB) → doc_id로 메타데이터 조인(RDB)."""
    hits = index.search(embed(question), k)
    ids = [doc_id for doc_id, _ in hits]
    rows = db.execute(
        f"""
        SELECT n.doc_id, n.date, n.source, n.text, c.name, c.car, c.n_events
        FROM news n JOIN cluster_effect c USING (cluster_id)
        WHERE n.doc_id IN ({",".join("?" * len(ids))})
        """,
        ids,
    ).fetchall()
    by_id = {r[0]: r for r in rows}
    return [
        dict(zip(["doc_id", "date", "source", "text", "cluster", "car", "n_events"], by_id[i]), sim=round(s, 3))
        for i, s in hits
    ]


def main() -> None:
    db, index = build()
    question = "최근 원유 공급 차질 뉴스는 과거에 유가를 어떻게 움직였어?"
    results = db_tool(db, index, question)

    print(f"질문: {question}\n")
    for r in results:
        print(f"[doc {r['doc_id']}] {r['date']} {r['source']} (sim {r['sim']})")
        print(f"   {r['text']}")
        print(f"   → 클러스터 '{r['cluster']}': 과거 {r['n_events']}건 평균 CAR {r['car']:+.2%}")

    answer = f"공급 차질 유형 뉴스는 과거 평균 {results[0]['car']:+.2%}의 누적 비정상 수익률을 보였습니다."
    db.execute(
        "INSERT INTO query_log (question, doc_ids, answer) VALUES (?,?,?)",
        (question, json.dumps([r["doc_id"] for r in results]), answer),
    )

    print("\n=== 근거 추적: 어떤 질문에 어떤 문서가 쓰였나 (SQL) ===")
    for q, ids, a in db.execute("SELECT question, doc_ids, answer FROM query_log"):
        print(f"Q: {q}\n   근거 doc_ids: {ids}\n   A: {a}")


if __name__ == "__main__":
    main()
