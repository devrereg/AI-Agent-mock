from langgraph.graph import MessagesState
from typing import TypedDict, Annotated, List, Union
from langchain_core.messages import BaseMessage
import operator

class AgentState(MessagesState):
    # Inherits 'messages' from MessagesState
    pass
