"""
Architecture Analyzer Service

Auto-detects codebase architecture patterns including framework,
async patterns, data flow, and import relationships.
"""

import logging
import re
from typing import Dict, Any, List, Optional, Set
from pathlib import Path
from backend.services.code_reader import CodeReader
from backend.services.ast_parser import ASTParser
from backend.services.code_explorer import CodeExplorer

logger = logging.getLogger("owlin.services.architecture_analyzer")


class ArchitectureAnalyzer:
    """Service for analyzing and detecting codebase architecture."""
    
    def __init__(self, repo_root: Optional[Path] = None):
        """
        Initialize the architecture analyzer.
        
        Args:
            repo_root: Path to repository root. If None, auto-detect.
        """
        self.code_reader = CodeReader(repo_root=repo_root)
        self.ast_parser = ASTParser()
        self.code_explorer = CodeExplorer()
        self.repo_root = self.code_reader.repo_root
        logger.info(f"ArchitectureAnalyzer initialized with repo_root: {self.repo_root}")
    
    def detect_framework(self, file_path: str) -> Dict[str, Any]:
        """
        Detect the framework used in a file.
        
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
            elif "express" in module or "koa" in module:
                framework_score["nodejs"] = framework_score.get("nodejs", 0) + 2
                indicators.append(f"Import: {imp.get('module')}")
        
        # Check decorators in functions
        functions = parsed.get("functions", [])
        for func in functions:
            decorators = func.get("decorators", [])
            for decorator in decorators:
                decorator_str = str(decorator).lower()
                if "@app.post" in decorator_str or "@app.get" in decorator_str or "@router" in decorator_str or "@router.post" in decorator_str:
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
        
        # Get framework-specific syntax rules
        syntax_rules = self._get_framework_syntax_rules(framework_name)
        
        return {
            "framework": framework_name,
            "confidence": confidence,
            "indicators": indicators,
            "score": framework_score,
            "file_path": file_path,
            "syntax_rules": syntax_rules
        }
    
    def _get_framework_syntax_rules(self, framework: str) -> Dict[str, Any]:
        """
        Get framework-specific syntax rules and patterns.
        
        Args:
            framework: Framework name (fastapi, flask, frontend, nodejs, etc.)
            
        Returns:
            Dict with allowed decorators, async patterns, and forbidden patterns
        """
        rules = {
            "fastapi": {
                "allowed_decorators": ["@app.post", "@app.get", "@app.put", "@app.delete", "@app.patch", 
                                       "@router.post", "@router.get", "@router.put", "@router.delete", "@router.patch"],
                "forbidden_decorators": ["@app.route"],
                "async_required": True,  # FastAPI endpoints should typically be async
                "request_access": "Request body via Pydantic models or UploadFile, not request.form",
                "forbidden_patterns": ["request.form", "request.args", "@app.route"],
                "required_imports": ["from fastapi import"],
                "example": "@app.post('/api/endpoint')\nasync def endpoint(data: Model):\n    return {'success': True}"
            },
            "flask": {
                "allowed_decorators": ["@app.route"],
                "forbidden_decorators": ["@app.post", "@app.get", "@router.post", "@router.get"],
                "async_required": False,  # Flask can use async but it's not required
                "request_access": "request.form, request.args, request.json",
                "forbidden_patterns": ["@app.post", "@router.post", "async def"],  # Not required, but common
                "required_imports": ["from flask import"],
                "example": "@app.route('/api/endpoint', methods=['POST'])\ndef endpoint():\n    data = request.json\n    return {'success': True}"
            },
            "frontend": {
                "allowed_decorators": [],  # React/Vue don't use decorators like this
                "forbidden_decorators": ["@app.route", "@app.post", "@router.post"],
                "async_required": False,
                "request_access": "fetch() API or axios",
                "forbidden_patterns": ["@app.route", "@app.post", "request.form"],
                "required_imports": ["import React", "import { useState }", "from vue"],
                "example": "const response = await fetch('/api/endpoint', { method: 'POST', body: JSON.stringify(data) })"
            },
            "nodejs": {
                "allowed_decorators": [],  # Express uses app.post(), not decorators
                "forbidden_decorators": ["@app.route", "@app.post"],
                "async_required": False,
                "request_access": "req.body, req.params, req.query",
                "forbidden_patterns": ["@app.route", "@app.post", "request.form"],
                "required_imports": ["const express = require('express')", "import express from 'express'"],
                "example": "app.post('/api/endpoint', async (req, res) => {\n    const data = req.body;\n    res.json({ success: true });\n})"
            }
        }
        
        return rules.get(framework, {
            "allowed_decorators": [],
            "forbidden_decorators": [],
            "async_required": False,
            "request_access": "Unknown",
            "forbidden_patterns": [],
            "required_imports": [],
            "example": "Unknown framework"
        })
    
    def detect_async_patterns(self, file_path: str) -> Dict[str, Any]:
        """
        Detect async/await patterns in a file.
        
        Args:
            file_path: Path to the file to analyze
            
        Returns:
            Dict with 'has_async', 'async_functions', 'await_calls', and 'patterns'
        """
        parsed = self.ast_parser.parse_file(file_path)
        if not parsed.get("success"):
            return {
                "has_async": False,
                "error": f"Could not parse file: {file_path}"
            }
        
        functions = parsed.get("functions", [])
        async_functions = [f for f in functions if f.get("is_async", False)]
        
        # Read file to check for await calls
        file_data = self.code_reader.read_file(file_path)
        content = file_data.get("content", "") if file_data.get("success") else ""
        
        # Count await calls
        await_count = len(re.findall(r'\bawait\s+', content))
        
        # Detect async patterns
        patterns = []
        if async_functions:
            patterns.append(f"Has {len(async_functions)} async function(s)")
        if await_count > 0:
            patterns.append(f"Has {await_count} await call(s)")
        if "asyncio" in content:
            patterns.append("Uses asyncio")
        if "async def" in content and "@app.post" in content:
            patterns.append("FastAPI async endpoint pattern")
        
        return {
            "has_async": len(async_functions) > 0 or await_count > 0,
            "async_functions": [f["name"] for f in async_functions],
            "async_function_count": len(async_functions),
            "await_calls": await_count,
            "patterns": patterns,
            "file_path": file_path
        }
    
    def detect_data_flow(
        self,
        start_file: str,
        end_file: str
    ) -> List[Dict[str, Any]]:
        """
        Detect data flow between two files.
        
        Args:
            start_file: Starting file path
            end_file: Ending file path
            
        Returns:
            List of flow steps with file paths and function calls
        """
        flow = []
        
        # Parse both files
        start_parsed = self.ast_parser.parse_file(start_file)
        end_parsed = self.ast_parser.parse_file(end_file)
        
        if not start_parsed.get("success") or not end_parsed.get("success"):
            return flow
        
        # Get imports from start file
        start_imports = start_parsed.get("imports", [])
        
        # Check if start file imports from end file
        end_file_name = Path(end_file).stem
        for imp in start_imports:
            module = imp.get("module", "")
            if end_file_name in module or module.endswith(end_file_name):
                flow.append({
                    "type": "import",
                    "from": start_file,
                    "to": end_file,
                    "module": module
                })
        
        # Get functions from both files
        start_functions = [f["name"] for f in start_parsed.get("functions", [])]
        end_functions = [f["name"] for f in end_parsed.get("functions", [])]
        
        # Read files to check for function calls
        start_data = self.code_reader.read_file(start_file)
        end_data = self.code_reader.read_file(end_file)
        
        if start_data.get("success") and end_data.get("success"):
            start_content = start_data["content"]
            end_content = end_data["content"]
            
            # Check if start file calls functions from end file
            for func in end_functions:
                if re.search(rf'\b{func}\s*\(', start_content):
                    flow.append({
                        "type": "function_call",
                        "from": start_file,
                        "to": end_file,
                        "function": func
                    })
        
        return flow
    
    def validate_code_suggestion(
        self,
        code_suggestion: str,
        detected_framework: str,
        syntax_rules: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Validate a code suggestion matches the detected framework syntax.
        
        Args:
            code_suggestion: Code snippet to validate
            detected_framework: Detected framework name
            syntax_rules: Optional syntax rules (if not provided, will fetch)
            
        Returns:
            Dict with 'valid', 'issues', 'mismatches', and 'suggestions'
        """
        if syntax_rules is None:
            syntax_rules = self._get_framework_syntax_rules(detected_framework)
        
        if detected_framework == "unknown":
            return {
                "valid": True,  # Can't validate unknown framework
                "issues": [],
                "mismatches": [],
                "suggestions": []
            }
        
        issues = []
        mismatches = []
        suggestions = []
        code_lower = code_suggestion.lower()
        
        # Check for forbidden decorators
        for forbidden_decorator in syntax_rules.get("forbidden_decorators", []):
            if forbidden_decorator.lower() in code_lower:
                issues.append(f"Uses forbidden decorator: {forbidden_decorator}")
                mismatches.append({
                    "type": "forbidden_decorator",
                    "found": forbidden_decorator,
                    "framework": detected_framework
                })
                # Suggest allowed alternative
                allowed = syntax_rules.get("allowed_decorators", [])
                if allowed:
                    suggestions.append(f"Use {allowed[0]} instead of {forbidden_decorator}")
        
        # Check for forbidden patterns
        for forbidden_pattern in syntax_rules.get("forbidden_patterns", []):
            if forbidden_pattern.lower() in code_lower:
                issues.append(f"Uses forbidden pattern: {forbidden_pattern}")
                mismatches.append({
                    "type": "forbidden_pattern",
                    "found": forbidden_pattern,
                    "framework": detected_framework
                })
                # Suggest alternative
                request_access = syntax_rules.get("request_access", "")
                if request_access:
                    suggestions.append(f"Use {request_access} instead of {forbidden_pattern}")
        
        # Check async requirement
        if syntax_rules.get("async_required", False):
            # FastAPI should use async def
            if "def " in code_suggestion and "async def" not in code_suggestion:
                # Check if it's an endpoint function (has decorator)
                has_decorator = any(
                    decorator in code_suggestion 
                    for decorator in syntax_rules.get("allowed_decorators", [])
                )
                if has_decorator:
                    issues.append("Endpoint should use 'async def' for FastAPI")
                    mismatches.append({
                        "type": "missing_async",
                        "framework": detected_framework
                    })
                    suggestions.append("Add 'async' keyword: 'async def endpoint(...)'")
        
        # Check decorator patterns match framework
        has_allowed_decorator = any(
            decorator in code_suggestion 
            for decorator in syntax_rules.get("allowed_decorators", [])
        )
        has_forbidden_decorator = any(
            decorator in code_suggestion 
            for decorator in syntax_rules.get("forbidden_decorators", [])
        )
        
        if has_forbidden_decorator and not has_allowed_decorator:
            issues.append("Decorator pattern doesn't match framework")
            mismatches.append({
                "type": "decorator_mismatch",
                "framework": detected_framework
            })
            allowed = syntax_rules.get("allowed_decorators", [])
            if allowed:
                suggestions.append(f"Use {allowed[0]} decorator pattern for {detected_framework}")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "mismatches": mismatches,
            "suggestions": suggestions,
            "framework": detected_framework
        }
    
    def detect_import_relationships(self, file_path: str) -> Dict[str, Any]:
        """
        Detect import relationships for a file.
        
        Args:
            file_path: Path to the file to analyze
            
        Returns:
            Dict with 'imports', 'exports', and 'dependencies'
        """
        parsed = self.ast_parser.parse_file(file_path)
        if not parsed.get("success"):
            return {
                "imports": [],
                "exports": [],
                "dependencies": [],
                "error": f"Could not parse file: {file_path}"
            }
        
        imports = parsed.get("imports", [])
        functions = parsed.get("functions", [])
        classes = parsed.get("classes", [])
        
        # Extract imported modules
        imported_modules = [imp.get("module", "") for imp in imports if imp.get("module")]
        
        # Extract exported items (functions and classes)
        exported_items = [f["name"] for f in functions] + [c["name"] for c in classes]
        
        # Get dependencies (modules imported)
        dependencies = list(set(imported_modules))
        
        return {
            "imports": [{"module": imp.get("module"), "names": imp.get("names", [])} for imp in imports],
            "exports": exported_items,
            "dependencies": dependencies,
            "file_path": file_path
        }
    
    def detect_function_calls(self, func_name: str) -> List[Dict[str, Any]]:
        """
        Detect where a function is called in the codebase.
        
        Args:
            func_name: Name of the function to find calls for
            
        Returns:
            List of call locations with file paths and line numbers
        """
        # Use grep to find function calls
        pattern = f"{func_name}\\s*\\("
        matches = self.code_explorer.grep_pattern(pattern)
        
        call_locations = []
        for file_path, lines in matches.items():
            for line_num in lines:
                # Read context around the call
                file_data = self.code_reader.read_file_with_context(file_path, line_num, context_lines=3)
                if file_data.get("success"):
                    call_locations.append({
                        "file": file_path,
                        "line": line_num,
                        "context": file_data["content"]
                    })
        
        return call_locations
    
    def analyze_architecture(self, file_paths: List[str]) -> Dict[str, Any]:
        """
        Comprehensive architecture analysis for multiple files.
        
        Args:
            file_paths: List of file paths to analyze
            
        Returns:
            Dict with framework detection, async patterns, and relationships
        """
        results = {
            "frameworks": {},
            "async_patterns": {},
            "relationships": {},
            "function_calls": {}
        }
        
        for file_path in file_paths:
            # Detect framework
            framework_result = self.detect_framework(file_path)
            if framework_result.get("confidence", 0) > 0.7:
                framework_name = framework_result["framework"]
                if framework_name not in results["frameworks"]:
                    results["frameworks"][framework_name] = []
                results["frameworks"][framework_name].append(file_path)
            
            # Detect async patterns
            async_result = self.detect_async_patterns(file_path)
            if async_result.get("has_async"):
                results["async_patterns"][file_path] = async_result
            
            # Detect relationships
            relationships = self.detect_import_relationships(file_path)
            results["relationships"][file_path] = relationships
        
        return results

