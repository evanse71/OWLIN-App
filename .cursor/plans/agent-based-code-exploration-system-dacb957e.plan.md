---
name: Code Assistant Improvements Implementation Plan
overview: ""
todos:
  - id: 62c047a8-1ab9-4e9e-b428-34d49083d15c
    content: Create CodeExplorer service class with search_concept, grep_pattern, find_function_calls, trace_data_flow, find_related_files, read_function, and suggest_exploration_path methods
    status: pending
  - id: a2b17038-cce2-47e0-a0ac-81c38ae5ddd4
    content: Fix _build_prompt() to respect file_specs max_lines from optimized_context instead of hardcoding 800
    status: pending
  - id: fb63c6f4-c010-44a0-96e7-d3ccc426634b
    content: Modify _force_code_analysis() to include actual code snippets with line numbers instead of just file names
    status: pending
  - id: eec41139-8051-49c0-932f-c4f663bbe007
    content: Implement _needs_exploration() helper to detect vague debugging questions that need exploration
    status: pending
  - id: 2a726377-f73e-408d-a39a-23f901e89702
    content: Implement _agent_explore_and_analyze() method for single-turn exploration workflow
    status: pending
  - id: f663bc97-a37e-4237-8dd6-3955aa3a24fe
    content: Integrate agent exploration into chat() method - route debugging questions through agent workflow when _needs_exploration() returns True
    status: pending
  - id: e66d90da-a737-4456-b270-567dfc343856
    content: "Add helper methods: _parse_exploration_plan(), _format_findings(), _parse_agent_commands()"
    status: pending
  - id: 378bdefd-e550-4c29-b634-4685e77cab21
    content: Implement _agent_conversation() method for multi-turn agent conversations with command parsing
    status: pending
  - id: f637ae7b-cb7b-4e49-8f4f-8c07b8256224
    content: Add AGENT_SYSTEM_PROMPT and AGENT_DEBUGGING_PROMPT constants and integrate into agent workflows
    status: pending
---

# Code Assistant Improvements Implementation Plan

## Overview

Implement all suggested improvements to enhance the code assistant's performance, reliability, intelligence, and user experience. Organized by priority: Critical → Important → Nice-to-Have → Quick Wins.

## Phase 1: Critical Improvements (High Priority)

### 1.1 Performance & Scalability

**Goal:** Make code exploration fast and efficient on large codebases

**Tasks:**

- Add search result caching with TTL (5-minute default)
- Implement parallel search execution for multiple search terms
- Add file read caching (cache file contents for repeated reads)
- Optimize file scanning with early termination
- Add search result ranking improvements

**Files to Modify:**

- `backend/services/code_explorer.py` - Add caching infrastructure
- `backend/services/code_reader.py` - Add file read caching

**New Dependencies:**

- `functools.lru_cache` or custom cache implementation
- `concurrent.futures` for parallel execution

### 1.2 Memory Management

**Goal:** Prevent memory issues and respect token limits

**Tasks:**

- Implement token estimation function (`_estimate_tokens`)
- Add findings truncation based on token budget
- Add max findings limit (configurable, default 50)
- Implement smart truncation (prioritize high-score results)
- Add memory usage monitoring/logging

**Files to Modify:**

- `backend/services/chat_service.py` - Add token estimation and truncation
- `backend/services/code_explorer.py` - Add result limiting

### 1.3 Error Recovery & Retries

**Goal:** Make system resilient to transient failures

**Tasks:**

- Implement `_call_ollama_with_retry()` with exponential backoff
- Add retry logic to all Ollama API calls
- Implement circuit breaker pattern for repeated failures
- Add graceful degradation (fallback to simpler exploration)
- Improve error messages with actionable guidance

**Files to Modify:**

- `backend/services/chat_service.py` - Add retry wrapper
- Create `backend/services/retry_handler.py` (new file)

### 1.4 Exploration Plan Validation

**Goal:** Ensure exploration plans are valid before execution

**Tasks:**

- Implement `_validate_exploration_plan()` method
- Validate file paths exist before reading
- Validate search terms (length, format)
- Filter invalid function names
- Add plan sanitization (remove duplicates, normalize paths)

**Files to Modify:**

- `backend/services/chat_service.py` - Add validation logic

## Phase 2: Important Enhancements

### 2.1 Progress Feedback

**Goal:** Provide visibility into exploration progress

**Tasks:**

- Add progress callback interface
- Implement progress events for each exploration step
- Add progress reporting to frontend (if applicable)
- Log progress milestones
- Add estimated time remaining

**Files to Modify:**

- `backend/services/chat_service.py` - Add progress callbacks
- `backend/routes/chat_router.py` - Add progress streaming (optional)

### 2.2 Exploration Result Deduplication

**Goal:** Remove duplicate findings to improve quality

**Tasks:**

- Implement `_deduplicate_findings()` method
- Add smart deduplication (same file:line, different context)
- Merge similar findings
- Prioritize findings with better context
- Add deduplication metrics

**Files to Modify:**

- `backend/services/chat_service.py` - Add deduplication logic

### 2.3 Smarter Exploration Heuristics

**Goal:** Improve exploration path suggestions

**Tasks:**

- Enhance `suggest_exploration_path()` with import graph analysis
- Add file dependency tracking
- Implement code structure analysis
- Add pattern-based suggestions (e.g., "api" → find API routes)
- Use file co-occurrence statistics

