@echo off
echo ================================================================
echo   Activating LLM-First Invoice Extraction
echo ================================================================
echo.

echo [Step 1] Running LLM diagnostics...
python check_llm.py
if errorlevel 1 (
    echo.
    echo [ERROR] LLM diagnostics failed!
    echo Please fix the issues above before continuing.
    pause
    exit /b 1
)

echo.
echo [Step 2] LLM extraction is now ENABLED by default in config.py
echo          FEATURE_LLM_EXTRACTION = True
echo.

echo [Step 3] Clearing OCR cache...
if exist clear_ocr_cache.py (
    python clear_ocr_cache.py --all
) else (
    echo No cache clear script found, skipping...
)

echo.
echo ================================================================
echo   LLM Extraction is Ready!
echo ================================================================
echo.
echo Next step: Restart your backend
echo   - Run: start_backend_5176.bat
echo   - Or restart your existing backend terminal
echo.
echo Then upload an invoice and watch "Unknown Item" disappear!
echo.
pause

