# 실제 사례: 실제로 돌았던 TASK-1과 TASK-2

[04-ai-assisted-workflow.md](04-ai-assisted-workflow.md)는 문서 템플릿을 추상적으로 설명한다. 이 문서는 실제 프로젝트 역사 두 가지를 가져와서 그 형식으로 다시 쓴다

---

## TASK-1: 서비스 간 호출을 선언형 Control Plane으로 이전

- 상태: 완료(남은 일부 라우트에 대해서는 안전망을 의도적으로 아직 유지)
- 관련 서비스: chatbot, orchestration-control, orchestration-worker, artifact-resolver, webcrawl, specrules, datanalyze, reportlayout
- 완료 기준: `chatbot`에서 나가는 카탈로그에 등록된 모든 호출이 (구체적 service/action이 아니라) 업무 intent를 선언함으로써 `orchestration-control`을 거쳐 도달하고, 남은 일부 라우트의 direct-call 안전망에 대한 제거 계획이 있다.
- 서비스별 분담:
  - **chatbot**: direct HTTP client를 Control을 호출하는 adapter로 교체; 호출자 계약을 `{service, action}`에서 `{intent, inputs}`로 이전.
  - **orchestration-control**: Intent Catalog, 승인 제어, 영속 실행 추적, 감사 API 구축.
  - **orchestration-worker**: SSRF/redirect 보호가 적용된 엔드포인트 allow-list에 대해, 격리된 다운스트림 자격증명으로 승인된 Action을 실행.
  - **artifact-resolver**: 바이너리 결과(렌더링된 문서, 가져온 파일)를 위한 콘텐츠 주소 기반 아티팩트 저장소 — 호출자가 다운스트림 스토리지 자격증명을 들고 다닐 필요가 없게.
  - **webcrawl / specrules / datanalyze / reportlayout**: 기존 엔드포인트를 카탈로그에 올릴 수 있는 Action으로 노출; 내부 재설계는 필요 없음.
- 진행 로그(실제 주요 단계별 한 줄 — 상세 log 항목은 §3 참고):
  1. Shadow 모드: Control이 모든 호출의 복사본을 받아 실제 응답과 비교 — 운영 리스크 0, 순수 신호 수집.
  2. 안전망 있는 전환(`control_with_direct_fallback`): 실제 트래픽이 Control을 거치고, 실패 시 direct로 폴백.
  3. 안전망 제거(strict, `control`): 카탈로그에 등록된 라우트에서 direct 폴백 제거 — **이 단계에서 실제 운영 사고가 터졌다**(§4).
  4. 선언형 intent: 호출자가 구체적 service/action을 지정하는 걸 완전히 멈춤.

## TASK-2: PDF/DOCX 렌더링 출력 수정 + 서식 표기법을 정규식으로 잘못 설명한 프롬프트 수정

- 상태: 완료
- 관련 서비스: chatbot, reportlayout
- 완료 기준: 문서 생성 실행이 PDF(또는 DOCX) 출력을 선택하면 실제로 다운로드 가능한 파일이 생성되고, 모델이 생성한 필드 값이 대량으로 서식 검증기를 통과하지 못하는 일 없이 통과한다.
- 서비스별 분담:
  - **chatbot**: 문서 생성 흐름이 DOCX를 하드코딩하는 대신 둘 중 어느 출력 형식이든 요청할 수 있게 함; 필드 생성 프롬프트 수정(이 프롬프트는 프로젝트 전용 서식 표기법을 표준 정규식이라고 알려주고 있었다 — 그게 아니다. 이 표기법에서 `[0]`는 "숫자 1자리"를 뜻하지만 실제 정규식에서는 "리터럴 문자 0"을 뜻한다 — 정반대라서 모델이 정확히 틀린 모양의 값을 만들어내게 했다).
  - **reportlayout**: 수정 필요 없음 — render 엔드포인트는 이미 출력 형식 파라미터를 받고 있었다; chatbot이 그냥 그걸 안 쓰고 있었을 뿐.
