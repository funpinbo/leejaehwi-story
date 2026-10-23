# 이재휘 개발 일지

> **물리학 → 광학 엔지니어 → AI Agent Engineer**
> 현장의 반복 업무를 데이터로 정의하고, LLM 에이전트와 데이터 파이프라인으로 자동화합니다.

이 저장소는 제가 직접 겪은 문제와, 그 문제를 풀면서 **배운 것**을 프로젝트 단위로 정리한 개발 일지입니다.
모든 경험 문서는 같은 틀로 작성했습니다.

```
상황(Context) → 문제(Problem) → 시도와 실패(Try) → 해결(Solution) → 결과(Result) → 배운 점(Lesson)
```

각 경험 폴더에는 **경험 문서(`README.md`)** 와 핵심 아이디어를 재현한 **예제 코드**가 함께 있습니다.
예제 코드는 회사 코드·실데이터가 아니라, 제가 내린 설계 판단을 최소 단위로 다시 구현한 것입니다.

---

## 한눈에 보기

| # | 프로젝트 | 기간 · 형태 | 핵심 키워드 | 대표 성과 |
|---|---|---|---|---|
| 04 | [브렌트 유가 예측 AI 에이전트](./04_브렌트유가_예측_AI에이전트) | SKALA · 6인 2개월 | LangGraph, Event Study, 듀얼 스토리지 | 방향성 정확도 **약 10%p 개선** |
| 05 | [AI 하이브리드 퀀트 트레이딩](./05_AI_하이브리드_퀀트트레이딩) | 2026.06~ · 1인 개발 | 3-Layer, 로컬 LLM, ReAct, asyncio | WebSocket 장애 **-90%**, 파싱 성공률 **20% → 90%+** |
| 06 | [MID · 문서 형식 유지 작성 AGENT](./06_MID_문서형식유지_작성AGENT) | 2026.07~ · 단독 | Content/Layout 분리, docx 템플릿 | 실제 PAD·계약서 양식 보존 |
| 07 | [MID · ECSS 규격 그래프DB 파이프라인](./07_MID_ECSS규격_그래프DB_파이프라인) | 2026.07~ · 단독 | Atomic Block, 스키마 진화, Graph RAG | 388 Block 추출, 641 canonical record |
| 08 | [MID · 사내 프롬프트 엔지니어링 교육](./08_MID_사내_프롬프트엔지니어링_교육) | 2026 · 단독 기획·발표 | CoT, ReAct, MCP, Skill | 전 직원 대상 세미나 진행 |
| 09 | [MID · PAD 에이전트 플랫폼](./09_MID_PAD_에이전트_플랫폼) | 2026.09~ · 1인 개발 (AI 코딩 에이전트 협업) | 결정적 단계 파이프라인, Outbox·Fencing, Artifact Resolver, GitOps | 단일 에이전트 → 다중 서비스 운영 플랫폼으로 확장 |

---

## 🧭 프로젝트가 이어지는 흐름

각 프로젝트는 따로 떨어진 경험이 아니라, 앞 프로젝트에서 얻은 질문이 다음 프로젝트의 출발점이 되었습니다.

```mermaid
flowchart LR
    E[04 브렌트 유가 에이전트<br/>정형+비정형 결합]
    E --> F[05 퀀트 트레이딩<br/>실시간 운영 시스템으로 확장]
    E --> G[06 문서 AGENT<br/>생성과 형식의 분리]
    G --> H[07 ECSS 그래프DB<br/>문서를 구조로]
    G --> I[08 사내 교육<br/>조직에 AI를 전파]
    G --> J[09 PAD 에이전트 플랫폼<br/>다중 서비스 운영]
    H --> J
```

---

## 경험에서 얻은 엔지니어링 원칙

