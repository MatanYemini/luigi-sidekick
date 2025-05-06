from fastapi import APIRouter, HTTPException
import subprocess
import os

from app.models.ai_models import CodexRequest, ClaudeCodeRequest, LuigiRequest
from app.utils import check_repo_exists
from app.config import REPOS_DIR

router = APIRouter()

def init_update_submodules(repo_path):
    """Initialize and update all git submodules in a repository.
    
    Args:
        repo_path: Path to the git repository
        
    Returns:
        dict: Result of the operation with status and messages
        
    Raises:
        subprocess.CalledProcessError: If git commands fail
    """
    try:
        # Initialize submodules
        subprocess.run(
            ["git", "submodule", "init"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True,
        )
        
        # Update submodules
        subprocess.run(
            ["git", "submodule", "update"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True,
        )
        
        return {
            "status": "success",
            "message": "Git submodules initialized and updated successfully"
        }
    except subprocess.CalledProcessError as e:
        return {
            "status": "error",
            "message": f"Failed to initialize or update git submodules: {e.stderr or e.stdout}"
        }

@router.post("/codex")
async def run_codex(req: CodexRequest):
    """Run OpenAI Codex CLI in full‑auto mode against a cloned repository.

    Expects:
        - repo: name of an existing directory under /repos (created via /repos/clone)
        - query: natural‑language prompt for Codex
    """
    repo_path = check_repo_exists(req.repo)

    # Initialize and update submodules before running Codex
    submodules_result = init_update_submodules(repo_path)
    if submodules_result["status"] == "error":
        print(f"Warning: {submodules_result['message']}")

    # Build the Codex CLI command: codex --approval-mode full-auto "query"
    cmd = [
        "codex",
        "-q",
        "-a",
        "full-auto",
        req.query,
    ]

    try:
        result = subprocess.run(
            cmd,
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minutes safety timeout
            check=True,
        )
        
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"Codex CLI failed: {e.stderr or e.stdout}")
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Codex CLI timed out. Try a simpler query.")

    # Return both stdout and stderr for transparency
    return {
        "status": "success",
        "stdout": result.stdout,
        "stderr": result.stderr,
    } 

@router.post("/claude-code")
async def run_claude_code(req: ClaudeCodeRequest):
    """Run Claude Code CLI in non-interactive mode against a cloned repository.
    
    Expects:
        - repo: name of an existing directory under /repos (created via /repos/clone)
        - query: natural-language prompt for Claude Code
    """
    repo_path = check_repo_exists(req.repo)
    
    # Initialize and update submodules before running Claude Code
    submodules_result = init_update_submodules(repo_path)
    if submodules_result["status"] == "error":
        print(f"Warning: {submodules_result['message']}")
    
    # Build the Claude Code command: claude -p "query" 
    # Using -p for non-interactive print mode with explicitly allowed tools
    cmd = [
        "claude",
        "-p",  # Print mode (non-interactive)
        req.query,
        "--allowedTools", 
        "Edit",           # Allow editing files
        "Bash",           # Allow running terminal commands
        "Search",         # Allow searching codebase
        "FileSearch",     # Allow file search
        "ListDir",        # Allow listing directories
        "Read",           # Allow reading files
        "Git",            # Allow git operations
    ]
    
    try:
        result = subprocess.run(
            cmd,
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minutes safety timeout
            check=True,
        )
        
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"Claude Code failed: {e.stderr or e.stdout}")
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Claude Code timed out. Try a simpler query.")
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="Claude Code CLI not found. Make sure it's installed (npm install -g @anthropic-ai/claude-code).")
    
    # Return both stdout and stderr for transparency
    return {
        "status": "success",
        "stdout": result.stdout,
        "stderr": result.stderr,
    } 

@router.post("/luigi-init")
async def generate_luigi_md(req: LuigiRequest):
    """Ensure repositories have a luigi.md file with helpful repository analysis.
    
    If no repo is specified, processes all repositories in the repos directory.
    If the file doesn't exist, create it using Claude Code analysis.
    
    Expects:
        - repo: (optional) name of an existing directory under /repos (created via /repos/clone)
                if not provided, all repositories will be processed
    """
    # Handle case where no specific repo is provided
    if req.repo is None:
        # Find all directories in the repos folder
        results = []
        
        # Check if repos directory exists
        if not os.path.exists(REPOS_DIR):
            raise HTTPException(status_code=404, detail=f"Repos directory {REPOS_DIR} not found")
            
        # List all items in the directory
        try:
            repo_names = [item for item in os.listdir(REPOS_DIR) 
                        if os.path.isdir(os.path.join(REPOS_DIR, item))]
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to list repos directory: {str(e)}")
            
        if not repo_names:
            return {
                "status": "info",
                "message": "No repositories found in the repos directory",
                "repos_processed": 0
            }
            
        # Process each repository
        for repo_name in repo_names:
            try:
                # Create a new request with the current repo name
                repo_request = LuigiRequest(repo=repo_name)
                # Process this specific repository
                result = await process_single_repo(repo_request)
                results.append({
                    "repo": repo_name,
                    "result": result
                })
            except Exception as e:
                # Log the error but continue with other repos
                results.append({
                    "repo": repo_name,
                    "error": str(e)
                })
                
        return {
            "status": "success",
            "repos_processed": len(repo_names),
            "results": results
        }
    else:
        # Process a single specified repository
        return await process_single_repo(req)

