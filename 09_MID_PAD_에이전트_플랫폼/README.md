# 09. MID · PAD 에이전트 플랫폼

> 부품 승인 문서(PAD, Parts Approval Document)를 자동으로 작성·검토하는 **멀티서비스 AI 협업 플랫폼**입니다.
> 문서 템플릿 실험([06](../06_MID_문서형식유지_작성AGENT))과 규격 구조화 실험([07](../07_MID_ECSS규격_그래프DB_파이프라인))에서 출발해 운영 플랫폼으로 확장했습니다.
> 회사 내 SW 개발 담당이 1인이라 설계 · 판단 · 검증을 맡았고, 구현은 AI 코딩 에이전트와 협업했습니다.

| 항목 | 내용 |
|---|---|
| 기간 | 2026.09 ~ 진행 중 |
| 형태 | 사내 프로젝트 · 1인 개발 (AI 코딩 에이전트 협업) |
| 주요 기술 | Python, FastAPI, LangGraph, PostgreSQL(pgvector · Apache AGE), vLLM 기반 로컬 모델 서빙, Vue 3, Kubernetes · GitOps(Jenkins · ArgoCD) |

> 설계 문서는 직접 작성한 아키텍처 문서를 옮긴 것이고, 소스 코드는 싣지 않았습니다. 경험 정리의 예제 코드는 가상 데이터로 직접 재현한 것입니다.

## 📖 문서

처음 보는 경우 아래 순서로 읽는 것을 권장합니다.

| # | 문서 | 내용 |
|---|---|---|
| 1 | [전체 프로젝트 개요](./docs/00-system-overview.md) | 시스템 경계, 서비스별 책임, 사용자 여정, 설계 원칙 |
| 2 | [시스템 아키텍처](./docs/01-architecture.md) | 계층별 구성, 런타임 흐름, 이벤트, 보안, 배포, 관측성 |
| 3 | [데이터 아키텍처](./docs/07-data-architecture.md) | 저장소, 데이터 소유권, source of truth, KG · RAG · 슬롯 · lineage, ACL |
| 4 | [파이프라인과 스케줄링](./docs/08-pipelines-and-scheduling.md) | 문서 수집 · 임베딩, OCR/KG, PAD/렌더, CronJob과 상주 loop |
| 5 | [오케스트레이션](./docs/02-orchestration.md) | Intent Catalog, DAG, fan-in, idempotency, lease/fencing, artifact backend |
| 6 | [챗봇 · 문서 에이전트](./docs/03-agent.md) | research loop, closed-set 판정, 근거 점수, state 관리 |
| 7 | [PAD 파이프라인](./docs/06-pad-pipeline.md) | STEP 0–12, 슬롯 · 근거 계약, 템플릿 변주, 구현 상태 |
| 8 | [AI 협업 개발 프로세스](./docs/04-ai-assisted-workflow.md) | task / memory 계층과 실행 순환 |
| 9 | [개발 작업 사례](./docs/05-example-task.md) | Control Plane 전환과 렌더링 버그 수정 사례 |

## 📚 경험 정리

| # | 경험 | 한 줄 요약 | 예제 코드 |
|---|---|---|---|
| 01 | [LLM은 판정하지 않는다 — 결정적 단계](./01_LLM은_판정하지_않는다_결정적_STEP) | LLM은 후보만, 확정은 테이블. 모든 칸에 근거와 상태 | `deterministic_steps.py` |
| 02 | [LLM은 경계만 판단 — 청킹](./02_LLM은_경계만_판단_청킹) | 텍스트를 다시 쓰지 않고 자를 위치만 고르게 해서 인용을 보존 | `boundary_chunking.py` |
| 03 | [근거 적용성 검증 루프](./03_근거_적용성_검증_루프) | 재검색 루프 안에서 매번 적용성을 다시 따지고, 부적합 근거는 실제로 제거 | `evidence_loop.py` |
| 04 | [멱등 배치와 상태 분리](./04_멱등_배치와_상태_분리) | 원장 상태와 RAG 상태를 분리, 복원 시 좌초 사고에서 배운 것 | `nas_scan_state.py` |
| 05 | [CronJob 사고를 검사기로](./05_CronJob_사고를_검사기로) | 타임존 · 라벨 누락 사고를 규칙으로 바꿔 린터로 만듦 | `cronjob_lint.py` |
| 06 | [Outbox와 Fencing — 실행 제어](./06_Outbox와_Fencing_실행제어) | 상태 변경과 이벤트를 한 트랜잭션에, 늦게 온 결과는 epoch로 차단 | `outbox_fencing.py` |
| 07 | [Artifact Resolver 수명주기](./07_Artifact_Resolver_수명주기) | 검증 · 확정 전에는 보이지 않고, 권한 없으면 존재도 숨김 | `artifact_lifecycle.py` |
| 08 | [Fail-Closed 호출 경계](./08_Fail-Closed_호출_경계) | 경로 정규화 후 allowlist, 계약 digest 불일치면 실행 거부 | `call_boundary.py` |
| 10 | [Control Plane 단계적 전환과 운영 사고](./10_Control_Plane_단계적_전환과_운영사고) | shadow → 안전망 → strict → intent, 안전망 제거 날 드러난 숨은 라우트 | `staged_migration.py` |
| 11 | [가짜 유사도 점수 버그](./11_가짜_유사도_점수_버그) | "점수 없음"을 1.0으로 찍어 진짜 근거가 밀려난 문제 | `evidence_cap.py` |
| 12 | [턴 사이 State 누수](./12_턴_사이_State_누수) | 체크포인터가 지난 턴 값을 이어받는 문제 → 턴 시작 리셋 | `turn_state_leak.py` |
| 13 | [AI 협업 개발 프로세스](./13_AI_협업_개발_프로세스) | 기억 없는 코딩 에이전트를 위한 plan / task / memory 계층과 hook | `memory_cycle.py` |
