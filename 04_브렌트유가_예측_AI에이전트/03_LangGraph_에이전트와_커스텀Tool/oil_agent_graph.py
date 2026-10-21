"""LangGraph로 만든 '여러 Tool을 순차 조합하는' 유가 분석 에이전트.

실제 프로젝트에서는 planner 노드가 LLM이었다.
여기서는 오프라인으로 실행되도록 planner를 규칙 기반 함수로 대체했고,
그래프 구조(State · 조건부 라우팅 · 루프 제한 · Tool 노드)는 실제와 같은 방식이다.

pip install langgraph
"""

from typing import Annotated, TypedDict
import operator

import numpy as np
from langgraph.graph import END, START, StateGraph

MAX_STEPS = 5
RNG = np.random.default_rng(3)
PRICES = 80 + np.cumsum(RNG.normal(0, 0.8, 60))  # 합성 브렌트 가격 60일


# ---------- 커스텀 Tool (MCP 서버가 아닌 직접 구현 함수) ----------
def web_search_tool(query: str) -> dict:
    return {"headline": "홍해 송유관 공격으로 공급 차질 우려", "day": 41}


def db_tool(query: str) -> dict:
    """RDB(메타데이터) + VDB(임베딩) 동시 조회 — 02 듀얼 스토리지 참고."""
    return {"cluster": "공급 차질", "past_car": 0.0234, "event_day": 41}


def price_api_tool(day: int, window: int = 5) -> dict:
    lo, hi = max(day - window, 0), min(day + window, len(PRICES))
    return {"days": list(range(lo, hi)), "prices": PRICES[lo:hi].round(2).tolist()}


def chart_tool(prices: list[float]) -> str:
    bars = "▁▂▃▄▅▆▇█"
    p = np.array(prices)
    scaled = ((p - p.min()) / (np.ptp(p) or 1) * (len(bars) - 1)).astype(int)
    return "".join(bars[i] for i in scaled)


# ---------- State ----------
class AgentState(TypedDict):
    question: str
    plan: list[str]                                  # 남은 Tool 호출 순서
    observations: Annotated[list[str], operator.add]  # 노드가 반환한 값이 누적됨 (reducer)
    context: dict
    steps: int
    answer: str


# ---------- 노드 ----------
def planner(state: AgentState) -> dict:
    """질문 유형에 따라 Tool 조합을 결정 (실제로는 LLM이 판단)."""
    q = state["question"]
    plan = []
    if "최근" in q or "뉴스" in q:
        plan.append("web_search")
    if "과거" in q or "영향" in q:
        plan.append("db")
    if "그래프" in q or "추이" in q:
        plan += ["price_api", "chart"]
    return {"plan": plan, "steps": 0}


def run_tool(state: AgentState) -> dict:
    tool, *rest = state["plan"]
    ctx = dict(state["context"])
    if tool == "web_search":
        ctx.update(web_search_tool(state["question"]))
        obs = f"web_search → '{ctx['headline']}' (day {ctx['day']})"
    elif tool == "db":
        ctx.update(db_tool(state["question"]))
        obs = f"db → 클러스터 '{ctx['cluster']}', 과거 평균 CAR {ctx['past_car']:+.2%}"
    elif tool == "price_api":
        # 앞 Tool의 결과(사건일)를 다음 Tool의 입력으로 사용 → 순차 조합
        day = ctx.get("event_day", ctx.get("day", len(PRICES) - 1))
        ctx.update(price_api_tool(day))
        obs = f"price_api(day={day}) → {len(ctx['prices'])}일치 가격"
    else:
        ctx["chart"] = chart_tool(ctx["prices"])
        obs = f"chart → {ctx['chart']}"
    return {"plan": rest, "context": ctx, "observations": [obs], "steps": state["steps"] + 1}


def answer(state: AgentState) -> dict:
    c = state["context"]
    parts = []
    if "headline" in c:
        parts.append(f"최근 뉴스: {c['headline']}")
    if "past_car" in c:
        parts.append(f"같은 유형의 과거 사건은 평균 {c['past_car']:+.2%} 움직였습니다")
    if "chart" in c:
        parts.append(f"사건일 전후 가격 {c['prices'][0]} → {c['prices'][-1]}  {c['chart']}")
    if state["steps"] >= MAX_STEPS and state["plan"]:
        parts.append("(최대 단계에 도달해 일부 분석을 생략했습니다)")
    return {"answer": "\n".join(parts) or "현재 도구로 답하기 어려운 질문입니다."}


# ---------- 라우팅 (순수 함수: State만 보고 다음 노드 결정) ----------
def route(state: AgentState) -> str:
    if not state["plan"] or state["steps"] >= MAX_STEPS:
        return "answer"
    return "run_tool"


def build_graph():
    g = StateGraph(AgentState)
    g.add_node("planner", planner)
    g.add_node("run_tool", run_tool)
    g.add_node("answer", answer)
    g.add_edge(START, "planner")
    g.add_conditional_edges("planner", route, {"run_tool": "run_tool", "answer": "answer"})
    g.add_conditional_edges("run_tool", route, {"run_tool": "run_tool", "answer": "answer"})
    g.add_edge("answer", END)
    return g.compile()


def main() -> None:
    app = build_graph()
    for q in ["최근 공급 차질 뉴스가 과거에 준 영향과 가격 그래프 보여줘", "오늘 날씨 어때?"]:
        result = app.invoke({"question": q, "plan": [], "observations": [], "context": {}, "steps": 0, "answer": ""})
        print(f"\n질문: {q}")
        for i, obs in enumerate(result["observations"], 1):
            print(f"  step {i}. {obs}")
        print("답변:\n  " + result["answer"].replace("\n", "\n  "))


if __name__ == "__main__":
    main()
