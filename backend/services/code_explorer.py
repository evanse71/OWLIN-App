"""
Code Explorer Service

Active exploration tools for agent-based code analysis.
Provides semantic search, pattern matching, data flow tracing, and related code discovery.
"""

import logging
import re
import time
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from backend.services.code_reader import CodeReader
from backend.services.explorer_config import get_config
from backend.services.ast_parser import ASTParser

logger = logging.getLogger("owlin.services.code_explorer")


class CodeExplorer:
    """Tools for LLM to explore codebase and find relevant code."""
    
    def __init__(self, max_findings: Optional[int] = None, cache_ttl: Optional[int] = None):
        """
        Initialize the code explorer with CodeReader.
        
        Args:
            max_findings: Maximum number of findings to return (None = use config)
            cache_ttl: Cache TTL in seconds (None = use config)
        """
        self.config = get_config()
        self.code_reader = CodeReader(cache_ttl=cache_ttl or self.config.cache_ttl)
        self.root_path = self.code_reader.repo_root
        self.max_findings = max_findings or self.config.max_findings
        self.cache_ttl = cache_ttl or self.config.cache_ttl
        self._search_cache: Dict[str, Tuple[float, List[Dict]]] = {}  # {key: (timestamp, results)}
        self.ast_parser = ASTParser()  # AST parser for better code understanding
        
    def search_concept(self, concept: str, max_results: int = 10, use_cache: bool = True, cancellation_flag=None) -> List[Dict]:
        """
        Semantic search for concepts in codebase with AST-enhanced understanding.
        
        Args:
            concept: Concept to search for (e.g., "line items", "upload display")
            max_results: Maximum number of results to return
            use_cache: Whether to use cached results if available
            cancellation_flag: Optional threading.Event to signal cancellation
            
        Returns:
            List of dicts with file, line, match, and context
        """
        # Check cache first
        if use_cache:
            cache_key = f"{concept.lower()}:{max_results}"
            if cache_key in self._search_cache:
                cached_time, cached_results = self._search_cache[cache_key]
                if time.time() - cached_time < self.cache_ttl:
                    logger.debug(f"Cache hit for search: {concept}")
                    return cached_results[:max_results]
                else:
                    # Cache expired, remove it
                    del self._search_cache[cache_key]
        
        results = []
        concept_lower = concept.lower()
        concept_words = concept_lower.split()
        
        # First, try AST-based search for function/class names (higher precision)
        # Early termination: stop when max_results reached
        if cancellation_flag is None or not cancellation_flag.is_set():
            ast_results = self._search_with_ast(concept, concept_words, max_results // 2, cancellation_flag)
            results.extend(ast_results)
            
            # Early termination: if we already have enough results, skip text search
            if len(results) >= max_results:
                results.sort(key=lambda x: x.get("score", 0), reverse=True)
                final_results = results[:max_results]
                # Cache results
                if use_cache:
                    cache_key = f"{concept.lower()}:{max_results}"
                    self._search_cache[cache_key] = (time.time(), final_results)
                    if len(self._search_cache) > self.config.max_cache_size:
                        self._clean_cache()
                return final_results
        
        # Then do text-based search for remaining results (broader coverage)
        # Early termination: only search for remaining slots
        if cancellation_flag is None or not cancellation_flag.is_set():
            remaining_slots = max_results - len(results)
            if remaining_slots > 0:
                text_results = self._search_text(concept, concept_words, remaining_slots, cancellation_flag)
                results.extend(text_results)
        
        # Sort by score and return top results
        results.sort(key=lambda x: x.get("score", 0), reverse=True)
        limit = min(max_results, self.max_findings)
        final_results = results[:limit]
        
        # Cache results
        if use_cache:
            cache_key = f"{concept.lower()}:{max_results}"
            self._search_cache[cache_key] = (time.time(), final_results)
            # Clean old cache entries if cache is getting large
            if len(self._search_cache) > self.config.max_cache_size:
                self._clean_cache()
        
        return final_results
    
    def _search_with_ast(self, concept: str, concept_words: List[str], max_results: int, cancellation_flag=None) -> List[Dict]:
        """Search using AST parsing for better structure understanding."""
        results = []
        concept_lower = concept.lower()
        
        # Search in common code file extensions
        # Limit search breadth: start with backend/** and frontend_clean/src/** only
        for ext in ['.py', '.ts', '.tsx', '.js', '.jsx']:
            # Early termination: check cancellation and result limit
            if cancellation_flag and cancellation_flag.is_set():
                break
            if len(results) >= max_results:
                break
            
            # Prioritize specific directories first (narrower search)
            search_dirs = []
            backend_src = self.code_reader.backend_dir
            frontend_src = self.code_reader.frontend_dir / "src" if self.code_reader.frontend_dir.exists() else None
            
            if backend_src.exists():
                search_dirs.append(backend_src)
            if frontend_src and frontend_src.exists():
                search_dirs.append(frontend_src)
            
            # If no results found in prioritized dirs, expand to full directories
            initial_results_count = len(results)
            
            for search_dir in search_dirs:
                # Early termination checks
                if cancellation_flag and cancellation_flag.is_set():
                    break
                if len(results) >= max_results:
                    break
                    
                for file_path in search_dir.rglob(f"*{ext}"):
                    # Early termination checks in inner loop
                    if cancellation_flag and cancellation_flag.is_set():
                        break
                    if len(results) >= max_results:
                        break
                    
                    if self.code_reader._should_skip_file(file_path):
                        continue
                    
                    # Skip AST parsing on large files (>300KB) for performance
                    try:
                        file_size = file_path.stat().st_size
                        if file_size > 300 * 1024:  # 300KB
                            continue  # Skip large files, fall back to text search
                    except:
                        pass  # If stat fails, try parsing anyway
                    
                    try:
                        # Parse file with AST
                        structure = self.ast_parser.parse_file(str(file_path))
                        if not structure.get("success"):
                            continue
                        
                        rel_path = file_path.relative_to(self.root_path)
                        
                        # Read file once for all operations
                        try:
                            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                                lines = f.readlines()
                        except Exception as e:
                            logger.debug(f"Error reading {file_path}: {e}")
                            continue
                        
                        # Search in function names
                        for func in structure.get("functions", []):
                            # Early termination checks
                            if cancellation_flag and cancellation_flag.is_set():
                                break
                            if len(results) >= max_results:
                                break
                            
                            func_name_lower = func["name"].lower()
                            if concept_lower in func_name_lower or any(word in func_name_lower for word in concept_words):
                                match_score = 0.95  # High score for function name match
                                if concept_lower == func_name_lower:
                                    match_score = 1.0
                                
                                func_line = func["line"]
                                end_line = func.get("end_line", func_line + 10)
                                func_code = '\n'.join(lines[func_line - 1:min(end_line, len(lines))])
                                
                                results.append({
                                    "file": str(rel_path),
                                    "line": func_line,
                                    "match": f"def {func['name']}({', '.join(func.get('args', []))})",
                                    "context": func_code[:500],
                                    "score": match_score,
                                    "type": "function_definition"
                                })
                        
                        # Search in class names
                        for cls in structure.get("classes", []):
                            # Early termination checks
                            if cancellation_flag and cancellation_flag.is_set():
                                break
                            if len(results) >= max_results:
                                break
                            
                            cls_name_lower = cls["name"].lower()
                            if concept_lower in cls_name_lower or any(word in cls_name_lower for word in concept_words):
                                match_score = 0.95
                                if concept_lower == cls_name_lower:
                                    match_score = 1.0
                                
                                cls_line = cls["line"]
                                end_line = cls.get("end_line", cls_line + 20)
                                cls_code = '\n'.join(lines[cls_line - 1:min(end_line, len(lines))])
                                
                                results.append({
                                    "file": str(rel_path),
                                    "line": cls_line,
                                    "match": f"class {cls['name']}",
                                    "context": cls_code[:500],
                                    "score": match_score,
                                    "type": "class_definition"
                                })
                        
                        # Search in method names within classes
                        for cls in structure.get("classes", []):
                            # Early termination checks
                            if cancellation_flag and cancellation_flag.is_set():
                                break
                            if len(results) >= max_results:
                                break
                            for method in cls.get("methods", []):
                                # Early termination checks
                                if cancellation_flag and cancellation_flag.is_set():
                                    break
                                if len(results) >= max_results:
                                    break
                                method_name_lower = method["name"].lower()
                                if any(word in method_name_lower for word in concept_words):
                                    results.append({
                                        "file": str(rel_path),
                                        "line": method["line"],
                                        "match": f"{cls['name']}.{method['name']}()",
                                        "context": self._get_context(lines, method["line"] - 1, 5),
                                        "score": 0.85,
                                        "type": "method_definition"
                                    })
                        
                    except Exception as e:
                        logger.debug(f"Error parsing {file_path} with AST: {e}")
                        continue
        
        return results[:max_results]
    
    def _search_text(self, concept: str, concept_words: List[str], max_results: int, cancellation_flag=None) -> List[Dict]:
        """Text-based search fallback."""
        results = []
        concept_lower = concept.lower()
        
        # Search in common code file extensions
        # Limit search breadth: start with backend/** and frontend_clean/src/** only
        for ext in ['.py', '.ts', '.tsx', '.js', '.jsx']:
            # Early termination checks
            if cancellation_flag and cancellation_flag.is_set():
                break
            if len(results) >= max_results:
                break
            
            # Prioritize specific directories first (narrower search)
            search_dirs = []
            backend_src = self.code_reader.backend_dir
            frontend_src = self.code_reader.frontend_dir / "src" if self.code_reader.frontend_dir.exists() else None
            
            if backend_src.exists():
                search_dirs.append(backend_src)
            if frontend_src and frontend_src.exists():
                search_dirs.append(frontend_src)
            
            # If no results found in prioritized dirs, expand to full directories
            if not search_dirs or len(results) == 0:
                if self.code_reader.backend_dir.exists() and backend_src not in search_dirs:
                    search_dirs.append(self.code_reader.backend_dir)
                if self.code_reader.frontend_dir.exists() and frontend_src not in search_dirs:
                    search_dirs.append(self.code_reader.frontend_dir)
            
            for search_dir in search_dirs:
                if len(results) >= max_results:
                    break
                    
                for file_path in search_dir.rglob(f"*{ext}"):
                    if len(results) >= max_results:
                        break
                        
                    if self.code_reader._should_skip_file(file_path):
                        continue
                    
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                            lines = f.readlines()
                            
                        for i, line in enumerate(lines, 1):
                            # Early termination check in line loop
                            if cancellation_flag and cancellation_flag.is_set():
                                break
                            if len(results) >= max_results:
                                break
                            
                            line_lower = line.lower()
                            
                            # Exact phrase match
                            if concept_lower in line_lower:
                                match_score = 1.0
                            # All words present
                            elif len(concept_words) > 1 and all(word in line_lower for word in concept_words):
                                match_score = 0.8
                            # Partial match
                            elif any(word in line_lower for word in concept_words):
                                match_score = 0.6
                            else:
                                continue
                            
                            rel_path = file_path.relative_to(self.root_path)
                            context = self._get_context(lines, i - 1, 3)
                            
                            results.append({
                                "file": str(rel_path),
                                "line": i,
                                "match": line.strip(),
                                "context": context,
                                "score": match_score,
                                "type": "text_match"
                            })
                            
                    except Exception as e:
                        logger.debug(f"Error reading {file_path}: {e}")
                        continue
        
        return results[:max_results]
    
    def _clean_cache(self):
        """Remove expired cache entries."""
        current_time = time.time()
        expired_keys = [
            key for key, (cached_time, _) in self._search_cache.items()
            if current_time - cached_time >= self.cache_ttl
        ]
        for key in expired_keys:
            del self._search_cache[key]
        logger.debug(f"Cleaned {len(expired_keys)} expired cache entries")
    
    def grep_pattern(self, pattern: str, file_pattern: str = None, max_results: int = 50, cancellation_flag=None) -> Dict[str, List[int]]:
        """
        Search for regex pattern in codebase with early termination.
        
        Args:
            pattern: Regex pattern to search for
            file_pattern: Optional file pattern filter (e.g., "*.py", "*.tsx")
            max_results: Maximum number of matches to return (default 50)
            cancellation_flag: Optional threading.Event to signal cancellation
            
        Returns:
            Dict mapping file paths to list of line numbers where pattern matches
        """
        matches = {}
        total_matches = 0
        
        # Determine file extensions to search
        if file_pattern:
            if "," in file_pattern:
                extensions = [ext.strip() for ext in file_pattern.split(",")]
            else:
                extensions = [file_pattern]
        else:
            extensions = ['.py', '.ts', '.tsx', '.js', '.jsx']
        
        search_dirs = []
        if self.code_reader.backend_dir.exists():
            search_dirs.append(self.code_reader.backend_dir)
        if self.code_reader.frontend_dir.exists():
            search_dirs.append(self.code_reader.frontend_dir)
        
        for search_dir in search_dirs:
            # Early termination check
            if cancellation_flag and cancellation_flag.is_set():
                break
            if total_matches >= max_results:
                break
                
            for ext in extensions:
                # Early termination check
                if cancellation_flag and cancellation_flag.is_set():
                    break
                if total_matches >= max_results:
                    break
                    
                # Normalize extension
                if not ext.startswith('.'):
                    ext = '.' + ext
                if '*' in ext:
                    ext = ext.replace('*', '')
                
                for file_path in search_dir.rglob(f'*{ext}'):
                    # Early termination check in file loop
                    if cancellation_flag and cancellation_flag.is_set():
                        break
                    if total_matches >= max_results:
                        break
                        
                    if self.code_reader._should_skip_file(file_path):
                        continue
                    
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                            lines = f.readlines()
                        
                        file_matches = []
                        for i, line in enumerate(lines, 1):
                            # Early termination check in line loop
                            if cancellation_flag and cancellation_flag.is_set():
                                break
                            if total_matches >= max_results:
                                break
                                
                            if re.search(pattern, line, re.IGNORECASE):
                                file_matches.append(i)
                                total_matches += 1
                                
                                # Early termination: stop when max_results reached
                                if total_matches >= max_results:
                                    break
                        
                        if file_matches:
                            rel_path = file_path.relative_to(self.root_path)
                            matches[str(rel_path)] = file_matches
                            
                    except Exception as e:
                        logger.debug(f"Error searching {file_path}: {e}")
                        continue
        
        return matches
    
    def find_function_calls(self, function_name: str) -> List[Dict]:
        """
        Find where a function is called using AST parsing for better accuracy.
        
        Args:
            function_name: Name of function to find calls for
            
        Returns:
            List of dicts with file, line, and context for each call site
        """
        results = []
        
        # First, try to find the function definition to understand its signature
        func_def = None
        for ext in ['.py', '.ts', '.tsx', '.js', '.jsx']:
            for search_dir in [self.root_path / "backend", self.root_path / "frontend_clean"]:
                if not search_dir.exists():
                    continue
                
                for file_path in search_dir.rglob(f"*{ext}"):
                    if self.code_reader._should_skip_file(file_path):
                        continue
                    
                    try:
                        structure = self.ast_parser.parse_file(str(file_path))
                        if structure.get("success"):
                            for func in structure.get("functions", []):
                                if func["name"] == function_name:
                                    func_def = func
                                    break
                    except Exception:
                        continue
                    
                    if func_def:
                        break
                if func_def:
                    break
            if func_def:
                break
        
        # Build pattern to match function calls (regex fallback)
        pattern = rf'\b{re.escape(function_name)}\s*\('
        matches = self.grep_pattern(pattern)
        
        for file_path, lines in matches.items():
            for line_num in lines:
                file_data = self.code_reader.read_file_with_context(
                    file_path, line_num, context_lines=5
                )
                if file_data.get("success"):
                    results.append({
                        "file": file_path,
                        "line": line_num,
                        "context": file_data["content"],
                        "type": "function_call"
                    })
        
        return results
    
    def trace_data_flow(self, start_point: str, end_point: str) -> List[Dict]:
        """
        Trace data flow between components.
        
        Args:
            start_point: Starting point (e.g., "upload.ts:normalizeUploadResponse" or "backend/main.py:upload")
            end_point: Ending point (e.g., "InvoiceDetailPanel.tsx:lineItems")
            
        Returns:
            List of flow steps with files, descriptions, and code
        """
        path = []
        
        # Parse start and end points
        start_file, start_ref = self._parse_reference(start_point)
        end_file, end_ref = self._parse_reference(end_point)
        
        # Use CodeReader's trace_data_flow if available
        if start_file and end_file:
            # Extract concepts from file paths
            start_concept = start_file.split('/')[-1].replace('.py', '').replace('.ts', '').replace('.tsx', '')
            end_concept = end_file.split('/')[-1].replace('.py', '').replace('.ts', '').replace('.tsx', '')
            
            flow_path = self.code_reader.trace_data_flow(start_concept, end_concept)
            
            # Enhance with actual file reading
            for step in flow_path:
                files = step.get("files", [])
                if files:
                    file_data = self.code_reader.read_file(files[0], max_lines=500)
                    if file_data.get("success"):
                        step["code"] = file_data["content"][:1000]  # First 1000 chars
                path.append(step)
        
        # If no flow found, try direct file reading
        if not path and start_file:
            start_data = self.code_reader.read_file(start_file, max_lines=500)
            if start_data.get("success"):
                path.append({
                    "file": start_file,
                    "description": f"Start: {start_ref or 'file start'}",
                    "code": start_data["content"][:1000]
                })
        
        if end_file and end_file != start_file:
            end_data = self.code_reader.read_file(end_file, max_lines=500)
            if end_data.get("success"):
                path.append({
                    "file": end_file,
                    "description": f"End: {end_ref or 'file end'}",
                    "code": end_data["content"][:1000]
                })
        
        return path
    
    def find_related_files(self, file_path: str) -> List[str]:
        """
        Find files that import/use this file, or files this file imports.
        
        Args:
            file_path: File to find related files for
            
        Returns:
            List of related file paths
        """
        related = []
        
        file_data = self.code_reader.read_file(file_path, max_lines=200)
        if not file_data.get("success"):
            return related
        
        content = file_data["content"]
        
        # Find imports in the file
        import_patterns = [
            r'from\s+["\']([^"\']+)["\']',
            r'import\s+.*from\s+["\']([^"\']+)["\']',
            r'require\(["\']([^"\']+)["\']\)',
            r'import\s+["\']([^"\']+)["\']',
        ]
        
        for pattern in import_patterns:
            matches = re.findall(pattern, content)
            for match in matches:
                resolved = self._resolve_import(match, file_path)
                if resolved and resolved not in related:
                    related.append(resolved)
        
        # Also use CodeReader's find_related_code if available
        related_code = self.code_reader.find_related_code(file_path)
        for item in related_code:
            file = item.get("file_path")
            if file and file not in related:
                related.append(file)
        
        return list(set(related))
    
    def read_function(self, function_name: str, file_path: str = None) -> Dict:
        """
        Read a specific function definition.
        
        Args:
            function_name: Name of function to read
            file_path: Optional file path to search in (if None, searches all files)
            
        Returns:
            Dict with file, lines, and code
        """
        if file_path:
            # Read specific file and find function
            file_data = self.code_reader.read_file(file_path)
            if not file_data.get("success"):
                return {"file": file_path, "lines": [], "code": "", "error": "File not found"}
            
            content = file_data["content"]
            lines = content.split('\n')
            
            # Find function definition
            for i, line in enumerate(lines, 1):
                # Match function definitions
                patterns = [
                    rf'^\s*def\s+{re.escape(function_name)}\s*\(',
                    rf'^\s*function\s+{re.escape(function_name)}\s*\(',
                    rf'^\s*const\s+{re.escape(function_name)}\s*=\s*\(',
                    rf'^\s*const\s+{re.escape(function_name)}\s*=\s*function',
                    rf'^\s*export\s+(?:default\s+)?function\s+{re.escape(function_name)}\s*\(',
                ]
                
                for pattern in patterns:
                    if re.search(pattern, line):
                        # Find function end (next def/class at same or less indentation, or end of file)
                        start_line = i
                        end_line = self._find_function_end(lines, i - 1)
                        
                        function_code = '\n'.join(lines[start_line - 1:end_line])
                        
                        return {
                            "file": file_path,
                            "lines": [start_line, end_line],
                            "code": function_code
                        }
        else:
            # Search for function across codebase
            pattern = rf'^\s*(?:def|function|const)\s+{re.escape(function_name)}\s*[=(]'
            matches = self.grep_pattern(pattern)
            
            if matches:
                # Return first match
                file_path = list(matches.keys())[0]
                return self.read_function(function_name, file_path)
        
        return {"file": file_path or "unknown", "lines": [], "code": "", "error": "Function not found"}
    
    def suggest_exploration_path(self, problem_description: str) -> List[str]:
        """
        Given a problem, suggest files/functions to explore.
        Uses heuristics based on problem keywords and import analysis.
        
        Args:
            problem_description: Description of the problem
            
        Returns:
            List of suggested file paths to explore
        """
        suggestions = []
        desc_lower = problem_description.lower()
        
        # Enhanced keyword to file mapping with patterns
        keyword_map = {
            "upload": [
                "frontend_clean/src/lib/upload.ts",
                "backend/main.py",
                "backend/routes/upload.py"
            ],
            "display": [
                "frontend_clean/src/components/InvoiceDetailPanel.tsx",
                "frontend_clean/src/pages/Invoices.tsx"
            ],
            "items": [
                "frontend_clean/src/lib/upload.ts",
                "backend/main.py",
                "backend/services/ocr_service.py"
            ],
            "invoice": [
                "frontend_clean/src/pages/Invoices.tsx",
                "backend/main.py",
                "backend/routes/invoices_submit.py"
            ],
            "status": [
                "backend/main.py",
                "frontend_clean/src/lib/upload.ts",
                "backend/routes/upload.py"
            ],
            "line": [
                "frontend_clean/src/lib/upload.ts",
                "backend/services/ocr_service.py",
                "backend/app/db.py"
            ],
            "card": [
                "frontend_clean/src/components/InvoiceCard.tsx",
                "frontend_clean/src/pages/Invoices.tsx"
            ],
            "dashboard": [
                "frontend_clean/src/pages/Dashboard.tsx",
                "backend/routes/metrics.py"
            ],
            "api": [
                "backend/main.py",
                "frontend_clean/src/lib/api.ts"
            ],
            "error": [
                "backend/main.py",
                "backend/services/chat_service.py"
            ]
        }
        
        # Find matching keywords
        for keyword, files in keyword_map.items():
            if keyword in desc_lower:
                suggestions.extend(files)
        
        # Enhanced: Find files that import commonly used modules
        if "api" in desc_lower or "fetch" in desc_lower or "request" in desc_lower:
            api_files = self._find_files_importing(["api", "fetch", "axios", "request"])
            suggestions.extend(api_files)
        
        if "database" in desc_lower or "db" in desc_lower or "query" in desc_lower:
            db_files = self._find_files_importing(["db", "database", "sqlite", "sql"])
            suggestions.extend(db_files)
        
        if "upload" in desc_lower or "file" in desc_lower:
            upload_files = self._find_files_importing(["upload", "file", "multipart"])
            suggestions.extend(upload_files)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_suggestions = []
        for file in suggestions:
            if file not in seen:
                seen.add(file)
                unique_suggestions.append(file)
        
        return unique_suggestions[:10]  # Limit to top 10 suggestions
    
    def _find_files_importing(self, module_names: List[str]) -> List[str]:
        """
        Find files that import any of the given module names.
        
        Args:
            module_names: List of module names to search for
            
        Returns:
            List of file paths that import these modules
        """
        found_files = []
        module_names_lower = [m.lower() for m in module_names]
        
        search_dirs = []
        if self.code_reader.backend_dir.exists():
            search_dirs.append(self.code_reader.backend_dir)
        if self.code_reader.frontend_dir.exists():
            search_dirs.append(self.code_reader.frontend_dir)
        
        for search_dir in search_dirs:
            for ext in ['.py', '.ts', '.tsx', '.js', '.jsx']:
                for file_path in search_dir.rglob(f'*{ext}'):
                    if self.code_reader._should_skip_file(file_path):
                        continue
                    
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                            content = f.read().lower()
                            
                        # Check if any module name appears in imports
                        for module in module_names_lower:
                            if f'import {module}' in content or f'from {module}' in content or f'require("{module}")' in content:
                                rel_path = file_path.relative_to(self.root_path)
                                found_files.append(str(rel_path))
                                break  # Found one match, move to next file
                    except Exception:
                        continue
        
        return found_files
    
    def _get_context(self, lines: List[str], line_idx: int, context: int = 3) -> str:
        """Get context around a line."""
        start = max(0, line_idx - context)
        end = min(len(lines), line_idx + context + 1)
        context_lines = lines[start:end]
        
        # Add line numbers
        numbered = []
        for i, line in enumerate(context_lines, start=start + 1):
            numbered.append(f"{i:4d} | {line.rstrip()}")
        
        return '\n'.join(numbered)
    
    def _parse_reference(self, ref: str) -> tuple:
        """Parse 'file.py:function' into (file, reference)."""
        if ':' in ref:
            parts = ref.split(':', 1)
            return parts[0].strip(), parts[1].strip()
        return ref.strip(), None
    
    def _resolve_import(self, import_path: str, from_file: str) -> Optional[str]:
        """Resolve import path to actual file."""
        base_path = Path(from_file).parent if '/' in from_file or '\\' in from_file else self.root_path
        
        # Try different strategies
        strategies = [
            # Direct path
            self.root_path / import_path,
            # Relative to from_file
            base_path / import_path,
            # With common extensions
            *[self.root_path / f"{import_path}{ext}" for ext in ['.py', '.ts', '.tsx', '.js', '.jsx']],
            # With backend/frontend prefixes
            *[self.root_path / prefix / import_path for prefix in ['backend', 'frontend_clean', 'frontend']],
        ]
        
        for candidate in strategies:
            if candidate.exists() and candidate.is_file():
                rel_path = candidate.relative_to(self.root_path)
                return str(rel_path)
        
        return None
    
    def _find_function_end(self, lines: List[str], start_idx: int) -> int:
        """Find the end of a function definition."""
        if start_idx >= len(lines):
            return len(lines)
        
        # Get indentation of function definition
        start_line = lines[start_idx]
        base_indent = len(start_line) - len(start_line.lstrip())
        
        # Find next line with same or less indentation that's not blank/comment
        for i in range(start_idx + 1, len(lines)):
            line = lines[i]
            stripped = line.lstrip()
            
            # Skip blank lines and comments
            if not stripped or stripped.startswith('#'):
                continue
            
            # Check if this is a new definition at same or less indentation
            indent = len(line) - len(stripped)
            if indent <= base_indent:
                # Check if it's a new def/class/function
                if re.match(r'^\s*(def|class|function|const|export)', stripped):
                    return i
            
            # Also stop at end of file
            if i == len(lines) - 1:
                return i + 1
        
        return len(lines)

