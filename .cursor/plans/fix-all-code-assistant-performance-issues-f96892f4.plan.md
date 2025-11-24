<!-- f96892f4-c97f-4abb-a40c-fdf6d67786dc 42a77ae9-14a6-4814-961f-76b74591bde3 -->
# Code Assistant Critical Improvements (P0)

## Overview

Implement the four critical (P0) improvement categories to make the code assistant more reliable and beneficial for building apps. Focus on command parsing, error handling, result formatting, and validation.

## Implementation Plan

### 1. Enhanced Command Parsing (`backend/services/chat_service.py`)

**Current Issues:**

- Line-by-line parsing misses multi-line commands
- No validation before execution
- No deduplication of identical commands
- No handling of malformed commands

**Changes:**

**1.1 Multi-line Command Parsing** (around line 3364)

- Modify `_parse_agent_commands` to handle commands spanning multiple lines
- Use regex patterns to match commands across line breaks
- Handle continuation markers (backslash, indentation)

**1.2 Command Validation** (new method `_validate_command`)

- Pre-execution validation:
- READ: Check file exists (with path resolution)
- GREP: Validate regex pattern syntax
- SEARCH: Check term is not empty
- TRACE: Verify start/end are valid
- Return validation errors with suggestions

**1.3 Command Deduplication** (in `_do_one_turn` around line 5555)

- Track commands executed in current turn
- Remove duplicate commands before execution
- Log deduplication for debugging

**1.4 Fuzzy Matching & Path Resolution** (new method `_resolve_file_path`)

- Try multiple path variations (backend/, frontend/, root)
- Use fuzzy matching for typos (Levenshtein distance)
- Return best match with confidence score

**1.5 Command Aliases** (in `_parse_agent_commands`)

- Support synonyms: FIND → SEARCH, OPEN → READ
- Map aliases to canonical command types

### 2. Improved Error Handling (`backend/services/chat_service.py`)

**Current Issues:**

- Generic error messages
- No retry logic for transient failures
- Errors don't update confidence scores
- Silent failures in parallel execution

**Changes:**

**2.1 Error Categorization** (new method `_categorize_error`)

- Classify errors: permanent (file not found) vs transient (network timeout, file lock)
- Return error category and retry strategy

**2.2 Retry Logic with Exponential Backoff** (modify command execution around lines 5934-6256)

- Add retry wrapper for transient errors
- Exponential backoff: 1s, 2s, 4s
- Max 3 retries for transient errors
- No retries for permanent errors

**2.3 Specific Error Messages** (modify error handling around lines 6524-6530)

- Replace generic messages with specific, actionable ones
- Include suggestions based on error type
- Provide alternative commands or paths

**2.4 Error Aggregation** (new method `_aggregate_errors`)

- Collect errors from parallel operations
- Group similar errors
- Report summary with details

**2.5 Confidence Score Updates** (modify `_calculate_confidence_score` around line 7174)

- Decrease confidence on permanent errors
- Maintain confidence on transient errors (if retry succeeds)
- Track error rate in confidence calculation

### 3. Smart Result Formatting (`backend/services/chat_service.py`)

**Current Issues:**

- Content truncated to 500 chars (loses context)
- Results not prioritized by relevance
- No deduplication of similar results
- Large result sets slow LLM processing

**Changes:**

**3.1 Smart Content Truncation** (modify `_format_findings` around line 3297)

- Keep function definitions, remove comments
- Preserve code structure (indentation, brackets)
- Truncate intelligently at function/class boundaries
- Show line numbers for truncated sections

**3.2 Relevance Scoring** (new method `_score_result_relevance`)

- Score results based on:
- Match quality (exact vs partial)
- File importance (frequently accessed files)
- Context relevance (related to user query)
- Sort results by relevance score

**3.3 Result Deduplication** (new method `_deduplicate_results`)

- Identify similar results (same file, nearby lines)
- Merge similar results with line ranges
- Remove exact duplicates

**3.4 Result Summarization** (new method `_summarize_results`)

- For large result sets (>20), create summary first
- Show: file count, match count, key findings
- Provide "show details" option in prompt

**3.5 Progressive Disclosure** (modify result formatting)

- Show summaries first, details on demand
- Group results by file
- Highlight most relevant matches

### 4. Context-Aware Validation (`backend/services/chat_service.py`)

**Current Issues:**

- Function verification only checks existence, not context
- No validation of code snippets match actual content
- Validation happens after generation (should be during)
- No execution path validation

**Changes:**

**4.1 Context-Aware Function Verification** (modify `_verify_function_names` around line 2384)

- Check function exists AND is called correctly
- Verify function signature matches usage
- Check function is accessible (not private if called externally)
- Validate import statements for external functions

**4.2 Code Snippet Validation** (new method `_validate_code_snippets`)

- Extract code snippets from response
- Match against actual file content
- Flag mismatches (wrong code, wrong line numbers)
- Verify variable names match actual code

**4.3 Incremental Validation** (modify validation around lines 6918-6950)

- Validate during generation (streaming validation)
- Catch issues early (placeholder code, invalid functions)
- Provide feedback to LLM mid-generation
- Use validation results to guide retry

**4.4 Execution Path Validation** (new method `_validate_execution_path`)

- Parse execution paths from response (A→B→C)
- Verify each step exists (function/file exists)
- Check call chain is valid (B is called from A)
- Flag broken chains

**4.5 Enhanced Placeholder Detection** (modify `_detect_placeholder_code` around line 2380)

- Check for TODO/FIXME in context
- Detect incomplete function bodies
- Identify stub implementations
- Flag generic code patterns

## Files to Modify

1. `backend/services/chat_service.py`

