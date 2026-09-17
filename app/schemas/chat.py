from pydantic import BaseModel, Field
from typing import Optional, Any

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="The user's input message")

class ChatResponse(BaseModel):
    answer: str = Field(..., description="The agent's natural language response")
    intent: str = Field(..., description="Detected intent of the user message")
    tool_used: Optional[str] = Field(None, description="Name of the tool used, if any")
    data: Optional[Any] = Field(None, description="Structured data returned by the tool")
