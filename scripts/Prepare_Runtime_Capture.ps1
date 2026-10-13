param([string]$Capture, [switch]$AnalyzeLatest)
# Preview-only setup, or explicit offline analysis of a supplied capture. Never launches RE9.
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$projectPython = Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
if (-not (Test-Path -LiteralPath $projectPython -PathType Leaf)) {
    throw 'Bundled Python missing. No dependencies or game files were installed.'
}
Push-Location -LiteralPath $projectRoot
try {
    if ($AnalyzeLatest) {
        & $projectPython (Join-Path $PSScriptRoot 'runtime_collect.py')
    } elseif ($Capture) {
        $resolvedCapture = (Resolve-Path -LiteralPath $Capture).Path
        $stamp = Get-Date -Format 'yyyyMMddTHHmmssfff'
        & $projectPython (Join-Path $PSScriptRoot 'runtime_capture.py') $resolvedCapture --output "reports/runtime_preparation_v0.2.0/captures/capture_$stamp.json"
    } else {
        & $projectPython (Join-Path $PSScriptRoot 'runtime_preflight.py')
    }
    if ($LASTEXITCODE -ne 0) { throw 'Offline check failed. Review its diagnostic; no installation was attempted.' }
} finally { Pop-Location }

