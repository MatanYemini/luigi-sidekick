from fastapi import APIRouter, HTTPException, Depends
import subprocess
import shutil
import os
import re
from urllib.parse import urlparse

from app.models.repo_models import RepoRequest
from app.config import REPOS_DIR
from app.utils import get_repo_path

# Set MCP timeout environment variables if not already set
# These control the timeout for MCP server startup and tool execution
os.environ.setdefault("MCP_TIMEOUT", "20000000")  # 20m milliseconds for server startup
os.environ.setdefault("MCP_TOOL_TIMEOUT", "20000000")  # 20m milliseconds for tool execution

# Function to get Bitbucket credentials from environment variables
def get_bitbucket_credentials():
    """Get Bitbucket credentials from environment variables if available."""
    return {
        "username": os.environ.get("BITBUCKET_USERNAME", ""),
        "app_password": os.environ.get("BITBUCKET_APP_PASSWORD", ""),
        "token": os.environ.get("BITBUCKET_TOKEN", "")
    }

router = APIRouter(
    prefix="/repos",
    tags=["repositories"],
    responses={404: {"description": "Repository not found"}},
)

@router.post("/clone", summary="Clone a Git repository", description="Clone a Git repository, auto-detects repository type and uses environment variables for authentication")
async def clone_repo(req: RepoRequest, bitbucket_creds: dict = Depends(get_bitbucket_credentials)):
    """
    Clone a Git repository from a URL.
    
    Automatically detects if it's GitHub or Bitbucket based on the URL.
    Uses environment variables for authentication with Bitbucket.
    
    Environment variables used:
    - BITBUCKET_USERNAME - Username for Bitbucket App Password authentication
    - BITBUCKET_APP_PASSWORD - App Password for Bitbucket authentication
    - BITBUCKET_TOKEN - Repository Access Token for Bitbucket authentication (fallback)
    
    If the repository already exists, it will be removed and re-cloned.
    """
    repo_url = str(req.url)
    
    # Parse the URL to get the components
    parsed_url = urlparse(repo_url)
    
    # Extract the hostname, path, and scheme
    hostname = parsed_url.netloc
    path = parsed_url.path
    scheme = parsed_url.scheme
    
    # Auto-detect if it's a Bitbucket repository
    is_bitbucket = 'bitbucket.org' in hostname.lower()
    
    # Format URL for Bitbucket with authentication if needed
    if is_bitbucket:
        # Prioritize username + app password authentication
        if bitbucket_creds["username"] and bitbucket_creds["app_password"]:
            # Format: https://username:password@bitbucket.org/YOURREPO/YOURREPONAME.git
            repo_url = f"{scheme}://{bitbucket_creds['username']}:{bitbucket_creds['app_password']}@bitbucket.org{path}"
            print(f"Using Bitbucket App Password authentication with username: {bitbucket_creds['username']}")
            print(f"URL format: {scheme}://{bitbucket_creds['username']}:***@bitbucket.org{path}")
        elif bitbucket_creds["token"]:
            # Fallback to token if username + app password not available
            repo_url = f"{scheme}://{bitbucket_creds['token']}@bitbucket.org{path}"
            print("Using Bitbucket Repository Access Token authentication")
            print(f"URL format: {scheme}://***@bitbucket.org{path}")
        else:
            # No authentication provided, proceed with public URL (will fail if repo is private)
            print("Warning: No Bitbucket credentials found in environment variables. Attempting to clone without authentication.")
            print(f"URL format: {scheme}://bitbucket.org{path}")
    
    # Determine repo name based on repository type
    if is_bitbucket:
        # For Bitbucket: extract just the repo name (last component of the path)
        # Bitbucket path format is typically /workspace/repo_name
        path_parts = path.strip('/').split('/')
        if len(path_parts) >= 2:
            # Extract just the repository name (last component)
            repo_name = path_parts[-1].replace('.git', '')
        else:
            # Fallback if path doesn't have expected format
            repo_name = path.strip('/').replace('.git', '')
        
        print(f"Extracted Bitbucket repository name: {repo_name}")
    else:
        # For other repositories (GitHub, etc.)
        match = re.search(r'\/([^\/]+?)(\.git)?$', repo_url)
        if match:
            repo_name = match.group(1)
        else:
            # Fallback to simple splitting if regex doesn't match
            repo_name = repo_url.split('/')[-1].replace('.git', '')
    
    target_path = get_repo_path(repo_name)

    # If repo exists, remove it first
    if os.path.exists(target_path):
        shutil.rmtree(target_path)
    
    # Create parent directories if they don't exist
    os.makedirs(os.path.dirname(target_path), exist_ok=True)

    try:
        # Hide the URL in case it contains sensitive information (like tokens or passwords)
        print(f"Cloning repository from {repo_url}...")
        safe_url_for_logs = repo_url
        
        # Sanitize logs to remove sensitive information
        if is_bitbucket:
            if bitbucket_creds["app_password"]:
                safe_url_for_logs = safe_url_for_logs.replace(bitbucket_creds["app_password"], "***")
            if bitbucket_creds["token"]:
                safe_url_for_logs = safe_url_for_logs.replace(bitbucket_creds["token"], "***")
        
        print(f"Sanitized URL for logs: {safe_url_for_logs}")
        print(f"Detected repository type: {'Bitbucket' if is_bitbucket else 'GitHub/Other'}")
        
        # Run the git clone command
        result = subprocess.run(
            ["git", "clone", repo_url, target_path],
            capture_output=True,
            text=True,
            check=True
        )
        
        return {
            "status": "success", 
            "path": target_path,
            "repo_name": repo_name,
            "repo_type": "bitbucket" if is_bitbucket else "github/other"
        }
        
    except subprocess.CalledProcessError as e:
        error_output = e.stderr or e.stdout
        
        # Sanitize error output to remove sensitive information
        if is_bitbucket:
            if bitbucket_creds["app_password"]:
                error_output = error_output.replace(bitbucket_creds["app_password"], "***")
            if bitbucket_creds["token"]:
                error_output = error_output.replace(bitbucket_creds["token"], "***")
            
        raise HTTPException(
            status_code=400, 
            detail=f"Git clone failed: {error_output}"
        ) 