- `_parse_agent_commands` (line 3364) - Enhanced parsing
- `_format_findings` (line 3297) - Smart formatting
- `_verify_function_names` (line 2384) - Context-aware verification
- `_detect_placeholder_code` (line 2380) - Enhanced detection
- `_do_one_turn` (line 5110) - Error handling, deduplication
- `_calculate_confidence_score` (line 7174) - Error-aware confidence

2. New helper methods to add:

- `_validate_command` - Pre-execution validation
- `_resolve_file_path` - Path resolution with fuzzy matching
- `_categorize_error` - Error classification
- `_aggregate_errors` - Error collection and reporting
- `_score_result_relevance` - Relevance scoring
- `_deduplicate_results` - Result deduplication
- `_summarize_results` - Result summarization
- `_validate_code_snippets` - Code snippet validation
- `_validate_execution_path` - Execution path validation

## Testing Strategy

1. **Command Parsing Tests:**

- Multi-line commands
- Malformed commands
- Command deduplication
- Path resolution

2. **Error Handling Tests:**

- Transient vs permanent errors
- Retry logic
- Error aggregation
- Confidence score updates

3. **Result Formatting Tests:**

- Smart truncation
- Relevance scoring
- Deduplication
- Summarization

4. **Validation Tests:**

- Context-aware function verification
- Code snippet validation
- Execution path validation
- Incremental validation

## Expected Outcomes

- More reliable command parsing (handles edge cases)
- Better error recovery (retries transient failures)
- Smarter result presentation (prioritized, deduplicated)
- Stronger validation (catches issues early)
- Improved user experience (specific errors, actionable suggestions)

### To-dos

- [ ] Make _get_framework_context() non-blocking with 2s timeout, reset agent_start_time before any blocking ops
- [ ] Remove duplicate agent_start_time resets at lines 4694 and 6226, keep only reset at line 4426
- [ ] Add aggressive timeout checks during initialization (fail fast if >10s), add checks after framework detection and system prompt building
- [ ] Remove immediate per-turn timeout check (lines 4817-4824), add checks after command execution and before LLM call
- [ ] Remove unnecessary time.sleep(0.1) at line 5187, keep necessary sleeps but add timeout awareness
- [ ] Create _execute_with_timeout helper and wrap all critical operations (_optimize_conversation_context, _check_verification_requirements, _calculate_confidence_score, _generate_smart_suggestions, _format_findings, _parse_agent_commands)
- [ ] Remove +2s buffer from ThreadPoolExecutor timeout at line 5004, use exact timeout value
- [ ] Limit results before processing (line 6120), implement single-pass processing, add early termination
- [ ] Add early termination to GREP operations, ensure matches are limited immediately after grep_pattern
- [ ] Add early termination to search_concept in code_explorer.py, stop when max_results reached
- [ ] Add limits to key_insights (50), results during collection (500), implement LRU cache for file_cache, limit conversation_context growth
- [ ] Fix set-to-list conversion bug at line 5439, ensure result is a set
- [ ] Add explicit thread cleanup in finally block, wait for heartbeat thread with timeout
- [ ] Add cancellation_flag, cancel ThreadPoolExecutor futures on timeout, check flag in operation loops
- [ ] Replace all 39 bare except: clauses with except Exception as e:, add proper logging, re-raise critical exceptions
- [ ] Create _handle_error helper method, standardize error handling patterns throughout
- [ ] Review and remove truly duplicate timeout checks, keep unique-purpose checks
- [ ] Fix race condition at line 4948 by recalculating elapsed_time right before use
- [ ] Fix task_id variable scope issue at line 5604, ensure it is defined before use
- [ ] Add size checks after results.extend(), limit during collection not just at formatting
- [ ] Extract system prompt to class constant, build once and cache, only rebuild if needed
- [ ] Add cancellation checks in all loops, return early on timeout, cancel futures immediately
- [ ] Verify message optimization is working, add message size check before LLM call, truncate if too large
- [ ] Add progress callbacks to blocking operations, emit progress during file reads and framework detection
- [ ] Add all hardcoded limits to ExplorerConfig, use config values throughout codebase
- [ ] Define timeout constants at top of _agent_mode_conversation, use consistently throughout, document strategy
- [ ] Implement multi-line command parsing in _parse_agent_commands to handle commands spanning multiple lines
- [ ] Add _validate_command method for pre-execution validation (file existence, regex syntax, etc.)
- [ ] Add command deduplication in _do_one_turn to remove duplicate commands before execution
- [ ] Add _resolve_file_path method with fuzzy matching for typos and path variations
- [ ] Add command alias support (FIND→SEARCH, OPEN→READ) in _parse_agent_commands
- [ ] Add _categorize_error method to classify errors as permanent vs transient
- [ ] Implement retry logic with exponential backoff for transient errors in command execution
- [ ] Replace generic error messages with specific, actionable ones including suggestions
- [ ] Add _aggregate_errors method to collect and group errors from parallel operations
- [ ] Update _calculate_confidence_score to account for errors (decrease on permanent, maintain on transient)
- [ ] Enhance _format_findings with smart truncation (keep function definitions, preserve structure)
- [ ] Add _score_result_relevance method to prioritize results by match quality and context
- [ ] Add _deduplicate_results method to merge similar results and remove duplicates
- [ ] Add _summarize_results method to create summaries for large result sets (>20 items)
- [ ] Enhance _verify_function_names to check function context (signature, accessibility, imports)
- [ ] Add _validate_code_snippets method to verify code snippets match actual file content
- [ ] Implement incremental validation during generation (catch issues early, provide feedback)
- [ ] Add _validate_execution_path method to verify execution paths (A→B→C) are valid
- [ ] Enhance _detect_placeholder_code to detect TODO/FIXME, incomplete bodies, stub implementations