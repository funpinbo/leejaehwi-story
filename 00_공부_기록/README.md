# 00. 공부 기록

> 회사에서 사내 로컬 서버로 LLM을 서빙하고 에이전트를 만들면서 생긴 질문을, **블로그에 글로 풀어 쓰며** 공부하고 있습니다.
> 원문은 블로그에 있고, 여기에는 무엇을 공부하고 있는지와 글마다 정리한 핵심을 모았습니다.

**블로그: [blog.jimmy-home.com/?user=jaehwi](https://blog.jimmy-home.com/?user=jaehwi)** · [RSS](https://blog.jimmy-home.com/rss.xml)

## 지금 공부하고 있는 것

| # | 주제 | 왜 공부하나 | 글 |
|---|---|---|---|
| 01 | [내 컴퓨터로 AGENT 개발하기](./01_내_컴퓨터로_AGENT_개발하기) | 실무에서 해 온 로컬 LLM 서빙 · 에이전트 개발을, LLM을 모르는 사람도 따라올 수 있게 처음부터 정리 | 6편 (연재 중) · [예시 코드](https://github.com/funpinbo/local-agent_example1) |
| 02 | [논문 리뷰](./02_논문_리뷰) | 시리즈 각 장의 바탕이 되는 논문을 골라 풀어서 읽기 | PagedAttention 3편, CoALA 1편 (진행 중) |
| 03 | [AWS MLA](./03_AWS_MLA) | 사내 로컬 서버에서 하던 일을 클라우드에서는 어떻게 설계 · 운영하는지. 2026.12.23 AWS Certified Machine Learning Engineer – Associate 시험 목표 | 4편 (진행 중) |

## 공부와 프로젝트가 이어지는 곳

| 공부 | 실제로 쓴 곳 |
|---|---|
| 하드웨어 선택(DGX Spark, 메모리 대역폭), vLLM 서빙, TTFT · TPOT | [09. PAD 에이전트 플랫폼](../09_PAD_에이전트_플랫폼)의 vLLM 기반 로컬 모델 서빙 |
| PagedAttention · KV cache · Continuous Batching | 같은 GPU에서 동시 요청을 얼마나 받을 수 있는지 판단하는 기준 |
| Deterministic Code와 LLM 의사결정의 분리 | [06. 문서 AGENT](../06_문서형식유지_작성AGENT)의 Content / Layout 분리, [09](../09_PAD_에이전트_플랫폼)의 결정적 단계 |
| LangGraph State · Checkpointer | [09](../09_PAD_에이전트_플랫폼/12_턴_사이_State_누수)의 턴 사이 State 누수 |
| Single Agent 설계별 실패 → 판단을 코드로 옮기기(Retry / Fallback / Stop), 행동 공간 줄이기 | [09](../09_PAD_에이전트_플랫폼)의 결정적 단계 파이프라인, "LLM은 판정하지 않는다" |
| 데이터 형식(Parquet 등) · 저장소 선택 | [10. MSDF](../10_MSDF_데이터중심_서비스연결_프레임워크)의 DataFrame Parquet 저장, Resolver 설계 |

## 쓰는 방식

- 시리즈는 **"이런 흐름으로 흘러가는구나"를 이해하는 것**이 목표라, 개념을 비유로 단순화하되 정확한 내용은 공식 문서 · 논문을 함께 보도록 안내합니다.
- 논문은 요약이 아니라 **배경지식부터 풀어 쓰는 장문**으로 읽고, 시리즈의 어느 장에서 필요한지를 기준으로 고릅니다.
- 자격증 공부는 서비스마다 **"설명"과 "시험에서의 핵심"** 을 나눠 적습니다.
