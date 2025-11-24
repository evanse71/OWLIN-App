Param(
  [string]$Key = $env:OPENAI_API_KEY
)
if (-not $Key) {
  $sec = Read-Host "Enter OPENAI_API_KEY" -AsSecureString
  $Key = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
    [Runtime.InteropServices.Marshal]::SecureStringToBSTR($sec)
  )
}
$env:OPENAI_API_KEY = $Key
python scripts/test_openai_key.py
if ($LASTEXITCODE -ne 0) { Write-Error "Key test failed."; exit 1 }
python scripts/invoke_prompt_and_write_sdk.py
