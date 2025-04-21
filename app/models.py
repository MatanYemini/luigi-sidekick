from pydantic import BaseModel, HttpUrl
from typing import Optional

class RepoRequest(BaseModel):
    url: HttpUrl

class CodexRequest(BaseModel):
    repo: str  # name of the repo folder under /repos
    query: str

class ClaudeCodeRequest(BaseModel):
    repo: str  # name of the repo folder under /repos
    query: str

class LuigiRequest(BaseModel):
    repo: Optional[str] = None  # Optional name of the repo folder under /repos 