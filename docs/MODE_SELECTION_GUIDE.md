# Mode Selection Guide

## Overview

The Code Assistant supports three modes of operation, each optimized for different use cases. This guide helps you choose the right mode for your needs.

## Mode Comparison

| Feature | Normal Mode | Search Mode | Agent Mode |
|---------|------------|-------------|------------|
| **Use Case** | Simple questions | Discovery & exploration | Complex problem-solving |
| **Exploration** | None | Comprehensive | Autonomous multi-step |
| **Speed** | Fast (< 5s) | Medium (10-30s) | Slow (30s-10min) |
| **Context Size** | Small (8k-16k) | Medium (16k-32k) | Large (32k-128k) |
| **Best For** | Specific files/functions | Finding patterns | Debugging, analysis |

## Normal Mode (Default)

**When to Use:**
- Questions about specific files or functions you already know
- Simple code explanations
- Quick lookups
- Questions that don't require exploration

**Example Queries:**
- "What does the `upload_file` function do?"
- "Show me the error handling in `backend/routes/upload.py`"
- "Explain this code snippet: [code]"

**Performance:**
- Response time: < 5 seconds
- Context size: 8k-16k tokens
- Resource usage: Low

**Limitations:**
- Cannot discover new files
- Limited to files already in context
- No autonomous exploration

**Example:**
```python
response = requests.post("/api/chat", json={
    "message": "What does upload_file do?",
    "context_size": 16000
})
```

## Search Mode

**When to Use:**
- Finding files, functions, or patterns across the codebase
- Discovery tasks ("find all X")
- Comprehensive exploration
- When you don't know where to look

**Example Queries:**
- "Find all error handling patterns"
- "Where are database queries executed?"
- "Find all files that use the upload service"
- "Show me all authentication middleware"

**Performance:**
- Response time: 10-30 seconds
- Context size: 16k-32k tokens
- Resource usage: Medium

**Features:**
- Comprehensive codebase exploration
- Multiple search strategies (semantic, grep, AST)
- Finds related files and patterns
- Returns structured findings

**Example:**
```python
response = requests.post("/api/chat", json={
    "message": "Find all error handling patterns",
    "use_search_mode": True,
    "context_size": 32000
})

findings = response.json()["findings"]
for finding in findings:
    print(f"{finding['file']}:{finding['line']} - {finding['match']}")
```

## Agent Mode

**When to Use:**
- Complex debugging tasks
- Multi-step investigations
- Root cause analysis
- When you need autonomous problem-solving
- Questions requiring multiple files and analysis

**Example Queries:**
- "Why is the upload endpoint returning 500 errors?"
- "Debug the authentication flow"
- "Find the root cause of the memory leak"
- "Analyze the data flow from upload to database"

**Performance:**
- Response time: 30 seconds - 10 minutes
- Context size: 32k-128k tokens
- Resource usage: High

**Features:**
- Autonomous multi-turn exploration
- Automatic command generation and execution
- Root cause analysis with file:line references
- Confidence scoring
- Progress tracking via streaming

**Example:**
```python
response = requests.post("/api/chat", json={
    "message": "Why is upload returning 500 errors?",
    "use_agent_mode": True,
    "context_size": 64000
})

result = response.json()
print(f"Confidence: {result['confidence']:.0%}")
print(f"Files analyzed: {len(result['files_read'])}")
print(result['response'])
```

## Performance Implications

### Response Times

| Mode | Min | Typical | Max |
|------|-----|---------|-----|
| Normal | 1s | 3s | 10s |
| Search | 5s | 15s | 60s |
| Agent | 30s | 2min | 10min |

### Resource Usage

| Mode | CPU | Memory | Network |
|------|-----|--------|---------|
| Normal | Low | Low | Low |
| Search | Medium | Medium | Medium |
| Agent | High | High | High |

### Context Size Recommendations

| Mode | Min | Recommended | Max |
|------|-----|-------------|-----|
| Normal | 8k | 16k | 32k |
| Search | 16k | 32k | 64k |
| Agent | 32k | 64k | 128k |

## Best Practices

### 1. Start Simple

Always start with Normal mode. Only use Search or Agent mode if Normal mode doesn't provide sufficient results.

### 2. Use Search Mode for Discovery

When you need to find files or patterns:
- Use Search mode instead of asking "where is X?"
- Search mode is faster than Agent mode for discovery
- Results are structured and easy to process

### 3. Use Agent Mode for Complex Problems

When you need:
- Multi-step analysis
- Root cause investigation
- Debugging complex issues
- Understanding data flows

### 4. Adjust Context Size

- **Small codebases (< 10k LOC)**: 16k-32k tokens
- **Medium codebases (10k-100k LOC)**: 32k-64k tokens
- **Large codebases (> 100k LOC)**: 64k-128k tokens

### 5. Monitor Confidence Scores

- **High confidence (> 0.7)**: Results are reliable
- **Medium confidence (0.5-0.7)**: Results are good but may need verification
- **Low confidence (< 0.5)**: More exploration needed

### 6. Use Streaming for Long Operations

For Agent mode or large Search operations, use the streaming API:
```python
response = requests.post("/api/chat/stream", json={...}, stream=True)
for line in response.iter_lines():
    # Process progress updates
```

## Query Formulation Tips

### Normal Mode Queries

✅ **Good:**
- "What does `upload_file` do in `backend/routes/upload.py`?"
- "Show me the error handling in the upload route"

❌ **Bad:**
- "Find the upload function" (use Search mode)
- "Debug the upload issue" (use Agent mode)

### Search Mode Queries

✅ **Good:**
- "Find all error handling patterns"
- "Where are database queries executed?"
- "Find all files that import the upload service"

❌ **Bad:**
- "What does this function do?" (use Normal mode)
- "Why is this failing?" (use Agent mode)

### Agent Mode Queries

✅ **Good:**
- "Why is the upload endpoint returning 500 errors?"
- "Debug the authentication flow"
- "Find the root cause of the memory leak"

❌ **Bad:**
- "What does this function do?" (use Normal mode)
- "Find all error handlers" (use Search mode)

## Mode Selection Decision Tree

```
Start
  │
  ├─ Is it a simple question about known code?
  │  └─ Yes → Normal Mode
  │
  ├─ Do you need to find files/patterns?
  │  └─ Yes → Search Mode
  │
  ├─ Is it a complex problem requiring analysis?
  │  └─ Yes → Agent Mode
  │
  └─ Default → Normal Mode
```

## Examples

### Example 1: Simple Question

**Query:** "What does the `process_upload` function do?"

**Mode:** Normal

**Reason:** Specific function, no exploration needed

### Example 2: Discovery

**Query:** "Find all places where we handle file uploads"

**Mode:** Search

**Reason:** Need to discover files across codebase

### Example 3: Debugging

**Query:** "Why are uploads failing with 500 errors?"

**Mode:** Agent

**Reason:** Complex problem requiring multi-step investigation

## See Also

- [API Usage Documentation](CODE_ASSISTANT_API.md)
- [Performance Tuning Guide](PERFORMANCE_TUNING.md)
- [Troubleshooting Guide](TROUBLESHOOTING_ASSISTANT.md)

