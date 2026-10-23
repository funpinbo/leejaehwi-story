# 오케스트레이션: Intent Catalog와 Control Plane

## 호출자 계약

호출자(예: `chatbot`)는 절대 "`datanalyze`의 `blocks_search` 엔드포인트를 호출해라"라고 말하지 않는다. 대신 이렇게 말한다:

```json
{
  "requester_service": "chatbot",
  "requests": [{ "intent": "knowledge.blocks.search", "inputs": { "standard": "...", "limit": 20 } }]
}
```

`orchestration-control`이 Intent Catalog — `knowledge.blocks.search`를 구체적인 다운스트림 service + Action + backend로 매핑하는 것 — 를 소유하며, 호출자의 코드나 배포가 전혀 바뀌지 않아도 그 매핑을 바꿀 수 있다. 호출자의 코드는 오직 `inputs`의 **형태**에만 합의하면 되고, 그건 intent와 지금 카탈로그가 가리키는 다운스트림 사이의 계약일 뿐이다.

이게 중요한 이유는 "유연성" 말고 두 가지가 더 있다: (1) 호출자의 서비스 identity는 다운스트림 전용 자격증명을 절대 들고 있지 않다 — Control/Worker가 intent별로 범위를 좁혀서 그걸 들고 있으므로, 호출자가 뚫려도 그게 지금까지 쓴 모든 다운스트림 자격증명을 넘겨주지는 않는다; (2) 승인 제어를 `intent:*`/`data:*` 정책 하나로 한 번만 작성하면 되고, 호출자마다 다운스트림 서비스마다 따로 작성할 필요가 없다.

## 요청 생명주기

1. **승인(Admission)** — Control이 호출자의 identity를 그 identity에 부여된 intent 목록(식별 토큰 자체와는 분리된, 비밀이 아닌 런타임 정책)과 대조한다 — 호출자의 권한 집합을 회전시키는 것이 자격증명을 다시 봉인하는 걸 요구하지 않는다.
2. **실행 계획 선택** — Intent Catalog가 intent를 (필요하면 파라미터화도 함께 — 예: `document.render` intent는 입력 필드에 따라 `document.render.pdf` 또는 `.docx`로 해석된다) DAG Template로 풀어낸다: 어느 service/Action을 어떤 순서로 부를지, intent가 둘 이상의 단계로 갈라지면 Rule Engine이 그 분기를 결정한다.
3. **영속 실행** — 각 단계는 lease/heartbeat/epoch fencing으로 추적되어, Worker 크래시나 재시작이 단계를 두 번 실행하거나 조용히 멈춰버리지 않게 한다; 취소와 타임아웃 둘 다 명시적인 복구 경로를 갖는다.
4. **Worker 실행** — Worker는 Control의 계획을 그대로 믿지 않고 자기 로컬 Action Spec에 대해 독립적으로 재검증한 뒤, SSRF/redirect 보호가 적용된 엔드포인트 allow-list에 대해, Worker가 들고 있는 다운스트림 전용의 회전 가능한 자격증명으로 다운스트림 서비스를 호출한다. 다운스트림 비밀은 Control이나 최초 호출자에게 절대 보이지 않는다.
5. **결과** — JSON 결과는 그대로 인라인으로 돌아온다. 바이너리 결과(렌더링된 PDF, 가져온 raw 파일)는 Worker가 Artifact Resolver에 쓰고, 호출자에게는 ownership-checked artifact-content 엔드포인트로 다시 읽을 수 있는 아티팩트 참조로 돌려준다 — 호출자는 Resolver나 다운스트림 스토리지 자격증명도 절대 들고 있지 않는다.
6. **감사** — 모든 request, execution, artifact 기록이 lineage와 함께 남고, 권한 기반 감사 API로 조회할 수 있다.

## Fan-in, idempotency, fencing

DAG 단계는 (바로 앞 단계의 결과를 기다리는 게 아니라) 둘 이상의 upstream 결과가 모여야 실행되는 명시적 fan-in을 가질 수 있다. Idempotency는 `(caller, payload)` 기준으로 키가 매겨져서, 재시도된 요청이 이미 끝난 단계를 다시 실행하지 않는다. 단계 소유권은 heartbeat와 epoch 카운터가 있는 lease를 쓴다: Worker가 단계 중간에 죽으면 lease가 만료되고, 백그라운드 복구 프로세스가 단계를 재배정하고, epoch fencing이 죽은 Worker의 (늦게 도착한) 완료 결과가 새 시도의 결과로 오인되지 않게 보장한다.

## Backend 추상화(Artifact Resolver)

호출자는 아티팩트를 물리 경로가 아니라 URI(`artifact://<kind>/<entity>/<alias>`)로 주소한다. Resolver가 그것을 이름으로 여러 개의 상호 교체 가능한 스토리지 backend(파일시스템/NAS mount, 소형 payload용 Postgres `bytea`, S3 호환 object storage, vector index) 중 하나로 매핑하고, 두 아티팩트의 content hash가 같으면 backend가 달라도 물리 저장을 중복 제거한다. Retention 정책, ACL(department/division/identity-scope 매칭), lineage(parent/child provenance, 예: "이 파생 문서는 이 세 개의 원본 revision으로부터 렌더링됐다")는 이 계층에서 집행되고, 호출자마다 다시 구현되지 않는다.

## 전환 규율

이 마이그레이션의 모든 단계 — shadow, 안전망 있는 전환, 안전망 제거 — 는 (mock이 아니라) 실제 서비스 트래픽으로 배포·검증된 뒤에야 다음 단계로 넘어갔고, 안전망(`control_with_direct_fallback`)은 그걸 정당화했던 구체적인 남은 갭들(장시간 비동기 action, 바이너리 payload 계약, GPU capability 범위의 inference)이 각자의 명시적 계약을 갖기 전까지 그대로 남아 있었다. "라우트 X는 아직 direct 폴백이 있다"는 건 암묵적으로 방치된 게 아니라, 명시적 제거 순서가 있는 범위 지정된 갭으로 추적됐다.
