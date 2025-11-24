"""
Devtools Runner

Executes local linting and testing tools to detect code issues.
All operations are offline and deterministic.
"""

import subprocess
import logging
import json
import time
import os
from typing import List, Dict, Any, Tuple
from pathlib import Path
from backend.devtools.models import CodeIssue

logger = logging.getLogger("owlin.devtools.runner")


class CheckRunner:
    """Runs local code quality checks and parses results into structured issues."""
    
    def __init__(self, repo_root: Path):
        """
        Initialize the check runner.
        
        Args:
            repo_root: Path to the repository root directory
        """
        self.repo_root = repo_root
        self.backend_dir = repo_root / "backend"
        self.frontend_dir = repo_root / "frontend_clean"
        
    def run_all_checks(self) -> Tuple[List[CodeIssue], List[str]]:
        """
        Run all available checks and return combined results.
        
        Returns:
            Tuple of (issues list, errors list)
        """
        all_issues: List[CodeIssue] = []
        all_errors: List[str] = []
        
        # Python backend checks
        if self.backend_dir.exists():
            logger.info("Running Python backend checks...")
            
            # MyPy type checking
            issues, errors = self._run_mypy()
            all_issues.extend(issues)
            all_errors.extend(errors)
            
            # Ruff linting
            issues, errors = self._run_ruff()
            all_issues.extend(issues)
            all_errors.extend(errors)
            
            # Pytest (skip tests, just check for syntax errors)
            issues, errors = self._run_pytest_collect()
            all_issues.extend(issues)
            all_errors.extend(errors)
        
        # TypeScript frontend checks
        if self.frontend_dir.exists():
            logger.info("Running TypeScript frontend checks...")
            
            # TypeScript compiler
            issues, errors = self._run_tsc()
            all_issues.extend(issues)
            all_errors.extend(errors)
            
            # ESLint
            issues, errors = self._run_eslint()
            all_issues.extend(issues)
            all_errors.extend(errors)
        
        logger.info(f"Total issues found: {len(all_issues)}")
        return all_issues, all_errors
    
    def _run_mypy(self) -> Tuple[List[CodeIssue], List[str]]:
        """Run MyPy type checker on Python code."""
        issues: List[CodeIssue] = []
        errors: List[str] = []
        
        try:
            # Run mypy with JSON output format
            result = subprocess.run(
                ["mypy", "backend", "--ignore-missing-imports", "--no-error-summary"],
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # Parse mypy output (line format: file.py:line:col: error: message)
            for line in result.stdout.splitlines():
                if ": error:" in line or ": warning:" in line:
                    try:
                        parts = line.split(":", 4)
                        if len(parts) >= 5:
                            file_path = parts[0].strip()
                            line_num = int(parts[1].strip()) if parts[1].strip().isdigit() else None
                            col_num = int(parts[2].strip()) if parts[2].strip().isdigit() else None
                            severity = parts[3].strip()  # "error" or "warning"
                            message = parts[4].strip()
                            
                            issue_id = f"mypy_{len(issues) + 1}"
                            issues.append(CodeIssue(
                                id=issue_id,
                                tool="mypy",
                                severity=severity,
                                file_path=file_path,
                                line=line_num,
                                column=col_num,
                                rule="type-check",
                                message=message
                            ))
                    except Exception as e:
                        logger.warning(f"Failed to parse mypy line: {line} - {e}")
            
            logger.info(f"MyPy found {len(issues)} issues")
            
        except FileNotFoundError:
            errors.append("MyPy not found. Install with: pip install mypy")
        except subprocess.TimeoutExpired:
            errors.append("MyPy check timed out after 30 seconds")
        except Exception as e:
            errors.append(f"MyPy check failed: {str(e)}")
        
        return issues, errors
    
    def _run_ruff(self) -> Tuple[List[CodeIssue], List[str]]:
        """Run Ruff linter on Python code."""
        issues: List[CodeIssue] = []
        errors: List[str] = []
        
        try:
            # Run ruff with JSON output format
            result = subprocess.run(
                ["ruff", "check", "backend", "--output-format=json"],
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # Parse JSON output
            if result.stdout.strip():
                try:
                    ruff_results = json.loads(result.stdout)
                    for item in ruff_results:
                        issue_id = f"ruff_{len(issues) + 1}"
                        issues.append(CodeIssue(
                            id=issue_id,
                            tool="ruff",
                            severity="error" if item.get("type") == "error" else "warning",
                            file_path=item.get("filename", "unknown"),
                            line=item.get("location", {}).get("row"),
                            column=item.get("location", {}).get("column"),
                            rule=item.get("code"),
                            message=item.get("message", "")
                        ))
                except json.JSONDecodeError:
                    logger.warning("Failed to parse Ruff JSON output")
            
            logger.info(f"Ruff found {len(issues)} issues")
            
        except FileNotFoundError:
            errors.append("Ruff not found. Install with: pip install ruff")
        except subprocess.TimeoutExpired:
            errors.append("Ruff check timed out after 30 seconds")
        except Exception as e:
            errors.append(f"Ruff check failed: {str(e)}")
        
        return issues, errors
    
    def _run_pytest_collect(self) -> Tuple[List[CodeIssue], List[str]]:
        """Run pytest --collect-only to check for syntax errors."""
        issues: List[CodeIssue] = []
        errors: List[str] = []
        
        try:
            # Run pytest collection only (doesn't run tests, just imports)
            result = subprocess.run(
                ["pytest", "--collect-only", "-q", "backend"],
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # Parse stderr for syntax errors
            if result.returncode != 0 and result.stderr:
                for line in result.stderr.splitlines():
                    if "SyntaxError" in line or "ImportError" in line:
                        issue_id = f"pytest_{len(issues) + 1}"
                        issues.append(CodeIssue(
                            id=issue_id,
                            tool="pytest",
                            severity="error",
                            file_path="backend/",
                            line=None,
                            column=None,
                            rule="syntax-error",
                            message=line.strip()
                        ))
            
            logger.info(f"Pytest collect found {len(issues)} issues")
            
        except FileNotFoundError:
            errors.append("Pytest not found. Install with: pip install pytest")
        except subprocess.TimeoutExpired:
            errors.append("Pytest check timed out after 30 seconds")
        except Exception as e:
            errors.append(f"Pytest check failed: {str(e)}")
        
        return issues, errors
    
    def _run_tsc(self) -> Tuple[List[CodeIssue], List[str]]:
        """Run TypeScript compiler check."""
        issues: List[CodeIssue] = []
        errors: List[str] = []
        
        try:
            # Run tsc --noEmit to check for type errors without generating files
            result = subprocess.run(
                ["npx", "tsc", "--noEmit", "--pretty", "false"],
                cwd=self.frontend_dir,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            # Parse TypeScript errors (format: file.ts(line,col): error TS####: message)
            for line in result.stdout.splitlines():
                if "): error TS" in line:
                    try:
                        # Example: src/App.tsx(12,5): error TS2322: Type 'string' is not assignable to type 'number'.
                        parts = line.split("): error TS", 1)
                        if len(parts) == 2:
                            location_part = parts[0]
                            error_part = parts[1]
                            
                            # Extract file and position
                            file_and_pos = location_part.rsplit("(", 1)
                            file_path = file_and_pos[0].strip() if len(file_and_pos) == 2 else location_part
                            
                            # Extract line and column
                            line_num = None
                            col_num = None
                            if len(file_and_pos) == 2:
                                pos_str = file_and_pos[1]
                                if "," in pos_str:
                                    line_str, col_str = pos_str.split(",", 1)
                                    line_num = int(line_str.strip()) if line_str.strip().isdigit() else None
                                    col_num = int(col_str.strip()) if col_str.strip().isdigit() else None
                            
                            # Extract error code and message
                            error_code = error_part.split(":", 1)[0].strip()
                            message = error_part.split(":", 1)[1].strip() if ":" in error_part else error_part
                            
                            issue_id = f"tsc_{len(issues) + 1}"
                            issues.append(CodeIssue(
                                id=issue_id,
                                tool="tsc",
                                severity="error",
                                file_path=f"frontend_clean/{file_path}",
                                line=line_num,
                                column=col_num,
                                rule=f"TS{error_code}",
                                message=message
                            ))
                    except Exception as e:
                        logger.warning(f"Failed to parse tsc line: {line} - {e}")
            
            logger.info(f"TypeScript found {len(issues)} issues")
            
        except FileNotFoundError:
            errors.append("TypeScript (tsc) not found. Install with: npm install typescript")
        except subprocess.TimeoutExpired:
            errors.append("TypeScript check timed out after 60 seconds")
        except Exception as e:
            errors.append(f"TypeScript check failed: {str(e)}")
        
        return issues, errors
    
    def _run_eslint(self) -> Tuple[List[CodeIssue], List[str]]:
        """Run ESLint on frontend code."""
        issues: List[CodeIssue] = []
        errors: List[str] = []
        
        try:
            # Run eslint with JSON format
            result = subprocess.run(
                ["npx", "eslint", "src", "--format=json"],
                cwd=self.frontend_dir,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            # Parse JSON output
            if result.stdout.strip():
                try:
                    eslint_results = json.loads(result.stdout)
                    for file_result in eslint_results:
                        file_path = file_result.get("filePath", "")
                        # Make path relative
                        if self.frontend_dir.as_posix() in file_path:
                            file_path = file_path.replace(str(self.frontend_dir), "frontend_clean")
                        
                        for msg in file_result.get("messages", []):
                            issue_id = f"eslint_{len(issues) + 1}"
                            severity = "error" if msg.get("severity", 1) == 2 else "warning"
                            issues.append(CodeIssue(
                                id=issue_id,
                                tool="eslint",
                                severity=severity,
                                file_path=file_path,
                                line=msg.get("line"),
                                column=msg.get("column"),
                                rule=msg.get("ruleId"),
                                message=msg.get("message", "")
                            ))
                except json.JSONDecodeError:
                    logger.warning("Failed to parse ESLint JSON output")
            
            logger.info(f"ESLint found {len(issues)} issues")
            
        except FileNotFoundError:
            errors.append("ESLint not found. Install with: npm install eslint")
        except subprocess.TimeoutExpired:
            errors.append("ESLint check timed out after 60 seconds")
        except Exception as e:
            errors.append(f"ESLint check failed: {str(e)}")
        
        return issues, errors


def get_code_snippet(file_path: Path, line_number: int, context_lines: int = 3) -> str:
    """
    Extract code snippet around a specific line.
    
    Args:
        file_path: Path to the file
        line_number: Line number (1-indexed)
        context_lines: Number of lines to include before and after
        
    Returns:
        Code snippet as string
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        start = max(0, line_number - context_lines - 1)
        end = min(len(lines), line_number + context_lines)
        
        snippet_lines = []
        for i in range(start, end):
            prefix = ">>> " if i == line_number - 1 else "    "
            snippet_lines.append(f"{prefix}{i + 1:4d} | {lines[i].rstrip()}")
        
        return "\n".join(snippet_lines)
    except Exception as e:
        logger.warning(f"Failed to extract code snippet from {file_path}:{line_number} - {e}")
        return ""

