from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse

from app.agent.agent import process_message, stream_message
from app.schemas.chat import ChatRequest, ChatResponse
from app.utils.jwt_utils import decode_access_token, oauth2_scheme
from app.core.context import user_token_var

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(
        request: ChatRequest,
        current_user: dict = Depends(decode_access_token),
        token: str = Depends(oauth2_scheme)
):
    """
    Chat endpoint for the AI Agent.
    Receives a message and returns an intent-aware response.
    """
    # Set the token in context for tools to access
    user_token_var.set(token)
    
    user_id = str(current_user.get("id"))
    try:
        # print(f"Received request: {current_user.get('id')}")
        response = await process_message(request, thread_id=user_id)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/chat/stream")
async def chat_stream_endpoint(
        request: ChatRequest,
        current_user: dict = Depends(decode_access_token),
        token: str = Depends(oauth2_scheme)
):
    """
    Streaming Chat endpoint for the AI Agent.
    Returns Server-Sent Events (SSE).
    """
    # Set the token in context for tools to access
    user_token_var.set(token)
    
    user_id = str(current_user.get("id"))
    
    return StreamingResponse(
        stream_message(request, thread_id=user_id),
        media_type="text/event-stream"
    )
