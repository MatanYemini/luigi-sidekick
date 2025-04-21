from fastapi import APIRouter, HTTPException, Depends
import httpx
import os
import re
from pydantic import BaseModel, Field
from typing import Dict, Optional, List, Any

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

def get_jira_credentials():
    """
    Get Jira credentials from environment variables.
    """
    jira_base_url = os.environ.get("JIRA_BASE_URL") or os.environ.get("JIRA_URL")
    jira_email = os.environ.get("JIRA_EMAIL") or os.environ.get("JIRA_USERNAME")
    jira_api_token = os.environ.get("JIRA_API_TOKEN")
    
    if not jira_base_url or not jira_email or not jira_api_token:
        raise HTTPException(
            status_code=500, 
            detail="Missing Jira credentials in environment variables (JIRA_BASE_URL/JIRA_URL, JIRA_EMAIL/JIRA_USERNAME, JIRA_API_TOKEN)"
        )
    
    return jira_base_url, jira_email, jira_api_token

def extract_issue_key_from_url(url: str) -> str:
    """
    Extract the issue key from a Jira URL.
    Example: https://your-domain.atlassian.net/browse/PROJECT-123 -> PROJECT-123
    """
    # Match the issue key pattern at the end of the URL
    match = re.search(r'\/([A-Z]+-\d+)(?:\/|$)', url)
    if match:
        return match.group(1)
    
    raise HTTPException(status_code=400, detail="Could not extract issue key from the provided URL")

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
    
    # Get Jira credentials
    jira_base_url, jira_email, jira_api_token = get_jira_credentials()
    
    try:
        # Build the Jira REST API URL
        api_url = f"{jira_base_url.rstrip('/')}/rest/api/3/issue/{issue_key}"
        
        # Make the request to the Jira API
        async with httpx.AsyncClient() as client:
            response = await client.get(
                api_url,
                auth=(jira_email, jira_api_token),
                headers={
                    "Accept": "application/json"
                },
                timeout=10.0  # 10 second timeout
            )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code, 
                    detail=f"Error from Jira API: {response.text}"
                )
            
            issue_data = response.json()
            
            # Extract relevant information
            title = issue_data.get("fields", {}).get("summary", "No title")
            
            # Extract description - handle Atlassian Document Format (ADF)
            description_data = issue_data.get("fields", {}).get("description", "No description")
            details = "No description"
            
            # Check if description is in Atlassian Document Format
            if isinstance(description_data, dict) and description_data.get("type") == "doc":
                extracted_text = []
                
                # Process the content array
                for content_item in description_data.get("content", []):
                    # Process paragraph or other content types
                    if "content" in content_item:
                        for text_item in content_item.get("content", []):
                            # Only extract text items, skip images
                            if text_item.get("type") == "text" and "text" in text_item:
                                extracted_text.append(text_item["text"])
                
                # Join all extracted text
                if extracted_text:
                    details = " ".join(extracted_text)
            else:
                # Fallback for plain text description
                details = description_data if isinstance(description_data, str) else "No description"
            
            labels = issue_data.get("fields", {}).get("labels", [])
            
            # Check for "Affected Repositories" field
            # The field name might vary depending on your Jira setup
            # We'll check a few common variations
            affected_repos = None
            custom_fields = [field for field in issue_data.get("fields", {}) 
                            if field.startswith("customfield_")]
            
            for field in custom_fields:
                field_value = issue_data.get("fields", {}).get(field)
                # Try to check the field name
                field_meta = None
                try:
                    # If the field name is available in the response, use it
                    field_meta = issue_data.get("names", {}).get(field, "").lower()
                except:
                    # Otherwise, continue with the field value
                    pass
                
                # If the field name contains repository or affected, or the field value seems relevant
                if field_value and field_meta and ("repository" in field_meta or "affected" in field_meta):
                    affected_repos = field_value
                    break
            
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
            
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Request to Jira API timed out")
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"Error connecting to Jira API: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}") 