import httpx
from typing import List, Dict, Any, Optional
from app.core.config import settings
from langchain_core.tools import tool
from app.core.context import user_token_var

@tool
async def search_youtube_creators(
    search_key: str = "",
    subscriber_min: int = 0,
    subscriber_max: int = 0,
    q_type: str = "basic",
    sort_type: str = "basic",
    categories: List[int] = [],
    ad_view_avg_min: int = 0,
    ad_view_avg_max: int = 0,
    ad_comment_avg_min: int = 0,
    ad_comment_avg_max: int = 0,
    ad_like_avg_min: int = 0,
    ad_like_avg_max: int = 0,
    country_code_list: List[str] = [],
    lang: str = None,
    size: int = 10
) -> List[Dict[str, Any]]:
    """
    Search for YouTube creators using specific criteria.
    
    Args:
        search_key: Search keyword.
        subscriber_min: Min subscribers.
        subscriber_max: Max subscribers (0 for no limit).
        q_type: 'basic' (integrated search) or 'channel' (channel name search).
        sort_type: Sort order. Options:
            - 'basic': Relevance
            - 'subscriber_cnt': Subscriber count
            - 'view_avg': Average views
            - 'like_avg': Average likes
            - 'comment_avg': Average comments
            - 'ad_video_view_avg': Long-form Ad Avg View
            - 'ad_video_like_avg': Long-form Ad Avg Like
            - 'ad_video_comment_avg': Long-form Ad Avg Comment
            - 'ad_shorts_view_avg': Shorts Ad Avg View
            - 'ad_shorts_like_avg': Shorts Ad Avg Like
            - 'ad_shorts_comment_avg': Shorts Ad Avg Comment
        categories: List of category IDs.
            Mapping:
            1: Beauty, 2: Fashion, 3: IT/Tech, 4: Food/Mukbang, 5: Cooking,
            6: Vlog/Daily, 7: Camping, 8: Fitness, 9: Parenting/Kids, 10: Pets/Cats,
            11: Travel, 12: Game, 14: Car
            *Important*: If the user requests a category NOT in this list, do NOT use this parameter. 
            Instead, include the category name in `search_key`.
        ad_view_avg_min/max: Min/Max for Ad Avg Views.
        ad_comment_avg_min/max: Min/Max for Ad Avg Comments.
        ad_like_avg_min/max: Min/Max for Ad Avg Likes.
        country_code_list: List of country codes (e.g., ["KR", "US"]).
        lang: Creator language code (e.g., "ko", "en").
        size: Number of creators to return (default 10). Use this if the user asks for a specific number of creators (e.g., "Find 5 creators").
    """
    url = f"{settings.WENOA_BACKEND_URL}/api/youtube/list/v3"
    
    params = {
        "searchKey": search_key,
        "qType": q_type,
        "subscriberMin": subscriber_min,
        "subscriberMax": subscriber_max,
        "sortType": sort_type,
        "categories": categories,
        "adViewAvgMin": ad_view_avg_min,
        "adViewAvgMax": ad_view_avg_max,
        "adCommentAvgMin": ad_comment_avg_min,
        "adCommentAvgMax": ad_comment_avg_max,
        "adLikeAvgMin": ad_like_avg_min,
        "adLikeAvgMax": ad_like_avg_max,
        "countryCodeList": country_code_list,
        "lang": lang,
        "page": 1,
        "size": size
    }
    
    # ... (header logic maps to same indentation level)
    
    headers = {"Accept-Language": "en-US"}
    token = user_token_var.get()
    if token:
        headers["Authorization"] = f"Bearer {token}"

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                url, 
                params=params, 
                headers=headers,
                timeout=10.0
            )
            
            if response.status_code == 403:
                 return [{"error": "Access Denied (403). Check API permissions or parameters."}]
            
            response.raise_for_status()
            data = response.json()
            
            if data.get("code") != 200:
                return [{"error": f"API Error: {data.get('message')}"}]

            youtube_data = data.get("data", {})
            if not youtube_data:
                return []
                
            items = youtube_data.get("list", [])
            
            # Simplify for LLM consumption
            results = []
            for item in items:
                results.append({
                    "name": item.get("title"),
                    "subscribers": item.get("subscriberCount"),
                    "description": item.get("description"),
                    "url": item.get("customURL"),
                    "recent_video": item.get("recentContents", [{}])[0].get("title") if item.get("recentContents") else None
                })
                
            return results[:size] # Limit to requested size
            
        except httpx.HTTPError as e:
            return [{"error": f"Network error searching YouTube: {str(e)}"}]
        except Exception as e:
            return [{"error": f"Unexpected error: {str(e)}"}]
