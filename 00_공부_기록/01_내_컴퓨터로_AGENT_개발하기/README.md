# 내 컴퓨터로 AGENT 개발하기

> LLM이 무엇인지 모르는 사람도 기초 개념부터 따라와서, 최종적으로 **자기 컴퓨터에서 AI Agent를 설계하고 개발할 수 있게** 하는 연재입니다.
> 실무에서 DGX 계열 장비로 모델을 서빙하고 에이전트를 만든 경험을 바탕으로 씁니다.

블로그 카테고리: [Local-Agent](https://blog.jimmy-home.com/@jaehwi?category=local-agent#posts)

## 전체 계획 — [작성할 순서](https://blog.jimmy-home.com/@jaehwi/local-agent)

| 편 | 다루는 것 | 함께 읽는 논문 | 상태 |
|---|---|---|---|
| 1 | LLM 기본 원리, 모델 고르기, 하드웨어, 서빙 | PagedAttention | 작성 완료 |
| 2 | Agent 개념, 개발 프레임워크, LangGraph 기본 구조 | CoALA | 작성 완료 |
| 3 | Single Agent, Workflow 패턴, Multi-Agent, Graph 기반 Agent | Reflexion | 작성 중 · [예시 코드](https://github.com/funpinbo/local-agent_example1) |
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

### [3(1) — 실습 환경과 Single Agent](https://blog.jimmy-home.com/@jaehwi/local-agent-3-1)

3편부터는 개념 설명 대신, 보고서를 쓰는 Agent 하나를 설계 방식만 바꿔 가며 직접 만들고 돌려 본 결과로 이야기합니다. 앞 방식으로 먼저 만들어 보고, 어디서 막히는지 확인한 뒤 다음 설계로 넘어가는 순서입니다. 글에 나오는 실패 사례는 모두 실제 실행 결과입니다.

**실습 환경 — 1편의 선택 기준을 집 PC(RTX 5060 Ti 16GB)에 그대로 적용**

| 선택 | 결정 | 이유 |
|---|---|---|
| 모델 | KANANA 1.5 8B Instruct | 실습 데이터가 모두 한국어, apache-2.0이라 직접 변환 가능. 뒤로 갈수록 판단이 복잡해져 2.1B 대신 8B |
| 양자화 | 직접 Q8_0 GGUF로 변환 (llama.cpp) | BF16 원본은 약 16GB라 16GB GPU에 올라가지 않음. BF16 GGUF에서 Q8_0(8.54GB) · Q4_K_M(4.92GB)을 각각 한 번씩 만들어 오차가 겹치지 않게 함 |
| 메모리 계산 | 가중치 8.5GB + KV cache 약 2GB(컨텍스트 16k) ≈ 10GB | `ollama ps`에서 SIZE 10GB · 100% GPU로 확인. Q8_0은 32개 블록마다 16비트 scale이 붙어 가중치당 8.5비트 |
| 서빙 | vLLM 대신 Ollama | Windows에서 바로 동작, 직접 만든 GGUF를 그대로 등록, 1인 개발·실험이라 vLLM의 배칭 이점을 쓸 일이 적음 |
| 도구 호출 | 응답 본문의 호출 형식을 `tool_calls`로 바꾸는 번역 층 | 모델은 도구를 형식대로 불렀지만, Ollama가 KANANA 고유 형식을 도구 호출로 인식하지 못함. 문제는 모델이 아니라 모델과 서빙 사이의 형식 차이 |
| 데이터 | MSDF(직접 만든 데이터 플로우 엔진)에 위임 | Agent 설계와 데이터 준비 이야기가 섞이지 않게, Agent는 결과물을 이름으로 요청만 함 |

**Single Agent 다섯 가지 설계 — 메모 한 장으로 주간 · 출장 보고 docx 작성**

| 설계 | 실제로 일어난 일 | 다음 설계로 넘어간 질문 |
|---|---|---|
| 1. 기본 Tool Calling | 양식 확인 도구는 잘 불렀지만, 저장 도구 없이 내용을 답변 글로 보여 주고 종료 → 파일 없음 | 한 번에 너무 큰 일을 맡겨서일까? |
| 2. ReAct Loop | 칸을 하나씩 채우는 도구를 줬는데도 다섯 칸을 글로 나열하고 LLM 호출 2번 만에 종료 | LLM이 혼자 판단할 것이 너무 많아서일까? |
| 3. Conditional Branch | 양식은 코드나 LLM이 고르게 분기. 칸 채우기와 저장을 한 번에 불러 **병렬 실행**되면서 저장이 빈 초안을 보고 거절됨. 그런데도 "저장 완료"라고 답함 | 끝났는지를 LLM의 말로 판단하는 게 문제 아닐까? |
| 4. Retry / Fallback / Stop | 코드가 답을 검사해 2번 재시도, 그래도 안 되면 코드가 칸 전체를 받아 직접 저장 → **처음으로 파일 생성** | 파일은 남았는데 내용은 맞을까? |
| 5. Reflection | 코드 점검 + 같은 모델의 자기 점검 후 저장. 이미 해결한 일이 "해야 할 일"로 바뀐 오류를 둘 다 놓침 | 근거 자료가 메모 한 장뿐인 게 한계 |

**정리한 것**

- **행동 공간은 도구 목록과 프롬프트를 함께 줄여야 한다.** 3번에서 도구 목록에서 뺀 도구를 LLM이 계속 부르다 반복 한도에 걸렸는데, 원인은 매 단계 들어가는 시스템 프롬프트에 그 도구 사용법이 남아 있었기 때문이었다. 도구 안내를 단계별로 옮긴 뒤에야 분기가 설계대로 동작했다. CoALA의 행동 공간 · 작업 기억 관점으로 설명할 수 있는 실패였다.
- **8B 모델에게 "언제 끝낼지"까지 맡기기는 어렵다.** 다섯 설계 모두 내용은 잘 만들었고, 흔들린 곳은 도구로 넘겨 저장하고 일을 끝내는 마지막 단계였다. 판단을 코드로 옮길수록(3 → 4 → 5) 결과가 안정됐다.
- **같은 모델의 자기 점검은 같은 오해를 반복한다.** 쓸 때 잘못 읽은 부분을 검토할 때도 그대로 넘어갔다. 다른 근거와 맞춰 볼 수 있어야 한다.
- 이 한계에서 다음 글이 시작된다: 볼 수 있는 자료를 사내 문서까지 넓히고, 일의 순서는 코드가 정하는 **Workflow 패턴**으로.

## 예시 코드 — [local-agent_example1](https://github.com/funpinbo/local-agent_example1)

3편 전체(1~4장)의 실습 코드입니다. 보고서 Agent 하나를 장마다 다른 설계 방식으로 다시 만들고, 글에 실린 그래프 코드는 이 저장소에서 그대로 가져왔습니다. 실습 데이터(가상 회사 "놀러가자"의 메모 · 사내 문서 · 그룹웨어 기록)의 이름과 수치는 모두 지어낸 것입니다.

| 폴더 | 3편 목차 | Agent가 하는 일 | 다루는 설계 |
|---|---|---|---|
| `s1_single/` | 1. Single Agent | 메모 한 장으로 주간 · 출장 보고 docx 작성 | Tool Calling, ReAct Loop, Conditional Branch, Retry / Fallback / Stop, Reflection |
| `s2_workflow/` | 2. Workflow 패턴 | 사내 문서를 검색해 근거를 단 기술 보고서 작성 | RAG 도구만 붙인 Single Agent, Prompt Chaining, Routing, Parallelization, Orchestrator–Worker, Evaluator–Optimizer |
| `s3_multi/` | 3. Multi-Agent | 그룹웨어의 메일 · 일정 · 결재를 모아 월간 보고 작성 | 도구를 많이 붙인 Single Agent, Supervisor / Worker, Handoff, Hierarchical, Sequential / Parallel, 상태 · 결과 공유 |
| `s4_graph/` | 4. Graph 기반 Agent | 월간 보고를 만들고 사람의 승인을 받아 결재 상신 | DAG / Cyclic Graph, Dynamic Routing, Planner–Executor · Replanning, Human-in-the-loop, 전체 그래프 |

2~4장은 **"앞 장의 방식으로 먼저 만들어 보고 한계를 확인하는 실습"**(`00_...` 파일)으로 시작합니다.

**구성**

| 층 | 만든 것 |
|---|---|
| 모델 서빙 (`serving/`) | KANANA 1.5 8B를 llama.cpp로 BF16 GGUF → Q8_0 / Q4_K_M 양자화, Ollama Modelfile로 등록. 도구 호출이 되는지 확인하는 점검 스크립트(`tools/check_ollama.py`) |
| LLM 연결 (`common/llm.py`) | `KananaChatOllama` — 응답 본문의 `<function=이름>{...}</function>`을 LangChain `tool_calls`로 바꾸고, JSON이 깨진 호출은 `invalid_tool_calls`로 분리. 덕분에 LangGraph의 `ToolNode` · `tools_condition`을 그대로 사용 |
| 데이터 (`infra/msdf/`) | [MSDF](https://github.com/funpinbo/MSDF) 0.6.0 DAG — 문서 읽기 → 청킹 → BM25 색인 → 검색, 그룹웨어 메일 · 일정 · 결재 수집. 같은 입력이면 저장된 결과를 재사용하고, 원본이 바뀌면 `invalidate`로 다시 만듦 |
| 외부 시스템 (`infra/groupware/`) | 메일 · 일정 · 결재 API와 웹 화면이 있는 실습용 그룹웨어. 결재선 순서대로 승인 · 반려 가능 |
| 실습 화면 (`chat_ui/`) | 설계 방식을 골라 실행하고, 노드마다 LLM 답 · 도구 호출과 인자 · 도구 결과 · State 변화 · MSDF 요청을 시간순으로 보여 주는 웹 화면. 문서 업로드, docx 내려받기, Human-in-the-loop 승인 · 반려 버튼 |
| 공통 (`common/`) | 보고서 양식(docx 템플릿)과 칸 정의, docx 저장, 실행 로그(jsonl), 가짜 LLM |
| 테스트 | 가짜 LLM으로 그래프의 연결과 흐름만 확인 — GPU와 Ollama 없이 실행 |

**코드를 쓰면서 정한 것**

- **Agent는 데이터를 결과물 이름으로만 요청한다** (`agent.fetch("doc_search", ...)`). 문서를 어떻게 청킹 · 색인하고 그룹웨어 기록을 어떻게 모으는지는 MSDF의 DAG가 정해서, Agent 설계 코드에 데이터 처리 코드가 섞이지 않는다.
- **쓰기 작업은 데이터 엔진을 거치지 않는다.** MSDF는 같은 입력이면 저장된 결과를 돌려주기 때문에, 같은 내용의 결재 상신이 건너뛰어질 수 있다. 그래서 4장의 결재 상신만 그룹웨어 API를 직접 부른다.
- **실행 과정을 눈으로 볼 수 있게 만든다.** "LLM이 어디서 무엇을 판단했고 어디서 어긋났는지"를 보여 주는 것이 글의 핵심이라, 실행 로그와 실습 화면을 Agent 코드만큼 공들였다.
- **같은 실습을 로컬 · 원격 두 방식으로 돌릴 수 있다.** 기본은 MSDF 엔진이 Agent 프로세스 안에서 잠깐 돌고(`MSDF_MODE=local`), 원격 모드에서는 엔진과 서비스 프로세스를 따로 띄워 웹 UI에서 어떤 단계가 실행되고 캐시로 건너뛰어졌는지 확인한다.

## 다음

- 3(2): Workflow 패턴 — Single Agent에 문서 검색 도구만 붙였을 때의 문제부터 시작해, 일의 순서를 코드가 정하는 패턴들로 넘어갑니다.
- 이어서 Multi-Agent(3장), Graph 기반 Agent(4장). 예시 코드는 이미 저장소에 있습니다.

---

- [공부 기록 목록](../README.md)
