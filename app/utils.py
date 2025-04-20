import os
import subprocess
import shutil
from fastapi import HTTPException

from app.config import REPOS_DIR

def get_repo_path(repo_name: str) -> str:
    """Get the absolute path to a repository directory."""
    return os.path.join(REPOS_DIR, repo_name)

def check_repo_exists(repo_name: str) -> str:
    """Check if a repository exists and return its path if it does."""
    repo_path = get_repo_path(repo_name)
    
    if not os.path.isdir(repo_path):
        raise HTTPException(status_code=404, detail=f"Repository '{repo_name}' not found. Please clone it first.")
    
    return repo_path 