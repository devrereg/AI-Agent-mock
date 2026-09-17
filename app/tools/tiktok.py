import httpx
from typing import List, Dict, Any, Optional
from app.core.config import settings
from langchain_core.tools import tool
from app.core.context import user_token_var

@tool
async def search_tiktok_creators(
    search_key: str = "",
    follower_min: int = 0,
    follower_max: int = 0,
    q_type: str = "basic",
    sort_type: str = "basic",
    categories: List[int] = [],
    ad_view_avg_min: int = 0,
    ad_view_avg_max: int = 0,
    ad_engagement_avg_min: int = 0,
    ad_engagement_avg_max: int = 0,
    country_code_list: List[str] = [],
    lang: str = None,
    size: int = 10
) -> List[Dict[str, Any]]:
    """
    Search for TikTok creators using specific criteria.
    Use this tool when the user wants to find TikTokers or influencers on TikTok.
    
    Args:
        search_key: Keywords to search for (e.g., "dance", "comedy", nickname).
        follower_min: Minimum number of followers.
        follower_max: Maximum number of followers. Use 0 for no limit.
        q_type: Search type. 'basic' by default, 'channel' for creator name.
        sort_type: Sort order. Options:
            - 'basic': Relevance
            - 'follower_cnt': Follower count
            - 'view_avg': 3-month Avg Views
            - 'like_avg': 3-month Avg Likes
            - 'comment_avg': 3-month Avg Comments
            - 'share_avg': 3-month Avg Shares
            - 'collect_avg': 3-month Avg Saves
            - 'ad_view_avg': Ad Content 3-month Avg Views
            - 'ad_like_avg': Ad Content 3-month Avg Likes
            - 'ad_comment_avg': Ad Content 3-month Avg Comments
            - 'ad_share_avg': Ad Content 3-month Avg Shares
            - 'ad_collect_avg': Ad Content 3-month Avg Saves
        categories: List of category IDs.
            Mapping:
            1: Beauty, 2: Fashion, 3: IT/Tech, 4: Food/Mukbang, 5: Cooking,
            6: Vlog/Daily, 7: Camping, 8: Fitness, 9: Parenting/Kids, 10: Pets/Cats,
            11: Travel, 12: Game, 14: Car
            *Important*: If the user requests a category NOT in this list, do NOT use this parameter. 
            Instead, include the category name in `search_key`.
        ad_view_avg_min/max: Min/Max for Ad Avg Views.
        ad_engagement_avg_min/max: Min/Max for Ad Avg Engagement (likes+comments+shares).
        country_code_list: List of country codes (e.g., ["KR", "US"]).
        lang: Creator language code (e.g., "ko", "en").
        size: Number of creators to return (default 10). Use this if the user asks for a specific number of creators.
    """
    # Assuming the prefix is adding /tiktok based on typical REST patterns or if the user omitted it.
    # The prompt user code was `@GetMapping("/list/open")` inside a controller, likely a TikTokController.
    # I will assume the route is `/tiktok/list/open`.
    url = f"{settings.WENOA_BACKEND_URL}/api/tiktok/list"
    
    params = {
        "searchKey": search_key,
        "qType": q_type,
        "followerMin": follower_min,
        "followerMax": follower_max,
        "sortType": sort_type,
        "adViewAvgMin": ad_view_avg_min,
        "adViewAvgMax": ad_view_avg_max,
        "adEngagementAvgMin": ad_engagement_avg_min,
        "adEngagementAvgMax": ad_engagement_avg_max,
        "categories": categories,
        "countryCodeList": country_code_list,
        "lang": lang,
        "page": 1,
        "size": size
    }

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
            
            # Response: ApiPaginationResponse<TikTokListResponse>
            if data.get("code") != 200:
                return [{"error": f"API Error: {data.get('message')}"}]

            tiktok_data = data.get("data", {})
            if not tiktok_data:
                return []
                
            items = tiktok_data.get("list", [])
            
            results = []
            for item in items:
                # Map TikTokItemResponse to simplified dict
                analyze = item.get("contentsAnalyze", {})
                
                results.append({
                    "nickname": item.get("nickname"),
                    "alias": item.get("alias"),
                    "followers": item.get("followerCount"),
                    "description": item.get("description"),
                    "post_count": item.get("postCount"),
                    "avg_view": analyze.get("viewAvg"),
                    "engagement_rate": analyze.get("followerEngagement"),
                    "recent_video_thumbnail": item.get("recentContents", [{}])[0].get("thumbnail") if item.get("recentContents") else None
                })
                
            return results[:size]
            
        except httpx.HTTPError as e:
            return [{"error": f"Network error searching TikTok: {str(e)}"}]
        except Exception as e:
            return [{"error": f"Unexpected error: {str(e)}"}]
