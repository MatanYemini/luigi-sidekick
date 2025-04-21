from fastapi import APIRouter
from app.routes.repo import router as repo_router
from app.routes.codetools import router as codetools_router
from app.routes.jira import router as jira_router

router = APIRouter()
router.include_router(repo_router)
router.include_router(codetools_router)
router.include_router(jira_router) 