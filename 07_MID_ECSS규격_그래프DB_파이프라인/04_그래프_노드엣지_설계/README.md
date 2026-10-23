# 그래프 노드 · 엣지 설계 — 유사도가 아니라 관계로 답하기

> **한 줄 요약**: "이 부품군에 적용되는 규격은?", "이 규격의 최신 Revision은?" 같은 질문은 비슷한 문장을 찾는 문제가 아니라 **관계를 따라가는 문제**라서, 노드 8종 · 엣지 7종의 규격 그래프를 설계했습니다.

---

## 1. 상황

PAD 작성자가 실제로 묻는 질문들입니다.

- 이 **부품군**에 적용되는 규격은 무엇인가?
- 그 규격의 **최신 Revision**은 무엇인가?
- 이 규격을 따르려면 **함께 봐야 하는 문서**는 무엇인가?
- 우리 프로젝트 **Class**에서도 유효한가?

## 2. 문제

- Vector Search는 "비슷한 문장"을 찾습니다. "최신 Revision"이나 "참조의 참조"는 문장 유사도로 답할 수 없습니다.
- 틀린 Revision은 승인 문서에서 바로 반려 사유가 됩니다.

## 3. 설계

| 노드 | 의미 |
|---|---|
| `Specification` | 규격 문서 (canonical record, [03](../03_ESCC_메타데이터_정규화)) |
| `DocumentRevision` | 규격의 특정 Issue / Revision |
| `Requirement` | 요구사항 Block ([01](../01_4계층_AtomicBlock_스키마)) |
| `ComponentFamily` | 부품군 (Capacitor, Resistor …) |
| `TestMethod` | 시험 방법 (TID, Leak …) |
| `Qualification` | 인증 · 평가 단계 |
| `ProjectClass` | 프로젝트 등급 |
| `PADSection` | PAD 문서의 섹션 |

| 엣지 | 의미 |
|---|---|
| `REFERENCES` | 문서/조항이 다른 문서/조항을 참조 |
| `APPLIES_TO` | 규격 → 부품군 |
| `REQUIRES` | 요구사항 → 인증 · 시험 |
| `SUPERSEDES` | 새 Revision → 이전 Revision |
| `RELATED_TO` | 일반 연관 (Revision ↔ 문서, 요구사항 ↔ 문서 등) |
| `USED_FOR_PAD` | 규격 → PAD 섹션 |
| `VALID_FOR_CLASS` | 규격 → 프로젝트 Class |

### 같은 질의를 Apache AGE(Cypher)로

```sql
-- Q1. Capacitor에 적용되는 규격의 최신 Revision (대체되지 않은 Revision)
SELECT * FROM cypher('spec_graph', $$
  MATCH (s:Specification)-[:APPLIES_TO]->(:ComponentFamily {name: 'Capacitor'})
  MATCH (r:DocumentRevision)-[:RELATED_TO]->(s)
  WHERE NOT EXISTS { MATCH (:DocumentRevision)-[:SUPERSEDES]->(r) }
  RETURN s.doc_number, r.issue
$$) AS (doc agtype, latest agtype);

-- Q2. 참조 체인 (최대 4단계)
SELECT * FROM cypher('spec_graph', $$
  MATCH p = (:Specification {doc_number: 'ESCC-3009-001'})-[:REFERENCES*1..4]->(:Specification)
  RETURN p
$$) AS (path agtype);
```

## 4. 결과

- Revision · 참조 체인 · Class 유효성처럼 **Vector Search로는 불안정한 질문을 그래프 탐색으로 결정적으로** 답할 수 있는 기반 마련
- 최신 Revision이 0개이거나 여러 개면 **추측하지 않고 사람 검토로** 넘기도록 설계

## 5. 배운 점

- **질문의 형태가 저장 구조를 정한다.** "비슷한 것"을 묻는 질문은 벡터로, "연결된 것"을 묻는 질문은 그래프로.
- **PostgreSQL 하나로 시작한다.** 1인 유지보수 환경이라 별도 그래프 DB 대신 PostgreSQL 확장(Apache AGE)을 택해, 메타데이터 · 벡터 · 그래프를 한 곳에서 운영할 수 있게 했습니다.

---

## 예제 코드 — `spec_graph.py`

인메모리 그래프로 노드 · 엣지 타입을 검증하면서 적재하고, Q1~Q3를 탐색합니다. (문서 번호 · 관계는 예시)

```bash
python spec_graph.py
```

```
Q1. Capacitor 부품군에 적용되는 규격과 최신 Revision은?
   ESCC-3009       최신: ESCC-3009@5
   ESCC-3009-001   최신: 등록된 Revision 없음 → 사람 검토

Q2. ESCC-3009-001을 따를 때 함께 봐야 하는 문서 (참조 체인)
   ESCC-3009-001 → ESCC-3009 → ESCC-2269000 → ESCC-22900

Q3. PAD '5. 시험' 섹션 작성에 쓰이는 규격과 관련 시험 방법
   ESCC-3009       시험방법 -  유효 Class ['Class1']
   ESCC-22900      시험방법 ['TID']  유효 Class 미지정
```
