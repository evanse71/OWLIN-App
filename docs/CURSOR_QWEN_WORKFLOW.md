# Cursor + Qwen Workflow Guide

## Overview

This guide provides best practices, recommended query patterns, and workflow strategies for using Qwen with Cursor's Codebase Search feature effectively.

## Core Workflow: Analysis → Understand → Fix

Since Agent/Composer mode doesn't work with local models, use this three-step workflow:

1. **Analysis** - Use @Codebase to find issues and understand code
2. **Understand** - Get detailed explanations and fix suggestions
3. **Fix** - Manually apply the fixes (copy-paste workflow)

## Best Practices

### 1. Start Broad, Then Narrow

**Bad:**
```
@Codebase fix the bug
```

**Good:**
```
@Codebase Find potential null pointer exceptions in the authentication module
```

**Better:**
```
@Codebase Review backend/routes/auth.py and backend/services/auth_service.py for null pointer exceptions and suggest fixes
```

### 2. Be Specific About What You Want

**Bad:**
```
@Codebase improve this code
```

**Good:**
```
@Codebase Review backend/services/chat_service.py and suggest improvements for:
1. Error handling in the _call_ollama method
2. Retry logic optimization
3. Memory usage in context building
```

### 3. Use File Paths and Function Names

**Bad:**
```
@Codebase how does pairing work?
```

**Good:**
```
@Codebase Explain how the pairing system works, focusing on:
- backend/services/pairing_service.py
- backend/matching/pairing.py
- The match_engine function
```

### 4. Ask for Code Examples

**Bad:**
```
@Codebase fix memory leaks
```

**Good:**
```
@Codebase Find memory leaks in the backend and provide complete code examples showing:
1. The problematic code
2. The fixed code
3. Explanation of why the fix works
```

### 5. Iterative Refinement

Don't try to solve everything in one query. Break it down:

**Query 1:**
```
@Codebase Find all places where database connections might not be closed properly
```

**Query 2 (after reviewing results):**
```
@Codebase Show me the specific code in backend/app/db.py that needs connection cleanup and provide the fix
```

**Query 3:**
```
@Codebase Are there any other files that use the same pattern and need the same fix?
```

## Recommended Query Patterns

### Pattern 1: Bug Hunting

**Structure:**
```
@Codebase Find [type of bug] in [module/area] and [action]
```

**Examples:**
```
@Codebase Find potential race conditions in the invoice processing module and explain why they're problematic
```

```
@Codebase Find memory leaks in backend/services/ and provide code fixes
```

```
@Codebase Find SQL injection vulnerabilities in database query code
```

### Pattern 2: Code Understanding

**Structure:**
```
@Codebase Explain how [system/feature] works, focusing on [specific aspects]
```

**Examples:**
```
@Codebase Explain how the invoice pairing system works, focusing on the matching algorithm and validation logic
```

```
@Codebase Show me the code flow from invoice upload to database storage
```

```
@Codebase How does the LLM extraction pipeline process invoices? Show the main components
```

### Pattern 3: Refactoring Suggestions

**Structure:**
```
@Codebase Review [file/path] and suggest improvements for [specific areas]
```

**Examples:**
```
@Codebase Review backend/services/chat_service.py and suggest improvements for error handling and retry logic
```

```
@Codebase Analyze backend/ocr/ocr_processor.py for code duplication and suggest refactoring
```

```
@Codebase Review the database connection handling and suggest improvements for connection pooling
```

### Pattern 4: Architecture Analysis

**Structure:**
```
@Codebase Analyze [system] architecture and identify [concerns/improvements]
```

**Examples:**
```
@Codebase Analyze the backend API architecture and identify potential bottlenecks
```

```
@Codebase Review the separation of concerns between routes, services, and models
```

```
@Codebase Identify circular dependencies in the backend codebase
```

### Pattern 5: Security Review

**Structure:**
```
@Codebase Find [security issue type] in [area] and provide secure alternatives
```

**Examples:**
```
@Codebase Find hardcoded credentials or API keys in the codebase
```

```
@Codebase Review authentication and authorization logic for security vulnerabilities
```

```
@Codebase Check for improper input validation in API endpoints
```

## Copy-Paste Workflow

Since Agent mode doesn't work, here's the efficient copy-paste workflow:

### Step 1: Get the Analysis

```
@Codebase Find and fix the memory leak in backend/services/chat_service.py
```

### Step 2: Review Qwen's Response

Qwen will provide:
- Location of the issue
- Explanation of the problem
- Code showing the fix
- Why the fix works

### Step 3: Apply the Fix

1. Open the file mentioned in Qwen's response
2. Navigate to the problematic code
3. Copy the fixed code from Qwen's response
4. Replace the old code
5. Review the changes
6. Test the fix

