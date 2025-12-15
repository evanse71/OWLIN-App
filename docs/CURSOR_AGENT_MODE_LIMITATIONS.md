# Cursor Agent/Composer Mode Limitations with Local Models

## Overview

This document explains why Cursor's Agent/Composer mode (Ctrl+I) does not work with local models like Qwen, and what happens when you try to use it.

## What is Agent/Composer Mode?

Agent/Composer mode (activated with `Ctrl+I` or `Cmd+I`) is Cursor's feature that allows AI to:
- Automatically edit files
- Navigate between files
- Execute commands
- Make multiple changes across your codebase
- Work autonomously to complete complex tasks

This is different from Chat mode (Ctrl+L), which only provides answers and suggestions.

## The Problem: Why Local Models Don't Work

### Technical Reason

Cursor's Agent/Composer mode uses a **proprietary command language** that only Claude (Anthropic) and GPT-4 (OpenAI) are trained to understand. This command language includes special instructions like:

```json
{"name": "SwitchMode", "args": {...}}
{"name": "EditFile", "args": {"path": "...", "edits": [...]}}
{"name": "ReadFile", "args": {"path": "..."}}
{"name": "SearchCodebase", "args": {...}}
```

When you select a local model (like Qwen) in Agent/Composer mode:

1. **Cursor sends the proprietary commands** to your local model
2. **Qwen doesn't understand the command format** (it wasn't trained on Cursor's API)
3. **Qwen outputs the raw JSON** instead of executing commands
4. **No code changes happen** - you just see JSON text in the response

### What You'll See

Instead of code being edited, you'll see output like:

```
{"name": "SwitchMode", "args": {"mode": "edit"}}
{"name": "EditFile", "args": {"path": "backend/main.py", "edits": [...]}}
```

This is Qwen literally outputting the commands as text, rather than Cursor executing them.

## Why This Limitation Exists

### 1. Proprietary API

Cursor has not released public documentation for their Agent/Composer API. The command language is:
- Proprietary to Cursor
- Only documented internally
- Only Claude and GPT-4 are trained on it

### 2. Training Requirements

For a model to work with Agent/Composer mode, it needs to be:
- Trained specifically on Cursor's command format
- Fine-tuned to understand the editor context
- Able to generate valid command sequences

Local models like Qwen, Llama, Mistral, etc. are general-purpose coding models. They haven't been trained on Cursor's specific API.

### 3. No Public API Documentation

Even if you wanted to fine-tune Qwen yourself, Cursor hasn't released:
- API documentation for local models
- Command format specifications
- Integration guidelines

## What Works vs. What Doesn't

### ✅ Works with Local Models

1. **Chat Mode (Ctrl+L)**
   - Regular Q&A
   - Code explanations
   - Suggestions and recommendations

2. **Codebase Search (@Codebase)**
   - Finding files and functions
   - Explaining code logic
   - Identifying bugs
   - Code analysis

3. **File Context**
   - Asking about selected code
   - Explaining specific functions
   - Reviewing code snippets

### ❌ Does NOT Work with Local Models

1. **Agent/Composer Mode (Ctrl+I)**
   - Automatic file editing
   - Multi-file refactoring
   - Autonomous task completion
   - Command execution

2. **Auto-Apply Changes**
   - Direct code modifications
   - Automatic fix application
   - Batch edits

## Workarounds

### 1. Copy-Paste Workflow

Since Agent mode doesn't work, use this workflow:

1. **Ask Qwen in Chat mode** (Ctrl+L) with @Codebase:
   ```
   @Codebase Find and fix memory leaks in the backend
   ```

2. **Qwen provides the fix** with code examples

3. **Manually copy and paste** the suggested code into your files

4. **Review and test** the changes

### 2. Use Continue Extension

The Continue extension (see `CURSOR_CONTINUE_EXTENSION.md`) provides:
- Open-source agent capabilities
- Built specifically for local models
- Works with Ollama
- Can perform some automated edits

**Trade-off:** Less polished than Cursor's native Agent mode, but actually works with local models.

### 3. Hybrid Approach

Use both:
- **Cursor Chat + @Codebase** for analysis and suggestions (with Qwen)
- **Claude/GPT-4 Agent mode** for complex automated refactoring (when needed)

## When Will This Be Fixed?

### Current Status

As of now, there's no timeline for:
- Public API documentation for local models
- Support for local models in Agent/Composer mode
- Fine-tuning guides for Cursor's command language

### Potential Future Solutions

1. **Cursor releases API docs** - Then community can fine-tune models
2. **Cursor adds native support** - Direct integration with Ollama/local models
3. **Community reverse-engineering** - Unlikely but possible

## Alternative: Continue Extension

If you need agent-like capabilities with local models, consider the Continue extension:

- **Open-source** and designed for local models
- **Works with Ollama** out of the box
- **Has agent capabilities** that actually work
- **Less polished** than Cursor's native mode

See `CURSOR_CONTINUE_EXTENSION.md` for setup instructions.

## Summary

| Feature | Local Models (Qwen) | Claude/GPT-4 |
|---------|---------------------|--------------|
| Chat Mode (Ctrl+L) | ✅ Works | ✅ Works |
| @Codebase Search | ✅ Works | ✅ Works |
| Agent/Composer (Ctrl+I) | ❌ Doesn't work | ✅ Works |
| Auto-edit files | ❌ Doesn't work | ✅ Works |

## Key Takeaways

1. **Agent/Composer mode requires proprietary API knowledge** that only Claude/GPT-4 have
2. **Local models output raw JSON** instead of executing commands
3. **Use Chat + @Codebase** for analysis, then manually apply fixes
4. **Consider Continue extension** if you need agent capabilities with local models
5. **No workaround exists** until Cursor releases API documentation

## Related Documentation

- `CURSOR_QWEN_SETUP.md` - How to set up Qwen for Codebase Search
- `CURSOR_QWEN_WORKFLOW.md` - Best practices for using Qwen effectively
- `CURSOR_CONTINUE_EXTENSION.md` - Alternative agent solution
- `CURSOR_QWEN_QUICK_REF.md` - Quick reference guide
