"""장중 5분 주기 재판단: 병렬 뉴스 검색 + ReAct 루프.

- 검색: 8개 쿼리 × 3채널(뉴스/블로그/웹)을 asyncio.gather로 병렬 실행
- ReAct: LLM이 Thought → Action(search | decide) → Observation을 반복.
         추가 검색이 필요한지 LLM이 스스로 판단하고, 최대 단계를 넘으면 HOLD로 안전 종료.
실제 시스템의 Naver Search API와 LLM 호출은 대역 함수로 대체했다.
"""

import asyncio
import json
import time

CHANNELS = ["news", "blog", "web"]
MAX_STEPS = 3


def make_queries(name: str) -> list[str]:
    return [f"{name} {kw}" for kw in ["실적", "수주", "공시", "고객사", "증설", "HBM", "주가", "리포트"]]


async def search(channel: str, query: str) -> list[str]:
    await asyncio.sleep(0.05)  # 네트워크 지연 대역
    if channel == "news" and "수주" in query:
        return [f"[{channel}] {query}: 대형 고객사 패키징 수주 확대 보도"]
    if channel == "news" and "공시" in query:
        return [f"[{channel}] {query}: 단일판매·공급계약 체결 공시"]
    return []


async def parallel_search(queries: list[str]) -> list[str]:
    tasks = [search(ch, q) for q in queries for ch in CHANNELS]  # 8 × 3 = 24건
    results = await asyncio.gather(*tasks)
    return [doc for docs in results for doc in docs]


def fake_llm(step: int, scratchpad: list[str]) -> str:
    """ReAct 형식 응답 대역. 실제로는 로컬 LLM(KANANA 1.5 8B)이 생성."""
    if step == 0:
        return json.dumps({"thought": "보유 중인데 장중 급등. 원인 뉴스가 있는지 먼저 확인해야 한다.",
                           "action": "search", "input": "하나마이크론"})
    if step == 1 and not any("계약" in s for s in scratchpad):
        return json.dumps({"thought": "수주 보도는 있으나 공시로 확인되지 않았다. 공시만 추가 확인.",
                           "action": "search", "input": "하나마이크론 공시"})
    return json.dumps({"thought": "수주 보도와 공급계약 공시가 모두 확인됨. 급등 근거가 있다.",
                       "action": "decide", "input": {"decision": "BUY_MORE", "confidence": 0.68}})


async def rejudge(code: str, name: str) -> dict:
    scratchpad: list[str] = []
    for step in range(MAX_STEPS + 1):
        msg = json.loads(fake_llm(step, scratchpad))
        print(f"  Thought {step + 1}: {msg['thought']}")
        if msg["action"] == "decide":
            return {"code": code, **msg["input"]}
        if step == MAX_STEPS:
            break
        queries = make_queries(name) if step == 0 else [msg["input"]]
        t0 = time.perf_counter()
        docs = await parallel_search(queries)
        elapsed = time.perf_counter() - t0
        print(f"  Action  {step + 1}: search {len(queries)}쿼리 × {len(CHANNELS)}채널 "
              f"= {len(queries) * len(CHANNELS)}건 병렬 ({elapsed:.2f}s)")
        for d in docs:
            print(f"    Observation: {d}")
        scratchpad += docs
    return {"code": code, "decision": "HOLD", "confidence": 0.0, "note": "최대 단계 초과 → 안전 종료"}


async def main() -> None:
    print("[09:35 재판단] 067310 하나마이크론 (보유, 장중 +6.2%)")
    result = await rejudge("067310", "하나마이크론")
    print(f"\n결정: {result}")
    print(f"(순차 실행이었다면 검색에만 약 {24 * 0.05:.1f}s 이상)")


if __name__ == "__main__":
    asyncio.run(main())
