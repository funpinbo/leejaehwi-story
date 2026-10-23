# 스키마 v3에서 v4로 — 실제 데이터가 스키마를 고친다

> **한 줄 요약**: v3 스키마로 실제 문서를 추출해 보니 **그룹 개념이 없고, 조항 앞 도입문(lead-in)이 잘려 의미가 깨지고, `normative_type`이 다른 필드와 섞여** 있었습니다. v4(`schema_version 1.1`)에서 `groups` · `relations(GOVERNS)` · 리드인 주입 · `derived_fields` 분리 · 스키마 메타 선언을 도입했습니다.

---

## 1. 상황

- [01. Block 스키마](../01_4계층_AtomicBlock_스키마)를 v3까지 만든 뒤, ECSS-P-00 문서를 실제로 추출해 388개 Block을 얻었습니다.
- 추출 결과를 하나씩 읽어보며 "이 Block 하나만 보고 의미가 통하는가?"를 검토했습니다.

## 2. v3에서 발견한 문제

| # | 문제 | 예시 |
|---|---|---|
| 1 | **그룹 개념 부재** | 목록 항목 a, b, c가 서로 관계없는 Block으로 흩어짐 |
| 2 | **리드인 문맥 손실** | "다음의 경우 공급자는 승인을 받아야 한다:" 아래의 "b. 부품을 교체하는 경우"만 떼면 **누가 무엇을 해야 하는지** 사라짐 |
| 3 | **`normative_type` 혼재** | 원문에서 추출한 값과, shall/should로 **추론한 값**이 같은 레벨에 섞임 |
| 4 | **필드 상태 불명확** | 어떤 필드가 필수인지, 나중에 채울 건지, 계산된 건지 스키마만 봐서는 모름 |

## 3. v4 개선 (`schema_version 1.1`)

| 문제 | v4 해결 |
|---|---|
| 그룹 부재 | **`groups` 계층 신설** — `group_type`: `LIST` / `FIGURE` / `TABLE` / `CONDITION_SCOPE` (총 31개 그룹) |
| 리드인 손실 | **`normalized_text`에 리드인 주입** — `atomic_text`(원문)는 그대로, 검색·LLM용 텍스트에만 문맥 보강 |
| 관계 표현 | **`relations` 신설** — 리드인 Block이 하위 항목을 `GOVERNS` |
| 필드 혼재 | 추론 값은 **`derived_fields`로 분리** (`normative_type` 등) |
| 필드 상태 | **`required` / `deferred` / `derived_fields` 메타 선언** — 스키마 거버넌스 |

```
v3: Block("b. 부품을 교체하는 경우")
       normalized_text = "부품을 교체하는 경우"            ← 무엇을 해야 하는지 모름

v4: Group(LIST)
     ├ Block(lead-in) "다음의 경우 공급자는 승인을 받아야 한다:"
     │     └ GOVERNS → b
     └ Block b
           atomic_text     = "b. 부품을 교체하는 경우"      ← 원문 불변
           normalized_text = "다음의 경우 공급자는 승인을 받아야 한다: 부품을 교체하는 경우"
           derived_fields  = {"normative_type": "MANDATORY"}  ← 리드인의 '해야 한다'에서 추론
```

## 4. 결과

- 목록 항목 Block 하나만 검색돼도 **완결된 의미**를 가지게 됨
- 원문 / 정규화 / 추론 값의 경계가 명확해져, 추론 로직이 바뀌어도 원문 데이터는 영향받지 않음

## 5. 배운 점

- **스키마는 한 번에 완성하는 게 아니라 데이터로 검증하며 진화시키는 것.** 실제 388개 Block을 읽어보지 않았다면 리드인 문제는 발견하지 못했을 것입니다.
- **"원문 · 가공 · 추론"을 다른 칸에 둔다.** 섞여 있으면 무엇을 신뢰할 수 있는지 판단할 수 없습니다.
- **스키마에도 버전과 거버넌스가 필요하다.** `schema_version`과 필드 상태 선언이 있어야 v3 데이터와 v4 데이터를 함께 다룰 수 있습니다.

---

## 예제 코드 — `migrate_v3_to_v4.py`

합성 v3 Block들을 v4로 마이그레이션합니다. 목록을 그룹으로 묶고, 리드인을 찾아 `GOVERNS` 관계를 만들고, `normalized_text`에 리드인을 주입하고, `normative_type`을 `derived_fields`로 옮깁니다.

```bash
python migrate_v3_to_v4.py
```
