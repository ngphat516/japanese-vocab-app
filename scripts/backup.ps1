param([string]$OutputDirectory = './backups')
$ErrorActionPreference = 'Stop'
New-Item -ItemType Directory -Force -Path $OutputDirectory | Out-Null
$backupName = 'vocab-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.dump'
docker compose exec -T db pg_dump -U vocab -d vocab -Fc -f /tmp/vocab-backup.dump
if ($LASTEXITCODE -ne 0) { throw 'pg_dump failed' }
docker compose cp db:/tmp/vocab-backup.dump (Join-Path $OutputDirectory $backupName)
if ($LASTEXITCODE -ne 0) { throw 'Backup copy failed' }
