"""
Code Verifier Service

Actually verifies LLM claims against real code in the codebase.
Uses AST parsing and file reading to validate function names, code snippets,
framework detection, and logging claims.
"""

import logging
import re
from typing import Dict, Any, Optional, Tuple, List
from pathlib import Path
from difflib import SequenceMatcher
from backend.services.code_reader import CodeReader
from backend.services.ast_parser import ASTParser
from backend.services.code_explorer import CodeExplorer

logger = logging.getLogger("owlin.services.code_verifier")

# Try to import rapidfuzz for fuzzy matching
try:
    from rapidfuzz import fuzz, process
    RAPIDFUZZ_AVAILABLE = True
except ImportError:
    RAPIDFUZZ_AVAILABLE = False
    logger.warning("rapidfuzz not available. Install with: pip install rapidfuzz")


class CodeVerifier:
    """Service for verifying LLM claims against actual code."""
    
    def __init__(self, repo_root: Optional[Path] = None):
        """
        Initialize the code verifier.
        
        Args:
            repo_root: Path to repository root. If None, auto-detect.
        """
        self.code_reader = CodeReader(repo_root=repo_root)
        self.ast_parser = ASTParser()
        self.code_explorer = CodeExplorer()
        self.repo_root = self.code_reader.repo_root
        logger.info(f"CodeVerifier initialized with repo_root: {self.repo_root}")
    
    def verify_function_exists(
        self, 
        func_name: str, 
        file_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Verify that a function actually exists in the codebase.
        
        Args:
            func_name: Name of the function to verify
            file_path: Optional specific file to check. If None, searches entire codebase.
            
        Returns:
            Dict with 'exists', 'file_path', 'line', 'signature', and 'match_confidence'
        """
        if file_path:
            # Check specific file
            func_def = self.ast_parser.find_function_definition(file_path, func_name)
            if func_def:
                return {
                    "exists": True,
                    "file_path": file_path,
                    "line": func_def.get("line"),
                    "end_line": func_def.get("end_line"),
                    "signature": self._format_function_signature(func_def),
                    "is_async": func_def.get("is_async", False),
                    "decorators": func_def.get("decorators", []),
                    "match_confidence": 1.0
                }
            else:
                return {
                    "exists": False,
                    "file_path": file_path,
                    "error": f"Function '{func_name}' not found in {file_path}",
                    "match_confidence": 0.0
                }
        else:
            # Search entire codebase
            # Use grep to find function definitions
            pattern = f"def {func_name}|async def {func_name}|function {func_name}|const {func_name}"
            matches = self.code_explorer.grep_pattern(pattern)
            
            if matches:
                # Get first match and parse it
                first_file = list(matches.keys())[0]
                first_line = matches[first_file][0]
                
                func_def = self.ast_parser.find_function_definition(first_file, func_name)
                if func_def:
                    return {
                        "exists": True,
                        "file_path": first_file,
                        "line": func_def.get("line"),
                        "end_line": func_def.get("end_line"),
                        "signature": self._format_function_signature(func_def),
                        "is_async": func_def.get("is_async", False),
                        "decorators": func_def.get("decorators", []),
                        "match_confidence": 1.0,
                        "all_locations": [(f, matches[f]) for f in matches.keys()]
                    }
            
            return {
                "exists": False,
                "error": f"Function '{func_name}' not found in codebase",
                "match_confidence": 0.0
            }
    
    def verify_code_snippet(
        self,
        claimed_code: str,
        file_path: str,
        line_range: Optional[Tuple[int, int]] = None
    ) -> Dict[str, Any]:
        """
        Verify that a code snippet matches actual code in a file.
        
        Args:
            claimed_code: The code snippet claimed by LLM
            file_path: File path where code should exist
            line_range: Optional (start_line, end_line) tuple. If None, searches for snippet.
            
        Returns:
            Dict with 'matches', 'similarity', 'actual_code', 'line_range', and 'differences'
        """
        # Read the actual file
        file_data = self.code_reader.read_file(file_path)
        if not file_data.get("success"):
            return {
                "matches": False,
                "similarity": 0.0,
                "error": f"Could not read file: {file_path}",
                "file_path": file_path,
                "claimed_code": claimed_code  # Store claimed code even in error case
            }
        
        actual_content = file_data["content"]
        actual_lines = actual_content.split('\n')
        
        if line_range:
            # Check specific line range
            start_line, end_line = line_range
            start_idx = max(0, start_line - 1)
            end_idx = min(len(actual_lines), end_line)
            actual_snippet = '\n'.join(actual_lines[start_idx:end_idx])
        else:
            # Search for the snippet in the file
            actual_snippet = self._find_similar_snippet(claimed_code, actual_content)
            if actual_snippet:
                # Find line range
                snippet_lines = actual_snippet.split('\n')
                for i in range(len(actual_lines) - len(snippet_lines) + 1):
                    if '\n'.join(actual_lines[i:i+len(snippet_lines)]) == actual_snippet:
                        line_range = (i + 1, i + len(snippet_lines))
                        break
        
        if not actual_snippet:
            return {
                "matches": False,
                "similarity": 0.0,
                "error": f"Code snippet not found in {file_path}",
                "file_path": file_path,
                "claimed_code": claimed_code
            }
        
        # Normalize both snippets for comparison
        normalized_claimed = self._normalize_code(claimed_code)
        normalized_actual = self._normalize_code(actual_snippet)
        
        # Calculate similarity
        similarity = SequenceMatcher(None, normalized_claimed, normalized_actual).ratio()
        
        # Find differences
        differences = self._find_code_differences(claimed_code, actual_snippet)
        
        return {
            "matches": similarity >= 0.85,  # 85% similarity threshold
            "similarity": similarity,
            "actual_code": actual_snippet,
            "claimed_code": claimed_code,  # Store claimed code for use as dict key
            "line_range": line_range,
            "file_path": file_path,
            "differences": differences,
            "match_confidence": similarity
        }
    
    def verify_function_signature(
        self,
        func_name: str,
        claimed_signature: str,
        file_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Verify that a function signature matches the actual function.
        
        Args:
            func_name: Name of the function
            claimed_signature: The signature claimed by LLM (e.g., "def func(arg1: str, arg2: int)")
            file_path: Optional specific file to check
        
        Returns:
            Dict with 'matches', 'actual_signature', 'differences'
        """
        verification = self.verify_function_exists(func_name, file_path)
        
        if not verification.get("exists"):
            return {
                "matches": False,
                "error": f"Function '{func_name}' does not exist",
                "match_confidence": 0.0
            }
        
        actual_signature = verification.get("signature", "")
        
        # Normalize signatures for comparison
        normalized_claimed = self._normalize_signature(claimed_signature)
        normalized_actual = self._normalize_signature(actual_signature)
        
        similarity = SequenceMatcher(None, normalized_claimed, normalized_actual).ratio()
        
        return {
            "matches": similarity >= 0.9,  # 90% similarity for signatures
            "similarity": similarity,
            "actual_signature": actual_signature,
            "claimed_signature": claimed_signature,
            "file_path": verification.get("file_path"),
            "line": verification.get("line"),
            "match_confidence": similarity
        }
    
    def verify_framework(self, file_path: str) -> Dict[str, Any]:
        """
        Detect and verify the framework used in a file.
        
        Args:
            file_path: Path to the file to analyze
        
        Returns:
            Dict with 'framework', 'confidence', 'indicators', and 'decorators'
        """
        file_data = self.code_reader.read_file(file_path)
        if not file_data.get("success"):
            return {
                "framework": "unknown",
                "confidence": 0.0,
                "error": f"Could not read file: {file_path}"
            }
        
        content = file_data["content"]
        parsed = self.ast_parser.parse_file(file_path)
        
        indicators = []
        framework_score = {}
        
        # Check imports
        imports = parsed.get("imports", [])
        for imp in imports:
            module = imp.get("module", "").lower()
            if "fastapi" in module:
                framework_score["fastapi"] = framework_score.get("fastapi", 0) + 3
                indicators.append(f"Import: {imp.get('module')}")
            elif "flask" in module:
                framework_score["flask"] = framework_score.get("flask", 0) + 3
                indicators.append(f"Import: {imp.get('module')}")
            elif "react" in module or "vue" in module or "angular" in module:
                framework_score["frontend"] = framework_score.get("frontend", 0) + 2
                indicators.append(f"Import: {imp.get('module')}")
        
        # Check decorators in functions
        functions = parsed.get("functions", [])
        for func in functions:
            decorators = func.get("decorators", [])
            for decorator in decorators:
                decorator_str = str(decorator).lower()
                if "@app.post" in decorator_str or "@app.get" in decorator_str or "@router" in decorator_str:
                    framework_score["fastapi"] = framework_score.get("fastapi", 0) + 2
                    indicators.append(f"Decorator: {decorator}")
                elif "@app.route" in decorator_str:
                    framework_score["flask"] = framework_score.get("flask", 0) + 2
                    indicators.append(f"Decorator: {decorator}")
        
        # Check content patterns
        if "@app.post" in content or "@app.get" in content or "@router.post" in content:
            framework_score["fastapi"] = framework_score.get("fastapi", 0) + 1
        if "@app.route" in content:
            framework_score["flask"] = framework_score.get("flask", 0) + 1
        if "async def" in content and ("FastAPI" in content or "from fastapi" in content):
            framework_score["fastapi"] = framework_score.get("fastapi", 0) + 1
        
        # Determine framework
        if framework_score:
            detected_framework = max(framework_score.items(), key=lambda x: x[1])
            framework_name = detected_framework[0]
            confidence = min(1.0, detected_framework[1] / 5.0)  # Normalize to 0-1
        else:
            framework_name = "unknown"
            confidence = 0.0
        
        return {
            "framework": framework_name,
            "confidence": confidence,
            "indicators": indicators,
            "score": framework_score,
            "file_path": file_path
        }
    
    def verify_logging_exists(
        self,
        pattern: str,
        file_path: str
    ) -> Dict[str, Any]:
        """
        Verify that logging with a specific pattern exists in a file.
        
        Args:
            pattern: Pattern to search for (e.g., "[LINE_ITEMS]", "Inserted.*line items")
            file_path: File to search in
        
        Returns:
            Dict with 'exists', 'matches', 'lines', and 'context'
        """
        file_data = self.code_reader.read_file(file_path)
        if not file_data.get("success"):
            return {
                "exists": False,
                "error": f"Could not read file: {file_path}",
                "match_confidence": 0.0
            }
        
        content = file_data["content"]
        lines = content.split('\n')
        
        # Search for pattern
        matches = []
        try:
            regex = re.compile(pattern, re.IGNORECASE)
            for i, line in enumerate(lines, 1):
                if regex.search(line):
                    # Get context (3 lines before and after)
                    start_idx = max(0, i - 4)
                    end_idx = min(len(lines), i + 3)
                    context = '\n'.join(lines[start_idx:end_idx])
                    matches.append({
                        "line": i,
                        "content": line.strip(),
                        "context": context
                    })
        except re.error:
            # If pattern is not valid regex, do simple string search
            for i, line in enumerate(lines, 1):
                if pattern.lower() in line.lower():
                    start_idx = max(0, i - 4)
                    end_idx = min(len(lines), i + 3)
                    context = '\n'.join(lines[start_idx:end_idx])
                    matches.append({
                        "line": i,
                        "content": line.strip(),
                        "context": context
                    })
        
        return {
            "exists": len(matches) > 0,
            "matches": matches,
            "count": len(matches),
            "file_path": file_path,
            "pattern": pattern,
            "match_confidence": 1.0 if matches else 0.0
        }
    
    def compare_code_examples(
        self,
        claimed: str,
        actual: str
    ) -> Dict[str, Any]:
        """
        Compare two code examples and find differences.
        
        Args:
            claimed: Code example from LLM
            actual: Actual code from file
        
        Returns:
            Dict with 'similarity', 'matches', 'differences', and 'normalized_versions'
        """
        # Normalize both
        normalized_claimed = self._normalize_code(claimed)
        normalized_actual = self._normalize_code(actual)
        
        # Calculate similarity
        similarity = SequenceMatcher(None, normalized_claimed, normalized_actual).ratio()
        
        # Find differences
        differences = self._find_code_differences(claimed, actual)
        
        return {
            "similarity": similarity,
            "matches": similarity >= 0.85,
            "differences": differences,
            "normalized_claimed": normalized_claimed,
            "normalized_actual": normalized_actual,
            "match_confidence": similarity
        }
    
    def _format_function_signature(self, func_def: Dict[str, Any]) -> str:
        """Format function definition into a signature string."""
        name = func_def.get("name", "")
        args = func_def.get("args", [])
        is_async = func_def.get("is_async", False)
        return_type = func_def.get("return_type")
        
        async_prefix = "async " if is_async else ""
        args_str = ", ".join(args) if args else ""
        return_suffix = f" -> {return_type}" if return_type else ""
        
        return f"{async_prefix}def {name}({args_str}){return_suffix}"
    
    def _normalize_code(self, code: str) -> str:
        """Normalize code for comparison (remove whitespace, normalize quotes, etc.)."""
        # Remove leading/trailing whitespace from each line
        lines = [line.rstrip() for line in code.split('\n')]
        # Remove empty lines
        lines = [line for line in lines if line.strip()]
        # Join and normalize whitespace
        normalized = ' '.join(lines)
        # Normalize quotes
        normalized = normalized.replace("'", '"')
        # Remove extra spaces
        normalized = re.sub(r'\s+', ' ', normalized)
        return normalized.strip()
    
    def _normalize_signature(self, signature: str) -> str:
        """Normalize function signature for comparison."""
        # Remove extra whitespace
        normalized = re.sub(r'\s+', ' ', signature.strip())
        # Normalize quotes
        normalized = normalized.replace("'", '"')
        # Remove type hints for comparison (optional)
        # normalized = re.sub(r':\s*\w+', '', normalized)
        return normalized.lower()
    
    def _find_similar_snippet(self, claimed: str, actual: str) -> Optional[str]:
        """Find a similar snippet in actual code."""
        claimed_lines = [l.strip() for l in claimed.split('\n') if l.strip()]
        if not claimed_lines:
            return None
        
        actual_lines = actual.split('\n')
        
        # Try to find matching sequence
        for i in range(len(actual_lines) - len(claimed_lines) + 1):
            candidate = '\n'.join(actual_lines[i:i+len(claimed_lines)])
            normalized_candidate = self._normalize_code(candidate)
            normalized_claimed = self._normalize_code(claimed)
            
            similarity = SequenceMatcher(None, normalized_claimed, normalized_candidate).ratio()
            if similarity >= 0.7:  # 70% similarity threshold
                return candidate
        
        return None
    
    def _find_code_differences(self, claimed: str, actual: str) -> List[Dict[str, Any]]:
        """Find specific differences between claimed and actual code."""
        differences = []
        
        claimed_lines = claimed.split('\n')
        actual_lines = actual.split('\n')
        
        # Use difflib to find differences
        matcher = SequenceMatcher(None, claimed_lines, actual_lines)
        
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == 'replace':
                differences.append({
                    "type": "replacement",
                    "claimed_lines": (i1 + 1, i2),
                    "actual_lines": (j1 + 1, j2),
                    "claimed_code": '\n'.join(claimed_lines[i1:i2]),
                    "actual_code": '\n'.join(actual_lines[j1:j2])
                })
            elif tag == 'delete':
                differences.append({
                    "type": "deletion",
                    "claimed_lines": (i1 + 1, i2),
                    "claimed_code": '\n'.join(claimed_lines[i1:i2])
                })
            elif tag == 'insert':
                differences.append({
                    "type": "insertion",
                    "actual_lines": (j1 + 1, j2),
                    "actual_code": '\n'.join(actual_lines[j1:j2])
                })
        
        return differences
    
    def find_similar_function_name(
        self,
        wrong_name: str,
        min_similarity: float = 0.75,
        file_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Find similar function names in codebase using fuzzy matching.
        
        Args:
            wrong_name: The incorrect function name to find a match for
            min_similarity: Minimum similarity score (0.0-1.0) to consider a match
            file_path: Optional specific file to search in. If None, searches entire codebase.
            
        Returns:
            Dict with 'found', 'correct_name', 'similarity', 'file_path', 'line', 'signature'
        """
        # First, try exact match
        exact_match = self.verify_function_exists(wrong_name, file_path)
        if exact_match.get("exists"):
            return {
                "found": True,
                "correct_name": wrong_name,
                "similarity": 1.0,
                "file_path": exact_match.get("file_path"),
                "line": exact_match.get("line"),
                "signature": exact_match.get("signature"),
                "is_async": exact_match.get("is_async", False)
            }
        
        # If no exact match and rapidfuzz not available, use SequenceMatcher fallback
        if not RAPIDFUZZ_AVAILABLE:
            return self._find_similar_with_sequence_matcher(wrong_name, min_similarity, file_path)
        
        # Collect all function names from codebase
        all_functions = self._get_all_function_names(file_path)
        
        if not all_functions:
            return {
                "found": False,
                "error": "No functions found in codebase",
                "similarity": 0.0
            }
        
        # Use rapidfuzz to find best match
        # Try different matching strategies
        best_match = None
        best_score = 0.0
        best_name = None
        
        for func_name, func_info in all_functions.items():
            # Try ratio (overall similarity)
            ratio_score = fuzz.ratio(wrong_name.lower(), func_name.lower()) / 100.0
            # Try partial_ratio (substring similarity)
            partial_score = fuzz.partial_ratio(wrong_name.lower(), func_name.lower()) / 100.0
            # Try token_sort_ratio (order-independent)
            token_sort_score = fuzz.token_sort_ratio(wrong_name.lower(), func_name.lower()) / 100.0
            # Try token_set_ratio (set-based)
            token_set_score = fuzz.token_set_ratio(wrong_name.lower(), func_name.lower()) / 100.0
            
            # Use weighted average
            combined_score = (
                ratio_score * 0.3 +
                partial_score * 0.2 +
                token_sort_score * 0.25 +
                token_set_score * 0.25
            )
            
            if combined_score > best_score:
                best_score = combined_score
                best_name = func_name
                best_match = func_info
        
        if best_score >= min_similarity and best_name:
            return {
                "found": True,
                "correct_name": best_name,
                "similarity": best_score,
                "file_path": best_match.get("file_path"),
                "line": best_match.get("line"),
                "signature": best_match.get("signature"),
                "is_async": best_match.get("is_async", False),
                "match_type": "fuzzy"
            }
        
        return {
            "found": False,
            "error": f"No similar function found (best match: {best_name} with {best_score:.2%} similarity)",
            "similarity": best_score,
            "best_candidate": best_name
        }
    
    def _get_all_function_names(self, file_path: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
        """
        Get all function names from codebase or specific file.
        
        Args:
            file_path: Optional specific file. If None, searches entire codebase.
            
        Returns:
            Dict mapping function names to their info (file_path, line, signature, etc.)
        """
        all_functions = {}
        
        if file_path:
            # Get functions from specific file
            parsed = self.ast_parser.parse_file(file_path)
            if parsed.get("success"):
                for func in parsed.get("functions", []):
                    func_name = func.get("name")
                    if func_name:
                        all_functions[func_name] = {
                            "file_path": file_path,
                            "line": func.get("line"),
                            "signature": self._format_function_signature(func),
                            "is_async": func.get("is_async", False)
                        }
        else:
            # Search entire codebase
            # Use grep to find all function definitions
            patterns = [
                r'^\s*def\s+(\w+)\s*\(',
                r'^\s*async\s+def\s+(\w+)\s*\(',
                r'^\s*function\s+(\w+)\s*\(',
                r'^\s*const\s+(\w+)\s*=\s*(?:async\s*)?\(',
                r'^\s*const\s+(\w+)\s*=\s*(?:async\s*)?function'
            ]
            
            for pattern in patterns:
                matches = self.code_explorer.grep_pattern(pattern)
                for file_path, lines in matches.items():
                    for line_num in lines[:1]:  # Just get first occurrence per file
                        # Parse the file to get function details
                        parsed = self.ast_parser.parse_file(file_path)
                        if parsed.get("success"):
                            for func in parsed.get("functions", []):
                                func_name = func.get("name")
                                if func_name and func_name not in all_functions:
                                    all_functions[func_name] = {
                                        "file_path": file_path,
                                        "line": func.get("line"),
                                        "signature": self._format_function_signature(func),
                                        "is_async": func.get("is_async", False)
                                    }
        
        return all_functions
    
    def _find_similar_with_sequence_matcher(
        self,
        wrong_name: str,
        min_similarity: float,
        file_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Fallback fuzzy matching using SequenceMatcher when rapidfuzz is not available."""
        all_functions = self._get_all_function_names(file_path)
        
        if not all_functions:
            return {
                "found": False,
                "error": "No functions found in codebase",
                "similarity": 0.0
            }
        
        best_match = None
        best_score = 0.0
        best_name = None
        
        for func_name, func_info in all_functions.items():
            similarity = SequenceMatcher(None, wrong_name.lower(), func_name.lower()).ratio()
            if similarity > best_score:
                best_score = similarity
                best_name = func_name
                best_match = func_info
        
        if best_score >= min_similarity and best_name:
            return {
                "found": True,
                "correct_name": best_name,
                "similarity": best_score,
                "file_path": best_match.get("file_path"),
                "line": best_match.get("line"),
                "signature": best_match.get("signature"),
                "is_async": best_match.get("is_async", False),
                "match_type": "sequence_matcher"
            }
        
        return {
            "found": False,
            "error": f"No similar function found (best match: {best_name} with {best_score:.2%} similarity)",
            "similarity": best_score,
            "best_candidate": best_name
        }

