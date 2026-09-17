from typing import Callable, Dict, Any
from app.tools.creator_search import search_creators
from app.tools.youtube import search_youtube_creators
from app.tools.tiktok import search_tiktok_creators
from app.tools.instagram import search_instagram_creators

class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, Callable] = {}
        self._register_defaults()
        
    def _register_defaults(self):
        self.register("search_creators", search_creators) # Mock tool
        self.register("search_youtube_creators", search_youtube_creators)
        self.register("search_tiktok_creators", search_tiktok_creators)
        self.register("search_instagram_creators", search_instagram_creators)
        
    def register(self, name: str, func: Callable):
        self._tools[name] = func
        
    def get_tool(self, name: str) -> Callable:
        return self._tools.get(name)
        
    def list_tools(self) -> Dict[str, str]:
        return {name: func.__doc__.strip() if func.__doc__ else "No description" for name, func in self._tools.items()}
    
    def get_all_tools(self) -> list:
        return [self._tools[k] for k in self._tools]

tool_registry = ToolRegistry()
