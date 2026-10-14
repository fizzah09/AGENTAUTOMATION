$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
try {
    $secure = Read-Host 'AEGIS admin password (hidden)' -AsSecureString
    $ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
    try { $env:AEGIS_ADMIN_PASSWORD = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr) }
    finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr) }
    if (-not $env:AEGIS_ADMIN_PASSWORD) { throw 'Administrator password must not be empty.' }
    $env:AEGIS_ENTERPRISE_MODE = '1'
    & "$PSScriptRoot\RUN_LOCAL.bat"
}
finally {
    Remove-Item Env:AEGIS_ADMIN_PASSWORD -ErrorAction SilentlyContinue
}
