from contextvars import ContextVar
from typing import Optional

# Context variable to store the raw Bearer token for the current request
user_token_var: ContextVar[Optional[str]] = ContextVar("user_token", default=None)
