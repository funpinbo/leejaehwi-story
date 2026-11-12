# 내 컴퓨터로 AGENT 개발하기

> LLM이 무엇인지 모르는 사람도 기초 개념부터 따라와서, 최종적으로 **자기 컴퓨터에서 AI Agent를 설계하고 개발할 수 있게** 하는 연재입니다.
> 실무에서 DGX 계열 장비로 모델을 서빙하고 에이전트를 만든 경험을 바탕으로 씁니다.

블로그 카테고리: [Local-Agent](https://blog.jimmy-home.com/@jaehwi?category=local-agent#posts)

## 전체 계획 — [작성할 순서](https://blog.jimmy-home.com/@jaehwi/local-agent)

| 편 | 다루는 것 | 함께 읽는 논문 | 상태 |
|---|---|---|---|
| 1 | LLM 기본 원리, 모델 고르기, 하드웨어, 서빙 | PagedAttention | 작성 완료 |
| 2 | Agent 개념, 개발 프레임워크, LangGraph 기본 구조 | CoALA | 작성 중 |
| 3 | Single Agent, Workflow 패턴, Multi-Agent, Graph 기반 Agent | Reflexion | 예정 |
| 4 | 통신(HTTP · SSE · WebSocket), Tool Calling, MCP, Agent Skill, A2A | SWE-agent | 예정 |
| 5 | DB(관계형 · 벡터 · 그래프), 전처리 · 청킹, 검색과 RAG, Knowledge Graph | MemGPT, GraphRAG | 예정 |
| 6 | Agent 시스템 기획과 아키텍처 (Agent / Backend 분리, Control · Execution Plane, 분산 상태) | | 예정 |
| 7 | 심화: Human-in-the-loop, 실행 예산, 실패 복구, 장기 실행, 평가 루프 | | 예정 |

## 쓴 글

### [1(1) — LLM 기본 원리와 모델 고르기](https://blog.jimmy-home.com/@jaehwi/local-agent-1-1)

- **Token / Tokenizer**: LLM은 문장을 그대로 계산하지 않고 토큰으로 나눠 숫자로 바꿔 처리한다.
- **Transformer / Attention / KV Cache**: 토큰을 따로 보지 않고 주변 토큰과의 관계를 계산한다. Decoder-only 모델이 주류가 된 이유(입력 · 출력을 하나의 시퀀스로, 다양한 작업을 "텍스트 생성"으로 통일).
- **Prefill / Decode**: 다른 모델이 아니라 같은 모델의 두 추론 단계.
- **Context Window**: 크기만이 아니라 무엇을 넣고 빼고 요약할지가 Agent의 설계 요소.
- **Sampling**: Temperature, Top-p.
- **모델 고르기**: Dense / MoE, Benchmark · Memory Bandwidth · TTFT / TPOT / Throughput, 양자화(AWQ, GGUF), 라이선스와 하드웨어 · 추론 엔진 호환성.

### [1(2) — 하드웨어와 서빙](https://blog.jimmy-home.com/@jaehwi/local-agent-1-2)

- **GPU 아키텍처**: SIMD / SIMT, Warp와 Warp Scheduler. Thread가 많다고 빠른 게 아니라 같은 연산을 효율적으로 하게 설계해야 한다.
- **DGX Spark(GB10) vs RTX Blackwell**: GPU 아키텍처뿐 아니라 CPU 아키텍처와 소프트웨어 호환성까지 확인해야 하는 이유. Unified Memory.
- **고르는 기준**: VRAM / Unified Memory, 메모리 대역폭(연산보다 데이터를 가져오는 속도가 병목), Compute 성능.
- **서빙**: Ollama, vLLM, TensorRT-LLM, OpenAI-compatible API, Continuous Batching / PagedAttention, TTFT · TPOT · Throughput · Latency 측정, 동시 요청과 메모리.

### [2(1) — LLM Agent와 개발 프레임워크](https://blog.jimmy-home.com/@jaehwi/local-agent-2-1)

- **AI에서 LLM까지**, LLM과 Agent의 차이, Workflow와 Agent.
- **Tool Calling, ReAct(Reason → Act → Observe)**, Agent Loop의 종료는 "LLM이 판단하는 정상 종료 + 코드가 강제하는 안전 종료"의 두 겹.
- **Deterministic Code와 LLM 의사결정**: 보고서 작성 Agent 경험을 예로, 스타일 · 틀은 코드로 잠그고 내용만 LLM에 연다. *Agent를 만든다는 것은 어디를 LLM에게 열고 어디를 코드로 잠글지 설계하는 일.*
- **프레임워크 비교**: LangChain / LangGraph, CrewAI, OpenAI Agents SDK, Google ADK, PydanticAI, LlamaIndex, Microsoft Agent Framework.

### [2(2) — LangGraph 기본 구조](https://blog.jimmy-home.com/@jaehwi/local-agent-2-2)

- 보고서 작성 Agent를 단계(자료 분석 → 빈칸 작성 → 조건 확인 · 재작성 → 파일 생성)로 나누는 것부터 시작.
- Node / Edge / Conditional Edge, State / State Reducer, Checkpointer · Persistence · Interrupt · Command, Subgraph(정보 탐색 Agent를 하나의 Node처럼), Compile · Invoke · Stream.

## 다음

- 2편 마무리 후 CoALA 리뷰를 이어서, 3편(Single / Multi-Agent)으로 넘어갑니다.

---

- [공부 기록 목록](../README.md)
