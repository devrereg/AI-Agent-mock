from langchain_openai import ChatOpenAI
from langgraph.prebuilt import ToolNode
from app.core.config import settings
from app.tools.tool_registry import tool_registry

# Initialize LLM safely
# If no key is provided, we use a dummy one to allow app startup/testing.
# The `agent.py` checks for the key before execution.
api_key = settings.OPENAI_API_KEY or "dummy-key-for-startup"

llm = ChatOpenAI(
    model=settings.MODEL_NAME,
    api_key=api_key,
    temperature=0
)

# Bind tools to LLM
tools = [
    tool_registry.get_tool("search_youtube_creators"),
    tool_registry.get_tool("search_tiktok_creators"),
    tool_registry.get_tool("search_instagram_creators")
]
llm_with_tools = llm.bind_tools(tools)

# Define Nodes
def call_model(state):
    """
    Invokes the LLM with the current conversation history.
    """
    messages = state["messages"]
    response = llm_with_tools.invoke(messages)
    return {"messages": [response]}

# Prebuilt tool node
tool_node = ToolNode(tools)
