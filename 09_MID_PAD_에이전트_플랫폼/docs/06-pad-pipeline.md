# PAD 문서 생성 파이프라인

## 1. 목적과 설계 원칙

PAD(Part Approval Document) 파이프라인은 전자부품 승인 문서에 필요한 값을 수집하고, 각 값의 근거를 보존하며, 고객·프로젝트별 템플릿으로 렌더링하는 흐름이다. 단순히 LLM이 문서를 한 번에 작성하는 구조가 아니다. 데이터시트, 표준 문서, 규칙 테이블, 사용자 입력을 단계별로 결합해 **검증 가능한 슬롯 JSON**을 만든 뒤, 마지막에 물리 문서로 변환한다.

핵심 원칙은 다음과 같다.

- LLM은 분류 후보 제안, 자연어 요약, 원문에서의 제한적 추출에 사용한다.
- 코드·규칙 테이블·closed set으로 확정할 수 있는 값은 결정론적으로 판정한다.
- 모든 필드는 값만 저장하지 않고 출처, 추출 방식, 검증 상태를 함께 남긴다.
- 근거가 없으면 값을 추측하지 않는다. 미확정 상태를 그대로 노출해 사람 검토로 넘긴다.
- 의미 슬롯과 물리 템플릿을 분리한다. 같은 슬롯 JSON을 여러 고객 템플릿에 투영할 수 있어야 한다.
- 한 항목의 실패가 전체 배치나 다른 항목을 오염시키지 않도록 항목 단위로 상태를 격리한다.
- STEP 12의 최종 승인·서명은 자동화 범위 밖에 두고 사람이 수행한다.

## 2. 전체 구성

| 구성 요소 | PAD에서의 책임 | 주요 코드/계약 |
|---|---|---|
| `chatbot` | STEP 그래프 실행, 상태 관리, 값·근거 수집 | pad_builder.py, PAD nodes |
| `specrules` | 부품 분류, family/group 코드, 규격 적용성, screening 기본 규칙 | pad_slots.md |
| `datanalyze` | 표준 코퍼스와 지식 그래프 검색, 조항·교차참조 근거 제공 | 서비스 내부 검색 API |
| `webcrawl` | 데이터시트와 공신력 있는 외부 문서 탐색·가져오기 | 서비스 내부 search/fetch API |
| `reportlayout` | 템플릿 계약 조회, 슬롯 검증, PDF/DOCX 렌더링 | reportlayout |
| `orchestration-control` | 업무 intent를 실행 계획으로 해석하고 승인·감사를 기록 | [오케스트레이션 설명](02-orchestration.md) |
| `orchestration-worker` | 허용된 Action 실행, 다운스트림 자격증명 격리, SSRF 방어 | [오케스트레이션 설명](02-orchestration.md) |
| `artifact-resolver` | 원문·중간 JSON·렌더 결과의 저장, ACL, lineage, retention | [오케스트레이션 설명](02-orchestration.md) |

서비스는 서로의 데이터베이스를 직접 읽지 않는다. 호출자는 구체적인 URL 대신 업무 intent와 입력만 전달하고, 실제 backend 선택·권한 확인·실행 추적은 Control Plane이 담당한다.

## 3. 요청부터 문서까지

```text
사용자/배치 요청
  │  프로젝트·부품·템플릿 단서
  ▼
layout_field ── 템플릿의 필드 계약 조회
  ▼
pad_defaults ── 안전한 기본값 초기화
  ▼
STEP 0 ── 입력 정규화와 프로젝트/부품 식별
  ▼
STEP 1 ── 부품 유형 분류(EEE / MATERIAL / MECH_RF)
  ▼
STEP 2 ── 데이터시트 검색·특성 요약
  ▼
evidence_tree ── 검색 근거를 필드별 provenance로 정리
  │
  │ 같은 thread_id의 체크포인트
  ▼
STEP 3 ── family/group 및 closed-set 코드 확정
  ▼
STEP 4 ── generic/detail/amendment 규격 계보 구성
  ▼
STEP 6 ── 품질 등급 파생
  ▼
STEP 7 ── screening/LAT/DPA 요구사항 결정
  ▼
STEP 11 ── 문서 번호·프로젝트·작성 메타데이터 채움
  ▼
layout_build ── 슬롯 검증 → 템플릿 매핑 → 렌더
  ▼
검토 가능한 PAD + 슬롯 JSON + 근거/lineage
```

코드는 파이프라인을 두 그래프로 나눈다.

- **검색 그래프**: `layout_field → pad_defaults → step0 → step1 → step2 → evidence_tree`
- **작성 그래프**: `step3 → step4 → step6 → step7 → step11 → layout_build`

두 그래프는 같은 `thread_id`와 체크포인터를 사용한다. 따라서 검색이 끝난 뒤 사람이 근거를 검토하거나 누락 입력을 보완하고, 그 상태에서 작성·렌더링을 재개할 수 있다. 그래프 정의는 pad_builder.py에 있다.

