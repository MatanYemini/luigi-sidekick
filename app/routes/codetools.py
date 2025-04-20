from fastapi import APIRouter, HTTPException
import subprocess

from app.models import CodexRequest, ClaudeCodeRequest
from app.utils import check_repo_exists

router = APIRouter()

@router.post("/codex")
async def run_codex(req: CodexRequest):
    """Run OpenAI Codex CLI in full‑auto mode against a cloned repository.

    Expects:
        - repo: name of an existing directory under /repos (created via /clone)
        - query: natural‑language prompt for Codex
    """
    repo_path = check_repo_exists(req.repo)

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
        - repo: name of an existing directory under /repos (created via /clone)
        - query: natural-language prompt for Claude Code
    """
    repo_path = check_repo_exists(req.repo)
    
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