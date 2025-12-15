---
name: Code Assistant Critical Improvements (P0)
overview: ""
todos:
  - id: 70594bef-3251-48bc-a991-eeea0e32f0f9
    content: Make _get_framework_context() non-blocking with 2s timeout, reset agent_start_time before any blocking ops
    status: pending
  - id: ad3b42a1-b785-4c30-86ad-a7c8dc39dc45
    content: Remove duplicate agent_start_time resets at lines 4694 and 6226, keep only reset at line 4426
    status: pending
  - id: 7c37fcd3-a05c-460f-a258-d69258c0ad8e
    content: Add aggressive timeout checks during initialization (fail fast if >10s), add checks after framework detection and system prompt building
    status: pending
  - id: 860ba2b4-f9cc-41bb-b334-70743e098bed
    content: Remove immediate per-turn timeout check (lines 4817-4824), add checks after command execution and before LLM call
    status: pending
  - id: b791190a-e0b4-4bf7-9045-18db6ec9612a
    content: Remove unnecessary time.sleep(0.1) at line 5187, keep necessary sleeps but add timeout awareness
    status: pending
  - id: b75e1881-5217-4cd6-b1ef-29c901245f4f
    content: Create _execute_with_timeout helper and wrap all critical operations (_optimize_conversation_context, _check_verification_requirements, _calculate_confidence_score, _generate_smart_suggestions, _format_findings, _parse_agent_commands)
    status: pending
  - id: 86ebf322-d7c7-4c81-b750-5a57cc9472fe
    content: Remove +2s buffer from ThreadPoolExecutor timeout at line 5004, use exact timeout value
    status: pending
  - id: a0e1908b-d007-4857-820f-0ffcd54cc8d2
    content: Limit results before processing (line 6120), implement single-pass processing, add early termination
    status: pending
  - id: 78b87624-1a24-4b0f-8e0a-c5b33796ed1c
    content: Add early termination to GREP operations, ensure matches are limited immediately after grep_pattern
    status: pending
  - id: adf8bc94-2a8e-4e13-975f-817b124f205a
    content: Add early termination to search_concept in code_explorer.py, stop when max_results reached
    status: pending
  - id: 60a46699-5ee3-4781-8831-01f855fcbcf2
    content: Add limits to key_insights (50), results during collection (500), implement LRU cache for file_cache, limit conversation_context growth
    status: pending
  - id: d95213e3-f13a-402b-b544-3305eb25e3e5
    content: Fix set-to-list conversion bug at line 5439, ensure result is a set
    status: pending
  - id: f86d5acf-70f8-446e-af08-82aeb53b9b54
    content: Add explicit thread cleanup in finally block, wait for heartbeat thread with timeout
    status: pending
  - id: 0223fb63-aeca-4223-9d6c-dc332cd32e28
    content: Add cancellation_flag, cancel ThreadPoolExecutor futures on timeout, check flag in operation loops
    status: pending
  - id: 0035fcfd-ba4a-4b1a-b976-036e3ce457c3
    content: "Replace all 39 bare except: clauses with except Exception as e:, add proper logging, re-raise critical exceptions"
    status: pending
  - id: 4f32ccdf-deb7-45ad-b0c5-281e7af90cef
    content: Create _handle_error helper method, standardize error handling patterns throughout
    status: pending
  - id: adcec970-3e08-4c53-a074-e91677fe2a2f
    content: Review and remove truly duplicate timeout checks, keep unique-purpose checks
    status: pending
  - id: 5680e966-0f86-4aef-b9b3-417752ac2eaf
    content: Fix race condition at line 4948 by recalculating elapsed_time right before use
    status: pending
  - id: 7b44d643-f384-4b31-a87d-b25ab9f67e4f
    content: Fix task_id variable scope issue at line 5604, ensure it is defined before use
    status: pending
  - id: be09bb16-7874-4def-8497-b2a834aeac0a
    content: Add size checks after results.extend(), limit during collection not just at formatting
    status: pending
  - id: e47d9203-f2d7-46f2-9e2c-c324e260378e
    content: Extract system prompt to class constant, build once and cache, only rebuild if needed
    status: pending
  - id: 19bb0cc1-e977-4f6e-bfaf-ebe220334aff
    content: Add cancellation checks in all loops, return early on timeout, cancel futures immediately
    status: pending
  - id: 4aa1e292-6826-4a5e-8ab4-3da07096f2f6
    content: Verify message optimization is working, add message size check before LLM call, truncate if too large
    status: pending
  - id: f90dfa23-b56e-4ba2-b396-c1f03f3cf223
    content: Add progress callbacks to blocking operations, emit progress during file reads and framework detection
    status: pending
  - id: 6ab26f38-72f5-445f-88f6-02ea93a4ffad
    content: Add all hardcoded limits to ExplorerConfig, use config values throughout codebase
    status: pending
  - id: 2f46deb4-4291-496c-b989-75d886029241
    content: Define timeout constants at top of _agent_mode_conversation, use consistently throughout, document strategy
    status: pending
  - id: 47247fb4-8d10-475c-9949-d3befec59f25
    content: Implement multi-line command parsing in _parse_agent_commands to handle commands spanning multiple lines
    status: pending
  - id: dd6b3fff-1f5c-4ac9-aaad-c595651ad755
    content: Add _validate_command method for pre-execution validation (file existence, regex syntax, etc.)
    status: pending
  - id: deab5feb-5b71-4527-b4c1-dad8293f3f00
    content: Add command deduplication in _do_one_turn to remove duplicate commands before execution
    status: pending
  - id: c97c5f26-1019-42fe-a0a6-6c2c46e333a5
    content: Add _resolve_file_path method with fuzzy matching for typos and path variations
    status: pending
  - id: 66c9d83f-34f0-4509-a1a1-a801214d2e3e
    content: Add command alias support (FIND→SEARCH, OPEN→READ) in _parse_agent_commands
    status: pending
  - id: 9bd4ffbc-c293-4d8f-ac03-2aaa8914c8b4
    content: Add _categorize_error method to classify errors as permanent vs transient
    status: pending
  - id: 5281f41f-ce06-4774-9346-80d2b191d6ce
    content: Implement retry logic with exponential backoff for transient errors in command execution
    status: pending
  - id: 254c04ea-5a2d-46de-bb45-463a9107be0f
    content: Replace generic error messages with specific, actionable ones including suggestions
    status: pending
  - id: 32e0c3be-e645-4102-a5d1-c8645c470dc3
    content: Add _aggregate_errors method to collect and group errors from parallel operations
    status: pending
  - id: 05eabbd1-17dc-475d-b78f-443391eefec3
    content: Update _calculate_confidence_score to account for errors (decrease on permanent, maintain on transient)
    status: pending
  - id: d9e36f33-2def-4d8d-a64f-c36cc5aebf51
    content: Enhance _format_findings with smart truncation (keep function definitions, preserve structure)
    status: pending
  - id: 58b0db42-396b-4303-8ace-c9c57e1642fd
    content: Add _score_result_relevance method to prioritize results by match quality and context
    status: pending
  - id: d9913d44-6be4-45ad-9e5c-67120d1ea94b
    content: Add _deduplicate_results method to merge similar results and remove duplicates
    status: pending
  - id: fd89af52-7d31-439a-bf29-1b9ce4f49241
    content: Add _summarize_results method to create summaries for large result sets (>20 items)
    status: pending
  - id: c0a31dc8-9d12-4a2a-b03b-4590497bec2a
    content: Enhance _verify_function_names to check function context (signature, accessibility, imports)
    status: pending
  - id: 2fa37f52-819d-40ca-a225-e38a3ab56214
    content: Add _validate_code_snippets method to verify code snippets match actual file content
    status: pending
  - id: b66b495d-82e5-4fb4-94ce-54f512158c7f
    content: Implement incremental validation during generation (catch issues early, provide feedback)
    status: pending
  - id: 8992e57b-3103-4bdb-8613-33d1073c98e5
    content: Add _validate_execution_path method to verify execution paths (A→B→C) are valid
    status: pending
  - id: 96add59f-9086-4a67-9258-fde644a6e9df
    content: Enhance _detect_placeholder_code to detect TODO/FIXME, incomplete bodies, stub implementations
    status: pending
---

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