**Files to Modify:**

- `backend/services/code_explorer.py` - Enhance suggestion logic
- Create `backend/services/import_analyzer.py` (new file)

### 2.4 Configuration & Limits

**Goal:** Make all limits configurable

**Tasks:**

- Create configuration class/schema
- Move hardcoded limits to config
- Add environment variable support
- Add runtime configuration updates
- Document all configuration options

**Files to Create/Modify:**

- `backend/services/explorer_config.py` (new file)
- `backend/services/code_explorer.py` - Use config
- `backend/services/chat_service.py` - Use config

## Phase 3: Nice-to-Have Features

### 3.1 Exploration Session Persistence

**Goal:** Save and restore exploration sessions

**Tasks:**

- Design session data structure
- Implement session save/load
- Add session metadata (timestamp, problem, findings)
- Create session browser UI (optional)
- Add session sharing capability

**Files to Create:**

- `backend/services/exploration_session.py` (new file)
- `backend/routes/exploration_sessions.py` (new file, optional)

### 3.2 Metrics & Analytics

**Goal:** Track exploration effectiveness

**Tasks:**

- Add exploration metrics tracking
- Track success rates, common patterns
- Log exploration paths taken
- Add performance metrics (time, files searched)
- Create analytics dashboard (optional)

**Files to Modify:**

- `backend/services/chat_metrics.py` - Add exploration metrics
- `backend/services/chat_service.py` - Log exploration data

### 3.3 Interactive Exploration

**Goal:** Allow users to guide exploration

**Tasks:**

- Add interactive exploration mode
- Allow users to approve/reject exploration steps
- Add "explore more" suggestions
- Implement exploration branching
- Add user feedback collection

**Files to Modify:**

- `backend/services/chat_service.py` - Add interactive mode
- `backend/routes/chat_router.py` - Add interactive endpoints

### 3.4 Code Change Suggestions

**Goal:** Generate actual code patches

**Tasks:**

- Parse LLM fix suggestions into code diffs
- Validate code changes (syntax, imports)
- Generate unified diff format
- Add "apply fix" capability (optional, dangerous)
- Preview changes before applying

**Files to Create:**

- `backend/services/code_patcher.py` (new file)

### 3.5 Multi-file Context Awareness

**Goal:** Better understanding of cross-file relationships

**Tasks:**

- Build import dependency graph
- Track data flow across files
- Identify related files automatically
- Add "context expansion" feature
- Visualize file relationships (optional)

**Files to Modify:**

- `backend/services/code_explorer.py` - Add dependency analysis
- Create `backend/services/dependency_graph.py` (new file)

### 3.6 Semantic Code Understanding

**Goal:** Use embeddings for semantic search

**Tasks:**

- Integrate embedding model (sentence-transformers)
- Add vector search capability
- Implement semantic similarity matching
- Cache embeddings for performance
- Add embedding-based code clustering

**Files to Create:**

- `backend/services/semantic_search.py` (new file)

## Phase 4: Quick Wins (Easy Improvements)

### 4.1 Timeout Management

**Tasks:**

- Add per-step timeouts to exploration
- Add total exploration timeout
- Improve timeout error messages

### 4.2 Logging & Statistics

**Tasks:**

- Add detailed exploration logging
- Log exploration statistics (files searched, time taken)
- Add exploration mode indicator in responses

### 4.3 Path Validation

**Tasks:**

- Validate all file paths before operations
- Add path normalization
- Handle relative/absolute path conversion

### 4.4 Result Limiting

**Tasks:**

- Add max findings limit (prevent memory issues)
- Implement result prioritization
- Add "top N" result selection

### 4.5 Error Messages

**Tasks:**

- Improve error messages with context
- Add actionable error guidance
- Include recovery suggestions

### 4.6 File Read Caching

**Tasks:**

- Cache file reads (same file requested multiple times)
- Add cache invalidation on file changes
- Implement cache size limits

## Implementation Order

**Sprint 1 (Critical):**

1. Memory Management (1.2)
2. Error Recovery & Retries (1.3)
3. Exploration Plan Validation (1.4)
4. Quick Wins: Timeout, Logging, Path Validation (4.1, 4.2, 4.3)

**Sprint 2 (Performance):**

1. Performance & Scalability (1.1)
2. Exploration Result Deduplication (2.2)
3. Configuration & Limits (2.4)
4. Quick Wins: Result Limiting, File Read Caching (4.4, 4.6)

**Sprint 3 (Enhancements):**

1. Progress Feedback (2.1)
2. Smarter Exploration Heuristics (2.3)
3. Quick Wins: Error Messages (4.5)

**Sprint 4 (Advanced Features):**

1. Metrics & Analytics (3.2)
2. Multi-file Context Awareness (3.5)
3. Code Change Suggestions (3.4)

**Sprint 5 (Future):**

1. Exploration Session Persistence (3.1)
2. Interactive Exploration (3.3)
3. Semantic Code Understanding (3.6)

## Success Criteria

- All critical improvements implemented and tested
- Performance: < 5s for typical exploration on medium codebase
- Memory: < 100MB for typical exploration
- Error rate: < 1% for valid exploration requests
- User satisfaction: Improved response quality and speed

## Testing Strategy

- Unit tests for each new feature
- Integration tests for exploration workflows
- Performance benchmarks
- Memory profiling
- Error scenario testing