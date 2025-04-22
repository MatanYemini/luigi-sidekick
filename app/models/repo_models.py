"""Models for repository operations."""

from pydantic import BaseModel, HttpUrl

class RepoRequest(BaseModel):
    url: HttpUrl 