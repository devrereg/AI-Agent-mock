from langgraph.graph import StateGraph, START, END
from langchain_core.messages import HumanMessage, SystemMessage
from app.agent.state import AgentState
from app.agent.nodes import call_model, tool_node
from app.schemas.chat import ChatRequest, ChatResponse
from app.agent.fallback import get_fallback_response
from app.core.config import settings
import os

SYSTEM_PROMPT = (
    "You are a helpful AI assistant for a marketing agency. "
    "Your goal is to help users find creators on YouTube, Instagram, and TikTok. "
    "You can search for creators using the available tools. "
    "If a user asks for something outside of creator search or general chat, kindly guide them back to finding creators. "
    "Always answer in the same language as the user's message."
)

from langgraph.checkpoint.memory import MemorySaver

# Define the graph
workflow = StateGraph(AgentState)
workflow.add_node("agent", call_model)
workflow.add_node("tools", tool_node)

workflow.add_edge(START, "agent")
workflow.add_conditional_edges(
    "agent",
    lambda x: "tools" if x["messages"][-1].tool_calls else END,
    {
        "tools": "tools",
        END: END
    }
)
workflow.add_edge("tools", "agent")

checkpointer = MemorySaver()
app_graph = workflow.compile(checkpointer=checkpointer)

async def process_message(request: ChatRequest, thread_id: str = None) -> ChatResponse:
    """
    New LangGraph-based processing with memory.
    """
    if not settings.OPENAI_API_KEY:
        # Fallback if no LLM key provided
        return get_fallback_response()

    try:
        config = {"configurable": {"thread_id": thread_id}} if thread_id else None
        
        # Check if we have existing history for this thread
        start_messages = []
        if config:
            existing_state = await app_graph.aget_state(config)
            # If no existing messages (empty state), initialize with System Prompt
            if not existing_state.values or not existing_state.values.get("messages"):
                start_messages.append(SystemMessage(content=SYSTEM_PROMPT))
        else:
             start_messages.append(SystemMessage(content=SYSTEM_PROMPT))

             
        start_messages.append(HumanMessage(content=request.message))

        initial_state = {
            "messages": start_messages
        }
        
        # Invoke the graph
        final_state = await app_graph.ainvoke(initial_state, config=config)
        
        last_message = final_state["messages"][-1]
        
        # Determine intent/tool usage from history
        # Simple heuristic for MVP: If tool calls exist in history, intent was SEARCH
        tool_was_used = any(m.tool_calls for m in final_state["messages"] if hasattr(m, "tool_calls"))
        intent = "CREATOR_SEARCH" if tool_was_used else "CHAT"
        
        # Find the actual tool name used
        tool_name = None
        if tool_was_used:
            for m in final_state["messages"]:
                if hasattr(m, "tool_calls") and m.tool_calls:
                    tool_name = m.tool_calls[0]["name"]
                    break

        return ChatResponse(
            answer=last_message.content,
            intent=intent,
            tool_used=tool_name
        )
        
    except Exception as e:
        # Log error in production
        print(f"Agent Error: {e}")
        return ChatResponse(
            answer=f"I encountered an error processing your request: {str(e)}",
            intent="ERROR"
        )

from typing import AsyncGenerator
import json

async def stream_message(request: ChatRequest, thread_id: str = None) -> AsyncGenerator[str, None]:
    """
    Stream response generator using LangGraph astream_events.
    Yields SSE-compatible data chunks.
    """
    if not settings.OPENAI_API_KEY:
        yield f"data: {json.dumps({'answer': 'Error: Missing OpenAI API Key', 'type': 'error'})}\n\n"
        return

    try:
        config = {"configurable": {"thread_id": thread_id}} if thread_id else None
        
        # Check if we have existing history (reuse logic from process_message if possible, or duplicate for now due to async generator nature)
        start_messages = []
        if config:
            existing_state = await app_graph.aget_state(config)
            if not existing_state.values or not existing_state.values.get("messages"):
                start_messages.append(SystemMessage(content=SYSTEM_PROMPT))
        else:
             start_messages.append(SystemMessage(content=SYSTEM_PROMPT))
             
        start_messages.append(HumanMessage(content=request.message))

        initial_state = {
            "messages": start_messages
        }

        # Use astream_events to get granular updates
        # version="v2" is standard for LangChain > 0.2
        async for event in app_graph.astream_events(initial_state, config=config, version="v2"):
            kind = event["event"]
            
            # 1. Stream Tokens from LLM
            if kind == "on_chat_model_stream":
                content = event["data"]["chunk"].content
                if content:
                    # Yield content chunk
                    yield f"data: {json.dumps({'answer': content, 'type': 'token'})}\n\n"
            
            # 2. Monitor Tool Calls (Optional: notify client that a tool is being called)
            elif kind == "on_tool_start":
                tool_name = event["name"]
                # Filter out internal tools or wrapper names if needed, but for now send all
                yield f"data: {json.dumps({'tool': tool_name, 'type': 'tool_start'})}\n\n"
                
            # 3. Monitor Tool Output
            elif kind == "on_tool_end":
                tool_name = event["name"]
                # yield f"data: {json.dumps({'tool': tool_name, 'type': 'tool_end'})}\n\n"
                pass

        # Final Done Event
        yield "data: [DONE]\n\n"

    except Exception as e:
        print(f"Stream Error: {e}")
        yield f"data: {json.dumps({'error': str(e), 'type': 'error'})}\n\n"
