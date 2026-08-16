# Environment doctor for vitae — Windows.
# Baseline: Windows 11+ up to date (winget preinstalled, PowerShell 5.1+).
# Read-only by default: diagnoses and PRINTS install commands, never runs them.
# Opt-in `-Install` fetches only the typst binary into %USERPROFILE%\.local\bin.
# If Windows refuses to run this ("running scripts is disabled"), run:
#   Unblock-File .\check_env.ps1
#   powershell -ExecutionPolicy Bypass -File .\check_env.ps1
param([switch]$Install)

$missing = 0
function Have($cmd) { return [bool](Get-Command $cmd -ErrorAction SilentlyContinue) }

if (Have "typst") {
    Write-Host "OK  typst $((typst --version) -replace 'typst ','')"
} else {
    $missing = 1
    Write-Host "MISSING  typst — install with ONE of:"
    Write-Host "  winget install --id Typst.Typst               # recommended (preinstalled on Win11)"
    Write-Host "  choco install typst | scoop install typst      # if you already use them"
    Write-Host "  cargo install typst-cli"
    Write-Host "  pip install typst             # no CLI: compiles via Python API, see references/ats.md"
    Write-Host "  .\check_env.ps1 -Install      # no-admin: binary -> ~\.local\bin"
}

if ((Have "pdftotext") -and (Have "pdfinfo")) {
    Write-Host "OK  poppler-utils (pdftotext, pdfinfo)"
} else {
    $missing = 1
    Write-Host "MISSING  poppler — needed for page-count and ATS extraction checks:"
    Write-Host "  choco install poppler | scoop install poppler"
    Write-Host "  (fallback without poppler: see references/ats.md — pypdf)"
}

$pil = $false
if (Have "python") { python -c "import PIL" 2>$null; if ($LASTEXITCODE -eq 0) { $pil = $true } }
elseif (Have "py") { py -c "import PIL" 2>$null; if ($LASTEXITCODE -eq 0) { $pil = $true } }
if ($pil) {
    Write-Host "OK  Pillow (measure_fill.py)"
} else {
    $missing = 1
    Write-Host "MISSING  Pillow — needed for the page-fill measurement:"
    Write-Host "  pip install Pillow    (or: uv pip install Pillow)"
}

if ($Install -and -not (Have "typst")) {
    $ErrorActionPreference = "Stop"   # fail cleanly instead of cascading
    # Real release assets: x86_64- and aarch64-pc-windows-msvc (no i686 build).
    # NOTE: HTTPS from official typst releases, no checksum verification —
    # prefer winget if that matters. URL shape may rot if typst renames targets.
    $arch = if ($env:PROCESSOR_ARCHITECTURE -eq "ARM64") { "aarch64" } else { "x86_64" }
    $url = "https://github.com/typst/typst/releases/latest/download/typst-$arch-pc-windows-msvc.zip"
    # .NET APIs instead of raw env vars: never null, portable
    $dest = Join-Path ([Environment]::GetFolderPath("UserProfile")) ".local/bin"
    New-Item -ItemType Directory -Force -Path $dest | Out-Null
    $tmp = Join-Path ([IO.Path]::GetTempPath()) "typst_dl"
    New-Item -ItemType Directory -Force -Path $tmp | Out-Null
    Write-Host "Downloading $url"
    Invoke-WebRequest -Uri $url -OutFile (Join-Path $tmp "typst.zip")
    Expand-Archive -Path (Join-Path $tmp "typst.zip") -DestinationPath $tmp -Force
    Get-ChildItem -Path $tmp -Recurse -Filter "typst.exe" | Select-Object -First 1 |
        ForEach-Object { Move-Item $_.FullName (Join-Path $dest "typst.exe") -Force }
    Remove-Item -Recurse -Force $tmp
    Write-Host "Installed to $(Join-Path $dest typst.exe) — add $dest to your PATH if needed:"
    Write-Host "  [Environment]::SetEnvironmentVariable('Path', `$env:Path + ';$dest', 'User')"
    $missing = 0
}

Write-Host "Environment check done."
exit $missing
