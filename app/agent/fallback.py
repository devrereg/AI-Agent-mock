from app.schemas.chat import ChatResponse
from app.agent.intent import INTENT_UNKNOWN

def get_fallback_response() -> ChatResponse:
    """
    Returns the standard fallback response when intent is not understood.
    """
    return ChatResponse(
        answer="I can help you find creators on Instagram, YouTube, and TikTok using custom filters. For example, try 'Find beauty influencers on Instagram with more than 10k followers'.",
        intent=INTENT_UNKNOWN
    )
