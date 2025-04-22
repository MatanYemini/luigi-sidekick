import subprocess
import os
from typing import Dict, Any
from fastapi import HTTPException

# Import from the utils package instead of the root utils.py file
from app.utils.utils import check_repo_exists

async def execute_ticket_with_claude(jira_info: Dict[str, Any], repo_name: str = None) -> Dict[str, Any]:
    """
    Execute code analysis and generation using Claude Code CLI based on Jira information.
    
    Args:
        jira_info: Dictionary containing relevant information from Jira issue
        repo_name: Optional repository name to run Claude against (must exist in REPOS_DIR)
        
    Returns:
        Dictionary containing Claude's response with generated code or analysis
    """
    # If repo_name is provided, verify it exists
    repo_path = None
    if repo_name:
        repo_path = check_repo_exists(repo_name)
    
    # Format the prompt for Claude Code CLI
    prompt = f"""
Based on this Jira ticket information, analyze the issue and implement a solution.

JIRA TICKET: {jira_info['issue_key']}
TITLE: {jira_info['title']}
DESCRIPTION:
{jira_info['description']}

{"AFFECTED REPOSITORIES: " + str(jira_info.get('affected_repositories', 'None specified'))}
{"COMPONENTS: " + ', '.join(jira_info.get('components', ['None specified']))}
{"LABELS: " + ', '.join(jira_info.get('labels', ['None']))}

{"ACCEPTANCE CRITERIA: " + jira_info.get('acceptance_criteria', 'None specified')}

## You must follow these guidelines:
1. Analyze the issue to understand the root cause
2. Develop a plan to resolve the issue
3. Implement the necessary code changes
4. If appropriate, add tests to verify the fix works
5. Run build and tests if exists in places like package.json, pyproject.toml, etc.
6. ultrathink about the code and the changes you are making, and make sure you are not missing anything
7. Remember that you are a senior software engineer, and you are writing code for a large company, so you need to follow the company's coding standards and best practices
8. Make sure to write code that is easy to understand and maintain

Focus on addressing the requirements in the ticket description and acceptance criteria.
"""
    
    # Build the Claude Code CLI command
    cmd = [
        "claude",
        "-p",  # Print mode (non-interactive)
        prompt,
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
        # Run Claude Code CLI in the specified repository directory or current directory
        result = subprocess.run(
            cmd,
            cwd=repo_path if repo_path else os.getcwd(),
            capture_output=True,
            text=True,
            timeout=600,  # 10 minutes timeout for complex issues
            check=True,
        )
        
        return {
            "status": "success",
            "analysis": result.stdout,
            "issue_key": jira_info["issue_key"],
            "title": jira_info["title"],
            "stderr": result.stderr
        }
            
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"Claude Code CLI failed: {e.stderr or e.stdout}")
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Claude Code CLI timed out. The issue may be too complex.")
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="Claude Code CLI not found. Make sure it's installed (npm install -g @anthropic-ai/claude-code).")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error executing Claude Code: {str(e)}") 