"""
Response Rewriter Service

Automatically fixes common errors in LLM responses by replacing wrong function names,
fixing file paths, correcting code examples, and enforcing format requirements.
"""

import logging
import re
from typing import Dict, Any, List, Optional, Tuple
from backend.services.code_verifier import CodeVerifier

logger = logging.getLogger("owlin.services.response_rewriter")


class ResponseRewriter:
    """Service for automatically fixing errors in LLM responses."""
    
    def __init__(self, code_verifier: Optional[CodeVerifier] = None):
        """
        Initialize the response rewriter.
        
        Args:
            code_verifier: CodeVerifier instance for verifying claims
        """
        self.code_verifier = code_verifier
        logger.info("ResponseRewriter initialized")
    
    def fix_function_names(
        self,
        response: str,
        verified_functions: Dict[str, Dict[str, Any]]
    ) -> str:
        """
        Replace wrong function names with correct ones based on verification.
        Uses CodeVerifier to search codebase with fuzzy matching instead of hardcoded mappings.
        
        Args:
            response: Response text
            verified_functions: Dict mapping wrong names to verification results
            
        Returns:
            Fixed response with correct function names
        """
        fixed_response = response
        
        for wrong_name, verification in verified_functions.items():
            correct_name = None
            
            if not verification.get("exists"):
                # Function doesn't exist - use CodeVerifier to find similar function in codebase
                if self.code_verifier:
                    fuzzy_match = self.code_verifier.find_similar_function_name(
                        wrong_name, 
                        min_similarity=0.75
                    )
                    if fuzzy_match.get("found"):
                        correct_name = fuzzy_match.get("correct_name")
                        logger.info(f"Found fuzzy match: {wrong_name} -> {correct_name} (similarity: {fuzzy_match.get('similarity', 0):.0%})")
                
                # Fallback: try to find correct name from response context (old method)
                if not correct_name:
                    correct_name = self._find_correct_function_name(wrong_name, response)
                
                if correct_name:
                    # Replace wrong name with correct one
                    pattern = rf'\b{re.escape(wrong_name)}\s*\('
                    fixed_response = re.sub(pattern, f"{correct_name}(", fixed_response)
                    logger.info(f"Fixed function name: {wrong_name} -> {correct_name}")
            else:
                # Function exists but might have wrong name variant
                # Extract actual name from signature
                if "signature" in verification:
                    sig = verification["signature"]
                    match = re.search(r'(?:async\s+)?def\s+(\w+)', sig)
                    if match:
                        actual_name = match.group(1)
                        if actual_name != wrong_name:
                            correct_name = actual_name
                            pattern = rf'\b{re.escape(wrong_name)}\s*\('
                            fixed_response = re.sub(pattern, f"{correct_name}(", fixed_response)
                            logger.info(f"Fixed function name: {wrong_name} -> {correct_name}")
                elif "fuzzy_match" in verification:
                    # Use fuzzy match suggestion if available
                    fuzzy_match = verification.get("fuzzy_match", {})
                    if fuzzy_match.get("found"):
                        correct_name = fuzzy_match.get("correct_name")
                        pattern = rf'\b{re.escape(wrong_name)}\s*\('
                        fixed_response = re.sub(pattern, f"{correct_name}(", fixed_response)
                        logger.info(f"Fixed function name using fuzzy match: {wrong_name} -> {correct_name}")
        
        return fixed_response
    
    def fix_file_paths(
        self,
        response: str,
        actual_paths: Dict[str, str]
    ) -> str:
        """
        Replace generic file paths with actual full paths.
        
        Args:
            response: Response text
            actual_paths: Dict mapping generic names to actual paths
            
        Returns:
            Fixed response with actual file paths
        """
        fixed_response = response
        
        for generic_path, actual_path in actual_paths.items():
            # Replace generic paths like "file.py:123" with "backend/path/to/file.py:123"
            pattern = rf'\b{re.escape(generic_path)}:(\d+)'
            replacement = f"{actual_path}:\\1"
            fixed_response = re.sub(pattern, replacement, fixed_response)
            logger.info(f"Fixed file path: {generic_path} -> {actual_path}")
        
        return fixed_response
    
    def fix_code_examples(
        self,
        response: str,
        verified_code: Dict[str, Dict[str, Any]]
    ) -> str:
        """
        Replace made-up code examples with actual code from files.
        
        Uses normalized code comparison with similarity matching to find and replace code snippets.
        This is more robust than using first 100 chars or exact string matching.
        
        Args:
            response: Response text
            verified_code: Dict mapping claimed code to verification results
                          (key MUST be claimed_code from response, not actual_code)
            
        Returns:
            Fixed response with actual code examples
        """
        from difflib import SequenceMatcher
        
        fixed_response = response
        replacements_made = 0
        
        for claimed_code, verification in verified_code.items():
            # Ensure we have the claimed_code in verification for safety
            if "claimed_code" not in verification:
                verification["claimed_code"] = claimed_code
            
            if not verification.get("matches") and verification.get("actual_code"):
                # Replace claimed code with actual code
                actual_code = verification["actual_code"]
                
                # Normalize claimed code for comparison
                normalized_claimed = self._normalize_code(claimed_code)
                
                # Find all code blocks in response
                code_block_pattern = r'```(?:python|typescript|javascript|js|ts|tsx|jsx)?\n(.*?)```'
                
                # Track which blocks we've already replaced to avoid double replacement
                replaced_blocks = set()
                
                def replace_matching_code_block(match):
                    """Replace code block if it matches claimed code with very high similarity."""
                    block_content = match.group(1)
                    block_key = match.group(0)  # Use full block as key to track replacements
                    
                    # Skip if already replaced
                    if block_key in replaced_blocks:
                        return match.group(0)
                    
                    normalized_block = self._normalize_code(block_content)
                    
                    # Calculate similarity between normalized versions
                    similarity = SequenceMatcher(None, normalized_claimed, normalized_block).ratio()
                    
                    # Use very high similarity threshold (0.95) to only replace code that's essentially the same
                    # This prevents replacing similar but different code (e.g., .upper() vs .lower())
                    # The 0.85 threshold from verification is for "does it match", but for replacement
                    # we need to be more strict to avoid replacing code that's similar but intentionally different
                    if similarity >= 0.95:
                        # Replace with actual code
                        lang = match.group(0).split('\n')[0].replace('```', '').strip() or 'python'
                        replaced_blocks.add(block_key)
                        return f"```{lang}\n{actual_code}\n```"
                    
                    return match.group(0)
                
                # Try to replace in code blocks first (most common case)
                before_replace = fixed_response
                fixed_response = re.sub(code_block_pattern, replace_matching_code_block, fixed_response, flags=re.DOTALL)
                
                # Verify replacement happened
                if fixed_response != before_replace:
                    replacements_made += 1
                    logger.info(f"Fixed code example at {verification.get('file_path', 'unknown')} using similarity matching")
                else:
                    # Fallback: try direct string replacement if code appears outside code blocks
                    # Only do this if the claimed code is unique enough (not too short)
                    if len(claimed_code.strip()) > 20 and claimed_code in fixed_response:
                        fixed_response = fixed_response.replace(claimed_code, actual_code)
                        replacements_made += 1
                        logger.info(f"Fixed code example at {verification.get('file_path', 'unknown')} using direct replacement")
                    else:
                        # Last resort: try normalized matching for code blocks that weren't caught
                        for match in re.finditer(code_block_pattern, fixed_response, re.DOTALL):
                            block_content = match.group(1)
                            normalized_block = self._normalize_code(block_content)
                            similarity = SequenceMatcher(None, normalized_claimed, normalized_block).ratio()
                            
                            # Use very high threshold (0.95) to avoid replacing similar but different code
                            if similarity >= 0.95:
                                lang = match.group(0).split('\n')[0].replace('```', '').strip() or 'python'
                                full_block = match.group(0)
                                replacement = f"```{lang}\n{actual_code}\n```"
                                fixed_response = fixed_response.replace(full_block, replacement, 1)  # Replace only first occurrence
                                replacements_made += 1
                                logger.info(f"Fixed code example at {verification.get('file_path', 'unknown')} using fallback normalized matching")
                                break
        
        if replacements_made > 0:
            logger.info(f"fix_code_examples: Made {replacements_made} replacement(s)")
        else:
            logger.debug(f"fix_code_examples: No replacements made (verified {len(verified_code)} code snippet(s))")
        
        return fixed_response
    
    def _normalize_code(self, code: str) -> str:
        """
        Normalize code for comparison (remove whitespace, normalize quotes, etc.).
        
        This matches the normalization used in CodeVerifier for consistent matching.
        
        Args:
            code: Code string to normalize
            
        Returns:
            Normalized code string
        """
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
    
    def enforce_format(self, response: str) -> str:
        """
        Enforce text-first format by moving large code blocks to end or removing them.
        
        Args:
            response: Response text
            
        Returns:
            Formatted response with enforced structure
        """
        # Find all code blocks
        code_block_pattern = r'```(?:python|typescript|javascript|js|ts|tsx|jsx)?\n(.*?)```'
        code_blocks = re.findall(code_block_pattern, response, re.DOTALL)
        
        # Check for large code blocks (> 5 lines)
        large_blocks = []
        for block in code_blocks:
            lines = [l for l in block.split('\n') if l.strip()]
            if len(lines) > 5:
                large_blocks.append(block)
        
        if large_blocks:
            # Remove large blocks or truncate them
            for block in large_blocks:
                lines = block.split('\n')
                if len(lines) > 5:
                    # Replace with truncated version
                    truncated = '\n'.join(lines[:5]) + "\n# ... (truncated - use READ command to see full code)"
                    response = response.replace(block, truncated)
                    logger.info(f"Truncated large code block ({len(lines)} lines -> 5 lines)")
        
        # Ensure text comes before code
        # Check if response starts with code block
        if response.strip().startswith('```'):
            # Move code blocks to end
            code_section = ""
            text_section = response
            
            for match in re.finditer(code_block_pattern, response, re.DOTALL):
                code_section += match.group(0) + "\n\n"
                text_section = text_section.replace(match.group(0), "")
            
            if code_section:
                response = text_section.strip() + "\n\n**Code Examples:**\n\n" + code_section
        
        return response
    
    def remove_large_code_dumps(self, response: str, max_lines: int = 5) -> str:
        """
        Remove or truncate large code dumps.
        
        Args:
            response: Response text
            max_lines: Maximum lines allowed per code block
            
        Returns:
            Response with large code dumps removed or truncated
        """
        # Find code blocks
        code_block_pattern = r'```(?:python|typescript|javascript|js|ts|tsx|jsx)?\n(.*?)```'
        
        def replace_large_block(match):
            block_content = match.group(1)
            lines = [l for l in block_content.split('\n') if l.strip()]
            
            if len(lines) > max_lines:
                # Truncate
                truncated = '\n'.join(lines[:max_lines])
                return f"```python\n{truncated}\n# ... ({len(lines) - max_lines} more lines - use READ command to see full code)\n```"
            return match.group(0)
        
        fixed_response = re.sub(code_block_pattern, replace_large_block, response, flags=re.DOTALL)
        
        return fixed_response
    
    def rewrite_response(
        self,
        response: str,
        verification_results: Optional[Dict[str, Any]] = None,
        files_read: Optional[set] = None
    ) -> str:
        """
        Comprehensive response rewriting using all fix methods.
        
        Args:
            response: Response text to fix
            verification_results: Optional verification results from CodeVerifier
            files_read: Optional set of files that were read
            
        Returns:
            Rewritten response with fixes applied
        """
        fixed_response = response
        
        if verification_results:
            # Fix function names
            if "function_verifications" in verification_results:
                fixed_response = self.fix_function_names(
                    fixed_response,
                    verification_results["function_verifications"]
                )
            
            # Fix code examples
            if "code_verifications" in verification_results:
                fixed_response = self.fix_code_examples(
                    fixed_response,
                    verification_results["code_verifications"]
                )
        
        # Fix file paths if files_read provided
        if files_read:
            # Build mapping of generic names to actual paths
            generic_to_actual = {}
            for file_path in files_read:
                filename = file_path.split('/')[-1]
                if filename not in generic_to_actual:
                    generic_to_actual[filename] = file_path
            
            fixed_response = self.fix_file_paths(fixed_response, generic_to_actual)
        
        # Enforce format
        fixed_response = self.enforce_format(fixed_response)
        
        # Remove large code dumps
        fixed_response = self.remove_large_code_dumps(fixed_response)
        
        return fixed_response
    
    def _find_correct_function_name(self, wrong_name: str, response: str) -> Optional[str]:
        """
        Try to find the correct function name from context in response.
        This is a fallback method when CodeVerifier is not available.
        
        Args:
            wrong_name: Wrong function name
            response: Response text that might contain correct name
            
        Returns:
            Correct function name if found, None otherwise
        """
        # First, try to use CodeVerifier if available (preferred method)
        if self.code_verifier:
            fuzzy_match = self.code_verifier.find_similar_function_name(wrong_name, min_similarity=0.75)
            if fuzzy_match.get("found"):
                return fuzzy_match.get("correct_name")
        
        # Fallback: try to find similar function name in response
        # Look for function definitions or calls
        func_pattern = rf'\b(?:async\s+)?def\s+(\w*{re.escape(wrong_name[:4])}\w*)\s*\('
        matches = re.findall(func_pattern, response, re.IGNORECASE)
        if matches:
            return matches[0]
        
        # Try broader pattern
        func_pattern2 = rf'\b(\w*{re.escape(wrong_name[:3])}\w*)\s*\('
        matches2 = re.findall(func_pattern2, response, re.IGNORECASE)
        if matches2:
            # Return the most similar match
            for match in matches2:
                if len(match) >= len(wrong_name) * 0.7:  # At least 70% of original length
                    return match
        
        return None

