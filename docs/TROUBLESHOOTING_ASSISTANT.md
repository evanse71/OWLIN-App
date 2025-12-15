# Troubleshooting Guide

## Overview

This guide helps you diagnose and resolve common issues with the Code Assistant, including timeout errors, low confidence scores, command parsing failures, and performance problems.

## Common Issues

### Timeout Errors

**Symptoms:**
- "Agent mode timed out after X minutes"
- Requests taking too long
- No response received

**Causes:**
1. Context size too large
2. Too many files to explore
3. Network/IO delays
4. Timeout settings too low

**Solutions:**

1. **Reduce Context Size:**
```python
# Instead of 128k, use 64k or 32k
response = requests.post("/api/chat", json={
    "message": "Your query",
    "context_size": 32000  # Reduced from 128000
})
```

2. **Increase Timeout:**
```bash
export EXPLORER_TIMEOUT=90  # Increase from default 45
```

3. **Use Search Mode First:**
```python
# Step 1: Narrow down with Search mode
search_result = chat("Find relevant files", use_search_mode=True)

# Step 2: Use Agent mode on specific files
agent_result = chat(
    f"Analyze: {search_result['findings']}",
    use_agent_mode=True
)
```

4. **Check Network/IO:**
- Verify file system performance
- Check network latency
- Monitor disk I/O

### Low Confidence Scores

**Symptoms:**
- Confidence < 0.5
- Warnings about low confidence
- Incomplete results

**Causes:**
1. Insufficient exploration
2. Too many errors
3. Missing file references
4. Validation issues

**Solutions:**

1. **Increase Exploration:**
```python
# Use Agent mode for more exploration
response = chat("Your query", use_agent_mode=True, context_size=64000)
```

2. **Check Error Count:**
```python
# Review error messages in response
if result.get('errors'):
    for error in result['errors']:
        print(f"Error: {error['message']}")
        print(f"Category: {error['category']}")
        print(f"Suggestion: {error['suggestion']}")
```

3. **Verify File References:**
- Ensure files exist
- Check file paths are correct
- Use fuzzy path resolution

4. **Fix Validation Issues:**
- Review validation warnings
- Correct function names
- Fix code snippet mismatches

### Command Parsing Failures

**Symptoms:**
- Commands not executed
- "Unknown command" errors
- Malformed command warnings

**Causes:**
1. Invalid command syntax
2. Missing required parameters
3. Multi-line command issues
4. Alias not recognized

**Solutions:**

1. **Check Command Syntax:**
```python
# Valid commands:
"READ backend/main.py"
"SEARCH upload endpoint"
"GREP def.*function"
"TRACE upload → database"

# Invalid commands:
"READ"  # Missing file
"SEARCH"  # Missing term
"GREP [unclosed"  # Invalid regex
```

2. **Use Proper Aliases:**
```python
# Supported aliases:
"FIND" → "SEARCH"
"OPEN" → "READ"
"VIEW" → "READ"
"SHOW" → "READ"
```

3. **Fix Multi-line Commands:**
```python
# Use continuation markers:
"READ backend/services/\\
chat_service.py"

# Or proper line breaks:
"READ backend/services/
chat_service.py"
```

4. **Validate Commands:**
```python
# Check command validation:
is_valid, error_msg, suggestion = chat_service._validate_command(cmd)
if not is_valid:
    print(f"Error: {error_msg}")
    print(f"Suggestion: {suggestion}")
```

### Error Handling Issues

**Symptoms:**
- Retry failures
- Circuit breaker opened
- Permanent errors not handled

**Causes:**
1. Too many retries
2. Circuit breaker threshold too low
3. Error categorization incorrect
4. Network issues

**Solutions:**

1. **Check Retry Configuration:**
```bash
export EXPLORER_MAX_RETRIES=3  # Default
export EXPLORER_RETRY_INITIAL_DELAY=1.0
export EXPLORER_RETRY_MAX_DELAY=10.0
```

2. **Adjust Circuit Breaker:**
```bash
export EXPLORER_CB_THRESHOLD=5  # Failures before opening
export EXPLORER_CB_TIMEOUT=60   # Seconds before retry
```

3. **Review Error Categories:**
```python
# Check error categorization:
category, should_retry, context = chat_service._categorize_error(error, cmd)
print(f"Category: {category}")
print(f"Should retry: {should_retry}")
print(f"Context: {context}")
```

4. **Handle Permanent Errors:**
```python
# Permanent errors won't retry:
# - FileNotFoundError
# - PermissionError
# - Invalid regex
# - Syntax errors

# Check error category and handle accordingly
if category == "permanent":
    # Don't retry, show error to user
    pass
elif category == "transient":
    # Will retry automatically
    pass
```

## Error Interpretation

### Error Categories

**Permanent Errors:**
- File not found
- Permission denied
- Invalid syntax
- Bad request (400, 404)

**Transient Errors:**
- Timeout
- Connection error
- Network issues
- Service unavailable (503, 502, 504)
- Rate limiting (429)

### Error Messages

**File Not Found:**
```
Error: File 'backend/missing.py' not found
Category: permanent
Suggestion: Check file path. Use SEARCH to find similar files.
```

**Timeout:**
```
Error: Operation timed out
Category: transient
Suggestion: Retry with smaller context size or increase timeout.
```