- 진행 로그:
  1. 사용자 보고("'형식과 일치하지 않음' 오류가 뜨는데 프롬프트 문제 같다")에서 실제 프롬프트 텍스트가 그 표기법을 정규식이라고 설명하고 있는 지점까지 근본 원인을 추적 — 사용자 자신의 진단이 맞았다.
  2. 잘못된 문법 대신 실제 표기법의 문법을 설명하도록 프롬프트를 고치고, UI부터 render 호출까지 출력 형식 선택을 연결.
  3. 작업을 완료라고 부르기 전에, 격리된 백엔드 테스트 스위트(43 passed)와 실제 render 요청(HTTP 200, 두 형식 모두 올바른 파일 시그니처)으로 검증.

---

## 1. TASK-1 진행 중 chatbot의 short-term memory가 어떤 모습이었나

```markdown
# chatbot short-term memory

## 지금 할 일
- long-term memory 항목: #4 — 공용 HTTP adapter를 service/action 라우팅에서 intent 기반 라우팅으로 전환
- 구체적 다음 행동: adapter의 라우트 테이블을 (service, method, path) → intent 조회로 바꾸고;
  `_via_control`이 `{service, action, inputs}` 대신 `{intent, inputs}`를 보내도록 수정; 요청을
  직접 구성하는 5개 호출부 업데이트.
- 시작 시각: (마이그레이션 중간)
```

## 2. TASK-1의 안전망 제거 단계에서 chatbot의 long-term memory가 어떤 모습이었나

```markdown
# chatbot long-term memory — TASK-1 (안전망 제거 단계)

> 안전망 있는 전환 단계가 끝나고 실제 트래픽으로 Control이 카탈로그에 등록된 모든 라우트를 제대로 처리하는 걸 확인한 뒤 다시 채워졌다.

1. [x] 검증된 Action 계약이 있는 라우트에 대해 adapter의 모드를 `control_with_direct_fallback`에서
   `control`로 전환 — 카탈로그에 없는 라우트가 조용히 direct로 가는 대신 fail closed하면 완료.
2. [x] 안전망이 제거된 상태에서 각 다운스트림 서비스의 대표 Action이 여전히 Control을 통해
   성공하는지 재검증.
3. [ ] 전환 전 audit이 놓친 "카탈로그에 없는 라우트" 실패가 없는지 운영 트래픽을 지켜본다.
```

## 3. 3번 항목에서 실제로 일어난 일 — 실제 log 항목

```markdown
### 2026-10-22 — 안전망 제거: 운영 사고와 수정

안전망 제거 배포 수 분 만에 라우트 하나가 운영에서 실패했다: `GET /api/agent/blocks/search`
(특정 research 코드 경로가 쓰는 datanalyze 호출)가 기존의 조용한 direct 폴백 대신
"카탈로그에 없는 라우트" 오류를 내기 시작했다.

근본 원인: 그 호출부는 호출자가 함수 파라미터로 Control 라우팅을 선택할 수 있게 해주는
두 번째의, 더 오래된 메커니즘을 거치고 있었다 — 하지만 실제로 그 파라미터를 설정하는
호출자는 하나도 없었고, 그래서 그 라우트는 쭉 조용히 "direct"로 빠지고 있었다. 범용
adapter의 라우트 테이블에 있던 주석 하나가 그 두 번째 메커니즘 때문에 이 라우트를 카탈로그에
등록할 필요가 없다고 잘못 가정하고 있었다. strict 모드가 그 가정이 낡았다는 걸 드러냈다.

수정: 아무도 안 쓰는 경로를 설명하는 주석을 믿는 대신, 실제 트래픽을 전부 처리하는 바로
그 한 곳에 라우트를 제대로 카탈로그에 올렸다. 그 라우트가 Control을 거쳐 해석된다는 걸
단언하는 회귀 테스트를 추가했다. 전체 테스트 스위트: 490 passed, 93 skipped. 배포했고,
운영 로그에서 더 이상 "카탈로그에 없는 라우트" 오류가 없는 걸 확인했다.

TASK-1 long-term memory 3번 항목 → 완료. 이 단계의 long-term memory 소진; chatbot이 맡은
TASK-1 부분은 다음 단계(선언형 intent)로 넘어갔다.
```

---

이게 문서들이 실제로 취하는 형태다: short-term 계층은 짧고, 지금 상태만 담고, 버려지는 게 당연하고; long-term 계층은 순서 있고 체크 가능한 목록이고; log 계층은 뭔가가 실제로 끝나서 확인됐을 때(그 전에는 아니고) 영구히, 구체적으로 남는 기록이다.
