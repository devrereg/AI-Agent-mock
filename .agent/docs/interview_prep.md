# 면접 대비 — 자연어 처리 에이전트(Wenoa Agent) Q&A 정리

> 대상 코드: `app/agent/`, `app/api/chat.py`, `app/tools/`, `app/schemas/chat.py`, `app/core/`, `app/utils/jwt_utils.py`
> 핵심 스택: FastAPI + LangGraph + LangChain(OpenAI) + httpx

---

## 0. 한 줄 요약

FastAPI `/chat`, `/chat/stream` 엔드포인트가 사용자 자연어 메시지를 받아 LangGraph `StateGraph`(agent ↔ tools 루프)에 전달하고, OpenAI 모델이 Function Calling으로 YouTube/Instagram/TikTok 크리에이터 검색 도구를 스스로 선택·호출한 뒤, 그 결과를 다시 자연어로 요약해 응답한다. 규칙 기반 정규식 파서 대신 **LLM의 tool-calling에 의도 파악과 파라미터 추출을 위임**한 것이 설계의 핵심.

---

## 1. 전체 아키텍처

**Q. 이 프로젝트의 자연어 처리 로직을 설명해주세요.**

**A.** 요청 흐름은 다음과 같다.

```
[Client] --POST /chat--> [chat.py] --JWT 검증/토큰 컨텍스트 저장--> [agent.py: process_message]
        --> LangGraph StateGraph(agent → tools → agent → END) 실행
        --> agent 노드: LLM이 자연어 → tool_call(JSON) 생성 or 바로 답변
        --> tools 노드: 실제 백엔드 API(httpx) 호출, 결과를 ToolMessage로 반환
        --> agent 노드가 결과를 자연어로 요약 --> ChatResponse 반환
```

- 엔드포인트: [app/api/chat.py](../../app/api/chat.py)
- 그래프 정의: [app/agent/agent.py](../../app/agent/agent.py)
- 노드 구현: [app/agent/nodes.py](../../app/agent/nodes.py)
- State 정의: [app/agent/state.py](../../app/agent/state.py)
- 도구 정의: [app/tools/](../../app/tools/)

---

## 2. LangGraph를 선택한 이유

**Q. 왜 단순 OpenAI Function Calling API 직접 호출이 아니라 LangGraph를 도입했나요?**

