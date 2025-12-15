# Performance Tuning Guide

## Overview

This guide explains how to optimize the Code Assistant for performance, including timeout configuration, caching strategies, result limiting, and optimization tips.

## Timeout Configuration

### ExplorerConfig Settings

Timeouts are configured via environment variables or `ExplorerConfig`:

```python
from backend.services.explorer_config import get_config

config = get_config()

# Timeout settings
config.exploration_timeout = 45      # Total exploration timeout (seconds)
config.per_step_timeout = 15         # Per-step timeout (seconds)
```

### Environment Variables

```bash
# Exploration timeouts
export EXPLORER_TIMEOUT=45           # Total timeout
export EXPLORER_PER_STEP_TIMEOUT=15  # Per-step timeout

# Agent mode timeouts (calculated dynamically based on context size)
# See _calculate_agent_timeout() for details
```

### Timeout Calculation

Agent mode timeouts are calculated dynamically based on:
- Context size (larger = more time)
- Number of files read
- Number of turns
- Maximum turns allowed

**Formula:**
```
base_timeout = 60 + (context_size / 1000) * 2
per_turn_timeout = base_timeout / max_turns
agent_timeout = base_timeout * max_turns
```

**Example:**
- Context size: 64k tokens
- Max turns: 10
- Base timeout: 60 + (64) * 2 = 188 seconds
- Per turn: 18.8 seconds
- Total: 1880 seconds (31 minutes)

### Timeout Limits

Timeouts are capped to prevent excessive waits:

| Context Size | Max Timeout |
|--------------|-------------|
| ≤ 32k | 8 minutes |
| ≤ 64k | 10 minutes |
| ≤ 100k | 12.5 minutes |
| ≥ 128k | 15 minutes |

## Caching Strategies

### File Cache (LRU)

File reads are cached using an LRU (Least Recently Used) cache:

```python
# Cache size (default: 50 files)
export EXPLORER_FILE_CACHE_SIZE=50

# Cache provides:
# - Fast repeated file reads
# - Reduced I/O operations
# - Memory-efficient eviction
```

**Cache Hit Rate:**
- Typical hit rate: 60-80%
- Cache size affects hit rate
- Larger caches = better hit rate but more memory

### Search Cache (TTL)

Search results are cached with TTL (Time To Live):

```python
# Cache TTL (default: 300 seconds = 5 minutes)
export EXPLORER_CACHE_TTL=300

# Cache size (default: 100 entries)
export EXPLORER_MAX_CACHE_SIZE=100
```

**Cache Invalidation:**
- Automatic expiration after TTL
- Manual invalidation on code changes
- Size-based eviction when full

### Relevance Score Cache

Relevance scores are cached for repeated queries:

```python
# Cache size: 1000 entries (hardcoded)
# Key: (file_path, query_hash)
# Value: relevance_score (0.0-1.0)
```

**Benefits:**
- Faster result scoring
- Consistent scoring for same queries
- Reduced computation

### Path Resolution Cache

Resolved file paths are cached:

```python
# Cache key: original_path
# Cache value: (resolved_path, confidence)
# Cache size: Unlimited (bounded by memory)
```

**Benefits:**
- Fast path resolution for repeated paths
- Consistent fuzzy matching results

## Result Limiting

### During Collection

Results are limited during collection to prevent memory issues:

```python
MAX_RESULTS_DURING_COLLECTION = 500
MAX_KEY_INSIGHTS = 50
MAX_DISCOVERED_FILES = 100
```

**Configuration:**
```python
# Max findings (default: 300)
export EXPLORER_MAX_FINDINGS=300

# Max search results per query (default: 10)
export EXPLORER_MAX_SEARCH_RESULTS=10

# Max files per plan (default: 20)
export EXPLORER_MAX_FILES_PER_PLAN=20
```

### During Formatting

Results are further limited during formatting:

```python
MAX_RESULTS_TO_FORMAT = 50  # Only format top 50 results
```

**Prioritization:**
1. Errors (all errors shown)
2. File reads (top 20)
3. Search/grep results (remaining slots)

### Smart Truncation

Content is intelligently truncated:

```python
# Truncation preserves:
# - Function/class definitions
# - Important code patterns
# - Line numbers
# - Code structure
```

**Configuration:**
- Default max length: 500 characters
- Preserves structure at boundaries
- Shows line numbers for truncated sections

## Optimization Tips

### 1. Query Formulation

**Good Queries:**
- Specific and focused
- Include file paths when known
- Use precise terminology

**Bad Queries:**
- Vague or ambiguous
- Too broad ("analyze everything")
- Missing context

### 2. Context Size Selection

**Small Codebases (< 10k LOC):**
```python
context_size = 16000  # 16k tokens
```

**Medium Codebases (10k-100k LOC):**
```python
context_size = 32000  # 32k tokens
```

