$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
Write-Host 'AEGIS Enterprise - real Gmail delivery is available only to approved cases.' -ForegroundColor Cyan
try {
    $secure = Read-Host 'Create/enter your local AEGIS administrator password (hidden)' -AsSecureString
    $ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
    try { $env:AEGIS_ADMIN_PASSWORD = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr) }
    finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr) }
    if ($env:AEGIS_ADMIN_PASSWORD.Length -lt 8) { throw 'Please use an administrator password of at least 8 characters.' }
    $env:AEGIS_ENTERPRISE_MODE = '1'
    & "$PSScriptRoot\RUN_LOCAL.bat"
}
finally {
    Remove-Item Env:AEGIS_ADMIN_PASSWORD -ErrorAction SilentlyContinue
    Remove-Item Env:AEGIS_ENTERPRISE_MODE -ErrorAction SilentlyContinue
}
