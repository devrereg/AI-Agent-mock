import re
from typing import Dict, Any, Tuple

INTENT_CREATOR_SEARCH = "CREATOR_SEARCH"
INTENT_UNKNOWN = "UNKNOWN"

def detect_intent(message: str) -> Tuple[str, Dict[str, Any]]:
    """
    Simple rule-based intent detection.
    
    Args:
        message: User input message.
        
    Returns:
        Tuple of (intent_name, extracted_entities).
    """
    message_lower = message.lower()
    
    # Creator search keywords
    search_keywords = ["find", "search", "looking for", "show me"]
    creator_keywords = ["influencers", "creators", "youtubers", "instagrammers", "tiktokers"]
    
    is_search = any(k in message_lower for k in search_keywords)
    is_creator = any(k in message_lower for k in creator_keywords)
    
    if is_search and is_creator:
        entities = {}
        
        # Extract Platform
        if "instagram" in message_lower:
            entities["platform"] = "instagram"
        elif "youtube" in message_lower:
            entities["platform"] = "youtube"
        elif "tiktok" in message_lower:
            entities["platform"] = "tiktok"
        else:
            # Default or require prompt (for now let's default to none/error handling in tool)
            pass 
            
        # Extract Follower Count (Simple 'more than 10k' logic)
        # Matches "more than 10k", "over 5000", "> 10000"
        follower_pattern = r"(?:more than|over|>) (\d+(?:k|m)?)"
        match = re.search(follower_pattern, message_lower)
        if match:
            amount_str = match.group(1)
            multiplier = 1
            if 'k' in amount_str:
                multiplier = 1000
                amount_str = amount_str.replace('k', '')
            elif 'm' in amount_str:
                multiplier = 1000000
                amount_str = amount_str.replace('m', '')
            
            try:
                entities["follower_min"] = int(float(amount_str) * multiplier)
            except ValueError:
                pass
                
        return INTENT_CREATOR_SEARCH, entities
        
    return INTENT_UNKNOWN, {}
