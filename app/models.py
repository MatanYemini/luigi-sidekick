from pydantic import BaseModel, HttpUrl

class RepoRequest(BaseModel):
    url: HttpUrl

class CodexRequest(BaseModel):
    repo: str  # name of the repo folder under /repos
    query: str

class ClaudeCodeRequest(BaseModel):
    repo: str  # name of the repo folder under /repos
    query: str 