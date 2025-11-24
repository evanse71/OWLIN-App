# Owlin Dev Debug Assistant

## Overview

The **Dev Debug Assistant** is an offline-first debugging tool integrated into Owlin that helps developers find and fix code quality issues without consuming Cursor credits. It scans your codebase locally, identifies issues, and generates AI-powered explanations with ready-to-copy Cursor prompts.

## 🎯 Key Features

- **Offline Code Quality Checks**: Runs local linting and type-checking tools
- **AI-Powered Explanations**: Uses Ollama (if available) or deterministic templates
- **Structured Issue Detection**: Parses errors from multiple tools into a unified format
- **Cursor-Ready Prompts**: Generates copy-paste prompts for quick fixes
- **No External APIs**: Fully offline, deterministic, and credit-free

## 🏗️ Architecture

### Backend Components

```
backend/
├── devtools/
│   ├── __init__.py          # Module initialization
│   ├── models.py            # Pydantic models for issues and explanations
│   ├── runner.py            # Executes local linting/testing tools
│   └── llm_explainer.py     # Generates explanations (Ollama or templates)
└── routes/
    └── dev_tools.py         # FastAPI endpoints
```

### Frontend Components

```
frontend_clean/src/
└── pages/
    └── DevDebug.tsx         # Main debug assistant UI
```

### API Endpoints

1. **`GET /api/dev/run_checks`**
   - Runs all available code quality checks
   - Returns structured list of issues with metadata
   - Response: `RunChecksResponse`

2. **`POST /api/dev/llm/explain`**
   - Generates explanation for a specific issue
   - Accepts issue details and optional code context
   - Returns plain English, technical cause, fix steps, and Cursor prompt
   - Response: `ExplainResponse`

3. **`GET /api/dev/status`**
   - Returns dev tools system status
   - Shows Ollama availability and tool configuration

## 📦 Supported Tools

### Python Backend
- **MyPy**: Static type checking
- **Ruff**: Fast Python linter
- **Pytest**: Test collection (syntax validation)

### TypeScript Frontend
- **tsc**: TypeScript compiler type checking
- **ESLint**: JavaScript/TypeScript linting

## 🚀 Getting Started

### Prerequisites

Install required tools for your development environment:

#### Python Tools (Backend)
```powershell
# Install Python linting and type checking tools
pip install mypy ruff pytest
```

#### TypeScript Tools (Frontend)
```powershell
# Navigate to frontend directory
cd frontend_clean

# Install Node dependencies (includes TypeScript and ESLint)
npm install
```

### Optional: Ollama for AI Explanations

For enhanced AI-powered explanations, install Ollama:

#### Windows
1. Download from: https://ollama.com/download/windows
2. Run the installer
3. Pull the CodeLlama model:
```powershell
ollama pull codellama:7b
```

#### Linux/macOS
```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull the CodeLlama model
ollama pull codellama:7b
```

**Note**: If Ollama is not available, the system automatically falls back to deterministic template-based explanations.

## 🎮 Usage

### Accessing the Debug Assistant

1. **Start the Owlin backend**:
```powershell
cd backend
uvicorn backend.main:app --reload --port 8000
```

2. **Start the frontend** (in development):
```powershell
cd frontend_clean
npm run dev
```

3. **Navigate to the Debug Assistant**:
   - Open your browser to: `http://localhost:5173/dev/debug`
   - Or in production: `http://localhost:8000/dev/debug`

### Workflow

#### Step 1: Run Checks
- Click the **"🔍 Run Checks"** button
- Wait for all tools to complete scanning (typically 10-30 seconds)
- View detected issues in the left panel

#### Step 2: Select an Issue
- Click on any issue in the left panel
- View issue details (file, line, error message)

#### Step 3: Add Code Context (Optional)
- Paste 30-60 lines of code around the error
- Provides better context for AI explanations
- Not required, but improves explanation quality

#### Step 4: Generate Explanation
- Click **"🤖 Generate Explanation & Patch Suggestion"**
- View structured explanation:
  - **Plain English**: Non-technical summary
  - **Technical Cause**: Root cause analysis
  - **Suggested Fix**: Step-by-step instructions
  - **Cursor Prompt**: Ready-to-copy prompt

#### Step 5: Copy and Apply Fix
- Click **"📋 Copy"** on the Cursor Prompt
- Paste into Cursor chat
- Let Cursor apply the fix

## 📊 Understanding the UI

### Stats Bar
Shows issue counts by:
- **Severity**: errors, warnings, info
- **Tool**: mypy, ruff, eslint, tsc, pytest

### Issue List (Left Panel)
- **Severity Icon**: ❌ error, ⚠️ warning, ℹ️ info
- **File Path**: Relative path from repo root
- **Line:Column**: Exact location
- **Message**: Original error message

