"""Models for AI code generation services."""

from pydantic import BaseModel
from typing import Optional

class CodexRequest(BaseModel):
    repo: str  # name of the repo folder under /repos
    query: str

class ClaudeCodeRequest(BaseModel):
    repo: str  # name of the repo folder under /repos
    query: str

class LuigiRequest(BaseModel):
    repo: Optional[str] = None  # Optional name of the repo folder under /repos 