| 원칙 | 처음 배운 곳 | 다시 적용한 곳 |
|---|---|---|
| **같은 방법을 반복하기 전에 원인을 다시 정의한다** | 05 LoRA 실패 → RAG 전환 | 06 문서 재생성 → 템플릿 |
| **결정적인 부분과 비결정적인 부분을 분리한다** | 06 Content / Layout 분리 | 07 원문(atomic) / 정규화(normalized) 분리 |
| **LLM 출력을 그대로 믿지 않는다** | 04 Hallucination 회고 | 07 `confidence`·`requires_review` 스키마 |
| **근거를 추적할 수 있게 저장한다** | 04 FAISS + PostgreSQL 듀얼 스토리지 | 07 `source_region_id` 역추적 |
| **외부 시스템의 제약을 먼저 확인한다** | 05 KIS WebSocket 단일 연결 제약 | 05 502 토큰 만료 대응 |
| **LLM은 판정하지 않고, 텍스트를 다시 쓰지 않는다** | 06 Content / Layout 분리 | 09 결정적 단계 파이프라인, 경계만 판단하는 청킹 |
| **재시도는 상태를 바꿀 때만, 실패한 것만** | 05 502 토큰 강제 갱신 | 09 실패 step만 재시도, epoch fencing |
| **사고는 규칙과 검사기로 남긴다** | 09 타임존 · 라벨 누락 사고 | 09 CronJob 표준 린터 |
| **큰 전환은 관찰부터, 안전망은 따로 걷어낸다** | 09 Control Plane shadow 모드 | 09 strict 전환 운영 사고 → 회귀 테스트 |
| **"없음"을 가짜 값으로 표현하지 않는다** | 09 가짜 유사도 1.0 | 09 턴 시작 state 리셋 |

---

## 🛠️ 기술 스택

| 분야 | 사용 기술 |
|---|---|
| Language | Python 3.10+ (asyncio, mypy strict, Pydantic v2) |
| LLM / Agent | LangGraph, ReAct, Ollama(KANANA 1.5 8B), Gemini 2.5 Flash, qwen 계열, GPT-OSS-120B, LoRA |
| Retrieval | FAISS, BM25, Elasticsearch(Nori), RRF, Embedding 클러스터링 |
| Data / DB | PostgreSQL(스키마 격리), TimescaleDB, pgvector, Apache AGE(Graph), Redis, JSON Schema |
| ML / DL | CatBoost, PatchTST, BSTS(orbit-ml), LoRA |
| Infra / API | FastAPI, APScheduler, WebSocket, KIS / Naver / FRED API, Kubernetes, Jenkins, ArgoCD(GitOps), Sealed Secrets |
| Model Serving | vLLM 기반 로컬 모델 서빙 (오픈 웨이트 LLM · VLM · OCR · 임베딩 모델) |
| Observability | Loki, Prometheus, Grafana Alloy, Arize Phoenix(OTel) |
| Docs | python-docx, Jinja 스타일 템플릿, OnlyOffice |

---

## 폴더 구조

```
leejaehwi-story/
├── README.md                          ← 지금 보고 있는 인덱스
└── {번호}_{프로젝트}/
    ├── README.md                      ← 프로젝트 인덱스 (문서 목록 · 경험 목록)
    ├── docs/                          ← 프로젝트 문서
    │   ├── 00-overview.md             ← 배경 · 문제 · 성과 · 회고
    │   └── 01-architecture.md         ← 아키텍처 (09는 시스템 · 데이터 · 오케스트레이션 등 9편)
    └── {번호}_{경험}/
        ├── README.md                  ← 경험 문서 (문제 → 해결 → 배운 점)
        └── *.py                       ← 핵심 아이디어 재현 예제 코드
```

예제 코드는 대부분 표준 라이브러리 또는 `numpy`, `pydantic`, `python-docx` 정도만으로 실행됩니다.
필요한 패키지는 [`requirements.txt`](./requirements.txt)에 있습니다.

```bash
pip install -r requirements.txt
python 05_AI_하이브리드_퀀트트레이딩/02_WebSocket_단일공유연결/shared_websocket.py
```
