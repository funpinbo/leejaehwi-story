# 프로젝트 개요 — ECSS 우주 규격 문서 그래프DB 데이터 파이프라인

> ECSS / ESCC / MIL 규격 문서는 조항끼리, 문서끼리 **참조가 극도로 많습니다.** 청크로 잘라 Vector Search만 하는 일반 RAG로는 참조가 끊기는 순간 의미가 무너집니다.
> 그래서 규격 문서를 **의미의 최소 단위(Atomic Block)** 로 쪼개고, Block 사이의 참조를 **그래프**로 연결하는 데이터 파이프라인을 설계·구현하고 있습니다.

| 항목 | 내용 |
|---|---|
| 기간 · 형태 | 2026.07 ~ 진행 중 · **단독 진행** |
| 대상 | ECSS / ESCC / MIL 규격 문서, ESCC Specification List |
| 기술 | Python, PDF Parsing, JSON Schema(버전 관리), PostgreSQL + Apache AGE(그래프), Vector DB / Embedding, BM25 |

## 1. 문제

| 일반 RAG | 규격 문서에서 생기는 일 |
|---|---|
| 문서를 고정 길이 청크로 자름 | "다음 조건을 만족해야 한다:"와 그 아래 항목이 다른 청크로 분리 → **의미 붕괴** |
| 유사도로 청크 검색 | "이 조항이 참조하는 다른 문서의 조항"을 따라갈 수 없음 |
| Revision 개념 없음 | PAD 같은 승인 문서에 필수인 **정확한 Revision**을 보장 못 함 |

## 2. 성과

- ECSS-P-00 문서에서 **388개 Block** 실제 추출
- 스키마 **v3 → v4** 개선: 31개 그룹, `GOVERNS` 관계, 리드인 주입, `derived_fields` 분리, 스키마 거버넌스 메타 선언
- ESCC Specification List **645건 → 641건 canonical record**, `schema_version 1.1`로 변환 완료
- Graph DB 노드 8종 · 엣지 7종 설계

## 3. 현재 상태

- 완료: Block 추출 파이프라인과 스키마 구현 · 반복 개선 중 (v4)
- 진행 중: Graph DB 실제 적재, Revision Verification 자동화, 전체 RAG 파이프라인 통합은 설계 · 진행 중

## 4. 회고

- 문서 간 참조와 Revision이 핵심인 도메인에서는 **Vector Search + Metadata + Graph + Revision + Source Trace**를 함께 결합해야 합니다.
- 스키마를 처음부터 완성하려 하지 않고 **실제 데이터로 돌려보며 v3 → v4로 진화**시켰습니다.
- [06. 문서 AGENT](../../06_문서형식유지_작성AGENT)의 "Content / Layout 분리" 통찰이 "Atomic Block / Graph" 구조로 확장된 프로젝트입니다.

## 5. 이후

이 파이프라인은 [09. PAD 에이전트 플랫폼](../../09_PAD_에이전트_플랫폼)에서 **규격 PDF → OCR → 지식그래프 → Block 구조화**와 **승인된 규격 관계만 판정에 쓰는 규칙 조회**로 발전했습니다.

---

- 다음 문서: [아키텍처](01-architecture.md)
- 경험 정리: [프로젝트 README](../README.md)
