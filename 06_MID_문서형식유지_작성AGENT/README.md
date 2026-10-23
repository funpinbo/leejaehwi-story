# 06. MID · 문서 형식 유지 문서 작성 AGENT

> 사내 PAD(Part Approval Document) 같은 정형 보고서를 자동으로 작성하려다, "LLM에게 Word 문서를 통째로 다시 만들게 하면 된다"는 접근이 **레이아웃을 무너뜨린다**는 것을 겪고,
> **내용(Content)은 LLM이, 형식(Layout)은 코드가** 맡는 구조로 재설계한 프로젝트입니다.

## 문서

| 문서 | 내용 |
|---|---|
| [00. 프로젝트 개요](./docs/00-overview.md) | 배경 · 문제 · 성과 · 회고 |
| [01. 아키텍처](./docs/01-architecture.md) | 구조와 흐름 |

## 경험 정리

| # | 경험 | 한 줄 요약 | 예제 코드 |
|---|---|---|---|
| 01 | [LLM 문서 재생성 실패 분석](./01_LLM_문서재생성_실패분석) | 무엇이 깨졌는지 9가지로 분류하고, "생성 방식 자체의 한계"라고 결론 | `layout_diff.py` |
| 02 | [Content / Layout 분리 템플릿 엔진](./02_Content_Layout_분리_템플릿엔진) | LLM은 JSON만, 코드는 원본 XML·스타일을 보존한 채 값만 주입 | `docx_template_engine.py` |
| 03 | [역할 분리 에이전트 설계](./03_역할분리_에이전트_설계) | Report / Layout / Verification 에이전트로 책임을 나눔 | `role_agents.py` |
