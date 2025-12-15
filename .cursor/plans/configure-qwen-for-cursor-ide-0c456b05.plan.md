---
name: Configure Qwen Model for Cursor IDE Integration
overview: ""
todos:
  - id: 8fd3f16f-7782-4c3f-ae03-4823639af885
    content: Create docs/CURSOR_QWEN_SETUP.md with step-by-step setup instructions for using Qwen with Cursor Codebase Search
    status: pending
  - id: 682140ce-148c-4add-9308-51dc532611af
    content: Create docs/CURSOR_AGENT_MODE_LIMITATIONS.md explaining why Agent/Composer mode does not work with local models
    status: pending
  - id: 7b29ce8b-96e1-4421-8799-7a0d9fa792fd
    content: Create docs/CURSOR_QWEN_WORKFLOW.md with best practices and recommended query patterns
    status: pending
  - id: 5cd44744-6389-474e-a07b-f7f13fa05786
    content: Create docs/CURSOR_CONTINUE_EXTENSION.md documenting the Continue extension as an alternative for local model agent capabilities
    status: pending
  - id: 0fa7fda6-c567-4a4f-be7f-6ec40998c335
    content: Create docs/CURSOR_QWEN_QUICK_REF.md with one-page quick reference for common tasks
    status: pending
---

# Configure Qwen Model for Cursor IDE Integration

## Overview

This plan documents how to configure your local Qwen model (via Ollama) to work with Cursor IDE's built-in features, specifically:

- **Codebase Search (@Codebase)** - ✅ Works with Qwen
- **Agent/Composer Mode (Ctrl+I)** - ❌ Not supported (technical limitation)

## Current State

Your codebase already has extensive Ollama/Qwen integration for backend services:

- `backend/config.py` - Configured with `qwen2.5-coder:7b` as primary model
- `backend/services/chat_service.py` - Chat service with multi-model support
- `backend/services/model_registry.py` - Model registry for dynamic selection
- Ollama URL: `http://localhost:11434` (default)

## Implementation Plan

### 1. Create Cursor IDE Configuration Guide

**File: `docs/CURSOR_QWEN_SETUP.md`**

Document:

- Prerequisites (Ollama installed, Qwen model pulled)
- How to select Qwen in Cursor Chat (Ctrl+L)
- Step-by-step guide for using @Codebase with Qwen
- Example queries and expected behavior
- Troubleshooting common issues

### 2. Document Agent/Composer Limitations

**File: `docs/CURSOR_AGENT_MODE_LIMITATIONS.md`**

Explain:

- Why Agent/Composer mode doesn't work with local models
- Technical reason (proprietary API only understood by Claude/GPT-4)
- What happens when Qwen tries to use Agent mode (raw JSON output)
- Current Cursor limitations (no public API docs for local models)

### 3. Create Workflow Guide

**File: `docs/CURSOR_QWEN_WORKFLOW.md`**

Provide:

- Best practices for using Qwen with Codebase Search
- Recommended query patterns
- How to structure questions for best results
- Copy-paste workflow for fixes (since Agent mode doesn't work)
- Context optimization tips

### 4. Document Continue Extension Alternative

**File: `docs/CURSOR_CONTINUE_EXTENSION.md`**

Include:

- What Continue extension is
- How to install it in Cursor
- How to connect it to Ollama
- When to use Continue vs native Cursor Chat
- Limitations and benefits

### 5. Create Quick Reference Card

**File: `docs/CURSOR_QWEN_QUICK_REF.md`**

One-page reference with:

- Keyboard shortcuts
- Model selection steps
- Common @Codebase queries
- Troubleshooting checklist

## Technical Details

### Codebase Search (@Codebase) - How It Works

1. Cursor's cloud servers index your codebase (fast embeddings)
2. When you use @Codebase, Cursor finds relevant file chunks
3. Those chunks are sent to your selected local model (Qwen)
4. Qwen reads the files and generates the answer
5. Result: Private, local code analysis

### Agent/Composer Mode - Why It Fails

- Cursor's Agent mode uses proprietary commands (e.g., `{"name": "SwitchMode"...}`)
- Only Claude and GPT-4 are trained on this API
- Qwen outputs raw JSON instead of executing commands
- No workaround available until Cursor releases local model API docs

## Files to Create

1. `docs/CURSOR_QWEN_SETUP.md` - Main setup guide
2. `docs/CURSOR_AGENT_MODE_LIMITATIONS.md` - Limitations explanation
3. `docs/CURSOR_QWEN_WORKFLOW.md` - Best practices workflow
4. `docs/CURSOR_CONTINUE_EXTENSION.md` - Alternative solution
5. `docs/CURSOR_QWEN_QUICK_REF.md` - Quick reference

## Verification Steps

After documentation is created:

1. Verify Ollama is running: `ollama list`
2. Verify Qwen model is available: `ollama list | grep qwen`
3. Test Codebase Search in Cursor with Qwen selected
4. Document any additional findings or edge cases

## Notes

- This is documentation-only (no code changes needed)
- Cursor IDE configuration is done through UI, not config files
- Backend Ollama integration is already working (separate from IDE integration)
- Focus on user-facing documentation and workflows