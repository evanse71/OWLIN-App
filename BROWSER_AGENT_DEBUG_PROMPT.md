# Browser Cursor Agent Debug Prompt

## Context
The OCR service is throwing a `UnboundLocalError: cannot access local variable 'Path' where it is not associated with a value` error when processing documents. This happens in exception handlers within `backend/services/ocr_service.py`.

## GitHub Repository
**Repository URL**: https://github.com/evanse71/OWLIN-App.git
**Branch**: main
**Latest Commit**: be0e648c (Fix Path scoping in exception handler - use local import with alias)

## Problem Description
Multiple documents are failing with the error:
```
OCR pipeline execution failed: cannot access local variable 'Path' where it is not associated with a value
```

This error occurs in the `_process_with_v2_pipeline` function's exception handler at line 566, where `Path` is used to create a log path.

## Files to Inspect
1. **`backend/services/ocr_service.py`** - Main file with the issue
   - Line 7: Module-level import: `from pathlib import Path`
   - Line 518: Comment indicating Path is imported at module level
   - Line 566: Exception handler using `Path(__file__).parent.parent.parent / ".cursor" / "debug.log"`

## Investigation Tasks

### Task 1: Verify Import Structure
1. Check if `Path` is properly imported at the module level (line 7)
2. Verify there are no conflicting local imports or assignments to `Path` in the function
3. Check if there are any `from pathlib import Path` statements inside functions that might shadow the module-level import

### Task 2: Analyze Exception Handler Scope
1. Examine the `_process_with_v2_pipeline` function (starting around line 506)
2. Check the exception handler at line 559-577
3. Determine why Python thinks `Path` is a local variable when it's used in the exception handler
4. Look for any code paths that might assign to `Path` before the exception handler runs

### Task 3: Check for Variable Shadowing
1. Search for any assignments like `Path = ...` anywhere in the function
2. Check if there are any `import Path` or `from ... import Path` statements that might conflict
3. Look for any nested functions or closures that might affect variable scoping

### Task 4: Review Recent Fixes
1. Check the latest commit (6e961440) to see what changes were made
2. Verify if the fix properly addresses the scoping issue
3. Check if there are other exception handlers in the file that might have the same problem

### Task 5: Identify Root Cause
Based on the error message "cannot access local variable 'Path' where it is not associated with a value", Python is treating `Path` as a local variable. This typically happens when:
- There's an assignment to `Path` somewhere in the function (even if it's never reached)
- There's a local import that shadows the module-level import
- There's a scoping issue with nested try-except blocks

## Expected Output
Provide:
1. **Root Cause**: Exact explanation of why Python thinks `Path` is local
2. **Code Location**: Specific line numbers where the issue occurs
3. **Fix**: Recommended code change to resolve the issue
4. **Verification**: How to verify the fix works

## Additional Context
- The backend is running with `--reload` flag, so changes should auto-reload
- Multiple documents are failing with this error
- The error occurs in exception handlers, suggesting it happens when an exception is raised during OCR processing
- The file uses `Path` extensively throughout (21 occurrences according to grep)

## Search Strategy
1. Read `backend/services/ocr_service.py` completely
2. Focus on the `_process_with_v2_pipeline` function
3. Check all exception handlers in the file
4. Look for any `Path` variable assignments or local imports
5. Verify the module-level import is correct

