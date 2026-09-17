import httpx
from typing import List, Dict, Any, Optional
from app.core.config import settings
from langchain_core.tools import tool
from app.core.context import user_token_var

@tool
async def search_instagram_creators(
    search_key: str = "",
    follower_min: int = 0,
    follower_max: int = 0,
    q_type: str = "basic",
    sort_type: str = "basic",
    categories: List[str] = [],
    ad_engagement_avg_min: int = 0,
    ad_engagement_avg_max: int = 0,
    lang: str = None,
    size: int = 10
) -> List[Dict[str, Any]]:
    """
    Search for Instagram creators using specific criteria.
    
    Args:
        search_key: Keywords to search for (e.g., "fashion", "food", account name).
        follower_min: Minimum number of followers (subscriberCount).
        follower_max: Maximum number of followers. Use 0 for no limit.
        q_type: Search type. 'basic' by default, 'channel' for exact account name.
        sort_type: Sort order. Options:
            - 'basic': Relevance
            - 'subscriber_cnt': Subscriber count
            - 'like_avg': Average likes
            - 'comment_avg': Average comments
            - 'ad_feed_like_avg': Ad Feed Avg Like
            - 'ad_feed_comment_avg': Ad Feed Avg Comment
            - 'ad_feed_follower_impact': Ad Feed Follower Impact
            - 'ad_reels_like_avg': Ad Reels Avg Like
            - 'ad_reels_comment_avg': Ad Reels Avg Comment
            - 'ad_reels_view_avg': Ad Reels Avg View
        categories: List of category Name Strings.
            Valid Values:
            '뷰티', '패션', 'IT/테크', '먹방', '요리',
            '일상/브이로그', '캠핑', '피트니스', '육아/키즈', '냥집사',
            '여행', '게임', '자동차'
            *Important*: If the user requests a category NOT in this list, do NOT use this parameter. 
            Instead, include the category name in `search_key`.
        ad_engagement_avg_min/max: Min/Max for Ad Engagement Rate.
        lang: Creator language code (e.g., "ko", "en").
        size: Number of creators to return (default 10). Use this if the user asks for a specific number of creators.
    """
    # Based on the user's manual correction for TikTok, we use /api/instagram...
    url = f"{settings.WENOA_BACKEND_URL}/api/instagram/list/v2"
    
    params = {
        "searchKey": search_key,
        "qType": q_type,
        "followerMin": follower_min,
        "followerMax": follower_max,
        "sortType": sort_type,
        "adEngagementAvgMin": ad_engagement_avg_min,
        "adEngagementAvgMax": ad_engagement_avg_max,
        "categories": categories,
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
            
            # Response: ApiPaginationResponse<InstagramListResponse>
            if data.get("code") != 200:
                return [{"error": f"API Error: {data.get('message')}"}]

            insta_data = data.get("data", {})
            if not insta_data:
                return []
                
            items = insta_data.get("list", [])
            
            results = []
            for item in items:
                # Extract relevant fields
                # postAnalyze -> feed -> normalSubscriberEngagementRate, etc.
                analyze = item.get("postAnalyze", {}).get("feed", {})
                
                results.append({
                    "name": item.get("title"), # defined in spec as full_name
                    "url": item.get("customURL"),
                    "followers": item.get("subscriberCount"),
                    "description": item.get("description"),
                    "post_count": item.get("postCount"),
                    "engagement_rate": analyze.get("normalSubscriberEngagementRate"),
                    "avg_likes": analyze.get("normalLikeAvg"),
                    "recent_post_thumbnail": item.get("recentContents", [{}])[0].get("thumbnail") if item.get("recentContents") else None
                })
                
            return results[:size]
            
        except httpx.HTTPError as e:
            return [{"error": f"Network error searching Instagram: {str(e)}"}]
        except Exception as e:
            return [{"error": f"Unexpected error: {str(e)}"}]