### Step 4: Verify

Ask a follow-up question:
```
@Codebase Verify that the fix I just applied to chat_service.py is correct and won't cause other issues
```

## Context Optimization Tips

### 1. Select Files Before Asking

1. Open the file(s) you want to analyze
2. Select relevant code sections
3. Then ask your question - Cursor will include the selected code in context

### 2. Use Multiple @Codebase Queries

Instead of one massive query, break it into focused queries:

**Query 1:** Find the issue
**Query 2:** Understand the root cause
**Query 3:** Get the specific fix
**Query 4:** Check for similar issues elsewhere

### 3. Reference Previous Answers

In follow-up queries, reference what Qwen found earlier:

```
@Codebase You mentioned a memory leak in chat_service.py. Show me the exact code that needs to be fixed with the complete solution
```

### 4. Combine @Codebase with File Selection

1. Select a function or class in your editor
2. Use @Codebase to ask about it
3. Cursor will include the selected code + codebase context

## Advanced Techniques

### Technique 1: Comparative Analysis

```
@Codebase Compare the error handling in backend/routes/invoices_submit.py with backend/routes/audit_export.py and suggest which approach is better
```

### Technique 2: Pattern Detection

```
@Codebase Find all places in the codebase that use the same anti-pattern as the code in backend/services/ocr_service.py line 45-60
```

### Technique 3: Dependency Analysis

```
@Codebase Show me all files that depend on backend/models/invoices.py and explain the dependency chain
```

### Technique 4: Performance Analysis

```
@Codebase Identify performance bottlenecks in the invoice processing pipeline and suggest optimizations
```

## Model Selection Strategy

### Use 7B Model For:
- Quick questions
- Simple code explanations
- Fast iterations
- When speed matters more than depth

### Use 32B Model For:
- Complex architectural questions
- Deep code analysis
- Multi-file refactoring suggestions
- When quality matters more than speed

## Common Workflows

### Workflow 1: Debugging a Bug

1. **Identify the problem:**
   ```
   @Codebase Find the cause of [error message] in [file/area]
   ```

2. **Understand the root cause:**
   ```
   @Codebase Explain why [the issue] happens and what triggers it
   ```

3. **Get the fix:**
   ```
   @Codebase Provide a complete fix for [the issue] with code examples
   ```

4. **Verify:**
   ```
   @Codebase Check if this fix could cause issues elsewhere in the codebase
   ```

### Workflow 2: Adding a New Feature

1. **Understand existing patterns:**
   ```
   @Codebase Show me how similar features are implemented, like [existing feature]
   ```

2. **Find integration points:**
   ```
   @Codebase Where should I add [new feature] and what files need to be modified?
   ```

3. **Get implementation guidance:**
   ```
   @Codebase Provide code examples for implementing [new feature] following the existing patterns
   ```

4. **Review:**
   ```
   @Codebase Review my implementation of [feature] and suggest improvements
   ```

### Workflow 3: Code Review

1. **Select the code** you want reviewed

2. **Ask for review:**
   ```
   @Codebase Review this code for:
   - Code quality issues
   - Potential bugs
   - Performance problems
   - Security concerns
   - Best practices violations
   ```

3. **Get specific suggestions:**
   ```
   @Codebase Provide specific code improvements for the issues you found
   ```

## Troubleshooting Workflow Issues

### Problem: Qwen gives generic answers

**Solution:** Be more specific, include file paths, function names, or code snippets

### Problem: Too much context, slow responses

**Solution:** Narrow your query, focus on specific files or functions

### Problem: Qwen misses relevant files

**Solution:** 
- Ensure codebase is indexed
- Be more explicit about file paths
- Use multiple focused queries instead of one broad query

### Problem: Fix doesn't work

**Solution:**
- Ask Qwen to verify the fix: `@Codebase Verify this fix is correct...`
- Provide error messages: `@Codebase This fix causes [error], what's wrong?`
- Get alternative solutions: `@Codebase Provide an alternative fix for...`

## Summary

1. **Be specific** - Include file paths, function names, and clear objectives
2. **Iterate** - Break complex tasks into multiple focused queries
3. **Use context** - Select code before asking questions
4. **Copy-paste** - Manually apply fixes since Agent mode doesn't work
5. **Verify** - Always follow up to ensure fixes are correct
6. **Choose the right model** - 7B for speed, 32B for depth

## Related Documentation

- `CURSOR_QWEN_SETUP.md` - Initial setup instructions
- `CURSOR_AGENT_MODE_LIMITATIONS.md` - Understanding what doesn't work
- `CURSOR_CONTINUE_EXTENSION.md` - Alternative for agent capabilities
- `CURSOR_QWEN_QUICK_REF.md` - Quick reference card
