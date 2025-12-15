# Cursor + Qwen Quick Reference

## Keyboard Shortcuts

| Action | Shortcut |
|--------|----------|
| Open Chat | `Ctrl+L` (Windows) / `Cmd+L` (Mac) |
| Open Agent/Composer | `Ctrl+I` (Windows) / `Cmd+I` (Mac) |
| Use @Codebase | Type `@Codebase` or `Ctrl+Enter` |
| Open Continue | Click Continue icon in sidebar |

## Model Selection Steps

1. Press `Ctrl+L` to open Chat
2. Click model dropdown at top of chat panel
3. Select `qwen2.5-coder:32b` (or your preferred Qwen model)
4. If model doesn't appear:
   - Verify Ollama is running: `ollama list`
   - Restart Cursor IDE
   - Check Ollama URL: `http://localhost:11434`

## Common @Codebase Queries

### Bug Finding
```
@Codebase Find [bug type] in [module/file]
```
**Example:**
```
@Codebase Find memory leaks in backend/services/
```

### Code Understanding
```
@Codebase Explain how [system/feature] works
```
**Example:**
```
@Codebase Explain how the invoice pairing system works
```

### Refactoring
```
@Codebase Review [file] and suggest improvements for [area]
```
**Example:**
```
@Codebase Review backend/services/chat_service.py and suggest error handling improvements
```

### Security Review
```
@Codebase Find [security issue] in [area]
```
**Example:**
```
@Codebase Find hardcoded credentials in the codebase
```

## Quick Verification Checklist

### Before Using Qwen

- [ ] Ollama is installed: `ollama --version`
- [ ] Qwen model is pulled: `ollama list | grep qwen`
- [ ] Ollama is running: `curl http://localhost:11434/api/tags`
- [ ] Cursor is restarted (if model doesn't appear)
- [ ] Codebase is indexed (check top-right status)

### Troubleshooting Quick Fixes

| Problem | Quick Fix |
|---------|-----------|
| Model not appearing | Restart Cursor, verify `ollama list` |
| Slow responses | Use 7B model, narrow query scope |
| Generic answers | Be more specific, include file paths |
| Can't find files | Check indexing status, re-index if needed |
| Connection errors | Verify Ollama running: `Get-Process ollama` |

## What Works vs. Doesn't Work

| Feature | Status | Notes |
|---------|--------|-------|
| Chat Mode (Ctrl+L) | ✅ Works | Full Q&A with Qwen |
| @Codebase Search | ✅ Works | Excellent code analysis |
| Agent/Composer (Ctrl+I) | ❌ Doesn't work | Use Continue extension instead |
| Auto-edit files | ❌ Doesn't work | Copy-paste workflow needed |

## Model Recommendations

| Use Case | Recommended Model | Reason |
|----------|------------------|--------|
| Quick questions | `qwen2.5-coder:7b` | Faster responses |
| Deep analysis | `qwen2.5-coder:32b` | Better quality |
| Complex refactoring | `qwen2.5-coder:32b` | More context understanding |

## Workflow Quick Steps

### Finding and Fixing Bugs

1. **Find:** `@Codebase Find [bug type] in [area]`
2. **Understand:** `@Codebase Explain why [issue] happens`
3. **Fix:** `@Codebase Provide complete fix for [issue]`
4. **Apply:** Copy-paste the fix manually
5. **Verify:** `@Codebase Verify this fix is correct`

### Understanding Code

1. **Broad:** `@Codebase How does [system] work?`
2. **Specific:** `@Codebase Show me [specific component]`
3. **Deep:** `@Codebase Explain [specific function/class]`

### Refactoring

1. **Analyze:** `@Codebase Review [file] for improvements`
2. **Get suggestions:** `@Codebase Suggest refactoring for [area]`
3. **Apply:** Copy-paste or use Continue extension
4. **Review:** `@Codebase Verify refactoring is correct`

## Continue Extension Quick Start

1. **Install:** Extensions → Search "Continue" → Install
2. **Connect:** Should auto-detect Ollama
3. **Use:** Select code → Type request → Auto-applies changes
4. **Verify:** Always review diffs before accepting

## Common Commands

### Ollama Commands
```powershell
# List models
ollama list

# Pull model
ollama pull qwen2.5-coder:32b

# Check if running
Get-Process ollama

# Test API
curl http://localhost:11434/api/tags
```

### Cursor Commands
- `Ctrl+L` - Open Chat
- `Ctrl+I` - Open Agent/Composer (won't work with Qwen)
- `@Codebase` - Codebase search
- `Ctrl+Shift+P` - Command palette

## Best Practices Summary

1. ✅ **Be specific** - Include file paths and function names
2. ✅ **Iterate** - Break complex tasks into multiple queries
3. ✅ **Use context** - Select code before asking
4. ✅ **Copy-paste** - Manually apply fixes
5. ✅ **Verify** - Always follow up to ensure correctness
6. ✅ **Choose right model** - 7B for speed, 32B for depth

## Quick Links to Full Docs

- **Setup:** `docs/CURSOR_QWEN_SETUP.md`
- **Limitations:** `docs/CURSOR_AGENT_MODE_LIMITATIONS.md`
- **Workflow:** `docs/CURSOR_QWEN_WORKFLOW.md`
- **Continue:** `docs/CURSOR_CONTINUE_EXTENSION.md`

## Emergency Troubleshooting

### Qwen Completely Not Working

1. Check Ollama: `ollama list`
2. Restart Ollama: `Stop-Service ollama` then `Start-Service ollama`
3. Restart Cursor completely
4. Verify model: `ollama pull qwen2.5-coder:32b`
5. Test Ollama API: `curl http://localhost:11434/api/tags`

### Slow Performance

1. Switch to 7B model
2. Narrow query scope
3. Check system resources
4. Ensure GPU is being used (if available)

### Poor Quality Answers

1. Be more specific in queries
2. Include file paths
3. Use 32B model instead of 7B
4. Break into smaller, focused queries

---

**Remember:** Agent/Composer mode (Ctrl+I) doesn't work with local models. Use Chat + @Codebase for analysis, then copy-paste fixes or use Continue extension for auto-editing.
