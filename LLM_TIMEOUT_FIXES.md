# LLM Timeout Fixes - Round 2

## Problem
Agent mode was failing on turn 5 with: "Request timed out after 25s (thread timeout)"

## Root Causes

1. **Minimum timeout too short**: 25s was insufficient for complex LLM queries
2. **LLM response too long**: `num_predict: 2000` tokens was generating long responses that took too long
3. **Context too large for later turns**: Large context (32k) was slowing down LLM processing on later turns
4. **Context optimization consuming time**: Expensive context optimization was running even when time was low
5. **LLM timeout too conservative**: 40s timeout was too short for complex queries

## Fixes Applied

### 1. Increased Minimum Timeout
- **Before**: 25s minimum for subsequent turns
- **After**: 35s minimum for subsequent turns
- **Impact**: Gives LLM more time to process complex queries

### 2. Reduced Token Output Limit
- **Before**: `num_predict: 2000` tokens
- **After**: `num_predict: 1000` tokens
- **Impact**: Faster response generation, shorter responses

### 3. Reduced Context Size for Later Turns
- **Before**: Full context (up to 32k) for all turns
- **After**: Context capped at 16k for turns 3+
- **Impact**: Faster LLM processing on later turns when time is critical

### 4. Skip Context Optimization When Low on Time
- **Before**: Always optimized context (could take 5s+)
- **After**: Skips optimization when 85% of timeout is used
- **Impact**: Saves time for LLM call when running low on time

### 5. Increased LLM Timeout
- **Before**: 40s timeout for subsequent turns
- **After**: 50s timeout for subsequent turns
- **Impact**: More time for LLM to process complex queries

### 6. Added Detailed Timing Logs
- Added logging before building messages
- Added logging after context optimization
- Added logging for context size reduction
- **Impact**: Better visibility into where time is being spent

## Expected Results

- **More reliable LLM calls**: 35s minimum + 50s max gives LLM enough time
- **Faster responses**: 1000 tokens instead of 2000 reduces generation time
- **Better time management**: Context optimization skipped when time is low
- **Faster later turns**: Reduced context size speeds up processing
- **Better diagnostics**: Detailed logs help identify bottlenecks

## Testing Recommendations

1. Test with 5+ turns to verify LLM calls complete successfully
2. Monitor logs for "Skipping context optimization" warnings
3. Check for "Reducing context size" messages on turns 3+
4. Verify LLM calls complete within timeout (should see successful completions)
5. Check timing logs to identify any remaining bottlenecks

