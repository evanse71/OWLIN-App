# Cursor IDE + Qwen Setup Guide

## Overview

This guide explains how to configure your local Qwen model (via Ollama) to work with Cursor IDE's Codebase Search feature. This allows you to use Qwen for private, local code analysis without sending your code to external services.

## Prerequisites

### 1. Install Ollama

If you haven't already, install Ollama from [ollama.ai](https://ollama.ai).

**Windows:**
- Download the installer from the website
- Run the installer
- Ollama will start automatically as a service

**Verify installation:**
```powershell
ollama --version
```

### 2. Pull Qwen Model

Pull the Qwen model you want to use. Recommended models:

```powershell
# Recommended: Qwen 2.5 Coder 7B (best balance of quality and speed)
ollama pull qwen2.5-coder:7b

# Alternative: Qwen 2.5 Coder 32B (better quality, slower)
ollama pull qwen2.5-coder:32b

# Or use the latest tag
ollama pull qwen2.5-coder:latest
```

**Verify model is available:**
```powershell
ollama list
```

You should see your Qwen model in the list.

### 3. Ensure Ollama is Running

Ollama should be running as a service. Verify it's accessible:

```powershell
# Test Ollama API
curl http://localhost:11434/api/tags
```

If you get a JSON response with model information, Ollama is running correctly.

## Step-by-Step Setup in Cursor

### Step 1: Open Cursor Chat

1. Press `Ctrl + L` (or `Cmd + L` on Mac) to open the Chat panel
2. The chat interface will appear on the right side of your screen

### Step 2: Select Qwen Model

1. Look for the model selector at the top of the chat panel
2. Click on the model dropdown (may show "Claude" or "GPT-4" by default)
3. Scroll through the list to find your local models
4. Select `qwen2.5-coder:32b` (or whichever Qwen model you pulled)

**Note:** If you don't see your local model:
- Ensure Ollama is running
- Restart Cursor IDE
- Check that the model is available: `ollama list`

### Step 3: Enable Codebase Indexing

Before using @Codebase, ensure your project is indexed:

1. Look at the top right of Cursor for "Codebase Indexing" status
2. Or go to: **Settings > Features > Codebase**
3. Ensure "Codebase Indexing" is enabled
4. Wait for indexing to complete (first time may take a few minutes)

### Step 4: Use @Codebase with Qwen

Now you're ready to use Codebase Search with Qwen:

1. In the chat input, type `@Codebase` (or press `Ctrl + Enter` after typing your query)
2. Type your question about your codebase
3. Press Enter

**Example queries:**
```
@Codebase Find any potential bugs in my user authentication logic
```

```
@Codebase Search the entire repo for memory leaks in the backend and show me the code to fix them
```

```
@Codebase How does the invoice pairing system work?
```

## How It Works

1. **Indexing Phase:** Cursor's cloud servers create embeddings of your codebase (this is fast and doesn't send your code to AI models)
2. **Search Phase:** When you use @Codebase, Cursor finds relevant file chunks using semantic search
3. **Analysis Phase:** Those file chunks are sent to your **local Qwen model** (running via Ollama)
4. **Response Phase:** Qwen reads the files and generates an answer locally on your machine
5. **Result:** Private, local code analysis without sending code to external services

## Example Usage

### Finding Bugs

**Query:**
```
@Codebase Find any potential bugs in my user authentication logic
```

**What happens:**
- Cursor finds files related to authentication
- Sends those files to your local Qwen model
- Qwen analyzes the code and identifies potential issues
- Returns a detailed explanation with code references

### Understanding Code Flow

**Query:**
```
@Codebase How does the invoice pairing system work? Show me the main components
```

**What happens:**
- Cursor finds files related to invoice pairing
- Qwen reads through the code and explains the architecture
- Returns a structured explanation with file paths and line numbers

### Code Refactoring Suggestions

**Query:**
```
@Codebase Review the backend/services/chat_service.py file and suggest improvements for error handling
```

**What happens:**
- Cursor loads the specific file
- Qwen analyzes the code structure
- Returns specific suggestions with code examples

## Troubleshooting

### Qwen Model Not Appearing in Cursor

**Problem:** You don't see your Qwen model in the model selector.

**Solutions:**
1. Verify Ollama is running:
   ```powershell
   ollama list
   ```

2. Restart Cursor IDE completely

3. Check Ollama is accessible:
   ```powershell
   curl http://localhost:11434/api/tags
   ```

4. Ensure you've pulled the model:
   ```powershell
   ollama pull qwen2.5-coder:32b
   ```

### Slow Responses

**Problem:** Qwen is responding slowly.

**Solutions:**
1. Use a smaller model (7B instead of 32B)
2. Reduce the scope of your @Codebase query
3. Check system resources (CPU/GPU usage)
4. Ensure Ollama is using GPU if available:
   ```powershell
   # Check if GPU is being used
   ollama ps
   ```

### Codebase Not Indexed

**Problem:** @Codebase doesn't find relevant files.

**Solutions:**
1. Check indexing status in Cursor settings
2. Manually trigger re-indexing: **Settings > Features > Codebase > Re-index**
3. Wait for indexing to complete (check progress indicator)

### Qwen Returns Generic Answers

**Problem:** Qwen gives generic responses instead of code-specific answers.

**Solutions:**
1. Be more specific in your query
2. Include file paths or function names in your question
3. Use multiple @Codebase queries to narrow down
4. Ensure the codebase is properly indexed

### Connection Errors

**Problem:** Cursor can't connect to Ollama.

**Solutions:**
1. Verify Ollama is running:
   ```powershell
   Get-Process ollama
   ```

2. Check Ollama URL (default: `http://localhost:11434`)

3. Restart Ollama service:
   ```powershell
   # Stop Ollama
   Stop-Service ollama
   # Start Ollama
   Start-Service ollama
   ```

## Best Practices

1. **Be Specific:** Instead of "find bugs," ask "find potential null pointer exceptions in the authentication module"

2. **Use File Context:** Reference specific files or functions in your queries

3. **Iterative Queries:** Start broad, then narrow down with follow-up questions

4. **Combine with File Selection:** Select files in the editor before asking questions for better context

5. **Model Selection:** Use 7B for faster responses, 32B for more complex analysis

## Limitations

- **Agent/Composer Mode (Ctrl+I) does NOT work** with local models. See `CURSOR_AGENT_MODE_LIMITATIONS.md` for details.
- Codebase Search works, but you'll need to manually apply fixes (copy-paste workflow)
- Large codebases may take longer to index and search

## Next Steps

- Read `CURSOR_QWEN_WORKFLOW.md` for best practices and query patterns
- Check `CURSOR_AGENT_MODE_LIMITATIONS.md` to understand what doesn't work
- Consider `CURSOR_CONTINUE_EXTENSION.md` for alternative agent capabilities
- Keep `CURSOR_QWEN_QUICK_REF.md` handy for quick reference
