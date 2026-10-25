# 아키텍처

## 1. 파이프라인

```
일반 RAG :  PDF → Chunk → Embedding → VectorDB → LLM

이 프로젝트:
PDF → Layout/Region → Atomic Block → Metadata → Embedding → Vector Search
                                                          ↘
                                         Graph Relation → Source Trace → LLM
```

```mermaid
flowchart TB
    D[Document] --> P[Page<br/>문단 단위]
    P --> G[Group<br/>LIST · TABLE · FIGURE · CONDITION_SCOPE]
    G --> B[Block<br/>의미의 최소 단위]
    B -- REFERENCES --> B2[다른 문서의 Block]
    B -- GOVERNS --> B3[같은 그룹의 하위 Block]
```

---

- 이전 문서: [프로젝트 개요](00-overview.md)
