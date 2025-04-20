from fastapi import APIRouter, HTTPException
import subprocess
import shutil
import os

from app.models import RepoRequest
from app.config import REPOS_DIR
from app.utils import get_repo_path

router = APIRouter()

@router.post("/clone")
async def clone_repo(req: RepoRequest):
    repo_url = str(req.url)
    repo_name = repo_url.split('/')[-1].replace('.git', '')
    target_path = get_repo_path(repo_name)

    # If repo exists, remove it first (optional behavior)
    if os.path.exists(target_path):
        shutil.rmtree(target_path)

    try:
        subprocess.check_output(["git", "clone", repo_url, target_path], stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=400, detail=f"Git clone failed: {e.output.decode()}")

    return {"status": "success", "path": target_path} 