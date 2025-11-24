"""
Devtools LLM Explainer

Generates explanations for code issues using Ollama (if available) or template fallbacks.
All operations are offline-first and deterministic.
"""

import logging
import requests
import time
from typing import Optional, Tuple
from backend.devtools.models import IssueExplanation, UnifiedDiff

logger = logging.getLogger("owlin.devtools.explainer")


class LLMExplainer:
    """Generates issue explanations using local LLM or template fallbacks."""
    
    def __init__(self, ollama_url: str = "http://localhost:11434"):
        """
        Initialize the LLM explainer.
        
        Args:
            ollama_url: Base URL for Ollama API
        """
        self.ollama_url = ollama_url
        self.ollama_available = self._check_ollama_available()
        
        if self.ollama_available:
            logger.info(f"Ollama is available at {ollama_url}")
        else:
            logger.info("Ollama not available, will use template fallbacks")
    
    def _check_ollama_available(self) -> bool:
        """Check if Ollama is running and accessible."""
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=2)
            return response.status_code == 200
        except Exception:
            return False
    
    def explain_issue(
        self,
        issue_id: str,
        tool: str,
        file_path: str,
        error_snippet: str,
        code_region: Optional[str] = None,
        line_number: Optional[int] = None
    ) -> IssueExplanation:
        """
        Generate explanation for a code issue.
        
        Args:
            issue_id: Unique issue identifier
            tool: Tool that detected the issue (mypy, eslint, etc.)
            file_path: File path where issue occurs
            error_snippet: Error message or snippet
            code_region: Optional surrounding code context
            line_number: Optional line number
            
        Returns:
            IssueExplanation with plain English, technical cause, fix, and Cursor prompt
        """
        # Try Ollama first if available
        if self.ollama_available:
            try:
                return self._explain_with_ollama(
                    issue_id, tool, file_path, error_snippet, code_region, line_number
                )
            except Exception as e:
                logger.warning(f"Ollama explanation failed, falling back to templates: {e}")
        
        # Fallback to deterministic templates
        return self._explain_with_template(
            issue_id, tool, file_path, error_snippet, code_region, line_number
        )
    
    def _explain_with_ollama(
        self,
        issue_id: str,
        tool: str,
        file_path: str,
        error_snippet: str,
        code_region: Optional[str],
        line_number: Optional[int]
    ) -> IssueExplanation:
        """Generate explanation using Ollama local LLM."""
        
        # Construct prompt for the LLM
        prompt = self._build_llm_prompt(tool, file_path, error_snippet, code_region, line_number)
        
        # Call Ollama API
        try:
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": "codellama:7b",  # Use CodeLlama for code explanations
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.3,  # Low temperature for consistent output
                        "num_predict": 500  # Limit response length
                    }
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                generated_text = result.get("response", "")
                
                # Parse LLM response into structured format
                return self._parse_llm_response(
                    issue_id, generated_text, file_path, line_number
                )
            else:
                logger.warning(f"Ollama API returned status {response.status_code}")
                raise Exception("Ollama API error")
                
        except Exception as e:
            logger.error(f"Ollama request failed: {e}")
            raise
    
    def _build_llm_prompt(
        self,
        tool: str,
        file_path: str,
        error_snippet: str,
        code_region: Optional[str],
        line_number: Optional[int]
    ) -> str:
        """Build prompt for LLM."""
        
        # Build code context section separately to avoid backslash in f-string
        code_context_section = ""
        if code_region:
            code_context_section = f"\nCode Context:\n{code_region}\n"
        
        prompt = f"""You are a code debugging assistant. Analyze this error and provide a clear explanation.

Tool: {tool}
File: {file_path}
{f"Line: {line_number}" if line_number else ""}

Error Message:
{error_snippet}
{code_context_section}
Please provide:
1. PLAIN_ENGLISH: Explain in simple terms what's wrong (1-2 sentences)
2. TECHNICAL_CAUSE: Technical root cause (1-2 sentences)
3. SUGGESTED_FIX: Step-by-step fix instructions (3-5 bullet points)
4. CURSOR_PROMPT: A one-line prompt for Cursor AI to fix this issue

Format your response exactly as:
PLAIN_ENGLISH: <explanation>
TECHNICAL_CAUSE: <cause>
SUGGESTED_FIX:
- <step 1>
- <step 2>
- <step 3>
CURSOR_PROMPT: <prompt>
"""
        return prompt
    
    def _parse_llm_response(
        self,
        issue_id: str,
        response_text: str,
        file_path: str,
        line_number: Optional[int]
    ) -> IssueExplanation:
        """Parse LLM response into structured IssueExplanation."""
        
        # Extract sections from response
        plain_english = ""
        technical_cause = ""
        suggested_fix = ""
        cursor_prompt = ""
        
        lines = response_text.split("\n")
        current_section = None
        
        for line in lines:
            line = line.strip()
            
            if line.startswith("PLAIN_ENGLISH:"):
                current_section = "plain"
                plain_english = line.replace("PLAIN_ENGLISH:", "").strip()
            elif line.startswith("TECHNICAL_CAUSE:"):
                current_section = "technical"
                technical_cause = line.replace("TECHNICAL_CAUSE:", "").strip()
            elif line.startswith("SUGGESTED_FIX:"):
                current_section = "fix"
            elif line.startswith("CURSOR_PROMPT:"):
                current_section = "cursor"
                cursor_prompt = line.replace("CURSOR_PROMPT:", "").strip()
            elif line and current_section == "fix":
                suggested_fix += line + "\n"
            elif line and current_section:
                # Continue previous section
                if current_section == "plain":
                    plain_english += " " + line
                elif current_section == "technical":
                    technical_cause += " " + line
                elif current_section == "cursor":
                    cursor_prompt += " " + line
        
        # Fallback to defaults if parsing failed
        if not plain_english:
            plain_english = "There's an issue in your code that needs attention."
        if not technical_cause:
            technical_cause = "A code quality check detected a problem."
        if not suggested_fix:
            suggested_fix = "Review the error message and fix the issue."
        if not cursor_prompt:
            cursor_prompt = f"Fix issue in {file_path}"
            if line_number:
                cursor_prompt += f" at line {line_number}"
        
        return IssueExplanation(
            issue_id=issue_id,
            plain_english=plain_english,
            technical_cause=technical_cause,
            suggested_fix=suggested_fix.strip(),
            cursor_prompt=cursor_prompt,
            confidence=0.85,
            generation_method="ollama_llm"
        )
    
    def _explain_with_template(
        self,
        issue_id: str,
        tool: str,
        file_path: str,
        error_snippet: str,
        code_region: Optional[str],
        line_number: Optional[int]
    ) -> IssueExplanation:
        """Generate explanation using deterministic templates."""
        
        # Tool-specific templates
        templates = {
            "mypy": self._template_mypy,
            "ruff": self._template_ruff,
            "eslint": self._template_eslint,
            "tsc": self._template_tsc,
            "pytest": self._template_pytest,
        }
        
        template_func = templates.get(tool.lower(), self._template_generic)
        return template_func(issue_id, file_path, error_snippet, line_number)
    
    def _template_mypy(
        self, issue_id: str, file_path: str, error_snippet: str, line_number: Optional[int]
    ) -> IssueExplanation:
        """Template for MyPy type errors."""
        
        plain_english = "There's a type mismatch in your Python code. "
        technical_cause = f"MyPy detected a type error: {error_snippet[:100]}"
        suggested_fix = """1. Check the variable types at the reported line
2. Ensure assignments match the declared type annotations
3. Add or correct type hints if missing
4. Consider using Optional[] for values that can be None"""
        
        cursor_prompt = f"Fix MyPy type error in {file_path}"
        if line_number:
            cursor_prompt += f" at line {line_number}"
        
        return IssueExplanation(
            issue_id=issue_id,
            plain_english=plain_english,
            technical_cause=technical_cause,
            suggested_fix=suggested_fix,
            cursor_prompt=cursor_prompt,
            confidence=0.9,
            generation_method="template_fallback"
        )
    
    def _template_ruff(
        self, issue_id: str, file_path: str, error_snippet: str, line_number: Optional[int]
    ) -> IssueExplanation:
        """Template for Ruff linting errors."""
        
        plain_english = "Your Python code violates a style or quality guideline."
        technical_cause = f"Ruff linter found an issue: {error_snippet[:100]}"
        suggested_fix = """1. Review the specific Ruff rule mentioned
2. Fix the code style or quality issue
3. Run 'ruff check --fix' for auto-fixable issues
4. Consider adding '# noqa: <rule>' if intentional"""
        
        cursor_prompt = f"Fix Ruff linting issue in {file_path}"
        if line_number:
            cursor_prompt += f" at line {line_number}"
        
        return IssueExplanation(
            issue_id=issue_id,
            plain_english=plain_english,
            technical_cause=technical_cause,
            suggested_fix=suggested_fix,
            cursor_prompt=cursor_prompt,
            confidence=0.9,
            generation_method="template_fallback"
        )
    
    def _template_eslint(
        self, issue_id: str, file_path: str, error_snippet: str, line_number: Optional[int]
    ) -> IssueExplanation:
        """Template for ESLint errors."""
        
        plain_english = "Your JavaScript/TypeScript code has a linting issue."
        technical_cause = f"ESLint detected: {error_snippet[:100]}"
        suggested_fix = """1. Review the ESLint rule mentioned in the error
2. Fix the code style or quality issue
3. Run 'npm run lint -- --fix' for auto-fixable issues
4. Add '// eslint-disable-next-line <rule>' if needed"""
        
        cursor_prompt = f"Fix ESLint issue in {file_path}"
        if line_number:
            cursor_prompt += f" at line {line_number}"
        
        return IssueExplanation(
            issue_id=issue_id,
            plain_english=plain_english,
            technical_cause=technical_cause,
            suggested_fix=suggested_fix,
            cursor_prompt=cursor_prompt,
            confidence=0.9,
            generation_method="template_fallback"
        )
    
    def _template_tsc(
        self, issue_id: str, file_path: str, error_snippet: str, line_number: Optional[int]
    ) -> IssueExplanation:
        """Template for TypeScript compiler errors."""
        
        plain_english = "TypeScript found a type error in your code."
        technical_cause = f"TypeScript compiler error: {error_snippet[:100]}"
        suggested_fix = """1. Check the types at the reported location
2. Ensure function arguments match expected types
3. Add proper type annotations where missing
4. Use type assertions (as Type) if you're certain of the type"""
        
        cursor_prompt = f"Fix TypeScript error in {file_path}"
        if line_number:
            cursor_prompt += f" at line {line_number}"
        
        return IssueExplanation(
            issue_id=issue_id,
            plain_english=plain_english,
            technical_cause=technical_cause,
            suggested_fix=suggested_fix,
            cursor_prompt=cursor_prompt,
            confidence=0.9,
            generation_method="template_fallback"
        )
    
    def _template_pytest(
        self, issue_id: str, file_path: str, error_snippet: str, line_number: Optional[int]
    ) -> IssueExplanation:
        """Template for Pytest errors."""
        
        plain_english = "There's a syntax or import error preventing tests from running."
        technical_cause = f"Pytest collection error: {error_snippet[:100]}"
        suggested_fix = """1. Fix any syntax errors in test files
2. Ensure all imports are available
3. Check for missing dependencies
4. Verify test file structure follows pytest conventions"""
        
        cursor_prompt = f"Fix test error in {file_path}"
        
        return IssueExplanation(
            issue_id=issue_id,
            plain_english=plain_english,
            technical_cause=technical_cause,
            suggested_fix=suggested_fix,
            cursor_prompt=cursor_prompt,
            confidence=0.85,
            generation_method="template_fallback"
        )
    
    def _template_generic(
        self, issue_id: str, file_path: str, error_snippet: str, line_number: Optional[int]
    ) -> IssueExplanation:
        """Generic template for unknown tools."""
        
        plain_english = "A code quality check found an issue that needs your attention."
        technical_cause = f"Issue detected: {error_snippet[:100]}"
        suggested_fix = """1. Review the error message carefully
2. Check the code at the reported location
3. Fix the issue according to the error message
4. Run the check again to verify the fix"""
        
        cursor_prompt = f"Fix issue in {file_path}"
        if line_number:
            cursor_prompt += f" at line {line_number}"
        
        return IssueExplanation(
            issue_id=issue_id,
            plain_english=plain_english,
            technical_cause=technical_cause,
            suggested_fix=suggested_fix,
            cursor_prompt=cursor_prompt,
            confidence=0.7,
            generation_method="template_fallback"
        )
    
    def generate_unified_diff(
        self,
        file_path: str,
        original_code: str,
        fixed_code: str
    ) -> Optional[UnifiedDiff]:
        """
        Generate a unified diff patch.
        
        Args:
            file_path: File being patched
            original_code: Original code
            fixed_code: Fixed code
            
        Returns:
            UnifiedDiff or None if unable to generate
        """
        try:
            import difflib
            
            original_lines = original_code.splitlines(keepends=True)
            fixed_lines = fixed_code.splitlines(keepends=True)
            
            diff_lines = list(difflib.unified_diff(
                original_lines,
                fixed_lines,
                fromfile=f"a/{file_path}",
                tofile=f"b/{file_path}",
                lineterm=""
            ))
            
            if not diff_lines:
                return None
            
            # Extract hunks (sections starting with @@)
            hunks = [line for line in diff_lines if line.startswith("@@")]
            patch_text = "\n".join(diff_lines)
            
            # Count changed lines (+ and - lines)
            changed_lines = len([l for l in diff_lines if l.startswith(("+", "-")) and not l.startswith(("+++", "---"))])
            
            return UnifiedDiff(
                file_path=file_path,
                hunks=hunks,
                patch_text=patch_text,
                line_count=changed_lines
            )
            
        except Exception as e:
            logger.error(f"Failed to generate unified diff: {e}")
            return None