**Invalid Regex:**
```
Error: Invalid regex pattern: [unclosed
Category: permanent
Suggestion: Check regex syntax. Use READ to see the file first.
```

## Debugging Timeout Issues

### 1. Check Timeout Configuration

```python
from backend.services.explorer_config import get_config

config = get_config()
print(f"Exploration timeout: {config.exploration_timeout}s")
print(f"Per-step timeout: {config.per_step_timeout}s")
```

### 2. Monitor Progress

Use streaming API to monitor progress:

```python
response = requests.post("/api/chat/stream", json={...}, stream=True)
for line in response.iter_lines():
    data = json.loads(line.decode('utf-8').replace('data: ', ''))
    if data.get('type') == 'progress':
        print(f"Progress: {data['current']}/{data['total']} - {data['message']}")
```

### 3. Check Logs

Review logs for timeout warnings:

```bash
# Look for timeout-related logs
grep -i "timeout" logs/chat_service.log

# Check agent mode logs
grep -i "agent.*timeout" logs/chat_service.log
```

### 4. Profile Performance

```python
import time

start = time.time()
result = chat("Your query", use_agent_mode=True)
elapsed = time.time() - start

print(f"Total time: {elapsed:.2f}s")
print(f"Files read: {len(result.get('files_read', []))}")
print(f"Commands: {len(result.get('commands_used', []))}")
```

## Performance Analysis

### Cache Effectiveness

**Check Cache Hit Rate:**
```python
# Review metrics
metrics = get_metrics()
cache_hits = metrics.get('cache_hits', 0)
cache_misses = metrics.get('cache_misses', 0)
hit_rate = cache_hits / (cache_hits + cache_misses) if (cache_hits + cache_misses) > 0 else 0

print(f"Cache hit rate: {hit_rate:.0%}")
```

**Improve Hit Rate:**
- Increase cache sizes
- Use repeated queries
- Keep cache warm

### Response Time Analysis

**Breakdown:**
```python
# Check timing breakdown
result = chat("Your query")
timing = result.get('timing', {})

print(f"Exploration: {timing.get('exploration', 0):.2f}s")
print(f"Formatting: {timing.get('formatting', 0):.2f}s")
print(f"Validation: {timing.get('validation', 0):.2f}s")
print(f"Total: {timing.get('total', 0):.2f}s")
```

**Optimize:**
- Reduce exploration time: Use Search mode first
- Reduce formatting time: Limit results
- Reduce validation time: Disable if not needed

### Memory Usage

**Monitor Memory:**
```python
import psutil
import os

process = psutil.Process(os.getpid())
memory_mb = process.memory_info().rss / 1024 / 1024

print(f"Memory usage: {memory_mb:.2f} MB")
```

**Reduce Memory:**
- Lower cache sizes
- Reduce result limits
- Use early termination

## Performance Metrics

### Accessing Metrics

Metrics are logged to `chat_metrics.jsonl`:

```python
import json

with open('chat_metrics.jsonl', 'r') as f:
    for line in f:
        metric = json.loads(line)
        print(f"{metric['timestamp']}: {metric['operation']} - {metric['duration_ms']}ms")
```

### Key Metrics

- **Response Time**: Total time to generate response
- **Cache Hit Rate**: Percentage of cache hits
- **Files Read**: Number of files accessed
- **Commands Executed**: Number of commands run
- **Error Rate**: Percentage of failed commands

### Benchmarking

Run benchmarks:

```bash
python -m pytest tests/test_performance_benchmark.py -v
```

## Common Patterns

### Pattern 1: Slow Agent Mode

**Problem:** Agent mode taking too long

**Solution:**
```python
# Use Search mode first to narrow scope
search_result = chat("Find relevant files", use_search_mode=True)

# Then use Agent mode on specific files
agent_result = chat(
    f"Analyze: {search_result['findings'][:5]}",  # Limit to top 5
    use_agent_mode=True,
    context_size=32000  # Reduced context
)
```

### Pattern 2: Low Confidence

**Problem:** Confidence score too low

**Solution:**
```python
# Increase exploration
result = chat("Your query", use_agent_mode=True, context_size=64000)

# Check errors
if result.get('errors'):
    # Fix errors first
    pass

# Verify files were read
if len(result.get('files_read', [])) < 3:
    # Need more exploration
    pass
```

### Pattern 3: Too Many Results

**Problem:** Response too large, slow formatting

**Solution:**
```bash
# Reduce result limits
export EXPLORER_MAX_FINDINGS=200
export EXPLORER_MAX_SEARCH_RESULTS=5
```

## Getting Help

### Logs

Check logs for detailed error information:

```bash
# Chat service logs
tail -f logs/chat_service.log

# Error logs
grep -i "error" logs/chat_service.log

# Performance logs
grep -i "performance" logs/chat_service.log
```

### Debug Mode

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Report Issues

When reporting issues, include:
1. Error message
2. Query used
3. Mode and context size
4. Logs (if available)
5. Expected vs actual behavior

## See Also

- [API Usage Documentation](CODE_ASSISTANT_API.md)
- [Mode Selection Guide](MODE_SELECTION_GUIDE.md)
- [Performance Tuning Guide](PERFORMANCE_TUNING.md)