async def process_single_repo(req: LuigiRequest):
    """Process a single repository to ensure it has a luigi.md file."""
    # Get the repository path
    try:
        repo_path = check_repo_exists(req.repo)
    except HTTPException as e:
        # Return the error instead of raising it, to allow processing other repos
        return {"status": "error", "message": e.detail}
    
    # Initialize and update submodules before analyzing
    submodules_result = init_update_submodules(repo_path)
    if submodules_result["status"] == "error":
        print(f"Warning: {submodules_result['message']}")
        
    luigi_md_path = os.path.join(repo_path, "luigi.md")
    
    # Check if luigi.md already exists
    if os.path.exists(luigi_md_path):
        return {
            "status": "success",
            "message": "luigi.md already exists",
            "path": luigi_md_path
        }
    
    # Create the luigi.md file using Claude Code analysis
    template = """# Repository: [Name]

## Repository Overview
[Brief description of the repository, its purpose, and key attributes]

## Primary Functionality
[Concise description of what this codebase does]

## Business Domains
[List of business domains/concepts this repository handles]

## Key Technical Concepts
[List of important technical concepts/patterns used]

## API Surface and Interfaces
[Summary of major APIs, interfaces, or endpoints]

## Key Data Models and Entities
[List of primary data entities with brief descriptions]

## Repository Structure
[High-level directory/module organization with purpose]

## UI Components and Component Hierarchy
[For frontend codebases: description of main UI components, their relationships, and component trees]

## Common Modification Patterns
[Patterns for how the code is typically modified for feature work]

## Search Keywords for Ticket Matching
[List of unique terms, function names, and patterns that can help match JIRA tickets to this repository]
"""
    
    query = f"""Analyze this codebase and generate a 'luigi.md' file that provides a comprehensive overview of the repository.
    
The luigi.md file should follow this template:

{template}

Replace each placeholder with detailed information about this repository based on your analysis.
Be specific and detailed in your analysis, focusing on:

1. What the codebase actually does and its primary purpose
2. Key business domains and concepts represented in the code
3. Important technical patterns, frameworks, and architectures used
4. Major APIs, interfaces, and endpoints that the code exposes
5. Primary data models and entities
6. Repository structure and organization
7. If this is a frontend codebase (React, Vue, Angular, etc.), identify and document:
   - Main UI components and their purpose
   - Component hierarchies and relationships
   - Key UI patterns, hooks, or state management approaches used
8. Common patterns for modifying or extending this code
9. Unique terms and patterns that would help identify this codebase when mentioned in tickets or issues

Create the luigi.md file at the root of the repository.
"""
    
    # Build the Claude Code command
    cmd = [
        "claude",
        "-p",  # Print mode (non-interactive)
        query,
        "--allowedTools", 
        "Edit",           # Allow editing files
        "Bash",           # Allow running terminal commands
        "Search",         # Allow searching codebase
        "FileSearch",     # Allow file search
        "ListDir",        # Allow listing directories
        "Read",           # Allow reading files
    ]
    
    try:
        result = subprocess.run(
            cmd,
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minutes safety timeout
            check=True,
        )
        
    except subprocess.CalledProcessError as e:
        return {
            "status": "error",
            "message": f"Claude Code failed: {e.stderr or e.stdout}"
        }
    except subprocess.TimeoutExpired:
        return {
            "status": "error",
            "message": "Claude Code timed out. Try again with a simpler query."
        }
    except FileNotFoundError:
        return {
            "status": "error",
            "message": "Claude Code CLI not found. Make sure it's installed (npm install -g @anthropic-ai/claude-code)."
        }
    
    # Check if luigi.md was created successfully
    if os.path.exists(luigi_md_path):
        return {
            "status": "success",
            "message": "luigi.md successfully created",
            "path": luigi_md_path
        }
    else:
        return {
            "status": "error",
            "message": f"Failed to create luigi.md {result.stdout} {result.stderr}"
        } 