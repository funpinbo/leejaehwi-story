---
name: pad-format-finalize
description: 검토가 끝난 PAD 내용을 Word 템플릿의 placeholder에 맞는 JSON으로 확정한다. 문서 파일을 직접 만들지 않고, 템플릿 엔진이 쓸 데이터만 만든다.
---

# 문서 양식 확정 Skill

## 입력
- 앞 단계에서 정리한 PAD 항목 (규격, Revision, 시험 항목, 결과 요약 …)
- 템플릿 placeholder 목록: `part_number`, `manufacturer`, `spec_ref`, `spec_revision`, `test_summary`

## 절차
1. 각 PAD 항목을 placeholder 키에 매핑한다.
2. 키마다 형식 규칙을 확인한다. (예: `part_number`는 `PN-YYYY-NNNN`, `test_summary`는 200자 이내)
3. 매핑되지 않은 placeholder는 비워 두지 말고 목록으로 보고한다.

## 규칙
- **문서(.docx)를 직접 생성하지 않는다.** 폰트·표·머리글 같은 형식은 템플릿이 책임진다.
- JSON 한 개만 출력한다.

## 출력
```json
{
  "part_number": "PN-2026-0412",
  "manufacturer": "...",
  "spec_ref": "...",
  "spec_revision": "...",
  "test_summary": "...",
  "_unmapped": []
}
```