## 4. STEP별 책임과 현재 구현 상태

| STEP | 책임 | 대표 입력 | 대표 산출 | 상태 |
|---:|---|---|---|---|
| 준비 | 템플릿 필드 계약 조회, 기본 상태 생성 | template/project hint | field contract, defaults | 구현 |
| 0 | 프로젝트·BOM 항목·품번·제조사·국가 정규화 | 사용자 입력, BOM | 기본 식별 슬롯 | 구현 |
| 1 | 부품 유형 분류 | 품번, 설명, 데이터시트 단서 | `part_type` | 구현 |
| 2 | 데이터시트 탐색과 상용명·기술특성·패키지 요약 | 품번, 제조사 | 요약 슬롯 + evidence | 구현 |
| 3 | family/group 및 F/G code 결정 | STEP 1·2 결과, 규칙 테이블 | `family`, `fcode`, `group`, `gcode` | 구현 |
| 4 | 적용 규격과 개정 계보 구성 | 분류 코드, 규격 edge | generic/detail/amendment | 구현 |
| 5 | 승인 목록(QPL/QML 등) 등재 여부 | 공식 승인 목록 | approval status + reference | 소스·정책 확정 필요 |
| 6 | 규격·분류에 따른 품질 등급 파생 | STEP 3·4 결과 | `quality_level` | 구현 |
| 7 | screening, LAT, buy-off, DPA 등 결정 | 부품 유형, 규격, 기본 규칙 | 시험 요구 슬롯 + 근거 | 구현 |
| 8 | 평가 프로그램 필요 여부 | 프로그램 정책, 시험 공백 | evaluation programme 슬롯 | 소스·판정 규칙 필요 |
| 9 | 방사선 내성 계획과 SEE/TID 항목 | 프로젝트 환경·시험 근거 | RHA/SEE/TID 슬롯 | 소스·판정 규칙 필요 |
| 10 | pure tin free 여부 | 재질·제조 공정 근거 | `pure_tin_free` | 소스·판정 규칙 필요 |
| 11 | 문서 관리 메타데이터 | 프로젝트/사용자 정보 | 문서번호, issue, 날짜, 담당 | 구현 |
| 12 | 최종 승인·서명 | 완성 문서, 검토 결과 | 사람 서명 | 자동화 제외 |

“미구현”은 빈칸을 임의 값으로 채운다는 뜻이 아니다. 현재 코드는 근거가 확정된 단계만 실행하며, STEP 5와 8–10은 신뢰할 원천과 판정 규칙이 마련될 때까지 명시적인 미확정 값으로 남겨야 한다.

## 5. 상태와 데이터 계약

PAD 상태는 일반 문서 생성 상태인 `DocState`를 확장한다. 출력 필드 값과 그래프 제어값을 구분한다.

- `field_values`: 최종 슬롯 후보. 렌더링과 검증의 대상이다.
- evidence/provenance: 슬롯을 뒷받침하는 원문, 검색 결과, 규칙 조회와 추출 메타데이터다.
- `part_type`: STEP 6·7·9의 분기를 위한 제어값이다. 문서에 직접 인쇄하지 않는다.
- layout contract: 선택된 템플릿이 요구하는 필드, 필수 여부, 타입·형식 제약이다.
- render/artifact metadata: 생성된 결과물과 입력 근거 사이의 lineage를 연결한다.

최소한 각 슬롯 후보는 다음 질문에 답할 수 있어야 한다.

1. 값은 무엇인가?
2. 어떤 STEP과 어떤 방식(`USER_INPUT`, `RULE`, `DERIVED`, `EXTRACTED`)으로 만들어졌는가?
3. 어떤 문서·조항·규칙 행이 이 값을 지지하는가?
4. 검증됐는가, 충돌하는 근거가 있는가, 사람 확인이 필요한가?
5. 어느 템플릿에서 인쇄되거나 생략되는가?

## 6. 공통 슬롯과 템플릿 변주

`pad-common@0.1`은 템플릿에 독립적인 의미 슬롯을 정의한다. 렌더 단계에서만 해당 슬롯을 템플릿의 실제 필드에 매핑한다.

예를 들어 두 템플릿이 같은 정보를 다르게 표현할 수 있다.

- 한 템플릿은 제조사와 국가를 별도 필드로, 다른 템플릿은 하나의 결합 필드로 표시한다.
- 한 템플릿은 SEE 항목을 종류별로 세분화하지만, 다른 템플릿은 하나의 요약 행에 합친다.
- remark가 섹션별로 나뉘거나 하나의 공용 영역으로 통합될 수 있다.
- 특정 슬롯이 어떤 템플릿에는 없을 수 있다. 이때 값 자체를 버리지 않고 슬롯 JSON에는 보존하며, 렌더 로그에 생략 사실을 남긴다.

