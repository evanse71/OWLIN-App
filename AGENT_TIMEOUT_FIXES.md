# Agent Mode Timeout Fixes

## Problem
Agent mode was timing out after 3.7 minutes (6 turns) with error: "insufficient time remaining for LLM call"

## Root Causes Identified

1. **Per-turn timeout mismatch**: Per-turn timeout was 60s, so 6 turns * 60s = 360s, but overall timeout is only 300s (5 min)
2. **LLM call timeout too long**: LLM calls were using 60s timeout, leaving insufficient time for final call
3. **No timeout checks between operations**: Operations could take a long time without checking if we're running out of time
4. **Too many retries**: 3 retries with exponential backoff was consuming too much time on failures
5. **Minimum timeout too high**: Required 30s minimum for LLM calls, which was too restrictive

## Fixes Applied

### 1. Reduced Per-Turn Timeout
- **Before**: 60s per turn (subsequent turns)
- **After**: 45s per turn (subsequent turns)
- **Impact**: Allows 6+ turns within 5-minute overall timeout (6 * 45s = 270s < 300s)

### 2. Reduced LLM Call Timeout
- **Before**: 60s timeout for subsequent turns
- **After**: 40s timeout for subsequent turns
- **Impact**: Faster failure detection, more time available for other operations

### 3. Reduced Minimum Timeout
- **Before**: 30s minimum for subsequent turns
- **After**: 25s minimum for subsequent turns
- **Impact**: Allows LLM calls with less remaining time

### 4. Reduced Retries
- **Before**: 3 retries on failure
- **After**: 2 retries on failure
- **Impact**: Saves time on failures, faster error recovery

### 5. Added Timeout Checks After Major Operations
- Added timeout checks after file reads
- Added timeout checks after searches
- Added timeout checks after GREP operations
- **Impact**: Fails fast when approaching timeout, prevents wasting time on operations that won't complete

### 6. Reduced File Read Timeout Adjustments
- **Before**: +20s for >10 files, +10s for >5 files
- **After**: +15s for >10 files, +8s for >5 files
- **Impact**: Prevents per-turn timeout from growing too large

## Expected Results

- **More turns possible**: 6-7 turns can now complete within 5-minute timeout
- **Faster failure detection**: Operations fail faster when approaching timeout
- **Better time management**: Timeout checks prevent wasting time on operations that won't complete
- **More reliable**: Reduced retries and timeouts make the system more predictable

## Testing Recommendations

1. Test with 6+ turns to verify timeout is no longer hit prematurely
2. Monitor logs for "Timeout approaching" warnings to identify slow operations
3. Verify LLM calls complete successfully with reduced timeout
4. Check that operations fail fast when approaching timeout

