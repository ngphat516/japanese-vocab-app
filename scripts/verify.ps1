param([string]$UvExecutable = 'uv')
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
& (Join-Path $projectRoot 'apps/backend/scripts/verify.ps1') -UvExecutable $UvExecutable
