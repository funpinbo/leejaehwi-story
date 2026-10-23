# Fail-Closed 호출 경계 — 허용된 것만, 정규화한 뒤에, 계약이 맞을 때만

> **한 줄 요약**: 다른 서비스를 대신 호출하는 Worker와, 임의 URL을 받아 웹 문서를 가져오는 검색 서비스은 **잘못 쓰이면 내부망 전체에 접근하는 통로**가 됩니다. 그래서 ① 경로를 **percent-decode · dot-segment 정규화한 뒤** allowlist로 검사하고 ② allowlist에 없으면 **기본 거부(fail-closed)** ③ Control이 보낸 계약 digest가 Worker가 가진 승인 계약과 **정확히 같을 때만** 실행 ④ 외부 fetch는 사설 IP · 클러스터 내부 주소를 **애플리케이션 레벨에서 차단**하도록 만들었습니다.

---

## 1. 상황

- **Worker**: Control이 "이 서비스의 이 action을 실행하라"고 보내면 실제 HTTP 호출을 수행합니다. 하위 서비스 토큰을 가지고 있습니다.
- **검색 서비스**: chatbot이 준 검색어 · URL로 외부 웹 문서를 가져옵니다.

## 2. 위협 시나리오

| 시나리오 | 예 |
|---|---|
| 경로 우회 | `/v1/../admin/delete`, `/v1/%2e%2e/admin` 처럼 allowlist 접두사를 통과한 뒤 다른 경로로 |
| 리다이렉트 우회 | 허용된 endpoint가 302로 허용되지 않은 곳으로 보냄 |
| 계약 불일치 | Control의 카탈로그와 Worker의 승인 계약 버전이 달라 다른 스키마로 호출 |
| 토큰 노출 | 하위 서비스 토큰을 요청 본문으로 주고받음 |
| SSRF | 검색 서비스에 `http://10.0.0.5/` 이나 `http://*.cluster.local/` 을 fetch하라고 요청 |
| suffix 공격 | `site=ecss.nl` 필터를 `fakeecss.nl`이 통과 |

## 3. 설계

| 장치 | 동작 |
|---|---|
| **경로 정규화 후 allowlist** | percent-decode → dot-segment(`.`, `..`) 제거 → canonical path로 만든 뒤 검사. 첫 리다이렉트 대상도 같은 검사 |
| **이중 검증 · fail-closed** | `허용 endpoint 목록`과 `승인된 action spec` 둘 다에 있어야 실행. 설정이 비어 있으면 전부 거부 |
| **계약 digest exact match** | catalog version · digest · 요청/응답 스키마 digest를 Worker가 **로컬 승인 spec에서 재계산**해 비교. 다르면 `ACTION_CONTRACT_MISMATCH` |
| **JSON Schema 검증** | 요청은 하위 호출 전, 응답은 반환 전 검증. 실패는 재시도 불가 오류이고 payload 원문은 로그에 남기지 않음 |
| **토큰은 받지 않는다** | 하위 서비스 토큰은 요청으로 받지 않고 Worker가 서비스 이름으로 **자기 Secret에서 조회**. Control DB에도 토큰 컬럼 없음 |
| **path 파라미터 인코딩** | `{name}` 치환값은 path segment 하나로 percent-encoding (`/`가 섞여도 경로가 바뀌지 않게) |
| **SSRF 가드** | 사설 IP · loopback · link-local · `*.cluster.local`로의 요청 차단 (네트워크 정책만으로는 "임의 URL fetch"를 막을 수 없음) |
| **site 필터** | hostname만 허용, IDNA 정규화, **label 경계**로 `site` 또는 `.site` 일치만 통과 |

## 4. 결과

- Worker 테스트는 mock이 아니라 **실제 TCP 스텁 서버**를 상대로 작성
- 실패 유형을 `TIMEOUT` / `CONNECTION_ERROR` / `DOWNSTREAM_ERROR` / `ENDPOINT_NOT_ALLOWED` / `CANCELLED` / `ACTION_CONTRACT_MISMATCH`로 나눠, 재시도 가능 여부를 유형으로 결정

## 5. 배운 점

- **문자열 비교 전에 정규화한다.** 보안 검사는 "사람이 보는 문자열"이 아니라 "서버가 실제로 해석할 값"에 대해 해야 합니다.
- **기본값은 거부.** 설정이 빠졌을 때 "전부 허용"이 되는 시스템은 언젠가 반드시 사고가 납니다.
- **비밀은 움직이지 않게 한다.** 토큰을 요청에 싣지 않으면, 로그 · DB · 오류 메시지로 새어나갈 경로 자체가 사라집니다.

---

## 🧪 예제 코드 — `call_boundary.py`

경로 정규화 + allowlist, 계약 digest 비교, SSRF 가드, site 필터를 표준 라이브러리만으로 구현하고, 위 위협 시나리오 입력을 넣어 각각 차단되는지 확인합니다. (실제 네트워크 요청은 하지 않습니다)

```bash
python call_boundary.py
```

## 🎤 면접에서 이렇게 말한다

> "다른 서비스를 대신 호출하는 Worker는 잘못 쓰이면 내부망 통로가 되기 때문에, 경로를 percent-decode하고 점 세그먼트를 정규화한 뒤 allowlist로 검사하고, 목록에 없으면 기본 거부합니다. Control이 보낸 계약 digest를 Worker가 직접 재계산해 다르면 실행하지 않고, 하위 서비스 토큰은 요청으로 받지 않습니다. 외부 URL을 가져오는 서비스에는 사설 IP와 클러스터 내부 주소를 막는 SSRF 가드를 넣었습니다."
