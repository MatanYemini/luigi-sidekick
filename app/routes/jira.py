from fastapi import APIRouter, HTTPException, Depends
import os
from pydantic import BaseModel, Field
from typing import Dict, Optional, List, Any
from app.utils.jira import extract_issue_key_from_url, fetch_jira_issue, extract_text_from_description, check_affected_repositories

router = APIRouter(prefix="/jira", tags=["jira"])

class JiraIssueRequest(BaseModel):
    issueId: Optional[str] = Field(None, description="The Jira issue ID (e.g., 38838)")
    issueUrl: Optional[str] = Field(None, description="URL to the Jira issue")

class JiraIssueResponse(BaseModel):
    issue_id: str
    title: str
    details: str
    labels: List[str] = []
    fields: Dict[str, Any] = {}
    message: str = ""

@router.post("/issue", response_model=JiraIssueResponse)
async def get_issue_info(request: JiraIssueRequest):
    """
    Fetches issue information directly from Jira REST API
    and checks if 'Affected Repositories' field is present.
    
    Accepts either issueId or issueUrl in the request body.
    """
    # Validate that at least one of issueId or issueUrl is provided
    if not request.issueId and not request.issueUrl:
        raise HTTPException(
            status_code=400, 
            detail="Either issueId or issueUrl must be provided"
        )
    
    # Get the issue key from either issueId or issueUrl
    issue_key = request.issueId if request.issueId else extract_issue_key_from_url(request.issueUrl)
    
    try:
        # Fetch the issue data from Jira API
        issue_data = await fetch_jira_issue(issue_key)
        
        # Extract relevant information
        title = issue_data.get("fields", {}).get("summary", "No title")
        
        # Extract description text
        description_data = issue_data.get("fields", {}).get("description", "No description")
        details = extract_text_from_description(description_data)
        
        labels = issue_data.get("fields", {}).get("labels", [])
        
        # Check for "Affected Repositories" field
        affected_repos = check_affected_repositories(issue_data)
        
        # Create the response
        response = JiraIssueResponse(
            issue_id=issue_key,
            title=title,
            details=details,
            labels=labels,
            fields=issue_data.get("fields", {})
        )
        
        # Check if "Affected Repositories" field is missing
        if not affected_repos:
            response.message = "Please fill 'Affected repositories'"
        else:
            response.message = "I have enough information to work on this ticket"
            
        return response
            
    except Exception as e:
        # Re-raise exceptions from the utility functions
        raise 