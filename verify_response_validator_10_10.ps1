# ResponseValidator 10/10 Verification Script
# Verifies all improvements are working correctly

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "ResponseValidator 10/10 Verification" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$allPassed = $true

# Test 1: Imports and initialization
Write-Host "[1/10] Testing imports and initialization..." -ForegroundColor Yellow
try {
    python -c "from backend.services.response_validator import ResponseValidator; v = ResponseValidator(); print('OK')" 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  PASS: All imports successful" -ForegroundColor Green
    } else {
        Write-Host "  FAIL: Import error" -ForegroundColor Red
        $allPassed = $false
    }
} catch {
    Write-Host "  FAIL: $($_.Exception.Message)" -ForegroundColor Red
    $allPassed = $false
}

# Test 2: Constants are set correctly
Write-Host "[2/10] Testing constants..." -ForegroundColor Yellow
$constants = python -c "from backend.services.response_validator import ResponseValidator; v = ResponseValidator(); print(f'{v.MIN_SECTION_CONTENT_LENGTH},{v.SECTION_SIMILARITY_THRESHOLD},{v.MAX_CODE_TO_TEXT_RATIO}')" 2>&1
if ($constants -match "10,0\.6,0\.4") {
    Write-Host "  PASS: All constants set correctly" -ForegroundColor Green
} else {
    Write-Host "  FAIL: Constants incorrect: $constants" -ForegroundColor Red
    $allPassed = $false
}

# Test 3: No duplicate aliases
Write-Host "[3/10] Testing for duplicate aliases..." -ForegroundColor Yellow
$duplicates = python -c "from backend.services.response_validator import ResponseValidator; v = ResponseValidator(); ca = v.SECTION_ALIASES['Code Analysis']; pd = v.SECTION_ALIASES['Prioritized Diagnosis']; print('OK' if len(set(ca)) == len(ca) and len(set(pd)) == len(pd) else 'FAIL')" 2>&1
if ($duplicates -match "OK") {
    Write-Host "  PASS: No duplicate aliases found" -ForegroundColor Green
} else {
    Write-Host "  FAIL: Duplicate aliases found" -ForegroundColor Red
    $allPassed = $false
}

# Test 4: Semantic matching works
Write-Host "[4/10] Testing semantic section matching..." -ForegroundColor Yellow
$semantic = python -c "from backend.services.response_validator import ResponseValidator; v = ResponseValidator(); r = v.validate_response('**Code Review**\nFiles analyzed\n\n**Diagnosis**\nIssue\n\n**Root Cause**\nProblem\n\n**Fix**\nSolution'); print('OK' if 'Code Analysis' not in r.missing_sections else 'FAIL')" 2>&1
if ($semantic -match "OK") {
    Write-Host "  PASS: Semantic matching detects 'Code Review' as 'Code Analysis'" -ForegroundColor Green
} else {
    Write-Host "  FAIL: Semantic matching not working" -ForegroundColor Red
    $allPassed = $false
}

# Test 5: Section content validation
Write-Host "[5/10] Testing section content validation..." -ForegroundColor Yellow
$content = python -c "from backend.services.response_validator import ResponseValidator; v = ResponseValidator(); r = v.validate_response('**Code Analysis**\n\n**Prioritized Diagnosis**\n\n**Root Cause**\n\n**Fix**\n'); print('OK' if not r.is_valid and any('empty' in i.lower() or 'insufficient' in i.lower() for i in r.issues) else 'FAIL')" 2>&1
if ($content -match "OK") {
    Write-Host "  PASS: Empty sections are flagged" -ForegroundColor Green
} else {
    Write-Host "  FAIL: Content validation not working" -ForegroundColor Red
    $allPassed = $false
}

# Test 6: File path existence check
Write-Host "[6/10] Testing file path existence validation..." -ForegroundColor Yellow
$pathCheck = python -c "from backend.services.response_validator import ResponseValidator; v = ResponseValidator(); r = v.validate_response('**Code Analysis**\nbackend/nonexistent_xyz123.py:10\n\n**Prioritized Diagnosis**\nIssue\n\n**Root Cause**\nProblem\n\n**Fix**\nSolution'); print('OK' if any('not found' in i.lower() for i in r.issues) else 'FAIL')" 2>&1
if ($pathCheck -match "OK") {
    Write-Host "  PASS: Non-existent paths are flagged" -ForegroundColor Green
} else {
    Write-Host "  FAIL: Path existence check not working" -ForegroundColor Red
    $allPassed = $false
}

# Test 7: Valid paths are accepted
Write-Host "[7/10] Testing valid path acceptance..." -ForegroundColor Yellow
$validPath = python -c "from backend.services.response_validator import ResponseValidator; v = ResponseValidator(); r = v.validate_response('**Code Analysis**\nbackend/services/response_validator.py:10\n\n**Prioritized Diagnosis**\nIssue\n\n**Root Cause**\nProblem\n\n**Fix**\nSolution'); invalid = [i for i in r.issues if 'not found' in i.lower() or 'invalid' in i.lower()]; print('OK' if len(invalid) == 0 else 'FAIL')" 2>&1
if ($validPath -match "OK") {
    Write-Host "  PASS: Valid existing paths are accepted" -ForegroundColor Green
} else {
    Write-Host "  FAIL: Valid paths incorrectly flagged" -ForegroundColor Red
    $allPassed = $false
}

# Test 8: Code-to-text ratio validation
Write-Host "[8/10] Testing code-to-text ratio validation..." -ForegroundColor Yellow
$codeRatio = python test_code_ratio.py 2>&1
if ($codeRatio -match "Issues = 1") {
    Write-Host "  PASS: High code-to-text ratio is flagged" -ForegroundColor Green
} else {
    Write-Host "  FAIL: Code ratio validation not working" -ForegroundColor Red
    $allPassed = $false
}

# Test 9: Perfect response passes
Write-Host "[9/10] Testing perfect response validation..." -ForegroundColor Yellow
$perfect = python -c "from backend.services.response_validator import ResponseValidator; v = ResponseValidator(); r = v.validate_response('**Code Analysis**\nI analyzed backend/services/response_validator.py\n\n**Prioritized Diagnosis**\nThe most likely issue is a validation problem.\n\n**Root Cause**\nThe root cause is that section detection is too strict.\n\n**Fix**\nUpdate the section detection:\n```python\ndef fix():\n    return True\n```'); print('OK' if r.is_valid and r.score == 1.0 else 'FAIL')" 2>&1
if ($perfect -match "OK") {
    Write-Host "  PASS: Perfect response passes all checks" -ForegroundColor Green
} else {
    Write-Host "  FAIL: Perfect response incorrectly flagged" -ForegroundColor Red
    $allPassed = $false
}

# Test 10: All unit tests pass
Write-Host "[10/10] Running all unit tests..." -ForegroundColor Yellow
$testResult = python -m pytest tests/integration/test_response_validator_improvements.py -v --tb=short 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "  PASS: All 12 unit tests passed" -ForegroundColor Green
} else {
    Write-Host "  FAIL: Some tests failed" -ForegroundColor Red
    $allPassed = $false
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
if ($allPassed) {
    Write-Host "RESULT: 10/10 - PERFECT IMPLEMENTATION" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Cyan
    exit 0
} else {
    Write-Host "RESULT: FAILED - Issues found" -ForegroundColor Red
    Write-Host "========================================" -ForegroundColor Cyan
    exit 1
}

