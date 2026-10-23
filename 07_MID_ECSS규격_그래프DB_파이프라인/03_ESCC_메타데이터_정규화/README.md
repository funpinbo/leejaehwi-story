# ESCC 메타데이터 정규화 — 이슈 단위 데이터를 문서 단위로

> **한 줄 요약**: ESCC Specification List CSV는 한 문서의 여러 Issue(개정판)가 각각 행으로 들어 있어, 원본 약 645건을 **고유 Document Number 기준 641건의 canonical record**로 정리하고, 검색(`search_text`) · PAD 연관도(`pad`) · 그래프 적재(`graph_hints`)용 필드를 설계해 JSON(`schema_version 1.1`)으로 변환했습니다.

---

## 1. 상황

- 규격 문서 본문(Block)과 별개로, **"어떤 규격 문서들이 존재하고 최신 Issue가 무엇인가"** 라는 목록 메타데이터가 필요했습니다.
- ESCC는 Specification List를 표(CSV) 형태로 제공합니다.

## 2. 문제

| 문제 | 영향 |
|---|---|
| 같은 Document Number가 **Issue마다 여러 행** | 그대로 노드로 만들면 같은 문서가 여러 개 생김 |
| 제목 · 번호 표기가 조금씩 다름 (공백, 대소문자) | 중복 판정 실패 |
| 목록에는 "PAD와 관련 있는가" 정보가 없음 | PAD 작성에 필요한 규격을 골라낼 수 없음 |

## 3. 설계

| 필드 | 내용 | 용도 |
|---|---|---|
| `doc_number` | 정규화된 고유 번호 (canonical key) | 노드 ID |
| `latest_issue` / `issues[]` | 최신 Issue와 전체 이력 | Revision 검증, `SUPERSEDES` 엣지 |
| `search_text` | 번호 + 제목 + 분류를 결합한 문자열 | **BM25 / 임베딩 검색**용 |
| `pad` | PAD 연관도 (제목 · 번호 기반 heuristic) | PAD 작성 시 우선 후보 |
| `graph_hints` | 부품군, 시험 방법 등 노드 생성 힌트 | **Graph DB 적재** 자동화 |

## 4. 결과

- 원본 이슈 데이터 약 **645건 → 641건 canonical record**
- `schema_version 1.1` JSON으로 변환 완료 → 검색 인덱스와 그래프 적재에 바로 사용 가능

## 5. 배운 점

- **"무엇이 하나인가(identity)"를 먼저 정의한다.** 행 = 문서가 아니었습니다. canonical key를 정하자 중복 · 이력 · Revision 문제가 한꺼번에 정리됐습니다.
- **필드는 "다음 단계가 무엇을 필요로 하는가"로 설계한다.** `search_text`는 검색을 위해, `graph_hints`는 그래프 적재를 위해 존재합니다.
- `pad`는 heuristic이라는 것을 명시해 두고, 추후 실제 PAD 문서에서 역으로 검증할 계획입니다.

---

## 예제 코드 — `escc_canonicalize.py`

합성 Specification List(CSV 문자열)를 canonical record로 정리합니다. 번호 표기 정규화, Issue 이력 병합, `search_text` · `pad` · `graph_hints` 생성까지 포함합니다. (문서 번호 · 제목은 예시)

```bash
python escc_canonicalize.py
```
