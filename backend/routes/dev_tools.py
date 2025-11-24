"""
Dev Tools Router

FastAPI endpoints for offline debugging assistant.
Provides code quality checks and LLM-powered issue explanations.
"""

import logging
import time
from pathlib import Path
from typing import Dict, Any
from fastapi import APIRouter, HTTPException
from backend.devtools.models import (
    RunChecksResponse,
    ExplainRequest,
    ExplainResponse,
    CodeIssue
)
from backend.devtools.runner import CheckRunner, get_code_snippet
from backend.devtools.llm_explainer import LLMExplainer
from backend.config import env_str

logger = logging.getLogger("owlin.routes.dev_tools")
router = APIRouter(prefix="/api/dev", tags=["dev-tools"])

# Initialize components (lazy loading for performance)
_check_runner: CheckRunner | None = None
_llm_explainer: LLMExplainer | None = None


def _get_check_runner() -> CheckRunner:
    """Get or create CheckRunner instance."""
    global _check_runner
    if _check_runner is None:
        # Get repository root (backend/routes/dev_tools.py -> repo root is 2 levels up)
        repo_root = Path(__file__).resolve().parent.parent.parent
        _check_runner = CheckRunner(repo_root)
    return _check_runner


def _get_llm_explainer() -> LLMExplainer:
    """Get or create LLMExplainer instance."""
    global _llm_explainer
    if _llm_explainer is None:
        ollama_url = env_str("OLLAMA_URL", "http://localhost:11434")
        _llm_explainer = LLMExplainer(ollama_url)
    return _llm_explainer


@router.get("/run_checks", response_model=RunChecksResponse)
async def run_checks() -> RunChecksResponse:
    """
    Run all local code quality checks (linting, type checking, etc.).
    
    Returns structured list of issues found in the codebase.
    All tools run locally without external API calls.
    
    Supported tools:
    - Python: MyPy, Ruff, Pytest
    - TypeScript: tsc, ESLint
    """
    start_time = time.time()
    
    try:
        logger.info("Starting code quality checks...")
        
        runner = _get_check_runner()
        issues, errors = runner.run_all_checks()
        
        # Calculate statistics
        by_severity: Dict[str, int] = {}
        by_tool: Dict[str, int] = {}
        
        for issue in issues:
            # Count by severity
            by_severity[issue.severity] = by_severity.get(issue.severity, 0) + 1
            # Count by tool
            by_tool[issue.tool] = by_tool.get(issue.tool, 0) + 1
        
        execution_time = time.time() - start_time
        
        logger.info(f"Checks completed in {execution_time:.2f}s: {len(issues)} issues, {len(errors)} errors")
        
        return RunChecksResponse(
            ok=True,
            issues=issues,
            total_count=len(issues),
            by_severity=by_severity,
            by_tool=by_tool,
            execution_time=execution_time,
            errors=errors
        )
        
    except Exception as e:
        logger.error(f"Failed to run checks: {e}")
        execution_time = time.time() - start_time
        
        return RunChecksResponse(
            ok=False,
            issues=[],
            total_count=0,
            by_severity={},
            by_tool={},
            execution_time=execution_time,
            errors=[f"Check runner failed: {str(e)}"]
        )


@router.post("/llm/explain", response_model=ExplainResponse)
async def explain_issue(request: ExplainRequest) -> ExplainResponse:
    """
    Generate LLM-powered explanation for a code issue.
    
    Uses Ollama (if available) or deterministic template fallbacks.
    Returns plain English explanation, technical cause, fix suggestions,
    and a ready-to-copy Cursor AI prompt.
    
    All processing is done locally without external API calls.
    """
    try:
        logger.info(f"Explaining issue {request.issue_id} in {request.file_path}")
        
        explainer = _get_llm_explainer()
        
        # Generate explanation
        explanation = explainer.explain_issue(
            issue_id=request.issue_id,
            tool=request.tool,
            file_path=request.file_path,
            error_snippet=request.error_snippet,
            code_region=request.code_region,
            line_number=request.line_number
        )
        
        logger.info(f"Generated explanation using {explanation.generation_method}")
        
        return ExplainResponse(
            ok=True,
            explanation=explanation,
            error=None
        )
        
    except Exception as e:
        logger.error(f"Failed to explain issue: {e}")
        
        return ExplainResponse(
            ok=False,
            explanation=None,
            error=f"Explanation generation failed: {str(e)}"
        )


@router.get("/status")
async def dev_tools_status() -> Dict[str, Any]:
    """
    Get status of dev tools system.
    
    Returns information about available tools and LLM status.
    """
    try:
        explainer = _get_llm_explainer()
        
        return {
            "status": "ok",
            "ollama_available": explainer.ollama_available,
            "ollama_url": explainer.ollama_url,
            "tools_available": {
                "mypy": True,  # Assume available, will error if not
                "ruff": True,
                "pytest": True,
                "tsc": True,
                "eslint": True
            },
            "fallback_mode": not explainer.ollama_available
        }
        
    except Exception as e:
        logger.error(f"Failed to get dev tools status: {e}")
        
        return {
            "status": "error",
            "error": str(e),
            "ollama_available": False,
            "fallback_mode": True
        }


@router.get("/issue/{issue_id}/snippet")
async def get_issue_snippet(issue_id: str) -> Dict[str, Any]:
    """
    Get code snippet for a specific issue.
    
    This is a helper endpoint to fetch code context after issues are detected.
    """
    try:
        # This would typically fetch from a cache of previously detected issues
        # For now, return a placeholder response
        
        return {
            "issue_id": issue_id,
            "snippet": "# Code snippet would be retrieved here",
            "context_lines": 5
        }
        
    except Exception as e:
        logger.error(f"Failed to get snippet for issue {issue_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

