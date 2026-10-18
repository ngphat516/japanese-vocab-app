param([string]$UvExecutable = 'uv')
$ErrorActionPreference = 'Stop'
function Invoke-Checked {
    param([string]$Executable, [string[]]$Arguments, [string]$Log)
    $previousPreference = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    & $Executable @Arguments *> $Log
    $nativeExitCode = $LASTEXITCODE
    $ErrorActionPreference = $previousPreference
    if ($nativeExitCode -ne 0) { throw "$Executable failed (exit $nativeExitCode). See $Log" }
}
$projectRoot = Split-Path -Parent $PSScriptRoot
Push-Location $projectRoot
try {
    New-Item -ItemType Directory -Force -Path 'verification' | Out-Null
    Invoke-Checked -Executable docker -Arguments @('version') -Log verification/docker.log
    Invoke-Checked -Executable $UvExecutable -Arguments @('sync', '--frozen') -Log verification/sync.log
    Invoke-Checked -Executable $UvExecutable -Arguments @('run', 'ruff', 'check', '.', '../../scripts') -Log verification/ruff.log
    Invoke-Checked -Executable $UvExecutable -Arguments @('run', 'ruff', 'format', '--check', '.', '../../scripts') -Log verification/format.log
    Invoke-Checked -Executable $UvExecutable -Arguments @('run', 'pytest', '--cov', '--cov-report=term-missing', '--cov-report=json', '--junitxml=verification/pytest.xml') -Log verification/pytest.log
    Invoke-Checked -Executable $UvExecutable -Arguments @('run', 'python', 'scripts/check_coverage.py', 'coverage.json') -Log verification/coverage.log
    Write-Output 'PASS: pytest, coverage, Ruff. Logs: verification/'
} finally {
    Pop-Location
}
