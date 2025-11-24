<!-- 17eb7958-8f0e-4a8a-866e-61c6682dc099 8c45fc69-8b8b-4030-861d-e802b00686e7 -->
# Fix Critical Integration Bugs

## Problem Summary

The verification system has 5 critical bugs preventing it from working:

1. `code_match_accuracy` calculation is broken (line 4365) - looks for `code_verifications` that doesn't exist
2. Code snippet verification results aren't collected/stored for confidence calculation
3. ResponseRewriter expects `code_verifications` but it's never populated
4. RuntimeVerifier has hardcoded paths that will fail
5. Multi-pass validation doesn't verify that rewrites actually fixed issues

## Fix 1: Collect Code Verification Results

**File**: `backend/services/chat_service.py`

**Location**: After `_filter_unverified_claims` call (around line 4296)

**Change**: Collect code snippet verification results from `_filter_unverified_claims` and store them for confidence calculation.

````python
# After line 4296, add:
code_verification_results = []
# Extract code snippets from response and verify them
code_snippet_pattern = r'```(?:python|typescript|javascript)?\n(.*?)```'
code_snippets = re.findall(code_snippet_pattern, final_response, re.DOTALL)

for snippet in code_snippets[:5]:  # Limit to 5
    # Find file:line reference near snippet
    snippet_start = final_response.find(snippet)
    context = final_response[max(0, snippet_start-200):snippet_start+len(snippet)+200]
    file_match = re.search(r'(\w+[/\\][\w/\\]+\.(?:py|ts|tsx|js|jsx)):(\d+)', context)
    if file_match:
        file_path = file_match.group(1).replace('\\', '/')
        line_num = int(file_match.group(2))
        line_range = (max(1, line_num - 2), line_num + 5)
        verification = self.code_verifier.verify_code_snippet(snippet.strip(), file_path, line_range)
        code_verification_results.append(verification)
````

**Location**: Update `_execute_diagnostic_queries` return (around line 4845)

**Change**: Add `code_verifications` to the returned dict:

```python
return {
    "sql_queries": results["sql_queries"],
    "api_calls": results["api_calls"],
    "log_searches": results["log_searches"],
    "code_verifications": code_verification_results  # ADD THIS
}
```

## Fix 2: Fix code_match_accuracy Calculation

**File**: `backend/services/chat_service.py`

**Location**: Lines 4360-4369

**Change**: Use actual code verification results instead of non-existent `diagnostic_results["code_verifications"]`:

```python
# Replace lines 4360-4369 with:
# Calculate code match accuracy from actual verification
code_match_accuracy = None
if diagnostic_results and "code_verifications" in diagnostic_results:
    similarities = []
    for verification in diagnostic_results["code_verifications"]:
        if verification.get("similarity") is not None:
            similarities.append(verification["similarity"])
    if similarities:
        code_match_accuracy = sum(similarities) / len(similarities)
```

## Fix 3: Fix ResponseRewriter Data Flow

**File**: `backend/services/chat_service.py`

**Location**: Line 4270 (in multi-pass validation)

**Change**: Pass actual code verification results to ResponseRewriter:

```python
# Replace line 4269-4274 with:
verification_data = getattr(self, '_last_verification_results', {})
# Add code verifications if available
if diagnostic_results and "code_verifications" in diagnostic_results:
    if "code_verifications" not in verification_data:
        verification_data["code_verifications"] = {}
    # Build dict mapping code snippets to verification results
    for i, verification in enumerate(diagnostic_results["code_verifications"]):
        if verification.get("actual_code"):
            verification_data["code_verifications"][verification.get("actual_code", "")] = verification

final_response = self.response_rewriter.rewrite_response(
    final_response,
    verification_results=verification_data,
    files_read=files_read_tracker
)
```

## Fix 4: Fix RuntimeVerifier Hardcoded Paths

**File**: `backend/services/runtime_verifier.py`

**Location**: `__init__` method (lines 23-34)

**Change**: Make paths configurable with environment variables or config, with fallbacks:

