"""Pydantic models for Jira API integration."""

from pydantic import BaseModel, Field
from typing import Dict, Optional, List, Any

class JiraIssueRequest(BaseModel):
    issueId: Optional[str] = Field(None, description="The Jira issue ID (e.g., 38838)")
    issueUrl: Optional[str] = Field(None, description="URL to the Jira issue")

class JiraExecuteRequest(BaseModel):
    issueId: Optional[str] = Field(None, description="The Jira issue ID (e.g., 38838)")
    issueUrl: Optional[str] = Field(None, description="URL to the Jira issue")
    repository: Optional[str] = Field(None, description="Repository name to run Claude against")

class JiraIssueResponse(BaseModel):
    issue_id: str
    title: str
    details: str
    labels: List[str] = []
    fields: Dict[str, Any] = {}
    message: str = ""

class JiraExecuteResponse(BaseModel):
    issue_key: str
    title: str
    analysis: str
    status: str
    affected_repositories: Optional[Any] = None
    stderr: Optional[str] = None 