# 04. 브렌트 유가 예측 AI 에이전트

> 뉴스·리포트 같은 **비정형 이벤트**가 유가라는 **정형 데이터**에 미치는 영향을 피처로 만들고,
> 여러 Tool을 스스로 조합해 조회·분석·시각화하는 **LangGraph 에이전트**를 만든 6인 팀 프로젝트입니다.

## 문서

| 문서 | 내용 |
|---|---|
| [00. 프로젝트 개요](./docs/00-overview.md) | 배경 · 문제 · 성과 · 회고 |
| [01. 아키텍처](./docs/01-architecture.md) | 구조와 흐름 |

## 경험 정리

| # | 경험 | 한 줄 요약 | 예제 코드 |
|---|---|---|---|
| 01 | [Event Study — 비정형 데이터 피처화](./01_EventStudy_비정형데이터_피처화) | 뉴스를 클러스터로 묶고, 클러스터별로 유가가 어떻게 움직였는지를 피처로 | `event_study.py` |
| 02 | [FAISS + PostgreSQL 듀얼 스토리지](./02_FAISS_PostgreSQL_듀얼스토리지) | 의미 검색은 Vector DB, 상관관계·근거 추적은 RDB | `dual_storage.py` |
| 03 | [LangGraph 에이전트와 커스텀 Tool](./03_LangGraph_에이전트와_커스텀Tool) | 질문 유형에 따라 Tool을 골라 순차 조합하는 그래프 | `oil_agent_graph.py` |
| 04 | [Hallucination 회고](./04_Hallucination_회고) | 해결하지 못한 문제를 회고로 남기고, 다음 설계 원칙으로 전환 | `numeric_grounding.py` |