이 분리 덕분에 규칙·근거 수집 로직을 고객 서식마다 복제하지 않고, 새 템플릿을 필드 매핑과 렌더 계약의 추가로 수용할 수 있다.

## 7. 근거 수집과 판정 경계

### 검색 우선순위

일반적인 순서는 내부 규칙·표준 코퍼스 → 공식/등록 문서 → 제한된 외부 검색이다. 표준 문서가 다른 표준이나 시험 방법을 참조하면 evidence tree가 교차참조를 따라가되, 깊이와 반복 횟수에 상한을 둔다.

### LLM이 해도 되는 일

- 데이터시트에서 후보 필드 추출
- 부품 설명의 정규화와 요약
- 검색어 후보 생성
- 정해진 후보 집합 안에서의 분류 보조

### 코드와 규칙이 결정해야 하는 일

- family/group 코드가 실제 catalog에 존재하는지
- 규격이 해당 부품군에 적용되는지
- 품질 등급과 screening 기본값
- 필수 슬롯, 타입, 형식, 허용값 검증
- 권한, 승인, 저장 위치와 실행 정책

모델 출력은 항상 schema·regex·catalog lookup으로 재검증한다. 원문에 없는 숫자나 식별자는 확정값으로 승격하지 않는다.

## 8. 오류 처리와 재실행

- 템플릿 계약을 읽을 수 없으면 검색 그래프는 즉시 종료하고 렌더를 시도하지 않는다.
- 슬롯 하나의 검색 실패는 다른 슬롯의 근거와 값을 지우지 않는다.
- 네트워크 재시도와 업무 재실행을 구분한다. 같은 요청은 idempotency key로 중복 실행을 막는다.
- Worker lease와 epoch fencing으로 오래된 실행의 늦은 결과가 새 실행을 덮어쓰지 못하게 한다.
- 검색과 작성 사이의 체크포인트를 사용해, 외부 검색을 반복하지 않고 수정된 입력으로 작성 단계만 재실행할 수 있다.
- 렌더 전에 필수값·타입·템플릿 호환성을 검사하고, 손실 가능한 매핑은 조용히 무시하지 않고 로그로 남긴다.

## 9. 보안과 자격증명

PAD 그래프는 다운스트림 서비스의 비밀을 직접 소유하지 않는다.

1. `chatbot`은 자신의 workload identity로 Control에 intent를 요청한다.
2. Control은 요청자의 intent 권한과 승인 정책을 검사하고 실행 계획을 만든다.
3. Worker는 계획을 다시 검증한 뒤, 허용된 endpoint에만 다운스트림 전용 자격증명을 붙여 호출한다.
4. 원문과 렌더 결과는 Artifact Resolver가 ACL과 lineage를 적용해 저장한다.
5. 호출자에게는 storage credential 대신 권한 검사가 적용되는 artifact reference만 반환한다.

읽기·쓰기·승인 권한과 사용자 위임 identity를 분리하고, 로그·오류·다운스트림 응답에서 토큰과 비밀을 redaction해야 한다. 자세한 실행 모델은 [02-orchestration.md](02-orchestration.md)를 참고한다.

## 10. 개발할 때 지켜야 할 규칙

- 새 STEP을 추가하기 전에 입력 원천, 신뢰 순위, 미확정 표현, 회귀 테스트를 먼저 정의한다.
- 새 슬롯은 공통 슬롯 스키마에 의미와 STEP을 추가하고, 템플릿별 매핑은 별도 계약으로 관리한다.
- 서비스 간 DB 직접 조회를 추가하지 않는다. 필요한 기능은 intent/Action 계약으로 노출한다.
- 샘플이나 테스트 fixture를 운영 fallback 값으로 사용하지 않는다.
- 공유 state나 evidence 타입을 바꾸면 저장·조회·관리 API를 포함해 저장소 전체 소비자를 검색한다.
- 외부 문서 fetch는 allow-list/redirect/SSRF 검사를 우회하지 않는다.
- 생성 문서만 테스트하지 말고 슬롯 JSON, 근거 링크, 미확정 상태, 템플릿별 손실 로그도 함께 검증한다.

## 11. 코드 탐색 순서

PAD를 처음 보는 개발자는 다음 순서로 읽는 것이 가장 빠르다.

1. `chatbot/back/app/graph/pad_builder.py` — 검색/작성 그래프와 실행 순서
2. `chatbot/back/app/graph/pad_state.py` — PAD 전용 제어 상태
3. `chatbot/back/app/graph/nodes/pad/` — STEP별 구현
4. `specrules/schema/pad_slots.md` — 공통 슬롯과 템플릿 차이
5. `reportlayout/` — 템플릿 계약과 렌더링
6. [`docs/02-orchestration.md`](02-orchestration.md) — 서비스 호출, 자격증명, 실행 복구
7. [`docs/03-agent.md`](03-agent.md) — evidence loop와 closed-set 판정 원칙
