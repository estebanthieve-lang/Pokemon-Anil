param(
  [Parameter(Mandatory = $true)]
  [string]$GameDir,

  [Parameter(Mandatory = $true)]
  [string]$SaveDir
)

$ErrorActionPreference = "Stop"

function Ensure-Dir($Path) {
  if (-not (Test-Path -LiteralPath $Path)) {
    New-Item -ItemType Directory -Force -Path $Path | Out-Null
  }
}

function Backup-ExistingSave($SavePath, $BackupRoot, $Reason) {
  if (-not (Test-Path -LiteralPath $SavePath)) {
    return
  }
  Ensure-Dir $BackupRoot
  $stamp = Get-Date -Format "yyyyMMdd_HHmmss"
  $name = [System.IO.Path]::GetFileNameWithoutExtension($SavePath)
  $ext = [System.IO.Path]::GetExtension($SavePath)
  $backupPath = Join-Path $BackupRoot "$name`_$Reason`_$stamp$ext"
  Copy-Item -LiteralPath $SavePath -Destination $backupPath -Force
}

Ensure-Dir $SaveDir
$backupRoot = Join-Path $SaveDir "backups\autosaves"
Ensure-Dir $backupRoot
Ensure-Dir (Join-Path $SaveDir "backups\manual")
Ensure-Dir (Join-Path $SaveDir "backups\updates")

$gameSaves = @()
if (Test-Path -LiteralPath $GameDir) {
  $gameSaves = Get-ChildItem -LiteralPath $GameDir -Filter "Partida *.rxdata" -File -ErrorAction SilentlyContinue
}

foreach ($gameSave in $gameSaves) {
  $appSave = Join-Path $SaveDir $gameSave.Name
  $shouldImport = -not (Test-Path -LiteralPath $appSave)
  if (-not $shouldImport) {
    $current = Get-Item -LiteralPath $appSave
    $shouldImport = $gameSave.LastWriteTimeUtc -gt $current.LastWriteTimeUtc
  }
  if ($shouldImport) {
    Backup-ExistingSave $appSave $backupRoot "before_import"
    Copy-Item -LiteralPath $gameSave.FullName -Destination $appSave -Force
  }
}

$appSaves = Get-ChildItem -LiteralPath $SaveDir -Filter "Partida *.rxdata" -File -ErrorAction SilentlyContinue
foreach ($appSave in $appSaves) {
  $gameSave = Join-Path $GameDir $appSave.Name
  $shouldCopyToGame = -not (Test-Path -LiteralPath $gameSave)
  if (-not $shouldCopyToGame) {
    $current = Get-Item -LiteralPath $gameSave
    $shouldCopyToGame = $appSave.LastWriteTimeUtc -gt $current.LastWriteTimeUtc
  }
  if ($shouldCopyToGame) {
    Copy-Item -LiteralPath $appSave.FullName -Destination $gameSave -Force
  }
}
