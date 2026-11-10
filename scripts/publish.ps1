param(
    [string]$Token
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$dist = Join-Path $root "dist"
if (-not (Test-Path $dist) -or -not (Get-ChildItem $dist -File -ErrorAction SilentlyContinue)) {
    throw "No distributions in $dist. Run: python -m build"
}

if (-not $Token) {
    $secure = Read-Host -AsSecureString "PyPI API token (pypi-...)"
    $ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
    try {
        $Token = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr)
    }
    finally {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr)
    }
}

if (-not $Token.StartsWith("pypi-")) {
    throw "That does not look like a PyPI API token."
}

$env:TWINE_USERNAME = "__token__"
$env:TWINE_PASSWORD = $Token
try {
    python -m twine upload --repository pypi "$dist\*"
}
finally {
    Remove-Item Env:\TWINE_PASSWORD -ErrorAction SilentlyContinue
    Remove-Item Env:\TWINE_USERNAME -ErrorAction SilentlyContinue
}
