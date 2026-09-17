import asyncio
from typing import Optional, List, Dict

async def search_creators(platform: str, follower_min: Optional[int] = None) -> List[Dict]:
    """
    Mock tool to search for creators on a specific platform.
    
    Args:
        platform: The social media platform (instagram, youtube, tiktok).
        follower_min: Minimum number of followers.
        
    Returns:
        A list of mock creator profiles.
    """
    # Simulate API latency
    await asyncio.sleep(0.5)
    
    mock_data = {
        "instagram": [
            {"name": "BeautyInfluencer1", "followers": 15000, "niche": "beauty"},
            {"name": "LifestyleGuru", "followers": 50000, "niche": "lifestyle"},
            {"name": "MicroInfluencer", "followers": 5000, "niche": "beauty"}
        ],
        "youtube": [
            {"name": "TechReviewer", "followers": 100000, "niche": "tech"},
            {"name": "VlogStar", "followers": 20000, "niche": "vlog"}
        ],
        "tiktok": [
            {"name": "DanceTrend", "followers": 500000, "niche": "dance"},
            {"name": "ComedyKing", "followers": 10000, "niche": "comedy"}
        ]
    }
    
    output = []
    platform_lower = platform.lower()
    
    if platform_lower in mock_data:
        creators = mock_data[platform_lower]
        for creator in creators:
            if follower_min is None or creator["followers"] >= follower_min:
                output.append(creator)
                
    return output
