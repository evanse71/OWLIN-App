"""
Chat Service

Manages conversational chat with Ollama LLM, handles code context,
and formats responses for the chat assistant.
"""

import logging
import requests
import re
import time
import uuid
import json
import os
import threading
import math
from typing import List, Dict, Any, Optional, Tuple, Callable
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError as FutureTimeoutError
from difflib import SequenceMatcher
from backend.services.code_reader import CodeReader
from backend.services.code_explorer import CodeExplorer
from backend.services.code_verifier import CodeVerifier
from backend.services.response_validator import ResponseValidator
from backend.services.runtime_verifier import RuntimeVerifier
from backend.services.architecture_analyzer import ArchitectureAnalyzer
from backend.services.response_rewriter import ResponseRewriter
from backend.services.model_registry import get_registry, ModelRegistry
from backend.services.chat_metrics import get_metrics
from backend.services.retry_handler import RetryHandler
from backend.services.explorer_config import get_config
from backend.services.exploration_history import save_exploration_session

logger = logging.getLogger("owlin.services.chat_service")

# Agent system prompts
AGENT_SYSTEM_PROMPT = """You are a code detective agent for Owlin. Your job is to FIND problems, not just analyze what's given to you.

WORKFLOW:
1. UNDERSTAND the problem
2. EXPLORE the codebase to find relevant code
3. TRACE data flows
4. ANALYZE the actual code you find
5. DIAGNOSE the root cause with file:line references

AVAILABLE TOOLS:
- SEARCH <concept> - Find files/functions related to concept
- READ <file> - Read a file (you can request specific line ranges)
- TRACE <start> → <end> - Trace data flow between components
- GREP <pattern> - Search for code patterns
- FIND_CALLS <function> - Find where function is called

EXPLORATION STRATEGY:
When investigating a problem:
1. Start with broad searches (e.g., "line items", "upload display")
2. Narrow down to specific files
3. Read relevant code sections
4. Trace data flow through the code
5. Identify where the problem occurs

RESPONSE FORMAT:
After exploration, provide:
**Files Explored:** [list with line ranges]
**Data Flow:** [trace through code]
**Root Cause:** [specific file:line]
**Analysis Summary:** [what's missing, what's broken, where it occurs, why it happens]

CRITICAL: You must explore and find the code yourself. Don't ask for code - search for it!"""

AGENT_DEBUGGING_PROMPT = """You are a code detective agent investigating a bug in Owlin.

YOUR MISSION: Find the problem by verifying runtime behavior, not just reading code.

CRITICAL: VERIFY BEFORE FIXING
- Don't assume code executes - verify with logs
- Don't assume data exists - check database/API
- Don't assume conditions are met - add diagnostic logging
- Focus on PRIMARY issues (why data is empty) not SECONDARY (error handling)

AVAILABLE TOOLS:
- SEARCH <concept> - Find files/functions related to concept
- READ <file> - Read a file completely
- TRACE <start> → <end> - Trace data flow
- GREP <pattern> - Search for pattern (VERIFY function names exist!)
- ANALYZE - Provide analysis after exploration

WORKFLOW:
1. READ THE CODEBASE FIRST - Use READ, GREP, SEARCH to understand actual implementation
2. VERIFY FUNCTION NAMES - Use GREP to find actual function definitions BEFORE mentioning them
3. VERIFY EXISTING CODE - Check what logging/functions already exist (use GREP)
4. DETECT FRAMEWORK - Check if FastAPI/Flask, React/vanilla JS (use GREP for decorators/imports)
5. TRACE ACTUAL EXECUTION PATH - Follow real code flow through actual files
6. IDENTIFY SPECIFIC ISSUES - Find mismatches (invoice_id vs doc_id), wrong field names
7. VERIFY runtime behavior - Ask for logs, database queries, API responses
8. ADD diagnostic logging - Only where it doesn't already exist (check first with GREP)
9. DIAGNOSE the root cause - Based on actual code, not generic suggestions

CRITICAL RULES - NEVER VIOLATE THESE:

1. VERIFY FUNCTION NAMES BEFORE CLAIMING THEY EXIST:
   - NEVER mention a function name without first using GREP to verify it exists
   - Example: Before saying "upload_document()", run: GREP "def upload|@app.post.*upload"
   - If GREP finds nothing, the function DOES NOT EXIST - don't mention it
   - If GREP finds a different name (e.g., "upload_file"), use THAT name, not what you assumed
   - WRONG: "upload_document() calls extract_table_from_block()"
   - RIGHT: "GREP found upload_file() at backend/main.py:572, not upload_document()"

2. NEVER MAKE UP CODE EXAMPLES:
   - NEVER provide code examples unless you've READ the actual file
   - NEVER use Flask syntax (@app.route) if you haven't verified the framework
   - NEVER use request.form if you haven't verified FastAPI vs Flask
   - If you don't know the exact code, say: "I need to READ this file first to see the actual code"
   - WRONG: "@app.route('/upload', methods=['POST']) def upload_document(): doc_id = request.form['doc_id']"
   - RIGHT: "I need to READ backend/main.py to see the actual upload endpoint code"

3. VERIFY FRAMEWORK BEFORE ASSUMING:
   - Use GREP to check framework: GREP "@app\\.|@router\\.|from fastapi|from flask"
   - FastAPI uses: @app.post(), @router.post(), async def
   - Flask uses: @app.route(), def (not async)
   - React uses: import React, function Component, useState
   - Vanilla JS: No imports, just functions
   - WRONG: Assuming Flask when it's FastAPI
   - RIGHT: "GREP found @app.post() and 'from fastapi', so this is FastAPI, not Flask"

4. VERIFY LOGGING EXISTS BEFORE CLAIMING:
   - Use GREP to check if logging exists: GREP "Inserted.*line items|logger.info.*line"
   - If GREP finds nothing, the logging DOES NOT EXIST
   - WRONG: "logger.info(f'Inserted {len(line_items)} line items') exists"
   - RIGHT: "GREP found no logging for line items insertion. Actual logging is at ocr_service.py:316 with format [LINE_ITEMS]"

5. READ FILES COMPLETELY, NOT PARTIALLY:
   - READ the entire file, not just a snippet
   - Check function definitions, imports, decorators
   - Verify the actual function names, signatures, and structure
   - WRONG: Reading 10 lines and assuming the rest
   - RIGHT: READ backend/main.py completely to see all functions

6. USE ACTUAL FILE PATHS AND LINE NUMBERS:
   - NEVER use generic names like "file.py:100" or "ocr.py:50"
   - ALWAYS use actual paths: "backend/main.py:561" or "backend/services/ocr_service.py:266"
   - Use real line numbers from the code you've READ
   - Read files first to get exact line numbers

7. VERIFY RUNTIME BEHAVIOR FIRST - BE SPECIFIC:
   - Don't say: "Check backend logs"
   - Say: "Search logs for '[LINE_ITEMS]' messages and share: how many blocks, what types, any table blocks?"
   - Don't say: "Check if data is stored"
   - Say: "Run SQL: SELECT supplier, value, (SELECT COUNT(*) FROM invoice_line_items WHERE doc_id = invoices.doc_id) as items FROM invoices ORDER BY id DESC LIMIT 1;"
   - Don't say: "Check API response"
   - Say: "Run: curl http://localhost:8000/api/upload/status?doc_id=XXX and share the response"

8. PRIORITIZE BY LIKELIHOOD:
   - Don't list all possibilities equally
   - Rank by probability: "MOST LIKELY (90%): Table blocks not detected"
   - Then: "If that's not it (5%): Table extraction returns empty"
   - Then: "Least likely (5%): Format conversion fails"

9. PROVIDE EXACT LOGGING CODE (only if verified missing):
   - First: GREP to check if logging already exists
   - If missing: "Add: logger.info(f'[TABLE_EXTRACT] Block type: {{ocr_result.type}}') at backend/ocr/owlin_scan_pipeline.py:704"
   - Include the exact code snippet, file path, and line number
   - Use actual variable names from the code you READ

10. TRACE ACTUAL EXECUTION PATH:
   - Follow: Upload → OCR → Extraction → Storage → API → Frontend
   - Use actual file paths: "backend/main.py:561 → backend/services/ocr_service.py:266 → backend/app/db.py:323"
   - Use actual function names from GREP/READ, not assumed names
   - Check each step with specific queries/logs

11. FOCUS ON PRIMARY ISSUES:
   - Primary: Why is data empty/missing? (core problem)
   - Secondary: Error handling (can wait)
   - Don't fix secondary while primary is unsolved

VALIDATION CHECKLIST BEFORE ANALYSIS:
Before using ANALYZE, verify:
□ All function names mentioned were verified with GREP
□ All code examples are from actual READ files, not made up
□ Framework detected (FastAPI/Flask, React/vanilla JS) with GREP
□ All logging claims verified with GREP
□ All file paths are actual paths from READ commands
□ All line numbers are from actual code you READ
□ Execution path uses actual function names from GREP/READ

RESPONSE FORMAT - CRITICAL:
- Write primarily in TEXT explaining the problem
- Use SMALL code snippets (3-5 lines max) ONLY from actual code you READ
- Always include file:line references with each snippet
- DO NOT dump entire files or large code blocks
- Include: Verification steps, Runtime verification needed, Diagnostic steps, Root cause, Analysis summary

Example format (based on ACTUAL code you READ):
**Code Analysis**:
- **Files Read**: READ backend/services/ocr_service.py, READ backend/app/db.py, READ backend/main.py
- **Framework Detected**: GREP found "@app.post" and "from fastapi" → FastAPI (not Flask)
- **Functions Verified**: 
  - GREP "def upload" → Found: upload_file() at backend/main.py:572 (NOT upload_document)
  - GREP "def.*line.*item" → Found: insert_line_items() at backend/app/db.py:323
- **Existing Logging**: GREP "Inserted.*line items" → NOT FOUND. GREP "[LINE_ITEMS]" → Found at ocr_service.py:316
- **Execution Path** (from actual code): upload_file() → _run_ocr_background() → process_document_ocr_v2() → insert_line_items()

**Prioritized Diagnosis:**

1. **MOST LIKELY (90%): invoice_id/doc_id mismatch**
   - **Verified**: READ backend/services/ocr_service.py:285 shows `invoice_id = doc_id`
   - **Verified**: READ backend/app/db.py:343 shows `get_line_items_for_invoice(invoice_id)` queries by invoice_id
   - **Issue Found**: "At ocr_service.py:285, invoice_id = doc_id, but get_line_items_for_invoice() at db.py:343 queries by invoice_id. If doc_id doesn't match invoice_id in database, query returns empty."
   - **Add logging** (GREP verified [INVOICE_ID] doesn't exist): `logger.info(f'[INVOICE_ID] doc_id={{doc_id}}, invoice_id={{invoice_id}}')` at `backend/services/ocr_service.py:285`
   - **Verify**: "Run SQL: SELECT doc_id, invoice_id FROM invoices ORDER BY id DESC LIMIT 1;"
   - **If not this**: Move to next item

**Execution Path** (from actual code):
`backend/main.py:572` (upload_file - VERIFIED with GREP) → `backend/services/ocr_service.py:266` (process_document_ocr_v2 - VERIFIED with READ) → `backend/app/db.py:323` (insert_line_items - VERIFIED with READ)

**Root Cause**: "invoice_id/doc_id mismatch: ocr_service.py:285 sets invoice_id = doc_id, but database query at db.py:343 may not find matching invoice_id"

**Analysis Summary**: [What's missing, what's broken, where it occurs, why it happens - based on actual code you READ]

CRITICAL: 
- NEVER mention a function name without GREP verification
- NEVER provide code examples unless you READ the actual file
- NEVER assume framework - verify with GREP
- If you're not certain, say "I need to verify this first" and use GREP/READ"""


class TaskTracker:
    """Tracks agent mode tasks with status, timing, and results."""
    
    def __init__(self):
        self.tasks: Dict[str, Dict] = {}
        self.task_order: List[str] = []
    
    def add_task(self, task_id: str, task_type: str, description: str, metadata: Optional[Dict] = None):
        """Add a new task to track."""
        self.tasks[task_id] = {
            "id": task_id,
            "type": task_type,
            "title": description,  # Alias for description
            "description": description,
            "status": "pending",
            "progress": 0,
            "start_time": None,
            "end_time": None,
            "duration": None,
            "started_at": None,  # Timestamp in ms
            "ended_at": None,  # Timestamp in ms
            "duration_ms": None,  # Duration in ms
            "result_count": 0,
            "error": None,
            "note": None,  # Short error message or note
            "metadata": metadata or {}
        }
        if task_id not in self.task_order:
            self.task_order.append(task_id)
    
    def start_task(self, task_id: str):
        """Mark a task as running."""
        if task_id in self.tasks:
            self.tasks[task_id]["status"] = "running"
            self.tasks[task_id]["start_time"] = time.time()
            self.tasks[task_id]["started_at"] = int(time.time() * 1000)  # Timestamp in ms
    
    def update_progress(self, task_id: str, progress: int):
        """Update task progress (0-100)."""
        if task_id in self.tasks:
            self.tasks[task_id]["progress"] = max(0, min(100, progress))
    
    def complete_task(self, task_id: str, result_count: int = 0, error: Optional[str] = None):
        """Mark a task as completed or failed."""
        if task_id in self.tasks:
            self.tasks[task_id]["status"] = "done" if not error else "failed"
            self.tasks[task_id]["end_time"] = time.time()
            self.tasks[task_id]["ended_at"] = int(time.time() * 1000)  # Timestamp in ms
            if self.tasks[task_id]["start_time"]:
                duration = self.tasks[task_id]["end_time"] - self.tasks[task_id]["start_time"]
                self.tasks[task_id]["duration"] = duration
                self.tasks[task_id]["duration_ms"] = int(duration * 1000)
            self.tasks[task_id]["progress"] = 100  # Set to 100 on completion
            self.tasks[task_id]["result_count"] = result_count
            if error:
                self.tasks[task_id]["error"] = error
                self.tasks[task_id]["note"] = error[:200] if error else None  # Short note
    
    def get_tasks(self) -> List[Dict]:
        """Get all tasks in order."""
        return [self.tasks[tid] for tid in self.task_order if tid in self.tasks]


class ChatService:
    """Service for managing chat conversations with code context."""
    
    def __init__(self, ollama_url: str = "http://localhost:11434", models: Optional[List[str]] = None):
        """
        Initialize the chat service with multi-model support.
        
        Args:
            ollama_url: Base URL for Ollama API
            models: List of model names in priority order (default: auto-detect from registry)
        """
        self.ollama_url = ollama_url
        self.code_reader = CodeReader()
        self.code_explorer = CodeExplorer()
        self.code_verifier = CodeVerifier()
        self.response_validator = ResponseValidator()
        self.runtime_verifier = RuntimeVerifier()
        self.architecture_analyzer = ArchitectureAnalyzer()
        self.response_rewriter = ResponseRewriter(code_verifier=self.code_verifier)
        config = get_config()
        self.retry_handler = RetryHandler(
            failure_threshold=config.circuit_breaker_threshold,
            timeout=config.circuit_breaker_timeout
        )
        # Cache for relevance scores (key: (file_path, query_hash), value: score)
        self._relevance_score_cache: Dict[Tuple[str, str], float] = {}
        self._file_access_count: Dict[str, int] = {}  # Track file access frequency
        self.ollama_available = self._check_ollama_available()
        
        # Initialize model registry
        self.model_registry = get_registry(ollama_url)
        
        # Set up model priority list
        if models:
            self.models = models
        else:
            # Default priority order (32B first for best code understanding)
            self.models = [
                "qwen2.5-coder:32b",  # Best quality for code analysis
                "qwen2.5-coder:7b",   # Fast fallback
                "deepseek-coder:6.7b",
                "codellama:7b",
                "llama3.2:3b"
            ]
        
        # Get available models from registry
        try:
            self.available_models = [
                model.name for model in self.model_registry.get_available_models()
                if model.name in self.models
            ]
        except Exception as e:
            logger.warning(f"Error getting available models, using empty list: {e}")
            self.available_models = []
        
        # Performance metrics tracking
        self._perf_metrics = []
        self._metrics_file = Path(self.code_reader.repo_root) / "data" / "chat_metrics.jsonl"
        self._metrics_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Agent mode flag (initialized to False)
        self._in_agent_mode = False
        
        # Set primary model (first available from priority list)
        # Always set self.model to ensure it exists even if initialization fails
        try:
            if self.available_models:
                self.model = self.available_models[0]
            elif models and len(models) > 0:
                self.model = models[0]  # Fallback to first in list even if not available
            else:
                self.model = "codellama:7b"  # Final fallback
        except Exception as e:
            logger.warning(f"Error setting model, using fallback: {e}")
            self.model = "codellama:7b"  # Final fallback
        
        if self.ollama_available:
            logger.info(
                f"ChatService initialized with Ollama at {ollama_url}\n"
                f"Primary model: {self.model}\n"
                f"Available models: {', '.join(self.available_models) if self.available_models else 'none'}\n"
                f"Model priority: {', '.join(self.models)}"
            )
        else:
            logger.info("ChatService initialized without Ollama (will use fallback responses)")
    
    def _log_perf_metric(self, phase: str, **kwargs):
        """
        Log a performance metric to the metrics file.
        
        Args:
            phase: Phase name (e.g., "build_plan", "reads", "searches", "analysis_call")
            **kwargs: Additional metric data (ms, files, count, turns, model, ctx, attempts, etc.)
        """
        try:
            metric_entry = {
                "phase": phase,
                "timestamp": time.time(),
                **kwargs
            }
            
            # Append to metrics file (JSONL format)
            with open(self._metrics_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(metric_entry) + '\n')
            
            # Also log to logger for debugging (only if verbose)
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"Perf metric: {phase} - {kwargs}")
        except Exception as e:
            # Don't fail if metrics logging fails - just log a warning
            logger.warning(f"Failed to log performance metric: {e}")
    
    def _check_ollama_available(self) -> bool:
        """Check if Ollama is running and accessible."""
        endpoints_to_try = [
            "/api/tags",
            "/api/version", 
            "/"
        ]
        
        for endpoint in endpoints_to_try:
            try:
                url = f"{self.ollama_url}{endpoint}"
                logger.info(f"Checking Ollama at: {url}")
                response = requests.get(url, timeout=5)
                logger.info(f"Ollama response: status={response.status_code}, url={url}")
                
                if response.status_code == 200:
                    logger.info(f"✓ Ollama is available at {url}")
                    return True
            except requests.exceptions.ConnectionError as e:
                logger.warning(f"Connection failed to {url}: {e}")
            except requests.exceptions.Timeout as e:
                logger.warning(f"Timeout connecting to {url}: {e}")
            except Exception as e:
                logger.warning(f"Unexpected error checking {url}: {e}")
        
        logger.error(f"Ollama is NOT available at {self.ollama_url} (tried all endpoints)")
        return False
    
    def _classify_question(self, message: str) -> Dict[str, Any]:
        """
        Classify question type and extract intent.
        
        Returns:
            Dict with type, complexity, concepts, relationships
        """
        message_lower = message.lower()
        
        # Question type patterns
        debugging_patterns = [
            r"why\s+did\s+(.+?)\s+(?:but|however|yet)\s+(.+?)\s+(?:not|isn't|aren't|doesn't)",  # "why did X but Y not"
            r"why\s+did\s+(.+?)\s+(?:upload|work|succeed|complete)\s+but\s+(.+?)\s+(?:not|isn't|aren't|doesn't)",  # "why did upload but not showing"
            r"why\s+(?:doesn't|does|isn't|is|can't|can|won't|will)\s+(.+?)(?:\s+work|\s+show|\s+display|\s+appear)?",
            r"why\s+(?:is|are)\s+(.+?)\s+(?:not|missing|broken|wrong)",
            r"(.+?)\s+(?:doesn't|isn't|can't|won't)\s+(?:work|show|display|appear|load)",
            r"(.+?)\s+(?:not|missing|broken|wrong|failing)",
            r"(.+?)\s+(?:aren't|are\s+not)\s+(?:displayed|shown|appearing|working)",  # "aren't displayed"
            r"(.+?)\s+(?:was|were)\s+(?:successful|success)\s+but\s+(.+?)\s+(?:not|aren't|isn't)",  # "was successful but"
            r"(.+?)\s+(?:upload|uploaded)\s+but\s+(.+?)\s+(?:not|isn't|aren't|doesn't)",  # "uploaded but not showing"
            r"problem\s+with\s+(.+)",
            r"issue\s+with\s+(.+)",
            r"error\s+(?:with|in)\s+(.+)",
            r"find\s+(?:the|an?)\s+(?:issue|problem|bug|fault)",  # "find the issue"
            r"can\s+you\s+find\s+(?:the|an?)\s+(?:issue|problem|bug|fault)",  # "can you find the issue"
            r"can\s+you\s+provide\s+(?:the|actual)\s+code",  # "can you provide the actual code"
            r"show\s+me\s+(?:the|actual)\s+code",  # "show me the actual code"
            r"what\s+(?:is|are)\s+(?:the|an?)\s+(?:problem|issue|bug|fault)",  # "what is the problem"
        ]
        
        how_to_patterns = [
            r"how\s+(?:do|does|can|should)\s+(?:i|you|we)\s+(.+)",
            r"how\s+(?:to|do)\s+(.+)",
            r"how\s+(?:does|is)\s+(.+?)\s+(?:work|implemented|done)",
            r"steps?\s+(?:to|for)\s+(.+)",
            r"way\s+to\s+(.+)"
        ]
        
        what_is_patterns = [
            r"what\s+(?:is|are)\s+(.+)",
            r"what\s+(?:does|do)\s+(.+?)\s+(?:do|mean)",
            r"explain\s+(.+)",
            r"tell\s+me\s+about\s+(.+)",
            r"describe\s+(.+)"
        ]
        
        flow_patterns = [
            r"how\s+(?:does|do)\s+(.+?)\s+(?:flow|go|travel|move)",
            r"flow\s+(?:of|from|to)\s+(.+)",
            r"path\s+(?:of|from|to)\s+(.+)",
            r"(.+?)\s+(?:to|→|->)\s+(.+)",
            r"from\s+(.+?)\s+to\s+(.+)"
        ]
        
        comparison_patterns = [
            r"difference\s+(?:between|in)\s+(.+?)\s+(?:and|vs|versus)\s+(.+)",
            r"compare\s+(.+?)\s+(?:and|with|to)\s+(.+)",
            r"(.+?)\s+vs\s+(.+)",
            r"(.+?)\s+versus\s+(.+)"
        ]
        
        # Determine question type
        question_type = "general"
        complexity = "simple"
        concepts = []
        relationships = []
        
        # Check for debugging questions
        for pattern in debugging_patterns:
            match = re.search(pattern, message_lower, re.IGNORECASE)
            if match:
                question_type = "debugging"
                complexity = "complex"
                concepts.append(match.group(1).strip() if match.lastindex else "")
                break
        
        # Check for how-to questions
        if question_type == "general":
            for pattern in how_to_patterns:
                match = re.search(pattern, message_lower, re.IGNORECASE)
                if match:
                    question_type = "how-to"
                    concepts.append(match.group(1).strip() if match.lastindex else "")
                    break
        
        # Check for what-is questions
        if question_type == "general":
            for pattern in what_is_patterns:
                match = re.search(pattern, message_lower, re.IGNORECASE)
                if match:
                    question_type = "what-is"
                    concepts.append(match.group(1).strip() if match.lastindex else "")
                    break
        
        # Check for flow questions
        for pattern in flow_patterns:
            match = re.search(pattern, message_lower, re.IGNORECASE)
            if match:
                if question_type == "general":
                    question_type = "flow"
                complexity = "complex"
                if match.lastindex and match.lastindex >= 2:
                    relationships.append({
                        "from": match.group(1).strip(),
                        "to": match.group(2).strip()
                    })
                break
        
        # Check for comparison questions
        for pattern in comparison_patterns:
            match = re.search(pattern, message_lower, re.IGNORECASE)
            if match:
                question_type = "comparison"
                complexity = "complex"
                if match.lastindex and match.lastindex >= 2:
                    relationships.append({
                        "item1": match.group(1).strip(),
                        "item2": match.group(2).strip()
                    })
                break
        
        # Extract additional concepts from message
        if not concepts:
            # Extract noun phrases and technical terms
            tech_terms = [
                "upload", "line items", "line_items", "invoice", "card", "cards",
                "database", "api", "endpoint", "frontend", "backend", "ocr",
                "parsing", "storage", "display", "rendering", "component",
                "content", "contents", "data", "show", "appear", "visible"
            ]
            for term in tech_terms:
                if term in message_lower:
                    concepts.append(term)
        
        # Determine complexity based on indicators
        complexity_indicators = [
            "but", "however", "although", "even though",
            "not showing", "not displayed", "not appearing", "not working",
            "why", "problem", "issue", "error", "fail", "broken"
        ]
        if any(indicator in message_lower for indicator in complexity_indicators):
            complexity = "complex"
        
        # Check for multiple concepts (indicates complex question)
        if len(concepts) > 2 or relationships:
            complexity = "complex"
        
        return {
            "type": question_type,
            "complexity": complexity,
            "concepts": concepts,
            "relationships": relationships,
            "original_message": message
        }
    
    def _extract_concepts_and_flow(self, message: str, question_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract concepts and understand data flow relationships.
        
        Returns:
            Dict with concepts, relationships, flow_paths, implicit_files
        """
        concepts = question_analysis.get("concepts", [])
        relationships = question_analysis.get("relationships", [])
        flow_paths = []
        implicit_files = []
        
        # Common data flow patterns in Owlin
        flow_patterns = {
            "upload": ["backend/main.py", "backend/services/ocr_service.py", "backend/app/db.py"],
            "line items": ["backend/services/ocr_service.py", "backend/app/db.py", "backend/routes/invoices_submit.py"],
            "cards": ["frontend_clean/src/components/InvoiceCard.tsx", "frontend_clean/src/pages/Invoices.tsx"],
            "invoice": ["backend/app/db.py", "backend/routes/invoices_submit.py", "frontend_clean/src/lib/api.ts"],
            "ocr": ["backend/services/ocr_service.py", "backend/ocr/"],
            "database": ["backend/app/db.py", "migrations/"],
            "api": ["backend/routes/", "backend/main.py"],
            "frontend": ["frontend_clean/src/"]
        }
        
        # Extract flow relationships
        message_lower = message.lower()
        
        # Detect flow patterns like "upload → line items → cards"
        if "upload" in message_lower and ("line items" in message_lower or "line_items" in message_lower):
            flow_paths.append({
                "from": "upload",
                "to": "line items",
                "path": ["upload", "ocr", "parsing", "storage", "api", "frontend"]
            })
        
        if ("line items" in message_lower or "line_items" in message_lower) and "card" in message_lower:
            flow_paths.append({
                "from": "line items",
                "to": "cards",
                "path": ["database", "api", "frontend", "display"]
            })
        
        # Find implicit files based on concepts
        for concept in concepts:
            concept_lower = concept.lower()
            for pattern, files in flow_patterns.items():
                if pattern in concept_lower:
                    implicit_files.extend(files)
        
        # Remove duplicates
        implicit_files = list(set(implicit_files))
        
        # Extract additional concepts from relationships
        for rel in relationships:
            if "from" in rel:
                concepts.append(rel["from"])
            if "to" in rel:
                concepts.append(rel["to"])
            if "item1" in rel:
                concepts.append(rel["item1"])
            if "item2" in rel:
                concepts.append(rel["item2"])
        
        # Remove duplicates and empty strings
        concepts = list(set([c for c in concepts if c and len(c) > 1]))
        
        return {
            "concepts": concepts,
            "relationships": relationships,
            "flow_paths": flow_paths,
            "implicit_files": implicit_files
        }
    
    def chat(
        self,
        message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        context: Optional[Dict[str, Any]] = None,
        context_size: Optional[int] = None,
        use_search_mode: bool = False,
        use_agent_mode: bool = False,
        force_agent: bool = False,
        progress_callback: Optional[Callable[[str, int, int], None]] = None,
        request_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process a chat message and return response.
        
        Args:
            message: User's message
            conversation_history: Previous conversation messages
            context: Additional context (current page, etc.)
            
        Returns:
            Dict with response, code_references, and metadata
        """
        # Generate unique request ID and start timing
        if not request_id:
            request_id = str(uuid.uuid4())[:8]
        self._current_request_id = request_id
        start_time = time.time()
        
        # Initialize metrics tracking
        metrics = get_metrics()
        generic_detected = False
        forced_retry = False
        success = False
        
        # Classify question type and extract concepts
        question_analysis = self._classify_question(message)
        question_type = question_analysis.get('type', 'general')
        logger.info(
            f"[{request_id}] Question classified as: {question_type}, "
            f"complexity: {question_analysis.get('complexity')}"
        )
        
        # Detect if user is asking to read a file
        code_context = self._extract_code_requests(message)
        
        # Enhanced concept extraction for complex questions
        if question_analysis.get('complexity') == 'complex':
            enhanced_context = self._extract_concepts_and_flow(message, question_analysis)
            # Merge enhanced context into code_context
            code_context.setdefault("concepts", []).extend(enhanced_context.get("concepts", []))
            code_context.setdefault("relationships", []).extend(enhanced_context.get("relationships", []))
            code_context.setdefault("flow_paths", []).extend(enhanced_context.get("flow_paths", []))
            code_context.setdefault("implicit_files", []).extend(enhanced_context.get("implicit_files", []))
        
        # Determine which mode to use
        use_search_mode_active = False
        # Check for force flag (env or request param)
        from backend.config import AGENT_FORCE_ON
        force_agent_on = force_agent or AGENT_FORCE_ON
        
        use_agent_mode_active = False
        
        # Handle mode flag precedence: if both are set, prioritize Agent mode
        if use_search_mode and use_agent_mode:
            # Both flags set - prioritize Agent but warn
            logger.warning(f"[{request_id}] Both search_mode and agent_mode set - using Agent mode (Agent takes precedence)")
            use_agent_mode_active = True
            use_search_mode_active = False
        elif use_search_mode and not force_agent_on:
            # User explicitly requested Search mode (information gathering)
            logger.info(f"[{request_id}] Search mode requested by user")
            use_search_mode_active = True
        elif use_agent_mode or force_agent_on:
            # User explicitly requested Agent mode OR force flag is on
            logger.info(f"[{request_id}] Agent mode requested by user (force={force_agent_on})")
            use_agent_mode_active = True
        elif question_analysis and question_analysis.get("type") == "debugging":
            # Check if user question is vague and needs exploration
            if self._needs_exploration(message):
                logger.info(f"[{request_id}] Vague debugging question detected - using agent mode")
                use_agent_mode_active = True
            else:
                # User provided specific location, use existing flow
                auto_files = self._get_related_files_for_debugging(message, code_context)
                for file_path in auto_files:
                    if file_path not in code_context.get("files", []):
                        code_context.setdefault("files", []).append(file_path)
                        logger.info(f"Auto-included related file for debugging: {file_path}")
        
        logger.info(f"Extracted code context: {len(code_context.get('files', []))} files, {len(code_context.get('search_queries', []))} search queries")
        
        # Re-check Ollama availability (in case it started after initialization)
        self.ollama_available = self._check_ollama_available()
        
        # Use provided context_size or default to 128k (max available for local models)
        effective_context_size = context_size if context_size is not None else 128000
        logger.info(f"Using context size: {effective_context_size} tokens")
        
        # Optimize context budget to fit within token limits
        optimized_code_context = self._optimize_context_budget(
            code_context,
            effective_context_size,
            conversation_history
        )
        
        # Use Search or Agent mode
        exploration_metadata = None
        if use_search_mode_active and self.ollama_available:
            logger.info(f"[{request_id}] Using Search mode workflow")
            try:
                # Search mode: comprehensive information gathering
                response_text, metadata = self._search_mode_with_metadata(
                    message,
                    question_analysis,
                    conversation_history,
                    progress_callback
                )
                exploration_metadata = metadata
            except Exception as e:
                import traceback
                error_trace = traceback.format_exc()
                logger.error(f"Search mode failed: {e}\n{error_trace}")
                use_search_mode_active = False
                exploration_metadata = None
        elif use_agent_mode_active and self.ollama_available:
            logger.info(f"[{request_id}] Using Agent mode workflow")
            try:
                # Agent mode: autonomous problem-solving
                response_text = self._agent_mode_conversation(
                    message,
                    progress_callback=progress_callback,
                    context_size=context_size,
                    force_agent=force_agent_on
                )
                exploration_metadata = {
                    "mode": "agent",
                    "turns": "multiple"
                }
            except Exception as e:
                import traceback
                error_trace = traceback.format_exc()
                logger.error(f"Agent mode failed: {e}\n{error_trace}")
                
                # Fallback to Search mode when Agent cannot start (guard against 0-turn stalls)
                if "timeout" in str(e).lower() or "0 turns" in str(e).lower():
                    logger.warning("Agent mode timed out or produced 0 turns, falling back to Search mode")
                    try:
                        response_text, metadata = self._search_mode_with_metadata(
                            message,
                            question_analysis,
                            conversation_history,
                            progress_callback
                        )
                        exploration_metadata = metadata
                        use_agent_mode_active = False
                    except Exception as fallback_error:
                        logger.error(f"Search mode fallback also failed: {fallback_error}")
                        response_text = f"Both Agent and Search modes failed. Error: {str(e)}"
                        exploration_metadata = None
                else:
                    # Check if Ollama became unavailable during agent mode
                    self.ollama_available = self._check_ollama_available()
                    if not self.ollama_available:
                        logger.warning("Ollama became unavailable during agent mode, falling back to standard mode")
                    
                    use_agent_mode_active = False
                    response_text = f"Agent mode failed: {str(e)}"
                    exploration_metadata = None
        
        # Standard flow (or fallback from Search/Agent mode)
        if not use_search_mode_active and not use_agent_mode_active:
            # Build prompt with optimized code context
            prompt = self._build_prompt(message, conversation_history, optimized_code_context, context, question_analysis)
            
            # Get response from Ollama with cascading model fallback
            if self.ollama_available:
                response_text = self._call_ollama_with_fallback(
                    prompt,
                    conversation_history,
                    effective_context_size,
                    question_analysis,
                    optimized_code_context
                )
            else:
                logger.debug("Ollama not available, using fallback response")
                response_text = self._fallback_response(message, optimized_code_context, question_analysis)
        
        # Extract code references from response
        code_references = self._extract_code_references(response_text, code_context)
        logger.info(f"Generated response with {len(code_references)} code references")
        
        # Determine which model was used
        code_files_count = len(code_context.get("files", []))
        selected_model, _ = self._select_model_for_request(
            question_analysis.get("type", "general"),
            effective_context_size,
            code_files_count
        )
        model_used = selected_model or self.model
        
        # Calculate response time and mark success
        response_time = time.time() - start_time
        success = True
        
        # Check if response is generic (for metrics)
        if question_analysis.get("type") == "debugging":
            generic_detected = self._is_generic_response(response_text)
        
        # Log metrics
        try:
            metrics.log_request(
                request_id=request_id,
                message=message,
                question_type=question_type,
                context_size=effective_context_size,
                files_count=code_files_count,
                model_selected=model_used,
                response_time=response_time,
                success=success,
                generic_detected=generic_detected,
                forced_retry=forced_retry,
                code_references_count=len(code_references)
            )
        except Exception as e:
            logger.error(f"Failed to log metrics: {e}")
        
        logger.info(
            f"[{request_id}] Request completed in {response_time:.2f}s: "
            f"model={model_used}, files={code_files_count}, refs={len(code_references)}, "
            f"generic={generic_detected}"
        )
        
        return {
            "response": response_text,
            "code_references": code_references,
            "model_used": model_used,
            "ollama_available": self.ollama_available,
            "request_id": request_id,
            "exploration_mode": use_search_mode_active or use_agent_mode_active,
            "exploration_metadata": exploration_metadata
        }
    
    def _extract_code_requests(self, message: str) -> Dict[str, Any]:
        """Extract file reading requests from user message."""
        code_context = {
            "files": [],
            "search_queries": []
        }
        
        # Look for file references with improved patterns for full paths
        # Pattern 1: "show me backend/main.py" or "read frontend_clean/src/pages/Invoices.tsx"
        # Pattern 2: "backend/main.py file" or "main.py code"
        # Pattern 3: "in backend/main.py" or "from upload.py"
        # Pattern 4: Paths with slashes/backslashes (Windows compatible)
        file_patterns = [
            r"(?:show|read|open|see|view)\s+(?:me\s+)?(?:the\s+)?(?:file\s+)?([a-zA-Z0-9_/\\\.-]+(?:/[a-zA-Z0-9_/\\\.-]+)*\.(?:py|tsx?|ts|jsx?|js|json|yaml|yml|md))",
            r"([a-zA-Z0-9_/\\\.-]+(?:/[a-zA-Z0-9_/\\\.-]+)*\.(?:py|tsx?|ts|jsx?|js))\s+(?:file|code)",
            r"(?:in|from|at)\s+([a-zA-Z0-9_/\\\.-]+(?:/[a-zA-Z0-9_/\\\.-]+)*\.(?:py|tsx?|ts|jsx?|js))",
            # Match paths that look like file paths (contain slashes and extension)
            r"([a-zA-Z0-9_]+(?:[/\\][a-zA-Z0-9_/\\\.-]+)+\.(?:py|tsx?|ts|jsx?|js|json|yaml|yml|md))"
        ]
        
        found_paths = set()  # Track found paths to avoid duplicates
        
        for pattern in file_patterns:
            matches = re.finditer(pattern, message, re.IGNORECASE)
            for match in matches:
                file_path = match.group(1).strip()
                # Normalize path separators (Windows backslash to forward slash)
                file_path = file_path.replace("\\", "/")
                
                if file_path in found_paths:
                    continue
                
                # Try direct path resolution first (for full paths like "backend/main.py")
                if "/" in file_path or "\\" in file_path:
                    # Try reading the file directly
                    file_data = self.code_reader.read_file(file_path)
                    if file_data.get("success"):
                        code_context["files"].append(file_path)
                        found_paths.add(file_path)
                        logger.info(f"Found file via direct path: {file_path}")
                        continue
                
                # If direct path didn't work, try smart resolution
                resolved = self.code_reader.resolve_file_path(file_path)
                if resolved:
                    code_context["files"].append(resolved)
                    found_paths.add(resolved)
                    logger.info(f"Found file via resolution: {file_path} -> {resolved}")
                    continue
                
                # Fallback: search by filename only
                filename = file_path.split("/")[-1]
                found_files = self.code_reader.find_files_by_name(filename, max_results=1)
                if found_files and found_files[0] not in found_paths:
                    code_context["files"].append(found_files[0])
                    found_paths.add(found_files[0])
                    logger.info(f"Found file via name search: {filename} -> {found_files[0]}")
        
        # Look for search queries (e.g., "find upload function", "search for database connection", "read the upload code")
        search_patterns = [
            r"(?:find|search|look\s+for|read|show)\s+(?:me\s+)?(?:the\s+)?(.+?)(?:\s+function|\s+code|\s+in\s+code)?$",
            r"where\s+(?:is|does)\s+(.+?)(?:\s+defined|\s+located)?",
            r"(?:the\s+)?(.+?)\s+(?:code|function|connection|endpoint|route)"  # Catch "upload code", "database connection", etc.
        ]
        
        for pattern in search_patterns:
            matches = re.finditer(pattern, message, re.IGNORECASE)
            for match in matches:
                query = match.group(1).strip()
                if len(query) > 3:  # Ignore very short queries
                    code_context["search_queries"].append(query)
        
        return code_context
    
    def _optimize_context_budget(
        self,
        code_context: Dict[str, Any],
        effective_context_size: int,
        conversation_history: Optional[List[Dict[str, str]]],
        system_prompt_estimate: int = 2000
    ) -> Dict[str, Any]:
        """
        Optimize context budget to fit within token limits.
        
        Budget allocation:
        - 20% for system prompt + conversation history
        - 50% for code context
        - 30% reserved for response
        
        Args:
            code_context: Code files and context
            effective_context_size: Total context window size
            conversation_history: Chat history
            system_prompt_estimate: Estimated tokens for system prompt
            
        Returns:
            Optimized code_context with pruned files if necessary
        """
        # Calculate token budgets - maximize code context for local processing
        reserved_for_response = int(effective_context_size * 0.10)  # Reduced to 10% (was 30%)
        reserved_for_system = int(effective_context_size * 0.05)   # Reduced to 5% (was 20%)
        available_for_code = effective_context_size - reserved_for_response - reserved_for_system  # Now 85% for code!
        
        # Estimate conversation history tokens (rough: 4 chars per token)
        conv_tokens = 0
        if conversation_history:
            conv_chars = sum(len(msg.get("content", "")) for msg in conversation_history)  # Use all history
            conv_tokens = conv_chars // 4
        
        # Adjust available budget
        available_for_code = max(1000, available_for_code - conv_tokens)
        
        logger.info(
            f"Context budget: total={effective_context_size}, "
            f"code={available_for_code}, system={reserved_for_system}, "
            f"response={reserved_for_response}"
        )
        
        # Estimate tokens for code files (rough: 4 chars per token)
        files = code_context.get("files", [])
        file_priorities = []
        
        for idx, file_path in enumerate(files):
            # Earlier files in the list are more relevant (based on pattern matching)
            priority = len(files) - idx
            
            # Estimate file size
            file_data = self.code_reader.read_file(file_path, max_lines=1)
            total_lines = file_data.get("total_lines", 100)
            estimated_tokens = total_lines * 20  # Rough estimate: 20 tokens per line
            
            file_priorities.append({
                "path": file_path,
                "priority": priority,
                "estimated_tokens": estimated_tokens,
                "max_lines": min(estimated_tokens // 20, total_lines)  # Use full file if budget allows
            })
        
        # Sort by priority
        file_priorities.sort(key=lambda x: x["priority"], reverse=True)
        
        # Allocate budget to files
        optimized_files = []
        tokens_used = 0
        
        for file_info in file_priorities:
            if tokens_used >= available_for_code:
                logger.info(f"Context budget exhausted, skipping {file_info['path']}")
                break
            
            remaining_budget = available_for_code - tokens_used
            
            if file_info["estimated_tokens"] <= remaining_budget:
                # File fits completely
                optimized_files.append({
                    "path": file_info["path"],
                    "max_lines": file_info["max_lines"],
                    "truncated": False
                })
                tokens_used += file_info["estimated_tokens"]
            elif remaining_budget > 500:  # At least 500 tokens left
                # Include partial file
                lines_to_include = int((remaining_budget / 20) * 0.8)  # Use 80% of remaining
                optimized_files.append({
                    "path": file_info["path"],
                    "max_lines": max(50, lines_to_include),  # Removed 500 cap - use full budget
                    "truncated": True
                })
                tokens_used += remaining_budget
                logger.info(f"Truncating {file_info['path']} to {lines_to_include} lines")
            else:
                logger.info(f"Insufficient budget for {file_info['path']}, skipping")
        
        # Update code_context with optimized files
        optimized_context = code_context.copy()
        optimized_context["files"] = [f["path"] for f in optimized_files]
        optimized_context["file_specs"] = optimized_files  # Include line limits
        
        logger.info(f"Optimized context: {len(optimized_files)}/{len(files)} files, ~{tokens_used} tokens")
        
        return optimized_context
    
    def _get_framework_context(self, code_context: Dict[str, Any], message: str) -> str:
        """
        Detect framework from code context and generate framework-specific prompt context.
        
        Args:
            code_context: Code context with files
            message: User message (to detect if framework-relevant)
            
        Returns:
            Framework context string to add to system prompt
        """
        # Only detect framework if message is about code/API/endpoints
        framework_keywords = ["endpoint", "api", "route", "upload", "post", "get", "decorator", 
                              "fastapi", "flask", "async", "def ", "function"]
        if not any(keyword in message.lower() for keyword in framework_keywords):
            return ""
        
        # Try to detect framework from files in context
        framework_result = None
        files_to_check = code_context.get("files", [])
        
        # Also check common backend files if no files in context
        if not files_to_check:
            common_files = ["backend/main.py", "backend/routes/upload.py", "backend/routes/documents.py"]
            files_to_check = common_files
        
        for file_path in files_to_check[:3]:  # Check up to 3 files
            try:
                result = self.architecture_analyzer.detect_framework(file_path)
                if result.get("confidence", 0) > 0.7:
                    framework_result = result
                    break
            except Exception as e:
                logger.debug(f"Framework detection failed for {file_path}: {e}")
                continue
        
        if not framework_result or framework_result.get("framework") == "unknown":
            return ""
        
        framework = framework_result["framework"]
        syntax_rules = framework_result.get("syntax_rules", {})
        confidence = framework_result.get("confidence", 0)
        
        # Build framework context
        context_parts = [
            f"\n\n=== FRAMEWORK DETECTION ===",
            f"This codebase uses {framework.upper()} (detected with {confidence:.0%} confidence).",
            f"You MUST use {framework.upper()} syntax in all code suggestions."
        ]
        
        # Add framework-specific rules
        if syntax_rules:
            allowed_decorators = syntax_rules.get("allowed_decorators", [])
            forbidden_decorators = syntax_rules.get("forbidden_decorators", [])
            forbidden_patterns = syntax_rules.get("forbidden_patterns", [])
            async_required = syntax_rules.get("async_required", False)
            request_access = syntax_rules.get("request_access", "")
            
            if allowed_decorators:
                context_parts.append(f"\nALLOWED DECORATORS: {', '.join(allowed_decorators[:3])}")
            if forbidden_decorators:
                context_parts.append(f"FORBIDDEN DECORATORS: {', '.join(forbidden_decorators)} - DO NOT USE THESE")
            if forbidden_patterns:
                context_parts.append(f"FORBIDDEN PATTERNS: {', '.join(forbidden_patterns)} - DO NOT USE THESE")
            if async_required:
                context_parts.append(f"ASYNC REQUIRED: Use 'async def' for endpoint functions")
            if request_access:
                context_parts.append(f"REQUEST ACCESS: {request_access}")
            
            example = syntax_rules.get("example", "")
            if example:
                context_parts.append(f"\nEXAMPLE SYNTAX:\n{example}")
        
        context_parts.append("=== END FRAMEWORK DETECTION ===\n")
        
        return "\n".join(context_parts)
    
    def _build_prompt(
        self,
        message: str,
        conversation_history: Optional[List[Dict[str, str]]],
        code_context: Dict[str, Any],
        context: Optional[Dict[str, Any]],
        question_analysis: Optional[Dict[str, Any]] = None
    ) -> str:
        """Build the prompt for Ollama with code context."""
        
        # Detect framework and get framework context
        framework_context = self._get_framework_context(code_context, message)
        
        # System prompt - enhanced for complex questions
        if question_analysis and question_analysis.get("complexity") == "complex":
            question_type = question_analysis.get("type", "general")
            if question_type == "debugging":
                system_prompt = """You are an expert code debugger analyzing Owlin's codebase.""" + framework_context + """

CRITICAL RULES:
1. EXPLAIN PROBLEMS IN TEXT - write clear explanations, don't just dump code
2. USE SMALL CODE SNIPPETS - 3-5 lines max per snippet, only to illustrate points
3. ALWAYS INCLUDE file:line references with each snippet
4. ANALYZE THE PROVIDED CODE - reference specific line numbers
5. TRACE DATA FLOW - show how data moves through files (in text, with file:line references)
6. IDENTIFY ROOT CAUSE - explain what's breaking and why (in text)
7. PROVIDE SPECIFIC FIX - exact code changes with file paths (small snippets only)
8. NEVER dump entire files or large code blocks
9. NEVER give generic troubleshooting advice

SYSTEM CONTEXT:
- Owlin is a fully offline invoice and delivery-verification platform
- Data flow: Upload → OCR → Parse → Normalize → Match → Detect Issues → Forecast → Dashboard
- Frontend: React 18 + Vite + TanStack Query (port 5176)
- Backend: FastAPI Python 3.12+ (port 8000)
- Database: SQLite WAL mode (data/owlin.db)
- Key tables: documents, invoices, invoice_line_items, issues

MANDATORY RESPONSE FORMAT:
Your response MUST follow this exact format. Do not skip steps.

**Step 1: Files Analyzed**
List the specific files you analyzed with line ranges:
- `file1.ts` (lines 217-263)
- `file2.py` (lines 630-723)
- etc.

**Step 2: Data Flow Trace**
Trace the exact path through the code showing how data flows:
- Start: [file.py:494] Upload endpoint returns {status: 'processing'}
- Step 1: [file.ts:224] Frontend polls /api/upload/status
- Step 2: [file.py:630] Status endpoint returns {items: [...]}
- Step 3: [file.ts:240] Normalize function merges response
- End: [file.tsx:12] Component displays metadata.lineItems

**Step 3: Code Analysis**
EXPLAIN THE PROBLEM IN TEXT. Use small code snippets (3-5 lines max) to illustrate your points. DO NOT dump entire files.

For each relevant code section, explain the problem in text, then show a small snippet:
The issue is that the condition doesn't handle the 'ready' status properly. Here's the problematic code:

```typescript
// upload.ts:236-238
const hasData = statusData.parsed || statusData.invoice || (statusData.status && statusData.status !== 'processing')
const hasItems = Array.isArray(statusData.items) && statusData.items.length > 0
```

**Explanation:** This condition checks if data exists, but if status is 'ready' and parsed is null, hasData will be false even though the invoice is processed. The logic assumes parsed or invoice must exist, but doesn't account for the 'ready' state where data might be in a different field.

**Step 4: Root Cause**
Identify the exact problem with file:line references:
- Issue: In `upload.ts:236`, the condition doesn't account for status='ready' when parsed is null
- Impact: Polling stops before data is available
- Location: `frontend_clean/src/lib/upload.ts` line 236

**Step 5: Fix**
Provide exact code changes with before/after:

BEFORE (upload.ts:236):
```typescript
const hasData = statusData.parsed || statusData.invoice || (statusData.status && statusData.status !== 'processing')
```

AFTER (upload.ts:236):
```typescript
const hasData = statusData.parsed || statusData.invoice || statusData.status === 'ready' || statusData.status === 'scanned' || (statusData.status && statusData.status !== 'processing')
```

CHAIN-OF-THOUGHT REQUIREMENT:
Show your reasoning step-by-step. For each file you analyze, explain:
- What this code does
- How it relates to the problem
- What you found (or didn't find) that's relevant

RESPONSE VALIDATION CHECKLIST:
Before submitting your response, verify:
- Did I quote actual code lines? (If no, add them)
- Did I provide file paths and line numbers? (If no, add them)
- Did I trace the data flow through actual code? (If no, do it)
- Am I giving generic advice? (If yes, replace with code-specific analysis)

CODE FLOW DIAGRAM:
For complex questions, include a text-based flow diagram showing the actual code path:
```
Upload → [main.py:494] → Status Check → [upload.ts:224] → Normalize → [upload.ts:59] → Display → [InvoiceDetailPanel.tsx:12]
```

CRITICAL ANTI-HALLUCINATION RULES:
- ONLY reference code that is actually provided in the context above
- If you don't see specific code, say "I need to see the code for [component]" - DO NOT make up code
- Always cite file paths and line numbers: `file.py:123`
- If you're unsure, ask for more code rather than guessing
- Base your analysis ONLY on the code provided, not assumptions or general knowledge
- When suggesting fixes, quote the exact code from the files provided
- If a file isn't in the context, explicitly state you need to see it
- DO NOT give generic responses like "check your configuration" or "ensure dependencies are installed"
- DO NOT provide troubleshooting steps without analyzing the actual code first

EXAMPLES:

BAD RESPONSE #1 (DO NOT DO THIS):
"Here are potential causes:
1. File format issues
2. File size limitations
3. File corruption
..."
This is generic and doesn't analyze the actual code.

BAD RESPONSE #2 (DO NOT DO THIS):
"Based on your description, it seems like there may be an issue with the OCR processing..."
This gives generic advice without looking at code.

BAD RESPONSE #3 (DO NOT DO THIS):
"Check if data is being extracted correctly. Verify data is stored in the database..."
This provides troubleshooting steps without analyzing actual code.

GOOD RESPONSE (DO THIS - COMPLETE EXAMPLE):
**Step 1: Files Analyzed**
Analyzing the following files:
- `frontend_clean/src/lib/upload.ts` (lines 217-263)
- `backend/main.py` (lines 630-723)
- `frontend_clean/src/components/InvoiceDetailPanel.tsx` (lines 1-50)

**Step 2: Data Flow Trace**
Tracing the data flow through the code:
- Start: [main.py:494] Upload endpoint receives file, returns {doc_id, status: 'processing'}
- Step 1: [upload.ts:224] Frontend calls `/api/upload/status?doc_id=${docId}`
- Step 2: [main.py:630] Status endpoint queries database: `SELECT ... FROM invoices WHERE doc_id = ?`
- Step 3: [main.py:691] Status endpoint returns {parsed: {...}, items: [...], invoice: {...}}
- Step 4: [upload.ts:240] Merged response combines statusData.parsed, statusData.invoice, and statusData.items
- Step 5: [upload.ts:250] normalizeUploadResponse extracts lineItems from merged response
- Step 6: [InvoiceDetailPanel.tsx:12] Component reads `metadata.lineItems || []`
- End: [InvoiceDetailPanel.tsx:15] Component renders lineItems array

**Step 3: Code Analysis**

File: frontend_clean/src/lib/upload.ts (lines 236-238)
```
 236: const hasData = statusData.parsed || statusData.invoice || (statusData.status && statusData.status !== 'processing')
 237: const hasItems = Array.isArray(statusData.items) && statusData.items.length > 0
 238: if (hasData || hasItems) {
```
Analysis: The condition on line 236 checks if parsed or invoice exists, OR if status is not 'processing'. However, if the status is 'ready' but parsed is null (which can happen if invoice was created but parsed data wasn't stored), hasData will be false. This causes polling to stop before the invoice data is available.

File: frontend_clean/src/lib/upload.ts (lines 240-248)
```
 240: const mergedResponse = {
 241:   ...statusData,
 242:   ...statusData.parsed,
 243:   ...statusData.invoice,
 244:   line_items: statusData.items || statusData.invoice?.items || [],
 245:   items: statusData.items || statusData.invoice?.items || [],
 246:   raw: statusData,
 247: }
 248: return normalizeUploadResponse(mergedResponse, undefined, Date.now())
```
Analysis: The merge looks correct - it combines all data sources. However, if statusData.items is an empty array (not null/undefined), line_items will be [] even if invoice.items has data.

**Step 4: Root Cause**
- Primary Issue: In `upload.ts:236`, the polling condition doesn't account for status='ready' when parsed is null
- Secondary Issue: In `upload.ts:244`, if statusData.items is [] (empty array), it takes precedence over statusData.invoice?.items
- Impact: Frontend stops polling before invoice data is available, or gets empty line_items even when invoice.items has data
- Location: `frontend_clean/src/lib/upload.ts` lines 236 and 244

**Step 5: Fix**

Fix #1: Update polling condition (upload.ts:236)
BEFORE:
```typescript
const hasData = statusData.parsed || statusData.invoice || (statusData.status && statusData.status !== 'processing')
```

AFTER:
```typescript
const hasData = statusData.parsed || statusData.invoice || statusData.status === 'ready' || statusData.status === 'scanned' || (statusData.status && statusData.status !== 'processing')
```

Fix #2: Improve items merge logic (upload.ts:244)
BEFORE:
```typescript
line_items: statusData.items || statusData.invoice?.items || [],
```

AFTER:
```typescript
line_items: (Array.isArray(statusData.items) && statusData.items.length > 0) ? statusData.items : (statusData.invoice?.items || []),
```

This analyzes actual code with specific line numbers and provides exact fixes.

Be thorough, systematic, and provide actionable code-level solutions."""
            elif question_type == "flow":
                system_prompt = """You are a code flow analyzer for Owlin. Explain how data flows through the system:""" + framework_context + """

SYSTEM CONTEXT:
- Owlin processes invoices through: Upload → OCR → Parse → Normalize → Match → Detect Issues → Forecast → Dashboard
- Frontend (React) communicates with Backend (FastAPI) via REST API
- Data is stored in SQLite database (data/owlin.db)

FLOW ANALYSIS:
1. Show the complete path from start to end
2. Identify each component (file, function, API endpoint)
3. Show code at each stage with file paths
4. Highlight data transformations and structure changes
5. Show how frontend consumes backend APIs

Use clear step-by-step explanations with code references."""
            else:
                system_prompt = """You are a helpful code assistant for Owlin, an offline invoice processing platform.""" + framework_context + """

SYSTEM CONTEXT:
- Owlin processes invoices: Upload → OCR → Parse → Normalize → Match → Detect Issues → Forecast → Dashboard
- Frontend: React 18 + Vite (frontend_clean/src/)
- Backend: FastAPI Python (backend/)
- Database: SQLite (data/owlin.db)

Provide detailed, structured answers with code examples. Reference specific files and line numbers."""
        else:
            system_prompt = """You are a debugging assistant for Owlin, an offline invoice processing platform for hospitality venues.""" + framework_context + """

SYSTEM OVERVIEW:
- Owlin processes invoices through: Upload → OCR → Parse → Normalize → Match → Detect Issues → Forecast → Dashboard
- Frontend: React 18 + Vite + TanStack Query (frontend_clean/src/)
- Backend: FastAPI Python 3.12+ (backend/)
- Database: SQLite WAL mode (data/owlin.db)
- Key components: documents, invoices, invoice_line_items tables

YOUR ROLE:
- Analyze code systematically to find bugs and issues
- Trace data flow through the system
- Identify where problems occur in the pipeline
- Provide specific code fixes with file paths and line numbers
- Check for mismatches between frontend expectations and backend responses
- Verify database operations and API endpoints

When analyzing code:
1. Read the actual code files provided
2. Identify what's wrong (missing data, incorrect logic, API mismatches)
3. Trace where the problem occurs in the data flow
4. Suggest specific fixes with code examples

CRITICAL ANTI-HALLUCINATION RULES:
- ONLY reference code that is actually provided in the context above
- If you don't see specific code, say "I need to see the code for [component]" - DO NOT make up code
- Always cite file paths and line numbers: `file.py:123`
- If you're unsure, ask for more code rather than guessing
- Base your analysis ONLY on the code provided, not assumptions
- When suggesting fixes, quote the exact code from the files provided

Be thorough, systematic, and provide actionable solutions."""

        # Add code context if files were requested
        code_snippets = []
        if code_context["files"]:
            # Check if file_specs are provided (from context budgeting optimization)
            file_specs = code_context.get("file_specs", [])
            file_specs_dict = {spec["path"]: spec for spec in file_specs if isinstance(spec, dict)}
            
            for file_path in code_context["files"]:  # No limit (local processing)
                # Use max_lines from file_specs if available, otherwise use high default for local processing
                max_lines = 5000  # Increased default for local processing
                if file_path in file_specs_dict:
                    max_lines = file_specs_dict[file_path].get("max_lines", 5000)  # Increased default
                
                file_data = self.code_reader.read_file(file_path, max_lines=max_lines)
                if file_data.get("success"):
                    content = file_data['content']
                    lines_read = file_data.get('lines_read', 0)
                    total_lines = file_data.get('total_lines', 0)
                    start_line = 1  # Files are read from the beginning
                    end_line = lines_read
                    
                    # Add line numbers to code content
                    # Handle edge cases: trailing newlines, Windows line endings, empty files
                    lines = content.split('\n')
                    # Remove trailing empty line if file ends with newline
                    if lines and lines[-1] == '' and content.endswith('\n'):
                        lines = lines[:-1]
                    
                    numbered_lines = []
                    for i, line in enumerate(lines, start=start_line):
                        # Remove Windows line endings if present
                        line = line.rstrip('\r')
                        numbered_lines.append(f"{i:4}: {line}")
                    numbered_content = '\n'.join(numbered_lines)
                    
                    # Format file header with line range
                    truncation_note = ""
                    if file_data.get("truncated"):
                        truncation_note = f" (showing lines {start_line}-{end_line} of {total_lines})"
                    else:
                        truncation_note = f" (lines {start_line}-{end_line})"
                    
                    code_snippets.append(f"File: {file_path}{truncation_note}\n```\n{numbered_content}\n```")
                else:
                    logger.warning(f"Failed to read file {file_path}: {file_data.get('error')}")
        
        # Add search results if queries were made
        if code_context["search_queries"]:
            for query in code_context["search_queries"]:  # No limit (local processing)
                results = self.code_reader.search_codebase(query, max_results=50)  # Increased for local processing
                if results:
                    snippets = "\n".join([f"{r['file_path']}:{r['line']} - {r['content']}" for r in results])
                    code_snippets.append(f"Search results for '{query}':\n{snippets}")
        
        # Log if no code was provided for debugging questions
        if question_analysis and question_analysis.get("type") == "debugging" and not code_snippets:
            logger.warning("DEBUGGING QUESTION BUT NO CODE CONTEXT PROVIDED - This will lead to generic responses!")
            logger.warning(f"Code context had {len(code_context.get('files', []))} files but none were readable")
        
        # Build full prompt
        prompt_parts = [system_prompt]
        
        if code_snippets:
            prompt_parts.append("\n=== CODE CONTEXT - YOU MUST ANALYZE THIS CODE ===")
            prompt_parts.append("The following code files are provided with line numbers. You MUST analyze them to answer the question.")
            prompt_parts.append("DO NOT give generic responses. You MUST reference specific code lines and file paths.")
            prompt_parts.append("The code includes line numbers in the format 'LINE: code'. Use these line numbers in your analysis.")
            prompt_parts.extend(code_snippets)
            prompt_parts.append("\n=== END CODE CONTEXT ===")
            if question_analysis and question_analysis.get("type") == "debugging":
                prompt_parts.append("\n=== MANDATORY ANALYSIS REQUIREMENTS ===")
                prompt_parts.append("You MUST start your response with 'Analyzing the following files:' and list all files you examined.")
                prompt_parts.append("You MUST quote at least 3 specific code lines from different files with their line numbers.")
                prompt_parts.append("You MUST show the data transformation at each step of the flow.")
                prompt_parts.append("You MUST follow the 5-step response format: Files Analyzed → Data Flow Trace → Code Analysis → Root Cause → Fix")
                prompt_parts.append("DO NOT give generic troubleshooting advice. Analyze the actual code provided above.")
                prompt_parts.append("DO NOT skip any steps in the mandatory response format.")
        else:
            if question_analysis and question_analysis.get("type") == "debugging":
                prompt_parts.append("\n=== WARNING: No code context provided ===")
                prompt_parts.append("This is a debugging question but no code files were found. Please request specific files to analyze.")
        
        if context and context.get("error_logs"):
            log_data = self.code_reader.read_error_logs(max_lines=30)
            if log_data.get("success"):
                prompt_parts.append(f"\n=== Recent Error Logs ===\n{log_data['content']}")
                
                # Add code context from files referenced in errors
                if log_data.get("file_references"):
                    error_code_snippets = []
                    for ref in log_data["file_references"]:  # No limit (local processing)
                        file_data = self.code_reader.read_file_with_context(
                            ref["file"], 
                            ref["line"], 
                            context_lines=10
                        )
                        if file_data.get("success"):
                            error_code_snippets.append(
                                f"File: {ref['file']}:{ref['line']} (from error log)\n"
                                f"Error context: {ref.get('error_line', 'N/A')}\n"
                                f"```\n{file_data['content']}\n```"
                            )
                    if error_code_snippets:
                        prompt_parts.append("\n=== Code from Error Locations ===")
                        prompt_parts.extend(error_code_snippets)
        
        # Add document/invoice context if user is asking about documents
        if context and ("document" in message.lower() or "invoice" in message.lower() or "fail" in message.lower() or "error" in message.lower()):
            doc_context = self._get_document_context(context)
            if doc_context:
                prompt_parts.append(f"\n=== Document Context ===\n{doc_context}")
        
        # Build comprehensive context for complex questions
        if question_analysis and question_analysis.get("complexity") == "complex":
            comprehensive_context = self._build_comprehensive_context(
                question_analysis.get("type", "general"),
                code_context.get("concepts", []),
                code_context
            )
            if comprehensive_context:
                prompt_parts.append("\n=== Comprehensive Context ===")
                for section, content in comprehensive_context.items():
                    if content:
                        prompt_parts.append(f"\n--- {section} ---\n{content}")
        
        prompt_parts.append(f"\n=== User Question ===\n{message}")
        
        return "\n".join(prompt_parts)
    
    def _build_comprehensive_context(self, question_type: str, concepts: List[str], code_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build comprehensive context for complex questions.
        
        Returns:
            Dict with files, code_snippets, api_routes, db_operations, errors, related_code
        """
        context = {
            "files": [],
            "code_snippets": [],
            "api_routes": [],
            "db_operations": [],
            "related_code": []
        }
        
        # Gather files from implicit_files if available
        implicit_files = code_context.get("implicit_files", [])
        for file_path in implicit_files:  # No limit (local processing)
            file_data = self.code_reader.read_file(file_path, max_lines=5000)  # Increased from 100
            if file_data.get("success"):
                context["files"].append(file_path)
                context["code_snippets"].append(f"**{file_path}**\n```\n{file_data['content']}\n```")
        
        # For flow questions, trace the data flow
        if question_type == "flow" or question_type == "debugging":
            flow_paths = code_context.get("flow_paths", [])
            for flow in flow_paths:
                if "from" in flow and "to" in flow:
                    traced_flow = self.code_reader.trace_data_flow(flow["from"], flow["to"])
                    if traced_flow:
                        flow_text = "Data Flow:\n"
                        for step in traced_flow:
                            flow_text += f"  {step['step']}: {step['concept']} - {step['description']}\n"
                            flow_text += f"    Files: {', '.join(step.get('files', []))}\n"
                        context["related_code"].append(flow_text)
        
        # For debugging questions, check database operations
        if question_type == "debugging":
            for concept in concepts:
                if "line items" in concept.lower() or "invoice" in concept.lower():
                    db_analysis = self.code_reader.analyze_database_flow("invoice_line_items", "select")
                    if db_analysis.get("operations"):
                        context["db_operations"].append(f"Database operations for invoice_line_items:\n")
                        for op in db_analysis["operations"]:  # No limit (local processing)
                            context["db_operations"].append(f"  {op['file']}:{op['line']} - {op['code']}")
        
        # Find API routes related to concepts
        for concept in concepts:
            if "api" in concept.lower() or "endpoint" in concept.lower():
                # Search for API routes
                api_results = self.code_reader.search_codebase("api", file_pattern="*.py", max_results=50)  # Increased for local
                if api_results:
                    context["api_routes"].extend([f"{r['file_path']}:{r['line']}" for r in api_results])
        
        return context
    
    def _get_document_context(self, context: Optional[Dict[str, Any]]) -> Optional[str]:
        """Get context about documents/invoices from database."""
        try:
            import sqlite3
            import os
            
            db_path = "data/owlin.db"
            if not os.path.exists(db_path):
                return None
            
            con = sqlite3.connect(db_path, check_same_thread=False)
            cur = con.cursor()
            
            # Get recent documents with low confidence or errors
            cur.execute("""
                SELECT d.id, d.filename, d.status, d.ocr_error, d.ocr_confidence,
                       i.supplier, i.date, i.value, i.confidence
                FROM documents d
                LEFT JOIN invoices i ON i.doc_id = d.id
                WHERE d.status = 'error' OR d.ocr_confidence < 0.5 OR i.confidence < 0.5
                ORDER BY d.uploaded_at DESC
                LIMIT 5
            """)
            
            rows = cur.fetchall()
            con.close()
            
            if not rows:
                return None
            
            context_lines = ["Recent documents with issues:"]
            for row in rows:
                doc_id, filename, status, ocr_error, ocr_conf, supplier, date, value, inv_conf = row
                context_lines.append(f"- {filename} (ID: {doc_id})")
                context_lines.append(f"  Status: {status}, OCR Confidence: {ocr_conf or 0}")
                if ocr_error:
                    context_lines.append(f"  Error: {ocr_error}")
                if supplier:
                    context_lines.append(f"  Supplier: {supplier}, Invoice Confidence: {inv_conf or 0}")
            
            return "\n".join(context_lines)
        except Exception as e:
            logger.warning(f"Failed to get document context: {e}")
            return None
    
    def _select_model_for_request(
        self,
        question_type: str,
        context_size: int,
        code_files_count: int
    ) -> Tuple[Optional[str], int]:
        """
        Select best model for this request using the model registry.
        
        Args:
            question_type: Type of question ("debugging", "code_flow", "general")
            context_size: Requested context size
            code_files_count: Number of code files to include
            
        Returns:
            Tuple of (selected_model_name, effective_context_size)
        """
        selected_model, effective_context = self.model_registry.select_best_model(
            question_type=question_type,
            context_size=context_size,
            code_files_count=code_files_count,
            preferred_models=self.models
        )
        
        # Fallback to primary model if selection fails
        if not selected_model:
            logger.warning("Model selection failed, using primary model")
            selected_model = self.model
            # Use full requested context size (local processing)
            effective_context = context_size
        
        return selected_model, effective_context
    
    def _call_ollama_with_fallback(
        self,
        prompt: str,
        conversation_history: Optional[List[Dict[str, str]]],
        context_size: int,
        question_analysis: Optional[Dict[str, Any]],
        code_context: Dict[str, Any]
    ) -> str:
        """
        Call Ollama with cascading model fallback chain.
        
        Tries models in priority order:
        1. Primary model (best for request)
        2. Secondary models (if primary fails)
        3. Enhanced fallback (if all models fail)
        """
        # Try each available model in order
        for attempt, model_name in enumerate(self.available_models):
            try:
                logger.info(f"Attempt {attempt + 1}/{len(self.available_models)}: trying model {model_name}")
                
                # Temporarily set the model
                original_model = self.model
                self.model = model_name
                
                # Call Ollama
                response_text = self._call_ollama(
                    prompt,
                    conversation_history,
                    context_size,
                    question_analysis,
                    code_context
                )
                
                # Restore original model
                self.model = original_model
                
                # Validate response - if generic, try next model
                # Relax validation in agent mode (agent responses are more exploratory)
                if self._is_generic_response(response_text, agent_mode=getattr(self, '_in_agent_mode', False)):
                    logger.warning(f"Model {model_name} returned generic response, trying next model")
                    continue
                
                logger.info(f"Model {model_name} returned valid response")
                return response_text
                
            except Exception as e:
                logger.warning(f"Model {model_name} failed: {e}")
                # Restore original model
                self.model = original_model
                
                # If this was the last model, raise the exception
                if attempt == len(self.available_models) - 1:
                    logger.error("All models failed, falling back to code-based response")
                    return self._generate_code_based_fallback(code_context, question_analysis)
                
                # Otherwise, try next model
                continue
        
        # If no models available, use enhanced fallback
        logger.warning(f"No models available (checked {len(self.available_models)} models), using code-based fallback")
        logger.info(f"Ollama available: {self.ollama_available}, Available models: {self.available_models}, Primary model: {self.model}")
        return self._generate_code_based_fallback(code_context, question_analysis)
    
    def _call_ollama(self, prompt: str, conversation_history: Optional[List[Dict[str, str]]], context_size: int = 100000, question_analysis: Optional[Dict[str, Any]] = None, code_context: Optional[Dict[str, Any]] = None) -> str:
        """Call Ollama API for chat response with intelligent model selection."""
        
        # Select best model for this request
        question_type = question_analysis.get("type", "general") if question_analysis else "general"
        code_files_count = len(code_context.get("files", [])) if code_context else 0
        
        selected_model, effective_context = self._select_model_for_request(
            question_type,
            context_size,
            code_files_count
        )
        
        logger.info(
            f"Selected model: {selected_model} with {effective_context}k context "
            f"for {question_type} question with {code_files_count} files"
        )
        
        # Build messages array
        messages = []
        
        # Add system message
        messages.append({
            "role": "system",
            "content": """You are a debugging assistant for Owlin, an offline invoice processing platform.

SYSTEM: Upload → OCR → Parse → Normalize → Match → Detect Issues → Forecast → Dashboard
Analyze code systematically, trace data flow, find bugs, and provide specific fixes."""
        })
        
        # Add conversation history
        if conversation_history:
            messages.extend(conversation_history)  # Use all history (local processing)
        
        # Add current prompt
        messages.append({
            "role": "user",
            "content": prompt
        })
        
        # Determine temperature based on question type (lower for debugging = less hallucination)
        is_debugging = False
        if question_analysis and question_analysis.get("type") == "debugging":
            is_debugging = True
        elif conversation_history:
            # Check last few messages for debugging keywords
            recent_messages = ' '.join([msg.get('content', '') for msg in conversation_history[-3:]])
            debugging_keywords = ['debug', 'issue', 'problem', 'broken', 'not working', 'not showing', 'error', 'fix']
            is_debugging = any(keyword in recent_messages.lower() for keyword in debugging_keywords)
        
        # Use even lower temperature for debugging questions (0.3) for maximum determinism
        temperature = 0.3 if is_debugging else 0.5
        
        # Calculate timeout based on context size (2.5s per 1k tokens, minimum 60s, maximum 300s)
        timeout = min(300, max(60, int(effective_context / 1000) * 2.5))
        
        response = requests.post(
            f"{self.ollama_url}/api/chat",
            json={
                "model": selected_model,  # Use selected model
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": -1,  # -1 = unlimited output (local processing)
                    "num_ctx": effective_context,  # Use effective context from model selection
                    "top_p": 0.9,
                    "repeat_penalty": 1.1,
                    "top_k": 40
                }
            },
            timeout=timeout
        )
        
        if response.status_code != 200:
            raise Exception(f"Ollama API returned status {response.status_code}")
        
        result = response.json()
        response_text = result.get("message", {}).get("content", "I'm sorry, I couldn't generate a response.")
        
        # Validate response format for debugging questions
        if is_debugging and code_context:
            logger.info(f"Debugging question detected. Code context has {len(code_context.get('files', []))} files")
            logger.debug(f"Response preview: {response_text[:200]}...")
            # Pre-check: Reject generic responses entirely
            # Relax validation in agent mode (agent responses are more exploratory)
            if self._is_generic_response(response_text, agent_mode=getattr(self, '_in_agent_mode', False)):
                logger.warning("LLM returned generic response for debugging question - forcing code analysis!")
                # Force a more explicit prompt with stronger instructions
                response_text = self._force_code_analysis(prompt, conversation_history, context_size, code_context, question_analysis)
            else:
                response_text = self._validate_and_enforce_debugging_format(response_text, code_context)
        elif is_debugging and not code_context:
            logger.warning("Debugging question detected but no code context provided!")
        
        return response_text
    
    def _fallback_response(self, message: str, code_context: Dict[str, Any], question_analysis: Optional[Dict[str, Any]] = None) -> str:
        """Generate a fallback response when Ollama is unavailable, actually reading files when requested."""
        
        # Use enhanced response generation for complex questions
        if question_analysis and question_analysis.get("complexity") == "complex":
            return self._generate_enhanced_response(
                question_analysis.get("type", "general"),
                code_context,
                question_analysis
            )
        
        message_lower = message.lower()
        response_parts = []
        
        # If files were requested, read and display them
        if code_context.get("files"):
            for file_path in code_context["files"]:  # No limit (local processing)
                file_data = self.code_reader.read_file(file_path, max_lines=5000)  # Increased for local processing
                if file_data.get("success"):
                    truncation_note = ""
                    if file_data.get("truncated"):
                        truncation_note = f"\n(Showing first {file_data['lines_read']} of {file_data['total_lines']} lines)"
                    
                    response_parts.append(f"""Here's the code from `{file_path}`{truncation_note}:

```python
{file_data['content']}
```""")
                else:
                    response_parts.append(f"Could not read file `{file_path}`: {file_data.get('error', 'Unknown error')}")
        
        # If search queries were made, show results
        if code_context.get("search_queries"):
            for query in code_context["search_queries"]:  # No limit (local processing)
                # Try multiple file patterns
                results = self.code_reader.search_codebase(query, file_pattern="*.py,*.tsx,*.ts,*.jsx,*.js", max_results=50)  # Increased
                if results:
                    response_parts.append(f"Search results for '{query}':\n")
                    for result in results:
                        response_parts.append(f"**{result['file_path']}:{result['line']}**\n```\n{result['context']}\n```\n")
                else:
                    # If no results, try to find files by name
                    found_files = self.code_reader.find_files_by_name(query.split()[-1] if query.split() else query, max_results=20)  # Increased
                    if found_files:
                        response_parts.append(f"Found files matching '{query}':\n")
                        for file_path in found_files:
                            file_data = self.code_reader.read_file(file_path, max_lines=5000)  # Increased for local
                            if file_data.get("success"):
                                response_parts.append(f"**{file_path}**\n```\n{file_data['content'][:500]}...\n```\n")
                    else:
                        response_parts.append(f"No results found for '{query}'. Try being more specific or asking to read a specific file.")
        
        # If error-related, include error logs and code from error locations
        if "error" in message_lower or "fail" in message_lower or "wrong" in message_lower:
            log_data = self.code_reader.read_error_logs(max_lines=30)
            if log_data.get("success") and log_data.get("error_count", 0) > 0:
                log_content = log_data['content']
                # Show last 2000 chars if log is very long
                if len(log_content) > 2000:
                    log_content = "... (earlier logs) ...\n" + log_content[-2000:]
                response_parts.append(f"""Recent error logs ({log_data['error_count']} errors found):

```
{log_content}
```""")
                
                # Show code from files referenced in errors
                if log_data.get("file_references"):
                    response_parts.append("**Code from error locations:**\n")
                    for ref in log_data["file_references"]:  # No limit (local processing)
                        file_data = self.code_reader.read_file_with_context(
                            ref["file"],
                            ref["line"],
                            context_lines=10
                        )
                        if file_data.get("success"):
                            response_parts.append(
                                f"**{ref['file']}:{ref['line']}** (referenced in error)\n"
                                f"```\n{file_data['content']}\n```\n"
                            )
        
        # If we have file/search results, return them
        if response_parts:
            # Only show a subtle note at the end, not prominently
            if not self.ollama_available:
                response_parts.append("\n---\n*Tip: Install Ollama for AI-powered explanations (optional)*")
            return "\n\n".join(response_parts)
        
        # Otherwise, provide helpful guidance
        if any(word in message_lower for word in ["show", "read", "see", "view"]):
            # Try to extract what they want to read
            if "upload" in message_lower:
                upload_results = self.code_reader.search_codebase("upload", file_pattern="*.py", max_results=50)  # Increased
                if upload_results:
                    response = "I found upload-related code:\n\n"
                    for result in upload_results:
                        response += f"**{result['file_path']}:{result['line']}**\n```\n{result['context']}\n```\n\n"
                    # Don't show the note here - it's redundant
                    return response
            
            return """I can read code files for you. Try asking:
- "Show me backend/main.py"
- "Read the upload code"
- "View frontend_clean/src/pages/Invoices.tsx"

*Tip: Install Ollama for AI-powered explanations (optional)*"""
        
        elif "upload" in message_lower or "file" in message_lower:
            # Try to find upload-related code
            upload_results = self.code_reader.search_codebase("upload", file_pattern="*.py", max_results=50)  # Increased
            if upload_results:
                response = "I found upload-related code:\n\n"
                for result in upload_results:
                    response += f"**{result['file_path']}:{result['line']}**\n```\n{result['context']}\n```\n\n"
                # Don't show redundant note
                return response
            return """I can help you with file uploads. The upload endpoint is in `backend/main.py` at the `/api/upload` route.

To see the code, you can ask me: "Show me backend/main.py" or "Read backend/main.py"

*Tip: Install Ollama for AI-powered explanations (optional)*"""
        
        else:
            return """I'm here to help with your code! I can:
- Read and explain code files
- Search for code patterns
- Help debug errors
- Answer questions about the codebase

Try asking:
- "Show me backend/main.py"
- "Find the upload function"
- "Why did my upload fail?"

*Tip: Install Ollama for AI-powered explanations (optional)*"""
    
    def _generate_enhanced_response(self, question_type: str, code_context: Dict[str, Any], question_analysis: Dict[str, Any]) -> str:
        """
        Generate high-quality response based on question type and context.
        
        Returns:
            Structured, detailed response
        """
        response_parts = []
        concepts = question_analysis.get("concepts", [])
        flow_paths = code_context.get("flow_paths", [])
        
        if question_type == "debugging":
            # Structured debugging response
            response_parts.append("## Problem Analysis\n")
            
            # Identify the issue
            problem_desc = question_analysis.get("original_message", "")
            response_parts.append(f"**Issue**: {problem_desc}\n")
            
            # Trace the flow
            if flow_paths:
                response_parts.append("## Data Flow Analysis\n")
                for flow in flow_paths:
                    if "from" in flow and "to" in flow:
                        traced = self.code_reader.trace_data_flow(flow["from"], flow["to"])
                        if traced:
                            # Generate flow diagram
                            diagram = self.code_reader.generate_flow_diagram(traced)
                            response_parts.append(f"**Flow from {flow['from']} to {flow['to']}:**\n")
                            response_parts.append(f"```\n{diagram}\n```\n")
                            
                            # Detailed steps
                            response_parts.append("**Detailed Steps:**\n")
                            for step in traced:
                                response_parts.append(f"1. **{step['concept']}** - {step['description']}")
                                if step.get('files'):
                                    response_parts.append(f"   - Files: {', '.join(step['files'])}")  # No limit
                            response_parts.append("")
            
            # Show relevant code - collect from all sources
            response_parts.append("## Relevant Code\n")
            
            # Collect files from multiple sources
            all_files = []
            
            # From implicit_files
            all_files.extend(code_context.get("implicit_files", []))
            
            # From regular files
            all_files.extend(code_context.get("files", []))
            
            # Extract from flow_paths
            for flow in flow_paths:
                if "from" in flow and "to" in flow:
                    traced = self.code_reader.trace_data_flow(flow["from"], flow["to"])
                    for step in traced:
                        step_files = step.get("files", [])
                        if isinstance(step_files, list):
                            all_files.extend(step_files)
                        elif step_files:
                            all_files.append(step_files)
            
            # Remove duplicates and filter out virtual environment files
            seen = set()
            filtered_files = []
            for file_path in all_files:
                if not file_path:
                    continue
                # Normalize path
                if isinstance(file_path, str):
                    file_path_str = file_path.replace("\\", "/")
                else:
                    file_path_str = str(file_path)
                
                # Skip if already seen or in virtual environment
                if file_path_str in seen:
                    continue
                if self.code_reader._should_skip_file(file_path_str):
                    continue
                
                seen.add(file_path_str)
                filtered_files.append(file_path_str)
            
            # Prioritize files: frontend components and API endpoints first
            # Sort by relevance: frontend components > API routes > services > others
            def file_priority(file_path):
                path_lower = file_path.lower()
                message_lower = question_analysis.get("original_message", "").lower()
                
                # Highest priority: frontend components that display invoices/cards
                if any(keyword in path_lower for keyword in ["invoicecard", "invoicedetail", "invoices.tsx", "invoicepanel"]):
                    return 0
                # High priority: upload.ts if question is about contents not showing
                elif ("content" in message_lower or "show" in message_lower) and "upload.ts" in path_lower:
                    return 1
                # High priority: upload/status endpoint in main.py if question is about contents
                elif ("content" in message_lower or "show" in message_lower) and "main.py" in path_lower:
                    return 1
                # High priority: API routes that return invoices/line_items
                elif ("/api/invoices" in path_lower or "invoices_submit" in path_lower or 
                      ("main.py" in path_lower and "invoices" in path_lower)):
                    return 2
                # Medium priority: database functions for line items
                elif ("get_line_items" in path_lower or "db.py" in path_lower):
                    return 3
                # Medium priority: OCR service that extracts line items
                elif "ocr_service" in path_lower:
                    return 4
                # Lower priority: other API routes
                elif "/api" in path_lower or "routes" in path_lower:
                    return 5
                # Lower priority: services
                elif "services" in path_lower:
                    return 6
                # Lowest priority: other frontend files
                elif "frontend" in path_lower:
                    return 7
                else:
                    return 8
            
            filtered_files.sort(key=file_priority)
            
            # Process all relevant files (local processing - no limit)
            # filtered_files = filtered_files[:5]  # Removed limit
            
            # Actually read and display code
            if filtered_files:
                for file_path in filtered_files:
                    file_data = self.code_reader.read_file(file_path, max_lines=5000)  # Increased for local
                    if file_data.get("success"):
                        truncation_note = ""
                        if file_data.get("truncated"):
                            truncation_note = f" *(showing first {file_data['lines_read']} of {file_data['total_lines']} lines)*"
                        response_parts.append(f"### {file_path}{truncation_note}\n```\n{file_data['content']}\n```\n")
                    else:
                        response_parts.append(f"### {file_path}\n*Could not read file: {file_data.get('error', 'Unknown error')}*\n")
            else:
                response_parts.append("*No relevant code files found. Try asking about specific files or functions.*\n")
            
            # Actionable suggestions - tailored to the specific issue
            response_parts.append("## Suggested Steps to Debug\n")
            
            # Check if this is about line items not showing
            message_lower = question_analysis.get("original_message", "").lower()
            if "line" in message_lower and ("item" in message_lower or "card" in message_lower):
                response_parts.append("**For line items not showing on cards:**\n")
                response_parts.append("1. **Check upload/status endpoint**: Verify `/api/upload/status?doc_id=...` returns `items` or `line_items` in the response")
                response_parts.append("2. **Check database**: Query `invoice_line_items` table to confirm line items are stored after OCR")
                response_parts.append("3. **Check frontend normalization**: In `frontend_clean/src/lib/upload.ts`, the `normalizeUploadResponse` function looks for `raw.line_items` or `raw.items` - verify the upload response includes these")
                response_parts.append("4. **Check polling**: The frontend polls `/api/upload/status` - verify `statusData.items` is populated when OCR completes")
                response_parts.append("5. **Alternative**: The `/api/invoices` endpoint returns `line_items` (line 347), but the frontend uses upload metadata. Consider fetching from `/api/invoices` after upload completes")
                response_parts.append("6. **Browser console**: Check for errors when polling status or normalizing the response")
            elif "content" in message_lower or ("invoice" in message_lower and ("show" in message_lower or "display" in message_lower or "appear" in message_lower)):
                response_parts.append("**For invoice contents not showing:**\n")
                response_parts.append("1. **Check upload/status endpoint**: After upload, the frontend polls `/api/upload/status?doc_id=...` - verify it returns:")
                response_parts.append("   - `parsed` object with supplier, date, value")
                response_parts.append("   - `items` array with line items")
                response_parts.append("   - `invoice` object with complete invoice data")
                response_parts.append("2. **Check OCR processing**: Verify the document status in database (`documents.status`) - should be 'scanned' or 'completed'")
                response_parts.append("3. **Check invoice creation**: Query `invoices` table to confirm an invoice record exists for the document (`doc_id`)")
                response_parts.append("4. **Check frontend polling**: In `frontend_clean/src/lib/upload.ts`, the `pollUploadStatus` function waits for `statusData.parsed` or `statusData.items` - verify these are present")
                response_parts.append("5. **Check InvoiceDetailPanel**: The component reads `metadata.lineItems` from upload response - verify the normalized response includes `lineItems`")
                response_parts.append("6. **Database check**: Run `SELECT * FROM invoices WHERE doc_id = ?` and `SELECT * FROM invoice_line_items WHERE doc_id = ?` to verify data exists")
                response_parts.append("7. **Browser console**: Check for errors in the upload/polling process or when rendering InvoiceDetailPanel")
            else:
                response_parts.append("1. Check if data is being extracted correctly")
                response_parts.append("2. Verify data is stored in the database")
                response_parts.append("3. Check API endpoints return the data")
                response_parts.append("4. Verify frontend components receive and display the data")
                response_parts.append("5. Check browser console for errors")
            
        elif question_type == "flow":
            # Flow explanation
            response_parts.append("## Data Flow Explanation\n")
            
            if flow_paths:
                for flow in flow_paths:
                    if "from" in flow and "to" in flow:
                        traced = self.code_reader.trace_data_flow(flow["from"], flow["to"])
                        if traced:
                            # Generate flow diagram
                            diagram = self.code_reader.generate_flow_diagram(traced)
                            response_parts.append(f"### Flow: {flow['from']} → {flow['to']}\n")
                            response_parts.append(f"```\n{diagram}\n```\n")
                            
                            # Detailed steps
                            for i, step in enumerate(traced, 1):
                                response_parts.append(f"{i}. **{step['concept']}**")
                                response_parts.append(f"   - {step['description']}")
                                if step.get('files'):
                                    response_parts.append(f"   - Code location: {', '.join(step['files'][:2])}")
                            response_parts.append("")
            
            # Show code at each step
            response_parts.append("## Code at Each Step\n")
            implicit_files = code_context.get("implicit_files", [])
            for file_path in implicit_files:  # No limit (local processing)
                file_data = self.code_reader.read_file(file_path, max_lines=5000)  # Increased for local
                if file_data.get("success"):
                    response_parts.append(f"### {file_path}\n```\n{file_data['content']}\n```\n")
        
        elif question_type == "how-to":
            # How-to guide
            response_parts.append("## How-To Guide\n")
            
            # Find similar code patterns
            for concept in concepts:
                results = self.code_reader.search_codebase(concept, max_results=50)  # Increased
                if results:
                    response_parts.append(f"### Related Code for '{concept}'\n")
                    for result in results:
                        response_parts.append(f"**{result['file_path']}:{result['line']}**\n```\n{result['context']}\n```\n")
        
        elif question_type == "what-is":
            # Definition/explanation
            response_parts.append("## Explanation\n")
            
            # Find definition and usage
            for concept in concepts:
                results = self.code_reader.search_codebase(concept, max_results=50)  # Increased
                if results:
                    response_parts.append(f"### '{concept}' in the codebase\n")
                    for result in results:  # No limit (local processing)
                        response_parts.append(f"**{result['file_path']}:{result['line']}**\n```\n{result['context']}\n```\n")
        
        else:
            # General complex question
            response_parts.append("## Analysis\n")
            response_parts.append(f"**Question**: {question_analysis.get('original_message', '')}\n")
            response_parts.append(f"**Concepts identified**: {', '.join(concepts)}\n")
            
            # Show relevant code
            if code_context.get("files") or code_context.get("implicit_files"):
                response_parts.append("## Relevant Code\n")
                all_files = code_context.get("files", []) + code_context.get("implicit_files", [])
                for file_path in all_files:  # No limit (local processing)
                    file_data = self.code_reader.read_file(file_path, max_lines=5000)  # Increased for local
                    if file_data.get("success"):
                        truncation_note = ""
                        if file_data.get("truncated"):
                            truncation_note = f"\n(Showing first {file_data['lines_read']} of {file_data['total_lines']} lines)"
                        response_parts.append(f"### {file_path}{truncation_note}\n```\n{file_data['content']}\n```\n")
        
        # Only show subtle tip at the end if Ollama is not available
        if not self.ollama_available:
            response_parts.append("\n---\n*Tip: Install Ollama for AI-powered explanations (optional)*")
        
        return "\n".join(response_parts)
    
    def _get_related_files_for_debugging(self, message: str, code_context: Dict[str, Any]) -> List[str]:
        """
        Automatically find and include related files for debugging questions.
        ALWAYS returns 3-10 files to ensure comprehensive code analysis.
        """
        message_lower = message.lower()
        related_files = []
        
        # Core file patterns - comprehensive coverage
        file_patterns = {
            # Upload flow patterns
            "upload": [
                "frontend_clean/src/lib/upload.ts",
                "backend/main.py",
                "backend/services/ocr_service.py",
                "backend/app/db.py"
            ],
            # Display/UI patterns
            "display": [
                "frontend_clean/src/pages/Invoices.tsx",
                "frontend_clean/src/components/InvoiceDetailPanel.tsx",
                "frontend_clean/src/lib/upload.ts",
                "backend/main.py"
            ],
            # Invoice/card patterns
            "invoice": [
                "frontend_clean/src/pages/Invoices.tsx",
                "frontend_clean/src/components/InvoiceDetailPanel.tsx",
                "backend/routes/invoices_submit.py",
                "backend/app/db.py",
                "frontend_clean/src/lib/upload.ts"
            ],
            # OCR/extraction patterns
            "ocr": [
                "backend/services/ocr_service.py",
                "backend/services/engine_select.py",
                "backend/main.py",
                "backend/app/db.py"
            ],
            # Database/storage patterns
            "database": [
                "backend/app/db.py",
                "backend/main.py",
                "backend/services/ocr_service.py"
            ],
            # API/endpoint patterns
            "api": [
                "backend/main.py",
                "backend/routes/invoices_submit.py",
                "frontend_clean/src/lib/api.ts",
                "frontend_clean/src/lib/upload.ts"
            ]
        }
        
        # Expanded keyword matching for each pattern
        pattern_keywords = {
            "upload": ["upload", "file", "status", "poll", "submit"],
            "display": ["display", "show", "shown", "appear", "visible", "render", "card", "content", "contents"],
            "invoice": ["invoice", "supplier", "items", "line items", "line_items", "card", "detail", "panel"],
            "ocr": ["ocr", "scan", "extract", "parse", "text", "recognition"],
            "database": ["database", "db", "table", "query", "sql", "store", "save"],
            "api": ["api", "endpoint", "request", "response", "fetch", "call"]
        }
        
        # Match patterns and collect files
        matched_patterns = set()
        for pattern_name, keywords in pattern_keywords.items():
            if any(keyword in message_lower for keyword in keywords):
                matched_patterns.add(pattern_name)
                related_files.extend(file_patterns[pattern_name])
        
        # Special combined patterns for common debugging scenarios
        # Scenario 1: Upload but not showing (full flow)
        if ("upload" in message_lower or "submit" in message_lower) and \
           any(word in message_lower for word in ["not", "isn't", "doesn't", "missing", "empty"]) and \
           any(word in message_lower for word in ["show", "display", "appear", "content", "items"]):
            logger.info("Detected full flow debugging: upload → processing → display")
            related_files.extend([
                "frontend_clean/src/lib/upload.ts",  # Upload normalization
                "frontend_clean/src/pages/Invoices.tsx",  # Display component
                "backend/main.py",  # API endpoints
                "backend/services/ocr_service.py",  # OCR processing
                "backend/app/db.py",  # Data storage
                "frontend_clean/src/components/InvoiceDetailPanel.tsx"  # Detail view
            ])
        
        # Scenario 2: Supplier name not showing
        if "supplier" in message_lower and any(word in message_lower for word in ["not", "missing", "empty", "unknown"]):
            logger.info("Detected supplier extraction issue")
            related_files.extend([
                "frontend_clean/src/lib/upload.ts",
                "backend/services/ocr_service.py",
                "backend/main.py"
            ])
        
        # Scenario 3: Line items not showing
        if ("line" in message_lower and "item" in message_lower) or "line_item" in message_lower:
            logger.info("Detected line items issue")
            related_files.extend([
                "frontend_clean/src/lib/upload.ts",
                "frontend_clean/src/components/InvoiceDetailPanel.tsx",
                "backend/app/db.py",
                "backend/services/ocr_service.py"
            ])
        
        # Remove duplicates while preserving order
        seen = set()
        unique_files = []
        for file_path in related_files:
            if file_path not in seen:
                seen.add(file_path)
                unique_files.append(file_path)
        
        # Validate files exist and collect valid ones
        valid_files = []
        for file_path in unique_files:
            file_data = self.code_reader.read_file(file_path, max_lines=1)
            if file_data.get("success"):
                valid_files.append(file_path)
        
        # ENSURE MINIMUM 3 FILES for debugging questions
        if len(valid_files) < 3:
            logger.warning(f"Only {len(valid_files)} files found, adding fallback core files")
            # Add core fallback files
            fallback_files = [
                "frontend_clean/src/pages/Invoices.tsx",
                "backend/main.py",
                "frontend_clean/src/lib/upload.ts",
                "backend/services/ocr_service.py",
                "backend/app/db.py"
            ]
            for fallback_file in fallback_files:
                if fallback_file not in valid_files:
                    file_data = self.code_reader.read_file(fallback_file, max_lines=1)
                    if file_data.get("success"):
                        valid_files.append(fallback_file)
                        if len(valid_files) >= 3:
                            break
        
        # No limit for local processing - use all valid files
        # if len(valid_files) > 10:
        #     logger.info(f"Limiting files from {len(valid_files)} to 10 for performance")
        #     valid_files = valid_files[:10]
        
        logger.info(f"Auto-included {len(valid_files)} files for debugging: {', '.join(valid_files)}")
        return valid_files
    
    def _detect_placeholder_code(self, response: str) -> List[str]:
        """
        Detect placeholder code patterns in response.
        Enhanced to detect TODO/FIXME, incomplete bodies, stub implementations.
        Checks both code blocks AND entire response text.
        """
        issues = []
        
        # Use base validator detection (checks code blocks)
        base_issues = self.response_validator._detect_placeholder_code(response)
        issues.extend(base_issues)
        
        # NEW: Check entire response text for placeholder patterns (not just code blocks)
        # This catches placeholder code in regular text like "def save_invoice_data_to_db(invoice_data): # Code to save..."
        placeholder_text_patterns = [
            r'def\s+\w+\([^)]*\):\s*#\s*Code\s+to\s+',  # def func(): # Code to...
            r'def\s+\w+\([^)]*\):\s*#\s*Code\s+to\s+[^\n]+(?:database|file|function|method|class)',  # def func(): # Code to save to database
            r'def\s+\w+\([^)]*\):\s*#\s*Code\s+to\s+[^\n]+(?:extract|save|store|insert|update)',  # def func(): # Code to extract/save/store
        ]
        
        for pattern in placeholder_text_patterns:
            if re.search(pattern, response, re.IGNORECASE | re.MULTILINE):
                issues.append("Response contains placeholder code in text (function with '# Code to...' comment)")
                break  # Only report once
        
        # Check for function definitions followed by only placeholder comments
        func_with_placeholder = re.findall(r'def\s+(\w+)\([^)]*\):\s*#\s*Code\s+to\s+[^\n]+', response, re.IGNORECASE)
        if func_with_placeholder:
            for func_name in func_with_placeholder:
                issues.append(f"Function '{func_name}' is defined with placeholder code ('# Code to...') instead of actual implementation")
        
        # Additional checks for TODO/FIXME in code context
        todo_fixme_pattern = r'(?:TODO|FIXME|XXX|HACK|NOTE|BUG)\s*:?\s*.*?(?:def\s+\w+|class\s+\w+|function\s+\w+)'
        if re.search(todo_fixme_pattern, response, re.IGNORECASE):
            issues.append("Code snippet contains TODO/FIXME markers indicating incomplete implementation")
        
        # Check for stub implementations (functions with only docstrings or comments)
        stub_patterns = [
            r'def\s+\w+\([^)]*\):\s*(?:"""[^"]*"""|#\s*[^\n]*)\s*$',  # def func(): """doc""" or def func(): # comment
            r'def\s+\w+\([^)]*\):\s*(?:pass|\.\.\.)\s*$',  # def func(): pass or def func(): ...
        ]
        for pattern in stub_patterns:
            if re.search(pattern, response, re.MULTILINE):
                issues.append("Code snippet contains stub implementation (only docstring/comments/pass)")
        
        # Check for generic code patterns
        generic_patterns = [
            r'def\s+\w+\([^)]*\):\s*#\s*(?:implement|add|todo|fixme)',
            r'class\s+\w+:\s*pass\s*$',
            r'return\s+None\s*#\s*(?:placeholder|stub|todo)',
        ]
        for pattern in generic_patterns:
            if re.search(pattern, response, re.IGNORECASE | re.MULTILINE):
                issues.append("Code snippet contains generic placeholder patterns")
        
        return issues
    
    def _verify_function_names(self, response: str, files_read_tracker: set) -> List[str]:
        """Verify that function names mentioned in response actually exist."""
        issues = []
        
        # Extract function names from response (patterns like "function_name()" or "def function_name")
        function_patterns = [
            r'\b(\w+)\s*\(',  # function_name(
            r'def\s+(\w+)',  # def function_name
            r'\.(\w+)\s*\(',  # .function_name(
            r'(?:function|method|def)\s+(\w+)',  # function function_name or method function_name
            r'the\s+function\s+(\w+)',  # the function function_name
            r'function\s+(\w+)\s+(?:calls|is|was|does)',  # function function_name calls/is/was/does
            r'method\s+(\w+)\s+(?:calls|is|was|does)',  # method function_name calls/is/was/does
            r'(\w+)\s+(?:function|method)\s+(?:calls|is|was|does)',  # function_name function/method calls/is/was/does
            r'-\s+(\w+)\s+in\s+',  # - function_name in file.py (list format)
            r'(\w+)\s+in\s+[\w/\\-]+\.(?:py|js|jsx|ts|tsx)',  # function_name in backend/file.py
            r'-\s+(\w+)(?:\s|$)',  # - function_name (list item, end of line or space)
        ]
        
        mentioned_functions = set()
        for pattern in function_patterns:
            matches = re.findall(pattern, response, re.IGNORECASE)
            mentioned_functions.update(matches)
        
        # Filter out common Python built-ins and common words
        common_words = {
            'print', 'len', 'str', 'int', 'float', 'list', 'dict', 'set', 'tuple',
            'range', 'enumerate', 'zip', 'map', 'filter', 'sorted', 'reversed',
            'get', 'set', 'has', 'is', 'in', 'and', 'or', 'not', 'if', 'else',
            'for', 'while', 'def', 'class', 'import', 'from', 'return', 'pass',
            'break', 'continue', 'try', 'except', 'finally', 'raise', 'with',
            'async', 'await', 'yield', 'lambda', 'self', 'None', 'True', 'False',
            'function', 'method', 'the', 'calls', 'is', 'was', 'does', 'to', 'be',
        }
        
        # For each mentioned function, check if it exists in codebase
        for func_name in mentioned_functions:
            if func_name.lower() in common_words or len(func_name) < 3:
                continue  # Skip common words and very short names
            
            # IMPROVED: More strict check - verify function actually exists with signature
            exists, func_info = self._function_exists_in_codebase(func_name, files_read_tracker)
            
            if not exists:
                # Check if it's mentioned in a "Functions Found" section (should only list existing functions)
                if re.search(r'Functions?\s+Found[:\s]*.*?' + re.escape(func_name), response, re.IGNORECASE):
                    issues.append(f"Function '{func_name}' listed in 'Functions Found' but does not exist in codebase")
                # Check if it's mentioned in code snippets (should only show existing functions)
                elif re.search(r'def\s+' + re.escape(func_name) + r'\(', response, re.IGNORECASE):
                    issues.append(f"Function '{func_name}' shown in code snippet but does not exist in codebase")
                else:
                    issues.append(f"Function '{func_name}' mentioned but not found in codebase")
        
        # Also check for "missing" claims - verify if functions claimed as missing actually exist
        missing_patterns = [
            r'missing\s+(?:method|function)\s*:?\s*(\w+)',
            r'missing\s+(\w+)\s+(?:method|function)',
            r'(\w+)\s+is\s+missing',
            r'(\w+)\s+is\s+not\s+defined',
            r'(\w+)\s+is\s+not\s+found',
        ]
        
        for pattern in missing_patterns:
            matches = re.findall(pattern, response, re.IGNORECASE)
            for func_name in matches:
                if func_name.lower() in common_words or len(func_name) < 3:
                    continue
                # If function is claimed as missing but actually exists, that's an issue
                exists, func_info = self._function_exists_in_codebase(func_name, files_read_tracker)
                if exists:
                    file_info = f" in {func_info['file']}:{func_info['line']}" if func_info else ""
                    issues.append(f"Function '{func_name}' is claimed as missing but actually exists{file_info}")
        
        return issues
    
    def _function_exists_in_codebase(self, func_name: str, files_read_tracker: set) -> Tuple[bool, Optional[Dict]]:
        """
        Check if function exists in codebase using grep.
        More strict: only matches actual function definitions, not assignments or calls.
        Returns function signature and file location if found.
        
        Returns:
            Tuple of (exists: bool, function_info: Optional[Dict]) where function_info contains:
            - file: file path
            - line: line number
            - signature: function signature
            - is_private: whether function is private (starts with _)
            - is_async: whether function is async
        """
        try:
            # Use code_explorer to search for function definition
            # Search for "def func_name(" to match actual function definitions
            # Also check for "async def func_name(" for async functions
            # And check for class methods: "def func_name(self" or "def func_name(cls"
            pattern = f"def {func_name}\\s*\\(|async\\s+def {func_name}\\s*\\("
            results = self.code_explorer.grep_pattern(pattern)
            
            # Filter results to ensure they're actual function definitions, not just mentions
            valid_results = []
            for file_path, line_numbers in results.items():
                for line_num in line_numbers[:5]:  # Check first 5 matches per file
                    try:
                        # Read the file to get the actual function signature
                        file_data = self.code_reader.read_file(file_path, max_lines=line_num + 5)
                        if file_data.get("success"):
                            lines = file_data.get("content", "").split('\n')
                            if line_num <= len(lines):
                                line = lines[line_num - 1].strip()
                                
                                # Check if it's a function definition (starts with def or async def)
                                if line.startswith(("def ", "async def ")) and func_name in line:
                                    # Extract function signature
                                    signature = line
                                    # Check if it's private (starts with _)
                                    is_private = func_name.startswith('_')
                                    # Check if it's async
                                    is_async = line.startswith("async def ")
                                    
                                    valid_results.append({
                                        "file": file_path,
                                        "line": line_num,
                                        "signature": signature,
                                        "is_private": is_private,
                                        "is_async": is_async
                                    })
                    except Exception as e:
                        logger.debug(f"Error reading file {file_path} at line {line_num}: {e}")
                        continue
            
            if valid_results:
                # Return the first valid result (prefer files in files_read_tracker)
                for result in valid_results:
                    if result["file"] in files_read_tracker:
                        return True, result
                return True, valid_results[0]
            
            return False, None
        except Exception as e:
            logger.warning(f"Error checking function existence for '{func_name}': {e}")
            return False, None  # Conservative: assume doesn't exist if check fails
    
    def _verify_file_paths(self, response: str) -> List[str]:
        """Verify that file paths mentioned in response actually exist."""
        issues = []
        
        # Extract file paths from multiple patterns:
        # 1. Code blocks: "backend/path/to/file.py:123"
        # 2. Text mentions: "file backend/path/to/file.py" or "in backend/path/to/file.py"
        # 3. Lists: "- backend/path/to/file.py"
        file_path_patterns = [
            r'([a-zA-Z0-9_/\\-]+\.(?:py|js|jsx|ts|tsx|json))(?::\d+)?',  # Standard path with optional line number
            r'(?:file|in|from|at)\s+([a-zA-Z0-9_/\\-]+\.(?:py|js|jsx|ts|tsx|json))',  # Text mentions
            r'-\s+([a-zA-Z0-9_/\\-]+\.(?:py|js|jsx|ts|tsx|json))',  # List items
            r'`([a-zA-Z0-9_/\\-]+\.(?:py|js|jsx|ts|tsx|json))`',  # Backtick-wrapped paths
        ]
        
        all_paths = set()
        for pattern in file_path_patterns:
            matches = re.findall(pattern, response, re.IGNORECASE)
            for match in matches:
                # Handle tuple results (pattern with groups)
                if isinstance(match, tuple):
                    file_path = match[0]
                else:
                    file_path = match
                # Remove line numbers if present
                file_path = file_path.split(':')[0]
                if file_path and len(file_path) > 3:  # Filter out very short matches
                    all_paths.add(file_path)
        
        checked_paths = set()  # Avoid checking same path multiple times
        
        for file_path in all_paths:
            if file_path in checked_paths:
                continue
            checked_paths.add(file_path)
            
            # Use fuzzy matching to resolve path
            resolved_path, confidence = self._resolve_file_path(file_path)
            
            # Check if file exists
            if confidence < 0.7 or not Path(resolved_path).exists():
                # Also check common prefixes
                possible_paths = [
                    file_path,
                    f"backend/{file_path}",
                    f"frontend/{file_path}",
                    f"frontend_clean/{file_path}",
                ]
                # Also try without leading directory if it starts with backend/frontend
                if file_path.startswith('backend/'):
                    possible_paths.append(file_path[8:])  # Remove 'backend/'
                elif file_path.startswith('frontend/'):
                    possible_paths.append(file_path[9:])  # Remove 'frontend/'
                
                exists = any(Path(p).exists() for p in possible_paths)
                if not exists:
                    # Check if it's mentioned in "Files Read" section (should only list existing files)
                    if re.search(r'Files?\s+(?:Read|Analyzed)[:\s]*.*?' + re.escape(file_path), response, re.IGNORECASE):
                        issues.append(f"File path '{file_path}' listed in 'Files Read' but does not exist")
                    else:
                        issues.append(f"File path '{file_path}' mentioned but does not exist")
        
        return issues
    
    def _is_generic_response(self, response_text: str, agent_mode: bool = False) -> bool:
        """
        Strict validation - check if response is generic troubleshooting without code analysis.
        Returns True if response should be rejected.
        
        Args:
            response_text: Response text to validate
            agent_mode: If True, use relaxed validation (agent responses are more exploratory)
        
        Rejection criteria:
        - Generic phrase count > 3 (or > 5 in agent mode)
        - Code references < 2 file names (or < 1 in agent mode)
        - No line numbers or function names for debugging questions (relaxed in agent mode)
        - Numbered generic troubleshooting lists
        """
        response_lower = response_text.lower()
        
        # Enhanced generic phrase patterns
        generic_patterns = [
            # Generic troubleshooting starters
            r'\d+\.\s+\*\*(?:issue|problem)\s+\d+:',  # "1. **Issue 1:"
            r'\d+\.\s+(?:incorrect|check|verify|ensure|try|adjust|make\s+sure)',
            r'issue\s+\d+:\s+(?:incorrect|poor|insufficient)',
            
            # Vague cause statements
            r'(?:could|might|may)\s+be\s+(?:caused|due\s+to|related\s+to)',
            r'(?:possible|potential)\s+(?:reasons|causes|issues)',
            r'there\s+(?:are|is|could\s+be)\s+(?:\d+|several|many|some)\s+(?:possible|potential)\s+(?:reasons|causes)',
            r'here\s+are\s+(?:some|a few|several|many)\s+(?:possible|potential)',
            
            # Generic troubleshooting advice
            r'(?:check|verify|ensure|confirm)\s+(?:that|if|whether)',
            r'you\s+(?:should|must|can|may)\s+(?:check|verify|ensure)',
            r'to\s+troubleshoot\s+(?:this|these)\s+(?:issue|problem)',
            r'try\s+(?:the\s+following|these)\s+steps',
            
            # Vague references
            r'based\s+on\s+(?:your|the)\s+(?:description|information|error)',
            r'it\s+seems\s+(?:like|that)',
            r'this\s+(?:could|might|may)\s+be',
            
            # Insufficient/incorrect patterns
            r'insufficient\s+(?:resources|memory|data)',
            r'incorrect\s+(?:configuration|format|file|data)',
            r'improper\s+(?:setup|configuration)',
            
            # Generic advice closings
            r'i\s+hope\s+this\s+helps',
            r'let\s+me\s+know\s+if',
            r'feel\s+free\s+to',
        ]
        
        # Count generic phrases
        generic_count = 0
        import re
        for pattern in generic_patterns:
            matches = re.findall(pattern, response_lower)
            generic_count += len(matches)
            if matches:
                logger.debug(f"Found {len(matches)} generic phrase(s): {pattern}")
        
        # Rejection threshold: > 3 generic phrases (relaxed to > 5 in agent mode)
        threshold = 5 if agent_mode else 3
        if generic_count > threshold:
            logger.warning(f"Generic response rejected: {generic_count} generic phrases detected (threshold: {threshold})")
            return True
        
        # Check for code references
        # Pattern 1: File names with extensions
        file_pattern = r'\b[\w/\\-]+\.(?:py|ts|tsx|js|jsx|json|yaml)\b'
        file_matches = re.findall(file_pattern, response_text)
        unique_files = set(file_matches)
        
        # Pattern 2: Line numbers (file.py:123 or line 123)
        line_pattern = r'(?:\w+\.(?:py|ts|tsx|js|jsx):\d+|line\s+\d+)'
        line_matches = re.findall(line_pattern, response_lower)
        
        # Pattern 3: Function/method names (def function_name, function functionName)
        function_pattern = r'(?:def|function|const|class)\s+\w+'
        function_matches = re.findall(function_pattern, response_text)
        
        # Pattern 4: Code snippets (triple backticks)
        code_snippet_pattern = r'```[\s\S]*?```'
        code_snippets = re.findall(code_snippet_pattern, response_text)
        
        logger.debug(
            f"Code reference analysis (agent_mode={agent_mode}): "
            f"files={len(unique_files)}, lines={len(line_matches)}, "
            f"functions={len(function_matches)}, snippets={len(code_snippets)}"
        )
        
        # Requirements for code references (relaxed in agent mode)
        min_files = 1 if agent_mode else 2
        if len(unique_files) < min_files:
            logger.warning(f"Generic response rejected: only {len(unique_files)} file(s) referenced (need {min_files}+)")
            return True
        
        # In agent mode, allow responses without line numbers if they have file references
        if not agent_mode and len(line_matches) == 0 and len(function_matches) == 0:
            logger.warning("Generic response rejected: no line numbers or function names referenced")
            return True
        
        # If lots of generic phrases and few code references, reject (relaxed in agent mode)
        min_files_for_generic = 2 if agent_mode else 3
        if generic_count > 1 and len(unique_files) < min_files_for_generic:
            logger.warning(f"Generic response rejected: {generic_count} generic phrases with only {len(unique_files)} files (need {min_files_for_generic}+)")
            return True
        
        logger.debug("Response validation passed: appears code-specific")
        return False
    
    def _force_code_analysis(self, prompt: str, conversation_history: Optional[List[Dict[str, str]]], context_size: int, code_context: Dict[str, Any], question_analysis: Optional[Dict[str, Any]]) -> str:
        """
        Force the LLM to analyze code by sending a MUCH stricter prompt.
        This is called when the LLM returns a generic response.
        Uses maximum pressure to get code-specific analysis.
        """
        logger.warning("FORCING code analysis with maximum strictness - previous response was generic")
        
        # Get file list and read actual code
        files_provided = code_context.get("files", [])
        file_specs = code_context.get("file_specs", [])
        file_specs_dict = {spec["path"]: spec for spec in file_specs if isinstance(spec, dict)}
        
        # Read actual code from files
        code_snippets = []
        for file_path in files_provided:  # No limit (local processing)
            # Use max_lines from file_specs if available, otherwise use config default
            max_lines = 5000  # Increased default for local processing
            if file_path in file_specs_dict:
                max_lines = file_specs_dict[file_path].get("max_lines", 5000)  # Removed 500 cap
            
            file_data = self.code_reader.read_file(file_path, max_lines=max_lines)
            if file_data.get("success"):
                content = file_data['content']
                lines = content.split('\n')
                # Remove trailing empty line if file ends with newline
                if lines and lines[-1] == '' and content.endswith('\n'):
                    lines = lines[:-1]
                
                # Add line numbers
                numbered_lines = []
                for i, line in enumerate(lines, 1):
                    line = line.rstrip('\r')
                    numbered_lines.append(f"{i:4}: {line}")
                
                numbered_content = '\n'.join(numbered_lines)
                lines_read = file_data.get('lines_read', len(lines))
                total_lines = file_data.get('total_lines', len(lines))
                
                truncation_note = ""
                if file_data.get("truncated"):
                    truncation_note = f" (showing lines 1-{lines_read} of {total_lines})"
                else:
                    truncation_note = f" (lines 1-{lines_read})"
                
                code_snippets.append(f"File: {file_path}{truncation_note}\n```\n{numbered_content}\n```")
        
        files_list = "\n".join([f"- {f}" for f in files_provided])
        code_block = "\n\n".join(code_snippets) if code_snippets else "No code files could be read."
        
        # Build extremely forceful prompt with actual code
        force_prompt = "="*80 + "\n"
        force_prompt += "PREVIOUS RESPONSE WAS TOO GENERIC. TRY AGAIN.\n"
        force_prompt += "="*80 + "\n\n"
        force_prompt += "CODE FILES PROVIDED FOR ANALYSIS:\n"
        force_prompt += files_list + "\n\n"
        force_prompt += "="*80 + "\n"
        force_prompt += "ACTUAL CODE FROM FILES (YOU MUST ANALYZE THIS):\n"
        force_prompt += "="*80 + "\n\n"
        force_prompt += code_block + "\n\n"
        force_prompt += "="*80 + "\n"
        force_prompt += "MANDATORY REQUIREMENTS:\n"
        force_prompt += "1. EXPLAIN PROBLEMS IN TEXT - don't just dump code\n"
        force_prompt += "2. Use SMALL code snippets (3-5 lines max) to illustrate points\n"
        force_prompt += "3. Always include file:line references with each snippet\n"
        force_prompt += "4. Cite at least 3 specific files from the code provided above\n"
        force_prompt += "5. Reference at least 5 line numbers (use file.py:123 format)\n"
        force_prompt += "6. Quote actual code snippets (small, 3-5 lines) from the files above\n"
        force_prompt += "7. Trace data flow through multiple files (explain in text with file:line refs)\n"
        force_prompt += "8. Identify exact breaking point in code (explain in text)\n"
        force_prompt += "9. Provide specific code changes (BEFORE/AFTER) - small snippets only\n"
        force_prompt += "10. DO NOT dump entire files or large code blocks\n"
        force_prompt += "="*80 + "\n\n"
        force_prompt += "ORIGINAL QUESTION:\n"
        force_prompt += prompt + "\n\n"
        force_prompt += "="*80 + "\n"
        force_prompt += "ANALYZE THE CODE ABOVE. DO NOT GIVE GENERIC TROUBLESHOOTING.\n"
        force_prompt += "="*80 + "\n"
        
        # Call Ollama again with forced prompt
        # Select best model again (possibly try a different one)
        question_type = question_analysis.get("type", "debugging") if question_analysis else "debugging"
        code_files_count = len(code_context.get("files", []))
        selected_model, effective_context = self._select_model_for_request(
            question_type,
            context_size,
            code_files_count
        )
        
        messages = []
        messages.append({
            "role": "system",
            "content": """You are an expert code debugger. You MUST analyze actual code with specific line numbers.

ABSOLUTE REQUIREMENTS:
1. Reference at least 3 files by name
2. Include at least 5 file:line references (e.g., upload.ts:240)
3. Quote actual code snippets
4. Trace data flow through code
5. NEVER give generic troubleshooting

If you give generic advice again, your response will be rejected."""
        })
        
        if conversation_history:
            messages.extend(conversation_history[-10:])
        
        messages.append({
            "role": "user",
            "content": force_prompt
        })
        
        # Use extremely low temperature for forced analysis
        temperature = 0.1  # Minimum hallucination
        
        # Longer timeout for forced analysis
        timeout = min(300, max(90, int(effective_context / 1000) * 3))
        
        try:
            response = requests.post(
                f"{self.ollama_url}/api/chat",
                json={
                    "model": selected_model,
                    "messages": messages,
                    "stream": False,
                    "options": {
                        "temperature": temperature,
                        "num_predict": -1,  # -1 = unlimited output (local processing)
                        "num_ctx": effective_context,
                        "top_p": 0.85,  # Slightly more focused
                        "repeat_penalty": 1.2,  # Discourage repetition
                        "top_k": 30  # More focused
                    }
                },
                timeout=timeout
            )
            
            if response.status_code != 200:
                raise Exception(f"Ollama API returned status {response.status_code}")
            
            result = response.json()
            response_text = result.get("message", {}).get("content", "I'm sorry, I couldn't generate a response.")
            
            # Validate again - if still generic, give up and return enhanced fallback
            # Relax validation in agent mode (agent responses are more exploratory)
            if self._is_generic_response(response_text, agent_mode=getattr(self, '_in_agent_mode', False)):
                logger.error("Forced code analysis still returned generic response - using enhanced fallback")
                return self._generate_code_based_fallback(code_context, question_analysis)
            
            # Validate format
            response_text = self._validate_and_enforce_debugging_format(response_text, code_context)
            
            return response_text
        except Exception as e:
            logger.error(f"Failed to force code analysis: {e}")
            # Return code-based fallback instead of error
            return self._generate_code_based_fallback(code_context, question_analysis)
    
    def _generate_code_based_fallback(self, code_context: Dict[str, Any], question_analysis: Optional[Dict[str, Any]]) -> str:
        """
        Generate a code-based response without LLM.
        Always shows actual code and provides structured analysis.
        """
        logger.info("Generating code-based fallback response")
        
        files = code_context.get("files", [])
        response_parts = []
        
        # Check why we're in fallback mode
        fallback_reason = "LLM unavailable"
        if self.ollama_available:
            if not self.available_models:
                fallback_reason = "No models available in Ollama"
            else:
                fallback_reason = "LLM returned generic response or all models failed"
        else:
            fallback_reason = f"Ollama not available at {self.ollama_url}"
        
        response_parts.append("## Code Analysis (Fallback Mode)")
        response_parts.append(f"**Status:** {fallback_reason}\n")
        
        # Show all code files with analysis
        if files:
            response_parts.append("### Files Analyzed\n")
            for file_path in files:  # No limit (local processing)
                file_data = self.code_reader.read_file(file_path, max_lines=5000)  # Increased for local
                if file_data.get("success"):
                    total_lines = file_data.get("total_lines", 0)
                    lines_shown = file_data.get("lines_read", 0)
                    truncated = " (truncated)" if file_data.get("truncated") else ""
                    
                    response_parts.append(f"#### `{file_path}` ({total_lines} lines total){truncated}\n")
                    
                    # Extract key information from the code
                    content = file_data['content']
                    
                    # Find function definitions
                    import re
                    functions = re.findall(r'def\s+(\w+)\s*\([^)]*\):', content)
                    classes = re.findall(r'class\s+(\w+)', content)
                    imports = re.findall(r'^import\s+(\S+)|^from\s+(\S+)\s+import', content, re.MULTILINE)
                    
                    if functions or classes:
                        response_parts.append("**Key Components:**\n")
                        if classes:
                            response_parts.append(f"- Classes: {', '.join(classes[:10])}\n")
                        if functions:
                            response_parts.append(f"- Functions: {', '.join(functions[:15])}\n")
                        if imports:
                            import_list = [imp[0] or imp[1] for imp in imports[:10]]
                            response_parts.append(f"- Imports: {', '.join(import_list)}\n")
                        response_parts.append("")
                    
                    # Show code (limit to first 200 lines for readability)
                    code_lines = content.split('\n')
                    if len(code_lines) > 200:
                        response_parts.append(f"```\n{chr(10).join(code_lines[:200])}\n... ({len(code_lines) - 200} more lines) ...\n```\n")
                    else:
                        response_parts.append(f"```\n{content}\n```\n")
                else:
                    response_parts.append(f"**Error reading `{file_path}`:** {file_data.get('error', 'Unknown error')}\n")
        else:
            response_parts.append("**No files provided in context.**\n")
            response_parts.append("To get code analysis, ask about specific files, e.g., 'read backend/main.py'\n")
        
        # Provide structured guidance based on question type
        if question_analysis and question_analysis.get("type") == "debugging":
            response_parts.append("### Debugging Steps\n")
            response_parts.append("1. **Review the code above** - Look for data flow issues, missing null checks, type mismatches")
            response_parts.append("2. **Check API responses** - Verify backend returns expected data structure (use browser DevTools Network tab)")
            response_parts.append("3. **Trace normalization** - Check if frontend normalizes backend responses correctly")
            response_parts.append("4. **Verify database** - Check if data is stored correctly (use SQL queries)")
            response_parts.append("5. **Console logs** - Check browser/server logs for errors\n")
            
            # Add data flow diagram
            response_parts.append("### Typical Data Flow\n")
            response_parts.append("```")
            response_parts.append("Upload → /api/upload → OCR Processing → Database")
            response_parts.append("↓")
            response_parts.append("Frontend polls /api/upload/status")
            response_parts.append("↓")
            response_parts.append("Response normalized in upload.ts")
            response_parts.append("↓")
            response_parts.append("Display in Invoices.tsx / InvoiceDetailPanel.tsx")
            response_parts.append("```\n")
        else:
            response_parts.append("### Next Steps\n")
            response_parts.append("1. Review the code files above")
            response_parts.append("2. Check for common issues: missing imports, incorrect function calls, data type mismatches")
            response_parts.append("3. Verify the code matches your expectations\n")
        
        # Add diagnostic information
        response_parts.append("### Diagnostic Information\n")
        response_parts.append(f"- **Ollama Status:** {'Available' if self.ollama_available else 'Not Available'}")
        if self.ollama_available:
            response_parts.append(f"- **Available Models:** {', '.join(self.available_models) if self.available_models else 'None'}")
            response_parts.append(f"- **Primary Model:** {self.model}")
        response_parts.append(f"- **Ollama URL:** {self.ollama_url}\n")
        
        # Installation instructions
        if not self.ollama_available:
            response_parts.append("### To Enable AI Analysis\n")
            response_parts.append("1. Install Ollama: https://ollama.ai")
            response_parts.append("2. Pull a model: `ollama pull qwen2.5-coder:7b` or `ollama pull deepseek-coder:6.7b`")
            response_parts.append("3. Restart the application\n")
        elif not self.available_models:
            response_parts.append("### To Enable AI Analysis\n")
            response_parts.append("Install a model: `ollama pull qwen2.5-coder:7b` or `ollama pull deepseek-coder:6.7b`\n")
        
        return "\n".join(response_parts)
    
    def _validate_and_enforce_debugging_format(self, response_text: str, code_context: Dict[str, Any]) -> str:
        """
        Validate that debugging response follows the mandatory format.
        If not, add warnings and attempt to guide the LLM.
        """
        response_lower = response_text.lower()
        
        # Check for required sections
        has_step1 = "step 1" in response_lower and ("files analyzed" in response_lower or "files examined" in response_lower)
        has_step2 = "step 2" in response_lower and ("data flow" in response_lower or "flow trace" in response_lower)
        has_step3 = "step 3" in response_lower and ("code analysis" in response_lower or "analysis" in response_lower)
        has_step4 = "step 4" in response_lower and ("root cause" in response_lower)
        has_step5 = "step 5" in response_lower and ("fix" in response_lower)
        
        # Check for file:line references (pattern like "file.ts:123" or "file.py:456")
        import re
        file_line_pattern = r'\b\w+\.(py|ts|tsx|js|jsx):\d+'
        has_file_references = bool(re.search(file_line_pattern, response_text))
        
        # Check for code blocks with line numbers
        has_numbered_code = bool(re.search(r'\d{1,4}:\s+', response_text))
        
        # Check for generic troubleshooting patterns - MORE AGGRESSIVE
        generic_patterns = [
            r'check\s+(?:your|the)\s+(?:configuration|settings|file format)',
            r'ensure\s+(?:that|your|the)',
            r'verify\s+(?:that|your|the)',
            r'make\s+sure\s+(?:that|your|the)',
            r'potential\s+causes?:',
            r'here\s+are\s+(?:some|a few|potential)',
            r'there\s+(?:are|is)\s+(?:two|three|four|five|six|seven|eight|nine|ten|several|many)\s+(?:possible|potential)\s+(?:reasons|causes)',  # "there are two possible reasons"
            r'incorrect\s+(?:ocr|supplier|file|database|configuration|pipeline|storage|connection|upload|file\s+format|file\s+size|file\s+type)',  # "Incorrect OCR confidence"
            r'you\s+can\s+try\s+(?:adjusting|using|changing|modifying)',  # "You can try adjusting"
            r'\d+\.\s+(?:Incorrect|Check|Verify|Ensure|Make\s+sure|Try|Adjust)',  # Numbered generic list starting with "1. Incorrect..."
            r'based\s+on\s+(?:your|the)\s+(?:description|information|question)',  # "Based on your description"
            r'it\s+seems\s+(?:like|that)\s+(?:there|you)',  # "It seems like there are..."
            r'i\s+hope\s+this\s+(?:information|helps)',  # "I hope this information helps"
            r'troubleshoot\s+(?:and\s+)?resolve',  # "troubleshoot and resolve"
        ]
        has_generic_advice = any(re.search(pattern, response_lower) for pattern in generic_patterns)
        
        # Build validation warnings
        warnings = []
        if not has_step1:
            warnings.append("MISSING: Step 1 (Files Analyzed)")
        if not has_step2:
            warnings.append("MISSING: Step 2 (Data Flow Trace)")
        if not has_step3:
            warnings.append("MISSING: Step 3 (Code Analysis)")
        if not has_step4:
            warnings.append("MISSING: Step 4 (Root Cause)")
        if not has_step5:
            warnings.append("MISSING: Step 5 (Fix)")
        if not has_file_references:
            warnings.append("MISSING: File:line references (e.g., 'file.ts:123')")
        if not has_numbered_code:
            warnings.append("MISSING: Code quotes with line numbers")
        if has_generic_advice:
            warnings.append("WARNING: Contains generic troubleshooting advice - should analyze actual code instead")
        
        # If validation fails, prepend warning to response
        if warnings:
            warning_header = "\n⚠️ RESPONSE FORMAT VALIDATION FAILED ⚠️\n"
            warning_header += "The response does not follow the mandatory debugging format:\n"
            for warning in warnings:
                warning_header += f"- {warning}\n"
            warning_header += "\nPlease reformat your response to include all 5 mandatory steps with file:line references.\n"
            warning_header += "=" * 60 + "\n\n"
            
            # Prepend warning but keep original response
            response_text = warning_header + response_text
            logger.warning(f"Debugging response validation failed: {', '.join(warnings)}")
        
        return response_text
    
    def _needs_exploration(self, message: str) -> bool:
        """
        Detect if user question suggests they don't know where problem is.
        
        Indicators:
        - "why did X but Y not" (vague)
        - "something is wrong" (no location)
        - "not working" (no specifics)
        - No file paths mentioned
        
        Args:
            message: User's question
            
        Returns:
            True if exploration is needed, False otherwise
        """
        message_lower = message.lower()
        
        # Vague patterns that suggest user doesn't know where problem is
        vague_patterns = [
            "why did", "but", "not showing", "not working",
            "something", "issue", "problem", "broken",
            "doesn't work", "isn't working", "can't find",
            "where is", "what happened", "why isn't"
        ]
        
        # Specific patterns that indicate user knows where problem is
        specific_patterns = [
            r'\b\w+\.(py|ts|tsx|js):\d+',  # File:line references
            "in the", "at line", "function", "endpoint",
            "in file", "in code", "in ", "file:", "line:"
        ]
        
        has_vague = any(p in message_lower for p in vague_patterns)
        has_specific = any(re.search(p, message) for p in specific_patterns)
        
        # If vague but no specific location mentioned, needs exploration
        return has_vague and not has_specific
    
    def _parse_exploration_plan(self, plan_text: str) -> Dict[str, Any]:
        """
        Parse LLM exploration plan into structured dict.
        
        Args:
            plan_text: LLM response with exploration plan
            
        Returns:
            Dict with SEARCH, FILES, TRACE, FUNCTIONS lists
        """
        plan = {
            "SEARCH": [],
            "FILES": [],
            "TRACE": [],
            "FUNCTIONS": []
        }
        
        lines = plan_text.split('\n')
        current_section = None
        
        for line in lines:
            line_upper = line.upper().strip()
            
            # Detect section headers
            if line_upper.startswith('SEARCH:'):
                current_section = "SEARCH"
                # Extract search terms from same line
                parts = line.split(':', 1)
                if len(parts) > 1:
                    terms = parts[1].strip()
                    if terms:
                        plan["SEARCH"].extend([t.strip() for t in terms.split(',') if t.strip()])
            elif line_upper.startswith('FILES:'):
                current_section = "FILES"
                parts = line.split(':', 1)
                if len(parts) > 1:
                    files = parts[1].strip()
                    if files:
                        plan["FILES"].extend([f.strip() for f in files.split(',') if f.strip()])
            elif line_upper.startswith('TRACE:'):
                current_section = "TRACE"
                parts = line.split(':', 1)
                if len(parts) > 1:
                    trace = parts[1].strip()
                    if trace:
                        plan["TRACE"].append(trace)
            elif line_upper.startswith('FUNCTIONS:'):
                current_section = "FUNCTIONS"
                parts = line.split(':', 1)
                if len(parts) > 1:
                    funcs = parts[1].strip()
                    if funcs:
                        plan["FUNCTIONS"].extend([f.strip() for f in funcs.split(',') if f.strip()])
            elif current_section and line.strip():
                # Continue reading items for current section
                items = [item.strip() for item in line.split(',') if item.strip()]
                plan[current_section].extend(items)
        
        return plan
    
    def _validate_exploration_plan(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and sanitize exploration plan.
        
        Args:
            plan: Exploration plan dict
            
        Returns:
            Validated and sanitized plan
        """
        validated = {
            "SEARCH": [],
            "FILES": [],
            "TRACE": [],
            "FUNCTIONS": []
        }
        
        # Validate and filter search terms
        for term in plan.get("SEARCH", []):
            if term and isinstance(term, str):
                term = term.strip()
                # Check length (2-100 chars)
                if 2 <= len(term) <= 100:
                    # Remove duplicates
                    if term not in validated["SEARCH"]:
                        validated["SEARCH"].append(term)
                else:
                    logger.warning(f"Invalid search term length: '{term[:50]}...' (length: {len(term)})")
        
        # Validate file paths exist
        for file_path in plan.get("FILES", []):
            if file_path and isinstance(file_path, str):
                file_path = file_path.strip()
                # Try to read file to validate it exists
                file_data = self.code_reader.read_file(file_path, max_lines=1)
                if file_data.get("success"):
                    if file_path not in validated["FILES"]:
                        validated["FILES"].append(file_path)
                else:
                    logger.warning(f"Invalid file in plan: {file_path} - {file_data.get('error', 'not found')}")
        
        # Validate trace descriptions
        for trace in plan.get("TRACE", []):
            if trace and isinstance(trace, str):
                trace = trace.strip()
                # Check if trace has valid format (contains arrow or "to")
                if ('→' in trace or '->' in trace or ' to ' in trace) and len(trace) <= 200:
                    if trace not in validated["TRACE"]:
                        validated["TRACE"].append(trace)
                else:
                    logger.warning(f"Invalid trace format: '{trace[:50]}...'")
        
        # Validate function names
        for func_name in plan.get("FUNCTIONS", []):
            if func_name and isinstance(func_name, str):
                func_name = func_name.strip()
                # Check if valid identifier (alphanumeric, underscore, dot)
                if re.match(r'^[a-zA-Z_][a-zA-Z0-9_.]*$', func_name) and len(func_name) <= 100:
                    if func_name not in validated["FUNCTIONS"]:
                        validated["FUNCTIONS"].append(func_name)
                else:
                    logger.warning(f"Invalid function name: '{func_name}'")
        
        logger.info(
            f"Plan validation: {len(validated['SEARCH'])} searches, "
            f"{len(validated['FILES'])} files, {len(validated['TRACE'])} traces, "
            f"{len(validated['FUNCTIONS'])} functions"
        )
        
        return validated
    
    def _validate_file_path(self, file_path: str) -> bool:
        """
        Validate file path before operations.
        
        Args:
            file_path: File path to validate
            
        Returns:
            True if path is valid, False otherwise
        """
        if not file_path or not isinstance(file_path, str):
            return False
        
        # Normalize path
        file_path = file_path.strip().replace('\\', '/')
        
        # Check for path traversal attempts
        if '..' in file_path or file_path.startswith('/'):
            logger.warning(f"Potential path traversal attempt: {file_path}")
            return False
        
        # Check if path is within repo root
        try:
            full_path = self.code_reader.repo_root / file_path
            resolved = full_path.resolve()
            repo_root_resolved = self.code_reader.repo_root.resolve()
            
            if not str(resolved).startswith(str(repo_root_resolved)):
                logger.warning(f"Path outside repo root: {file_path}")
                return False
        except Exception as e:
            logger.warning(f"Path validation error for {file_path}: {e}")
            return False
        
        return True
    
    def _estimate_tokens(self, text: str) -> int:
        """
        Estimate token count for text.
        Rough estimation: ~4 characters per token (conservative).
        
        Args:
            text: Text to estimate tokens for
            
        Returns:
            Estimated token count
        """
        if not text:
            return 0
        # Conservative estimate: 4 chars per token
        # More accurate would be using tiktoken, but this is fast and good enough
        return len(text) // 4
    
    def _truncate_findings(self, findings: List[Dict], max_tokens: int = None) -> List[Dict]:
        """
        Truncate findings to fit within token budget (disabled for local processing).
        Prioritizes high-score results and important finding types.
        
        Args:
            findings: List of exploration result dicts
            max_tokens: Maximum tokens to allow (None = no limit for local processing)
            
        Returns:
            Truncated list of findings (or all if max_tokens is None)
        """
        if not findings:
            return []
        
        # If no limit specified, return all findings (local processing)
        if max_tokens is None or max_tokens <= 0:
            return findings
        
        # Sort by priority: file > trace > search > function_call > other
        type_priority = {
            "file": 4,
            "trace": 3,
            "search": 2,
            "function_call": 2,
            "grep": 1,
            "unknown": 0
        }
        
        # Sort findings by priority and score
        def get_priority(finding: Dict) -> tuple:
            finding_type = finding.get("type", "unknown")
            priority = type_priority.get(finding_type, 0)
            score = finding.get("score", 0)
            return (-priority, -score)  # Negative for descending sort
        
        sorted_findings = sorted(findings, key=get_priority)
        
        # Truncate based on token budget
        truncated = []
        total_tokens = 0
        
        for finding in sorted_findings:
            # Estimate tokens for this finding
            finding_text = str(finding)
            tokens = self._estimate_tokens(finding_text)
            
            if total_tokens + tokens > max_tokens:
                logger.info(f"Truncating findings at {len(truncated)}/{len(findings)} (token budget: {max_tokens})")
                break
            
            truncated.append(finding)
            total_tokens += tokens
        
        return truncated
    
    def _deduplicate_findings(self, findings: List[Dict]) -> List[Dict]:
        """
        Remove duplicate findings to improve quality.
        Merges similar findings (same file:line, different context).
        
        Args:
            findings: List of exploration result dicts
            
        Returns:
            Deduplicated list of findings
        """
        if not findings:
            return []
        
        seen = set()
        unique = []
        
        for finding in findings:
            finding_type = finding.get("type", "unknown")
            file_path = finding.get("file") or finding.get("file_path", "unknown")
            line = finding.get("line", 0)
            
            # Create key based on file:line:type
            key = (file_path, line, finding_type)
            
            if key not in seen:
                seen.add(key)
                unique.append(finding)
            else:
                # Same file:line:type - merge contexts if available
                # Find existing finding and merge context
                for existing in unique:
                    if (existing.get("file") or existing.get("file_path")) == file_path and \
                       existing.get("line") == line and \
                       existing.get("type") == finding_type:
                        # Merge context if new finding has better context
                        new_context = finding.get("context", "")
                        existing_context = existing.get("context", "")
                        if new_context and len(new_context) > len(existing_context):
                            existing["context"] = new_context
                        break
        
        logger.debug(f"Deduplication: {len(findings)} -> {len(unique)} findings")
        return unique
    
    def _format_findings(self, findings: List[Dict], query_context: Optional[str] = None, files_read_tracker: Optional[set] = None) -> str:
        """
        Format exploration results for LLM consumption with smart truncation.
        
        Args:
            findings: List of exploration result dicts
            query_context: Optional user query for context
            files_read_tracker: Optional set of previously read files
            
        Returns:
            Formatted string with findings
        """
        if not findings:
            return "No findings from exploration."
        
        # Deduplicate results first
        findings = self._deduplicate_results(findings)
        
        # Summarize if too many results
        summary_info = self._summarize_results(findings, max_items=20)
        if summary_info["should_summarize"]:
            findings = summary_info["details"]
            summary_text = summary_info["summary"]
        else:
            summary_text = None
        
        # Score and sort by relevance
        scored_findings = [(self._score_result_relevance(f, query_context, files_read_tracker), f) for f in findings]
        scored_findings.sort(reverse=True, key=lambda x: x[0])
        findings = [f for _, f in scored_findings]
        
        # Limit findings to prevent huge output
        MAX_FINDINGS = 50
        if len(findings) > MAX_FINDINGS:
            logger.info(f"Limiting findings formatting to {MAX_FINDINGS} (from {len(findings)})")
            findings = findings[:MAX_FINDINGS]
        
        formatted = []
        formatted.append("=== EXPLORATION FINDINGS ===\n")
        
        # Add summary if available
        if summary_text:
            formatted.append(f"Summary: {summary_text}\n")
        
        for i, finding in enumerate(findings, 1):
            finding_type = finding.get("type", "unknown")
            
            if finding_type == "file" or finding_type == "read":
                file_path = finding.get("file", "unknown")
                content = finding.get("content", "")
                
                # Smart truncation: keep function definitions, remove comments
                truncated_content = self._smart_truncate_content(content, max_length=500)
                
                formatted.append(f"\n[{i}] File: {file_path}")
                formatted.append(f"Content preview:\n{truncated_content}")
                if len(content) > 500:
                    formatted.append(f"... (truncated, showing key code sections)")
            elif finding_type == "search":
                file_path = finding.get("file", finding.get("file_path", "unknown"))
                line = finding.get("line", 0)
                match = finding.get("match", finding.get("content", ""))
                context = finding.get("context", "")
                formatted.append(f"\n[{i}] Search match in {file_path}:{line}")
                formatted.append(f"Match: {match}")
                if context:
                    # Smart truncate context too
                    truncated_context = self._smart_truncate_content(context, max_length=200)
                    formatted.append(f"Context:\n{truncated_context}")
            elif finding_type == "trace":
                file_path = finding.get("file", "unknown")
                description = finding.get("description", "")
                code = finding.get("code", "")
                formatted.append(f"\n[{i}] Data flow: {file_path}")
                formatted.append(f"Description: {description}")
                if code:
                    truncated_code = self._smart_truncate_content(code, max_length=500)
                    formatted.append(f"Code preview:\n{truncated_code}")
            elif finding_type == "error":
                # Format errors with suggestions
                error_msg = finding.get("error", "Unknown error")
                command = finding.get("command", {})
                suggestions = finding.get("suggestions", "")
                error_category = finding.get("error_category", "unknown")
                
                formatted.append(f"\n❌ ERROR [{i}]: {error_msg}")
                if command:
                    cmd_type = command.get('type', 'UNKNOWN')
                    cmd_param = command.get('file', command.get('term', command.get('pattern', '')))
                    formatted.append(f"   Command: {cmd_type} {cmd_param}")
                if error_category:
                    formatted.append(f"   Category: {error_category}")
                if suggestions:
                    formatted.append(f"   💡 {suggestions}")
            else:
                # Generic finding
                formatted.append(f"\n[{i}] {finding}")
        
        formatted.append("\n=== END FINDINGS ===\n")
        return "\n".join(formatted)
    
    def _smart_truncate_content(self, content: str, max_length: int = 500, start_line: int = 1) -> str:
        """
        Smart truncation: preserve code structure, truncate at boundaries, show line numbers.
        
        Args:
            content: Content to truncate
            max_length: Maximum length
            start_line: Starting line number (for line number display)
            
        Returns:
            Truncated content with line numbers and boundary markers
        """
        if len(content) <= max_length:
            return content
        
        lines = content.split('\n')
        important_lines = []
        current_length = 0
        line_num = start_line
        in_function = False
        in_class = False
        brace_count = 0
        bracket_count = 0
        paren_count = 0
        last_important_line = 0
        
        # Track indentation to preserve structure
        base_indent = 0
        if lines:
            first_line = lines[0]
            base_indent = len(first_line) - len(first_line.lstrip())
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            line_indent = len(line) - len(line.lstrip())
            
            # Count brackets/braces/parens to detect boundaries
            brace_count += line.count('{') - line.count('}')
            bracket_count += line.count('[') - line.count(']')
            paren_count += line.count('(') - line.count(')')
            
            # Detect function/class boundaries
            is_function_def = bool(re.match(r'^\s*(def|async\s+def)\s+', stripped))
            is_class_def = bool(re.match(r'^\s*class\s+', stripped))
            is_decorator = bool(re.match(r'^\s*@', stripped))
            is_import = bool(re.match(r'^\s*(import|from)\s+', stripped))
            is_type_hint = bool(re.match(r'^\s*[A-Z][a-zA-Z0-9_]*\s*:', stripped))  # Type hints
            
            # Prioritize important code patterns
            is_important = (
                is_function_def or
                is_class_def or
                is_decorator or
                is_import or
                is_type_hint or
                (stripped and not stripped.startswith('#') and not stripped.startswith('"""') and not stripped.startswith("'''"))
            )
            
            # Check if we're at a natural boundary (end of function/class)
            at_boundary = (
                (brace_count == 0 and bracket_count == 0 and paren_count == 0) or
                (in_function and is_function_def) or  # New function starts
                (in_class and is_class_def)  # New class starts
            )
            
            # If we're approaching the limit and at a boundary, truncate here
            if current_length > max_length * 0.9 and at_boundary and not is_important:
                break
            
            # Add line if important or we have room
            if is_important or current_length < max_length * 0.7:
                important_lines.append((line_num, line))
                current_length += len(line) + 1
                last_important_line = line_num
                
                if is_function_def:
                    in_function = True
                if is_class_def:
                    in_class = True
            elif current_length < max_length:
                # Add non-important lines if we have room
                important_lines.append((line_num, line))
                current_length += len(line) + 1
            
            # Stop if we've exceeded the limit
            if current_length > max_length:
                break
            
            line_num += 1
        
        # Build result with line numbers
        result_lines = []
        for line_num, line in important_lines:
            result_lines.append(f"{line_num:4d} | {line}")
        
        result = '\n'.join(result_lines)
        
        # Add truncation marker with line range
        if len(content) > len(result):
            original_lines = len(lines)
            shown_lines = len(important_lines)
            result += f"\n... (truncated: showing lines {start_line}-{last_important_line} of {original_lines} total lines, {len(result)}/{len(content)} chars)"
        
        return result
    
    def _resolve_file_path(self, file_path: str, files_read_tracker: Optional[set] = None) -> Tuple[str, float]:
        """
        Resolve file path with fuzzy matching for typos and path variations.
        Uses Levenshtein-like distance (SequenceMatcher) and caches resolved paths.
        
        Args:
            file_path: Original file path (may have typos)
            files_read_tracker: Optional set of previously read files for context
            
        Returns:
            Tuple of (resolved_path, confidence_score) where confidence is 0.0-1.0
        """
        from pathlib import Path
        
        # Cache resolved paths to avoid repeated lookups
        if not hasattr(self, '_path_resolution_cache'):
            self._path_resolution_cache = {}
        
        # Check cache first
        cache_key = (file_path, tuple(sorted(files_read_tracker)) if files_read_tracker else None)
        if cache_key in self._path_resolution_cache:
            return self._path_resolution_cache[cache_key]
        
        # Try exact match first
        if Path(file_path).exists():
            result = (file_path, 1.0)
            self._path_resolution_cache[cache_key] = result
            return result
        
        # Try common path variations
        possible_paths = [
            file_path,
            f"backend/{file_path}",
            f"frontend/{file_path}",
            f"frontend_clean/{file_path}",
        ]
        
        # If path starts with backend/frontend, also try without prefix
        if file_path.startswith('backend/'):
            possible_paths.append(file_path[8:])
        elif file_path.startswith('frontend/'):
            possible_paths.append(file_path[9:])
        
        # Check exact matches in variations
        for path in possible_paths:
            if Path(path).exists():
                result = (path, 0.9)
                self._path_resolution_cache[cache_key] = result
                return result
        
        # If we have files_read_tracker, use it for fuzzy matching
        if files_read_tracker:
            best_match = None
            best_score = 0.0
            
            for known_file in files_read_tracker:
                # Calculate similarity using SequenceMatcher (Levenshtein-like distance)
                similarity = SequenceMatcher(None, file_path.lower(), known_file.lower()).ratio()
                if similarity > best_score and similarity > 0.7:  # 70% similarity threshold
                    best_score = similarity
                    best_match = known_file
            
            if best_match:
                result = (best_match, best_score)
                self._path_resolution_cache[cache_key] = result
                return result
        
        # Try fuzzy matching against all files in workspace
        try:
            workspace_files = []
            for root_dir in ['backend', 'frontend', 'frontend_clean', '.']:
                root_path = Path(root_dir)
                if root_path.exists():
                    for file in root_path.rglob('*.py'):
                        workspace_files.append(str(file))
                    for file in root_path.rglob('*.js'):
                        workspace_files.append(str(file))
                    for file in root_path.rglob('*.jsx'):
                        workspace_files.append(str(file))
                    for file in root_path.rglob('*.ts'):
                        workspace_files.append(str(file))
                    for file in root_path.rglob('*.tsx'):
                        workspace_files.append(str(file))
            
            best_match = None
            best_score = 0.0
            
            # Extract filename for comparison
            target_filename = Path(file_path).name.lower()
            
            for workspace_file in workspace_files[:1000]:  # Limit search for performance
                workspace_filename = Path(workspace_file).name.lower()
                similarity = SequenceMatcher(None, target_filename, workspace_filename).ratio()
                if similarity > best_score and similarity > 0.8:  # 80% similarity threshold
                    best_score = similarity
                    best_match = workspace_file
            
            if best_match:
                result = (best_match, best_score * 0.8)  # Lower confidence for workspace search
                self._path_resolution_cache[cache_key] = result
                return result
        except Exception as e:
            logger.debug(f"Error in fuzzy file matching: {e}")
        
        # Return original path with low confidence if no match found
        result = (file_path, 0.0)
        self._path_resolution_cache[cache_key] = result
        return result
    
    def _validate_command(self, cmd: Dict) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Validate command before execution.
        
        Args:
            cmd: Command dict with type and parameters
            
        Returns:
            Tuple of (is_valid, error_message, suggestion)
        """
        cmd_type = cmd.get("type")
        
        if cmd_type == "READ":
            file_path = cmd.get("file")
            # Validate parameter type
            if not file_path:
                return False, "READ command missing 'file' field", "Specify a file path: READ backend/main.py"
            if not isinstance(file_path, str):
                return False, f"READ command 'file' must be a string, got {type(file_path).__name__}", "Specify a file path as a string: READ backend/main.py"
            if not file_path.strip():
                return False, "READ command 'file' field is empty", "Specify a non-empty file path: READ backend/main.py"
            
            # Try to resolve path
            resolved_path, confidence = self._resolve_file_path(file_path)
            if confidence < 0.7:
                suggestions = []
                if confidence > 0.0:
                    suggestions.append(f"Did you mean: {resolved_path}?")
                suggestions.append("Check the file path spelling and location.")
                return False, f"File '{file_path}' not found (confidence: {confidence:.0%})", " | ".join(suggestions)
            
            # Update command with resolved path if different
            if resolved_path != file_path:
                cmd["file"] = resolved_path
                logger.info(f"Resolved file path: {file_path} -> {resolved_path} (confidence: {confidence:.0%})")
            
            return True, None, None
        
        elif cmd_type == "GREP":
            pattern = cmd.get("pattern")
            # Validate parameter type
            if not pattern:
                return False, "GREP command missing 'pattern' field", "Specify a search pattern: GREP def function_name"
            if not isinstance(pattern, str):
                return False, f"GREP command 'pattern' must be a string, got {type(pattern).__name__}", "Specify a search pattern as a string: GREP def function_name"
            if not pattern.strip():
                return False, "GREP command 'pattern' field is empty", "Specify a non-empty search pattern: GREP def function_name"
            
            # Pre-validate regex pattern syntax
            try:
                re.compile(pattern)
            except re.error as e:
                error_msg = str(e)
                suggestion = "Check regex syntax. Common issues:\n"
                suggestion += "- Unclosed brackets: use \\[ or \\] for literal brackets\n"
                suggestion += "- Invalid escape sequences: use \\\\ for backslash\n"
                suggestion += "- Unmatched parentheses: check all ( and ) are balanced\n"
                suggestion += "Use READ to see the file first, then use a simpler pattern."
                return False, f"Invalid regex pattern: {error_msg}", suggestion
            
            return True, None, None
        
        elif cmd_type == "SEARCH":
            term = cmd.get("term")
            # Validate parameter type
            if not term:
                return False, "SEARCH command missing 'term' field", "Specify a search term: SEARCH upload endpoint"
            if not isinstance(term, str):
                return False, f"SEARCH command 'term' must be a string, got {type(term).__name__}", "Specify a search term as a string: SEARCH upload endpoint"
            if not term.strip():
                return False, "SEARCH command 'term' field is empty", "Specify a non-empty search term: SEARCH upload endpoint"
            
            return True, None, None
        
        elif cmd_type == "TRACE":
            start = cmd.get("start")
            end = cmd.get("end")
            # Validate parameter types and presence
            if not start:
                return False, "TRACE command missing 'start' field", "Specify start point: TRACE upload → database"
            if not isinstance(start, str):
                return False, f"TRACE command 'start' must be a string, got {type(start).__name__}", "Specify start point as a string: TRACE upload → database"
            if not start.strip():
                return False, "TRACE command 'start' field is empty", "Specify a non-empty start point: TRACE upload → database"
            if not end:
                return False, "TRACE command missing 'end' field", "Specify end point: TRACE upload → database"
            if not isinstance(end, str):
                return False, f"TRACE command 'end' must be a string, got {type(end).__name__}", "Specify end point as a string: TRACE upload → database"
            if not end.strip():
                return False, "TRACE command 'end' field is empty", "Specify a non-empty end point: TRACE upload → database"
            
            return True, None, None
        
        elif cmd_type == "ANALYZE":
            return True, None, None
        
        else:
            return False, f"Unknown command type: {cmd_type}", "Supported commands: READ, SEARCH, GREP, TRACE, ANALYZE"
    
    def _categorize_error(self, error: Exception, cmd: Dict) -> Tuple[str, bool, Dict[str, Any]]:
        """
        Categorize error as permanent or transient with detailed context.
        
        Args:
            error: Exception that occurred
            cmd: Command that failed
            
        Returns:
            Tuple of (error_category, should_retry, error_context) where:
            - error_category is 'permanent' or 'transient'
            - should_retry is True if error should be retried
            - error_context is a dict with error details (file, line, command_type, error_type, error_message)
        """
        error_str = str(error).lower()
        error_type = type(error).__name__
        cmd_type = cmd.get("type", "UNKNOWN")
        
        # Build error context
        error_context = {
            "error_type": error_type,
            "error_message": str(error),
            "command_type": cmd_type,
            "file": cmd.get("file") if cmd_type == "READ" else None,
            "pattern": cmd.get("pattern") if cmd_type == "GREP" else None,
            "term": cmd.get("term") if cmd_type == "SEARCH" else None,
        }
        
        # Permanent errors (don't retry)
        permanent_indicators = [
            'file not found',
            'no such file',
            'cannot find',
            'does not exist',
            'invalid regex',
            'syntax error',
            'invalid',
            'not found',
            'filenotfounderror',
            'permission denied',
            'access denied',
            'is a directory',
            'is not a file',
            'invalid path',
            'malformed',
            'bad request',
            '400',  # HTTP 400 Bad Request
            '404',  # HTTP 404 Not Found
        ]
        
        # Transient errors (should retry)
        transient_indicators = [
            'timeout',
            'connection',
            'network',
            'temporary',
            'busy',
            'locked',
            'resource',
            'eagain',
            'eintr',
            'timedout',
            'connectionerror',
            'timeouterror',
            '503',  # HTTP 503 Service Unavailable
            '502',  # HTTP 502 Bad Gateway
            '504',  # HTTP 504 Gateway Timeout
            'rate limit',
            'too many requests',
            '429',  # HTTP 429 Too Many Requests
        ]
        
        # Check error message
        for indicator in permanent_indicators:
            if indicator in error_str:
                error_context["category_reason"] = f"Permanent error detected: '{indicator}' in error message"
                return 'permanent', False, error_context
        
        for indicator in transient_indicators:
            if indicator in error_str:
                error_context["category_reason"] = f"Transient error detected: '{indicator}' in error message"
                return 'transient', True, error_context
        
        # Check error type
        permanent_error_types = [
            'FileNotFoundError', 
            'PermissionError', 
            'ValueError', 
            'SyntaxError',
            'KeyError',
            'AttributeError',
            'TypeError',
            'IndexError',
            'PatternError',  # re.PatternError for invalid regex
            'error',  # re.error (base class for regex errors)
        ]
        
        transient_error_types = [
            'TimeoutError', 
            'ConnectionError', 
            'requests.exceptions.Timeout', 
            'requests.exceptions.ConnectionError',
            'OSError',  # Often transient (EAGAIN, EINTR)
            'IOError',  # Often transient
        ]
        
        if error_type in permanent_error_types:
            error_context["category_reason"] = f"Permanent error type: {error_type}"
            return 'permanent', False, error_context
        
        if error_type in transient_error_types:
            error_context["category_reason"] = f"Transient error type: {error_type}"
            return 'transient', True, error_context
        
        # Default: treat as transient for unknown errors (safer to retry)
        error_context["category_reason"] = "Unknown error type, treating as transient (safer to retry)"
        return 'transient', True, error_context
    
    def _aggregate_errors(self, errors: List[Dict]) -> Dict[str, Any]:
        """
        Aggregate errors from parallel operations with intelligent grouping and actionable suggestions.
        
        Args:
            errors: List of error dicts with 'error', 'command', 'type', 'error_category', 'error_context' fields
            
        Returns:
            Aggregated error summary dict with groups, suggestions, and retry information
        """
        if not errors:
            return {"total": 0, "groups": [], "summary": "", "suggestions": [], "retry_info": {}}
        
        # Group errors by category and type for better organization
        error_groups = {}
        permanent_count = 0
        transient_count = 0
        retry_attempts = {}
        
        for error_info in errors:
            error_msg = error_info.get("error", "Unknown error")
            cmd_type = error_info.get("command", {}).get("type", "UNKNOWN")
            error_category = error_info.get("error_category", "unknown")
            error_context = error_info.get("error_context", {})
            suggestion = error_info.get("suggestions")
            
            # Track error categories
            if error_category == "permanent":
                permanent_count += 1
            elif error_category == "transient":
                transient_count += 1
            
            # Create group key based on category, command type, and error message
            # This groups similar errors together more intelligently
            error_key = error_msg[:100]  # Use first 100 chars for grouping
            group_key = f"{error_category}:{cmd_type}:{error_key}"
            
            if group_key not in error_groups:
                error_groups[group_key] = {
                    "count": 0,
                    "category": error_category,
                    "cmd_type": cmd_type,
                    "error": error_msg,
                    "error_type": error_context.get("error_type", "Unknown"),
                    "commands": [],
                    "suggestions": [],
                    "files": set(),
                    "patterns": set(),
                }
            
            error_groups[group_key]["count"] += 1
            error_groups[group_key]["commands"].append(error_info.get("command", {}))
            
            # Collect suggestions (deduplicate)
            if suggestion and suggestion not in error_groups[group_key]["suggestions"]:
                error_groups[group_key]["suggestions"].append(suggestion)
            
            # Collect file paths for READ errors
            if cmd_type == "READ" and error_context.get("file"):
                error_groups[group_key]["files"].add(error_context["file"])
            
            # Collect patterns for GREP errors
            if cmd_type == "GREP" and error_context.get("pattern"):
                error_groups[group_key]["patterns"].add(error_context["pattern"])
        
        # Build actionable summary with suggestions
        summary_parts = []
        all_suggestions = []
        
        for group_key, group_info in error_groups.items():
            count = group_info["count"]
            cmd_type = group_info["cmd_type"]
            error = group_info["error"]
            category = group_info["category"]
            
            # Build error description
            if count == 1:
                error_desc = f"{cmd_type} error ({category}): {error}"
            else:
                error_desc = f"{count} {cmd_type} errors ({category}): {error}"
            
            # Add file/pattern context if available
            if group_info["files"]:
                files_list = list(group_info["files"])[:3]  # Show first 3 files
                error_desc += f" [Files: {', '.join(files_list)}]"
            if group_info["patterns"]:
                patterns_list = list(group_info["patterns"])[:2]  # Show first 2 patterns
                error_desc += f" [Patterns: {', '.join(patterns_list)}]"
            
            summary_parts.append(error_desc)
            
            # Collect suggestions
            if group_info["suggestions"]:
                all_suggestions.extend(group_info["suggestions"])
        
        # Convert sets to lists for JSON serialization
        for group_info in error_groups.values():
            group_info["files"] = list(group_info["files"])
            group_info["patterns"] = list(group_info["patterns"])
        
        # Build retry information
        retry_info = {
            "permanent_errors": permanent_count,
            "transient_errors": transient_count,
            "total_errors": len(errors),
            "should_retry": transient_count > 0,
        }
        
        # Deduplicate suggestions
        unique_suggestions = []
        seen_suggestions = set()
        for suggestion in all_suggestions:
            suggestion_lower = suggestion.lower().strip()
            if suggestion_lower and suggestion_lower not in seen_suggestions:
                unique_suggestions.append(suggestion)
                seen_suggestions.add(suggestion_lower)
        
        return {
            "total": len(errors),
            "groups": list(error_groups.values()),
            "summary": " | ".join(summary_parts),
            "suggestions": unique_suggestions[:5],  # Limit to top 5 suggestions
            "retry_info": retry_info,
        }
    
    def _score_result_relevance(self, result: Dict, query_context: Optional[str] = None, files_read_tracker: Optional[set] = None) -> float:
        """
        Score result relevance based on match quality, file importance, and context.
        Uses caching for repeated queries and tracks file access frequency.
        
        Args:
            result: Result dict with 'type', 'file', 'match', 'line', etc.
            query_context: Optional user query for context matching
            files_read_tracker: Optional set of previously read files
            
        Returns:
            Relevance score between 0.0 and 1.0
        """
        result_type = result.get("type", "")
        file_path = result.get("file", "")
        match_text = result.get("match", result.get("content", "")).lower()
        
        # Check cache first (use query hash for cache key)
        if query_context:
            import hashlib
            query_hash = hashlib.md5(query_context.lower().encode()).hexdigest()[:8]
            cache_key = (file_path, query_hash)
            if cache_key in self._relevance_score_cache:
                return self._relevance_score_cache[cache_key]
        
        score = 0.5  # Base score
        
        # Enhanced match quality scoring with semantic matching
        if query_context:
            query_lower = query_context.lower()
            query_words = set(query_lower.split())
            
            # Exact phrase match (highest priority)
            if query_lower in match_text:
                score += 0.3
            
            # Word-level matching with position weighting
            match_words = set(match_text.split())
            common_words = query_words & match_words
            
            if common_words:
                # Calculate word overlap ratio
                overlap_ratio = len(common_words) / max(len(query_words), 1)
                score += overlap_ratio * 0.2
                
                # Boost for important keywords (longer words, function names, etc.)
                important_words = [w for w in common_words if len(w) > 4 or w.isalnum()]
                if important_words:
                    score += min(len(important_words) * 0.05, 0.1)
            
            # Semantic matching: check for related terms (simple heuristic)
            # Boost if match contains words that often appear with query words
            semantic_boost = 0.0
            if 'function' in query_lower and ('def' in match_text or 'function' in match_text):
                semantic_boost += 0.05
            if 'class' in query_lower and 'class' in match_text:
                semantic_boost += 0.05
            if 'error' in query_lower and ('error' in match_text or 'exception' in match_text):
                semantic_boost += 0.05
            score += semantic_boost
        
        # File importance weighting based on access frequency
        file_importance = 0.0
        if file_path:
            # Track file access
            self._file_access_count[file_path] = self._file_access_count.get(file_path, 0) + 1
            
            # Boost for frequently accessed files (importance = log(access_count + 1) / 10)
            access_count = self._file_access_count[file_path]
            file_importance = min(math.log(access_count + 1) / 10, 0.15)
            score += file_importance
            
            # Boost for files in current context
            if files_read_tracker and file_path in files_read_tracker:
                score += 0.1
        
        # Result type weighting
        if result_type == "read":
            score += 0.15  # File reads are most important
        elif result_type == "search":
            score += 0.08
        elif result_type == "grep":
            score += 0.05
        elif result_type == "trace":
            score += 0.1  # Traces are important for understanding flow
        
        # Penalize very long matches (less focused)
        if len(match_text) > 500:
            score -= 0.1
        elif len(match_text) < 20:
            score += 0.05  # Short, focused matches are often better
        
        # Boost for results with line numbers (more specific)
        if result.get("line") is not None:
            score += 0.05
        
        # Cache the score
        if query_context:
            cache_key = (file_path, query_hash)
            # Limit cache size to prevent unbounded growth
            if len(self._relevance_score_cache) < 1000:
                self._relevance_score_cache[cache_key] = score
        
        # Ensure score is between 0.0 and 1.0
        return max(0.0, min(1.0, score))
    
    def _deduplicate_results(self, results: List[Dict]) -> List[Dict]:
        """
        Deduplicate similar results with intelligent merging of line ranges and context.
        Merges results from same file with nearby lines (within 10 lines) into line ranges.
        
        Args:
            results: List of result dicts
            
        Returns:
            Deduplicated list of results with merged line ranges and best context
        """
        if not results:
            return results
        
        # Group results by file and type for efficient merging
        grouped_results: Dict[Tuple[str, str], List[Dict]] = {}
        
        for result in results:
            result_type = result.get("type", "")
            file_path = result.get("file", "")
            group_key = (file_path, result_type)
            
            if group_key not in grouped_results:
                grouped_results[group_key] = []
            grouped_results[group_key].append(result)
        
        deduplicated = []
        
        for (file_path, result_type), group_results in grouped_results.items():
            if result_type == "read":
                # For READ results, keep only one per file (most recent or with most context)
                best_result = max(group_results, key=lambda r: len(r.get("content", r.get("match", ""))))
                deduplicated.append(best_result)
            
            elif result_type in ["search", "grep"]:
                # Sort by line number for range merging
                sorted_results = sorted(group_results, key=lambda r: r.get("line", 0))
                
                # Merge nearby results (within 10 lines) into ranges
                merged_ranges = []
                current_range = None
                
                for result in sorted_results:
                    line = result.get("line", 0)
                    match_text = result.get("match", "")
                    context = result.get("context", "")
                    
                    if current_range is None:
                        # Start new range
                        current_range = {
                            "type": result_type,
                            "file": file_path,
                            "line": line,
                            "line_end": line,
                            "matches": [match_text],
                            "contexts": [context] if context else [],
                            "result": result  # Keep original result structure
                        }
                    else:
                        # Check if this result is within 10 lines of current range
                        if line <= current_range["line_end"] + 10:
                            # Extend current range
                            current_range["line_end"] = line
                            if match_text and match_text not in current_range["matches"]:
                                current_range["matches"].append(match_text)
                            if context and context not in current_range["contexts"]:
                                current_range["contexts"].append(context)
                        else:
                            # Save current range and start new one
                            merged_ranges.append(current_range)
                            current_range = {
                                "type": result_type,
                                "file": file_path,
                                "line": line,
                                "line_end": line,
                                "matches": [match_text],
                                "contexts": [context] if context else [],
                                "result": result
                            }
                
                # Add last range
                if current_range:
                    merged_ranges.append(current_range)
                
                # Convert merged ranges back to result format
                for merged in merged_ranges:
                    if merged["line"] == merged["line_end"]:
                        # Single line result
                        result = merged["result"].copy()
                        result["line"] = merged["line"]
                    else:
                        # Multi-line range result
                        result = merged["result"].copy()
                        result["line"] = merged["line"]
                        result["line_range"] = f"{merged['line']}-{merged['line_end']}"
                        # Merge best context (longest or most relevant)
                        if merged["contexts"]:
                            best_context = max(merged["contexts"], key=len)
                            result["context"] = best_context
                        # Merge matches
                        if len(merged["matches"]) > 1:
                            result["match"] = f"{len(merged['matches'])} matches: " + ", ".join(merged["matches"][:3])
                    
                    deduplicated.append(result)
            
            else:
                # For other types (trace, etc.), use exact deduplication
                seen_keys = set()
                for result in group_results:
                    key = f"{result_type}:{file_path}:{result.get('line', 0)}:{result.get('match', '')[:50]}"
                    if key not in seen_keys:
                        seen_keys.add(key)
                        deduplicated.append(result)
        
        return deduplicated
    
    def _summarize_results(self, results: List[Dict], max_items: int = 20) -> Dict[str, Any]:
        """
        Create summary for large result sets.
        
        Args:
            results: List of result dicts
            max_items: Maximum items before summarization kicks in
            
        Returns:
            Summary dict with 'summary', 'details', 'should_summarize' fields
        """
        if len(results) <= max_items:
            return {
                "summary": "",
                "details": results,
                "should_summarize": False
            }
        
        # Group results by type and file
        by_type = {}
        by_file = {}
        
        for result in results:
            result_type = result.get("type", "unknown")
            file_path = result.get("file", "unknown")
            
            if result_type not in by_type:
                by_type[result_type] = 0
            by_type[result_type] += 1
            
            if file_path not in by_file:
                by_file[file_path] = 0
            by_file[file_path] += 1
        
        # Create summary text
        summary_parts = [f"Found {len(results)} results:"]
        
        for result_type, count in by_type.items():
            summary_parts.append(f"  - {count} {result_type} results")
        
        summary_parts.append(f"\nFiles: {len(by_file)} files")
        summary_parts.append("Top files:")
        for file_path, count in sorted(by_file.items(), key=lambda x: x[1], reverse=True)[:5]:
            summary_parts.append(f"  - {file_path}: {count} results")
        
        # Keep top N most relevant results for details
        scored_results = [(self._score_result_relevance(r), r) for r in results]
        scored_results.sort(reverse=True)
        top_results = [r for _, r in scored_results[:max_items]]
        
        return {
            "summary": "\n".join(summary_parts),
            "details": top_results,
            "should_summarize": True,
            "total_count": len(results)
        }
    
    def _validate_code_snippets(self, response: str, files_read_tracker: set) -> List[str]:
        """
        Validate code snippets match actual file content with improved extraction and fuzzy matching.
        
        Args:
            response: LLM response text
            files_read_tracker: Set of files that were read
            
        Returns:
            List of validation issues with specific line numbers and expected vs actual
        """
        issues = []
        
        # Extract code blocks from response (handle more formats)
        code_block_patterns = [
            r'```(?:python|javascript|typescript|js|ts|json)?\n(.*?)```',  # Standard code blocks
            r'```(?:python|javascript|typescript|js|ts|json)?\s*\n(.*?)```',  # With optional language tag
            r'<code[^>]*>(.*?)</code>',  # HTML code tags
        ]
        
        code_blocks = []
        for pattern in code_block_patterns:
            code_blocks.extend(re.findall(pattern, response, re.DOTALL))
        
        # Also extract inline code snippets (backticks)
        inline_code_pattern = r'`([^`\n]+)`'  # Exclude newlines from inline code
        inline_codes = re.findall(inline_code_pattern, response)
        
        # Extract file:line references (improved pattern)
        file_line_patterns = [
            r'([a-zA-Z0-9_/\\-]+\.(?:py|js|jsx|ts|tsx|json)):(\d+)',  # Standard format
            r'([a-zA-Z0-9_/\\-]+\.(?:py|js|jsx|ts|tsx|json))\((\d+)\)',  # Alternative format
            r'at\s+([a-zA-Z0-9_/\\-]+\.(?:py|js|jsx|ts|tsx|json)):(\d+)',  # "at file.py:123"
        ]
        
        file_line_refs = []
        for pattern in file_line_patterns:
            file_line_refs.extend(re.findall(pattern, response))
        
        # For each file:line reference, verify the code matches
        for file_path, line_num_str in file_line_refs:
            try:
                line_num = int(line_num_str)
                
                # Resolve file path
                resolved_path, confidence = self._resolve_file_path(file_path, files_read_tracker)
                if confidence < 0.7:
                    issues.append(f"Code snippet references file '{file_path}' that doesn't exist (confidence: {confidence:.2f})")
                    continue
                
                # Try to read the file and check the line
                try:
                    # Read more context around the line for better matching
                    context_lines = 5
                    file_data = self.code_reader.read_file(resolved_path, max_lines=line_num + context_lines)
                    if file_data.get("success"):
                        content = file_data.get("content", "")
                        lines = content.split('\n')
                        if line_num <= len(lines):
                            actual_line = lines[line_num - 1]
                            actual_line_stripped = actual_line.strip()
                            
                            # Get surrounding context for better matching
                            start_line = max(0, line_num - context_lines - 1)
                            end_line = min(len(lines), line_num + context_lines)
                            context_block = '\n'.join(lines[start_line:end_line])
                            
                            # Find code snippets that reference this line
                            for code_block in code_blocks:
                                # Check if code block contains placeholder comments instead of actual code
                                if re.search(r'#\s*(?:Code|TODO|FIXME|PLACEHOLDER)\s+to\s+', code_block, re.IGNORECASE):
                                    issues.append(f"Code snippet at {resolved_path}:{line_num} contains placeholder code ('# Code to...') instead of actual code")
                                    continue
                                
                                # Check if the actual line from file is in the code block (fuzzy matching)
                                if actual_line_stripped and len(actual_line_stripped) > 5:  # Only check substantial lines
                                    # Extract non-comment, non-whitespace content from actual line
                                    actual_content = re.sub(r'^\s*#.*$', '', actual_line_stripped).strip()
                                    actual_content_no_ws = re.sub(r'\s+', '', actual_content)
                                    
                                    # Normalize code block for comparison (remove extra whitespace)
                                    code_block_normalized = re.sub(r'\s+', ' ', code_block)
                                    
                                    # Check exact match first
                                    if actual_content in code_block or actual_content_no_ws in code_block_normalized:
                                        continue  # Match found, no issue
                                    
                                    # Fuzzy matching: check if key parts match (function names, variable names)
                                    # Extract identifiers from actual line
                                    identifiers = re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b', actual_content)
                                    if identifiers:
                                        # Check if at least 50% of identifiers are in code block
                                        matches = sum(1 for ident in identifiers if ident in code_block)
                                        if matches < len(identifiers) * 0.5:
                                            # Mismatch detected
                                            expected_preview = actual_content[:60] + "..." if len(actual_content) > 60 else actual_content
                                            issues.append(
                                                f"Code snippet at {resolved_path}:{line_num} doesn't match actual code. "
                                                f"Expected: '{expected_preview}' (line {line_num})"
                                            )
                                
                                # Check variable names match
                                # Extract variable names from code block and actual code
                                code_vars = set(re.findall(r'\b([a-z_][a-z0-9_]*)\b', code_block, re.IGNORECASE))
                                actual_vars = set(re.findall(r'\b([a-z_][a-z0-9_]*)\b', actual_line_stripped, re.IGNORECASE))
                                
                                # Filter out common keywords
                                keywords = {'def', 'class', 'if', 'else', 'for', 'while', 'return', 'import', 'from', 'as', 'in', 'is', 'not', 'and', 'or'}
                                code_vars -= keywords
                                actual_vars -= keywords
                                
                                # If code block has variables that don't exist in actual code, flag it
                                if code_vars and actual_vars:
                                    mismatched_vars = code_vars - actual_vars
                                    if mismatched_vars and len(mismatched_vars) > len(code_vars) * 0.3:  # More than 30% mismatch
                                        issues.append(
                                            f"Code snippet at {resolved_path}:{line_num} contains variables that don't match actual code: {', '.join(list(mismatched_vars)[:3])}"
                                        )
                                
                                # Also check inline code snippets
                                for inline_code in inline_codes:
                                    if file_path in inline_code or str(line_num) in inline_code:
                                        if re.search(r'#\s*(?:Code|TODO|FIXME|PLACEHOLDER)\s+to\s+', inline_code, re.IGNORECASE):
                                            issues.append(f"Code snippet at {resolved_path}:{line_num} contains placeholder code in inline snippet")
                                            continue
                                        
                                        # Check if inline code matches actual line
                                        if actual_line_stripped and len(actual_line_stripped) > 5:
                                            actual_content = re.sub(r'^\s*#.*$', '', actual_line_stripped).strip()
                                            if actual_content not in inline_code and actual_content[:20] not in inline_code:
                                                issues.append(
                                                    f"Inline code snippet at {resolved_path}:{line_num} doesn't match actual code: '{actual_content[:50]}...'"
                                                )
                except Exception as e:
                    logger.debug(f"Error validating code snippet for {resolved_path}:{line_num}: {e}")
                    issues.append(f"Error validating code snippet at {resolved_path}:{line_num}: {str(e)}")
            except ValueError:
                # Invalid line number
                issues.append(f"Invalid line number '{line_num_str}' in reference to '{file_path}'")
        
        return issues
    
    def _validate_execution_path(self, response: str, files_read_tracker: set) -> List[str]:
        """
        Validate execution paths (A→B→C) are valid with improved parsing and call chain verification.
        
        Args:
            response: LLM response text
            files_read_tracker: Set of files that were read
            
        Returns:
            List of validation issues with specific details about broken chains
        """
        issues = []
        
        # Extract execution paths (handle more arrow formats: →, ->, =>, TO)
        path_patterns = [
            # Two-step paths: A → B
            r'([a-zA-Z0-9_/\\-]+\.(?:py|js|jsx|ts|tsx)(?::\d+)?)\s*(?:→|->|=>|TO)\s*([a-zA-Z0-9_/\\-]+\.(?:py|js|jsx|ts|tsx)(?::\d+)?)',
            # Multi-step paths: A → B → C (capture all steps)
            r'([a-zA-Z0-9_/\\-]+\.(?:py|js|jsx|ts|tsx)(?::\d+)?)\s*(?:→|->|=>|TO)\s*([a-zA-Z0-9_/\\-]+\.(?:py|js|jsx|ts|tsx)(?::\d+)?)\s*(?:→|->|=>|TO)\s*([a-zA-Z0-9_/\\-]+\.(?:py|js|jsx|ts|tsx)(?::\d+)?)',
            # Text format: "from A to B" or "A calls B"
            r'(?:from|in)\s+([a-zA-Z0-9_/\\-]+\.(?:py|js|jsx|ts|tsx)(?::\d+)?)\s+(?:to|calls|→|->|=>)\s+([a-zA-Z0-9_/\\-]+\.(?:py|js|jsx|ts|tsx)(?::\d+)?)',
        ]
        
        for pattern in path_patterns:
            matches = re.findall(pattern, response, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    paths = [p for p in match if p]  # Filter out empty strings
                else:
                    paths = [match]
                
                if len(paths) < 2:
                    continue
                
                # Verify each file in path exists
                previous_path = None
                for i, path_with_line in enumerate(paths):
                    # Extract file path and line number
                    if ':' in path_with_line:
                        path, line_str = path_with_line.rsplit(':', 1)
                        try:
                            line_num = int(line_str)
                        except ValueError:
                            line_num = None
                    else:
                        path = path_with_line
                        line_num = None
                    
                    # Resolve file path
                    resolved_path, confidence = self._resolve_file_path(path, files_read_tracker)
                    if confidence < 0.7:
                        issues.append(f"Execution path step {i+1} references file '{path}' that doesn't exist (confidence: {confidence:.2f})")
                        previous_path = None
                        continue
                    
                    # Verify step exists (if line number provided)
                    if line_num is not None:
                        try:
                            file_data = self.code_reader.read_file(resolved_path, max_lines=line_num + 5)
                            if file_data.get("success"):
                                lines = file_data.get("content", "").split('\n')
                                if line_num > len(lines):
                                    issues.append(f"Execution path step {i+1} references line {line_num} in '{resolved_path}' but file only has {len(lines)} lines")
                        except Exception as e:
                            logger.debug(f"Error validating execution path step at {resolved_path}:{line_num}: {e}")
                    
                    # Check call chain validity: verify B is actually called from A
                    if previous_path and i > 0:
                        prev_resolved, prev_confidence = self._resolve_file_path(previous_path, files_read_tracker)
                        if prev_confidence >= 0.7:
                            # Try to verify that resolved_path is imported/called from prev_resolved
                            try:
                                prev_file_data = self.code_reader.read_file(prev_resolved, max_lines=5000)
                                if prev_file_data.get("success"):
                                    prev_content = prev_file_data.get("content", "")
                                    
                                    # Check if current file is imported in previous file
                                    current_file_name = os.path.basename(resolved_path).replace('.py', '').replace('.js', '').replace('.ts', '')
                                    import_patterns = [
                                        f"import.*{current_file_name}",
                                        f"from.*{current_file_name}.*import",
                                        f"require.*{current_file_name}",
                                        f"import.*{resolved_path.replace(os.sep, '/')}",
                                    ]
                                    
                                    has_import = any(re.search(pattern, prev_content, re.IGNORECASE) for pattern in import_patterns)
                                    
                                    if not has_import:
                                        # Check if it's a relative import or different pattern
                                        # This is a warning, not an error, as the call might be indirect
                                        logger.debug(f"Execution path: '{prev_resolved}' → '{resolved_path}' - no direct import found (might be indirect)")
                            except Exception as e:
                                logger.debug(f"Error checking call chain from {prev_resolved} to {resolved_path}: {e}")
                    
                    previous_path = path
        
        return issues
    
    def _validate_root_cause(self, response: str, files_read_tracker: set) -> List[str]:
        """
        Validate root cause section for accuracy.
        
        Args:
            response: LLM response text
            files_read_tracker: Set of files that were read
            
        Returns:
            List of validation issues
        """
        issues = []
        
        # Extract root cause section
        root_cause_patterns = [
            r'\*\*Root Cause\*\*[:\s]*(.*?)(?=\*\*|\n\n|$)',
            r'Root Cause[:\s]*(.*?)(?=\*\*|\n\n|$)',
            r'## Root Cause[:\s]*(.*?)(?=##|\n\n|$)',
        ]
        
        root_cause_text = None
        for pattern in root_cause_patterns:
            match = re.search(pattern, response, re.IGNORECASE | re.DOTALL)
            if match:
                root_cause_text = match.group(1).strip()
                break
        
        if not root_cause_text:
            # Root cause section not found - this is already checked elsewhere
            return issues
        
        # Check that root cause contains file:line references (should be specific)
        file_line_pattern = r'([a-zA-Z0-9_/\\-]+\.(?:py|js|jsx|ts|tsx)):(\d+)'
        file_line_refs = re.findall(file_line_pattern, root_cause_text)
        
        if not file_line_refs:
            issues.append("Root Cause section should contain specific file:line references (e.g., backend/file.py:123)")
        
        # Validate each file:line reference
        for file_path, line_num_str in file_line_refs:
            try:
                line_num = int(line_num_str)
                resolved_path, confidence = self._resolve_file_path(file_path, files_read_tracker)
                if confidence < 0.7:
                    issues.append(f"Root Cause references file '{file_path}' that doesn't exist")
                    continue
                
                # Verify line number is valid
                try:
                    file_data = self.code_reader.read_file(resolved_path, max_lines=line_num + 5)
                    if file_data.get("success"):
                        content = file_data.get("content", "")
                        lines = content.split('\n')
                        if line_num > len(lines):
                            issues.append(f"Root Cause references line {line_num} in '{resolved_path}' but file only has {len(lines)} lines")
                except Exception as e:
                    logger.debug(f"Error validating root cause line number for {resolved_path}:{line_num}: {e}")
            except ValueError:
                issues.append(f"Root Cause contains invalid line number '{line_num_str}' in '{file_path}'")
        
        # Check for function/class names mentioned in root cause
        function_patterns = [
            r'(?:method|function|class)\s+(\w+)',
            r'(\w+)\s+(?:method|function|class)',
            r'(\w+)\s+in\s+[\w/\\-]+\.(?:py|js|jsx|ts|tsx)',
        ]
        
        mentioned_functions = set()
        for pattern in function_patterns:
            matches = re.findall(pattern, root_cause_text, re.IGNORECASE)
            mentioned_functions.update(matches)
        
        # Filter out common words
        common_words = {'class', 'method', 'function', 'the', 'a', 'an', 'in', 'at', 'is', 'are', 'was', 'were'}
        for func_name in mentioned_functions:
            if func_name.lower() in common_words or len(func_name) < 3:
                continue
            
            # Check if function/class exists
            exists, _ = self._function_exists_in_codebase(func_name, files_read_tracker)
            if not exists:
                # Check if it's a class name (try different pattern)
                class_pattern = f"class {func_name}"
                class_results = self.code_explorer.grep_pattern(class_pattern)
                if len(class_results) == 0:
                    issues.append(f"Root Cause mentions '{func_name}' (function/class) that doesn't exist in codebase")
        
        return issues
    
    def _parse_agent_commands(self, response: str) -> List[Dict]:
        """
        Parse LLM response for agent commands.
        Supports multiple formats, multi-line commands, and aliases.
        
        Args:
            response: LLM response text
            
        Returns:
            List of command dicts with type and parameters
        """
        commands = []
        
        # Validate input
        if not response or not isinstance(response, str):
            return commands
        
        # Command aliases mapping
        command_aliases = {
            'FIND': 'SEARCH',
            'OPEN': 'READ',
            'LOOKUP': 'SEARCH',
            'VIEW': 'READ',
            'SHOW': 'READ',
            'GATHER': 'SEARCH',
        }
        
        # Normalize response: handle multi-line commands with continuation markers
        # Enhanced to handle 3+ line commands with better regex patterns
        normalized_lines = []
        current_command = None
        continuation_count = 0  # Track how many lines we've continued
        
        lines = response.split('\n')
        for i, line in enumerate(lines):
            stripped = line.strip()
            original_line = line  # Keep original for indentation check
            
            # Check if this is a blank line
            if not stripped:
                # If we have a command in progress, check if next non-blank line continues it
                if current_command:
                    # Look ahead to see if next non-blank line is a continuation
                    next_non_blank = None
                    for j in range(i + 1, min(i + 3, len(lines))):  # Look ahead up to 2 lines
                        next_line = lines[j].strip()
                        if next_line:
                            next_non_blank = next_line
                            break
                    
                    # If next line doesn't start a new command, it might be continuation
                    if next_non_blank:
                        next_upper = next_non_blank.upper()
                        is_new_command = any(next_upper.startswith(cmd + ' ') for cmd in 
                                           ['READ', 'SEARCH', 'GREP', 'TRACE', 'ANALYZE', 'FIND', 'OPEN', 'LOOKUP', 'VIEW', 'SHOW', 'GATHER'])
                        if not is_new_command and not next_non_blank.startswith(('```', '---', '===')):
                            # Likely continuation, keep current_command
                            continue
                    
                    # Blank line ends current command
                    normalized_lines.append(current_command)
                    current_command = None
                    continuation_count = 0
                continue
            
            # Check if this line continues a previous command
            if current_command:
                # Enhanced continuation detection: backslash, indentation, parentheses, quotes
                has_backslash = line.rstrip().endswith('\\')
                has_indentation = original_line.startswith((' ', '\t')) and not stripped.startswith(('READ', 'SEARCH', 'GREP', 'TRACE', 'ANALYZE', 'FIND', 'OPEN', 'LOOKUP', 'VIEW', 'SHOW', 'GATHER'))
                has_open_paren = current_command.count('(') > current_command.count(')')
                has_open_quote = (current_command.count('"') % 2 != 0) or (current_command.count("'") % 2 != 0)
                is_continuation_marker = stripped.startswith(('...', '→', '->', 'TO', 'to'))
                
                # Check if line starts a new command (must be at start of line, not indented)
                line_upper = stripped.upper()
                is_new_command = not original_line.startswith((' ', '\t')) and any(line_upper.startswith(cmd + ' ') for cmd in 
                                                                                  ['READ', 'SEARCH', 'GREP', 'TRACE', 'ANALYZE', 'FIND', 'OPEN', 'LOOKUP', 'VIEW', 'SHOW', 'GATHER'])
                
                # Determine if this is a continuation
                if is_new_command:
                    # New command starts - save previous and start new
                    normalized_lines.append(current_command)
                    current_command = stripped
                    continuation_count = 0
                elif has_backslash or has_indentation or has_open_paren or has_open_quote or is_continuation_marker:
                    # Continuation - append to current command
                    if has_backslash:
                        current_command += ' ' + stripped.rstrip('\\')
                    else:
                        current_command += ' ' + stripped
                    continuation_count += 1
                    # Safety limit: don't continue forever (max 10 continuation lines)
                    if continuation_count > 10:
                        normalized_lines.append(current_command)
                        current_command = None
                        continuation_count = 0
                else:
                    # Ambiguous - check if it looks like a new command or continuation
                    # If it starts with a command keyword but is indented, treat as continuation
                    if has_indentation:
                        current_command += ' ' + stripped
                        continuation_count += 1
                    else:
                        # Likely a new command or non-command text
                        normalized_lines.append(current_command)
                        current_command = None
                        continuation_count = 0
                        # Check if this line starts a new command
                        if any(line_upper.startswith(cmd) for cmd in ['READ', 'SEARCH', 'GREP', 'TRACE', 'ANALYZE', 'FIND', 'OPEN', 'LOOKUP', 'VIEW', 'SHOW', 'GATHER']):
                            current_command = stripped
            else:
                # Check if line starts a command
                line_upper = stripped.upper()
                if any(line_upper.startswith(cmd) for cmd in ['READ', 'SEARCH', 'GREP', 'TRACE', 'ANALYZE', 'FIND', 'OPEN', 'LOOKUP', 'VIEW', 'SHOW', 'GATHER']):
                    current_command = stripped
                    continuation_count = 0
                else:
                    # Not a command line, but might be continuation of previous (if we had one)
                    # For now, just add as-is (will be ignored if not a command)
                    normalized_lines.append(stripped)
        
        # Add last command if exists
        if current_command:
            normalized_lines.append(current_command)
        
        # Parse normalized lines
        for line in normalized_lines:
            line = line.strip()
            if not line:
                continue
            
            line_upper = line.upper()
            
            # Check for command aliases and normalize
            command_type = None
            for alias, canonical in command_aliases.items():
                if line_upper.startswith(alias + ' '):
                    command_type = canonical
                    line = line[len(alias):].strip()
                    line_upper = line_upper[len(alias):].strip()
                    break
            
            # SEARCH command (or FIND alias)
            if line_upper.startswith('SEARCH ') or (command_type == 'SEARCH'):
                if command_type == 'SEARCH':
                    term = line.strip()
                else:
                    term = line[7:].strip()
                # Remove quotes if present
                term = term.strip('"\'')
                if term:
                    commands.append({"type": "SEARCH", "term": term})
            elif 'SEARCH:' in line_upper or 'SEARCH -' in line_upper:
                # Handle "SEARCH: term" or "SEARCH - term"
                term = line.split(':', 1)[-1].split('-', 1)[-1].strip().strip('"\'')
                if term:
                    commands.append({"type": "SEARCH", "term": term})
            
            # READ command (or OPEN/VIEW/SHOW alias)
            elif line_upper.startswith('READ ') or (command_type == 'READ'):
                if command_type == 'READ':
                    file_path = line.strip()
                else:
                    file_path = line[5:].strip()
                # Remove quotes if present
                file_path = file_path.strip('"\'')
                # Handle "READ: file" format
                if ':' in file_path:
                    file_path = file_path.split(':', 1)[-1].strip()
                if file_path:
                    commands.append({"type": "READ", "file": file_path})
            elif line_upper.startswith('READ FILE ') or line_upper.startswith('READ FILE:'):
                file_path = line.split(':', 1)[-1].split('FILE', 1)[-1].strip().strip('"\'')
                if file_path:
                    commands.append({"type": "READ", "file": file_path})
            
            # TRACE command
            elif line_upper.startswith('TRACE '):
                trace = line[6:].strip()
                if '→' in trace or '->' in trace or ' to ' in trace or ' TO ' in trace:
                    # Parse start and end
                    if '→' in trace:
                        parts = trace.split('→', 1)
                    elif '->' in trace:
                        parts = trace.split('->', 1)
                    elif ' TO ' in trace:
                        parts = trace.split(' TO ', 1)
                    else:
                        parts = trace.split(' to ', 1)
                    
                    start = parts[0].strip().strip('"\'') if len(parts) > 0 else ""
                    end = parts[1].strip().strip('"\'') if len(parts) > 1 else ""
                    
                    # Only add TRACE command if both start and end are present
                    if start and end:
                        commands.append({
                            "type": "TRACE",
                            "start": start,
                            "end": end
                        })
            
            # GREP command
            elif line_upper.startswith('GREP '):
                pattern = line[5:].strip().strip('"\'')
                if pattern:
                    commands.append({"type": "GREP", "pattern": pattern})
            elif 'GREP:' in line_upper or 'GREP -' in line_upper:
                pattern = line.split(':', 1)[-1].split('-', 1)[-1].strip().strip('"\'')
                if pattern:
                    commands.append({"type": "GREP", "pattern": pattern})
            
            # ANALYZE command
            elif line_upper.startswith('ANALYZE') or line_upper == 'ANALYZE':
                commands.append({"type": "ANALYZE"})
        
        return commands
    
    def _search_mode_with_metadata(
        self,
        message: str,
        question_analysis: Dict[str, Any],
        conversation_history: Optional[List[Dict[str, str]]],
        progress_callback: Optional[Callable[[str, int, int], None]] = None
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Search mode: comprehensive information gathering workflow with metadata.
        
        Returns tuple of (response_text, metadata_dict)
        """
        # Pass progress callback through
        response_text = self._search_mode(
            message,
            question_analysis,
            conversation_history,
            progress_callback
        )
        
        # Extract metadata from exploration (we'll track this during execution)
        metadata = getattr(self, '_last_exploration_metadata', {
            "mode": "single_turn",
            "files_searched": 0,
            "files_read": [],
            "searches_executed": 0,
            "search_terms": [],
            "findings_count": 0,
            "exploration_time": 0,
            "timed_out": False
        })
        
        return response_text, metadata
    
    def _search_mode(
        self,
        message: str,
        question_analysis: Dict[str, Any],
        conversation_history: Optional[List[Dict[str, str]]],
        progress_callback: Optional[Callable[[str, int, int], None]] = None
    ) -> str:
        """
        Search mode: Comprehensive information gathering workflow.
        
        Step 1: Understand what information is needed and generate search plan
        Step 2: Execute comprehensive searches (search, trace, read files)
        Step 3: Collect and organize all findings
        Step 4: Generate comprehensive summary of what was found
        
        Focus: Information discovery and collection, not problem-solving.
        
        Args:
            message: User's information request
            question_analysis: Question classification results
            conversation_history: Previous conversation messages
            
        Returns:
            Comprehensive information summary with code references
        """
        logger.info("Starting Search mode workflow")
        config = get_config()
        exploration_start_time = time.time()
        exploration_timeout = config.exploration_timeout
        
        # Initialize exploration session
        self._last_exploration_session_id = str(uuid.uuid4())
        try:
            from backend.services.exploration_history import save_exploration_session
            save_exploration_session(
                session_id=self._last_exploration_session_id,
                user_message=message,
                response_text=None,  # Will be updated later
                exploration_metadata={},  # Will be updated later
                findings=[],  # Will be updated later
                request_id=getattr(self, '_current_request_id', None)
            )
        except Exception as e:
            logger.warning(f"Failed to create exploration session: {e}")
        
        if progress_callback:
            progress_callback("Generating exploration plan...", 0, 4)
        
        # Step 1: Generate search plan using LLM
        search_plan_prompt = f"""You are a code information gatherer. The user wants to find information about: "{message}"

Generate a comprehensive search plan to gather ALL relevant information. Think broadly - what should we search for? What files might contain relevant code? What functions or data flows are related?

CRITICAL: If the query is about API endpoints, routes, or HTTP methods, you MUST:
- Search for ALL route decorators: @app.post, @app.get, @router.post, @router.get, @app.put, @app.delete, @app.patch
- Search for route registration patterns: app.include_router, app.add_api_route
- Search in main.py and all route files (routes/, api/, backend/routes/, backend/api/)
- Look for FastAPI/Flask route patterns comprehensively
- Include variations: @app.route, @router.route, app.post, router.post

Your goal is to find and collect information, not to solve problems.

Respond in this format:
SEARCH: [list of search terms, comma-separated - be comprehensive, include variations]
FILES: [list of file paths to check, comma-separated - include main.py and route files]
TRACE: [data flows to trace, e.g., "upload → normalize → display"]
FUNCTIONS: [function names to find, comma-separated]

Be thorough and comprehensive - cast a wide net to gather all relevant information."""
        
        # Get search plan from LLM
        try:
            plan_text = self._call_ollama_simple(search_plan_prompt, temperature=0.3)
            logger.info(f"Exploration plan generated: {plan_text[:200]}...")
        except Exception as e:
            logger.warning(f"Failed to generate exploration plan: {e}, using heuristics")
            # Fallback to heuristic-based suggestions
            plan_text = ""
            suggestions = self.code_explorer.suggest_exploration_path(message)
            plan = {
                "SEARCH": [message],
                "FILES": suggestions,  # No limit (local processing)
                "TRACE": [],
                "FUNCTIONS": []
            }
        else:
            # Parse plan
            plan = self._parse_exploration_plan(plan_text)
        
        # Validate and sanitize exploration plan
        plan = self._validate_exploration_plan(plan)
        
        # Check if plan has any valid actions
        total_actions = (
            len(plan.get("SEARCH", [])) + 
            len(plan.get("FILES", [])) + 
            len(plan.get("TRACE", [])) + 
            len(plan.get("FUNCTIONS", []))
        )
        if total_actions == 0:
            logger.warning("Plan validation removed all items, using heuristic fallback")
            suggestions = self.code_explorer.suggest_exploration_path(message)
            plan = {
                "SEARCH": [message] if message else ["code", "function"],
                "FILES": suggestions[:config.max_files_per_plan],
                "TRACE": [],
                "FUNCTIONS": []
            }
            # Re-validate the fallback plan
            plan = self._validate_exploration_plan(plan)
            total_actions = (
                len(plan.get("SEARCH", [])) + 
                len(plan.get("FILES", [])) + 
                len(plan.get("TRACE", [])) + 
                len(plan.get("FUNCTIONS", []))
            )
            if total_actions == 0:
                logger.error("Even heuristic fallback produced empty plan")
                return (
                    "[Exploration Mode] Unable to generate exploration plan.\n\n"
                    "**Issue:** No valid files or search terms could be determined from your question.\n\n"
                    "**Suggestions:**\n"
                    "1. Include specific file names (e.g., 'in upload.ts')\n"
                    "2. Mention specific functions or features\n"
                    "3. Use more concrete terms related to the problem\n"
                    "4. Try rephrasing with technical keywords"
                )
        
        # Check circuit breaker before starting
        ollama_cb = self.retry_handler.circuit_breakers.get("ollama_api")
        if ollama_cb and not ollama_cb.can_attempt():
            logger.warning("Circuit breaker is open for ollama_api, skipping exploration")
            return (
                "[Exploration Mode] Ollama API is temporarily unavailable (circuit breaker open).\n\n"
                "**Status:** Too many recent failures detected. System is protecting itself.\n\n"
                "**Recovery Actions:**\n"
                "1. Wait 60 seconds and try again\n"
                "2. Check if Ollama is running: `ollama serve`\n"
                "3. Verify Ollama is accessible at the configured URL\n"
                "4. Try a more specific question that doesn't require exploration"
            )
        
        if progress_callback:
            progress_callback("Plan validated, starting exploration...", 1, 4)
        
        # Check timeout before starting exploration
        if time.time() - exploration_start_time > exploration_timeout:
            logger.warning("Exploration timeout before starting execution")
            return (
                "[Exploration Mode] Exploration timed out during planning phase.\n\n"
                "**Issue:** Planning took too long (>2 minutes).\n\n"
                "**Suggestions:**\n"
                "1. Try a more specific question\n"
                "2. Include file paths or function names\n"
                "3. Break down complex questions into smaller parts"
            )
        
        # Step 2: Execute exploration
        findings = []
        files_searched = 0
        searches_executed = 0
        files_read = []
        search_terms_used = []
        
        # Execute searches in parallel with per-step timeout
        max_searches = config.max_files_per_plan  # Reuse max_files for searches too
        search_terms = plan.get("SEARCH", [])[:max_searches]
        total_searches = len(search_terms)
        
        if total_searches > 0:
            if progress_callback:
                progress_callback(f"Starting {total_searches} parallel searches...", 1, 4)
            
            # Define search function for parallel execution
            def execute_search(search_term: str) -> Tuple[str, List[Dict], Optional[str]]:
                """Execute a single search and return (term, results, error)."""
                try:
                    if time.time() - exploration_start_time > exploration_timeout:
                        return (search_term, [], "timeout")
                    
                    search_start = time.time()
                    results = self.code_explorer.search_concept(search_term, max_results=config.max_search_results)
                    search_time = time.time() - search_start
                    logger.info(f"Search '{search_term}' completed in {search_time:.2f}s, found {len(results)} results")
                    return (search_term, results, None)
                except Exception as e:
                    logger.warning(f"Search failed for '{search_term}': {e}")
                    return (search_term, [], str(e))
            
            # Execute searches in parallel (cap max_workers to avoid context switching)
            completed_searches = 0
            max_workers = min(config.max_parallel_searches, total_searches, min(8, os.cpu_count() or 4))
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit all search tasks
                future_to_term = {
                    executor.submit(execute_search, term): term 
                    for term in search_terms
                }
                
                # Process results as they complete
                for future in as_completed(future_to_term):
                    if time.time() - exploration_start_time > exploration_timeout:
                        logger.warning(f"Exploration timeout during parallel searches")
                        # Cancel remaining tasks
                        for f in future_to_term:
                            f.cancel()
                        findings.append({
                            "type": "timeout",
                            "file": "exploration",
                            "line": 0,
                            "match": f"Exploration timed out after {searches_executed} searches",
                            "context": "Exploration exceeded time limit. Partial results may be incomplete."
                        })
                        break
                    
                    try:
                        search_term, results, error = future.result()
                        completed_searches += 1
                        
                        # Update progress
                        if progress_callback:
                            progress_callback(
                                f"Searching... ({completed_searches}/{total_searches} complete)",
                                1,
                                4
                            )
                        
                        if error:
                            logger.warning(f"Search '{search_term}' failed: {error}")
                        else:
                            search_terms_used.append(search_term)
                            searches_executed += 1
                            for result in results:
                                findings.append({
                                    "type": "search",
                                    "file": result.get("file"),
                                    "line": result.get("line"),
                                    "match": result.get("match"),
                                    "context": result.get("context")
                                })
                    except Exception as e:
                        search_term = future_to_term[future]
                        logger.error(f"Unexpected error in search '{search_term}': {e}")
            
            logger.info(f"Parallel search execution completed: {searches_executed}/{total_searches} successful")
            
            # Post-processing: If query is about endpoints/routes/API, do additional endpoint discovery
            if any(term in message.lower() for term in ["endpoint", "route", "api", "http method"]):
                logger.info("Endpoint-related query detected, performing additional endpoint discovery")
                endpoint_patterns = [
                    r"@app\.(post|get|put|delete|patch)\(",
                    r"@router\.(post|get|put|delete|patch)\(",
                    r"app\.(post|get|put|delete|patch)\(",
                    r"router\.(post|get|put|delete|patch)\(",
                ]
                endpoint_findings_count = 0
                for pattern in endpoint_patterns:
                    try:
                        if time.time() - exploration_start_time > exploration_timeout:
                            logger.warning("Endpoint discovery timeout")
                            break
                        endpoint_results = self.code_explorer.search_concept(pattern, max_results=100)
                        for result in endpoint_results:
                            # Check if this finding is already present (same file and nearby line)
                            existing = any(
                                f.get("file") == result.get("file") and 
                                abs(f.get("line", 0) - result.get("line", 0)) < 5
                                for f in findings
                            )
                            if not existing:
                                findings.append({
                                    "type": "search",
                                    "file": result.get("file"),
                                    "line": result.get("line"),
                                    "match": result.get("match"),
                                    "context": result.get("context")
                                })
                                endpoint_findings_count += 1
                    except Exception as e:
                        logger.warning(f"Endpoint discovery search failed for pattern {pattern}: {e}")
                
                logger.info(f"Endpoint discovery added {endpoint_findings_count} additional endpoint findings")
        
        # Extract unique file paths from search results to read them
        files_from_searches = set()
        for finding in findings:
            if finding.get("type") == "search" and finding.get("file"):
                file_path = finding.get("file")
                if self._validate_file_path(file_path):
                    files_from_searches.add(file_path)
                    # Limit files from searches to avoid reading too many
                    if len(files_from_searches) >= config.max_files_per_plan:
                        break
        
        # Combine plan files with files found in searches (prioritize plan files)
        plan_files = plan.get("FILES", [])[:config.max_files_per_plan]
        # Merge: plan files first, then search files (up to max limit)
        all_file_paths = list(plan_files)
        remaining_slots = config.max_files_per_plan - len(all_file_paths)
        if remaining_slots > 0:
            search_files_list = list(files_from_searches)[:remaining_slots]
            # Add search files that aren't already in plan
            for search_file in search_files_list:
                if search_file not in all_file_paths:
                    all_file_paths.append(search_file)
        
        total_files = len(all_file_paths)
        logger.info(f"Files to read: {len(plan_files)} from plan, {len(files_from_searches)} from searches, {total_files} total")
        
        if total_files > 0:
            if progress_callback:
                progress_callback(f"Reading {total_files} files in parallel...", 2, 4)
            
            # Define file read function for parallel execution
            def execute_file_read(file_path: str) -> Tuple[str, Optional[Dict], Optional[str]]:
                """Execute a single file read and return (path, file_data, error)."""
                try:
                    if time.time() - exploration_start_time > exploration_timeout:
                        return (file_path, None, "timeout")
                    
                    # Validate path before reading
                    if not self._validate_file_path(file_path):
                        return (file_path, None, "invalid_path")
                    
                    file_start = time.time()
                    file_data = self.code_reader.read_file(file_path, max_lines=config.max_lines_per_file)
                    file_time = time.time() - file_start
                    logger.info(f"Read file '{file_path}' in {file_time:.2f}s")
                    return (file_path, file_data, None)
                except Exception as e:
                    logger.warning(f"Error reading file '{file_path}': {e}")
                    return (file_path, None, str(e))
            
            # Execute file reads in parallel (cap max_workers to avoid context switching)
            completed_reads = 0
            max_workers = min(config.max_parallel_file_reads, total_files, min(8, os.cpu_count() or 4))
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit all file read tasks
                future_to_path = {
                    executor.submit(execute_file_read, path): path 
                    for path in all_file_paths
                }
                
                # Process results as they complete
                for future in as_completed(future_to_path):
                    if time.time() - exploration_start_time > exploration_timeout:
                        logger.warning(f"Exploration timeout during parallel file reads")
                        # Cancel remaining tasks
                        for f in future_to_path:
                            f.cancel()
                        findings.append({
                            "type": "timeout",
                            "file": "exploration",
                            "line": 0,
                            "match": f"Exploration timed out after reading {files_searched} files",
                            "context": "Exploration exceeded time limit. Partial results may be incomplete."
                        })
                        break
                    
                    try:
                        file_path, file_data, error = future.result()
                        completed_reads += 1
                        
                        # Update progress
                        if progress_callback:
                            progress_callback(
                                f"Reading files... ({completed_reads}/{total_files} complete)",
                                2,
                                4
                            )
                        
                        if error == "timeout":
                            break
                        elif error == "invalid_path":
                            logger.warning(f"Invalid file path: {file_path}")
                            continue
                        elif error:
                            logger.warning(f"File read failed for '{file_path}': {error}")
                            continue
                        
                        files_searched += 1
                        if file_data and file_data.get("success"):
                            files_read.append(file_path)
                            findings.append({
                                "type": "file",
                                "file": file_path,
                                "line": 0,
                                "match": file_data.get("content", "")[:200],  # First 200 chars
                                "context": file_data.get("content", "")
                            })
                    except Exception as e:
                        file_path = future_to_path[future]
                        logger.error(f"Unexpected error reading file '{file_path}': {e}")
            
            logger.info(f"Parallel file read execution completed: {files_searched}/{total_files} successful")
        
        # Execute traces
        for trace_desc in plan.get("TRACE", [])[:config.max_traces]:
            try:
                # Parse trace (e.g., "upload → normalize → display")
                if '→' in trace_desc or '->' in trace_desc or ' to ' in trace_desc:
                    if '→' in trace_desc:
                        parts = trace_desc.split('→')
                    elif '->' in trace_desc:
                        parts = trace_desc.split('->')
                    else:
                        parts = trace_desc.split(' to ')
                    
                    if len(parts) >= 2:
                        start = parts[0].strip()
                        end = parts[-1].strip()
                        trace_results = self.code_explorer.trace_data_flow(start, end)
                        findings.extend([{"type": "trace", **r} for r in trace_results])
            except Exception as e:
                logger.warning(f"Trace failed for '{trace_desc}': {e}")
        
        # Find function calls
        for func_name in plan.get("FUNCTIONS", [])[:config.max_functions]:
            try:
                calls = self.code_explorer.find_function_calls(func_name)
                for call in calls:
                    findings.append({
                        "type": "function_call",
                        "file": call.get("file"),
                        "line": call.get("line"),
                        "context": call.get("context")
                    })
            except Exception as e:
                logger.warning(f"Function call search failed for '{func_name}': {e}")
        
        exploration_time = time.time() - exploration_start_time
        timed_out = exploration_time >= exploration_timeout
        
        # Store metadata for retrieval
        self._last_exploration_metadata = {
            "mode": "single_turn",
            "files_searched": files_searched,
            "files_read": files_read,  # No limit (local processing)
            "searches_executed": searches_executed,
            "search_terms": search_terms_used,  # No limit (local processing)
            "findings_count": len(findings),
            "exploration_time": round(exploration_time, 2),
            "timed_out": timed_out,
            "success": True,
            "model_used": getattr(self, 'model', None)
        }
        
        logger.info(
            f"Exploration completed in {exploration_time:.2f}s: "
            f"{len(findings)} findings, {searches_executed} searches, {files_searched} files read"
        )
        
        # Handle empty findings gracefully
        if not findings:
            # Safety check: total_actions might not be defined if early return occurred
            plan_actions_info = f"- Plan actions: {total_actions}\n" if 'total_actions' in locals() else ""
            helpful_msg = (
                f"[Exploration Mode] No code found matching: '{message}'\n\n"
                f"**Exploration Summary:**\n"
                f"- Searches executed: {searches_executed}\n"
                f"- Files checked: {files_searched}\n"
                f"- Time taken: {exploration_time:.2f}s\n"
                f"{plan_actions_info}\n"
                f"**Why this might happen:**\n"
                f"1. The code you're looking for might not exist\n"
                f"2. Search terms might be too vague or incorrect\n"
                f"3. Files might be in a different location than expected\n\n"
                f"**Suggestions:**\n"
                f"1. Try rephrasing with specific file/function names (e.g., 'in upload.ts')\n"
                f"2. Use more specific search terms related to the feature\n"
                f"3. Check if the feature exists in the codebase\n"
                f"4. Provide file paths if you know them\n"
                f"5. Try breaking down the question into smaller parts"
            )
            
            # Log metrics for empty findings
            try:
                metrics = get_metrics()
                request_id = str(uuid.uuid4())[:8]
                metrics.log_exploration(
                    request_id=request_id,
                    message=message,
                    findings_count=0,
                    searches_executed=searches_executed,
                    files_read=files_searched,
                    traces_executed=len(plan.get("TRACE", [])),
                    exploration_time=exploration_time,
                    success=False,
                    timeout=timed_out
                )
            except Exception as e:
                logger.warning(f"Failed to log exploration metrics: {e}")
            
            return helpful_msg
        
        # Log exploration metrics (success case)
        try:
            metrics = get_metrics()
            request_id = str(uuid.uuid4())[:8]
            metrics.log_exploration(
                request_id=request_id,
                message=message,
                findings_count=len(findings),
                searches_executed=searches_executed,
                files_read=files_searched,
                traces_executed=len(plan.get("TRACE", [])),
                exploration_time=exploration_time,
                success=True,
                timeout=timed_out
            )
        except Exception as e:
            logger.warning(f"Failed to log exploration metrics: {e}")
        
        if progress_callback:
            progress_callback(f"Processing {len(findings)} findings...", 2, 4)
        
        # Deduplicate findings
        findings = self._deduplicate_findings(findings)
        logger.info(f"After deduplication: {len(findings)} findings")
        
        # Truncate findings by count first (max_findings = 300)
        if len(findings) > config.max_findings:
            logger.info(f"Truncating findings from {len(findings)} to {config.max_findings} by count")
            # Sort by priority before truncating
            type_priority = {"file": 4, "trace": 3, "search": 2, "function_call": 2, "grep": 1, "unknown": 0}
            findings.sort(key=lambda f: (-type_priority.get(f.get("type", "unknown"), 0), -f.get("score", 0)))
            findings = findings[:config.max_findings]
        
        # Then truncate by tokens if limit is set (disabled for local processing)
        if config.max_findings_tokens > 0:
            findings = self._truncate_findings(findings, max_tokens=config.max_findings_tokens)
        else:
            findings = self._truncate_findings(findings, max_tokens=None)  # No limit
        logger.info(f"After truncation: {len(findings)} findings")
        
        if progress_callback:
            progress_callback("Analyzing findings with LLM...", 3, 4)
        
        # Step 3: Analyze findings with LLM
        findings_text = self._format_findings(findings, message, files_read_tracker)
        
        if progress_callback:
            progress_callback("Generating response...", 4, 4)
        
        # Update exploration session with response after analysis
        if hasattr(self, '_last_exploration_session_id'):
            try:
                from backend.services.exploration_history import save_exploration_session
                save_exploration_session(
                    session_id=self._last_exploration_session_id,
                    user_message=message,
                    response_text=None,  # Will update after we get response
                    exploration_metadata=self._last_exploration_metadata,
                    findings=findings,
                    request_id=getattr(self, '_current_request_id', None)
                )
            except Exception as e:
                logger.warning(f"Failed to update exploration session: {e}")
        
        # Search mode: Information gathering and summary (not problem-solving)
        summary_prompt = f"""You are a code information gatherer. The user asked: "{message}"

You have collected comprehensive information from the codebase:

{findings_text}

Your task is to organize and summarize what you found. Focus on INFORMATION, but make it ACTIONABLE and COMPLETE.

CRITICAL REQUIREMENTS:
1. **COMPLETENESS**: If the query asks for "all" of something (endpoints, functions, files), you MUST list EVERYTHING found. Don't miss any items.
2. **ACCURACY**: Verify file paths and line numbers match the actual findings. Don't make up locations.
3. **ACTIONABILITY**: For each item, explain what it does and where it's used, not just that it exists.
4. **ORGANIZATION**: Group related items together (e.g., all upload endpoints, all database functions).

Provide a comprehensive summary:

1. **Information Overview**: What did you find related to the user's query? Be specific about counts and completeness.
2. **Complete List**: If asking for "all" items, provide a COMPLETE numbered list with file:line references.
3. **Files Discovered**: List all relevant files with brief descriptions and what they contain.
4. **Key Components**: What functions, classes, or modules are involved? Include their exact locations.
5. **Data Flows**: How does data move through the system (if relevant)? Show the complete path.
6. **Code Locations**: Where is the relevant code located (file:line references)? Be precise.
7. **Usage Context**: How are these components used? What calls them? What do they call?
8. **Runtime Verification Points**: Where would you check logs/database/API to verify behavior? Be specific.

Format:
**Summary**
[Brief overview with counts: "Found X endpoints, Y functions, Z files"]

**Complete List** (if query asks for "all")
1. `endpoint_name` - `file.py:123` - [description]
2. `endpoint_name` - `file.py:456` - [description]
...

**Files Discovered**
- `file1.ts` (lines X-Y): [description of what it contains]
- `file2.py` (lines A-B): [description of what it contains]

**Key Components**
- Function/Class names with exact locations and purposes
- Include what calls them and what they call

**Code Snippets** (3-5 lines max per snippet, with file:line references)
[Small snippets to illustrate key points - only from actual findings]

**Execution Path** (if relevant)
[How data flows: file1.py:123 → file2.ts:456 → file3.py:789]

**Usage Context**
[How components are used, what depends on them, integration points]

**Runtime Verification Points**
[Specific commands/queries to verify: "Run: curl http://localhost:5177/api/upload", "Check logs for '[UPLOAD]' messages"]

**Additional Information**
[Any other relevant details found]

Remember: 
- Be COMPLETE - if asked for "all", list everything found
- Be ACCURATE - verify file paths and line numbers from findings
- Be ACTIONABLE - explain what each item does and how to use/verify it
- Be ORGANIZED - group related items together"""
        
        # Get summary from LLM
        try:
            summary = self._call_ollama_simple(summary_prompt, temperature=0.2)
            logger.info("Search mode summary completed")
            
            if progress_callback:
                progress_callback("Summary complete!", 4, 4)
            
            # Add search mode indicator
            summary = f"[Search Mode] {summary}"
            
            # Update exploration session with final response
            if hasattr(self, '_last_exploration_session_id'):
                try:
                    save_exploration_session(
                        session_id=self._last_exploration_session_id,
                        user_message=message,
                        response_text=summary,
                        exploration_metadata=self._last_exploration_metadata,
                        findings=findings,
                        request_id=getattr(self, '_current_request_id', None)
                    )
                except Exception as e:
                    logger.warning(f"Failed to update exploration session with response: {e}")
            
            return summary
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            logger.error(f"Agent analysis failed: {e}\n{error_trace}")
            # Fallback to formatted findings with better error message
            error_type = type(e).__name__
            is_timeout = "timeout" in str(e).lower() or "timed out" in str(e).lower()
            is_connection = "connection" in str(e).lower() or "connect" in str(e).lower()
            
            if is_timeout:
                error_context = (
                    "**Error Type:** Request Timeout\n"
                    "**Issue:** LLM took too long to analyze the findings.\n"
                    "**Possible Causes:**\n"
                    "- Too many findings to process\n"
                    "- LLM model is slow or overloaded\n"
                    "- Network latency\n\n"
                )
            elif is_connection:
                error_context = (
                    "**Error Type:** Connection Error\n"
                    "**Issue:** Cannot connect to Ollama service.\n"
                    "**Possible Causes:**\n"
                    "- Ollama is not running\n"
                    "- Network connectivity issues\n"
                    "- Ollama service crashed\n\n"
                )
            else:
                error_context = (
                    f"**Error Type:** {error_type}\n"
                    f"**Issue:** LLM analysis encountered an error.\n"
                    f"**Error Details:** {str(e)}\n\n"
                )
            
            error_msg = (
                f"[Exploration Mode] Exploration completed but LLM analysis failed.\n\n"
                f"{error_context}"
                f"**Recovery Actions:**\n"
                f"1. Review the findings below manually\n"
                f"2. Try rephrasing your question\n"
                f"3. Check Ollama service status\n"
                f"4. Retry the request\n\n"
                f"**Exploration Results:**\n"
                f"- Found {len(findings)} relevant code sections\n"
                f"- Searched {searches_executed} terms\n"
                f"- Read {files_searched} files\n\n"
                f"**Findings:**\n{findings_text}"
            )
            return error_msg
    
    def _call_ollama_simple(self, prompt: str, temperature: float = 0.7) -> str:
        """
        Simple LLM call without full conversation context.
        Used for exploration planning and analysis.
        
        Args:
            prompt: Prompt to send
            temperature: Temperature for generation
            
        Returns:
            LLM response text
        """
        if not self.ollama_available:
            raise Exception("Ollama not available")
        
        messages = [{"role": "user", "content": prompt}]
        
        def make_request():
            response = requests.post(
                f"{self.ollama_url}/api/chat",
                json={
                    "model": self.model,
                    "messages": messages,
                    "stream": False,
                    "options": {
                        "temperature": temperature,
                        "num_predict": -1,  # -1 = unlimited output (local processing)
                        "num_ctx": 8000,
                    }
                },
                timeout=60
            )
            
            if response.status_code != 200:
                raise Exception(f"Ollama API returned status {response.status_code}")
            
            result = response.json()
            return result.get("message", {}).get("content", "")
        
        # Use retry handler with circuit breaker
        config = get_config()
        try:
            return self.retry_handler.retry_with_backoff(
                make_request,
                max_retries=config.max_retries,
                initial_delay=config.retry_initial_delay,
                max_delay=config.retry_max_delay,
                retry_on=(requests.exceptions.Timeout, requests.exceptions.ConnectionError, Exception),
                circuit_breaker_key="ollama_api"
            )
        except Exception as e:
            logger.error(f"Simple Ollama call failed after retries: {e}")
            raise
    
    def _execute_with_timeout(self, func, timeout, default_return, *args, **kwargs):
        """
        Execute a function with timeout protection.
        
        Args:
            func: Function to execute
            timeout: Timeout in seconds
            default_return: Value to return if timeout or error
            *args, **kwargs: Arguments to pass to func
            
        Returns:
            Result of func or default_return if timeout/error
        """
        try:
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(func, *args, **kwargs)
                return future.result(timeout=timeout)
        except (FutureTimeoutError, TimeoutError):
            logger.warning(f"{func.__name__} timed out after {timeout}s, using default")
            return default_return
        except Exception as e:
            logger.error(f"{func.__name__} failed: {e}, using default")
            return default_return
    
    def _calculate_agent_timeout(
        self,
        context_size: Optional[int],
        files_read: int,
        turns: int,
        max_turns: int
    ) -> Tuple[int, int]:
        """
        Calculate adaptive timeout based on context size and progress.
        TIMEOUTS DISABLED: Returns very high values to effectively disable timeouts.
        
        Returns:
            Tuple of (overall_timeout, per_turn_timeout) in seconds
        """
        # TIMEOUTS DISABLED: Set to very high values (effectively infinite)
        timeout = 999999  # Effectively no timeout
        per_turn_timeout = 999999  # Effectively no per-turn timeout
        
        logger.info(f"_calculate_agent_timeout called with context_size={context_size}, files_read={files_read}, turns={turns} - TIMEOUTS DISABLED")
        logger.info(f"_calculate_agent_timeout returning timeout={timeout}s (effectively infinite)")
        
        return timeout, per_turn_timeout
    
    def _optimize_conversation_context(
        self,
        conversation_context: List[Dict[str, str]],
        files_read_tracker: set,
        key_insights: List[str]
    ) -> List[Dict[str, str]]:
        """
        Optimize conversation context by keeping recent messages and summarizing if needed.
        
        Args:
            conversation_context: List of message dicts with 'role' and 'content'
            files_read_tracker: Set of files that have been read
            key_insights: List of key insights discovered during analysis
            
        Returns:
            Optimized list of message dicts
        """
        if not conversation_context:
            return []
        
        # Keep last 12 messages (6 user-assistant pairs) to maintain recent context
        # This prevents context from growing unbounded while keeping recent conversation
        MAX_RECENT_MESSAGES = 12
        
        if len(conversation_context) <= MAX_RECENT_MESSAGES:
            # Conversation is short enough, return as-is
            return conversation_context
        
        # Conversation is long, keep only recent messages
        optimized = conversation_context[-MAX_RECENT_MESSAGES:]
        
        # Optionally add a summary of older messages if we have key insights
        # Limit key_insights to prevent unbounded growth
        MAX_KEY_INSIGHTS = 50
        if len(key_insights) > MAX_KEY_INSIGHTS:
            key_insights = key_insights[-MAX_KEY_INSIGHTS:]
        
        if key_insights and len(conversation_context) > MAX_RECENT_MESSAGES:
            # Add a brief summary of what was discussed earlier
            summary = "**Previous conversation summary:**\n"
            summary += f"- Files analyzed: {len(files_read_tracker)}\n"
            if key_insights:
                summary += f"- Key findings: {', '.join(key_insights[-3:])}\n"
            summary += "\n[Earlier messages truncated to save context. Continuing with recent conversation...]"
            
            # Insert summary as a system message at the start of optimized context
            optimized.insert(0, {
                "role": "system",
                "content": summary
            })
        
        return optimized
    
    def _extract_insights_from_results(
        self,
        results: List[Dict],
        files_read_tracker: set
    ) -> List[str]:
        """
        Extract key insights from command execution results.
        
        Args:
            results: List of result dicts from command execution
            files_read_tracker: Set of files that have been read
            
        Returns:
            List of insight strings
        """
        insights = []
        
        if not results:
            return insights
        
        # Extract insights from different result types
        for result in results:
            result_type = result.get("type", "")
            
            # Insights from READ results
            if result_type == "read" and result.get("file"):
                file_path = result.get("file")
                # Note important files that were read
                if file_path not in files_read_tracker:
                    continue  # Skip if not actually read yet
                
                # Extract function/class definitions from content
                content = result.get("content", "")
                if content:
                    # Look for function definitions
                    func_matches = re.findall(r'def\s+(\w+)\s*\(', content)
                    if func_matches:
                        func_list = ', '.join(func_matches[:5])  # Limit to 5
                        insights.append(f"Found functions in {file_path}: {func_list}")
                    
                    # Look for class definitions
                    class_matches = re.findall(r'class\s+(\w+)', content)
                    if class_matches:
                        class_list = ', '.join(class_matches[:3])  # Limit to 3
                        insights.append(f"Found classes in {file_path}: {class_list}")
            
            # Insights from SEARCH results
            elif result_type == "search" and result.get("file"):
                file_path = result.get("file")
                match = result.get("match", "")
                if match and len(match) < 100:  # Only short matches
                    # Extract key terms
                    if any(keyword in match.lower() for keyword in ["def ", "class ", "import ", "from "]):
                        insights.append(f"Found code pattern in {file_path}: {match[:80]}")
            
            # Insights from GREP results
            elif result_type == "grep" and result.get("file"):
                file_path = result.get("file")
                matches = result.get("matches", [])
                if matches:
                    # Extract unique patterns
                    unique_patterns = set()
                    for match in matches[:5]:  # Limit to 5 matches
                        line = match.get("line", "")
                        if line and len(line) < 100:
                            unique_patterns.add(line[:80])
                    if unique_patterns:
                        pattern_str = ', '.join(list(unique_patterns)[:3])
                        insights.append(f"Found patterns in {file_path}: {pattern_str}")
            
            # Insights from errors
            elif result_type == "error":
                error_msg = result.get("error", "")
                if error_msg:
                    # Extract meaningful error insights
                    if "not found" in error_msg.lower() or "does not exist" in error_msg.lower():
                        file_path = result.get("file", "unknown")
                        insights.append(f"File/function not found: {file_path} - may need different search")
        
        # Deduplicate insights
        unique_insights = []
        seen = set()
        for insight in insights:
            if insight not in seen:
                seen.add(insight)
                unique_insights.append(insight)
        
        # Limit to most important insights (max 5)
        return unique_insights[:5]
    
    def _generate_smart_suggestions(
        self,
        message: str,
        files_read_tracker: set,
        results: List[Dict],
        discovered_files: set,
        commands_history: List[str]
    ) -> str:
        """
        Generate smart suggestions for agent exploration based on current state.
        
        Args:
            message: Original user message
            files_read_tracker: Set of files that have been read
            results: List of results from previous commands
            discovered_files: Set of files discovered but not yet read
            commands_history: History of commands used
            
        Returns:
            String with smart suggestions
        """
        suggestions = []
        message_lower = message.lower()
        
        # Suggest reading discovered files if any
        if discovered_files:
            unread_discovered = [f for f in discovered_files if f not in files_read_tracker]
            if unread_discovered:
                # Suggest top 3 discovered files
                for file_path in list(unread_discovered)[:3]:
                    suggestions.append(f"- READ {file_path}")
        
        # Analyze message to suggest relevant searches
        if "upload" in message_lower:
            if not any("upload" in cmd.lower() for cmd in commands_history):
                suggestions.append("- SEARCH upload")
                suggestions.append("- GREP def.*upload|@app\\.(post|get).*upload")
        
        if "line item" in message_lower or "lineitem" in message_lower:
            if not any("line" in cmd.lower() for cmd in commands_history):
                suggestions.append("- SEARCH line items")
                suggestions.append("- GREP line_item|lineitem")
        
        if "card" in message_lower or "display" in message_lower or "show" in message_lower:
            if not any("card" in cmd.lower() or "display" in cmd.lower() for cmd in commands_history):
                suggestions.append("- SEARCH card display")
                suggestions.append("- SEARCH frontend components")
        
        if "data" in message_lower and ("not" in message_lower or "missing" in message_lower or "empty" in message_lower):
            # Suggest tracing data flow
            if not any("trace" in cmd.lower() for cmd in commands_history):
                suggestions.append("- TRACE upload → database")
                suggestions.append("- TRACE database → display")
        
        # Suggest reading files from results if any
        if results:
            result_files = set()
            for result in results:
                file_path = result.get("file")
                if file_path and file_path not in files_read_tracker:
                    result_files.add(file_path)
            
            if result_files:
                for file_path in list(result_files)[:2]:  # Top 2 files
                    suggestions.append(f"- READ {file_path}")
        
        # If no files read yet, suggest starting with common files
        if not files_read_tracker:
            if "upload" in message_lower:
                suggestions.append("- READ backend/main.py")
                suggestions.append("- SEARCH upload endpoint")
            elif "display" in message_lower or "card" in message_lower:
                suggestions.append("- SEARCH frontend components")
                suggestions.append("- SEARCH card display")
            else:
                suggestions.append("- SEARCH " + message.split()[0] if message.split() else "relevant code")
        
        # If we have files read but no results, suggest grepping for functions
        if files_read_tracker and not results:
            # Extract potential function names from message
            words = message.split()
            for word in words:
                if word.isalnum() and len(word) > 3:
                    # Check if it might be a function name
                    if not any(word.lower() in cmd.lower() for cmd in commands_history):
                        suggestions.append(f"- GREP {word}")
                        break  # Only suggest one
        
        # Format suggestions
        if suggestions:
            return "\n\n💡 Smart suggestions:\n" + "\n".join(suggestions[:5])  # Limit to 5 suggestions
        
        return ""
    
    def _execute_single_read_command(self, cmd, file_cache, file_relationships, discovered_files, files_read_tracker, turn_num, max_cache_size):
        """Execute a single READ command."""
        try:
            file_path = cmd.get("file")
            if not file_path:
                return [{"type": "error", "command": cmd, "error": "READ command missing 'file' field"}]
            
            # Check if file is already in cache
            if file_path in file_cache:
                file_data = file_cache[file_path]
                files_read_tracker.add(file_path)
                return [{"type": "read", "file": file_path, "content": file_data.get("content", ""), "lines_read": file_data.get("lines_read", 0), "total_lines": file_data.get("total_lines", 0)}]
            
            # Read file
            file_data = self.code_reader.read_file(file_path, max_lines=config.max_lines_per_file)
            if file_data.get("success"):
                content = file_data.get("content", "")
                lines_read = file_data.get("lines_read", 0)
                total_lines = file_data.get("total_lines", 0)
                
                # Cache file (with size limit)
                if len(file_cache) < max_cache_size:
                    file_cache[file_path] = file_data
                elif file_path not in file_cache:
                    # Remove oldest entry if cache is full
                    oldest = next(iter(file_cache))
                    del file_cache[oldest]
                    file_cache[file_path] = file_data
                
                files_read_tracker.add(file_path)
                discovered_files.add(file_path)
                
                return [{"type": "read", "file": file_path, "content": content, "lines_read": lines_read, "total_lines": total_lines}]
            else:
                error_msg = file_data.get("error", "Unknown error")
                return [{"type": "error", "command": cmd, "error": f"Failed to read file '{file_path}': {error_msg}"}]
        except Exception as e:
            logger.warning(f"READ command failed: {e}")
            return [{"type": "error", "command": cmd, "error": str(e)}]
    
    def _execute_read_commands_parallel(self, read_commands, file_cache, file_relationships, discovered_files, files_read_tracker, turn_num, max_cache_size, cancellation_flag, agent_start_time, agent_timeout):
        """Execute multiple READ commands in parallel with cancellation support."""
        if not read_commands:
            return []
        
        results = []
        
        def execute_single_read(cmd):
            """Execute a single read command."""
            try:
                # Check cancellation before starting
                if cancellation_flag.is_set():
                    return {"type": "cancelled", "command": cmd}
                
                # TIMEOUTS DISABLED: Skip timeout check before read
                
                return self._execute_single_read_command(cmd, file_cache, file_relationships, discovered_files, files_read_tracker, turn_num, max_cache_size)
            except Exception as e:
                logger.warning(f"Parallel read failed: {e}")
                return [{"type": "error", "command": cmd, "error": str(e)}]
        
        # Execute reads in parallel (max 6 workers)
        max_workers = min(config.max_parallel_file_reads, len(read_commands), 6)
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_cmd = {executor.submit(execute_single_read, cmd): cmd for cmd in read_commands}
            for future in as_completed(future_to_cmd):
                # Check cancellation flag in loop
                if cancellation_flag.is_set():
                    break
                # TIMEOUTS DISABLED: Skip timeout check in loop
                
                try:
                    cmd_result = future.result()
                    if isinstance(cmd_result, list):
                        results.extend(cmd_result)
                    elif isinstance(cmd_result, dict):
                        results.append(cmd_result)
                except Exception as e:
                    cmd = future_to_cmd[future]
                    logger.warning(f"Error processing READ result: {e}")
                    results.append({"type": "error", "command": cmd, "error": str(e)})
        
        return results
    
    def _agent_mode_conversation(
        self,
        message: str,
        max_turns: Optional[int] = None,
        progress_callback: Optional[Callable[[str, int, int], None]] = None,
        context_size: Optional[int] = None,
        force_agent: bool = False
    ) -> str:
        """
        Agent mode: autonomous problem-solving conversation where LLM executes tasks sequentially.
        
        The agent breaks down problems into tasks, executes them one by one, analyzes results,
        and decides next steps until a solution is found.
        
        Args:
            message: Initial user question/problem
            max_turns: Maximum number of conversation turns
            
        Returns:
            Final analysis response
        """
        # Set agent mode flag for validation and other checks
        self._in_agent_mode = True
        config = get_config()
        max_turns = max_turns or config.max_conversation_turns or 10  # Default to 10 if both are None/0
        if max_turns <= 0:
            max_turns = 10  # Safety fallback
        logger.info(f"Starting Agent mode conversation (max {max_turns} turns)")
        
        # Define timeout constants at top of function for consistency
        TIMEOUT_FRAMEWORK_DETECTION = 2.0
        TIMEOUT_OPTIMIZE_CONTEXT = 5.0
        TIMEOUT_VERIFICATION = 10.0
        TIMEOUT_CONFIDENCE = 5.0
        TIMEOUT_SUGGESTIONS = 5.0
        TIMEOUT_FORMAT_FINDINGS = 10.0
        TIMEOUT_PARSE_COMMANDS = 2.0
        TIMEOUT_INIT_MAX = 15.0  # Increased from 10s to 15s for slower systems
        MAX_RESULTS_DURING_COLLECTION = 500  # Limit results during collection to prevent unbounded growth
        
        # Performance tracking
        # CRITICAL: Reset agent_start_time EARLY, before any blocking operations
        # This ensures all setup time counts against timeout correctly
        agent_start_time = time.time()
        build_plan_start = time.time()
        
        if progress_callback:
            progress_callback("Starting agent exploration...", 1, 4)
        
        explorer = self.code_explorer
        conversation_context = []
        
        # Auto-detect architecture from files that will likely be read
        # Use the same helper method as _build_prompt for consistency
        # CRITICAL: Make framework detection non-blocking with timeout to prevent blocking initialization
        code_context_for_detection = {"files": []}
        try:
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(self._get_framework_context, code_context_for_detection, message)
                architecture_context = future.result(timeout=TIMEOUT_FRAMEWORK_DETECTION)  # 2s max for framework detection
        except (FutureTimeoutError, Exception) as e:
            logger.warning(f"Framework detection timed out/failed: {e}, continuing without framework context")
            architecture_context = ""
        
        # Check timeout after framework detection (fail fast if initialization takes too long)
        elapsed = time.time() - agent_start_time
        # TIMEOUTS DISABLED: Skip initialization timeout check
        if False:  # Disabled timeout check
            logger.warning(f"Initialization took too long after framework detection: {elapsed:.1f}s")
            if progress_callback:
                try:
                    progress_callback(json.dumps({
                        "type": "error",
                        "message": "Agent initialization timeout. Please try again."
                    }), 4, 4)
                except Exception:
                    pass
            return "Agent initialization timeout. Please try again."
        
        # Log build_plan phase
        build_plan_ms = int((time.time() - build_plan_start) * 1000)
        self._log_perf_metric("build_plan", ms=build_plan_ms)
        
        # Fast first turn guard: if plan creation exceeds 3s, defer heavy searches
        if build_plan_ms > 3000:
            logger.warning(f"Plan creation took {build_plan_ms}ms (>3s), deferring heavy searches to next turn")
            if progress_callback:
                progress_callback("Plan created, starting with quick exploration...", 1, 4)
        
        # Initial system prompt for Agent mode (analysis and diagnosis focus)
        system_prompt = f"""You are an autonomous code analysis agent. Your task is to analyze: "{message}"{architecture_context}

YOUR MISSION: Find and diagnose problems by READING THE CODEBASE FIRST, then analyzing the code structure and data flow.

CRITICAL WORKFLOW - READ CODE FIRST:
1. READ THE CODEBASE - Use READ, GREP, SEARCH to understand actual implementation
2. VERIFY EXISTING CODE - Check what logging/functions already exist
3. TRACE ACTUAL EXECUTION PATH - Follow real code flow, not assumptions
4. IDENTIFY SPECIFIC ISSUES - Find mismatches, inconsistencies, bugs, missing methods
5. ANALYZE CODE STRUCTURE - Understand relationships, data flow, and potential problem areas
6. DIAGNOSE THE ROOT CAUSE - Based on actual code analysis, not generic suggestions

FOCUS: Your primary goal is ANALYSIS and DIAGNOSIS, not providing fixes. Focus on:
- Finding where problems occur (file:line references)
- Understanding why problems happen (root cause analysis)
- Identifying what's missing or broken (missing methods, mismatches, etc.)
- Analyzing large codebases to understand context and relationships

MANDATORY: READ CODE BEFORE SUGGESTING
Before making ANY suggestions, you MUST:
1. READ actual files mentioned in the problem
2. USE GREP to find function definitions and calls
3. USE SEARCH to understand relationships and data flow
4. CHECK what logging/functions already exist
5. TRACE the actual execution path through real code
6. IDENTIFY specific bugs (mismatches, wrong field names, etc.)

NEVER:
- Assume function signatures or names
- Suggest adding logging that might already exist
- Provide generic code examples that don't match the codebase
- Make suggestions without reading the actual code first

AVAILABLE COMMANDS (USE THESE FIRST):
- READ <file> - Read actual code files (DO THIS FIRST) - Can read entire files to understand large contexts
- GREP <pattern> - Find function definitions, calls, specific code patterns
- SEARCH <term> - Search codebase for concepts and relationships
- TRACE <start> → <end> - Trace data flow through actual code
- ANALYZE - Provide your analysis and diagnosis (ONLY after reading code)

MANDATORY FIRST STEPS:
1. READ the files mentioned in the problem (e.g., READ backend/services/ocr_service.py) - Read entire files to understand full context
2. GREP for function names to find actual definitions (e.g., GREP _is_vague_problem)
3. SEARCH for related code to understand the flow and relationships
4. TRACE the actual execution path through real code
5. CHECK what already exists (logging, functions, methods, etc.)
6. ANALYZE and DIAGNOSE the problem - identify what's missing, broken, or mismatched

CRITICAL RULES:
1. USE ACTUAL FILE PATHS AND LINE NUMBERS:
   - NEVER use generic names like "file.py:100" or "ocr.py:50"
   - ALWAYS use actual paths: "backend/main.py:561" or "backend/services/ocr_service.py:266"
   - Use real line numbers from the code you've read
   - If you don't know exact line numbers, read the file first

2. VERIFY RUNTIME BEHAVIOR FIRST - BE SPECIFIC:
   - Don't say: "Check backend logs"
   - Say: "Search logs for '[LINE_ITEMS]' messages and share: how many blocks, what types, any table blocks?"
   - Don't say: "Check if data is stored"
   - Say: "Run SQL: SELECT supplier, value, (SELECT COUNT(*) FROM invoice_line_items WHERE doc_id = invoices.doc_id) as items FROM invoices ORDER BY id DESC LIMIT 1;"
   - Don't say: "Check API response"
   - Say: "Run: curl http://localhost:8000/api/upload/status?doc_id=XXX and share the response"

3. PRIORITIZE BY LIKELIHOOD:
   - Don't list all possibilities equally
   - Rank by probability: "MOST LIKELY (90%): Table blocks not detected"
   - Then: "If that's not it (5%): Table extraction returns empty"
   - Then: "Least likely (5%): Format conversion fails"

4. PROVIDE EXACT LOGGING CODE:
   - Don't say: "Add logging to verify"
   - Say: "Add: logger.info(f'[TABLE_EXTRACT] Block type: {{ocr_result.type}}') at backend/ocr/owlin_scan_pipeline.py:704"
   - Include the exact code snippet, file path, and line number
   - Use actual variable names from the code

6. TRACE ACTUAL EXECUTION PATH (read code first):
   - READ the actual files to understand the flow
   - Follow: Upload → OCR → Extraction → Storage → API → Frontend
   - Use actual file paths from code you READ: "backend/main.py:561 → backend/services/ocr_service.py:266 → backend/app/db.py:323"
   - Map actual function calls, parameter passing (doc_id, invoice_id, etc.)
   - Check each step with specific queries/logs

7. IDENTIFY SPECIFIC ISSUES (based on actual code):
   - Look for mismatches: invoice_id vs doc_id, wrong field names
   - Check query logic vs insert logic (do they match?)
   - Verify database relationships (how tables connect)
   - Find inconsistencies in actual code, not assumptions

8. FOCUS ON PRIMARY ISSUES:
   - Primary: Why is data empty/missing? (the core problem)
   - Secondary: Error handling improvements (can wait)
   - Don't fix secondary issues while primary is unsolved

9. BE CONCRETE, NOT GENERIC (based on actual code):
   - Instead of: "improve logic to handle more cases"
   - Say: "In backend/services/ocr_service.py:611, add: logger.info(f'Block types found: {{[b.type for b in blocks]}}')" (after checking it doesn't exist)
   - Instead of: "Check if data exists"
   - Say: "Run: SELECT * FROM invoices WHERE id = (SELECT MAX(id) FROM invoices);"

RESPONSE FORMAT:
When you ANALYZE, provide in this EXACT format:

**Code Analysis** (based on actual code you READ):
- **Files Read**: List files you actually read (e.g., READ backend/services/ocr_service.py)
- **Functions Found**: Actual function names from code (e.g., extract_table_from_block, not extract_table)
- **Existing Logging**: What logging already exists (from GREP results)
- **Execution Path**: Actual code flow from files you READ

**Prioritized Diagnosis (by likelihood):**

1. **MOST LIKELY (90%): [Issue name]**
   - **Check**: `backend/path/to/file.py:123-145` (actual file path from code you READ)
   - **Existing Code**: Quote actual code snippet from file (3-5 lines)
   - **Issue Found**: Specific bug/mismatch identified (e.g., "invoice_id = doc_id but query uses invoice_id")
   - **Add logging** (if doesn't exist): `logger.info(f'[TAG] Message: {{variable}}')` at `backend/path/to/file.py:130` (exact code with real variable names from actual code)
   - **Verify**: "Search logs for '[TAG]' messages and share: [specific data points]" (exact log search)
   - **If not this**: Move to next item

2. **If that's not it (5%): [Issue name]**
   - **Check**: `backend/path/to/file.py:200-220` (actual path from code you READ)
   - **Existing Code**: Quote actual code snippet
   - **Issue Found**: Specific bug identified
   - **Add logging** (if doesn't exist): `logger.info(f'[TAG2] Data: {{variable}}')` at `backend/path/to/file.py:210` (exact code)
   - **Verify**: "Run SQL: SELECT ... FROM ... WHERE ...;" (exact query)

3. **Least likely (5%): [Issue name]**
   - **Check**: `backend/path/to/file.py:300-320` (actual path)
   - **Verify**: "Run: curl http://localhost:8000/api/endpoint?param=value" (exact command)

**Execution Path** (actual file paths from code you READ):
`backend/main.py:561` (actual function name) → `backend/services/ocr_service.py:266` (actual function name) → `backend/app/db.py:323` (actual function name)

**Root Cause**: [Based on actual code analysis, not assumptions - e.g., "Missing method _is_vague_problem in ChatService class at backend/services/chat_service.py:4307"]

**Analysis Summary**:
- **What's Missing**: [List missing methods, functions, imports, etc. found in code]
- **What's Broken**: [List mismatches, wrong references, incorrect logic found in code]
- **Where It Occurs**: [Specific file:line references from code you READ]
- **Why It Happens**: [Root cause explanation based on code analysis]

CRITICAL: 
1. READ actual code files FIRST before making analysis - read entire files to understand full context
2. Use GREP to check what already exists (methods, functions, imports)
3. Use ACTUAL file paths, function names, and line numbers from code you READ
4. Identify SPECIFIC issues (missing methods, mismatches, wrong field names, etc.) from actual code
5. FOCUS ON ANALYSIS AND DIAGNOSIS - identify problems, not provide fixes
6. ANALYZE LARGE CONTEXTS - read entire files to understand relationships and data flow

Start by READING the codebase files related to the problem."""
        
        user_message = message
        turns = 0
        files_read_tracker = set()  # Track which files have been read
        commands_history = []  # Track all commands used
        discovered_files = set()  # Files discovered from searches but not yet read
        tools_used = False  # Track if any tools have been used
        key_insights = []  # Track key insights learned
        
        # Implement LRU cache for file_cache to prevent unbounded memory growth
        from collections import OrderedDict
        
        class LRUCache:
            def __init__(self, max_size=50):
                self.cache = OrderedDict()
                self.max_size = max_size
                self.hits = 0
                self.misses = 0
            
            def get(self, key):
                if key in self.cache:
                    self.cache.move_to_end(key)
                    self.hits += 1
                    return self.cache[key]
                self.misses += 1
                return None
            
            def put(self, key, value):
                if key in self.cache:
                    self.cache.move_to_end(key)
                self.cache[key] = value
                if len(self.cache) > self.max_size:
                    self.cache.popitem(last=False)
            
            def __contains__(self, key):
                return key in self.cache
            
            def __len__(self):
                return len(self.cache)
            
            def keys(self):
                return self.cache.keys()
            
            def get_stats(self):
                """Get cache statistics."""
                total = self.hits + self.misses
                hit_rate = (self.hits / total * 100) if total > 0 else 0.0
                return {
                    "hits": self.hits,
                    "misses": self.misses,
                    "hit_rate": hit_rate,
                    "size": len(self.cache),
                    "max_size": self.max_size
                }
        
        file_cache = LRUCache(max_size=config.file_cache_size)  # Use LRU cache with config value
        file_relationships = {}  # Track relationships between files
        task_tracker = TaskTracker()  # Track agent tasks with status and timing
        
        # Cumulative limits tracking across all turns
        cumulative_file_reads = 0
        cumulative_searches = 0
        cumulative_traces = 0
        cumulative_greps = 0
        cumulative_error_count = 0  # Track total errors across turns
        cumulative_permanent_error_count = 0  # Track permanent errors across turns
        MAX_CUMULATIVE_FILE_READS = config.max_files_per_plan * 2  # Allow 2x per-turn limit across all turns
        MAX_CUMULATIVE_SEARCHES = config.max_search_results * 3  # Allow 3x per-turn limit
        MAX_CUMULATIVE_TRACES = config.max_traces * 2  # Allow 2x per-turn limit
        MAX_CUMULATIVE_GREPS = 50  # Reasonable limit for grep operations
        
        # Emit initial plan event with planning task (will be updated when real tasks are built)
        if progress_callback:
            try:
                progress_callback(json.dumps({
                    "type": "plan",
                    "tasks": [{
                        "id": "planning",
                        "title": "📋 Planning tasks...",
                        "type": "ANALYZE",
                        "status": "running"
                    }]
                }), 1, 4)
            except Exception as e:
                logger.debug(f"Progress callback failed: {e}")
                pass
        
        # Limits to prevent unbounded growth
        MAX_FILE_CACHE_SIZE = 50
        MAX_DISCOVERED_FILES = 100
        MAX_COMMANDS_HISTORY = 200
        
        # Track consecutive invalid command attempts to prevent infinite loops
        consecutive_invalid_commands = 0
        MAX_CONSECUTIVE_INVALID = 3
        
        # Check if problem description is vague and ask clarifying questions
        # Note: _is_vague_problem and _generate_clarifying_questions methods removed
        # Agent should proceed with analysis even if problem is vague
        
        # Use original context size for timeout calculation (don't cap for timeout purposes)
        # The LLM will use the full context, so timeout should match
        original_context = context_size or 128000  # Default to 128k if not specified
        effective_context = min(original_context, 128000)  # Cap at 128k max for LLM processing
        logger.info(f"Agent mode context: original={context_size}, effective={effective_context} (using original for timeout calculation)")
        
        # Calculate adaptive timeout based on ORIGINAL context size (not capped)
        # This ensures timeout matches the actual context capability, allowing more time for larger contexts
        agent_timeout, per_turn_timeout = self._calculate_agent_timeout(
            context_size=original_context,  # Use original context size for timeout calculation
            files_read=0,  # Will update as we go
            turns=0,
            max_turns=max_turns
        )
        # TIMEOUTS DISABLED: No timeout capping
        logger.info(f"Agent mode timeout set to {agent_timeout/60:.1f} minutes ({agent_timeout}s) - TIMEOUTS DISABLED (context_size: {effective_context}, per_turn: {per_turn_timeout}s)")
        
        # Emit early progress event for fast first turn
        if progress_callback:
            try:
                progress_callback(json.dumps({
                    "type": "agent_started",
                    "max_turns": max_turns,
                    "timeout_seconds": int(agent_timeout),
                    "message": message[:100]  # Include question preview
                }), 1, 4)
                # Also emit a plan event with empty tasks to show "Planning..." state
                progress_callback(json.dumps({
                    "type": "plan",
                    "tasks": [{
                        "id": "planning",
                        "title": "Planning tasks...",
                        "type": "ANALYZE",
                        "status": "running"
                    }]
                }), 1, 4)
            except Exception as e:
                logger.debug(f"Progress callback failed: {e}")
                pass
        
        # Note: agent_start_time was reset earlier (line 4426) before any blocking operations
        # The heartbeat loop will use the same reset value via nonlocal
        logger.info(f"Agent mode starting (timeout: {agent_timeout/60:.1f} minutes, context_size: {effective_context}, original_context_size: {context_size})")
        
        # Heartbeat and watchdog setup
        heartbeat_active = threading.Event()
        heartbeat_active.set()  # Start active
        # Add cancellation flag for in-flight operations
        cancellation_flag = threading.Event()
        last_task_update_time = time.time()
        phase_counters = {"reads": {"current": 0, "total": 0}, "greps": {"current": 0, "total": 0}, 
                         "searches": {"current": 0, "total": 0}, "traces": {"current": 0, "total": 0}}
        
        def heartbeat_loop():
            """Emit heartbeat every 2s and watchdog check."""
            nonlocal agent_start_time, agent_timeout, cancellation_flag  # Must declare as nonlocal to see reset value and timeout
            while heartbeat_active.is_set():
                try:
                    current_time = time.time()
                    
                    # Check for timeout in heartbeat loop (catches hangs even if main loop is blocked)
                    elapsed_time = current_time - agent_start_time
                    # Debug logging for timeout issues
                    # TIMEOUTS DISABLED: Skip timeout check in heartbeat loop
                    # if elapsed_time > agent_timeout:
                    #     heartbeat_active.clear()
                    #     if progress_callback:
                    #         try:
                    #             progress_callback(json.dumps({
                    #                 "type": "error",
                    #                 "message": f"Agent mode timed out after {elapsed_time/60:.1f} minutes. Please try again or use a more specific question."
                    #             }), 4, 4)
                    #         except Exception as e:
                    #             logger.debug(f"Progress callback failed: {e}")
                    #             pass
                    #     break
                    
                    # Emit heartbeat
                    if progress_callback:
                        try:
                            progress_callback(json.dumps({
                                "type": "heartbeat",
                                "ts": int(current_time * 1000)
                            }), 2, 4)
                        except Exception as e:
                            logger.debug(f"Progress callback failed: {e}")
                            pass
                    
                    # Watchdog: if no task_update for 10s, emit heartbeat + progress dump
                    if current_time - last_task_update_time > 10:
                        if progress_callback:
                            try:
                                # Emit progress dump
                                for phase, counters in phase_counters.items():
                                    if counters["total"] > 0:
                                        progress_callback(json.dumps({
                                            "type": "progress",
                                            "phase": phase,
                                            "current": counters["current"],
                                            "total": counters["total"],
                                            "percentage": int((counters["current"] / counters["total"]) * 100) if counters["total"] > 0 else 0
                                        }), 2, 4)
                            except Exception as e:
                                logger.debug(f"Progress callback failed: {e}")
                                pass
                    
                    # Sleep for 2 seconds (use time.sleep to ensure consistent 2s interval)
                    time.sleep(2.0)
                    # Check if we should continue (event might have been cleared)
                    if not heartbeat_active.is_set():
                        break
                except Exception as e:
                    logger.warning(f"Heartbeat loop error: {e}")
                    break
        
        # Start heartbeat thread
        heartbeat_thread = threading.Thread(target=heartbeat_loop, daemon=True)
        heartbeat_thread.start()
        
        def _do_one_turn(turn_num):
            """
            Execute one turn of the agent loop.
            Returns: {"exit": bool, "skip": bool, "result": str|None}
            - exit=True: exit the main loop (equivalent to break)
            - skip=True: skip incrementing turn counter (equivalent to continue)
            - result: if exit=True, this contains the final result string (for timeouts/errors)
            """
            # CRITICAL: Declare nonlocal variables FIRST, before any use
            nonlocal agent_timeout, per_turn_timeout, user_message, commands_history, tools_used, discovered_files
            nonlocal cumulative_file_reads, cumulative_searches, cumulative_traces, cumulative_greps
            nonlocal agent_start_time, cancellation_flag  # Must be nonlocal to see the reset value and cancellation flag
            nonlocal cumulative_error_count, cumulative_permanent_error_count  # Track errors across turns
            nonlocal config  # Access config from outer scope for retry logic
            nonlocal conversation_context  # Access conversation context from outer scope
            nonlocal key_insights  # Access key insights from outer scope
            
            # TIMEOUTS DISABLED: Skip timeout check at start of turn
            elapsed_time = time.time() - agent_start_time
            # Timeout check removed - agent will run indefinitely
            
            # Now safe to log and access variables
            logger.info(f"Starting turn {turn_num + 1} (elapsed: {elapsed_time:.1f}s)")
            # Recalculate timeout if we've made progress (files_read updated)
            if len(files_read_tracker) >= 3 and turn_num < 5:
                agent_timeout, per_turn_timeout = self._calculate_agent_timeout(
                    context_size=effective_context,  # Use capped context size, not original
                    files_read=len(files_read_tracker),
                    turns=turn_num,
                    max_turns=max_turns
                )
            # Track turn start time for per-turn timeout (will check after operations that take time)
            turn_start_time = time.time()
            # Send time remaining update
            time_remaining = agent_timeout - elapsed_time
            if progress_callback and time_remaining > 0:
                minutes = int(time_remaining // 60)
                seconds = int(time_remaining % 60)
                formatted_time = f"{minutes}m {seconds}s" if minutes > 0 else f"{seconds}s"
                try:
                    import json
                    progress_callback(json.dumps({
                        "type": "time_remaining",
                        "seconds": int(time_remaining),
                        "formatted": formatted_time
                    }), 2, 4)
                except Exception as e:
                    logger.debug(f"Progress callback failed: {e}")
                    pass  # Fallback to regular callback if JSON fails
            # TIMEOUTS DISABLED: Skip timeout warning
            # Build messages for this turn
            if progress_callback:
                progress_callback(f"Agent turn {turn_num + 1}/{max_turns}...", 2, 4)
                progress_callback(f"🤔 Agent is thinking about the problem...", 2, 4)
                # Emit heartbeat to show agent is alive
                try:
                    progress_callback(json.dumps({
                        "type": "heartbeat",
                        "ts": int(time.time() * 1000),
                        "turn": turn_num + 1,
                        "max_turns": max_turns
                    }), 2, 4)
                except Exception as e:
                    logger.debug(f"Progress callback failed: {e}")
                    pass
            # TIMEOUTS DISABLED: Skip timeout check before LLM call
            elapsed_time = time.time() - agent_start_time
            # Build messages for this turn
            elapsed_before_build = time.time() - agent_start_time
            logger.info(f"Building messages for turn {turn_num + 1} (elapsed: {elapsed_before_build:.1f}s, remaining: {agent_timeout - elapsed_before_build:.1f}s)")
            messages = [{"role": "system", "content": system_prompt}]
            # Optimize context: summarize old turns if conversation is getting long
            # Skip optimization if we're running low on time to save time for LLM call
            default_context = conversation_context[-12:] if len(conversation_context) > 12 else conversation_context
            # For first turn, skip optimization entirely to speed up initialization
            # For later turns, skip if we've used too much time
            # TIMEOUTS DISABLED: Always optimize context (no timeout check)
            if False:  # Disabled timeout check
                if turn_num == 0:
                    logger.info(f"Skipping context optimization for first turn to speed up initialization")
                else:
                    logger.warning(f"Skipping context optimization to save time: {elapsed_before_build:.1f}s/{agent_timeout}s ({elapsed_before_build/agent_timeout*100:.1f}%)")
                optimized_context = default_context  # Skip optimization, use default
            else:
                # Use shorter timeout for optimization
                optimize_timeout = TIMEOUT_OPTIMIZE_CONTEXT
                optimized_context = self._execute_with_timeout(
                    self._optimize_conversation_context,
                    optimize_timeout,
                    default_context,
                    conversation_context,
                    files_read_tracker,
                    key_insights
                )
            elapsed_after_optimize = time.time() - agent_start_time
            logger.info(f"After context optimization: elapsed={elapsed_after_optimize:.1f}s, remaining={agent_timeout - elapsed_after_optimize:.1f}s")
            # Check timeout after context optimization (fail fast if setup takes too long)
            # Skip this check entirely for first turn (turn_num == 0) - initialization can take time
            # TIMEOUTS DISABLED: Skip timeout check after context optimization
            messages.extend(optimized_context)
            messages.append({"role": "user", "content": user_message})
            # LLM responds with command or analysis
            # Check Ollama availability before making LLM call
            if not self.ollama_available:
                logger.error("Ollama is not available, cannot make LLM call")
                heartbeat_active.clear()
                if progress_callback:
                    try:
                        progress_callback(json.dumps({
                            "type": "error",
                            "message": "Ollama service is not available. Please ensure Ollama is running and try again."
                        }), 4, 4)
                    except Exception as e:
                        logger.debug(f"Progress callback failed: {e}")
                        pass
                return {"exit": True, "skip": False, "result": "Ollama service is not available. Please ensure Ollama is running and try again."}
            
            # Quick health check before first turn (fast timeout)
            if turn_num == 0:
                logger.info("Performing Ollama health check before first turn...")
                try:
                    health_check = requests.get(f"{self.ollama_url}/api/tags", timeout=2)
                    if health_check.status_code != 200:
                        raise Exception("Ollama health check failed")
                    logger.info("Ollama health check passed before first turn")
                except Exception as e:
                    logger.error(f"Ollama health check failed before first turn: {e}")
                    self.ollama_available = False
                    heartbeat_active.clear()
                    if progress_callback:
                        try:
                            progress_callback(json.dumps({
                                "type": "error",
                                "message": f"Ollama service is not responding: {str(e)}"
                            }), 4, 4)
                        except:
                            pass
                    return {"exit": True, "skip": False, "result": f"Ollama service is not responding: {str(e)}. Please ensure Ollama is running and try again."}
            
            # Retry logic for connection errors
            max_retries = 2  # Reduced from 3 to 2 to save time on failures
            retry_delay = 2  # seconds
            llm_response = None
            # Performance tracking for Ollama call
            analysis_call_start = time.time()
            first_token_time = None
            # Check per-turn timeout and cancellation flag before LLM call (after command execution)
            if cancellation_flag.is_set():
                logger.warning("Cancellation flag set, stopping turn")
                return {"exit": False, "skip": False}
            # TIMEOUTS DISABLED: Skip per-turn timeout check
            turn_elapsed = time.time() - turn_start_time
            
            # TIMEOUTS DISABLED: Set very high timeout for LLM calls
            current_elapsed_time = time.time() - agent_start_time
            time_remaining_for_call = 999999  # Effectively no timeout
            logger.info(f"Before LLM call: elapsed={current_elapsed_time:.1f}s - TIMEOUTS DISABLED")
            for retry_attempt in range(max_retries):
                try:
                    # Timeout for agent mode - use remaining time or per-turn timeout, whichever is smaller
                    # For first turn, use whatever time we have (may be minimal due to slow initialization)
                    # For subsequent turns, use up to 50s
                    # But ensure we never go below the minimum
                    # TIMEOUTS DISABLED: Set very high timeout for all LLM calls
                    timeout = 999999  # Effectively no timeout
                    logger.info(f"LLM call timeout set to {timeout}s (effectively infinite)")
                    # Track first token time (for streaming, we'd check stream, but for non-streaming we approximate)
                    call_start = time.time()
                    
                    # Add progress feedback before LLM call
                    if progress_callback:
                        try:
                            progress_callback("🔄 Calling LLM to generate initial plan...", 2, 4)
                        except Exception as e:
                            logger.debug(f"Progress callback failed: {e}")
                    
                    # Add logging
                    logger.info(f"Starting LLM call (turn {turn_num + 1}, timeout={timeout}s, model={self.model}, attempt {retry_attempt + 1})")
                    
                    # Wrap in thread-based timeout for reliability
                    def make_llm_request():
                        """Make the LLM request - executed in separate thread."""
                        try:
                            # Reduce context size for later turns to speed up LLM calls
                            # After turn 3, cap context at 16k to reduce processing time
                            if turn_num >= 3:
                                turn_context = min(effective_context, 16000)  # Cap at 16k for later turns
                                logger.info(f"Reducing context size for turn {turn_num + 1}: {effective_context} -> {turn_context} (to speed up LLM call)")
                            else:
                                turn_context = effective_context
                            
                            return requests.post(
                                f"{self.ollama_url}/api/chat",
                                json={
                                    "model": self.model,
                                    "messages": messages,
                                    "stream": False,
                                    "options": {
                                        "temperature": 0.1,  # Reduced from 0.3 for more deterministic
                                        "top_p": 0.9,
                                        "num_predict": 1000,  # Reduced from 2000 to 1000 for faster responses
                                        "num_ctx": turn_context,  # Use reduced context for later turns
                                    }
                                },
                                timeout=timeout
                            )
                        except Exception as e:
                            logger.error(f"Error in make_llm_request: {e}")
                            raise
                    
                    # Execute with thread-based timeout (more reliable than requests timeout alone)
                    response = None
                    try:
                        with ThreadPoolExecutor(max_workers=1) as executor:
                            future = executor.submit(make_llm_request)
                            # Use exact timeout value (no buffer to prevent exceeding timeout budget)
                            response = future.result(timeout=timeout)
                        call_duration = time.time() - call_start
                        logger.info(f"LLM call completed in {call_duration:.2f}s (turn {turn_num + 1})")
                    except FutureTimeoutError as e:
                        # ThreadPoolExecutor timeout
                        call_duration = time.time() - call_start
                        logger.error(f"LLM call timed out after {call_duration:.2f}s (thread timeout, turn {turn_num + 1})")
                        raise requests.exceptions.Timeout(f"Request timed out after {timeout}s (thread timeout)")
                    except requests.exceptions.Timeout as e:
                        # Requests library timeout
                        call_duration = time.time() - call_start
                        logger.warning(f"LLM call timed out after {call_duration:.2f}s (requests timeout, turn {turn_num + 1}): {e}")
                        raise
                    except Exception as e:
                        call_duration = time.time() - call_start
                        logger.error(f"LLM call failed after {call_duration:.2f}s (turn {turn_num + 1}): {e}")
                        raise
                    
                    if response.status_code != 200:
                        raise Exception(f"Ollama API returned status {response.status_code}")
                    # Approximate first token time (for non-streaming, it's when we get response)
                    if first_token_time is None:
                        first_token_time = time.time()
                        first_token_ms = int((first_token_time - call_start) * 1000)
                        self._log_perf_metric("first_token", ms=first_token_ms)
                    result = response.json()
                    llm_response = result.get("message", {}).get("content", "")
                    # Show what the agent is thinking
                    if progress_callback and llm_response:
                        # Extract thinking/reasoning from response (first 200 chars)
                        thinking_preview = llm_response[:200].replace('\n', ' ')
                        if len(llm_response) > 200:
                            thinking_preview += "..."
                        progress_callback(f"💭 Agent thinking: {thinking_preview}", 2, 4)
                        # Emit heartbeat after receiving LLM response
                        try:
                            progress_callback(json.dumps({
                                "type": "heartbeat",
                                "ts": int(time.time() * 1000),
                                "turn": turn_num + 1,
                                "max_turns": max_turns,
                                "status": "processing_response"
                            }), 2, 4)
                        except Exception as e:
                            logger.debug(f"Progress callback failed: {e}")
                            pass
                    # Validate LLM response is not empty
                    if not llm_response or not llm_response.strip():
                        logger.warning(f"Empty LLM response on turn {turn_num + 1}, attempt {retry_attempt + 1}")
                        if retry_attempt < max_retries - 1:
                            time.sleep(retry_delay)
                            continue
                        # Don't increment turn - retry same turn
                        user_message = "I received an empty response. Please try again or rephrase your question."
                        conversation_context.append({
                            "role": "user",
                            "content": user_message
                        })
                        return {"exit": False, "skip": True}  # Retry same turn
                    # Log analysis call performance
                    analysis_call_ms = int((time.time() - analysis_call_start) * 1000)
                    self._log_perf_metric("analysis_call", 
                                         model=self.model, 
                                         ctx=effective_context, 
                                         ms=analysis_call_ms, 
                                         attempts=retry_attempt + 1)
                    # Success - break out of retry loop
                    break
                except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
                    error_type = "Connection" if isinstance(e, requests.exceptions.ConnectionError) else "Timeout"
                    call_duration = time.time() - call_start if 'call_start' in locals() else 0
                    logger.warning(f"Agent turn {turn_num + 1} {error_type} error after {call_duration:.1f}s (attempt {retry_attempt + 1}/{max_retries}): {e}")
                    if retry_attempt < max_retries - 1:
                        # Retry with exponential backoff
                        wait_time = retry_delay * (2 ** retry_attempt)
                        logger.info(f"Retrying in {wait_time} seconds...")
                        time.sleep(wait_time)
                        continue
                    else:
                        # All retries exhausted
                        logger.error(f"Agent conversation turn {turn_num + 1} failed after {max_retries} attempts: {e}")
                        # Check if Ollama is still available
                        self.ollama_available = self._check_ollama_available()
                        # Stop heartbeat and emit error event
                        heartbeat_active.clear()
                        if progress_callback:
                            try:
                                progress_callback(json.dumps({
                                    "type": "error",
                                    "message": f"Agent mode failed on turn {turn_num + 1} due to {error_type.lower()} error: {str(e)}"
                                }), 4, 4)
                            except Exception as e:
                                logger.debug(f"Progress callback failed: {e}")
                                pass
                        if not self.ollama_available:
                            return {"exit": True, "skip": False, "result": "Ollama service is not available. Please ensure Ollama is running and try again."}
                        return {"exit": True, "skip": False, "result": f"Agent mode failed on turn {turn_num + 1} due to {error_type.lower()} error: {str(e)}. Please try again or use a more specific question."}
                except FutureTimeoutError as e:
                    # ThreadPoolExecutor timeout (from concurrent.futures)
                    call_duration = time.time() - call_start if 'call_start' in locals() else 0
                    logger.error(f"Agent turn {turn_num + 1} thread timeout after {call_duration:.1f}s (attempt {retry_attempt + 1}/{max_retries}): {e}")
                    # Treat as timeout and retry
                    if retry_attempt < max_retries - 1:
                        wait_time = retry_delay * (2 ** retry_attempt)
                        logger.info(f"Retrying in {wait_time} seconds...")
                        time.sleep(wait_time)
                        continue
                    else:
                        # All retries exhausted
                        logger.error(f"Agent conversation turn {turn_num + 1} failed after {max_retries} attempts: thread timeout")
                        self.ollama_available = self._check_ollama_available()
                        heartbeat_active.clear()
                        if progress_callback:
                            try:
                                progress_callback(json.dumps({
                                    "type": "error",
                                    "message": f"Agent mode failed on turn {turn_num + 1} due to timeout. Ollama may be unresponsive."
                                }), 4, 4)
                            except Exception as e:
                                logger.debug(f"Progress callback failed: {e}")
                                pass
                        if not self.ollama_available:
                            return {"exit": True, "skip": False, "result": "Ollama service is not available. Please ensure Ollama is running and try again."}
                        return {"exit": True, "skip": False, "result": f"Agent mode failed on turn {turn_num + 1} due to timeout. Ollama may be unresponsive. Please try again."}
                except Exception as e:
                    # For other exceptions, log and retry if it's a recoverable error
                    error_str = str(e).lower()
                    is_recoverable = any(keyword in error_str for keyword in ["timeout", "connection", "network", "temporary"])
                    if is_recoverable and retry_attempt < max_retries - 1:
                        logger.warning(f"Agent turn {turn_num + 1} recoverable error (attempt {retry_attempt + 1}/{max_retries}): {e}")
                        wait_time = retry_delay * (2 ** retry_attempt)
                        time.sleep(wait_time)
                        continue
                    else:
                        # Non-recoverable error or all retries exhausted
                        logger.error(f"Agent conversation turn {turn_num + 1} failed: {e}")
                        # Stop heartbeat and emit error event
                        heartbeat_active.clear()
                        if progress_callback:
                            try:
                                progress_callback(json.dumps({
                                    "type": "error",
                                    "message": f"Agent mode failed on turn {turn_num + 1}: {str(e)}"
                                }), 4, 4)
                            except Exception as e:
                                logger.debug(f"Progress callback failed: {e}")
                                pass
                        return {"exit": True, "skip": False, "result": f"Agent mode failed on turn {turn_num + 1}: {str(e)}. Please try again or use a more specific question."}
            # If we get here without llm_response, something went wrong
            if not llm_response:
                logger.error(f"Agent turn {turn_num + 1} failed: No response after {max_retries} attempts")
                # Check Ollama one more time
                self.ollama_available = self._check_ollama_available()
                error_msg = "Ollama service is not responding" if not self.ollama_available else "No response from Ollama after multiple attempts"
                # Stop heartbeat and emit error event
                heartbeat_active.clear()
                if progress_callback:
                    try:
                        progress_callback(json.dumps({
                            "type": "error",
                            "message": f"{error_msg}. Please ensure Ollama is running and try again."
                        }), 4, 4)
                    except Exception as e:
                        logger.debug(f"Progress callback failed: {e}")
                        pass
                return {"exit": True, "skip": False, "result": f"{error_msg}. Please ensure Ollama is running and try again."}
            # Add LLM response to conversation
            conversation_context.append({
            "role": "assistant",
            "content": llm_response
            })
            # Limit conversation context size (max 100 messages)
            MAX_CONVERSATION_MESSAGES = 100
            if len(conversation_context) > MAX_CONVERSATION_MESSAGES:
                # Keep most recent messages (sliding window)
                conversation_context = conversation_context[-MAX_CONVERSATION_MESSAGES:]
                logger.debug(f"Limited conversation_context to {MAX_CONVERSATION_MESSAGES} messages (kept most recent)")
            # Parse commands from LLM response (with timeout protection)
            commands = self._execute_with_timeout(
                self._parse_agent_commands,
                TIMEOUT_PARSE_COMMANDS,
                [],
                llm_response
            )
            
            # Check for unexpected responses (URLs, non-command text)
            if not commands and llm_response:
                llm_response_trimmed = llm_response.strip()
                # Check if response looks like a URL or non-command
                if (llm_response_trimmed.startswith('http://') or 
                    llm_response_trimmed.startswith('https://') or
                    (len(llm_response_trimmed) < 50 and '://' in llm_response_trimmed)):
                    logger.warning(f"LLM returned URL/non-command response instead of commands on turn {turn_num + 1}: {llm_response_trimmed[:100]}")
                    if progress_callback:
                        try:
                            progress_callback("⚠️ LLM returned unexpected response. Retrying...", 2, 4)
                        except Exception:
                            pass
                    # For first turn, this is a problem - retry or return error
                    if turn_num == 0:
                        # On first turn, if we get a URL, treat as error
                        heartbeat_active.clear()
                        if progress_callback:
                            try:
                                progress_callback(json.dumps({
                                    "type": "error",
                                    "message": "LLM returned unexpected response. Please try again."
                                }), 4, 4)
                            except Exception:
                                pass
                        return {"exit": True, "skip": False, "result": "LLM returned unexpected response. Please try again or rephrase your question."}
                    # For later turns, continue but log warning
                    logger.warning(f"Continuing despite unexpected response on turn {turn_num + 1}")
            
            # Early exit handling: if no commands and force_agent is on, still emit plan and done
            if not commands and force_agent:
                logger.warning(f"Agent mode (force) received no commands on turn {turn_num + 1}, emitting empty plan and done")
                # Emit empty plan
                if progress_callback:
                    try:
                        progress_callback(json.dumps({
                            "type": "plan",
                            "tasks": []
                        }), 2, 4)
                    except:
                        pass
                # Keep heartbeat running briefly, then emit done
                # No sleep needed - heartbeat will emit naturally
                heartbeat_active.clear()
                if progress_callback:
                    try:
                        all_tasks = task_tracker.get_tasks()
                        duration_ms = int((time.time() - agent_start_time) * 1000)
                        progress_callback(json.dumps({
                            "type": "done",
                            "summary": {
                                "tasks_total": len(all_tasks),
                                "completed": 0,
                                "failed": 0,
                                "duration_ms": duration_ms,
                                "reason": "empty_plan"
                            }
                        }), 4, 4)
                    except Exception as e:
                        logger.debug(f"Progress callback failed: {e}")
                        pass
                return {"exit": True, "skip": False, "result": "Agent mode received no commands. Please rephrase your request with specific actions (READ, GREP, SEARCH, TRACE)."}
            
            # Show what tasks the agent set for itself
            if progress_callback and commands:
                task_list = []
                for cmd in commands:
                    if cmd["type"] == "READ":
                        task_list.append(f"📖 Read {cmd.get('file', 'file')}")
                    elif cmd["type"] == "GREP":
                        pattern = cmd.get('pattern', 'pattern')[:30]
                        if len(cmd.get('pattern', '')) > 30:
                            pattern += "..."
                        task_list.append(f"🔍 Grep '{pattern}'")
                    elif cmd["type"] == "SEARCH":
                        term = cmd.get('term', 'term')[:30]
                        if len(cmd.get('term', '')) > 30:
                            term += "..."
                        task_list.append(f"🔎 Search '{term}'")
                    elif cmd["type"] == "TRACE":
                        start = cmd.get('start', 'start')[:20]
                        end = cmd.get('end', 'end')[:20]
                        task_list.append(f"🔗 Trace {start} → {end}")
                    elif cmd["type"] == "ANALYZE":
                        task_list.append("📊 Analyze findings")
                if task_list:
                    tasks_text = " | ".join(task_list[:3])  # Show first 3 tasks
                    if len(task_list) > 3:
                        tasks_text += f" (+{len(task_list) - 3} more)"
                    progress_callback(f"📋 Agent tasks: {tasks_text}", 2, 4)
            # Validate commands and deduplicate
            valid_commands = []
            seen_command_keys = set()  # For deduplication
            validation_errors = []
            
            for cmd in commands:
                # Validate command
                is_valid, error_msg, suggestion = self._validate_command(cmd)
                
                if not is_valid:
                    logger.warning(f"Command validation failed: {cmd.get('type')} - {error_msg}")
                    validation_errors.append({
                        "command": cmd,
                        "error": error_msg,
                        "suggestion": suggestion
                    })
                    continue
                
                # Deduplicate: create unique key for command
                if cmd["type"] == "READ":
                    cmd_key = f"READ:{cmd.get('file', '')}"
                elif cmd["type"] == "GREP":
                    cmd_key = f"GREP:{cmd.get('pattern', '')}"
                elif cmd["type"] == "SEARCH":
                    cmd_key = f"SEARCH:{cmd.get('term', '')}"
                elif cmd["type"] == "TRACE":
                    cmd_key = f"TRACE:{cmd.get('start', '')}→{cmd.get('end', '')}"
                elif cmd["type"] == "ANALYZE":
                    cmd_key = f"ANALYZE:{turn_num}"  # Allow ANALYZE once per turn
                else:
                    cmd_key = f"{cmd['type']}:{hash(str(cmd))}"
                
                # Skip if already seen in this turn
                if cmd_key in seen_command_keys:
                    logger.debug(f"Skipping duplicate command: {cmd_key}")
                    continue
                
                seen_command_keys.add(cmd_key)
                valid_commands.append(cmd)
            
            # Track consecutive invalid command attempts
            if len(commands) > 0 and len(valid_commands) == 0:
                consecutive_invalid_commands += 1
                if consecutive_invalid_commands >= MAX_CONSECUTIVE_INVALID:
                    logger.warning(f"Too many consecutive invalid commands ({consecutive_invalid_commands}), forcing analysis")
                    # Force analysis to break the loop
                    return {"exit": True, "skip": False}
            else:
                consecutive_invalid_commands = 0  # Reset counter on valid commands
            
            # Log deduplication results
            if len(commands) != len(valid_commands):
                logger.info(f"Command deduplication: {len(commands)} -> {len(valid_commands)} commands")
            
            # Add validation errors to results if any
            if validation_errors:
                for error_info in validation_errors:
                    results.append({
                        "type": "error",
                        "command": error_info["command"],
                        "error": error_info["error"],
                        "suggestions": error_info["suggestion"]
                    })
            
            commands = valid_commands
            # Create task entries for each valid command (after validation)
            task_ids = {}  # Maps command_key -> task_id
            cmd_to_key = {}  # Maps cmd object id -> command_key (for lookup)
            cmd_key_counter = {}  # Track duplicates to make keys unique
            if commands:
                for idx, cmd in enumerate(commands):
                    # Create a base hashable key from command fields
                    if cmd["type"] == "READ":
                        base_key = f"READ_{cmd.get('file', '')}"
                    elif cmd["type"] == "GREP":
                        base_key = f"GREP_{cmd.get('pattern', '')}"
                    elif cmd["type"] == "SEARCH":
                        base_key = f"SEARCH_{cmd.get('term', '')}"
                    elif cmd["type"] == "TRACE":
                        base_key = f"TRACE_{cmd.get('start', '')}_{cmd.get('end', '')}"
                    elif cmd["type"] == "ANALYZE":
                        base_key = f"ANALYZE_{turn_num}"
                    else:
                        base_key = f"{cmd['type']}_{hash(str(cmd))}_{turn_num}"
                    # Make cmd_key unique by including index if duplicate
                    if base_key in cmd_key_counter:
                        cmd_key_counter[base_key] += 1
                        cmd_key = f"{base_key}_{cmd_key_counter[base_key]}"
                    else:
                        cmd_key_counter[base_key] = 0
                        cmd_key = base_key
                    task_id = f"{cmd['type']}_{hash(cmd_key)}_{turn_num}_{idx}"
                    task_ids[cmd_key] = task_id
                    cmd_to_key[id(cmd)] = cmd_key  # Use id() to reference the cmd object
                    # Generate task description (more action-oriented, like Cursor's planning)
                    if cmd["type"] == "READ":
                        file_path = cmd.get('file', 'file')
                        # Extract just filename for cleaner display
                        filename = file_path.split('/')[-1] if '/' in file_path else file_path
                        description = f"📖 Reading {filename}"
                    elif cmd["type"] == "GREP":
                        pattern = cmd.get('pattern', 'pattern')[:40]
                        description = f"🔍 Searching for '{pattern}'"
                    elif cmd["type"] == "SEARCH":
                        term = cmd.get('term', 'term')[:40]
                        description = f"🔎 Exploring '{term}'"
                    elif cmd["type"] == "TRACE":
                        start = cmd.get('start', 'start')[:25]
                        end = cmd.get('end', 'end')[:25]
                        description = f"🔗 Tracing {start} → {end}"
                    elif cmd["type"] == "ANALYZE":
                        description = "📊 Analyzing findings"
                    else:
                        description = f"⚙️ {cmd['type']} command"
                    task_tracker.add_task(task_id, cmd["type"], description)
            # Initialize phase counters based on planned tasks
            for tid in task_tracker.task_order:
                if tid in task_tracker.tasks:
                    task = task_tracker.tasks[tid]
                    task_type = task["type"]
                    if task_type == "READ":
                        phase_counters["reads"]["total"] += 1
                    elif task_type == "GREP":
                        phase_counters["greps"]["total"] += 1
                    elif task_type == "SEARCH":
                        phase_counters["searches"]["total"] += 1
                    elif task_type == "TRACE":
                        phase_counters["traces"]["total"] += 1
            # Emit plan event immediately after building task list
            if progress_callback and commands:  # Only emit if we have commands
                try:
                    # Build plan tasks list with proper format
                    plan_tasks = []
                    for tid in task_tracker.task_order:
                        if tid in task_tracker.tasks:
                            task = task_tracker.tasks[tid]
                            plan_tasks.append({
                                "id": task["id"],
                                "title": task["title"],
                                "type": task["type"],
                                "status": task["status"]
                            })
                    if plan_tasks:  # Only emit if we have tasks
                        progress_callback(json.dumps({
                            "type": "plan",
                            "tasks": plan_tasks
                        }), 2, 4)
                        # Log plan emission for metrics
                        self._log_perf_metric("plan_emitted", tasks_count=len(plan_tasks), ms=int((time.time() - agent_start_time) * 1000))
                except Exception as e:
                    logger.warning(f"Failed to emit plan event: {e}")
                    # Fallback to old format
                    try:
                        all_tasks = task_tracker.get_tasks()
                        if all_tasks:
                            progress_callback(json.dumps({
                                "type": "plan",
                                "tasks": [{
                                    "id": t["id"],
                                    "title": t["title"],
                                    "type": t["type"],
                                    "status": t["status"]
                                } for t in all_tasks]
                            }), 2, 4)
                    except:
                        pass
            # Check cumulative limits before executing commands
            read_count = sum(1 for c in valid_commands if c["type"] == "READ")
            grep_count = sum(1 for c in valid_commands if c["type"] == "GREP")
            search_count = sum(1 for c in valid_commands if c["type"] == "SEARCH")
            trace_count = sum(1 for c in valid_commands if c["type"] == "TRACE")
            
            # Check if executing these commands would exceed cumulative limits
            if cumulative_file_reads + read_count > MAX_CUMULATIVE_FILE_READS:
                logger.warning(f"Cumulative file reads limit reached ({cumulative_file_reads}/{MAX_CUMULATIVE_FILE_READS}), skipping {read_count} READ commands")
                valid_commands = [c for c in valid_commands if c["type"] != "READ"]
                read_count = 0
            if cumulative_greps + grep_count > MAX_CUMULATIVE_GREPS:
                logger.warning(f"Cumulative greps limit reached ({cumulative_greps}/{MAX_CUMULATIVE_GREPS}), skipping {grep_count} GREP commands")
                valid_commands = [c for c in valid_commands if c["type"] != "GREP"]
                grep_count = 0
            if cumulative_searches + search_count > MAX_CUMULATIVE_SEARCHES:
                logger.warning(f"Cumulative searches limit reached ({cumulative_searches}/{MAX_CUMULATIVE_SEARCHES}), skipping {search_count} SEARCH commands")
                valid_commands = [c for c in valid_commands if c["type"] != "SEARCH"]
                search_count = 0
            if cumulative_traces + trace_count > MAX_CUMULATIVE_TRACES:
                logger.warning(f"Cumulative traces limit reached ({cumulative_traces}/{MAX_CUMULATIVE_TRACES}), skipping {trace_count} TRACE commands")
                valid_commands = [c for c in valid_commands if c["type"] != "TRACE"]
                trace_count = 0
            
            # Update cumulative counters based on commands that passed limit checks
            cumulative_file_reads += read_count
            cumulative_greps += grep_count
            cumulative_searches += search_count
            cumulative_traces += trace_count
            
            # Warn when approaching limits (80% threshold)
            if cumulative_file_reads > MAX_CUMULATIVE_FILE_READS * 0.8:
                logger.warning(f"Approaching cumulative file reads limit: {cumulative_file_reads}/{MAX_CUMULATIVE_FILE_READS}")
            if cumulative_searches > MAX_CUMULATIVE_SEARCHES * 0.8:
                logger.warning(f"Approaching cumulative searches limit: {cumulative_searches}/{MAX_CUMULATIVE_SEARCHES}")
            
            # Show what commands will be executed
            if progress_callback and valid_commands:
                exec_summary = []
                if read_count > 0:
                    exec_summary.append(f"{read_count} READ")
                if grep_count > 0:
                    exec_summary.append(f"{grep_count} GREP")
                if search_count > 0:
                    exec_summary.append(f"{search_count} SEARCH")
                if trace_count > 0:
                    exec_summary.append(f"{trace_count} TRACE")
                if exec_summary:
                    progress_callback(f"⚙️ Executing: {', '.join(exec_summary)}", 2, 4)
            # Limit commands_history to prevent unbounded growth
            if len(commands_history) > MAX_COMMANDS_HISTORY:
                commands_history = commands_history[-MAX_COMMANDS_HISTORY:]
            # Update commands to use filtered valid_commands
            commands = valid_commands
            
            # Track tool usage and command history
            tool_used_this_turn = any(cmd["type"] in ["READ", "GREP", "SEARCH", "TRACE"] for cmd in commands)
            if tool_used_this_turn:
                tools_used = True
                # Store command strings for validation
                for cmd in commands:
                    if cmd["type"] == "READ":
                        commands_history.append(f"READ {cmd.get('file', '')}")
                    elif cmd["type"] == "GREP":
                        commands_history.append(f"GREP {cmd.get('pattern', '')}")
                    elif cmd["type"] == "SEARCH":
                        commands_history.append(f"SEARCH {cmd.get('term', '')}")
                    elif cmd["type"] == "TRACE":
                        commands_history.append(f"TRACE {cmd.get('start', '')} → {cmd.get('end', '')}")
                # Track files read
                for cmd in commands:
                    if cmd["type"] == "READ" and cmd.get("file"):
                        files_read_tracker.add(cmd["file"])
                        # Remove from discovered files if it was there
                        discovered_files.discard(cmd["file"])
                # Limit discovered_files to prevent unbounded growth
                if len(discovered_files) >= MAX_DISCOVERED_FILES:
                    # Keep only most recent (convert to list, keep last N, then convert back to set)
                    discovered_files = set(list(discovered_files)[-MAX_DISCOVERED_FILES:])
                # Check if LLM wants to analyze
                if any(cmd["type"] == "ANALYZE" for cmd in commands):
                    if progress_callback:
                        progress_callback("Analyzing findings...", 3, 4)
                    # STRICT validation before allowing analysis (with timeout protection)
                    default_verification = {"can_analyze": False, "blocking_message": "Verification check timed out. Please try again."}
                    verification = self._execute_with_timeout(
                        self._check_verification_requirements,
                        TIMEOUT_VERIFICATION,
                        default_verification,
                        message,
                        files_read_tracker,
                        commands_history
                    )
                    # Store verification results for confidence calculation
                    self._last_verification_results = {
                        "function_verifications": verification.get("verification_results", {}),
                        "framework_results": verification.get("framework_results", {})
                    }
                    if not verification["can_analyze"]:
                        user_message = verification["blocking_message"]
                        return {"exit": False, "skip": True}  # Skip turn, retry
                    # Also check if tools were used
                    elif not tools_used:
                        user_message = "You requested ANALYZE but haven't used any tools yet. You MUST read the codebase first:\n\n1. Use READ command on files mentioned in the problem (e.g., READ backend/services/ocr_service.py)\n2. Use GREP to find function definitions (e.g., GREP insert_line_items)\n3. Use SEARCH to understand relationships (e.g., SEARCH line items)\n\nOnly use ANALYZE after you've read actual code files. Start with READ commands."
                        return {"exit": False, "skip": True}  # Skip turn, retry
                    else:
                        # EARLY CONFIDENCE-BASED BLOCKING (before ANALYZE)
                        # Calculate confidence DURING exploration, block BEFORE generation (with timeout protection)
                        default_confidence = 0.5  # Default to medium confidence if calculation times out
                        current_confidence = self._execute_with_timeout(
                            self._calculate_confidence_score,
                            TIMEOUT_CONFIDENCE,
                            default_confidence,
                            files_read_tracker,
                            commands_history,
                            key_insights,
                            [],
                            self._last_verification_results,
                            None,  # code_match_accuracy - Not available yet during exploration
                            None   # runtime_checks - Not available yet during exploration
                        )
                        if current_confidence < 0.7:
                            logger.warning(f"Low confidence score ({current_confidence:.0%}) before ANALYZE, blocking early")
                            blocking_message = f"⚠️ ANALYSIS BLOCKED - Low Confidence ({current_confidence:.0%})\n\n"
                            blocking_message += "Your confidence is too low to provide a reliable analysis. The analysis has low confidence due to:\n"
                            if len(files_read_tracker) < 2:
                                blocking_message += f"  - Only {len(files_read_tracker)} file(s) read (need at least 2)\n"
                            if not self._last_verification_results.get("function_verifications"):
                                blocking_message += "  - No function verification performed (use GREP to verify function names)\n"
                            if not self._last_verification_results.get("framework_results"):
                                blocking_message += "  - Framework not detected (use GREP to detect FastAPI/Flask)\n"
                            # Get exploration suggestions
                            suggestions = self._get_exploration_suggestions(
                                files_read=files_read_tracker,
                                commands_history=commands_history,
                                confidence=current_confidence,
                                verification_results=self._last_verification_results
                            )
                            if suggestions:
                                blocking_message += f"\n💡 Suggestions to improve confidence:\n{suggestions}\n"
                            blocking_message += "\nPlease complete these steps before using ANALYZE:\n"
                            blocking_message += "1. READ more files related to the problem\n"
                            blocking_message += "2. Use GREP to verify function names exist\n"
                            blocking_message += "3. Use GREP to detect framework (FastAPI/Flask)\n"
                            blocking_message += "4. Re-run ANALYZE after completing these steps\n"
                            user_message = blocking_message
                            return {"exit": False, "skip": True}  # Skip turn, retry
                        else:
                            logger.info(f"Agent requested analysis after {turn_num + 1} turns (files read: {len(files_read_tracker)}, confidence: {current_confidence:.0%}, verifications passed)")
                            # Log total agent run time
                            total_ms = int((time.time() - agent_start_time) * 1000)
                            self._log_perf_metric("totals", ms=total_ms, turns=turn_num + 1, files_read=len(files_read_tracker))
                            return {"exit": True, "skip": False}  # Exit loop, ready for analysis
            
            # Check per-turn timeout and cancellation flag after operations that might take time (before command execution)
            if cancellation_flag.is_set():
                logger.warning("Cancellation flag set, stopping turn")
                return {"exit": False, "skip": False}
            turn_elapsed = time.time() - turn_start_time
            # TIMEOUTS DISABLED: Skip per-turn timeout check before command execution
            # if turn_elapsed > per_turn_timeout:
            #     if progress_callback:
            #         progress_callback(f"Turn {turn_num + 1} timed out after {per_turn_timeout}s. Breaking turn.", 2, 4)
            #     return {"exit": False, "skip": False}  # Normal end, just timed out
            
            # Before executing commands, check if we have enough time
            elapsed_before_commands = time.time() - agent_start_time
            logger.info(f"Before command execution: elapsed={elapsed_before_commands:.1f}s, remaining={agent_timeout - elapsed_before_commands:.1f}s, commands={len(commands)}")
            if elapsed_before_commands > agent_timeout * 0.7:  # If we've used 70% of timeout
                logger.warning(f"Timeout approaching before command execution: {elapsed_before_commands:.1f}s/{agent_timeout}s ({elapsed_before_commands/agent_timeout*100:.1f}%)")
                # Skip command execution, go straight to LLM call with what we have
                logger.info("Skipping command execution to save time for LLM call")
                commands = []  # Skip commands, proceed to LLM call
            
            # Execute commands (with parallel execution for READ commands)
            results = []
            # Performance tracking for command execution
            searches_start = time.time()
            reads_start = time.time()
            traces_start = time.time()
            search_count = 0
            read_count = 0
            trace_count = 0
            # Separate commands by type for parallel execution
            read_commands = [cmd for cmd in commands if cmd["type"] == "READ"]
            search_commands = [cmd for cmd in commands if cmd["type"] == "SEARCH"]
            grep_commands = [cmd for cmd in commands if cmd["type"] == "GREP"]
            trace_commands = [cmd for cmd in commands if cmd["type"] == "TRACE"]
            other_commands = [cmd for cmd in commands if cmd["type"] not in ["READ", "SEARCH", "GREP", "TRACE"]]
            # Execute READ commands in parallel (if multiple)
            # Early stop: limit to max_files_per_plan to prevent unbounded reads
            if len(read_commands) > 0:
                reads_start = time.time()
                # Limit first turn to fewer files to ensure LLM call happens quickly
                if turn_num == 0:
                    first_turn_limit = min(config.max_files_per_plan, 5)  # Max 5 files on first turn
                    if len(read_commands) > first_turn_limit:
                        logger.info(f"First turn: Limiting READ commands from {len(read_commands)} to {first_turn_limit}")
                        read_commands = read_commands[:first_turn_limit]
                else:
                    # Limit reads to max_files_per_plan for subsequent turns
                    if len(read_commands) > config.max_files_per_plan:
                        logger.info(f"Limiting READ commands from {len(read_commands)} to {config.max_files_per_plan}")
                        read_commands = read_commands[:config.max_files_per_plan]
                # Mark all READ tasks as running and emit task_update
                for cmd in read_commands:
                    cmd_key = cmd_to_key.get(id(cmd))
                    if cmd_key and cmd_key in task_ids:
                        task_id = task_ids[cmd_key]
                        task_tracker.start_task(task_id)
                        # Emit task_update event
                        if progress_callback:
                            try:
                                task = task_tracker.tasks[task_id]
                                last_task_update_time = time.time()
                                progress_callback(json.dumps({
                                    "type": "task_update",
                                    "task": {
                                        "id": task["id"],
                                        "title": task.get("title", task.get("description", "")),
                                        "type": task.get("type", ""),
                                        "status": task["status"],
                                        "started_at": task["started_at"]
                                    }
                                }), 2, 4)
                            except Exception as e:
                                logger.debug(f"Progress callback failed: {e}")
                                pass
                read_results = self._execute_read_commands_parallel(read_commands, file_cache, file_relationships, discovered_files, files_read_tracker, turn_num, MAX_FILE_CACHE_SIZE, cancellation_flag, agent_start_time, agent_timeout)
                results.extend(read_results)
                # Limit results during collection to prevent unbounded growth
                if len(results) > MAX_RESULTS_DURING_COLLECTION:
                    # Keep most relevant results (sort by score if available)
                    results = sorted(results, key=lambda x: x.get('score', 0), reverse=True)[:MAX_RESULTS_DURING_COLLECTION]
                read_count = len(read_commands)
                reads_ms = int((time.time() - reads_start) * 1000)
                self._log_perf_metric("reads", files=read_count, ms=reads_ms)
                logger.info(f"After file reads: elapsed={time.time() - agent_start_time:.1f}s, files_read={read_count}, duration={reads_ms}ms")
                # TIMEOUTS DISABLED: Skip timeout check after file reads
                # if elapsed_time > agent_timeout:
                #     return {"exit": True, "skip": False, "result": f"Agent mode timed out after {elapsed_time/60:.1f} minutes - file reads took too long. Please try a more specific question."}
                #     # Cancel remaining operations
                #     cancellation_flag.set()
                #     logger.warning("Cancelling remaining operations (searches, GREP) due to timeout")
                #     # Skip remaining command execution
                #     search_commands = []
                #     grep_commands = []
                #     trace_commands = []
                # Mark READ tasks as completed and emit task_update
                for cmd in read_commands:
                    cmd_key = cmd_to_key.get(id(cmd))
                    if cmd_key and cmd_key in task_ids:
                        task_id = task_ids[cmd_key]
                        result_count = sum(1 for r in read_results if r.get("file") == cmd.get("file") and r.get("type") != "error")
                        error = next((r.get("error") for r in read_results if r.get("file") == cmd.get("file") and r.get("type") == "error"), None)
                        task_tracker.complete_task(task_id, result_count, error)
                        # Emit task_update event
                        if progress_callback:
                            try:
                                task = task_tracker.tasks[task_id]
                                last_task_update_time = time.time()
                                phase_counters["reads"]["current"] += 1
                                progress_callback(json.dumps({
                                    "type": "task_update",
                                    "task": {
                                        "id": task["id"],
                                        "title": task.get("title", task.get("description", "")),
                                        "type": task.get("type", ""),
                                        "status": task["status"],
                                        "progress": task["progress"],
                                        "ended_at": task["ended_at"],
                                        "duration_ms": task["duration_ms"],
                                        "note": task.get("note")
                                    }
                                }), 2, 4)
                                # Emit progress event for reads phase
                                if phase_counters["reads"]["total"] > 0:
                                    progress_callback(json.dumps({
                                        "type": "progress",
                                        "phase": "reads",
                                        "current": phase_counters["reads"]["current"],
                                        "total": phase_counters["reads"]["total"],
                                        "percentage": int((phase_counters["reads"]["current"] / phase_counters["reads"]["total"]) * 100)
                                    }), 2, 4)
                            except Exception as e:
                                logger.debug(f"Progress callback failed: {e}")
                                pass
            elif len(read_commands) == 1:
                # Single READ command - execute normally
                cmd = read_commands[0]
                cmd_key = cmd_to_key.get(id(cmd))
                task_id = None  # Initialize task_id
                if cmd_key and cmd_key in task_ids:
                    task_id = task_ids[cmd_key]
                    task_tracker.start_task(task_id)
                # Emit task_update event
                if progress_callback and task_id:
                    try:
                        task = task_tracker.tasks[task_id]
                        last_task_update_time = time.time()
                        progress_callback(json.dumps({
                            "type": "task_update",
                            "task": {
                                "id": task["id"],
                                "title": task.get("title", task.get("description", "")),
                                "type": task.get("type", ""),
                                "status": task["status"],
                                "started_at": task["started_at"]
                            }
                        }), 2, 4)
                    except:
                        pass
                    read_results = self._execute_single_read_command(cmd, file_cache, file_relationships, discovered_files, files_read_tracker, turn_num, MAX_FILE_CACHE_SIZE)
                    results.extend(read_results)
                    # Limit results during collection to prevent unbounded growth
                    if len(results) > MAX_RESULTS_DURING_COLLECTION:
                        # Keep most relevant results (sort by score if available)
                        results = sorted(results, key=lambda x: x.get('score', 0), reverse=True)[:MAX_RESULTS_DURING_COLLECTION]
                    read_count = 1
                    reads_ms = int((time.time() - reads_start) * 1000)
                    self._log_perf_metric("reads", files=read_count, ms=reads_ms)
                    if cmd_key and cmd_key in task_ids:
                        task_id = task_ids[cmd_key]
                        result_count = sum(1 for r in read_results if r.get("type") != "error")
                        error = next((r.get("error") for r in read_results if r.get("type") == "error"), None)
                        task_tracker.complete_task(task_id, result_count, error)
                        # Emit task_update event
                        if progress_callback:
                            try:
                                task = task_tracker.tasks[task_id]
                                last_task_update_time = time.time()
                                phase_counters["reads"]["current"] += 1
                                progress_callback(json.dumps({
                                    "type": "task_update",
                                    "task": {
                                        "id": task["id"],
                                        "title": task.get("title", task.get("description", "")),
                                        "type": task.get("type", ""),
                                        "status": task["status"],
                                        "progress": task["progress"],
                                        "ended_at": task["ended_at"],
                                        "duration_ms": task["duration_ms"],
                                        "note": task.get("note")
                                    }
                                }), 2, 4)
                                # Emit progress event for reads phase
                                if phase_counters["reads"]["total"] > 0:
                                    progress_callback(json.dumps({
                                        "type": "progress",
                                        "phase": "reads",
                                        "current": phase_counters["reads"]["current"],
                                        "total": phase_counters["reads"]["total"],
                                        "percentage": int((phase_counters["reads"]["current"] / phase_counters["reads"]["total"]) * 100)
                                    }), 2, 4)
                            except Exception as e:
                                logger.debug(f"Progress callback failed: {e}")
                                pass
            # Execute SEARCH commands in parallel (if multiple) - PERFORMANCE OPTIMIZATION
            if search_commands:
                searches_start = time.time()
                search_count = len(search_commands)
                # Limit searches to prevent too many parallel operations
                if len(search_commands) > config.max_parallel_searches:
                    logger.info(f"Limiting SEARCH commands from {len(search_commands)} to {config.max_parallel_searches}")
                    search_commands = search_commands[:config.max_parallel_searches]
                # Mark all SEARCH tasks as running
                for cmd in search_commands:
                    cmd_key = cmd_to_key.get(id(cmd))
                    if cmd_key and cmd_key in task_ids:
                        task_id = task_ids[cmd_key]
                        task_tracker.start_task(task_id)
                        if progress_callback:
                            try:
                                task = task_tracker.tasks[task_id]
                                last_task_update_time = time.time()
                                progress_callback(json.dumps({
                                    "type": "task_update",
                                    "task": {
                                        "id": task["id"],
                                        "title": task.get("title", task.get("description", "")),
                                        "type": task.get("type", ""),
                                        "status": task["status"],
                                        "started_at": task["started_at"]
                                    }
                                }), 2, 4)
                            except Exception as e:
                                logger.debug(f"Progress callback failed: {e}")
                                pass
                # Execute searches in parallel
                def execute_search(cmd):
                    """Execute a single search command."""
                    try:
                        # Check cancellation before starting
                        if cancellation_flag.is_set():
                            return {"type": "cancelled", "command": cmd}
                        
                        term = cmd.get("term")
                        if not term:
                            return {"type": "error", "command": cmd, "error": "SEARCH command missing 'term' field"}
                        
                        # Check timeout before search
                        elapsed = time.time() - agent_start_time
                        if elapsed > agent_timeout * 0.8:
                            return {"type": "timeout", "command": cmd, "error": "Timeout approaching"}
                        
                        # Reduce max_results for faster searches (10 instead of 20)
                        search_results = explorer.search_concept(term, max_results=min(10, config.max_search_results), cancellation_flag=cancellation_flag)
                        cmd_results = []
                        for result in search_results:
                            # Check cancellation flag in loop
                            if cancellation_flag.is_set():
                                break
                            # Add timeout check in loop
                            elapsed = time.time() - agent_start_time
                            if elapsed > agent_timeout * 0.8:
                                break
                            file_path = result.get("file")
                            if file_path and file_path not in files_read_tracker:
                                discovered_files.add(file_path)
                            cmd_results.append({
                                "type": "search",
                                "file": file_path,
                                "line": result.get("line"),
                                "match": result.get("match"),
                                "context": result.get("context")
                            })
                        return {"type": "success", "command": cmd, "results": cmd_results}
                    except Exception as e:
                        logger.warning(f"Search failed for '{cmd.get('term', 'unknown')}': {e}")
                        return {"type": "error", "command": cmd, "error": str(e)}
                
                # Execute searches in parallel
                max_workers = min(config.max_parallel_searches, len(search_commands), 4)  # Cap at 4 workers
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    search_futures = {executor.submit(execute_search, cmd): cmd for cmd in search_commands}
                    for future in as_completed(search_futures):
                        cmd = search_futures[future]
                        cmd_key = cmd_to_key.get(id(cmd))
                        try:
                            result = future.result()
                            if result["type"] == "success":
                                results.extend(result["results"])
                                result_count = len(result["results"])
                                # Limit results during collection to prevent unbounded growth
                                if len(results) > MAX_RESULTS_DURING_COLLECTION:
                                    # Keep most relevant results (sort by score if available)
                                    results = sorted(results, key=lambda x: x.get('score', 0), reverse=True)[:MAX_RESULTS_DURING_COLLECTION]
                            else:
                                results.append(result)
                                result_count = 0
                            # Mark task as completed
                            if cmd_key and cmd_key in task_ids:
                                task_id = task_ids[cmd_key]
                                error = result.get("error") if result["type"] == "error" else None
                                task_tracker.complete_task(task_id, result_count, error)
                                if progress_callback:
                                    try:
                                        task = task_tracker.tasks[task_id]
                                        last_task_update_time = time.time()
                                        phase_counters["searches"]["current"] += 1
                                        progress_callback(json.dumps({
                                            "type": "task_update",
                                            "task": {
                                                "id": task["id"],
                                                "title": task.get("title", task.get("description", "")),
                                                "type": task.get("type", ""),
                                                "status": task["status"],
                                                "progress": task["progress"],
                                                "ended_at": task["ended_at"],
                                                "duration_ms": task["duration_ms"]
                                            }
                                        }), 2, 4)
                                        if phase_counters["searches"]["total"] > 0:
                                            progress_callback(json.dumps({
                                                "type": "progress",
                                                "phase": "searches",
                                                "current": phase_counters["searches"]["current"],
                                                "total": phase_counters["searches"]["total"],
                                                "percentage": int((phase_counters["searches"]["current"] / phase_counters["searches"]["total"]) * 100)
                                            }), 2, 4)
                                    except Exception as e:
                                        logger.debug(f"Progress callback failed: {e}")
                                        pass
                        except Exception as e:
                            logger.warning(f"Error processing search result: {e}")
                            if cmd_key and cmd_key in task_ids:
                                task_id = task_ids[cmd_key]
                                task_tracker.complete_task(task_id, 0, str(e))
                if search_count > 0:
                    searches_ms = int((time.time() - searches_start) * 1000)
                    self._log_perf_metric("searches", count=search_count, ms=searches_ms)
                    logger.info(f"After searches: elapsed={time.time() - agent_start_time:.1f}s, searches={search_count}, duration={searches_ms}ms")
                    # Check timeout after searches with 5s buffer for early termination
                    elapsed_time = time.time() - agent_start_time
                    time_remaining = agent_timeout - elapsed_time
                    if time_remaining <= 5.0:  # 5s buffer - return partial results if timeout approaching
                        logger.warning(f"Timeout approaching after searches (within 5s buffer): {elapsed_time:.1f}s/{agent_timeout}s, {time_remaining:.1f}s remaining")
                        if cancellation_flag.is_set() or elapsed_time >= agent_timeout:
                            return {"exit": True, "skip": False, "result": f"Agent mode timed out after {elapsed_time/60:.1f} minutes - searches took too long. Please try a more specific question."}
                        # Cancel remaining operations and return partial results
                        cancellation_flag.set()
                        logger.warning("Cancelling remaining operations (GREP) due to timeout approaching - returning partial results")
                        grep_commands = []
                        trace_commands = []
                    elif elapsed_time > agent_timeout * 0.8:  # Changed from 0.9 to 0.8 for earlier detection
                        logger.warning(f"Timeout approaching after searches: {elapsed_time:.1f}s/{agent_timeout}s ({elapsed_time/agent_timeout*100:.1f}%)")
                        if cancellation_flag.is_set() or elapsed_time > agent_timeout:
                            return {"exit": True, "skip": False, "result": f"Agent mode timed out after {elapsed_time/60:.1f} minutes - searches took too long. Please try a more specific question."}
                        # Cancel remaining operations
                        cancellation_flag.set()
                        logger.warning("Cancelling remaining operations (GREP) due to timeout")
                        grep_commands = []
                        trace_commands = []
            else:
                search_count = 0
            # Execute GREP commands in parallel (if multiple) - PERFORMANCE OPTIMIZATION
            if grep_commands:
                greps_start = time.time()
                grep_count = len(grep_commands)
                # Limit greps to prevent too many parallel operations
                if len(grep_commands) > 4:  # Cap at 4 parallel GREP commands
                    logger.info(f"Limiting GREP commands from {len(grep_commands)} to 4")
                    grep_commands = grep_commands[:4]
                # Mark all GREP tasks as running
                for cmd in grep_commands:
                    cmd_key = cmd_to_key.get(id(cmd))
                    if cmd_key and cmd_key in task_ids:
                        task_id = task_ids[cmd_key]
                        task_tracker.start_task(task_id)
                        if progress_callback:
                            try:
                                task = task_tracker.tasks[task_id]
                                last_task_update_time = time.time()
                                progress_callback(json.dumps({
                                    "type": "task_update",
                                    "task": {
                                        "id": task["id"],
                                        "title": task.get("title", task.get("description", "")),
                                        "type": task.get("type", ""),
                                        "status": task["status"],
                                        "started_at": task["started_at"]
                                    }
                                }), 2, 4)
                            except Exception as e:
                                logger.debug(f"Progress callback failed: {e}")
                                pass
                # Execute greps in parallel
                def execute_grep(cmd):
                    """Execute a single GREP command."""
                    try:
                        # Check cancellation before starting
                        if cancellation_flag.is_set():
                            return {"type": "cancelled", "command": cmd}
                        
                        pattern = cmd.get("pattern")
                        if not pattern:
                            return {"type": "error", "command": cmd, "error": "GREP command missing 'pattern' field"}
                        
                        # Check timeout before GREP
                        elapsed = time.time() - agent_start_time
                        if elapsed > agent_timeout * 0.8:
                            return {"type": "timeout", "command": cmd, "error": "Timeout approaching"}
                        
                        matches = explorer.grep_pattern(pattern, max_results=100, cancellation_flag=cancellation_flag)
                        # Limit matches to prevent excessive processing
                        MAX_MATCHES_PER_FILE = 20
                        MAX_TOTAL_MATCHES = 100
                        
                        # Limit matches to top 20 files immediately
                        if len(matches) > 20:
                            sorted_matches = sorted(matches.items(), key=lambda x: len(x[1]), reverse=True)
                            matches = dict(sorted_matches[:20])
                        
                        cmd_results = []
                        match_count = 0
                        file_cache_grep = {}
                        
                        # Collect files that need to be read
                        files_to_read = list(matches.keys())
                        
                        # Read files in parallel
                        if files_to_read:
                            def read_file_for_grep(file_path):
                                """Read a file for GREP processing."""
                                try:
                                    file_data = self.code_reader.read_file(file_path)
                                    if file_data.get("success"):
                                        content = file_data.get("content", "")
                                        if content:
                                            return file_path, content.split('\n')
                                    return file_path, None
                                except Exception as e:
                                    logger.warning(f"Failed to read {file_path} for GREP: {e}")
                                    return file_path, None
                            
                            # Read files in parallel (max 6 workers)
                            max_workers = min(6, len(files_to_read))
                            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                                future_to_file = {executor.submit(read_file_for_grep, fp): fp for fp in files_to_read}
                                for future in as_completed(future_to_file):
                                    # Check cancellation flag in loop
                                    if cancellation_flag.is_set():
                                        break
                                    file_path, file_lines = future.result()
                                    if file_lines:
                                        file_cache_grep[file_path] = file_lines
                        
                        # Extract contexts from cached files
                        for file_path, lines in matches.items():
                            # Check cancellation flag in loop
                            if cancellation_flag.is_set():
                                break
                            if match_count >= MAX_TOTAL_MATCHES:
                                break
                            
                            # Skip if file wasn't read successfully
                            if file_path not in file_cache_grep:
                                continue
                            
                            # Limit matches per file
                            limited_lines = lines[:MAX_MATCHES_PER_FILE]
                            file_lines = file_cache_grep[file_path]
                            
                            # Extract context for each match
                            for line_num in limited_lines:
                                # Check cancellation flag in inner loop
                                if cancellation_flag.is_set():
                                    break
                                if match_count >= MAX_TOTAL_MATCHES:
                                    break
                                # Validate line number
                                if not isinstance(line_num, int) or line_num < 1:
                                    continue
                                # Extract context from cached file content
                                context_lines = 3
                                line_idx = line_num - 1
                                if line_idx >= len(file_lines):
                                    continue
                                start_line = max(0, line_idx - context_lines)
                                end_line = min(len(file_lines), line_idx + context_lines + 1)
                                if start_line < end_line:
                                    context = '\n'.join(file_lines[start_line:end_line])
                                else:
                                    context = file_lines[line_idx] if line_idx < len(file_lines) else ""
                                cmd_results.append({
                                    "type": "grep",
                                    "file": file_path,
                                    "line": line_num,
                                    "context": context
                                })
                                match_count += 1
                        
                        return {"type": "success", "command": cmd, "results": cmd_results}
                    except Exception as e:
                        logger.warning(f"GREP failed for '{cmd.get('pattern', 'unknown')}': {e}")
                        return {"type": "error", "command": cmd, "error": str(e)}
                
                # Execute greps in parallel
                max_workers = min(4, len(grep_commands))  # Cap at 4 workers
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    grep_futures = {executor.submit(execute_grep, cmd): cmd for cmd in grep_commands}
                    for future in as_completed(grep_futures):
                        cmd = grep_futures[future]
                        cmd_key = cmd_to_key.get(id(cmd))
                        try:
                            result = future.result()
                            if result["type"] == "success":
                                results.extend(result["results"])
                                result_count = len(result["results"])
                                # Limit results during collection to prevent unbounded growth
                                if len(results) > MAX_RESULTS_DURING_COLLECTION:
                                    # Keep most relevant results (sort by score if available)
                                    results = sorted(results, key=lambda x: x.get('score', 0), reverse=True)[:MAX_RESULTS_DURING_COLLECTION]
                            else:
                                results.append(result)
                                result_count = 0
                            # Mark task as completed
                            if cmd_key and cmd_key in task_ids:
                                task_id = task_ids[cmd_key]
                                error = result.get("error") if result["type"] == "error" else None
                                task_tracker.complete_task(task_id, result_count, error)
                                if progress_callback:
                                    try:
                                        task = task_tracker.tasks[task_id]
                                        last_task_update_time = time.time()
                                        phase_counters["greps"]["current"] += 1
                                        progress_callback(json.dumps({
                                            "type": "task_update",
                                            "task": {
                                                "id": task["id"],
                                                "title": task.get("title", task.get("description", "")),
                                                "type": task.get("type", ""),
                                                "status": task["status"],
                                                "progress": task["progress"],
                                                "ended_at": task["ended_at"],
                                                "duration_ms": task["duration_ms"]
                                            }
                                        }), 2, 4)
                                        if phase_counters["greps"]["total"] > 0:
                                            progress_callback(json.dumps({
                                                "type": "progress",
                                                "phase": "greps",
                                                "current": phase_counters["greps"]["current"],
                                                "total": phase_counters["greps"]["total"],
                                                "percentage": int((phase_counters["greps"]["current"] / phase_counters["greps"]["total"]) * 100)
                                            }), 2, 4)
                                    except Exception as e:
                                        logger.debug(f"Progress callback failed: {e}")
                                        pass
                        except Exception as e:
                            logger.warning(f"Error processing GREP result: {e}")
                            if cmd_key and cmd_key in task_ids:
                                task_id = task_ids[cmd_key]
                                task_tracker.complete_task(task_id, 0, str(e))
                if grep_count > 0:
                    greps_ms = int((time.time() - greps_start) * 1000)
                    self._log_perf_metric("greps", count=grep_count, ms=greps_ms)
                    logger.info(f"After GREP: elapsed={time.time() - agent_start_time:.1f}s, greps={grep_count}, duration={greps_ms}ms")
                    # Check timeout after GREP operations with 5s buffer for early termination
                    elapsed_time = time.time() - agent_start_time
                    time_remaining = agent_timeout - elapsed_time
                    if time_remaining <= 5.0:  # 5s buffer - return partial results if timeout approaching
                        logger.warning(f"Timeout approaching after GREP (within 5s buffer): {elapsed_time:.1f}s/{agent_timeout}s, {time_remaining:.1f}s remaining")
                        if cancellation_flag.is_set() or elapsed_time >= agent_timeout:
                            return {"exit": True, "skip": False, "result": f"Agent mode timed out after {elapsed_time/60:.1f} minutes - GREP operations took too long. Please try a more specific question."}
                        # Cancel remaining operations and return partial results
                        cancellation_flag.set()
                        logger.warning("Cancelling remaining operations due to timeout approaching - returning partial results")
                        trace_commands = []
                    elif elapsed_time > agent_timeout * 0.8:  # Changed from 0.9 to 0.8 for earlier detection
                        logger.warning(f"Timeout approaching after GREP: {elapsed_time:.1f}s/{agent_timeout}s ({elapsed_time/agent_timeout*100:.1f}%)")
                        if cancellation_flag.is_set() or elapsed_time > agent_timeout:
                            return {"exit": True, "skip": False, "result": f"Agent mode timed out after {elapsed_time/60:.1f} minutes - GREP operations took too long. Please try a more specific question."}
                        # Cancel remaining operations
                        cancellation_flag.set()
                        logger.warning("Cancelling remaining operations due to timeout")
                        trace_commands = []
            # Execute other commands sequentially (TRACE, etc.)
            for cmd in other_commands:
                # Mark task as running and emit task_update
                cmd_key = cmd_to_key.get(id(cmd))
                if cmd_key and cmd_key in task_ids:
                    task_id = task_ids[cmd_key]
                    task_tracker.start_task(task_id)
                    # Emit task_update event
                    if progress_callback:
                        try:
                            task = task_tracker.tasks[task_id]
                            last_task_update_time = time.time()
                            progress_callback(json.dumps({
                                "type": "task_update",
                                "task": {
                                    "id": task["id"],
                                    "title": task.get("title", task.get("description", "")),
                                    "type": task.get("type", ""),
                                    "status": task["status"],
                                    "started_at": task["started_at"]
                                }
                            }), 2, 4)
                        except Exception as e:
                            logger.debug(f"Progress callback failed: {e}")
                            pass
                cmd_results = []
                try:
                    # Note: SEARCH and GREP commands are now handled in parallel above, so they won't be in other_commands
                    if cmd["type"] == "TRACE":
                        if trace_count == 0:
                            traces_start = time.time()
                        trace_count += 1
                        start = cmd.get("start")
                        end = cmd.get("end")
                        if not start or not end:
                            logger.warning(f"TRACE command missing 'start' or 'end' field: {cmd}")
                            cmd_results.append({
                                "type": "error",
                                "command": cmd,
                                "error": "TRACE command missing 'start' or 'end' field"
                            })
                        else:
                            trace_results = explorer.trace_data_flow(start, end)
                            cmd_results.extend([{"type": "trace", **r} for r in trace_results])
                    # Note: GREP commands are now handled in parallel above, so they won't be in other_commands
                except Exception as e:
                    # Categorize error and determine retry strategy
                    error_category, should_retry, error_context = self._categorize_error(e, cmd)
                    
                    # Retry logic for transient errors using RetryHandler
                    if should_retry and error_category == 'transient':
                        # Define command execution function for retry
                        def execute_command_with_retry():
                            """Execute command - used by RetryHandler."""
                            # Check cancellation before retry
                            if cancellation_flag.is_set():
                                raise Exception("Command cancelled")
                            
                            # Check timeout before retry
                            elapsed = time.time() - agent_start_time
                            if elapsed > agent_timeout * 0.8:
                                raise TimeoutError("Timeout approaching, skipping retry")
                            
                            # Re-execute command based on type
                            if cmd["type"] == "READ":
                                return self._execute_single_read_command(cmd, file_cache, file_relationships, discovered_files, files_read_tracker, turn_num, MAX_FILE_CACHE_SIZE)
                            elif cmd["type"] == "SEARCH":
                                term = cmd.get("term")
                                search_results = explorer.search_concept(term, max_results=min(10, config.max_search_results), cancellation_flag=cancellation_flag)
                                return [{"type": "search", "file": r.get("file"), "line": r.get("line"), "match": r.get("match"), "context": r.get("context")} for r in search_results]
                            elif cmd["type"] == "GREP":
                                pattern = cmd.get("pattern")
                                grep_results = explorer.grep_pattern(pattern, max_results=50, cancellation_flag=cancellation_flag)
                                # Convert grep_results dict to list format
                                retry_results = []
                                for file_path, lines in grep_results.items():
                                    for line_num in lines[:20]:  # Limit to 20 matches per file
                                        retry_results.append({
                                            "type": "grep",
                                            "file": file_path,
                                            "line": line_num,
                                            "match": f"Pattern found at line {line_num}",
                                            "context": ""
                                        })
                                return retry_results
                            elif cmd["type"] == "TRACE":
                                start = cmd.get("start")
                                end = cmd.get("end")
                                trace_results = explorer.trace_data_flow(start, end)
                                return [{"type": "trace", **r} for r in trace_results]
                            else:
                                return []
                        
                        # Use RetryHandler with circuit breaker
                        try:
                            retry_results = self.retry_handler.retry_with_backoff(
                                func=execute_command_with_retry,
                                max_retries=config.max_retries,
                                initial_delay=config.retry_initial_delay,
                                max_delay=config.retry_max_delay,
                                exponential_base=2.0,
                                retry_on=(Exception,),
                                circuit_breaker_key=f"command_{cmd['type']}"
                            )
                            
                            # If retry succeeded, add results
                            if retry_results:
                                cmd_results.extend(retry_results)
                                logger.info(f"Retry succeeded for {cmd['type']} command using RetryHandler")
                                continue
                        except Exception as retry_error:
                            # RetryHandler exhausted all retries or circuit breaker opened
                            logger.warning(f"RetryHandler failed for {cmd['type']} command: {retry_error}")
                            # Fall through to error handling
                    
                    # Error handling (for permanent errors or failed retries)
                    logger.warning(f"Command execution failed: {cmd}, error: {e}, category: {error_category}")
                    
                    # Create specific error message based on error type
                    error_msg = str(e)
                    suggestion = None
                    
                    if cmd["type"] == "READ":
                        file_path = cmd.get("file", "")
                        suggestion = self._suggest_similar_files(file_path)
                        if "not found" in error_msg.lower() or "does not exist" in error_msg.lower():
                            error_msg = f"File '{file_path}' not found. {suggestion if suggestion else 'Check the file path.'}"
                    elif cmd["type"] == "SEARCH":
                        if "timeout" in error_msg.lower():
                            error_msg = f"Search timed out. Try a more specific search term or use GREP with a pattern."
                        else:
                            error_msg = f"Search failed: {error_msg}. Try a more specific search term or use GREP with a pattern."
                        suggestion = "Try a more specific search term or use GREP with a pattern"
                    elif cmd["type"] == "GREP":
                        if "invalid" in error_msg.lower() or "regex" in error_msg.lower():
                            error_msg = f"Invalid regex pattern: {error_msg}. Check the pattern syntax."
                        else:
                            error_msg = f"GREP failed: {error_msg}"
                        suggestion = "Check the pattern syntax. Use READ to see the file first."
                    elif cmd["type"] == "TRACE":
                        error_msg = f"Trace failed: {error_msg}. Verify the start and end points exist."
                        suggestion = "Verify the start and end points exist and are accessible."
                    
                    error_info = {
                        "type": "error",
                        "command": cmd,
                        "error": error_msg,
                        "error_category": error_category,
                        "error_context": error_context,  # Include detailed error context
                        "suggestions": suggestion
                    }
                    cmd_results.append(error_info)
                # Aggregate errors if any
                errors_in_results = [r for r in cmd_results if r.get("type") == "error"]
                if errors_in_results:
                    error_summary = self._aggregate_errors(errors_in_results)
                    if error_summary["total"] > 0:
                        logger.info(f"Aggregated {error_summary['total']} errors: {error_summary['summary']}")
                
                # Add command results to main results
                results.extend(cmd_results)
                # Limit results during collection to prevent unbounded growth
                if len(results) > MAX_RESULTS_DURING_COLLECTION:
                    # Score and sort by relevance before limiting
                    scored_results = [(self._score_result_relevance(r, message, files_read_tracker), r) for r in results]
                    scored_results.sort(reverse=True, key=lambda x: x[0])
                    results = [r for _, r in scored_results[:MAX_RESULTS_DURING_COLLECTION]]
                # Mark task as completed and emit task_update
                if cmd_key and cmd_key in task_ids:
                    task_id = task_ids[cmd_key]
                    result_count = sum(1 for r in cmd_results if r.get("type") != "error")
                    error = next((r.get("error") for r in cmd_results if r.get("type") == "error"), None)
                    task_tracker.complete_task(task_id, result_count, error)
                    # Emit task_update event
                    if progress_callback:
                        try:
                            task = task_tracker.tasks[task_id]
                            last_task_update_time = time.time()
                            # Update phase counters
                            if cmd["type"] == "GREP":
                                phase_counters["greps"]["current"] += 1
                            elif cmd["type"] == "SEARCH":
                                phase_counters["searches"]["current"] += 1
                            elif cmd["type"] == "TRACE":
                                phase_counters["traces"]["current"] += 1
                            progress_callback(json.dumps({
                                "type": "task_update",
                                "task": {
                                    "id": task["id"],
                                    "title": task.get("title", task.get("description", "")),
                                    "type": task.get("type", ""),
                                    "status": task["status"],
                                    "progress": task["progress"],
                                    "ended_at": task["ended_at"],
                                    "duration_ms": task["duration_ms"],
                                    "note": task.get("note")
                                }
                            }), 2, 4)
                            # Emit progress event for the phase
                            phase_name = None
                            if cmd["type"] == "GREP":
                                phase_name = "greps"
                            elif cmd["type"] == "SEARCH":
                                phase_name = "searches"
                            elif cmd["type"] == "TRACE":
                                phase_name = "traces"
                            if phase_name and phase_counters[phase_name]["total"] > 0:
                                progress_callback(json.dumps({
                                    "type": "progress",
                                    "phase": phase_name,
                                    "current": phase_counters[phase_name]["current"],
                                    "total": phase_counters[phase_name]["total"],
                                    "percentage": int((phase_counters[phase_name]["current"] / phase_counters[phase_name]["total"]) * 100)
                                }), 2, 4)
                        except Exception as e:
                            logger.debug(f"Progress callback failed: {e}")
                            pass
            # Log performance metrics for searches and traces after all commands complete
            if search_count > 0:
                searches_ms = int((time.time() - searches_start) * 1000)
                self._log_perf_metric("searches", count=search_count, ms=searches_ms)
            if trace_count > 0:
                traces_ms = int((time.time() - traces_start) * 1000)
                self._log_perf_metric("traces", count=trace_count, ms=traces_ms)
            # Send final task update after all commands complete
            if progress_callback and task_ids:
                try:
                    import json
                    progress_callback(json.dumps({
                        "type": "tasks",
                        "tasks": task_tracker.get_tasks()
                    }), 2, 4)
                except Exception as e:
                    logger.debug(f"Progress callback failed: {e}")
                    pass  # Fallback if JSON fails
            # Show what the agent found - SINGLE PASS OPTIMIZATION
            # Process all results in one pass to collect statistics and error suggestions
            file_set = set()
            error_count = 0
            permanent_error_count = 0  # Track permanent errors separately
            match_count = 0
            error_suggestions = []
            has_actual_paths = False
            has_errors = False
            
            for r in results:
                # Check cancellation flag in loop
                if cancellation_flag.is_set():
                    break
                # Collect file information
                file_path = r.get("file")
                if file_path:
                    file_set.add(file_path)
                    if "backend/" in str(file_path) or "frontend/" in str(file_path):
                        has_actual_paths = True
                
                # Count by type
                r_type = r.get("type")
                if r_type == "error":
                    error_count += 1
                    has_errors = True
                    # Check if this is a permanent error (from error_category field)
                    error_category = r.get("error_category", "unknown")
                    if error_category == "permanent":
                        permanent_error_count += 1
                    # Build error suggestions
                    if r.get("suggestions"):
                        error_suggestions.append(f"💡 {r.get('suggestions')}")
                    else:
                        cmd = r.get('command', {})
                        error_suggestions.append(f"💡 Command failed: {cmd.get('type', 'unknown')} - {r.get('error', 'unknown error')}")
                elif r_type in ["grep", "search"]:
                    match_count += 1
            
            # Update cumulative error counts
            cumulative_error_count += error_count
            cumulative_permanent_error_count += permanent_error_count
            
            # Build result summary for progress callback
            if progress_callback and results:
                result_summary = []
                if file_set:
                    result_summary.append(f"{len(file_set)} file(s)")
                if match_count > 0:
                    result_summary.append(f"{match_count} match(es)")
                if error_count > 0:
                    result_summary.append(f"{error_count} error(s)")
                if result_summary:
                    progress_callback(f"✅ Found: {', '.join(result_summary)}", 2, 4)
            
            # Format results and add to conversation
            # Limit results before formatting to prevent huge formatted strings
            if results:
                MAX_RESULTS_TO_FORMAT = 50  # Only format top 50 results
                if len(results) > MAX_RESULTS_TO_FORMAT:
                    # Prioritize: errors first, then reads, then searches/greps
                    errors = [r for r in results if r.get("type") == "error"]
                    reads = [r for r in results if r.get("type") == "read"][:20]
                    others = [r for r in results if r.get("type") not in ["error", "read"]][:MAX_RESULTS_TO_FORMAT - len(errors) - len(reads)]
                    results_to_format = errors + reads + others
                    logger.info(f"Limiting results formatting from {len(results)} to {len(results_to_format)}")
                else:
                    results_to_format = results
                # Format findings with timeout protection
                findings_text = self._execute_with_timeout(
                    self._format_findings,
                    TIMEOUT_FORMAT_FINDINGS,
                    "Results formatting timed out. Please try again.",
                    results_to_format
                )
            
            # Build error warning
            error_warning = ""
            if has_errors:
                error_warning = f"\n\n⚠️ WARNING: {error_count} command(s) failed during execution. Results may be incomplete."
            reminder = ""
            if not has_actual_paths and turn_num > 1:
                reminder = "\n\n⚠️ REMINDER: You need to read ACTUAL code files. Use READ commands on specific files (e.g., READ backend/services/ocr_service.py) to get real file paths and line numbers. Don't make suggestions based on assumptions.\n"
            elif len(files_read_tracker) == 0 and turn_num > 0:
                reminder = "\n\n⚠️ REMINDER: You haven't read any files yet. Use READ command on files mentioned in the problem before making suggestions.\n"
            progress_note = ""
            if files_read_tracker:
                progress_note = f"\n\n📚 Progress: {len(files_read_tracker)} file(s) read so far. Continue exploring or use ANALYZE when ready."
            # Show discovered files that haven't been read yet
            discovered_note = ""
            if discovered_files and len(discovered_files) <= 5:
                discovered_note = f"\n\n🔍 Discovered files (not yet read): {', '.join(list(discovered_files)[:5])}. Consider reading these with READ command."
            # Show related files based on relationships
            related_files_note = ""
            related = set()
            if file_relationships and len(files_read_tracker) > 0:
                related = self._find_related_files(files_read_tracker, file_relationships, discovered_files)
            if related:
                related_files_note = f"\n\n🔗 Related files (based on imports/relationships): {', '.join(list(related)[:3])}. These might be relevant."
            # Show runtime integration hints
            runtime_hints = ""
            if turn_num > 1 and len(files_read_tracker) >= 2:
                runtime_hints = self._generate_runtime_integration_hints(message, files_read_tracker, results)
            if runtime_hints:
                runtime_hints = f"\n\n🔧 Runtime Integration Hints:\n{runtime_hints}"
            # Context summary if we have multiple turns
            context_summary = ""
            if turn_num > 2 and len(key_insights) > 0:
                context_summary = f"\n\n📝 Key insights so far:\n" + "\n".join(f"  - {insight}" for insight in key_insights[-5:])  # Last 5 insights
            # Extract insights from results
            new_insights = self._extract_insights_from_results(results, files_read_tracker)
            key_insights.extend(new_insights)
            # Limit key_insights to prevent unbounded growth (keep last 50)
            MAX_KEY_INSIGHTS = 50
            if len(key_insights) > MAX_KEY_INSIGHTS:
                key_insights = key_insights[-MAX_KEY_INSIGHTS:]
                logger.debug(f"Limited key_insights to {MAX_KEY_INSIGHTS} (kept most recent)")
            # CONFIDENCE CALCULATION DURING EXPLORATION (after READ/GREP)
            # Calculate confidence after each exploration step to track progress
            current_confidence = self._calculate_confidence_score(
            files_read=files_read_tracker,
            commands_history=commands_history,
            key_insights=key_insights,
            validation_issues=[],
            verification_results=getattr(self, '_last_verification_results', None),
            code_match_accuracy=None,  # Not available during exploration
            runtime_checks=None,  # Not available during exploration
            error_count=cumulative_error_count,  # Pass cumulative error count
            permanent_error_count=cumulative_permanent_error_count  # Pass cumulative permanent error count
            )
            # Log confidence progress
            logger.info(f"Exploration confidence after turn {turn_num + 1}: {current_confidence:.0%} (files: {len(files_read_tracker)}, commands: {len(commands_history)})")
            # Add confidence indicator to progress note
            confidence_note = ""
            if current_confidence < 0.5:
                confidence_note = f"\n\n⚠️ Low confidence ({current_confidence:.0%}) - Consider reading more files and verifying functions with GREP"
            elif current_confidence < 0.7:
                confidence_note = f"\n\n📊 Confidence: {current_confidence:.0%} - Good progress, but more exploration recommended before ANALYZE"
            elif current_confidence >= 0.7:
                confidence_note = f"\n\n✅ Confidence: {current_confidence:.0%} - Ready for analysis"
            # Smart suggestions if agent seems stuck
            smart_suggestions = ""
            if not commands and turn_num > 0:
                smart_suggestions = self._execute_with_timeout(
                    self._generate_smart_suggestions,
                    TIMEOUT_SUGGESTIONS,
                    "",
                    message,
                    files_read_tracker,
                    results,
                    discovered_files,
                    commands_history
                )
            error_help = ""
            if error_suggestions:
                error_help = "\n\n" + "\n".join(error_suggestions)
                user_message = f"Exploration results:\n\n{findings_text}{error_warning}{reminder}{progress_note}{confidence_note}{discovered_note}{related_files_note}{context_summary}{error_help}{runtime_hints}{smart_suggestions}\n\nBefore suggesting fixes, remember:\n1. READ actual code files first - use READ command on files mentioned\n2. VERIFY FUNCTION NAMES - use GREP before mentioning any function (e.g., GREP 'def upload')\n3. VERIFY FRAMEWORK - use GREP to check FastAPI vs Flask (e.g., GREP '@app\\.|from fastapi')\n4. VERIFY LOGGING - use GREP to check if logging exists before claiming it does\n5. NEVER MAKE UP CODE - only quote code you've actually READ\n6. Use ACTUAL file paths (e.g., backend/main.py:561) not generic names\n7. Ask for SPECIFIC runtime data: exact log searches, SQL queries, curl commands\n8. Prioritize by likelihood (90%, 5%, 5%) - focus on MOST LIKELY first\n9. Provide EXACT logging code with real variable names from the ACTUAL code\n10. Focus on PRIMARY issue (why data is empty) not secondary (error handling)\n11. TRACE actual execution path through real code, not assumptions\n\nVALIDATION CHECKLIST before ANALYZE:\n□ All function names verified with GREP\n□ Framework detected (FastAPI/Flask) with GREP\n□ All code examples from actual READ files\n□ All logging claims verified with GREP\n□ All file paths are actual paths from READ\n\nContinue exploring (use READ/GREP to understand actual code) or use ANALYZE to provide your analysis (only after reading code)."
            else:
                # If no results and no commands, remind agent to use tools
                if not commands:
                    # Don't increment turn if nothing happened (prevent wasted turns)
                    smart_suggestions = self._execute_with_timeout(
                        self._generate_smart_suggestions,
                        5.0,
                        "",
                        message,
                        files_read_tracker,
                        [],
                        discovered_files,
                        commands_history
                    )
                    user_message = f"You need to use tools to explore the codebase. Try:\n- READ backend/services/ocr_service.py (or other files mentioned in the problem)\n- GREP insert_line_items (to find function definitions)\n- SEARCH line items (to find related code)\n\nDon't make suggestions without reading the actual code first.{smart_suggestions}"
                    # Don't increment turns here - skip rest of turn to retry same turn
                    conversation_context.append({
                        "role": "user",
                        "content": user_message
                    })
                    return {"exit": False, "skip": True}  # Skip turn, retry
                else:
                    user_message = "No results found. Try a different search or use READ command on specific files mentioned in the problem."
                    conversation_context.append({
                        "role": "user",
                        "content": user_message
                    })
            # Normal end of turn
            return {"exit": False, "skip": False}
        
        def _run_agent_core():
            """Core agent execution logic extracted from try block."""
            # == AGENT_CORE_START ==
            nonlocal agent_start_time  # Must declare as nonlocal to see reset value from outer scope
            # Note: agent_start_time was reset earlier (line 4426) before any blocking operations
            # Use the same reset value throughout
            elapsed_since_reset = time.time() - agent_start_time
            logger.info(f"Agent core loop starting (timeout: {agent_timeout/60:.1f} minutes, elapsed since reset: {elapsed_since_reset:.1f}s)")
            turns = 0
            while True:
                outcome = _do_one_turn(turns)
                if outcome.get("exit"):
                    # If there's a result string, return it (for timeouts/errors)
                    if outcome.get("result"):
                        return outcome["result"]
                    # Otherwise, break to proceed to final analysis
                    break
                # Preserve prior semantics: a skipped turn still counts
                if not outcome.get("skip"):
                    turns += 1
                if turns >= max_turns:
                    break
            # Final analysis (outside while loop, inside helper function)
            # Log if we reached max turns
            if turns >= max_turns:
                logger.warning(f"Reached max turns ({max_turns}), forcing analysis")
            # Validation note based on what was actually read
            validation_note = ""
            if len(files_read_tracker) == 0:
                validation_note = "\n\n⚠️ WARNING: You haven't read any actual code files yet. Your analysis MUST be based on actual code you've read, not assumptions.\n"
            elif len(files_read_tracker) < 2:
                validation_note = f"\n\n📝 Note: You've read {len(files_read_tracker)} file(s). Make sure you've read all relevant files.\n"
            # Validate prompt template before sending
            template_prompt = f"""You've explored the codebase. Now provide your analysis.{validation_note}
                CRITICAL: FOCUS ON DIAGNOSIS AND ACTIONABLE TROUBLESHOOTING, NOT JUST DESCRIPTION

                REMEMBER: Write primarily in TEXT explaining the problem. Use small code snippets (3-5 lines max) with file:line references to illustrate your points. DO NOT dump entire files.

                Provide in this EXACT format:

                **Code Analysis** (based on actual code you READ):
                - **Files Read**: List files you actually read (read entire files to understand full context)
                - **Functions Found**: Actual function names from code (or missing functions if not found)
                - **Missing Methods/Functions**: List any methods or functions that are called but don't exist
                - **Existing Logging**: What logging already exists (with file:line references)
                - **Execution Path**: Actual code flow from files you READ (with file:line references)

                **Prioritized Diagnosis (by likelihood - MUST rank by probability):**

                1. **MOST LIKELY (90%): [Issue name]**
                   - **Location**: `backend/path/to/file.py:123-145` (actual file path from code you READ)
                   - **Existing Code**: Quote actual code snippet (3-5 lines) showing the problem
                   - **Issue Found**: Specific problem identified (missing method, mismatch, wrong reference, data not flowing, etc.)
                   - **Why It Happens**: Root cause explanation based on code analysis
                   - **How to Verify**: SPECIFIC steps to confirm this is the issue:
                     * Run: [exact command/query]
                     * Check: [exact log search or database query]
                     * Look for: [specific error message or data pattern]
                   - **Impact**: What happens when this issue occurs (what breaks, what doesn't work)

                2. **If that's not it (5%): [Issue name]**
                   - **Location**: `backend/path/to/file.py:200-220` (actual path from code you READ)
                   - **Issue Found**: Specific problem identified
                   - **How to Verify**: SPECIFIC steps to confirm
                   - **Impact**: What happens when this issue occurs

                3. **Least likely (5%): [Issue name]**
                   - **Location**: `backend/path/to/file.py:300-320` (actual path from code you READ)
                   - **Issue Found**: Specific problem identified
                   - **How to Verify**: SPECIFIC steps to confirm
                   - **Impact**: What happens when this issue occurs

                **Root Cause**: [Based on actual code analysis, not assumptions - e.g., "Missing method _is_vague_problem called at line 4307 but not defined in ChatService class", or "invoice_id vs doc_id mismatch: code sets invoice_id=doc_id but query uses invoice_id which may not match"]

                **Analysis Summary**:
                - **What's Missing**: [List missing methods, functions, imports, data, etc. found in code]
                - **What's Broken**: [List mismatches, wrong references, incorrect logic, data flow breaks found in code]
                - **Where It Occurs**: [Specific file:line references from code you READ]
                - **Why It Happens**: [Root cause explanation based on code analysis]
                - **Data Flow Issue**: [If applicable, explain where data flow breaks: "Data flows from A→B→C, but at B the invoice_id is set incorrectly, so C can't find the data"]

                **Actionable Next Steps** (in order of priority):
                1. [First verification step - specific command/query]
                2. [Second verification step - specific command/query]
                3. [If verified, then diagnostic step - specific action]

                FOCUS: Your goal is to DIAGNOSE problems and provide ACTIONABLE troubleshooting steps. Identify what's wrong, where it occurs, why it happens, and HOW TO VERIFY IT."""
            # Validate template
            template_validation = self.response_validator.validate_template(template_prompt)
            if not template_validation.is_valid:
                logger.warning(f"Prompt template validation issues: {template_validation.issues}")
            # Add validation checklist to prompt
            validation_checklist = "\n\nVALIDATION CHECKLIST - You MUST include:\n"
            validation_checklist += "□ Code Analysis section (with files read, functions found, missing methods)\n"
            validation_checklist += "□ Prioritized Diagnosis section (ranked by likelihood)\n"
            validation_checklist += "□ Root Cause section (specific problem identified)\n"
            validation_checklist += "□ Analysis Summary (what's missing, what's broken, where, why)\n"
            validation_checklist += "□ Code snippets are 3-5 lines max\n"
            validation_checklist += "□ File paths are full paths (backend/...)\n"
            validation_checklist += "□ Text-first explanations, not code dumps\n"
            validation_checklist += "□ FOCUS ON ANALYSIS - identify problems, not provide fixes\n"
            final_prompt = template_prompt + validation_checklist
            conversation_context.append({
                "role": "user",
                "content": final_prompt
            })
            # Get final response with multi-pass validation
            if progress_callback:
                progress_callback("Generating final response...", 4, 4)
            messages = [{"role": "system", "content": system_prompt}]
            messages.extend(conversation_context)  # Use all conversation history (local processing)
            max_validation_passes = 3
            validation_pass = 0
            final_response = None
            last_candidate_response = None  # Track last candidate for fallback
            while validation_pass < max_validation_passes:
                try:
                    response = requests.post(
                        f"{self.ollama_url}/api/chat",
                        json={
                            "model": self.model,
                            "messages": messages,
                            "stream": False,
                            "options": {
                                "temperature": 0.1,
                                "top_p": 0.9,
                                "num_predict": 2000,
                                "num_ctx": effective_context,
                            }
                        },
                        timeout=120
                    )
                    if response.status_code != 200:
                        raise Exception(f"Ollama API returned status {response.status_code}")
                    result = response.json()
                    candidate_response = result.get("message", {}).get("content", "")
                    last_candidate_response = candidate_response  # Track for fallback
                    if not candidate_response or not candidate_response.strip():
                        logger.warning(f"Empty response on validation pass {validation_pass + 1}")
                        validation_pass += 1
                        continue
                    # Validate response structure AND check for generic response
                    validation_result = self.response_validator.validate_response(candidate_response)
                    is_generic = self._is_generic_response(candidate_response, agent_mode=True)
                    
                    # NEW: Check for placeholder code
                    placeholder_issues = self._detect_placeholder_code(candidate_response)
                    has_placeholder_code = len(placeholder_issues) > 0
                    
                    # NEW: Verify function names exist
                    function_verification_issues = self._verify_function_names(candidate_response, files_read_tracker)
                    has_invalid_functions = len(function_verification_issues) > 0
                    
                    # NEW: Verify file paths exist
                    file_path_issues = self._verify_file_paths(candidate_response)
                    has_invalid_paths = len(file_path_issues) > 0
                    
                    # NEW: Validate code snippets match actual file content
                    code_snippet_issues = self._validate_code_snippets(candidate_response, files_read_tracker)
                    has_invalid_code_snippets = len(code_snippet_issues) > 0
                    
                    # NEW: Validate execution paths (A→B→C)
                    execution_path_issues = self._validate_execution_path(candidate_response, files_read_tracker)
                    has_invalid_execution_paths = len(execution_path_issues) > 0
                    
                    # NEW: Validate root cause section
                    root_cause_issues = self._validate_root_cause(candidate_response, files_read_tracker)
                    has_invalid_root_cause = len(root_cause_issues) > 0
                    
                    # Also check for required sections (Code Analysis, Prioritized Diagnosis, Root Cause, Analysis Summary)
                    response_lower = candidate_response.lower()
                    has_code_analysis = any(term in response_lower for term in ["code analysis", "files read", "files analyzed"])
                    has_diagnosis = any(term in response_lower for term in ["prioritized diagnosis", "most likely", "diagnosis"])
                    has_root_cause = any(term in response_lower for term in ["root cause", "cause"])
                    has_analysis_summary = any(term in response_lower for term in ["analysis summary", "what's missing", "what's broken", "where it occurs"])
                    
                    # Primary validation: strict requirements (REJECT if placeholder code or invalid functions/paths/snippets)
                    if (validation_result.is_valid and not is_generic and 
                        not has_placeholder_code and not has_invalid_functions and not has_invalid_paths and
                        not has_invalid_code_snippets and not has_invalid_execution_paths and
                        not has_invalid_root_cause and
                        (has_code_analysis or has_diagnosis or has_root_cause or has_analysis_summary)):
                        final_response = candidate_response
                        break
                    
                    # Secondary validation: accept response ONLY if no placeholder code or invalid functions/paths
                    elif (not has_placeholder_code and not has_invalid_functions and not has_invalid_paths and
                          not has_invalid_code_snippets and not has_invalid_execution_paths and
                          not has_invalid_root_cause and
                          (has_code_analysis or has_diagnosis or has_root_cause or has_analysis_summary) and 
                          len(candidate_response) > 200):
                        # Accept response if it has required sections and is substantial, even if validation has minor issues
                        logger.info(f"Accepting response with required sections despite validation issues (pass {validation_pass + 1})")
                        final_response = candidate_response
                        break
                    else:
                        issues = list(validation_result.issues) if not validation_result.is_valid else []
                        
                        # Add new validation issues
                        if has_placeholder_code:
                            issues.extend(placeholder_issues[:3])  # Limit to 3 issues
                        if has_invalid_functions:
                            issues.extend(function_verification_issues[:3])
                        if has_invalid_paths:
                            issues.extend(file_path_issues[:3])
                        if has_invalid_code_snippets:
                            issues.extend(code_snippet_issues[:3])
                        if has_invalid_execution_paths:
                            issues.extend(execution_path_issues[:3])
                        if has_invalid_root_cause:
                            issues.extend(root_cause_issues[:3])
                        
                        if is_generic:
                            issues.append("Response is too generic - needs specific code analysis with file:line references")
                        if not has_code_analysis:
                            issues.append("Missing 'Code Analysis' section - must list files you actually read")
                        if not has_diagnosis:
                            issues.append("Missing 'Prioritized Diagnosis' section - must rank issues by likelihood")
                        if not has_root_cause:
                            issues.append("Missing 'Root Cause' section - must identify the specific problem")
                        if not has_analysis_summary:
                            issues.append("Missing 'Analysis Summary' section - must list what's missing, what's broken, where it occurs, and why")
                        
                        logger.warning(f"Response validation failed on pass {validation_pass + 1}: {issues}")
                        if validation_pass < max_validation_passes - 1:
                            # Add feedback to conversation for next pass
                            feedback = f"\n\nYour previous response had these issues:\n" + "\n".join(f"- {issue}" for issue in issues[:5])
                            feedback += "\n\nCRITICAL: Your response MUST include:\n"
                            feedback += "1. **Code Analysis** section listing files you actually READ and missing methods/functions found\n"
                            feedback += "2. **Prioritized Diagnosis** section ranking issues by likelihood (90%, 5%, 5%)\n"
                            feedback += "3. **Root Cause** section identifying the specific problem\n"
                            feedback += "4. **Analysis Summary** section listing what's missing, what's broken, where it occurs, and why\n"
                            
                            # NEW: Add specific feedback about placeholder code
                            if has_placeholder_code:
                                feedback += "\n\n❌ PLACEHOLDER CODE DETECTED:\n"
                                feedback += "- DO NOT include placeholder code (functions with 'pass', empty implementations)\n"
                                feedback += "- Only include ACTUAL code snippets from files you READ\n"
                                feedback += "- If you haven't read a file, say 'I need to READ this file first' instead of guessing\n"
                            
                            # NEW: Add specific feedback about invalid functions
                            if has_invalid_functions:
                                feedback += "\n\n❌ INVALID FUNCTION NAMES:\n"
                                feedback += "- Verify function names exist using GREP before mentioning them\n"
                                feedback += "- Use actual function names from the codebase, not assumed names\n"
                                feedback += "- If a function doesn't exist, don't mention it\n"
                            
                            # NEW: Add specific feedback about invalid file paths
                            if has_invalid_paths:
                                feedback += "\n\n❌ INVALID FILE PATHS:\n"
                                feedback += "- Only reference files you have actually READ\n"
                                feedback += "- Use actual file paths from READ commands, not guessed paths\n"
                                feedback += "- Verify file paths exist before referencing them\n"
                            
                            feedback += "\nFOCUS ON ANALYSIS AND DIAGNOSIS - identify problems, not provide fixes. DO NOT provide generic troubleshooting advice. Base your response on actual code you READ."
                            conversation_context.append({
                                "role": "user",
                                "content": feedback
                            })
                            messages = [{"role": "system", "content": system_prompt}]
                            messages.extend(conversation_context)
                        validation_pass += 1
                except Exception as e:
                    logger.error(f"Final analysis call failed: {e}")
                    if validation_pass < max_validation_passes - 1:
                        validation_pass += 1
                        continue
                    else:
                        # Use last candidate or fallback
                        final_response = candidate_response if candidate_response else "Analysis generation failed. Please try again."
                        break
            if not final_response:
                # Use the last candidate response if available, even if validation failed
                if last_candidate_response and len(last_candidate_response) > 100:
                    logger.warning("Using last candidate response despite validation failure")
                    final_response = last_candidate_response
                else:
                    final_response = "Unable to generate a valid analysis response. Please try again or ask a more specific question."
            # Stop heartbeat and emit done event
            heartbeat_active.clear()
            if progress_callback:
                try:
                    all_tasks = task_tracker.get_tasks()
                    completed = sum(1 for t in all_tasks if t["status"] == "done")
                    failed = sum(1 for t in all_tasks if t["status"] == "failed")
                    duration_ms = int((time.time() - agent_start_time) * 1000)
                    progress_callback(json.dumps({
                        "type": "done",
                        "summary": {
                            "tasks_total": len(all_tasks),
                            "completed": completed,
                            "failed": failed,
                            "duration_ms": duration_ms
                        }
                    }), 4, 4)
                except Exception as e:
                    logger.debug(f"Progress callback failed: {e}")
                    pass
            return final_response
            # == AGENT_CORE_END ==
        
        # Note: agent_start_time was reset earlier (line 4426) before any blocking operations
        # Check if we've already timed out before starting agent core (fail fast if >10s)
        elapsed_before_start = time.time() - agent_start_time
        logger.info(f"Agent core ready to start (timeout: {agent_timeout/60:.1f} minutes ({agent_timeout}s), elapsed since reset: {elapsed_before_start:.1f}s)")
        
        # Fail fast if initialization takes too long (more aggressive than full timeout)
        if elapsed_before_start > TIMEOUT_INIT_MAX:  # Changed from agent_timeout to 10s for faster failure
            logger.warning(f"Agent mode timed out during initialization ({elapsed_before_start:.1f}s, {elapsed_before_start/60:.1f} minutes)")
            heartbeat_active.clear()
            if progress_callback:
                try:
                    progress_callback(json.dumps({
                        "type": "error",
                        "message": f"Agent mode timed out during initialization after {elapsed_before_start/60:.1f} minutes. Please try again."
                    }), 4, 4)
                except Exception as e:
                    logger.debug(f"Progress callback failed: {e}")
                    pass
            return f"Agent mode timed out during initialization after {elapsed_before_start/60:.1f} minutes. Please try again or use a more specific question."
        
        try:
            result = _run_agent_core()
        except Exception as e:
            logger.exception("Agent mode fatal error")
            # Stop heartbeat on error
            heartbeat_active.clear()
            if progress_callback:
                try:
                    progress_callback(json.dumps({
                        "type": "error",
                        "message": str(e)
                    }), 4, 4)
                except Exception as e:
                    logger.debug(f"Progress callback failed: {e}")
                    pass
            result = f"Agent mode fatal error: {str(e)}"
        finally:
            # Ensure heartbeat is stopped
            heartbeat_active.clear()
            # Wait for heartbeat thread to finish (with timeout)
            if 'heartbeat_thread' in locals():
                heartbeat_thread.join(timeout=1.0)
            # Log cache statistics if available
            if 'file_cache' in locals() and hasattr(file_cache, 'get_stats'):
                cache_stats = file_cache.get_stats()
                logger.info(f"File cache statistics: {cache_stats}")
                self._log_perf_metric("cache_stats", **cache_stats)
            # Emit done event if not already emitted
            if progress_callback:
                try:
                    all_tasks = task_tracker.get_tasks() if 'task_tracker' in locals() else []
                    completed = sum(1 for t in all_tasks if t.get("status") == "done")
                    failed = sum(1 for t in all_tasks if t.get("status") == "failed")
                    duration_ms = int((time.time() - agent_start_time) * 1000) if 'agent_start_time' in locals() else 0
                    progress_callback(json.dumps({
                        "type": "done",
                        "summary": {
                            "tasks_total": len(all_tasks),
                            "completed": completed,
                            "failed": failed,
                            "duration_ms": duration_ms
                        }
                    }), 4, 4)
                except Exception as e:
                    logger.debug(f"Progress callback failed: {e}")
                    pass
            # Clear agent mode flag
            self._in_agent_mode = False
        return result
    
    def _validate_response_quality(self, response: str, files_read: set) -> List[str]:
        """
        Validate that the response follows quality guidelines.
        
        Args:
            response: The response text to validate
            files_read: Set of files that were actually read
            
        Returns:
            List of validation issues found
        """
        issues = []
        
        # Check for actual file paths (not generic names)
        has_actual_paths = "backend/" in response or "frontend/" in response
        has_generic_paths = any(pattern in response.lower() for pattern in ["file.py", "ocr.py", "service.py", "utils.py"])
        
        if not has_actual_paths and has_generic_paths:
            issues.append("Response contains generic file names instead of actual paths")
        
        # Check if response mentions files that weren't read
        if files_read:
            mentioned_files = set()
            import re
            # Find file references in response
            file_pattern = r'([a-zA-Z0-9_/\\-]+\.(py|ts|tsx|js|jsx|json|md|txt|yaml|yml))'
            matches = re.findall(file_pattern, response)
            for match, ext in matches:
                # Normalize path
                path = match.replace('\\', '/')
                # Check if it's a full path
                if '/' in path and (path.startswith('backend/') or path.startswith('frontend/')):
                    mentioned_files.add(path)
            
            # Check if any mentioned files weren't actually read
            unread_files = mentioned_files - files_read
            if unread_files:
                issues.append(f"Response mentions files that weren't read: {', '.join(list(unread_files)[:3])}")
        
        # Check for code dumps (too much code, not enough explanation)
        code_blocks = response.count('```')
        if code_blocks > 10:
            issues.append("Response contains too many code blocks - should be text-first with small snippets")
        
        # Check for proper structure (should have sections)
        has_analysis = "analysis" in response.lower() or "diagnosis" in response.lower()
        has_root_cause = "root cause" in response.lower() or "issue" in response.lower()
        has_fix = "fix" in response.lower() or "solution" in response.lower()
        
        if not (has_analysis and has_root_cause and has_fix):
            issues.append("Response missing required sections: analysis, root cause, or fix")
        
        return issues
    
    def _calculate_confidence_score(
        self,
        files_read: set,
        commands_history: List[str],
        key_insights: List[str],
        validation_issues: List[str],
        verification_results: Optional[Dict],
        code_match_accuracy: Optional[float],
        runtime_checks: Optional[Dict],
        error_count: Optional[int] = None,
        permanent_error_count: Optional[int] = None
    ) -> float:
        """
        Calculate confidence score based on exploration quality, verification results,
        code match accuracy, runtime checks, and error rates.
        
        WEIGHTING: Function verification > file count (verification is more important)
        ERRORS: Permanent errors decrease confidence, transient errors don't affect it
        
        Args:
            files_read: Files that were read
            commands_history: History of commands used
            key_insights: Key insights learned
            validation_issues: Validation issues found
            verification_results: Optional verification results from CodeVerifier
            code_match_accuracy: Optional average code match accuracy (0.0-1.0)
            runtime_checks: Optional runtime verification results
            error_count: Optional total number of errors encountered
            permanent_error_count: Optional number of permanent errors encountered
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        score = 0.0
        
        # Base score from files read (max 0.15) - REDUCED from 0.25
        # Files are important but verification matters more
        files_score = min(len(files_read) / 5.0, 1.0) * 0.15
        score += files_score
        
        # Score from commands used (max 0.1) - REDUCED from 0.15
        if commands_history:
            unique_commands = len(set(cmd.split()[0] if isinstance(cmd, str) else cmd.get("type", "") for cmd in commands_history))
            commands_score = min(unique_commands / 4.0, 1.0) * 0.1
            score += commands_score
        
        # Score from insights (max 0.1)
        if key_insights:
            insights_score = min(len(key_insights) / 5.0, 1.0) * 0.1
            score += insights_score
        
        # Score from verification results (max 0.35) - INCREASED from 0.25
        # Function verification is MOST IMPORTANT - weighted higher than file count
        if verification_results:
            verification_score = 0.0
            func_verifications = verification_results.get("function_verifications", {})
            framework_results = verification_results.get("framework_results", {})
            
            # Check function verification pass rate (max 0.25) - INCREASED from 0.15
            if func_verifications:
                verified_count = sum(1 for v in func_verifications.values() if v.get("exists"))
                total_count = len(func_verifications)
                if total_count > 0:
                    verification_score += (verified_count / total_count) * 0.25
            
            # Check framework detection (max 0.1)
            if framework_results:
                framework_detected = any(r.get("confidence", 0) > 0.7 for r in framework_results.values())
                if framework_detected:
                    verification_score += 0.1
            
            score += verification_score
        
        # Score from code match accuracy (max 0.2) - INCREASED from 0.15
        # Code match accuracy is important for confidence
        if code_match_accuracy is not None:
            code_score = code_match_accuracy * 0.2
            score += code_score
        
        # Score from runtime checks (max 0.1)
        if runtime_checks:
            runtime_score = 0.0
            if runtime_checks.get("sql_queries"):
                successful_queries = sum(1 for q in runtime_checks["sql_queries"] if q.get("result", {}).get("success"))
                total_queries = len(runtime_checks["sql_queries"])
                if total_queries > 0:
                    runtime_score += (successful_queries / total_queries) * 0.05
            
            if runtime_checks.get("api_calls"):
                successful_apis = sum(1 for a in runtime_checks["api_calls"] if a.get("result", {}).get("success"))
                total_apis = len(runtime_checks["api_calls"])
                if total_apis > 0:
                    runtime_score += (successful_apis / total_apis) * 0.05
            
            score += runtime_score
        
        # Penalty for validation issues (max -0.3)
        if validation_issues:
            penalty = min(len(validation_issues) / 5.0, 1.0) * 0.3
            score -= penalty
        
        # Penalty for errors (max -0.4)
        # Permanent errors have more impact than transient errors
        if error_count is not None and error_count > 0:
            # Calculate error rate (errors per command)
            total_commands = len(commands_history) if commands_history else 1
            error_rate = min(error_count / max(total_commands, 1), 1.0)
            
            # Base penalty from error rate
            error_penalty = error_rate * 0.2
            
            # Additional penalty for permanent errors (more severe)
            if permanent_error_count is not None and permanent_error_count > 0:
                permanent_error_rate = min(permanent_error_count / max(error_count, 1), 1.0)
                # Permanent errors get 2x penalty
                permanent_penalty = permanent_error_rate * 0.2
                error_penalty += permanent_penalty
            
            score -= min(error_penalty, 0.4)  # Cap total error penalty at 0.4
            logger.debug(f"Error penalty applied: {error_penalty:.3f} (errors: {error_count}, permanent: {permanent_error_count})")
        
        # Bonus for diverse exploration (max +0.1)
        if len(files_read) >= 3 and len(commands_history) >= 5:
            score += 0.1
        
        return max(0.0, min(1.0, score))  # Clamp between 0 and 1
    
    def _extract_code_references(self, response_text: str, code_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract code file references from response text."""
        references = []
        
        # Add files that were read
        for file_path in code_context.get("files", []):
            file_data = self.code_reader.read_file(file_path, max_lines=5000)  # Increased for local
            if file_data.get("success"):
                references.append({
                    "file": file_path,
                    "lines": None,
                    "snippet": file_data["content"][:500]  # First 500 chars
                })
        
        return references

