# Run test script and capture output
$ErrorActionPreference = "Continue"
$storiPath = "data\uploads\36d55f24-1a00-41f3-8467-015e11216c91__Storiinvoiceonly1.pdf"

Write-Host "Running Stori invoice test..."
Write-Host "Path: $storiPath"
Write-Host ""

python backend/scripts/test_invoice_validation.py $storiPath

Write-Host ""
Write-Host "Test completed with exit code: $LASTEXITCODE"