**Large Codebases (> 100k LOC):**
```python
context_size = 64000  # 64k tokens
```

**Very Large Codebases (> 500k LOC):**
```python
context_size = 128000  # 128k tokens
```

### 3. Mode Selection

- **Normal Mode**: Fastest, use for simple questions
- **Search Mode**: Medium speed, use for discovery
- **Agent Mode**: Slowest, use only for complex problems

### 4. Parallel Execution

Commands are executed in parallel when possible:

```python
# Max parallel searches (default: 4)
export EXPLORER_MAX_PARALLEL_SEARCHES=4

# Max parallel file reads (default: 6)
export EXPLORER_MAX_PARALLEL_FILE_READS=6
```

**Tuning:**
- Increase for faster execution (more CPU/memory)
- Decrease for lower resource usage

### 5. Early Termination

Operations terminate early when:
- Timeout approaching (within 5s buffer)
- Cancellation flag set
- Sufficient results collected

**Benefits:**
- Faster responses
- Lower resource usage
- Better user experience

### 6. Result Deduplication

Results are deduplicated to reduce noise:

```python
# Deduplication:
# - Merges nearby results (within 10 lines)
# - Combines line ranges
# - Removes exact duplicates
```

**Impact:**
- Reduces result set size
- Improves relevance
- Faster processing

## Performance Metrics

### Monitoring

Performance metrics are logged to `chat_metrics.jsonl`:

```json
{
  "timestamp": "2025-01-01T12:00:00Z",
  "operation": "agent_mode",
  "duration_ms": 1234,
  "files_read": 5,
  "commands_executed": 12,
  "cache_hits": 8,
  "cache_misses": 4
}
```

### Key Metrics

- **Response Time**: Total time to generate response
- **Cache Hit Rate**: Percentage of cache hits
- **Files Read**: Number of files accessed
- **Commands Executed**: Number of commands run
- **Error Rate**: Percentage of failed commands

### Benchmarking

Run performance benchmarks:

```bash
python -m pytest tests/test_performance_benchmark.py -v
```

**Benchmarks:**
- Command parsing performance
- Result formatting with large datasets
- Search operations with early termination
- Caching effectiveness
- Timeout handling

## Tuning for Large Codebases

### 1. Increase Cache Sizes

```bash
export EXPLORER_FILE_CACHE_SIZE=100
export EXPLORER_MAX_CACHE_SIZE=200
```

### 2. Increase Parallel Execution

```bash
export EXPLORER_MAX_PARALLEL_SEARCHES=8
export EXPLORER_MAX_PARALLEL_FILE_READS=12
```

### 3. Adjust Timeouts

```bash
export EXPLORER_TIMEOUT=90
export EXPLORER_PER_STEP_TIMEOUT=30
```

### 4. Limit Results More Aggressively

```bash
export EXPLORER_MAX_FINDINGS=200
export EXPLORER_MAX_SEARCH_RESULTS=5
```

### 5. Use Search Mode First

For large codebases, use Search mode to narrow down before Agent mode:

```python
# Step 1: Search to find relevant files
search_result = chat("Find upload-related files", use_search_mode=True)

# Step 2: Agent mode with specific files
agent_result = chat(
    f"Analyze these files: {search_result['findings']}",
    use_agent_mode=True
)
```

## Memory Management

### Cache Memory Usage

```
File Cache: ~50 files * 10KB = 500KB
Search Cache: ~100 entries * 5KB = 500KB
Relevance Cache: ~1000 entries * 100B = 100KB
Total: ~1.1MB (typical)
```

### Result Memory Usage

```
500 results * 2KB = 1MB
50 insights * 1KB = 50KB
100 discovered files * 100B = 10KB
Total: ~1.1MB (typical)
```

### Peak Memory

Peak memory usage during agent mode:
- Base: ~50MB
- Per file read: ~100KB
- Per search result: ~5KB
- **Typical peak: 100-200MB**

## Troubleshooting Performance Issues

### Slow Responses

1. **Check context size**: Reduce if too large
2. **Check mode**: Use Normal mode if possible
3. **Check cache hit rate**: Low hit rate = more I/O
4. **Check timeout settings**: May be too high

### High Memory Usage

1. **Reduce cache sizes**: Lower `EXPLORER_FILE_CACHE_SIZE`
2. **Reduce result limits**: Lower `EXPLORER_MAX_FINDINGS`
3. **Use early termination**: Enable cancellation flags

### Timeout Issues

1. **Increase timeouts**: For large codebases
2. **Reduce context size**: Faster processing
3. **Use Search mode first**: Narrow scope before Agent mode

## See Also

- [API Usage Documentation](CODE_ASSISTANT_API.md)
- [Mode Selection Guide](MODE_SELECTION_GUIDE.md)
- [Troubleshooting Guide](TROUBLESHOOTING_ASSISTANT.md)

