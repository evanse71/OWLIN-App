"""
AST Parser Service

Provides Abstract Syntax Tree parsing for better code understanding.
Uses Python's built-in ast module for Python files and regex-based parsing
for TypeScript/JavaScript files.
"""

import ast
import re
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger("owlin.services.ast_parser")


@dataclass
class FunctionDef:
    """Represents a function definition."""
    name: str
    line: int
    end_line: Optional[int] = None
    args: List[str] = None
    docstring: Optional[str] = None
    decorators: List[str] = None
    is_async: bool = False
    return_type: Optional[str] = None


@dataclass
class ClassDef:
    """Represents a class definition."""
    name: str
    line: int
    end_line: Optional[int] = None
    bases: List[str] = None
    methods: List[FunctionDef] = None
    docstring: Optional[str] = None
    decorators: List[str] = None


@dataclass
class Import:
    """Represents an import statement."""
    module: str
    names: List[str]
    line: int
    is_from: bool = False


class ASTParser:
    """Parser for extracting code structure from files."""
    
    def __init__(self):
        """Initialize the AST parser."""
        self._cache: Dict[str, Dict[str, Any]] = {}
    
    def parse_file(self, file_path: str) -> Dict[str, Any]:
        """
        Parse a file and extract its structure.
        
        Args:
            file_path: Path to the file to parse
            
        Returns:
            Dictionary with functions, classes, imports, and other structure info
        """
        file_path_obj = Path(file_path)
        
        # Check cache
        cache_key = str(file_path_obj.resolve())
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        try:
            with open(file_path_obj, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
                lines = content.split('\n')
        except Exception as e:
            logger.warning(f"Failed to read file {file_path}: {e}")
            return {"success": False, "error": str(e)}
        
        # Determine file type and parse accordingly
        ext = file_path_obj.suffix.lower()
        
        if ext == '.py':
            result = self._parse_python(content, lines)
        elif ext in ['.ts', '.tsx', '.js', '.jsx']:
            result = self._parse_typescript(content, lines, str(file_path_obj))
        else:
            # Fallback to basic parsing
            result = self._parse_basic(content, lines)
        
        result["file_path"] = str(file_path_obj)
        result["success"] = True
        
        # Cache result
        self._cache[cache_key] = result
        
        return result
    
    def _parse_python(self, content: str, lines: List[str]) -> Dict[str, Any]:
        """Parse Python file using ast module."""
        try:
            tree = ast.parse(content)
        except SyntaxError as e:
            logger.warning(f"Python syntax error: {e}")
            return self._parse_basic(content, lines)
        except Exception as e:
            logger.warning(f"Python parse error: {e}")
            return self._parse_basic(content, lines)
        
        functions = []
        classes = []
        imports = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                func = self._extract_function(node, lines)
                functions.append(func)
            elif isinstance(node, ast.AsyncFunctionDef):
                func = self._extract_function(node, lines, is_async=True)
                functions.append(func)
            elif isinstance(node, ast.ClassDef):
                cls = self._extract_class(node, lines)
                classes.append(cls)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(Import(
                        module=alias.name,
                        names=[alias.asname or alias.name],
                        line=node.lineno,
                        is_from=False
                    ))
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                names = [alias.asname or alias.name for alias in node.names]
                imports.append(Import(
                    module=module,
                    names=names,
                    line=node.lineno,
                    is_from=True
                ))
        
        return {
            "functions": [self._function_to_dict(f) for f in functions],
            "classes": [self._class_to_dict(c) for c in classes],
            "imports": [self._import_to_dict(i) for i in imports],
            "language": "python"
        }
    
    def _extract_function(self, node: ast.FunctionDef, lines: List[str], is_async: bool = False) -> FunctionDef:
        """Extract function definition from AST node."""
        args = []
        for arg in node.args.args:
            arg_name = arg.arg
            if arg.annotation:
                arg_name += f": {ast.unparse(arg.annotation) if hasattr(ast, 'unparse') else 'Any'}"
            args.append(arg_name)
        
        return_type = None
        if node.returns:
            return_type = ast.unparse(node.returns) if hasattr(ast, 'unparse') else None
        
        decorators = []
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Name):
                decorators.append(decorator.id)
            elif isinstance(decorator, ast.Attribute):
                if hasattr(ast, 'unparse'):
                    decorators.append(ast.unparse(decorator))
                else:
                    decorators.append(str(decorator))
        
        docstring = ast.get_docstring(node)
        
        # Estimate end line (find next definition or end of file)
        end_line = self._find_end_line(node.lineno, lines)
        
        return FunctionDef(
            name=node.name,
            line=node.lineno,
            end_line=end_line,
            args=args,
            docstring=docstring,
            decorators=decorators,
            is_async=is_async,
            return_type=return_type
        )
    
    def _extract_class(self, node: ast.ClassDef, lines: List[str]) -> ClassDef:
        """Extract class definition from AST node."""
        bases = []
        for base in node.bases:
            if isinstance(base, ast.Name):
                bases.append(base.id)
            elif isinstance(base, ast.Attribute):
                # Handle dotted names like "BaseClass"
                parts = []
                current = base
                while isinstance(current, ast.Attribute):
                    parts.insert(0, current.attr)
                    current = current.value
                if isinstance(current, ast.Name):
                    parts.insert(0, current.id)
                    bases.append('.'.join(parts))
                else:
                    bases.append(str(base))
            elif hasattr(ast, 'unparse'):
                bases.append(ast.unparse(base))
            else:
                bases.append(str(base))
        
        methods = []
        for item in node.body:
            if isinstance(item, ast.FunctionDef):
                methods.append(self._extract_function(item, lines))
            elif isinstance(item, ast.AsyncFunctionDef):
                methods.append(self._extract_function(item, lines, is_async=True))
        
        decorators = []
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Name):
                decorators.append(decorator.id)
            elif isinstance(decorator, ast.Attribute):
                # Handle dotted decorators
                parts = []
                current = decorator
                while isinstance(current, ast.Attribute):
                    parts.insert(0, current.attr)
                    current = current.value
                if isinstance(current, ast.Name):
                    parts.insert(0, current.id)
                    decorators.append('.'.join(parts))
                else:
                    decorators.append(str(decorator))
            elif hasattr(ast, 'unparse'):
                decorators.append(ast.unparse(decorator))
            else:
                decorators.append(str(decorator))
        
        docstring = ast.get_docstring(node)
        end_line = self._find_end_line(node.lineno, lines)
        
        return ClassDef(
            name=node.name,
            line=node.lineno,
            end_line=end_line,
            bases=bases,
            methods=[self._function_to_dict(m) for m in methods],
            docstring=docstring,
            decorators=decorators
        )
    
    def _parse_typescript(self, content: str, lines: List[str], file_path: Optional[str] = None) -> Dict[str, Any]:
        """Parse TypeScript/JavaScript file using regex patterns."""
        functions = []
        classes = []
        imports = []
        
        # Determine language from file extension if available
        language = "javascript"
        if file_path:
            ext = Path(file_path).suffix.lower()
            if ext in ['.ts', '.tsx']:
                language = "typescript"
        
        for i, line in enumerate(lines, 1):
            line_stripped = line.strip()
            
            # Parse imports
            if line_stripped.startswith('import ') or line_stripped.startswith('export import '):
                import_match = re.match(
                    r'(?:export\s+)?import\s+(?:\*\s+as\s+(\w+)|(\w+)|{([^}]+)})\s+from\s+["\']([^"\']+)["\']',
                    line_stripped
                )
                if import_match:
                    module = import_match.group(4)
                    if import_match.group(1):  # import * as X
                        names = [import_match.group(1)]
                    elif import_match.group(2):  # import X
                        names = [import_match.group(2)]
                    else:  # import { X, Y }
                        names = [n.strip() for n in import_match.group(3).split(',')]
                    imports.append(Import(
                        module=module,
                        names=names,
                        line=i,
                        is_from=True
                    ))
            
            # Parse function definitions
            func_patterns = [
                r'(?:export\s+)?(?:async\s+)?function\s+(\w+)',
                r'(?:export\s+)?const\s+(\w+)\s*[:=]\s*(?:async\s*)?\([^)]*\)\s*[:=]>\s*',
                r'(?:export\s+)?(?:async\s+)?(\w+)\s*[:=]\s*(?:async\s*)?\([^)]*\)\s*[:=]>\s*',
            ]
            
            for pattern in func_patterns:
                match = re.search(pattern, line_stripped)
                if match:
                    func_name = match.group(1)
                    is_async = 'async' in line_stripped
                    args_match = re.search(r'\(([^)]*)\)', line_stripped)
                    args = []
                    if args_match:
                        args = [a.strip() for a in args_match.group(1).split(',') if a.strip()]
                    
                    end_line = self._find_end_line_ts(i, lines)
                    
                    functions.append(FunctionDef(
                        name=func_name,
                        line=i,
                        end_line=end_line,
                        args=args,
                        is_async=is_async
                    ))
                    break
            
            # Parse class definitions
            class_match = re.search(r'(?:export\s+)?(?:default\s+)?class\s+(\w+)', line_stripped)
            if class_match:
                class_name = class_match.group(1)
                # Find extends/implements
                bases = []
                extends_match = re.search(r'extends\s+(\w+)', line_stripped)
                if extends_match:
                    bases.append(extends_match.group(1))
                
                end_line = self._find_end_line_ts(i, lines)
                
                classes.append(ClassDef(
                    name=class_name,
                    line=i,
                    end_line=end_line,
                    bases=bases
                ))
        
        return {
            "functions": [self._function_to_dict(f) for f in functions],
            "classes": [self._class_to_dict(c) for c in classes],
            "imports": [self._import_to_dict(i) for i in imports],
            "language": "typescript" if Path(content).suffix in ['.ts', '.tsx'] else "javascript"
        }
    
    def _parse_basic(self, content: str, lines: List[str]) -> Dict[str, Any]:
        """Basic regex-based parsing for unsupported file types."""
        functions = []
        classes = []
        imports = []
        
        for i, line in enumerate(lines, 1):
            line_stripped = line.strip()
            
            # Function patterns
            if re.search(r'^\s*(?:def|function|const\s+\w+\s*[:=]\s*(?:async\s*)?\(|export\s+function)', line_stripped):
                match = re.search(r'(?:def|function|const\s+(\w+)|export\s+function\s+(\w+))', line_stripped)
                if match:
                    func_name = match.group(1) or match.group(2)
                    functions.append({
                        "name": func_name,
                        "line": i,
                        "args": [],
                        "is_async": "async" in line_stripped
                    })
            
            # Class patterns
            if re.search(r'^\s*(?:class|export\s+class)', line_stripped):
                match = re.search(r'class\s+(\w+)', line_stripped)
                if match:
                    classes.append({
                        "name": match.group(1),
                        "line": i,
                        "bases": []
                    })
            
            # Import patterns
            if re.search(r'^\s*(?:import|from)', line_stripped):
                imports.append({
                    "module": line_stripped,
                    "line": i,
                    "is_from": "from" in line_stripped
                })
        
        return {
            "functions": functions,
            "classes": classes,
            "imports": imports,
            "language": "unknown"
        }
    
    def _find_end_line(self, start_line: int, lines: List[str]) -> int:
        """Find the end line of a Python definition."""
        if start_line > len(lines):
            return len(lines)
        
        start_idx = start_line - 1
        start_line_content = lines[start_idx]
        base_indent = len(start_line_content) - len(start_line_content.lstrip())
        
        for i in range(start_idx + 1, len(lines)):
            line = lines[i]
            if not line.strip() or line.strip().startswith('#'):
                continue
            
            indent = len(line) - len(line.lstrip())
            if indent <= base_indent:
                # Check if it's a new definition
                if re.match(r'^\s*(def|class|async def)', line):
                    return i + 1
        
        return len(lines)
    
    def _find_end_line_ts(self, start_line: int, lines: List[str]) -> int:
        """Find the end line of a TypeScript/JavaScript definition."""
        if start_line > len(lines):
            return len(lines)
        
        start_idx = start_line - 1
        brace_count = 0
        in_function = False
        
        for i in range(start_idx, len(lines)):
            line = lines[i]
            brace_count += line.count('{') - line.count('}')
            
            if '{' in line:
                in_function = True
            
            if in_function and brace_count == 0:
                return i + 1
        
        return len(lines)
    
    def _function_to_dict(self, func: FunctionDef) -> Dict[str, Any]:
        """Convert FunctionDef to dictionary."""
        return {
            "name": func.name,
            "line": func.line,
            "end_line": func.end_line,
            "args": func.args or [],
            "docstring": func.docstring,
            "decorators": func.decorators or [],
            "is_async": func.is_async,
            "return_type": func.return_type
        }
    
    def _class_to_dict(self, cls: ClassDef) -> Dict[str, Any]:
        """Convert ClassDef to dictionary."""
        return {
            "name": cls.name,
            "line": cls.line,
            "end_line": cls.end_line,
            "bases": cls.bases or [],
            "methods": cls.methods or [],
            "docstring": cls.docstring,
            "decorators": cls.decorators or []
        }
    
    def _import_to_dict(self, imp: Import) -> Dict[str, Any]:
        """Convert Import to dictionary."""
        return {
            "module": imp.module,
            "names": imp.names,
            "line": imp.line,
            "is_from": imp.is_from
        }
    
    def find_function_definition(self, file_path: str, function_name: str) -> Optional[Dict[str, Any]]:
        """
        Find a specific function definition in a file.
        
        Args:
            file_path: Path to the file
            function_name: Name of the function to find
            
        Returns:
            Function definition dictionary or None
        """
        parsed = self.parse_file(file_path)
        if not parsed.get("success"):
            return None
        
        for func in parsed.get("functions", []):
            if func["name"] == function_name:
                return func
        
        return None
    
    def find_class_definition(self, file_path: str, class_name: str) -> Optional[Dict[str, Any]]:
        """
        Find a specific class definition in a file.
        
        Args:
            file_path: Path to the file
            class_name: Name of the class to find
            
        Returns:
            Class definition dictionary or None
        """
        parsed = self.parse_file(file_path)
        if not parsed.get("success"):
            return None
        
        for cls in parsed.get("classes", []):
            if cls["name"] == class_name:
                return cls
        
        return None
    
    def get_file_structure(self, file_path: str) -> Dict[str, Any]:
        """
        Get the complete structure of a file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Dictionary with functions, classes, imports, and relationships
        """
        parsed = self.parse_file(file_path)
        if not parsed.get("success"):
            return parsed
        
        # Add relationships
        relationships = {
            "imports": parsed.get("imports", []),
            "exports": [],  # Could be enhanced
            "dependencies": [imp["module"] for imp in parsed.get("imports", [])]
        }
        
        parsed["relationships"] = relationships
        return parsed
    
    def clear_cache(self):
        """Clear the parser cache."""
        self._cache.clear()

