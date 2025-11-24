"""
Code Reader Service

Utilities for reading files from the codebase, searching code patterns,
and accessing error logs. Used by the chat assistant to provide code context.
"""

import logging
import os
import re
import time
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

logger = logging.getLogger("owlin.services.code_reader")


class CodeReader:
    """Service for reading and searching code files."""
    
    def __init__(self, repo_root: Optional[Path] = None, cache_ttl: int = 300):
        """
        Initialize the code reader.
        
        Args:
            repo_root: Path to repository root. If None, auto-detect from backend location.
            cache_ttl: Cache TTL in seconds for file reads (default: 300 = 5 minutes)
        """
        if repo_root is None:
            # Auto-detect: backend/services/code_reader.py -> repo root is 2 levels up
            self.repo_root = Path(__file__).resolve().parent.parent.parent
        else:
            self.repo_root = Path(repo_root).resolve()
        
        self.backend_dir = self.repo_root / "backend"
        self.frontend_dir = self.repo_root / "frontend_clean"
        self.cache_ttl = cache_ttl
        self._file_cache: Dict[str, Tuple[float, Dict[str, Any]]] = {}  # {file_path: (timestamp, file_data)}
        # Get max cache size from config if available
        try:
            from backend.services.explorer_config import get_config
            self._max_cache_size = get_config().file_cache_size
        except ImportError:
            self._max_cache_size = 50  # Default fallback
        
        # Cache statistics
        self._cache_hits = 0
        self._cache_misses = 0
        
        logger.info(f"CodeReader initialized with repo_root: {self.repo_root}")
    
    def _should_skip_file(self, file_path: Path) -> bool:
        """
        Check if file should be skipped (venv, node_modules, test files, generated code, etc.).
        
        Args:
            file_path: Path object or string path to check
            
        Returns:
            True if file should be skipped, False otherwise
        """
        if isinstance(file_path, Path):
            path_str = str(file_path)
        else:
            path_str = str(file_path)
        
        # Existing filters for virtual environments
        skip_patterns = [".venv", "venv", "node_modules", "__pycache__", ".git"]
        if any(pattern in path_str for pattern in skip_patterns):
            return True
        
        # Enhanced filters for "rubbish code" - test files, generated code, build artifacts
        skip_patterns_extended = [
            # Test directories and files
            "__tests__", "__mocks__", "__test__",
            ".test.", ".spec.", ".test.ts", ".test.tsx", ".test.js", ".test.py",
            "test_", "spec_",
            # Generated/minified files
            ".min.js", ".min.css", ".d.ts", ".map",
            # Build artifacts
            "dist/", "build/", ".next/", "out/", ".turbo/",
            # Coverage and reports
            "coverage/", ".nyc_output/",
            # Lock files (too large, not useful for code analysis)
            "package-lock.json", "yarn.lock", "pnpm-lock.yaml",
            # Generated types and code
            ".generated.", "generated/",
            # Logs and temporary files
            ".log", ".tmp", ".cache",
            # Database files
            "*.sqlite", "*.db",
            # Data uploads (exclude from code analysis)
            "data/uploads/",
        ]
        
        # Check filename patterns
        filename_lower = Path(path_str).name.lower()
        if any(pattern in filename_lower for pattern in [".test.", ".spec.", ".min.", ".d.ts", ".map"]):
            return True
        
        # Check for database files by extension
        if filename_lower.endswith((".sqlite", ".db")):
            return True
        
        # Check path patterns
        path_lower = path_str.lower()
        if any(pattern in path_lower for pattern in skip_patterns_extended):
            return True
        
        return False
    
    def read_file(self, file_path: str, max_lines: Optional[int] = None, use_cache: bool = True) -> Dict[str, Any]:
        """
        Read a file from the codebase.
        
        Args:
            file_path: Relative path from repo root (e.g., "backend/main.py")
            max_lines: Maximum number of lines to read (None = all)
            use_cache: Whether to use cached file content if available
            
        Returns:
            Dict with file contents, line count, and metadata
        """
        # Check cache first
        if use_cache and max_lines is None:
            cache_key = file_path
            if cache_key in self._file_cache:
                cached_time, cached_data = self._file_cache[cache_key]
                if time.time() - cached_time < self.cache_ttl:
                    logger.debug(f"Cache hit for file: {file_path}")
                    self._cache_hits += 1
                    # Log cache hit ratio periodically (every 10 hits)
                    if self._cache_hits % 10 == 0:
                        total = self._cache_hits + self._cache_misses
                        if total > 0:
                            hit_ratio = self._cache_hits / total
                            logger.info(f"Cache hit ratio: {hit_ratio:.1%} ({self._cache_hits} hits, {self._cache_misses} misses)")
                    return cached_data
                else:
                    # Cache expired, remove it
                    del self._file_cache[cache_key]
                    self._cache_misses += 1
            else:
                self._cache_misses += 1
        else:
            if use_cache:
                self._cache_misses += 1
        
        try:
            # Resolve path relative to repo root
            full_path = self.repo_root / file_path
            
            # Security: ensure path is within repo
            if not str(full_path.resolve()).startswith(str(self.repo_root.resolve())):
                raise ValueError(f"Path {file_path} is outside repository root")
            
            if not full_path.exists():
                return {
                    "success": False,
                    "error": f"File not found: {file_path}",
                    "file_path": file_path
                }
            
            if not full_path.is_file():
                return {
                    "success": False,
                    "error": f"Path is not a file: {file_path}",
                    "file_path": file_path
                }
            
            # Read file
            with open(full_path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
            
            total_lines = len(lines)
            
            # Limit lines if requested
            if max_lines and len(lines) > max_lines:
                lines = lines[:max_lines]
                truncated = True
            else:
                truncated = False
            
            content = "".join(lines)
            
            result = {
                "success": True,
                "file_path": file_path,
                "content": content,
                "total_lines": total_lines,
                "lines_read": len(lines),
                "truncated": truncated,
                "file_size": full_path.stat().st_size
            }
            
            # Cache full file reads (not truncated)
            if use_cache and not truncated and max_lines is None:
                cache_key = file_path
                # Manage cache size
                if len(self._file_cache) >= self._max_cache_size:
                    # Remove oldest entry
                    oldest_key = min(
                        self._file_cache.keys(),
                        key=lambda k: self._file_cache[k][0]
                    )
                    del self._file_cache[oldest_key]
                    logger.debug(f"Cache full, removed oldest entry: {oldest_key}")
                
                self._file_cache[cache_key] = (time.time(), result)
            
            logger.debug(f"Successfully read file {file_path} ({len(lines)} lines, {full_path.stat().st_size} bytes)")
            return result
            
        except FileNotFoundError:
            logger.warning(f"File not found: {file_path}")
            return {
                "success": False,
                "error": f"File not found: {file_path}",
                "file_path": file_path
            }
        except PermissionError as e:
            logger.error(f"Permission denied reading file {file_path}: {e}")
            return {
                "success": False,
                "error": f"Permission denied: {file_path}",
                "file_path": file_path
            }
        except Exception as e:
            logger.error(f"Failed to read file {file_path}: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "file_path": file_path
            }
    
    def read_file_lines(self, file_path: str, start_line: int, end_line: int) -> Dict[str, Any]:
        """
        Read specific lines from a file.
        
        Args:
            file_path: Relative path from repo root
            start_line: Start line number (1-indexed)
            end_line: End line number (1-indexed, inclusive)
            
        Returns:
            Dict with file contents for specified lines
        """
        try:
            full_path = self.repo_root / file_path
            
            if not full_path.exists():
                return {
                    "success": False,
                    "error": f"File not found: {file_path}",
                    "file_path": file_path
                }
            
            with open(full_path, "r", encoding="utf-8", errors="replace") as f:
                all_lines = f.readlines()
            
            total_lines = len(all_lines)
            
            # Adjust to 0-indexed
            start_idx = max(0, start_line - 1)
            end_idx = min(total_lines, end_line)
            
            selected_lines = all_lines[start_idx:end_idx]
            content = "".join(selected_lines)
            
            return {
                "success": True,
                "file_path": file_path,
                "content": content,
                "start_line": start_line,
                "end_line": end_line,
                "total_lines": total_lines,
                "lines_read": len(selected_lines)
            }
            
        except Exception as e:
            logger.error(f"Failed to read lines from {file_path}: {e}")
            return {
                "success": False,
                "error": str(e),
                "file_path": file_path
            }
    
    def search_codebase(self, query: str, file_pattern: str = "*.py", max_results: int = 10, context_lines: int = 5) -> List[Dict[str, Any]]:
        """
        Search for code patterns in the codebase with enhanced matching.
        
        Args:
            query: Search query (substring match, supports function/class name patterns)
            file_pattern: File pattern to search (e.g., "*.py", "*.tsx", or comma-separated "*.py,*.tsx")
            max_results: Maximum number of results
            context_lines: Number of lines before/after to include in context
            
        Returns:
            List of matches with file path, line number, and context
        """
        results = []
        
        try:
            # Parse multiple file patterns if provided
            if "," in file_pattern:
                patterns = [p.strip() for p in file_pattern.split(",")]
            else:
                patterns = [file_pattern]
            
            # Search in backend and frontend
            search_dirs = []
            if self.backend_dir.exists():
                search_dirs.append(self.backend_dir)
            if self.frontend_dir.exists():
                search_dirs.append(self.frontend_dir)
            
            query_lower = query.lower()
            query_words = query_lower.split()
            
            # Enhanced matching: check for function/class definitions
            is_function_query = any(word in query_lower for word in ["function", "def", "class", "method"])
            
            for search_dir in search_dirs:
                for pattern in patterns:
                    for file_path in search_dir.rglob(pattern):
                        # Skip virtual environments and other excluded directories
                        if self._should_skip_file(file_path):
                            continue
                        
                        try:
                            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                                lines = f.readlines()
                            
                            # Search for query in file
                            for line_num, line in enumerate(lines, 1):
                                line_lower = line.lower()
                                
                                # Basic substring match
                                if query_lower in line_lower:
                                    match_score = 1
                                # Multi-word match (all words present)
                                elif len(query_words) > 1 and all(word in line_lower for word in query_words):
                                    match_score = 0.8
                                # Function/class definition match
                                elif is_function_query and any(
                                    f"def {query_words[-1]}" in line_lower or
                                    f"class {query_words[-1]}" in line_lower or
                                    f"function {query_words[-1]}" in line_lower or
                                    f"const {query_words[-1]}" in line_lower
                                    for word in query_words
                                ):
                                    match_score = 0.9
                                else:
                                    continue
                                
                                # Get relative path
                                rel_path = file_path.relative_to(self.repo_root)
                                
                                # Get enhanced context
                                context = self._get_line_context(lines, line_num - 1, context_lines)
                                
                                results.append({
                                    "file_path": str(rel_path),
                                    "line": line_num,
                                    "content": line.strip(),
                                    "context": context,
                                    "score": match_score
                                })
                                
                                if len(results) >= max_results * 2:  # Get more, then sort
                                    break
                                    
                        except Exception as e:
                            logger.warning(f"Failed to search file {file_path}: {e}")
                            continue
                    
                    if len(results) >= max_results * 2:
                        break
                
                if len(results) >= max_results * 2:
                    break
            
            # Sort by score and return top results
            results.sort(key=lambda x: x.get("score", 0), reverse=True)
            final_results = results[:max_results]
            logger.info(f"Codebase search for '{query}' found {len(final_results)} results")
            return final_results
            
        except Exception as e:
            logger.error(f"Codebase search failed for query '{query}': {e}", exc_info=True)
            return []
    
    def _get_line_context(self, lines: List[str], line_idx: int, context_lines: int = 5) -> str:
        """Get context around a line with line numbers."""
        start = max(0, line_idx - context_lines)
        end = min(len(lines), line_idx + context_lines + 1)
        context = lines[start:end]
        
        # Add line numbers for better readability
        context_with_numbers = []
        for i, line in enumerate(context, start=start + 1):
            context_with_numbers.append(f"{i:4d} | {line}")
        
        return "".join(context_with_numbers)
    
    def get_file_structure(self, directory: str = "backend", max_depth: int = 3) -> Dict[str, Any]:
        """
        Get directory structure of the codebase.
        
        Args:
            directory: Directory to explore (relative to repo root)
            max_depth: Maximum depth to traverse
            
        Returns:
            Dict with directory structure
        """
        try:
            target_dir = self.repo_root / directory
            
            if not target_dir.exists():
                return {
                    "success": False,
                    "error": f"Directory not found: {directory}"
                }
            
            structure = self._build_tree(target_dir, self.repo_root, max_depth, 0)
            
            return {
                "success": True,
                "directory": directory,
                "structure": structure
            }
            
        except Exception as e:
            logger.error(f"Failed to get file structure: {e}")
            return {
                "success": False,
                "error": str(e),
                "directory": directory
            }
    
    def _build_tree(self, dir_path: Path, repo_root: Path, max_depth: int, current_depth: int) -> Dict[str, Any]:
        """Recursively build directory tree."""
        if current_depth >= max_depth:
            return {}
        
        tree = {}
        
        try:
            for item in sorted(dir_path.iterdir()):
                # Skip hidden files and common ignore patterns
                if item.name.startswith(".") or item.name in ["__pycache__", "node_modules", ".git"]:
                    continue
                
                rel_path = item.relative_to(repo_root)
                
                if item.is_dir():
                    tree[item.name] = {
                        "type": "directory",
                        "path": str(rel_path),
                        "children": self._build_tree(item, repo_root, max_depth, current_depth + 1)
                    }
                else:
                    tree[item.name] = {
                        "type": "file",
                        "path": str(rel_path),
                        "size": item.stat().st_size
                    }
        except PermissionError:
            pass
        
        return tree
    
    def read_error_logs(self, log_file: str = "backend_stdout.log", max_lines: int = 50) -> Dict[str, Any]:
        """
        Read recent error logs and extract file references.
        
        Args:
            log_file: Log file name (relative to repo root)
            max_lines: Maximum number of lines to read
            
        Returns:
            Dict with log contents, error count, and extracted file references
        """
        try:
            log_path = self.repo_root / log_file
            
            if not log_path.exists():
                return {
                    "success": False,
                    "error": f"Log file not found: {log_file}",
                    "log_file": log_file
                }
            
            with open(log_path, "r", encoding="utf-8", errors="replace") as f:
                all_lines = f.readlines()
            
            # Get last N lines
            recent_lines = all_lines[-max_lines:] if len(all_lines) > max_lines else all_lines
            content = "".join(recent_lines)
            
            # Count errors and extract file references
            error_count = 0
            file_references = []
            import re
            
            for line in recent_lines:
                line_lower = line.lower()
                if "ERROR" in line or "error" in line_lower or "exception" in line_lower or "traceback" in line_lower:
                    error_count += 1
                    
                    # Try to extract file paths and line numbers from error messages
                    # Pattern: "File \"path/to/file.py\", line 123"
                    file_pattern = r'File\s+["\']([^"\']+\.(?:py|tsx?|ts|jsx?|js))["\']\s*,\s*line\s+(\d+)'
                    matches = re.finditer(file_pattern, line, re.IGNORECASE)
                    for match in matches:
                        file_path = match.group(1)
                        line_num = int(match.group(2))
                        # Normalize path
                        file_path = file_path.replace("\\", "/")
                        # Try to resolve relative to repo root
                        if not file_path.startswith(("backend/", "frontend_clean/", "frontend/")):
                            # Try to find the file
                            resolved = self.resolve_file_path(file_path)
                            if resolved:
                                file_path = resolved
                        file_references.append({
                            "file": file_path,
                            "line": line_num,
                            "error_line": line.strip()
                        })
                    
                    # Also look for patterns like "backend/services/file.py:123"
                    path_line_pattern = r'([a-zA-Z0-9_/\\\.-]+\.(?:py|tsx?|ts|jsx?|js)):(\d+)'
                    matches = re.finditer(path_line_pattern, line)
                    for match in matches:
                        file_path = match.group(1).replace("\\", "/")
                        line_num = int(match.group(2))
                        resolved = self.resolve_file_path(file_path)
                        if resolved:
                            file_references.append({
                                "file": resolved,
                                "line": line_num,
                                "error_line": line.strip()
                            })
            
            # Remove duplicates
            seen = set()
            unique_refs = []
            for ref in file_references:
                key = (ref["file"], ref["line"])
                if key not in seen:
                    seen.add(key)
                    unique_refs.append(ref)
            
            logger.info(f"Read error logs: {error_count} errors found, {len(unique_refs)} file references extracted")
            return {
                "success": True,
                "log_file": log_file,
                "content": content,
                "total_lines": len(all_lines),
                "lines_read": len(recent_lines),
                "error_count": error_count,
                "file_references": unique_refs[:10]  # Limit to 10 references
            }
            
        except FileNotFoundError:
            logger.warning(f"Error log file not found: {log_file}")
            return {
                "success": False,
                "error": f"Log file not found: {log_file}",
                "log_file": log_file
            }
        except Exception as e:
            logger.error(f"Failed to read error logs from {log_file}: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "log_file": log_file
            }
    
    def resolve_file_path(self, file_path: str) -> Optional[str]:
        """
        Intelligently resolve a file path by trying multiple strategies.
        
        Args:
            file_path: File path (can be partial, full, or just filename)
            
        Returns:
            Resolved file path relative to repo root, or None if not found
        """
        # Normalize path separators
        file_path = file_path.replace("\\", "/")
        
        # Strategy 1: Try direct path
        result = self.read_file(file_path)
        if result.get("success"):
            logger.debug(f"Resolved file via direct path: {file_path}")
            return file_path
        
        # Strategy 2: Try with common prefixes
        common_prefixes = ["backend/", "frontend_clean/", "frontend/", "app/"]
        for prefix in common_prefixes:
            prefixed_path = prefix + file_path
            result = self.read_file(prefixed_path)
            if result.get("success"):
                logger.debug(f"Resolved file via prefix {prefix}: {prefixed_path}")
                return prefixed_path
        
        # Strategy 3: If path contains slashes, try removing leading parts
        if "/" in file_path:
            parts = file_path.split("/")
            # Try with just the last 2 parts, then last 3, etc.
            for i in range(1, len(parts)):
                partial_path = "/".join(parts[-i:])
                result = self.read_file(partial_path)
                if result.get("success"):
                    logger.debug(f"Resolved file via partial path: {partial_path}")
                    return partial_path
                
                # Also try with prefixes
                for prefix in common_prefixes:
                    prefixed_partial = prefix + partial_path
                    result = self.read_file(prefixed_partial)
                    if result.get("success"):
                        logger.debug(f"Resolved file via prefix + partial: {prefixed_partial}")
                        return prefixed_partial
        
        # Strategy 4: Search by filename only
        filename = file_path.split("/")[-1]
        found_files = self.find_files_by_name(filename, max_results=1)
        if found_files:
            logger.debug(f"Resolved file via name search: {filename} -> {found_files[0]}")
            return found_files[0]
        
        logger.debug(f"Could not resolve file path after all strategies: {file_path}")
        return None
    
    def read_file_with_context(self, file_path: str, line_number: Optional[int] = None, context_lines: int = 10) -> Dict[str, Any]:
        """
        Read a file with context around a specific line (useful for error debugging).
        
        Args:
            file_path: Relative path from repo root
            line_number: Line number to center context around (1-indexed)
            context_lines: Number of lines before/after to include
            
        Returns:
            Dict with file contents and metadata
        """
        if line_number is None:
            return self.read_file(file_path)
        
        try:
            full_path = self.repo_root / file_path
            
            if not full_path.exists():
                return {
                    "success": False,
                    "error": f"File not found: {file_path}",
                    "file_path": file_path
                }
            
            with open(full_path, "r", encoding="utf-8", errors="replace") as f:
                all_lines = f.readlines()
            
            total_lines = len(all_lines)
            
            # Calculate context range
            start_line = max(1, line_number - context_lines)
            end_line = min(total_lines, line_number + context_lines)
            
            return self.read_file_lines(file_path, start_line, end_line)
            
        except Exception as e:
            logger.error(f"Failed to read file with context {file_path}: {e}")
            return {
                "success": False,
                "error": str(e),
                "file_path": file_path
            }
    
    def find_files_by_name(self, filename: str, max_results: int = 10) -> List[str]:
        """
        Find files by name pattern.
        
        Args:
            filename: Filename to search for (can be partial)
            max_results: Maximum number of results
            
        Returns:
            List of relative file paths
        """
        results = []
        
        try:
            search_dirs = []
            if self.backend_dir.exists():
                search_dirs.append(self.backend_dir)
            if self.frontend_dir.exists():
                search_dirs.append(self.frontend_dir)
            
            filename_lower = filename.lower()
            
            for search_dir in search_dirs:
                for file_path in search_dir.rglob("*"):
                    # Skip virtual environments and other excluded directories
                    if self._should_skip_file(file_path):
                        continue
                    
                    if file_path.is_file() and filename_lower in file_path.name.lower():
                        rel_path = file_path.relative_to(self.repo_root)
                        results.append(str(rel_path))
                        
                        if len(results) >= max_results:
                            return results
            
            return results[:max_results]
            
        except Exception as e:
            logger.error(f"File search failed: {e}")
            return []
    
    def trace_data_flow(self, start_concept: str, end_concept: str) -> List[Dict[str, Any]]:
        """
        Trace data flow from start to end concept.
        
        Args:
            start_concept: Starting point (e.g., "upload", "line items")
            end_concept: Ending point (e.g., "cards", "display")
            
        Returns:
            List of flow steps with files, functions, and data transformations
        """
        flow_path = []
        
        # Common flow patterns in Owlin
        flow_mappings = {
            "upload": {
                "files": ["backend/main.py"],
                "functions": ["upload", "upload_file"],
                "next_steps": ["ocr", "processing"]
            },
            "ocr": {
                "files": ["backend/services/ocr_service.py"],
                "functions": ["process_document_ocr", "_process_with_v2_pipeline"],
                "next_steps": ["parsing", "line_items"]
            },
            "line_items": {
                "files": ["backend/services/ocr_service.py", "backend/app/db.py"],
                "functions": ["_extract_line_items_from_page", "insert_line_items"],
                "next_steps": ["storage", "database"]
            },
            "database": {
                "files": ["backend/app/db.py"],
                "functions": ["insert_line_items", "get_line_items_for_invoice"],
                "next_steps": ["api", "retrieval"]
            },
            "api": {
                "files": ["backend/routes/invoices_submit.py", "backend/main.py"],
                "functions": ["list_invoices", "get_invoice"],
                "next_steps": ["frontend", "display"]
            },
            "frontend": {
                "files": ["frontend_clean/src/lib/api.ts", "frontend_clean/src/pages/Invoices.tsx"],
                "functions": ["fetchInvoices", "useQuery"],
                "next_steps": ["display", "cards"]
            },
            "cards": {
                "files": ["frontend_clean/src/components/InvoiceCard.tsx"],
                "functions": ["InvoiceCard", "render"],
                "next_steps": []
            }
        }
        
        start_lower = start_concept.lower()
        end_lower = end_concept.lower()
        
        # Find starting point
        start_info = None
        for key, info in flow_mappings.items():
            if key in start_lower or start_lower in key:
                start_info = info
                flow_path.append({
                    "step": "start",
                    "concept": key,
                    "files": info["files"],
                    "description": f"Data starts at {key}"
                })
                break
        
        # Trace through intermediate steps
        if start_info:
            current_step = start_info
            visited = set()
            
            while current_step and current_step.get("next_steps"):
                for next_step_name in current_step["next_steps"]:
                    if next_step_name in visited:
                        continue
                    visited.add(next_step_name)
                    
                    # Check if we've reached the end
                    if end_lower in next_step_name or next_step_name in end_lower:
                        if next_step_name in flow_mappings:
                            end_info = flow_mappings[next_step_name]
                            flow_path.append({
                                "step": "end",
                                "concept": next_step_name,
                                "files": end_info["files"],
                                "description": f"Data reaches {next_step_name}"
                            })
                            return flow_path
                    
                    # Add intermediate step
                    if next_step_name in flow_mappings:
                        step_info = flow_mappings[next_step_name]
                        flow_path.append({
                            "step": "intermediate",
                            "concept": next_step_name,
                            "files": step_info["files"],
                            "description": f"Data flows through {next_step_name}"
                        })
                        current_step = step_info
                        break
                else:
                    break
        
        # If we didn't find a path, search for connections
        if not flow_path:
            # Search for files containing both concepts
            start_results = self.search_codebase(start_concept, max_results=10)
            end_results = self.search_codebase(end_concept, max_results=10)
            
            # Filter out virtual environment files
            start_results = [r for r in start_results if not self._should_skip_file(r["file_path"])]
            end_results = [r for r in end_results if not self._should_skip_file(r["file_path"])]
            
            if start_results and end_results:
                flow_path.append({
                    "step": "start",
                    "concept": start_concept,
                    "files": [r["file_path"] for r in start_results[:3]],
                    "description": f"Found code related to {start_concept}"
                })
                flow_path.append({
                    "step": "end",
                    "concept": end_concept,
                    "files": [r["file_path"] for r in end_results[:3]],
                    "description": f"Found code related to {end_concept}"
                })
        
        return flow_path
    
    def map_api_to_frontend(self, api_endpoint: str) -> List[Dict[str, Any]]:
        """
        Find frontend components that consume an API endpoint.
        
        Args:
            api_endpoint: API endpoint path (e.g., "/api/invoices", "/api/upload")
            
        Returns:
            List of frontend files, components, and data flow
        """
        results = []
        
        # Normalize endpoint
        endpoint_clean = api_endpoint.replace("/api/", "").replace("/", "_")
        
        # Search frontend for API calls
        frontend_dir = self.repo_root / "frontend_clean"
        if not frontend_dir.exists():
            return results
        
        # Search for API endpoint references
        search_patterns = [
            f"/api/{endpoint_clean.replace('_', '/')}",
            f"api/{endpoint_clean}",
            endpoint_clean,
            api_endpoint
        ]
        
        for pattern in search_patterns:
            for file_path in frontend_dir.rglob("*.{ts,tsx,js,jsx}"):
                try:
                    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                        content = f.read()
                        if pattern in content.lower():
                            rel_path = file_path.relative_to(self.repo_root)
                            
                            # Try to find the component/function name
                            lines = content.split("\n")
                            component_name = None
                            for i, line in enumerate(lines):
                                if "function" in line or "const" in line or "export" in line:
                                    if "=" in line or "function" in line:
                                        # Extract name
                                        match = re.search(r"(?:function|const|export\s+(?:default\s+)?function)\s+(\w+)", line)
                                        if match:
                                            component_name = match.group(1)
                                            break
                            
                            results.append({
                                "file": str(rel_path),
                                "component": component_name,
                                "endpoint": api_endpoint,
                                "line": next((i for i, line in enumerate(lines, 1) if pattern.lower() in line.lower()), None)
                            })
                except Exception as e:
                    logger.warning(f"Failed to search file {file_path}: {e}")
                    continue
        
        return results[:10]  # Limit results
    
    def analyze_database_flow(self, table_name: str, operation: str = "select") -> Dict[str, Any]:
        """
        Analyze how data flows through database operations.
        
        Args:
            table_name: Database table name (e.g., "invoices", "invoice_line_items")
            operation: Operation type ("select", "insert", "update", "delete")
            
        Returns:
            Dict with insert/select operations, related code, data transformations
        """
        results = {
            "table": table_name,
            "operation": operation,
            "operations": [],
            "related_files": [],
            "data_flow": []
        }
        
        # Search for database operations
        search_query = f"{operation}.*{table_name}|{table_name}.*{operation}"
        
        # Search in backend
        backend_dir = self.repo_root / "backend"
        if backend_dir.exists():
            for file_path in backend_dir.rglob("*.py"):
                try:
                    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                        content = f.read()
                        if table_name.lower() in content.lower() and operation.lower() in content.lower():
                            rel_path = file_path.relative_to(self.repo_root)
                            
                            # Find specific operations
                            lines = content.split("\n")
                            for i, line in enumerate(lines, 1):
                                if table_name.lower() in line.lower() and operation.lower() in line.lower():
                                    results["operations"].append({
                                        "file": str(rel_path),
                                        "line": i,
                                        "code": line.strip()
                                    })
                            
                            if str(rel_path) not in results["related_files"]:
                                results["related_files"].append(str(rel_path))
                except Exception as e:
                    logger.warning(f"Failed to analyze file {file_path}: {e}")
                    continue
        
        # Also check migrations
        migrations_dir = self.repo_root / "migrations"
        if migrations_dir.exists():
            for file_path in migrations_dir.rglob("*.sql"):
                try:
                    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                        content = f.read()
                        if table_name.lower() in content.lower():
                            rel_path = file_path.relative_to(self.repo_root)
                            results["related_files"].append(str(rel_path))
                except Exception:
                    continue
        
        return results
    
    def semantic_search(self, query: str, concept: str = None) -> List[Dict[str, Any]]:
        """
        Semantic search that understands code relationships.
        
        Args:
            query: Search query
            concept: Related concept to find connections
            
        Returns:
            List of related code with explanations
        """
        results = []
        
        # First do a regular search
        base_results = self.search_codebase(query, max_results=10)
        results.extend(base_results)
        
        # If concept provided, find related code
        if concept:
            # Find functions/classes that use the concept
            concept_results = self.search_codebase(concept, max_results=5)
            
            # Find related patterns
            related_patterns = {
                "upload": ["file", "document", "process"],
                "line items": ["invoice", "items", "products"],
                "cards": ["display", "render", "component"],
                "database": ["query", "insert", "select"],
                "api": ["endpoint", "route", "request"]
            }
            
            for pattern, related in related_patterns.items():
                if pattern in concept.lower():
                    for rel_term in related:
                        rel_results = self.search_codebase(rel_term, max_results=3)
                        results.extend(rel_results)
        
        # Remove duplicates
        seen = set()
        unique_results = []
        for result in results:
            key = (result["file_path"], result["line"])
            if key not in seen:
                seen.add(key)
                unique_results.append(result)
        
        return unique_results[:10]
    
    def find_related_code(self, file_path: str, function_name: str = None) -> List[Dict[str, Any]]:
        """
        Find related functions/classes to a given file or function.
        
        Args:
            file_path: File to find related code for
            function_name: Specific function/class name
            
        Returns:
            List of related code locations
        """
        results = []
        
        # Read the file to find imports and function calls
        file_data = self.read_file(file_path)
        if not file_data.get("success"):
            return results
        
        content = file_data["content"]
        lines = content.split("\n")
        
        # Find imports
        imports = []
        for line in lines:
            if line.strip().startswith("import ") or line.strip().startswith("from "):
                imports.append(line.strip())
        
        # Find function/class definitions
        definitions = []
        for i, line in enumerate(lines, 1):
            if re.search(r"^(def|class|function|const|export)\s+\w+", line):
                match = re.search(r"(def|class|function|const|export\s+(?:default\s+)?function|const)\s+(\w+)", line)
                if match:
                    definitions.append({
                        "name": match.group(2),
                        "line": i,
                        "type": match.group(1)
                    })
        
        # Search for usages of imported modules
        for imp in imports[:5]:  # Limit to 5 imports
            # Extract module name
            match = re.search(r"from\s+([\w.]+)|import\s+([\w.]+)", imp)
            if match:
                module = match.group(1) or match.group(2)
                module_parts = module.split(".")[-1]  # Get last part
                usage_results = self.search_codebase(module_parts, max_results=3)
                results.extend(usage_results)
        
        # Search for calls to defined functions
        if function_name:
            call_results = self.search_codebase(function_name, max_results=5)
            results.extend(call_results)
        
        # Remove duplicates
        seen = set()
        unique_results = []
        for result in results:
            key = (result["file_path"], result["line"])
            if key not in seen:
                seen.add(key)
                unique_results.append(result)
        
        return unique_results[:10]
    
    def generate_flow_diagram(self, flow_path: List[Dict[str, Any]]) -> str:
        """
        Generate text-based flow diagram to visualize data paths.
        
        Args:
            flow_path: List of flow steps from trace_data_flow
            
        Returns:
            Text-based diagram showing the flow
        """
        if not flow_path:
            return "No flow path found."
        
        diagram_lines = []
        diagram_lines.append("Data Flow Diagram:")
        diagram_lines.append("=" * 50)
        
        for i, step in enumerate(flow_path):
            step_type = step.get("step", "unknown")
            concept = step.get("concept", "unknown")
            description = step.get("description", "")
            files = step.get("files", [])
            
            # Visual representation
            if step_type == "start":
                diagram_lines.append(f"\n┌─ START: {concept.upper()}")
            elif step_type == "end":
                diagram_lines.append(f"└─ END: {concept.upper()}")
            else:
                diagram_lines.append(f"├─ {concept}")
            
            diagram_lines.append(f"│  {description}")
            
            if files:
                diagram_lines.append(f"│  Files: {', '.join(files[:2])}")
            
            if i < len(flow_path) - 1:
                diagram_lines.append("│")
                diagram_lines.append("↓")
        
        diagram_lines.append("=" * 50)
        
        return "\n".join(diagram_lines)