```python
def __init__(self, db_path: Optional[str] = None, log_dir: Optional[str] = None):
    """
    Initialize the runtime verifier.
    
    Args:
        db_path: Path to SQLite database (default: from env or "data/owlin.db")
        log_dir: Directory containing log files (default: from env or "data/logs")
    """
    import os
    from backend.services.explorer_config import get_config
    
    config = get_config()
    
    self.db_path = Path(db_path or os.getenv("OWLIN_DB_PATH", "data/owlin.db"))
    self.log_dir = Path(log_dir or os.getenv("OWLIN_LOG_DIR", "data/logs"))
    self.api_base_url = os.getenv("OWLIN_API_URL", "http://localhost:8000")
    
    # Create directories if they don't exist
    self.db_path.parent.mkdir(parents=True, exist_ok=True)
    self.log_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"RuntimeVerifier initialized with db_path: {self.db_path}, log_dir: {self.log_dir}")
```

**Location**: `query_database` method (around line 120)

**Change**: Add error handling for missing database:

```python
if not db_file.exists():
    return {
        "success": False,
        "error": f"Database file not found: {db_file}. Check OWLIN_DB_PATH environment variable.",
        "query": query
    }
```

## Fix 5: Verify Multi-Pass Validation Actually Works

**File**: `backend/services/chat_service.py`

**Location**: Multi-pass validation loop (lines 4247-4288)

**Change**: After rewriting, actually verify the rewrite fixed the issues before continuing:

```python
if needs_rewrite:
    logger.info(f"Response needs rewriting (pass {validation_pass + 1}/{max_validation_passes}): {rewrite_reasons}")
    
    # Rewrite response
    verification_data = getattr(self, '_last_verification_results', {})
    # ... (add code verification data as in Fix 3)
    
    final_response = self.response_rewriter.rewrite_response(
        final_response,
        verification_results=verification_data,
        files_read=files_read_tracker
    )
    
    # VERIFY THE REWRITE ACTUALLY FIXED ISSUES
    structure_validation_after = self.response_validator.validate_response(final_response)
    unverified_after = self._filter_unverified_claims(final_response, files_read_tracker, commands_history)
    
    # Check if issues were actually fixed
    if structure_validation_after.is_valid and "⚠️" not in unverified_after:
        logger.info(f"Rewrite successful - issues resolved")
        break  # Exit loop, rewrite worked
    else:
        logger.warning(f"Rewrite did not fully resolve issues, will retry")
        # Continue to next pass
    
    # Add rewrite instruction to conversation
    rewrite_prompt = f"The previous response had issues: {', '.join(rewrite_reasons[:3])}. Please regenerate the response with these fixes applied."
    # ... (rest of existing code)
```

## Testing Checklist

After fixes:

- [ ] Code match accuracy is calculated from actual verification results
- [ ] ResponseRewriter receives code verification data
- [ ] RuntimeVerifier works with custom paths
- [ ] Multi-pass validation verifies fixes before accepting
- [ ] All verification results flow correctly through the system

### To-dos

- [ ] Create CodeVerifier service with actual code verification methods (verify_function_exists, verify_code_snippet, verify_framework, verify_logging_exists, compare_code_examples)
- [ ] Integrate CodeVerifier into _check_verification_requirements() to actually verify claims before allowing ANALYZE
- [ ] Update _filter_unverified_claims() to use CodeVerifier for actual code comparison instead of pattern matching
- [ ] Create ResponseValidator service to validate response structure and format before generation
- [ ] Add pre-generation blocking in chat_service.py to enforce validation checklist before LLM generates response
- [ ] Implement response structure enforcement to validate sections and format, reject invalid responses
- [ ] Create RuntimeVerifier service with methods to check logs, query database, and test API endpoints
- [ ] Integrate RuntimeVerifier into workflow to actually execute diagnostic queries and verify runtime behavior
- [ ] Create ArchitectureAnalyzer service to auto-detect framework, async patterns, and data flow
- [ ] Integrate ArchitectureAnalyzer to validate LLM architecture claims and provide architecture context
- [ ] Create ResponseRewriter service to automatically fix function names, file paths, and code examples
- [ ] Implement confidence-based blocking using verification results, code match accuracy, and runtime checks
- [ ] Add multi-pass validation loop that rewrites and re-validates responses until they pass or max attempts reached