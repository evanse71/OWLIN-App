---
name: Fix Agent Timeout Detection at Start of Turn
overview: ""
todos:
  - id: c1040c25-1ef1-4b8f-b761-9637593911cb
    content: Replace multiple result iterations with single-pass processing (lines 5714-5743)
    status: pending
  - id: 2338b038-b447-4f19-9340-79afa7790da9
    content: Add result limiting before _format_findings call (line 5728)
    status: pending
  - id: 4b080eaa-071f-459e-bcbe-f3be8dc58848
    content: Add limit check and optimize _format_findings method (lines 3154-3213)
    status: pending
  - id: 84f65fb3-cbb3-49f9-862a-600db2f13408
    content: Parallelize GREP file reading using ThreadPoolExecutor (lines 5575-5627)
    status: pending
  - id: 25b967e3-b981-4ffa-9616-7e97008c5671
    content: Separate and parallelize GREP commands execution (lines 5256-5260, 5512-5513)
    status: pending
  - id: 66029d33-883d-4baa-964a-63df92fe407f
    content: Use 30s timeout for first turn, 60s for subsequent turns (line 4812)
    status: pending
  - id: 9666be1b-cbf9-4067-b685-f0bef9a73aee
    content: Limit GREP matches to top 20 files immediately after grep_pattern (line 5568)
    status: pending
  - id: 7cb087b6-6868-4a65-bb3a-295afbc1502e
    content: Improve early termination in GREP processing loops (lines 5578-5627)
    status: pending
  - id: a38516ba-4318-4299-a946-6c7558703d3e
    content: Remove or reduce blocking time.sleep(1.0) (line 4964)
    status: pending
  - id: 85861edd-b119-4008-ab0d-09560c63e9b2
    content: Move timeout check to absolute first line of _do_one_turn function (before logging, before any operations)
    status: pending
  - id: bf80a278-05da-4f95-9f19-eb9d297122d2
    content: Remove duplicate timeout check at lines 4686-4738 since it is now at start of function
    status: pending
  - id: 86691519-261c-4a26-a4a0-bc8387e19f6f
    content: Verify heartbeat loop timeout check is working correctly (no changes needed, just verify)
    status: pending
  - id: 5ee2fee8-a55a-4b15-9d5a-f32cb2eea65a
    content: Add diagnostic context to timeout messages to indicate where timeout was detected
    status: pending
---

# Fix Agent Timeout Detection at Start of Turn

## Problem Analysis

The agent is timing out with "0 turns" after 5 minutes, indicating the timeout check at line 4688 happens too late. If something blocks before that check, the timeout won't be detected. The timeout check needs to be the FIRST operation in `_do_one_turn` to ensure it runs immediately.

## Solution Overview

1. Move timeout check to the absolute first line of `_do_one_turn` (before logging, before any variable access)
2. Ensure heartbeat loop timeout check is working correctly
3. Add better error context to distinguish between different timeout scenarios

## Implementation Details

### 1. Move Timeout Check to First Line of _do_one_turn

**File:** `backend/services/chat_service.py`

**Location:** Lines 4666-4674 (start of `_do_one_turn` function)

**Current Issue:**

- Timeout check happens at line 4688, after logging and variable assignments
- If anything blocks before line 4688, timeout won't be detected
- The check needs to be the very first operation

**Changes:**

- Move the timeout check to the absolute first line of the function
- Check `elapsed_time` before any other operations
- Return immediately if timeout exceeded
- Keep the existing timeout handling logic but execute it first

**Implementation:**

```python
def _do_one_turn(turn_num):
    """
    Execute one turn of the agent loop.
    Returns: {"exit": bool, "skip": bool, "result": str|None}
    - exit=True: exit the main loop (equivalent to break)
    - skip=True: skip incrementing turn counter (equivalent to continue)
    - result: if exit=True, this contains the final result string (for timeouts/errors)
    """
    # CRITICAL: Check timeout FIRST, before any other operations (including logging)
    elapsed_time = time.time() - agent_start_time
    if elapsed_time > agent_timeout:
        logger.warning(f"Agent mode overall timeout reached at start of turn {turn_num + 1} ({elapsed_time:.1f}s, {elapsed_time/60:.1f} minutes)")
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
            except:
                pass
        return {"exit": True, "skip": False, "result": f"Agent mode timed out after {elapsed_time/60:.1f} minutes ({turn_num} turns). Please try a more specific question or break it into smaller parts."}
    
    # Now safe to log and access variables
    logger.info(f"Starting turn {turn_num + 1} (elapsed: {elapsed_time:.1f}s)")
    nonlocal agent_timeout, per_turn_timeout, user_message, commands_history, tools_used, discovered_files
    # ... rest of function continues
```

**Note:** Remove the duplicate timeout check at line 4688 since it's now at the start.

### 2. Remove Duplicate Timeout Check

**File:** `backend/services/chat_service.py`

**Location:** Lines 4686-4738 (duplicate timeout check after variable assignments)

**Changes:**

- Remove the timeout check at lines 4686-4738 since it's now at the start of the function
- Keep the per-turn timeout check (line 4739) as it serves a different purpose

**Implementation:**

- Delete lines 4686-4738 (the timeout check block)
- Keep the per-turn timeout check that follows

### 3. Verify Heartbeat Loop Timeout Check

**File:** `backend/services/chat_service.py`

**Location:** Lines 4611-4624 (heartbeat loop timeout check)

**Current State:**

- Heartbeat loop already has timeout check at the start
- This is correct and should remain

**Verification:**

- Ensure the timeout check in heartbeat loop is working correctly
- The check should be at the very start of the loop iteration (already implemented)
- No changes needed here, just verify it's correct

### 4. Add Diagnostic Information to Timeout Messages

**File:** `backend/services/chat_service.py`

**Location:** Multiple timeout return statements

**Changes:**

- Add context about where the timeout was detected
- Help distinguish between timeout at start of turn vs during execution

**Implementation:**

- Update timeout message at start of `_do_one_turn` to indicate "timeout detected at start of turn"
- Keep existing messages for other timeout scenarios

## Testing Strategy

1. Test with normal operation - should work as before
2. Test with timeout scenario - should detect timeout immediately at start of turn
3. Verify logs show "timeout reached at start of turn" when appropriate
4. Verify heartbeat loop still catches timeouts if main loop is blocked

## Expected Outcomes

- Timeout detected immediately when `_do_one_turn` is called if timeout already exceeded
- No more 5-minute waits before timeout detection
- Better diagnostic information about where timeout occurred
- Agent fails fast instead of hanging