"""비정형 뉴스 → 클러스터 → 클러스터별 누적 비정상 수익률(CAR) → 예측 피처.

합성 데이터:
  - 유가 일간 수익률: 평소엔 노이즈, 사건 유형에 따라 사건 이후 며칠간 drift가 생김
  - 뉴스: 사건 유형별 어휘로 생성
"""

import re
from collections import Counter

import numpy as np

RNG = np.random.default_rng(7)
DAYS = 500
EVENT_TYPES = {
    "공급 차질": (["송유관", "공격", "생산", "중단", "공급", "차질", "중동"], +0.006),
    "수요 둔화": (["경기", "둔화", "수요", "감소", "중국", "제조업", "부진"], -0.005),
    "OPEC 증산": (["OPEC", "증산", "합의", "산유국", "회의", "생산량", "확대"], -0.004),
}


# ---------- 1. 합성 데이터 ----------
def make_data():
    returns = RNG.normal(0, 0.01, DAYS)
    news: list[tuple[int, str, str]] = []  # (day, text, true_type)
    for _ in range(45):
        day = int(RNG.integers(30, DAYS - 10))
        etype = RNG.choice(list(EVENT_TYPES))
        words, drift = EVENT_TYPES[etype]
        returns[day : day + 3] += drift  # 사건 이후 3일간 영향
        text = " ".join(RNG.choice(words, size=6)) + " 관련 보도"
        news.append((day, text, etype))
    return returns, sorted(news)


# ---------- 2. 임베딩 + 클러스터링 ----------
def bow_embed(texts: list[str]) -> tuple[np.ndarray, list[str]]:
    tokenized = [re.findall(r"\w+", t) for t in texts]
    vocab = sorted({w for toks in tokenized for w in toks})
    idx = {w: i for i, w in enumerate(vocab)}
    X = np.zeros((len(texts), len(vocab)))
    for r, toks in enumerate(tokenized):
        for w, c in Counter(toks).items():
            X[r, idx[w]] = c
    X /= np.linalg.norm(X, axis=1, keepdims=True)
    return X, vocab


def kmeans(X: np.ndarray, k: int, iters: int = 50) -> np.ndarray:
    # k-means++ 초기화
    centers = [X[RNG.integers(len(X))]]
    for _ in range(k - 1):
        d = np.min([((X - c) ** 2).sum(1) for c in centers], axis=0)
        centers.append(X[RNG.choice(len(X), p=d / d.sum())])
    centers = np.array(centers)
    for _ in range(iters):
        labels = np.argmin(((X[:, None] - centers[None]) ** 2).sum(-1), axis=1)
        centers = np.array([X[labels == j].mean(0) for j in range(k)])
    return labels


# ---------- 3. Event Study ----------
def car(returns: np.ndarray, day: int, est=(-30, -5), event=(0, 3)) -> float:
    """사건 윈도우의 누적 비정상 수익률 = Σ(실제 - 추정 구간 평균)."""
    normal = returns[day + est[0] : day + est[1]].mean()
    window = returns[day + event[0] : day + event[1]]
    return float((window - normal).sum())


def main() -> None:
    returns, news = make_data()
    X, vocab = bow_embed([t for _, t, _ in news])
    labels = kmeans(X, k=3)

    print("클러스터별 Event Study 결과")
    print(f"{'클러스터':<8}{'대표 단어':<28}{'사건 수':>6}{'평균 CAR':>10}  실제 유형")
    cluster_car = {}
    for j in range(3):
        members = [i for i in range(len(news)) if labels[i] == j]
        top_words = [vocab[w] for w in np.argsort(-X[members].sum(0))[:3]]
        cars = [car(returns, news[i][0]) for i in members]
        cluster_car[j] = float(np.mean(cars))
        true_type = Counter(news[i][2] for i in members).most_common(1)[0][0]
        print(f"C{j:<7}{', '.join(top_words):<28}{len(members):>6}{cluster_car[j]:>+10.4f}  {true_type}")

    # ---------- 4. 새 뉴스 → 피처 ----------
    new_text = "중동 송유관 공격 으로 생산 중단"
    x_new, _ = bow_embed([new_text] + [t for _, t, _ in news])
    centroid = np.array([x_new[1:][labels == j].mean(0) for j in range(3)])
    j = int(np.argmax(centroid @ x_new[0]))
    print(f"\n새 뉴스: '{new_text}'")
    print(f"→ 클러스터 C{j}, 이벤트 피처(event_car) = {cluster_car[j]:+.4f}  (양수 = 상승 압력)")


if __name__ == "__main__":
    main()
