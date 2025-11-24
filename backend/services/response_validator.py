"""
Response Validator Service

Validates LLM response structure and format before and after generation.
Enforces required sections, code snippet size limits, and file path format.
"""

import logging
import re
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from pathlib import Path
from difflib import SequenceMatcher

logger = logging.getLogger("owlin.services.response_validator")


@dataclass
class ValidationResult:
    """Result of response validation."""
    is_valid: bool
    issues: List[str]
    missing_sections: List[str]
    code_snippet_issues: List[str]
    file_path_issues: List[str]
    score: float  # 0.0 to 1.0


class ResponseValidator:
    """Service for validating LLM response structure and format."""
    
    # Required sections for analysis responses
    REQUIRED_SECTIONS = [
        "Code Analysis",
        "Prioritized Diagnosis",
        "Root Cause",
        "Fix"
    ]
    
    # Alternative section names (flexible matching)
    SECTION_ALIASES = {
        "Code Analysis": ["code analysis", "files read", "files analyzed", "code review", "analysis of code"],
        "Prioritized Diagnosis": ["prioritized diagnosis", "diagnosis", "most likely", "issues"],
        "Root Cause": ["root cause", "cause", "problem", "issue"],
        "Fix": ["fix", "solution", "change", "modification"]
    }
    
    MAX_CODE_SNIPPET_LINES = 5  # Maximum lines per code snippet
    MAX_CODE_BLOCKS = 10  # Maximum number of code blocks
    MIN_SECTION_CONTENT_LENGTH = 10  # Minimum characters for section content
    SECTION_SIMILARITY_THRESHOLD = 0.6  # Minimum similarity for semantic matching
    MAX_CODE_TO_TEXT_RATIO = 0.4  # Maximum ratio of code to total text (40%)
    
    def __init__(self, repo_root: Optional[Path] = None):
        """
        Initialize the response validator.
        
        Args:
            repo_root: Path to repository root. If None, auto-detect from backend location.
        """
        if repo_root is None:
            # Auto-detect: backend/services/response_validator.py -> repo root is 2 levels up
            self.repo_root = Path(__file__).resolve().parent.parent.parent
        else:
            self.repo_root = Path(repo_root).resolve()
    
    def validate_template(self, response_template: str) -> ValidationResult:
        """
        Validate response template structure before generation.
        
        Args:
            response_template: Template or prompt for response generation
            
        Returns:
            ValidationResult with validation status
        """
        issues = []
        
        # Check if template mentions required sections
        template_lower = response_template.lower()
        missing_sections = []
        
        for section in self.REQUIRED_SECTIONS:
            section_found = False
            # Check main name
            if section.lower() in template_lower:
                section_found = True
            # Check aliases
            if not section_found:
                for alias in self.SECTION_ALIASES.get(section, []):
                    if alias in template_lower:
                        section_found = True
                        break
            
            if not section_found:
                missing_sections.append(section)
        
        if missing_sections:
            issues.append(f"Template missing required sections: {missing_sections}")
        
        # Check if template enforces code snippet limits
        if "3-5 lines" not in template_lower and "small snippet" not in template_lower:
            issues.append("Template should enforce code snippet size limits (3-5 lines)")
        
        # Check if template requires file paths
        if "file path" not in template_lower and "backend/" not in template_lower:
            issues.append("Template should require actual file paths")
        
        score = 1.0 - (len(issues) * 0.2)  # Deduct 0.2 per issue
        score = max(0.0, min(1.0, score))
        
        return ValidationResult(
            is_valid=len(issues) == 0,
            issues=issues,
            missing_sections=missing_sections,
            code_snippet_issues=[],
            file_path_issues=[],
            score=score
        )
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate similarity between two texts using SequenceMatcher.
        
        Args:
            text1: First text
            text2: Second text
            
        Returns:
            Similarity score between 0.0 and 1.0
        """
        return SequenceMatcher(None, text1.lower(), text2.lower()).ratio()
    
    def _find_section_in_response(self, section: str, response: str) -> Optional[Dict[str, Any]]:
        """
        Find a section in the response using semantic matching.
        
        Args:
            section: The section name to find
            response: The response text
            
        Returns:
            Dict with 'found', 'name', 'content', 'similarity' or None if not found
        """
        response_lower = response.lower()
        section_lower = section.lower()
        
        # Check exact matches first (with markdown formatting)
        patterns = [
            f"**{section}**",
            f"## {section}",
            f"# {section}",
            section_lower
        ]
        
        for pattern in patterns:
            pattern_lower = pattern.lower()
            if pattern_lower in response_lower:
                # Extract section content
                content = self._extract_section_content(response, pattern)
                return {
                    "found": True,
                    "name": section,
                    "content": content,
                    "similarity": 1.0,
                    "match_type": "exact"
                }
        
        # Check aliases
        for alias in self.SECTION_ALIASES.get(section, []):
            if alias in response_lower:
                content = self._extract_section_content(response, alias)
                return {
                    "found": True,
                    "name": section,
                    "content": content,
                    "similarity": 1.0,
                    "match_type": "alias"
                }
        
        # Try semantic matching on section headers
        # Look for markdown headers and check similarity
        header_pattern = r'(?:^|\n)(?:#{1,3}\s+|\*\*)([^*\n]+?)(?:\*\*|:)\s*\n'
        for match in re.finditer(header_pattern, response, re.MULTILINE):
            header_text = match.group(1).strip()
            similarity = self._calculate_similarity(header_text, section)
            
            if similarity >= self.SECTION_SIMILARITY_THRESHOLD:
                content = self._extract_section_content(response, header_text)
                return {
                    "found": True,
                    "name": section,
                    "content": content,
                    "similarity": similarity,
                    "match_type": "semantic"
                }
        
        return None
    
    def _extract_section_content(self, response: str, section_header: str) -> str:
        """
        Extract content of a section from the response.
        
        Args:
            response: The response text
            section_header: The section header to find
            
        Returns:
            The section content
        """
        # Find the section header position
        header_pattern = re.escape(section_header)
        pattern = rf'(?:^|\n)(?:#{1,3}\s+|\*\*)?{header_pattern}(?:\*\*|:)?\s*\n(.*?)(?=\n(?:#{1,3}\s+|\*\*)|$)'
        match = re.search(pattern, response, re.MULTILINE | re.DOTALL | re.IGNORECASE)
        
        if match and match.group(1):
            return match.group(1).strip()
        
        # Fallback: find text after the header
        pos = response.lower().find(section_header.lower())
        if pos != -1:
            # Find next section or end of response
            next_section_pattern = r'\n(?:#{1,3}\s+|\*\*)([^*\n]+?)(?:\*\*|:)'
            next_match = re.search(next_section_pattern, response[pos:], re.MULTILINE)
            if next_match:
                content = response[pos + len(section_header):pos + next_match.start()].strip()
                return content if content else ""
            else:
                content = response[pos + len(section_header):].strip()
                return content if content else ""
        
        return ""
    
    def check_required_sections(self, response: str) -> List[str]:
        """
        Check if response contains all required sections with content validation.
        
        Args:
            response: The response text to validate
            
        Returns:
            List of missing section names
        """
        missing = []
        
        for section in self.REQUIRED_SECTIONS:
            section_info = self._find_section_in_response(section, response)
            
            if not section_info:
                missing.append(section)
            else:
                # Validate section has meaningful content
                content = section_info.get("content", "")
                # Remove code blocks for content length check
                content_without_code = re.sub(r'```.*?```', '', content, flags=re.DOTALL)
                content_without_code = re.sub(r'`[^`]+`', '', content_without_code)
                content_length = len(content_without_code.strip())
                
                if content_length < self.MIN_SECTION_CONTENT_LENGTH:
                    # Section exists but has no meaningful content
                    missing.append(f"{section} (empty or insufficient content)")
        
        return missing
    
    def validate_code_snippet_size(self, response: str) -> Dict[str, Any]:
        """
        Validate that code snippets are within size limits and check code-to-text ratio.
        
        Args:
            response: The response text to validate
            
        Returns:
            Dict with 'valid', 'issues', 'large_snippets', 'total_blocks', 'code_length', 'text_length', 'code_ratio'
        """
        issues = []
        large_snippets = []
        
        # Find all code blocks
        code_block_pattern = r'```(?:python|typescript|javascript|js|ts|tsx|jsx)?\n(.*?)```'
        code_blocks = re.findall(code_block_pattern, response, re.DOTALL)
        
        # Also find inline code that might be too long
        inline_code_pattern = r'`([^`\n]{50,})`'  # Inline code longer than 50 chars
        inline_code = re.findall(inline_code_pattern, response)
        
        total_blocks = len(code_blocks) + len(inline_code)
        total_code_length = sum(len(block) for block in code_blocks) + sum(len(code) for code in inline_code)
        
        # Check each code block
        for i, block in enumerate(code_blocks, 1):
            lines = [line for line in block.split('\n') if line.strip()]
            line_count = len(lines)
            
            if line_count > self.MAX_CODE_SNIPPET_LINES:
                large_snippets.append({
                    "block_number": i,
                    "lines": line_count,
                    "max_allowed": self.MAX_CODE_SNIPPET_LINES,
                    "preview": '\n'.join(lines[:3]) + "..." if len(lines) > 3 else '\n'.join(lines),
                    "length": len(block)
                })
                issues.append(f"Code block #{i} has {line_count} lines (max {self.MAX_CODE_SNIPPET_LINES})")
        
        # Check total number of code blocks
        if total_blocks > self.MAX_CODE_BLOCKS:
            issues.append(f"Too many code blocks: {total_blocks} (max {self.MAX_CODE_BLOCKS})")
        
        # Calculate code-to-text ratio
        # Remove code blocks to get text length
        text_without_code = re.sub(r'```.*?```', '', response, flags=re.DOTALL)
        text_without_code = re.sub(r'`[^`]+`', '', text_without_code)
        text_length = len(text_without_code.strip())
        total_length = text_length + total_code_length
        
        code_ratio = 0.0
        if total_length > 0:
            code_ratio = total_code_length / total_length
        
        # Check code-to-text ratio
        if code_ratio > self.MAX_CODE_TO_TEXT_RATIO:
            issues.append(
                f"Code-to-text ratio too high: {code_ratio:.1%} "
                f"(max {self.MAX_CODE_TO_TEXT_RATIO:.1%}). "
                f"Response should be text-first with small code snippets."
            )
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "large_snippets": large_snippets,
            "total_blocks": total_blocks,
            "max_blocks": self.MAX_CODE_BLOCKS,
            "code_length": total_code_length,
            "text_length": text_length,
            "code_ratio": code_ratio
        }
    
    def check_file_path_format(self, response: str) -> List[str]:
        """
        Check if file paths in response are in correct format and exist.
        
        Args:
            response: The response text to validate
            
        Returns:
            List of invalid file paths found
        """
        invalid_paths = []
        
        # Find all file path references with line numbers
        # Pattern: backend/path/to/file.py:123 or frontend/path/to/file.ts:456
        full_path_pattern = r'((?:backend|frontend|frontend_clean)[/\w\-\.]+\.(?:py|ts|tsx|js|jsx))(?::\d+)?'
        path_matches = re.finditer(full_path_pattern, response)
        
        for match in path_matches:
            path_str = match.group(1)
            
            # Validate path format
            if not path_str.startswith(('backend/', 'frontend/', 'frontend_clean/')):
                invalid_paths.append(f"{path_str} (invalid format)")
                continue
            
            # Check if path exists
            full_path = self.repo_root / path_str
            try:
                if not full_path.exists():
                    invalid_paths.append(f"{path_str} (file not found)")
                elif not full_path.is_file():
                    invalid_paths.append(f"{path_str} (not a file)")
            except Exception as e:
                logger.warning(f"Error checking path {path_str}: {e}")
                invalid_paths.append(f"{path_str} (validation error)")
        
        # Also check for generic paths (not starting with backend/ or frontend/)
        generic_path_pattern = r'\b(\w+\.(?:py|ts|tsx|js|jsx))(?::\d+)?'
        generic_matches = re.finditer(generic_path_pattern, response)
        
        for match in generic_matches:
            path = match.group(1)
            # Skip if it's part of a full path we already checked
            if path.startswith(('backend/', 'frontend/', 'frontend_clean/')):
                continue
            
            # Check if it's mentioned near a full path (might be acceptable)
            path_pos = match.start()
            context = response[max(0, path_pos-100):path_pos+100]
            if not re.search(r'(backend|frontend|frontend_clean)[/\w\-\.]+\.(?:py|ts|tsx|js|jsx)', context):
                invalid_paths.append(f"{path} (generic path, use full path)")
        
        return invalid_paths
    
    def validate_response(self, response: str) -> ValidationResult:
        """
        Comprehensive response validation.
        
        Args:
            response: The response text to validate
            
        Returns:
            ValidationResult with all validation issues
        """
        issues = []
        
        # Check required sections
        missing_sections = self.check_required_sections(response)
        if missing_sections:
            issues.append(f"Missing required sections: {missing_sections}")
        
        # Validate code snippet sizes
        code_validation = self.validate_code_snippet_size(response)
        if not code_validation["valid"]:
            issues.extend(code_validation["issues"])
        
        # Check file path format
        invalid_paths = self.check_file_path_format(response)
        if invalid_paths:
            issues.append(f"Invalid/generic file paths: {invalid_paths[:5]}")
        
        # Code-to-text ratio is now checked in validate_code_snippet_size
        # No need to duplicate the check here
        
        # Calculate score
        score = 1.0
        score -= len(missing_sections) * 0.25  # -0.25 per missing section
        score -= len(code_validation["issues"]) * 0.15  # -0.15 per code issue
        score -= len(invalid_paths) * 0.1  # -0.1 per invalid path
        score = max(0.0, min(1.0, score))
        
        return ValidationResult(
            is_valid=len(issues) == 0,
            issues=issues,
            missing_sections=missing_sections,
            code_snippet_issues=code_validation["issues"],
            file_path_issues=invalid_paths,
            score=score
        )
    
    def extract_sections(self, response: str) -> Dict[str, str]:
        """
        Extract sections from response.
        
        Args:
            response: The response text
            
        Returns:
            Dict mapping section names to their content
        """
        sections = {}
        
        # Try to find sections by markdown headers
        section_pattern = r'(?:^|\n)(?:#{1,3}\s+|\*\*)([^*\n]+?)(?:\*\*|:)\s*\n(.*?)(?=\n(?:#{1,3}\s+|\*\*)|$)'
        matches = re.finditer(section_pattern, response, re.MULTILINE | re.DOTALL)
        
        for match in matches:
            section_name = match.group(1).strip()
            section_content = match.group(2).strip()
            
            # Normalize section name
            for required_section in self.REQUIRED_SECTIONS:
                if required_section.lower() in section_name.lower():
                    sections[required_section] = section_content
                    break
                # Check aliases
                for alias in self.SECTION_ALIASES.get(required_section, []):
                    if alias in section_name.lower():
                        sections[required_section] = section_content
                        break
        
        return sections
    
    def suggest_improvements(self, validation_result: ValidationResult) -> List[str]:
        """
        Generate improvement suggestions based on validation results.
        
        Args:
            validation_result: The validation result
            
        Returns:
            List of improvement suggestions
        """
        suggestions = []
        
        if validation_result.missing_sections:
            suggestions.append(f"Add missing sections: {', '.join(validation_result.missing_sections)}")
        
        if validation_result.code_snippet_issues:
            suggestions.append("Reduce code snippet sizes to 3-5 lines maximum")
            suggestions.append("Use text explanations with small code snippets, not large code dumps")
        
        if validation_result.file_path_issues:
            suggestions.append("Use full file paths (e.g., backend/main.py:123) instead of generic names")
        
        if validation_result.score < 0.7:
            suggestions.append("Response format needs significant improvement - follow the required structure")
        
        return suggestions
    
    def _detect_placeholder_code(self, response: str) -> List[str]:
        """Detect placeholder code patterns in response."""
        issues = []
        placeholder_patterns = [
            r'def\s+\w+\([^)]*\):\s*pass\s*$',  # def func(): pass
            r'def\s+\w+\([^)]*\):\s*#\s*Code\s+to\s+',  # def func(): # Code to...
            r'def\s+\w+\([^)]*\):[\s\n]+\s*#\s*Code\s+to\s+',  # def func():\n    # Code to... (multiline with indentation)
            r'def\s+\w+\([^)]*\):\s*#\s*.*\s+pass\s*$',  # def func(): # comment pass
            r'def\s+\w+\([^)]*\):[\s\n]+\s*#\s*.*[\s\n]+\s*pass\s*$',  # def func():\n    # comment\n    pass (multiline with indentation)
            r'def\s+\w+\([^)]*\):[\s\n]+\s*#\s+.*[\s\n]+\s*pass',  # def func():\n    # Code to...\n    pass (with any indentation)
            r'return\s+None\s*#\s*placeholder',  # return None # placeholder
            r'\bpass\s*$',  # standalone pass statement
            r'#\s*(?:TODO|FIXME|stub|placeholder)',  # TODO/FIXME/stub comments
        ]
        
        # Check code blocks
        code_blocks = re.findall(r'```[\w]*\n(.*?)```', response, re.DOTALL)
        for block in code_blocks:
            for pattern in placeholder_patterns:
                if re.search(pattern, block, re.MULTILINE | re.IGNORECASE):
                    issues.append(f"Placeholder code detected: function with placeholder pattern")
                    break  # Only report once per block
        
        # NEW: Also check entire response text for placeholder patterns (not just code blocks)
        # This catches cases where placeholder code appears in regular text
        for pattern in placeholder_patterns:
            if re.search(pattern, response, re.MULTILINE | re.IGNORECASE):
                # Make sure we haven't already reported this from code blocks
                if not any('Placeholder code detected' in issue for issue in issues):
                    issues.append(f"Placeholder code detected in response text: function with placeholder pattern")
                break  # Only report once
        
        # Also check for placeholder language in code blocks
        for block in code_blocks:
            block_lower = block.lower()
            placeholder_indicators = [
                "code to",
                "example code",
                "would be",
                "should be",
                "might be",
                "could be",
            ]
            
            # Check if block is mostly comments or placeholder text
            lines = block.split('\n')
            code_lines = [l for l in lines if l.strip() and not l.strip().startswith('#') and not l.strip().startswith('//')]
            
            # Check for function definitions with only comments (no actual code)
            has_function_def = bool(re.search(r'def\s+\w+', block))
            if has_function_def:
                # Check if function has only pass statement or only comments
                func_match = re.search(r'def\s+\w+\([^)]*\):', block)
                if func_match:
                    func_start = func_match.end()
                    func_body = block[func_start:].strip()
                    func_body_lines = [l.strip() for l in func_body.split('\n') if l.strip()]
                    # If function body is only comments and pass, it's placeholder
                    non_comment_lines = [l for l in func_body_lines if not l.startswith('#') and not l.startswith('//') and l != 'pass']
                    if len(non_comment_lines) == 0 and ('pass' in func_body_lines or len(func_body_lines) <= 2):
                        issues.append("Code snippet contains function definition with only comments and pass statement (placeholder code)")
                elif len(code_lines) < 2:  # Function def but less than 2 actual code lines
                    issues.append("Code snippet contains function definition but insufficient actual code (mostly comments)")
            
            # Check for placeholder language
            if any(indicator in block_lower for indicator in placeholder_indicators):
                issues.append("Code snippet contains placeholder language instead of actual code")
        
        return issues
    
    def _check_code_snippets_are_actual_code(self, response: str) -> List[str]:
        """Verify code snippets contain actual code, not summaries."""
        issues = []
        
        # Find code blocks
        code_blocks = re.findall(r'```[\w]*\n(.*?)```', response, re.DOTALL)
        
        for block in code_blocks:
            block_lower = block.lower()
            # Check for placeholder indicators
            placeholder_indicators = [
                "code to",
                "example code",
                "would be",
                "should be",
                "might be",
                "could be",
            ]
            
            # If block is mostly comments or placeholder text
            lines = block.split('\n')
            code_lines = [l for l in lines if l.strip() and not l.strip().startswith('#') and not l.strip().startswith('//')]
            
            # Check for function definitions with only comments
            has_function_def = bool(re.search(r'def\s+\w+|function\s+\w+|const\s+\w+\s*=', block))
            
            if has_function_def and len(code_lines) < 2:  # Function def but less than 2 actual code lines
                issues.append("Code snippet contains function definition but insufficient actual code (mostly comments)")
            elif len(code_lines) < 2:  # Less than 2 actual code lines
                issues.append("Code snippet contains insufficient actual code (mostly comments)")
            
            # Check for placeholder language
            if any(indicator in block_lower for indicator in placeholder_indicators):
                issues.append("Code snippet contains placeholder language instead of actual code")
            
            # Check for function definitions that only have comments (no implementation)
            if has_function_def:
                # Check if function body is only comments
                func_match = re.search(r'(def\s+\w+\([^)]*\):|function\s+\w+\([^)]*\)\s*\{)', block)
                if func_match:
                    func_start = func_match.end()
                    func_body = block[func_start:].strip()
                    func_body_lines = [l.strip() for l in func_body.split('\n') if l.strip()]
                    # If all remaining lines are comments, it's placeholder
                    if func_body_lines and all(l.startswith('#') or l.startswith('//') for l in func_body_lines):
                        issues.append("Code snippet contains function definition with only comments, no actual implementation")
        
        return issues

