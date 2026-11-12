# 논문 리뷰

> 「내 컴퓨터로 AGENT 개발하기」의 각 편에서 **한 번쯤 짚고 넘어가면 좋을 주제**를 기준으로 논문을 고릅니다.
> 요약이 아니라, 논문을 읽는 데 필요한 배경지식부터 **풀어서 소개하는 장문**으로 씁니다.

블로그 카테고리: [ML/DL/LLM](https://blog.jimmy-home.com/@jaehwi?category=mldlllm#posts)

| 논문 | 연결되는 편 | 글 | 상태 |
|---|---|---|---|
| Efficient Memory Management for Large Language Model Serving with **PagedAttention** (vLLM) | 1편 서빙 | [1](https://blog.jimmy-home.com/@jaehwi/pagedattention-1) · [2](https://blog.jimmy-home.com/@jaehwi/pagedattention-2) · [3](https://blog.jimmy-home.com/@jaehwi/pagedattention-3) | 완료 |
| Cognitive Architectures for Language Agents (**CoALA**) | 2편 Agent 개념 | [1](https://blog.jimmy-home.com/@jaehwi/coala-1) | 작성 중 |
| Reflexion · SWE-agent · MemGPT · GraphRAG | 3 · 4 · 5편 | | 예정 |

## PagedAttention

### [(1) 논문을 보기 전](https://blog.jimmy-home.com/@jaehwi/pagedattention-1)

논문 2장(Background)에 해당하는 배경지식을 먼저 풀었습니다.
LLM이 작동하는 방식, Self-attention(Q · K · V), **KV cache가 얼마나 큰지**, 생성 단계(prefill / decode), Batching.

> 기존 시스템의 문제는 하나의 뿌리에서 나온다. **"KV cache는 동적으로 자라는데, 연속된 공간에 미리 잡아야 한다."**
> 100토큰만 만들고 끝나는 요청도 최대 길이만큼의 공간을 차지한다.

### [(2) 메모리 문제와 PagedAttention](https://blog.jimmy-home.com/@jaehwi/pagedattention-2)

- LLM 서빙의 메모리 도전: 큰 KV cache, 복잡한 디코딩 알고리즘, 입력 · 출력 길이를 모르는 스케줄링, 기존 시스템의 관리 방식.
- **왜 paging인가**: OS 가상 메모리처럼 고정 크기 블록으로 나누고, 논리 블록을 물리 블록에 이어 준다.
- PagedAttention은 계산 결과는 그대로 두고 **KV cache를 담는 단위를 토큰에서 블록으로** 바꿔, 블록이 메모리 어디에 있어도 되게 한 attention.
- KV Cache Manager, 디코딩 과정, parallel sampling · beam search · shared prefix, Scheduling과 Preemption.

### [(3) 구현과 평가](https://blog.jimmy-home.com/@jaehwi/pagedattention-3)

- 커널 최적화: fused reshape & block write, block read + attention 결합, fused block copy.
- 여러 디코딩 알고리즘을 **fork · append · free 세 연산**으로 구현.
- 평가: 같은 지연 수준에서 Orca 대비 1.7~2.7배(Oracle) · 2.7~8배(Max), FasterTransformer 대비 최대 22배 높은 요청률. Beam search에서 메모리 37.6~55.2% 절약.

## CoALA

### [(1) 배경](https://blog.jimmy-home.com/@jaehwi/coala-1) — 작성 중

에이전트마다 용어와 구조가 제각각이라 비교하기 어려운 문제를, 인지과학의 인지 아키텍처 개념으로 정리한 틀.
**메모리, 행동 공간, 의사결정 절차** 세 축으로 에이전트를 설명합니다. 새 기법이 아니라 에이전트를 바라보는 기준을 세운 논문이라, 이후 Single / Multi-Agent 글의 개념적 토대로 골랐습니다.

---

- [공부 기록 목록](../README.md)
