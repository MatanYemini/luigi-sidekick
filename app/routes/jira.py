from fastapi import APIRouter, HTTPException
import os
from typing import Dict, Any

# Import models
from app.models.jira_models import (
    JiraIssueRequest,
    JiraExecuteRequest,
    JiraIssueResponse,
    JiraExecuteResponse
)

# Import utility functions
from app.utils import (
    extract_issue_key_from_url,
    fetch_jira_issue,
    extract_text_from_description,
    check_affected_repositories,
    extract_programming_info,
    execute_ticket_with_claude
)

# Create the router
router = APIRouter(prefix="/jira", tags=["jira"])

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

@router.post("/execute", response_model=JiraExecuteResponse)
async def execute_jira_issue(request: JiraExecuteRequest):
    """
    Executes the following steps:
    1. Get the JIRA ticket information
    2. Extract the relevant affected repositories
    3. Extract programming-relevant information
    4. Execute code generation/analysis using Claude Code CLI
    
    Accepts either issueId or issueUrl in the request body.
    
    Optionally accepts a repository name to run Claude against.
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
        # Step 1: Fetch the JIRA ticket information
        issue_data = await fetch_jira_issue(issue_key)
        
        # Step 2 & 3: Extract programming-relevant information (including affected repositories)
        programming_info = extract_programming_info(issue_data)
        
        # Check if affected repositories information is available
        if not programming_info.get("affected_repositories"):
            # We can still proceed, but with a warning
            print(f"Warning: No affected repositories found for issue {issue_key} - currently will not run the code at all")
            raise HTTPException(status_code=400, detail="No affected repositories found for this issue")
        
        # Step 4: Execute code generation/analysis using Claude Code CLI
        claude_response = await execute_ticket_with_claude(programming_info, request.repository)
        
        # Create the response
        response = JiraExecuteResponse(
            issue_key=issue_key,
            title=programming_info["title"],
            analysis=claude_response["analysis"],
            status=claude_response["status"],
            affected_repositories=programming_info.get("affected_repositories"),
            stderr=claude_response.get("stderr")
        )
        
        return response
        
    except Exception as e:
        # Re-raise exceptions from the utility functions
        raise 