### Explanation Panel (Right Panel)
- **Selected Issue**: Full details of current issue
- **Code Context**: Input field for surrounding code
- **Explanation Sections**: Color-coded cards
  - 📖 Blue: Plain English
  - 🔧 Purple: Technical Cause
  - ✅ Green: Suggested Fix
  - 🎯 Orange: Cursor Prompt

## 🔧 Configuration

### Environment Variables

```bash
# Optional: Custom Ollama URL (default: http://localhost:11434)
export OLLAMA_URL="http://localhost:11434"
```

### Tool-Specific Configuration

#### MyPy Configuration
Create or edit `mypy.ini` in repo root:
```ini
[mypy]
python_version = 3.11
ignore_missing_imports = True
warn_return_any = True
warn_unused_configs = True
```

#### Ruff Configuration
Create or edit `pyproject.toml`:
```toml
[tool.ruff]
line-length = 120
select = ["E", "F", "W", "I"]
ignore = ["E501"]
```

#### ESLint Configuration
Already configured in `frontend_clean/.eslintrc.js` or `package.json`

## 🧪 Testing the Installation

Run this PowerShell script to verify all tools are available:

```powershell
# Test Python tools
Write-Host "Testing Python tools..." -ForegroundColor Cyan
python -c "import mypy; print('✓ MyPy installed')"
python -c "import ruff; print('✓ Ruff installed')"
python -c "import pytest; print('✓ Pytest installed')"

# Test Node tools
Write-Host "`nTesting Node tools..." -ForegroundColor Cyan
cd frontend_clean
npx tsc --version
npx eslint --version

# Test Ollama (optional)
Write-Host "`nTesting Ollama (optional)..." -ForegroundColor Cyan
try {
    $response = Invoke-RestMethod -Uri "http://localhost:11434/api/tags" -ErrorAction Stop
    Write-Host "✓ Ollama is running" -ForegroundColor Green
} catch {
    Write-Host "✗ Ollama not running (will use template fallback)" -ForegroundColor Yellow
}

Write-Host "`nDev Debug Assistant ready!" -ForegroundColor Green
```

## 🎓 Example Workflow

### Scenario: Fix a Type Error

1. **Run Checks** → Finds MyPy error: `Incompatible types in assignment`
2. **Select Issue** → See error in `backend/services/ocr_service.py:42`
3. **Add Context** → Paste function containing the error
4. **Generate Explanation** → Receives:
   - **Plain English**: "You're trying to assign a text value to a variable that expects a number"
   - **Technical**: "Type mismatch at line 42"
   - **Fix**: "Change assignment to use correct type"
   - **Cursor Prompt**: "Fix type error at line 42 in backend/services/ocr_service.py"
5. **Copy Prompt** → Paste in Cursor → Issue fixed!

## 🎯 Best Practices

### For Best Results
1. **Provide Code Context**: Paste surrounding code for better explanations
2. **Run Checks Regularly**: Catch issues early
3. **Fix Errors First**: Address errors before warnings
4. **Use Cursor Prompts**: They're optimized for Cursor AI

### Troubleshooting

#### No Issues Found But Code Has Errors
- Ensure tools are installed: `pip list | grep -E "mypy|ruff|pytest"`
- Check frontend tools: `cd frontend_clean && npx tsc --version`
- Verify file structure matches expected layout

#### Explanation Generation Fails
- Check if Ollama is running: `curl http://localhost:11434/api/tags`
- System will automatically fall back to templates
- Check backend logs for detailed errors

#### Slow Performance
- First run is slower (tool initialization)
- Subsequent runs are faster
- Consider running checks on specific directories only (future enhancement)

## 🔒 Security and Privacy

- **Fully Offline**: No data leaves your machine
- **No External APIs**: All processing is local
- **No File Modification**: Only reads files, never writes
- **Deterministic**: Template fallbacks ensure consistent results

## 📝 Limitations

- **No Auto-Fix**: Generates suggestions only, doesn't modify code
- **Tool Dependencies**: Requires linting tools to be installed
- **Single File Focus**: Best for file-level issues
- **No Real-Time**: Manual check runs only

## 🚧 Future Enhancements

Potential improvements (not implemented):
- [ ] Auto-apply simple fixes
- [ ] Watch mode for real-time checking
- [ ] Custom rule configuration UI
- [ ] Export reports as CSV/JSON
- [ ] Integration with CI/CD pipelines
- [ ] Support for additional tools (flake8, prettier, etc.)

## 🆘 Support

If you encounter issues:
1. Check tool installation: Run test script above
2. Review backend logs: `backend_stdout.log`
3. Verify API endpoints: `http://localhost:8000/api/dev/status`
4. Check browser console for frontend errors

## 📄 License

This feature is part of the Owlin project and follows the same license.

---

**Built with 🔧 for offline-first development**

