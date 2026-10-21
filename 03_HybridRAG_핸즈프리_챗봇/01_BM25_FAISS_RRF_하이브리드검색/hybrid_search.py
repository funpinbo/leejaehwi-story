"""BM25 + Vector 검색을 RRF로 결합하는 하이브리드 검색 예제.

실제 프로젝트는 Elasticsearch(Nori) + FAISS를 썼다.
여기서는 외부 의존성 없이 동작하도록
  - BM25: 직접 구현 (k1=1.5, b=0.75)
  - Vector: 문자 n-gram 해싱 임베딩 + 코사인 유사도 (FAISS IndexFlatIP와 같은 완전 탐색)
으로 대체했다.
"""

import math
import re
import zlib
from collections import Counter

import numpy as np

DOCS = [
    "EBR-3D-OPT-V2 장비의 조명 캘리브레이션 절차와 GrayValue 기준",
    "검사 장비 광학계 조명 밝기를 맞추는 방법 안내",
    "공정이상감지 알람 발생 시 LOT 비교 테스트 요청 절차",
    "웨이퍼 가장자리 고리 형태 결함(Edge-Ring)의 원인 분석",
    "EBR-2D-STD 장비 정기 점검 체크리스트",
    "카메라 노출 시간과 이미지 밝기의 관계",
]

# 사용자 사전: 장비 코드는 쪼개지 않는다 (Nori 사용자 사전 역할)
USER_DICT = re.compile(r"[A-Z]{2,}(?:-[A-Z0-9]+)+")
# 간이 형태소 분리: 실제로는 Nori가 처리
COMPOUND = {"공정이상감지": ["공정", "이상", "감지"]}


def tokenize(text: str) -> list[str]:
    codes = USER_DICT.findall(text)
    rest = USER_DICT.sub(" ", text)
    tokens = []
    for w in re.findall(r"[가-힣A-Za-z0-9]+", rest):
        tokens += COMPOUND.get(w, [w])
    # 한국어 조사 간이 제거
    tokens = [re.sub(r"(의|를|을|이|가|와|과|은|는|에|에서)$", "", t) or t for t in tokens]
    return codes + tokens


class BM25:
    def __init__(self, docs: list[str], k1: float = 1.5, b: float = 0.75):
        self.docs = [tokenize(d) for d in docs]
        self.k1, self.b = k1, b
        self.avgdl = sum(map(len, self.docs)) / len(self.docs)
        df = Counter(t for d in self.docs for t in set(d))
        n = len(self.docs)
        self.idf = {t: math.log((n - f + 0.5) / (f + 0.5) + 1) for t, f in df.items()}

    def scores(self, query: str) -> list[float]:
        q = tokenize(query)
        out = []
        for d in self.docs:
            tf = Counter(d)
            s = 0.0
            for t in q:
                if t not in tf:
                    continue
                # TF 포화(k1) + 문서 길이 정규화(b)
                denom = tf[t] + self.k1 * (1 - self.b + self.b * len(d) / self.avgdl)
                s += self.idf[t] * tf[t] * (self.k1 + 1) / denom
            out.append(s)
        return out


def embed(text: str, dim: int = 512) -> np.ndarray:
    """문자 2~3gram 해싱 임베딩. 표현이 조금 달라도 겹치는 글자 조각으로 유사도가 생긴다."""
    v = np.zeros(dim)
    s = re.sub(r"\s+", " ", text.lower())
    for n in (2, 3):
        for i in range(len(s) - n + 1):
            v[zlib.crc32(s[i : i + n].encode()) % dim] += 1
    return v / (np.linalg.norm(v) or 1)  # L2 정규화 → 내적 = 코사인 유사도


def rank(scores) -> list[int]:
    return sorted(range(len(scores)), key=lambda i: -scores[i])


def rrf(*rankings: list[int], k: int = 60) -> list[tuple[int, float]]:
    fused: dict[int, float] = {}
    for ranking in rankings:
        for r, doc_id in enumerate(ranking, start=1):
            fused[doc_id] = fused.get(doc_id, 0.0) + 1 / (k + r)
    return sorted(fused.items(), key=lambda x: -x[1])


def main() -> None:
    bm25 = BM25(DOCS)
    doc_vecs = np.stack([embed(d) for d in DOCS])

    for query in [
        "EBR-3D-OPT-V2 캘리브레이션",   # 정확한 장비 코드 → BM25가 강함
        "EBR 3D OPT V2 캘리브래이션",   # STT 오인식(하이픈 누락·오타) → BM25 실패, Vector가 보완
        "공정 이상 알람 대응",
    ]:
        bm25_scores = bm25.scores(query)
        bm25_rank = [i for i in rank(bm25_scores) if bm25_scores[i] > 0]  # 일치 0건이면 순위에서 제외
        vec_rank = rank(doc_vecs @ embed(query))
        fused = rrf(bm25_rank, vec_rank)

        print(f"\n질문: {query}")
        print(f"  {'순위':<4}{'BM25':<8}{'Vector':<8}{'RRF':<8}")
        for i in range(3):
            b = f"doc{bm25_rank[i]}" if i < len(bm25_rank) else "-"
            print(f"  {i + 1:<5}{b:<8}doc{vec_rank[i]:<5}doc{fused[i][0]:<5}")
        if not bm25_rank:
            print("  (BM25: 일치하는 토큰 없음)")
        print(f"  → RRF 1위: {DOCS[fused[0][0]]}")


if __name__ == "__main__":
    main()
