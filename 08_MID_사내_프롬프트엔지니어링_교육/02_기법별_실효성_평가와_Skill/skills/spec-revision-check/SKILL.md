---
name: spec-revision-check
description: 문서에 인용된 규격 번호의 Revision(Issue)이 최신인지 확인한다. PAD나 보고서에 규격 번호를 적은 뒤, 제출 전에 사용한다.
---

# 규격 버전 확인 Skill

## 입력
- 인용된 규격 목록: `[{"doc": "ESCC-3009", "revision": "Issue 4"}, ...]`

## 절차
1. 각 규격을 사내 규격 목록의 canonical 번호로 정규화한다. (예: `ESCC3009` → `ESCC-3009`)
2. 최신 Revision을 조회한다. (`SUPERSEDES`로 대체되지 않은 Revision)
3. 인용 Revision과 비교한다.
   - 같으면 ✅
   - 오래됐으면 ⚠ 최신 Revision과 변경 요약을 함께 제시
   - 최신을 판단할 수 없으면(0개 또는 여러 개) ❓ 사람 확인 요청

## 규칙
- 웹 검색이나 기억으로 Revision을 추정하지 않는다. 근거는 사내 규격 목록뿐이다.
- 프로젝트 계약상 특정 Revision이 고정된 경우가 있으므로, "최신으로 바꿔라"가 아니라 "최신과 다르다"고 알린다.

## 출력
| 규격 | 인용 Revision | 최신 Revision | 상태 |
|---|---|---|---|
