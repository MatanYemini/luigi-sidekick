import httpx
import os
import re
from fastapi import HTTPException
from typing import Dict, List, Tuple, Any, Optional

def get_jira_credentials() -> Tuple[str, str, str]:
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

async def fetch_jira_issue(issue_key: str) -> Dict[str, Any]:
    """
    Fetch issue information from Jira REST API.
    
    Args:
        issue_key: The Jira issue key (e.g., PROJECT-123)
        
    Returns:
        The JSON response from Jira API
    """
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
            
            return response.json()
            
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Request to Jira API timed out")
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"Error connecting to Jira API: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

def extract_text_from_description(description_data: Any) -> str:
    """
    Extract text content from Jira description which may be in Atlassian Document Format (ADF).
    Ignores images and only extracts text content.
    
    Args:
        description_data: The description field from Jira API response
        
    Returns:
        Extracted text as a string
    """
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
    
    return details

def check_affected_repositories(issue_data: Dict[str, Any]) -> Optional[Any]:
    """
    Check for "Affected Repositories" field in Jira issue data.
    
    Args:
        issue_data: The JSON response from Jira API
        
    Returns:
        The value of the "Affected Repositories" field, or None if not found
    """
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
    
    return affected_repos 