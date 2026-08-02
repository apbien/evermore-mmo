# Session backup (D-067).
#
# Git carries the source of truth (generators, content/, docs/). The generated
# state — assets/ and review/shots/ — is NOT in git, so this script zips a
# point-in-time copy into backups/ at the start of each session (SessionStart
# hook in .claude/settings.json). backups/ sits inside the OneDrive-synced
# tree, so every zip is also carried off-machine.
#
# Behaviour:
#   - skips if the newest backup is younger than 60 minutes (sessions restart
#     often; identical state does not need a second zip)
#   - keeps the newest 3 zips, deletes older ones
#   - uses tar.exe (bsdtar, ships with Windows 10+) because Compress-Archive
#     in PowerShell 5.1 chokes near the 2 GB mark and review/shots alone is
#     1.8 GB

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$backupDir = Join-Path $root 'backups'
$log = Join-Path $backupDir 'backup.log'

if (-not (Test-Path $backupDir)) { New-Item -ItemType Directory $backupDir | Out-Null }

function Log($msg) {
    $stamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
    Add-Content -Path $log -Value "$stamp  $msg" -Encoding utf8
}

# Skip if a fresh backup already exists
$newest = Get-ChildItem $backupDir -Filter 'evermore-backup-*.zip' -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTime -Descending | Select-Object -First 1
if ($null -ne $newest -and $newest.LastWriteTime -gt (Get-Date).AddMinutes(-60)) {
    Log "skip: $($newest.Name) is under an hour old"
    exit 0
}

# What to back up: everything generated and untracked
$targets = @()
if (Test-Path (Join-Path $root 'assets'))       { $targets += 'assets' }
if (Test-Path (Join-Path $root 'review\shots')) { $targets += 'review/shots' }
if ($targets.Count -eq 0) { Log 'skip: nothing to back up'; exit 0 }

$name = 'evermore-backup-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.zip'
$zip = Join-Path $backupDir $name

# Full path to Windows' bundled bsdtar: a bare `tar` can resolve to Git Bash's
# GNU tar, which reads `C:\...` as a remote host and cannot write zip at all.
$bsdtar = Join-Path $env:SystemRoot 'System32\tar.exe'

Log "start: zipping $($targets -join ', ') -> $name"
Push-Location $root
try {
    & $bsdtar -a -c -f $zip @targets
    if ($LASTEXITCODE -ne 0) { throw "tar.exe exited $LASTEXITCODE" }
} catch {
    Log "FAILED: $_"
    if (Test-Path $zip) { Remove-Item $zip -Force }
    Pop-Location
    exit 1
}
Pop-Location

$size = [math]::Round((Get-Item $zip).Length / 1MB)
Log "done: $name ($size MB)"

# Rotate: keep the newest 3
Get-ChildItem $backupDir -Filter 'evermore-backup-*.zip' |
    Sort-Object LastWriteTime -Descending | Select-Object -Skip 3 |
    ForEach-Object { Log "rotate: deleting $($_.Name)"; Remove-Item $_.FullName -Force }