**A.** 두 가지 이유.
1. **멀티턴 루프**가 필요했다. "도구 호출 → 결과를 다시 LLM에 전달 → 최종 답변 생성"을 `agent → tools → agent → END` 그래프의 조건부 엣지로 표현할 수 있다([agent.py:26-34](../../app/agent/agent.py#L26-L34)).
2. **체크포인터(MemorySaver)** 하나만 붙이면 `thread_id`(user_id) 단위로 대화 히스토리가 자동 저장·복원되어, 세션 관리 로직을 직접 짤 필요가 없다.

```python
workflow.add_conditional_edges(
    "agent",
    lambda x: "tools" if x["messages"][-1].tool_calls else END,
    {"tools": "tools", END: END}
)
```

---

## 3. State (LangGraph 상태 관리)

**Q. `AgentState`는 무엇이고 왜 필요한가요?**

**A.** [state.py](../../app/agent/state.py)는 LangGraph 제공 `MessagesState`를 상속만 한다.

```python
class AgentState(MessagesState):
    pass
```

`MessagesState`는 `messages: Annotated[list[AnyMessage], add_messages]` 필드를 가지며, 이 프로젝트는 대화 히스토리 외에 추가로 추적할 상태가 없어 필드를 더 얹지 않았다. 모든 노드는 이 State를 입출력 단위로 공유한다.

**Q. `call_model`은 `{"messages": [response]}` 한 개만 반환하는데 기존 히스토리가 안 사라지는 이유는?**

**A.** `messages` 필드가 `add_messages` reducer로 선언돼 있어서, LangGraph가 노드의 반환값을 **덮어쓰기가 아니라 append**로 병합한다. 노드는 "새로 추가된 메시지"만 반환하면 되고 reducer가 누적을 책임진다. (reducer를 지정하지 않으면 기본 동작은 덮어쓰기.)

**Q. 조건부 분기는 State의 어떤 값을 보고 판단하나요?**

**A.** `x["messages"][-1].tool_calls` — 방금 `agent` 노드가 만든 **마지막 메시지**에 tool_call이 있는지를 본다. 라우팅 자체가 State 스냅샷에 대한 순수 함수(lambda)로 표현된다.

**Q. 대화가 끝난 뒤 State는 어디에 저장되나요? 프로덕션에 적합한가요?**

**A.** `MemorySaver` 체크포인터가 `thread_id`별로 스냅샷을 저장한다([agent.py:36](../../app/agent/agent.py#L36)). 다음 요청 시 `aget_state`로 기존 `messages` 유무를 확인해 시스템 프롬프트 재주입 여부를 결정한다([agent.py:52-58](../../app/agent/agent.py#L52-L58)).
**한계**: `MemorySaver`는 프로세스 인메모리라 (1) 재시작 시 소실, (2) 다중 인스턴스 환경에서 같은 user의 요청이 다른 인스턴스로 가면 히스토리 단절. → Postgres/Redis 기반 체크포인터로 교체 필요.

**Q. 대화가 길어지면 State는 어떻게 되나요?**

**A.** `add_messages`는 계속 append만 하므로 `messages` 리스트가 무한정 커진다. 매 턴 전체 히스토리를 LLM에 다시 넣어야 해서 토큰 비용·지연시간이 계속 증가하고 결국 컨텍스트 윈도우 한계에 부딪힌다. 현재 트리밍/요약 로직 없음 → `trim_messages`나 요약 노드 추가가 개선안.

**Q. `state.py`에 `TypedDict`, `Annotated`, `operator` 등 안 쓰이는 import가 있는데 왜 남아있나요?**

**A.** 확장을 염두에 둔 스캐폴딩(예: `search_filters`, `last_platform` 같은 커스텀 필드 추가 대비)이었지만 현재는 `messages` 하나로 충분해 정리되지 않은 죽은 코드. 정직하게 지적하고 정리 계획을 답하는 게 좋음.

---

## 4. 인텐트(의도) 판별

**Q. 사용자 의도는 어떻게 분류하나요?**

**A.** 두 레이어가 공존한다.
- **실동작**: LLM이 시스템 프롬프트+tool 스키마를 보고 스스로 도구 호출 여부 결정. `process_message`는 응답 후 `tool_was_used` 여부만으로 사후에 `CREATOR_SEARCH`/`CHAT` 라벨링([agent.py:74-75](../../app/agent/agent.py#L74-L75)).
- **보조/레거시**: [intent.py](../../app/agent/intent.py)에 키워드+정규식 룰(`find/search` + `creators/influencers`, `more than 10k` 파싱)이 있지만 메인 플로우에서 호출되지 않고, `fallback.py`가 `INTENT_UNKNOWN` 상수만 참조.

**꼬리질문 — "intent.py는 죽은 코드 아닌가요?"**
→ LLM 라우팅 전환 이전의 MVP 룰 기반 파서 잔재. 제거하거나, "LLM 호출 전 저비용 사전 필터"로 재활용하는 두 방향을 답할 수 있어야 함.

---

## 5. 파라미터(엔티티) 추출

**Q. "구독자 1만 이상 뷰티 유튜버 찾아줘"에서 구조화된 조건은 어떻게 뽑나요?**

**A.** 정규식이 아니라 LLM이 직접 뽑는다. `@tool` 데코레이터가 함수 시그니처+docstring을 OpenAI function schema로 변환하고, LLM이 `subscriber_min`, `categories`, `country_code_list` 등을 채워 호출한다. 카테고리 매핑표(뷰티=1, 패션=2…)를 docstring에 명시해 LLM이 정확한 ID로 매핑하도록 유도([youtube.py:45-51](../../app/tools/youtube.py#L45-L51)).

---

## 6. Agent 응답 → 실제 서비스 기능 호출 연결

**Q. LLM의 판단이 실제 백엔드 API 호출로 어떻게 이어지나요?**

**A.** 4단계.

1. **스키마 바인딩**: `llm.bind_tools(tools)`([nodes.py:18-23](../../app/agent/nodes.py#L18-L23))로 등록된 도구들의 함수 시그니처/docstring을 OpenAI function-calling 스키마로 매 요청 LLM에 함께 전달. 등록은 [tool_registry.py](../../app/tools/tool_registry.py)가 이름→함수 맵으로 관리.
2. **자연어 → 구조화 호출 의도**: `call_model`이 `llm_with_tools.invoke(messages)` 호출 시, LLM은 직접 실행하지 않고 `{"name": "search_youtube_creators", "args": {...}}` 형태의 `tool_calls` JSON만 반환. 아직 실제 API 미호출.
3. **조건부 라우팅 → 실제 실행**: `tool_calls` 존재 시 `tools` 노드(`ToolNode(tools)`, [nodes.py:35](../../app/agent/nodes.py#L35))로 분기, 이 시점에 비로소 매칭되는 파이썬 함수(`youtube.py` 등)가 실행되며 `httpx.AsyncClient`로 `settings.WENOA_BACKEND_URL`에 실제 HTTP 요청([youtube.py:87-99](../../app/tools/youtube.py#L87-L99)). 인증 토큰은 LLM 인자에 섞지 않고 `ContextVar`(`user_token_var`)에서 직접 꺼내 헤더에 부착([youtube.py:82-85](../../app/tools/youtube.py#L82-L85)) — LLM이 JWT를 다루지 않도록 분리.
4. **결과 → 자연어 재변환**: 백엔드 응답이 `ToolMessage`로 State에 append되고 `tools → agent` 엣지로 다시 `call_model` 호출. `tool_calls`가 더 없으면 `END`로 빠져 `last_message.content`가 최종 응답.

**핵심 포인트**: "자연어 → 함수 인자 추출"은 LLM이, "함수 인자 → 실제 서비스 호출"은 LangGraph `ToolNode`가 사전에 정의된 파이썬 함수를 실행하는 방식으로 역할이 분리되어 있다. LLM은 절대 직접 HTTP 요청을 만들지 않는다 — 이게 핵심 안전장치.

---

## 7. 대화 세션 / Thread 관리

**Q. 멀티턴 대화 맥락은 어떻게 유지되나요?**

**A.** `config={"configurable": {"thread_id": user_id}}`로 그래프를 호출하면 `MemorySaver`가 같은 `thread_id`의 기존 메시지 히스토리를 자동으로 이어붙인다. 최초 요청일 때만 시스템 프롬프트를 주입([agent.py:52-58](../../app/agent/agent.py#L52-L58)).

---

## 8. 스트리밍(SSE) 구현

**Q. 실시간 타이핑처럼 응답이 나오는 건 어떻게 구현했나요?**

**A.** `app_graph.astream_events(..., version="v2")`로 그래프 내부 이벤트를 구독. `on_chat_model_stream` 이벤트에서 토큰 delta를 SSE(`data: {...}\n\n`)로 스트리밍하고, `on_tool_start`는 별도 타입으로 전달해 프론트가 "검색 중..." 상태를 표시할 수 있게 함([agent.py:131-151](../../app/agent/agent.py#L131-L151)).

---

## 9. 인증 / 사용자 컨텍스트 전파

**Q. tool 함수 안에서 인증 토큰은 어떻게 쓰이나요? 함수 인자로 넘기지 않던데요.**

**A.** `ContextVar`(`user_token_var`, [context.py](../../app/core/context.py))를 사용. 요청 시작 시 `chat.py`가 `user_token_var.set(token)`으로 현재 요청의 JWT를 저장하고, LLM이 생성한 tool_call 인자와 무관하게 tool 함수 내부에서 `user_token_var.get()`으로 꺼내 `Authorization: Bearer` 헤더에 부착. LLM이 토큰을 다루지 않게 하려는 설계.

**꼬리질문 — "asyncio 환경에서 ContextVar가 요청 간 섞일 위험은?"**
→ `ContextVar`는 asyncio Task 단위로 격리되므로 FastAPI가 요청마다 별도 Task로 처리하는 한 안전. 다만 코드 내에서 명시적으로 `asyncio.create_task`를 띄우면 컨텍스트가 복사되지 않을 수 있어 주의 필요.

---

## 10. 알려진 약점 / 개선점 총정리 (꼬리질문 대비)

| 항목 | 문제 | 개선 방향 |
|---|---|---|
| JWT 실패 처리 | [jwt_utils.py:21-26](../../app/utils/jwt_utils.py#L21-L26) `decode_access_token`이 `JWTError` 시 예외 대신 `None` 반환 → `chat.py`에서 `current_user.get("id")` 호출 시 401이 아니라 `AttributeError`로 500 에러 발생 | 실패 시 `HTTPException(401)` 직접 raise, 또는 `get_current_user` 패턴으로 통일 |
| MemorySaver | 인메모리라 재시작/다중 인스턴스 환경에서 히스토리 소실·단절 | Postgres/Redis 기반 체크포인터로 교체 |
| 메시지 무한 누적 | 대화가 길어질수록 토큰 비용·지연시간 증가, 컨텍스트 윈도우 한계 | 트리밍(`trim_messages`) 또는 요약 노드 추가 |
| intent.py 이원화 | 룰 기반 파서가 메인 플로우에서 미사용, `fallback.py`만 참조 | 제거하거나 LLM 호출 전 저비용 사전 필터로 재활용 |
| state.py 미사용 import | 확장 스캐폴딩이 정리 안 된 채 남음 | 코드 정리 |
| 에러 메시지 노출 | `str(e)`를 그대로 사용자에게 반환([agent.py:94-96](../../app/agent/agent.py#L94-L96)) | 프로덕션에서는 일반화된 메시지로 감싸고 상세는 서버 로그로만 |
| 프롬프트 인젝션 방어 | 시스템 프롬프트 수준의 가드레일만 존재, 입력 새니타이징/출력 필터링 없음 | 도구 파라미터 서버사이드 검증(화이트리스트, 음수 방지 등) 추가 |
| temperature=0 | 구조화된 tool_call 추출의 결정성 확보 목적([nodes.py:14](../../app/agent/nodes.py#L14)) | 트레이드오프: 일반 대화 응답의 자연스러움은 다소 저하될 수 있음 |

---

## 11. 예상 한 줄 정리 답변 (엘리베이터 피치)

> "사용자 자연어 요청을 FastAPI가 받아 LangGraph 기반 에이전트에 전달하고, OpenAI 모델이 Function Calling으로 의도와 파라미터를 구조화한 뒤 LangGraph의 ToolNode가 실제 백엔드 API를 호출합니다. 결과는 다시 LLM이 자연어로 요약해 응답하고, thread_id 기반 체크포인터로 멀티턴 대화 맥락을 유지합니다. 인증 토큰은 LLM 파라미터와 분리해 ContextVar로 전달해 보안을 분리했습니다."
