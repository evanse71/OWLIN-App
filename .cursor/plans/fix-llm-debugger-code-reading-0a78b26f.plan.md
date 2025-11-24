<!-- 0a78b26f-b45a-49cd-8bfb-40ac8a6e054e 407d12fa-4879-401e-9db8-9d8d73bf7808 -->
# Force LLM to Analyze Actual Code Instead of Generic Responses

## Problem

The LLM shows code files but gives generic troubleshooting advice instead of analyzing the actual code. It's not following the "MUST analyze code" instructions.

## Solution

Restructure the prompt to require a mandatory structured analysis format with step-by-step reasoning, add examples of good vs bad responses, and improve code context presentation.

## Implementation

### 1. Add Mandatory Structured Response Format

**File**: `backend/services/chat_service.py` (around line 457-506)

Replace the debugging system prompt with a format that REQUIRES structured analysis:

- Add a "RESPONSE FORMAT" section that mandates:
  - Step 1: "Files Analyzed" - list specific files with line ranges
  - Step 2: "Data Flow Trace" - trace the exact path through the code
  - Step 3: "Code Analysis" - quote specific code lines with issues
  - Step 4: "Root Cause" - identify exact problem with file:line references
  - Step 5: "Fix" - provide exact code changes with before/after

- Add explicit instruction: "Your response MUST follow this exact format. Do not skip steps."

### 2. Add Examples of Good vs Bad Responses

**File**: `backend/services/chat_service.py` (after system prompt)

Add a section showing:

- BAD EXAMPLE: Generic troubleshooting list
- GOOD EXAMPLE: Specific code analysis with file:line references

This teaches the LLM what we expect.

### 3. Improve Code Context Presentation

**File**: `backend/services/chat_service.py` (around line 567-576)

Enhance code snippet formatting:

- Add line numbers to code blocks (format: `1: code here`)
- Group related code sections together
- Add file path headers with line ranges: `File: path/to/file.ts (lines 217-263)`
- Highlight key functions/endpoints mentioned in the question

### 4. Add Chain-of-Thought Requirement

**File**: `backend/services/chat_service.py` (in debugging prompt)

Add instruction: "Show your reasoning step-by-step. For each file you analyze, explain:

- What this code does
- How it relates to the problem
- What you found (or didn't find) that's relevant"

### 5. Add Response Validation Instructions

**File**: `backend/services/chat_service.py` (in debugging prompt)

Add: "Before submitting your response, verify:

- Did I quote actual code lines? (If no, add them)
- Did I provide file paths and line numbers? (If no, add them)
- Did I trace the data flow through actual code? (If no, do it)
- Am I giving generic advice? (If yes, replace with code-specific analysis)"

### 6. Enhance Post-Prompt Instructions

**File**: `backend/services/chat_service.py` (around line 602-607)

Strengthen the post-code-context instructions:

- Change from suggestions to requirements
- Add: "You MUST start with 'Analyzing the following files:' and list them"
- Add: "You MUST quote at least 3 specific code lines from different files"
- Add: "You MUST show the data transformation at each step"

### 7. Add Code Flow Diagram Requirement

**File**: `backend/services/chat_service.py` (in debugging prompt)

For complex questions, require a text-based flow diagram showing:

```
Upload → [file.py:494] → Status Check → [file.ts:224] → Normalize → [file.ts:59] → Display
```

This forces the LLM to map the actual code path.

## Files to Modify

1. `backend/services/chat_service.py`

   - Lines 457-506: Replace debugging system prompt
   - Lines 567-576: Enhance code snippet formatting
   - Lines 596-607: Strengthen post-code-context instructions

## Expected Outcome

When user asks: "upload was successful but contents aren't showing"

The LLM will respond with:

1. "Analyzing: frontend_clean/src/lib/upload.ts (lines 217-263), backend/main.py (lines 630-723)..."
2. "Data Flow: Upload endpoint (main.py:494) returns {status: 'processing'} → Frontend polls (upload.ts:224) → Status endpoint (main.py:630) returns {items: [...]} → Normalize (upload.ts:240) merges response..."
3. "Issue Found: In upload.ts:236, the condition `hasData || hasItems` may fail if status is 'ready' but parsed is null..."
4. "Fix: Update line 236 to also check `statusData.status === 'ready'`..."

Instead of generic troubleshooting steps.

### To-dos

- [ ] Add question classification system to detect question types (debugging, how-to, what-is, flow, comparison)
- [ ] Fix fallback response to actually read and display files instead of generic messages
- [ ] Add smart file path resolution in code_reader.py (try direct path, then search by name)
- [ ] Improve error log integration to automatically include relevant code when debugging errors
- [ ] Enhance code search functionality with better matching and more context
- [ ] Add logging and error handling improvements throughout the code reading system
- [ ] Replace debugging system prompt with mandatory structured response format (5 required steps)
- [ ] Add examples section showing good vs bad responses
- [ ] Enhance code snippet formatting with line numbers and file headers
- [ ] Add chain-of-thought requirement to show reasoning for each file
- [ ] Add response validation checklist instructions
- [ ] Strengthen post-code-context instructions from suggestions to requirements
- [ ] Add code flow diagram requirement for complex questions