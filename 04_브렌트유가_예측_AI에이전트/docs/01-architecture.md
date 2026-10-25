# 아키텍처

## 1. 아키텍처

```mermaid
flowchart LR
    N[뉴스·리포트] --> E[임베딩] --> C[클러스터링]
    P[유가 시계열] --> ES[Event Study<br/>클러스터별 영향 분석]
    C --> ES
    ES --> F[이벤트 피처] --> M[예측 모델]
    E --> V[(FAISS<br/>원문 임베딩)]
    ES --> R[(PostgreSQL<br/>상관관계·메타데이터)]
    U[사용자 질문] --> A{LangGraph Agent}
    A --> T1[Web Search Tool]
    A --> T2[정형 데이터 API Tool]
    A --> T3[RDB+VDB 조회 Tool]
    A --> T4[시각화 Tool]
    T3 --> V & R
```

---

- 이전 문서: [프로젝트 개요](00-overview.md)
