# Code Assistant API Documentation

## Overview

The Code Assistant API provides intelligent code exploration, analysis, and problem-solving capabilities through multiple modes of operation. This document describes the API endpoints, request/response formats, and usage examples.

## Endpoints

### POST `/api/chat`

Main chat endpoint for code assistant interactions.

**Request Body:**
```json
{
  "message": "Find the upload endpoint issue",
  "context_size": 32000,
  "use_search_mode": false,
  "use_agent_mode": true,
  "force_agent": false
}
```

**Response:**
```json
{
  "response": "I found the issue in backend/routes/upload.py:42...",
  "confidence": 0.85,
  "files_read": ["backend/routes/upload.py"],
  "commands_used": ["SEARCH", "READ"],
  "findings": [...]
}
```

### POST `/api/chat/stream`

Streaming chat endpoint for real-time progress updates using Server-Sent Events (SSE).

**Request Body:** Same as `/api/chat`

**Response:** SSE stream with events:
- `plan`: Exploration plan with tasks
- `progress`: Progress updates (current/total)
- `task`: Task status updates
- `done`: Final response
- `error`: Error messages

## ChatRequest Parameters

### `message` (required)
- **Type:** `string`
- **Description:** User's question or request
- **Example:** `"Find all upload endpoints"`

### `context_size` (optional)
- **Type:** `integer`
- **Default:** `128000`
- **Description:** Maximum context size in tokens
- **Range:** `8000` - `128000`
- **Example:** `32000`

### `use_search_mode` (optional)
- **Type:** `boolean`
- **Default:** `false`
- **Description:** Enable search/exploration mode for comprehensive codebase exploration
- **Use when:** You need to discover files, functions, or patterns across the codebase

### `use_agent_mode` (optional)
- **Type:** `boolean`
- **Default:** `false`
- **Description:** Enable autonomous agent mode for complex problem-solving
- **Use when:** You need multi-step analysis, debugging, or complex investigations

### `force_agent` (optional)
- **Type:** `boolean`
- **Default:** `false`
- **Description:** Force agent mode even if not automatically detected as needed
- **Use when:** You want guaranteed autonomous exploration

## Mode Examples

### Normal Mode (Default)

Simple questions that don't require exploration:

```python
import requests

response = requests.post("http://localhost:5176/api/chat", json={
    "message": "What does the upload function do?",
    "context_size": 16000
})

print(response.json()["response"])
```

### Search Mode

Comprehensive exploration to find files and patterns:

```python
response = requests.post("http://localhost:5176/api/chat", json={
    "message": "Find all error handling patterns in the codebase",
    "use_search_mode": True,
    "context_size": 32000
})

result = response.json()
print(f"Found {len(result['findings'])} matches")
for finding in result['findings']:
    print(f"  - {finding['file']}:{finding['line']}")
```

### Agent Mode

Complex problem-solving with autonomous exploration:

```python
response = requests.post("http://localhost:5176/api/chat", json={
    "message": "Why is the upload endpoint returning 500 errors?",
    "use_agent_mode": True,
    "context_size": 64000
})

result = response.json()
print(f"Confidence: {result['confidence']:.0%}")
print(f"Files analyzed: {len(result['files_read'])}")
print(result['response'])
```

## Streaming API

Use the streaming endpoint for real-time progress updates:

```python
import requests
import json

response = requests.post(
    "http://localhost:5176/api/chat/stream",
    json={
        "message": "Analyze the entire codebase structure",
        "use_agent_mode": True,
        "context_size": 128000
    },
    stream=True
)

for line in response.iter_lines():
    if line:
        data = json.loads(line.decode('utf-8').replace('data: ', ''))
        event_type = data.get('type')
        
        if event_type == 'plan':
            print(f"Plan: {data.get('tasks', [])}")
        elif event_type == 'progress':
            print(f"Progress: {data.get('current')}/{data.get('total')} - {data.get('message')}")
        elif event_type == 'done':
            print(f"Response: {data.get('response')}")
        elif event_type == 'error':
            print(f"Error: {data.get('message')}")
```

## Response Formats

### ChatResponse

```typescript
interface ChatResponse {
  response: string;              // Main response text
  confidence?: number;           // Confidence score (0.0-1.0)
  files_read?: string[];         // Files that were read
  commands_used?: string[];      // Commands executed
  findings?: Finding[];          // Search/grep findings
  error?: string;                // Error message if failed
}
```

### Finding

```typescript
interface Finding {
  type: "read" | "search" | "grep" | "trace";
  file: string;
  line?: number;
  line_range?: string;           // e.g., "10-20"
  match?: string;
  context?: string;
}
```

## Error Handling

### Error Response Format

```json
{
  "error": "File not found: backend/missing.py",
  "error_category": "permanent",
  "suggestions": ["Check file path", "Use SEARCH to find similar files"]
}
```

### Error Categories

- **permanent**: Errors that won't be fixed by retrying (e.g., file not found, invalid syntax)
- **transient**: Errors that might succeed on retry (e.g., timeout, connection error)

### Retry Logic

Transient errors are automatically retried with exponential backoff:
- Initial delay: 1 second
- Max delay: 10 seconds
- Max retries: 3

Circuit breaker prevents cascading failures after repeated errors.

## Code Examples

### JavaScript/TypeScript

```typescript
async function askAssistant(message: string, useAgentMode = false) {
  const response = await fetch('http://localhost:5176/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message,
      use_agent_mode: useAgentMode,
      context_size: 32000
    })
  });
  
  if (!response.ok) {
    throw new Error(`API error: ${response.statusText}`);
  }
  
  return await response.json();
}

// Usage
const result = await askAssistant(
  "Find all database queries in the codebase",
  true  // Use agent mode
);

console.log(result.response);
console.log(`Confidence: ${(result.confidence * 100).toFixed(0)}%`);
```

### Python

```python
import requests
from typing import Dict, Any, Optional

def chat(message: str, 
         use_search_mode: bool = False,
         use_agent_mode: bool = False,
         context_size: int = 32000) -> Dict[str, Any]:
    """Send a chat request to the code assistant."""
    response = requests.post(
        "http://localhost:5176/api/chat",
        json={
            "message": message,
            "use_search_mode": use_search_mode,
            "use_agent_mode": use_agent_mode,
            "context_size": context_size
        }
    )
    response.raise_for_status()
    return response.json()

# Usage examples
result = chat("What does the upload function do?")
print(result["response"])

result = chat(
    "Find all error handling patterns",
    use_search_mode=True
)

result = chat(
    "Debug the 500 error in upload endpoint",
    use_agent_mode=True,
    context_size=64000
)
```

## Best Practices

1. **Start with Normal Mode**: Use normal mode for simple questions
2. **Use Search Mode for Discovery**: When you need to find files or patterns
3. **Use Agent Mode for Complex Problems**: For debugging, analysis, or multi-step investigations
4. **Adjust Context Size**: Larger contexts allow more exploration but take longer
5. **Monitor Confidence Scores**: Low confidence (< 0.5) suggests more exploration needed
6. **Use Streaming for Long Operations**: Stream progress for agent mode or large searches
7. **Handle Errors Gracefully**: Check error categories and suggestions

## Rate Limiting

- No explicit rate limiting, but circuit breakers prevent abuse
- Large context sizes and agent mode operations may take several minutes
- Use streaming API for better user experience during long operations

## See Also

- [Mode Selection Guide](MODE_SELECTION_GUIDE.md)
- [Performance Tuning Guide](PERFORMANCE_TUNING.md)
- [Troubleshooting Guide](TROUBLESHOOTING_ASSISTANT.md)

