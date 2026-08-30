# ============================================================
#  Angel — PowerShell launcher (richer output than the .bat)
#  Usage:  .\run_angel.ps1        (from the project folder)
# ============================================================
$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

function Fail($msg) {
    Write-Host "`n[Angel] $msg" -ForegroundColor Red
    Read-Host "Press Enter to close"
    exit 1
}

# ---- Python present and modern enough -------------------------------------
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    Fail "Python not found. Install 3.11/3.12 from https://www.python.org/downloads/ (check 'Add to PATH')."
}
$version = & python -c "import sys; print(f'{sys.version_info[0]}.{sys.version_info[1]}')"
if ([version]$version -lt [version]"3.10") {
    Fail "Python $version is too old — Angel needs 3.10+ (3.11/3.12 recommended)."
}

# ---- Virtual environment ---------------------------------------------------
if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "[Angel] First run - creating virtual environment..." -ForegroundColor DarkYellow
    python -m venv .venv
    Write-Host "[Angel] Installing dependencies (a few minutes the first time)..." -ForegroundColor DarkYellow
    & .venv\Scripts\python.exe -m pip install --upgrade pip
    & .venv\Scripts\python.exe -m pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) { Fail "Dependency installation failed - see output above." }
}

# ---- .env ------------------------------------------------------------------
if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "[Angel] Created .env - open it and add OPENROUTER_API_KEY and FISH_API_KEY." -ForegroundColor DarkYellow
}

# ---- Launch ----------------------------------------------------------------
Write-Host "[Angel] Awakening..." -ForegroundColor DarkGray
& .venv\Scripts\python.exe app.py
if ($LASTEXITCODE -ne 0) { Read-Host "Angel exited with an error - press Enter to close" }
