"""
Devtools Models

Pydantic models for dev tool responses, issues, and explanations.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class CodeIssue(BaseModel):
    """Represents a single code issue detected by a linting/testing tool."""
    
    id: str = Field(..., description="Unique issue identifier")
    tool: str = Field(..., description="Tool that detected the issue (eslint, mypy, pytest, etc.)")
    severity: str = Field(..., description="Severity level: error, warning, info")
    file_path: str = Field(..., description="Relative file path")
    line: Optional[int] = Field(None, description="Line number where issue occurs")
    column: Optional[int] = Field(None, description="Column number")
    rule: Optional[str] = Field(None, description="Rule/check identifier")
    message: str = Field(..., description="Original error message")
    code_snippet: Optional[str] = Field(None, description="Relevant code snippet")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "eslint_1",
                "tool": "eslint",
                "severity": "error",
                "file_path": "src/components/MyComponent.tsx",
                "line": 42,
                "column": 10,
                "rule": "no-unused-vars",
                "message": "'myVar' is assigned a value but never used",
                "code_snippet": "const myVar = 123;"
            }
        }


class UnifiedDiff(BaseModel):
    """Represents a unified diff patch suggestion."""
    
    file_path: str = Field(..., description="File to be patched")
    hunks: List[str] = Field(..., description="List of diff hunks")
    patch_text: str = Field(..., description="Complete unified diff text")
    line_count: int = Field(..., description="Number of lines changed")
    
    class Config:
        json_schema_extra = {
            "example": {
                "file_path": "src/utils/helper.ts",
                "hunks": ["@@ -42,3 +42,4 @@"],
                "patch_text": "--- a/src/utils/helper.ts\n+++ b/src/utils/helper.ts\n@@ -42,3 +42,4 @@\n-const unused = 5;\n+// Removed unused variable",
                "line_count": 2
            }
        }


class IssueExplanation(BaseModel):
    """LLM-generated explanation and fix suggestion for a code issue."""
    
    issue_id: str = Field(..., description="Reference to CodeIssue.id")
    plain_english: str = Field(..., description="Plain English explanation for non-technical users")
    technical_cause: str = Field(..., description="Technical root cause analysis")
    suggested_fix: str = Field(..., description="Step-by-step fix instructions")
    unified_diff: Optional[UnifiedDiff] = Field(None, description="Proposed unified diff patch")
    cursor_prompt: str = Field(..., description="Ready-to-copy prompt for Cursor AI")
    confidence: float = Field(0.8, description="Confidence score (0.0 - 1.0)")
    generation_method: str = Field(..., description="Method used: 'ollama_llm' or 'template_fallback'")
    
    class Config:
        json_schema_extra = {
            "example": {
                "issue_id": "eslint_1",
                "plain_english": "You declared a variable called 'myVar' but never actually used it in your code.",
                "technical_cause": "ESLint rule 'no-unused-vars' detected an unused variable declaration at line 42.",
                "suggested_fix": "1. Remove the unused variable declaration\n2. Or use the variable in your code if it was meant to be used",
                "unified_diff": None,
                "cursor_prompt": "Remove unused variable 'myVar' at line 42 in src/components/MyComponent.tsx",
                "confidence": 0.95,
                "generation_method": "template_fallback"
            }
        }


class RunChecksResponse(BaseModel):
    """Response from /api/dev/run_checks endpoint."""
    
    ok: bool = Field(..., description="Whether checks completed successfully")
    issues: List[CodeIssue] = Field(default_factory=list, description="List of detected issues")
    total_count: int = Field(0, description="Total number of issues found")
    by_severity: Dict[str, int] = Field(default_factory=dict, description="Count by severity")
    by_tool: Dict[str, int] = Field(default_factory=dict, description="Count by tool")
    execution_time: float = Field(0.0, description="Time taken to run checks (seconds)")
    errors: List[str] = Field(default_factory=list, description="Any errors during execution")
    
    class Config:
        json_schema_extra = {
            "example": {
                "ok": True,
                "issues": [],
                "total_count": 0,
                "by_severity": {"error": 0, "warning": 0},
                "by_tool": {"eslint": 0, "mypy": 0},
                "execution_time": 2.5,
                "errors": []
            }
        }


class ExplainRequest(BaseModel):
    """Request for /api/dev/llm/explain endpoint."""
    
    issue_id: str = Field(..., description="ID of the issue to explain")
    file_path: str = Field(..., description="File path where issue occurs")
    error_snippet: str = Field(..., description="Error message or snippet")
    code_region: Optional[str] = Field(None, description="30-60 lines of surrounding code")
    line_number: Optional[int] = Field(None, description="Line number of the issue")
    tool: str = Field("unknown", description="Tool that reported the issue")
    
    class Config:
        json_schema_extra = {
            "example": {
                "issue_id": "mypy_1",
                "file_path": "backend/services/ocr_service.py",
                "error_snippet": "error: Incompatible types in assignment (expression has type 'str', variable has type 'int')",
                "code_region": "def process_doc(id: int):\n    id = 'abc'  # Wrong type\n    return id",
                "line_number": 42,
                "tool": "mypy"
            }
        }


class ExplainResponse(BaseModel):
    """Response from /api/dev/llm/explain endpoint."""
    
    ok: bool = Field(..., description="Whether explanation was generated successfully")
    explanation: Optional[IssueExplanation] = Field(None, description="Generated explanation")
    error: Optional[str] = Field(None, description="Error message if failed")
    
    class Config:
        json_schema_extra = {
            "example": {
                "ok": True,
                "explanation": {
                    "issue_id": "mypy_1",
                    "plain_english": "You're trying to assign a text value to a variable that expects a number.",
                    "technical_cause": "Type mismatch: variable 'id' is declared as int but assigned a str value.",
                    "suggested_fix": "Change the assignment to use an integer value instead of a string.",
                    "cursor_prompt": "Fix type error at line 42 in backend/services/ocr_service.py by using correct type",
                    "confidence": 0.9,
                    "generation_method": "template_fallback"
                },
                "error": None
            }
        }

