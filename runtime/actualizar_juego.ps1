param(
  [Parameter(Mandatory = $true)]
  [string]$InstallRoot,

  [string]$UpdateRoot = ""
)

$ErrorActionPreference = "Stop"

function Resolve-LocalPath([string]$root, [string]$relative) {
  $clean = $relative -replace "/", "\"
  return [System.IO.Path]::GetFullPath((Join-Path (Normalize-InputPath $root) $clean))
}

function Resolve-AppDataPath([string]$path) {
  return $path.Replace("%APPDATA%", $env:APPDATA)
}

function Normalize-InputPath([string]$path) {
  return ($path -replace '"', "").Trim()
}

function Read-JsonFile([string]$path) {
  return Get-Content -Raw -LiteralPath $path | ConvertFrom-Json
}

function Read-JsonFromUrl([string]$url) {
  $response = Invoke-WebRequest -Uri $url -UseBasicParsing
  $json = [string]$response.Content
  return $json.Trim([char]0xFEFF) | ConvertFrom-Json
}

function Get-LatestManifest($manifest) {
  $latestUrl = [string]$manifest.updates.latestManifestUrl
  if (-not $latestUrl) { return $manifest }

  Write-Host ""
  Write-Host "Leyendo manifest remoto:" -ForegroundColor Cyan
  Write-Host "  $latestUrl"
  return Read-JsonFromUrl $latestUrl
}

function Backup-ExistingPath([string]$target, [string]$backupRoot, [string]$relative) {
  if (-not (Test-Path -LiteralPath $target)) { return }
  $backupTarget = Resolve-LocalPath $backupRoot $relative
  $backupParent = Split-Path $backupTarget -Parent
  if ($backupParent) { New-Item -ItemType Directory -Force -Path $backupParent | Out-Null }
  Copy-Item -LiteralPath $target -Destination $backupTarget -Recurse -Force
}

function Copy-UpdatePath([string]$source, [string]$target) {
  if ((Get-Item -LiteralPath $source).PSIsContainer) {
    New-Item -ItemType Directory -Force -Path $target | Out-Null
    Copy-Item -LiteralPath (Join-Path $source "*") -Destination $target -Recurse -Force
    return
  }
  $targetParent = Split-Path $target -Parent
  if ($targetParent) { New-Item -ItemType Directory -Force -Path $targetParent | Out-Null }
  Copy-Item -LiteralPath $source -Destination $target -Force
}

function Merge-ActionsConfig([string]$currentPath, [string]$incomingPath) {
  if (-not (Test-Path -LiteralPath $currentPath)) {
    Copy-UpdatePath $incomingPath $currentPath
    return
  }

  $current = Read-JsonFile $currentPath
  $incoming = Read-JsonFile $incomingPath

  foreach ($property in $incoming.PSObject.Properties) {
    if ($property.Name -eq "actions") {
      $current.actions = $incoming.actions
      continue
    }
    if (-not ($current.PSObject.Properties.Name -contains $property.Name)) {
      $current | Add-Member -MemberType NoteProperty -Name $property.Name -Value $property.Value
    }
  }

  $json = $current | ConvertTo-Json -Depth 100
  $encoding = [System.Text.UTF8Encoding]::new($false)
  [System.IO.File]::WriteAllText($currentPath, $json, $encoding)
}

$installPath = [System.IO.Path]::GetFullPath((Normalize-InputPath $InstallRoot))
$configPath = Join-Path $installPath "game.config.json"
if (-not (Test-Path -LiteralPath $configPath)) {
  throw "Falta game.config.json en la instalacion actual."
}

$currentManifestPath = Join-Path $installPath "game-manifest.json"
$currentManifest = if (Test-Path -LiteralPath $currentManifestPath) { Read-JsonFile $currentManifestPath } else { $null }
$tempUpdateRoot = $null

if (-not $UpdateRoot) {
  $latestManifest = Get-LatestManifest $currentManifest
  $downloadUrl = [string]$latestManifest.updates.downloadUrl

  if ($downloadUrl) {
    Write-Host ""
    Write-Host "Descargando paquete liviano de actualizacion:" -ForegroundColor Cyan
    Write-Host "  $downloadUrl"
    $tempUpdateRoot = Join-Path $env:TEMP ("pokemon-anil-update-" + [guid]::NewGuid().ToString("N"))
    $zipPath = Join-Path $tempUpdateRoot "update.zip"
    $extractRoot = Join-Path $tempUpdateRoot "extract"
    New-Item -ItemType Directory -Force -Path $tempUpdateRoot,$extractRoot | Out-Null
    Invoke-WebRequest -Uri $downloadUrl -OutFile $zipPath
    Expand-Archive -LiteralPath $zipPath -DestinationPath $extractRoot -Force
    $candidate = Get-ChildItem -LiteralPath $extractRoot -Directory | Where-Object {
      Test-Path -LiteralPath (Join-Path $_.FullName "game-manifest.json")
    } | Select-Object -First 1
    if (-not $candidate -and (Test-Path -LiteralPath (Join-Path $extractRoot "game-manifest.json"))) {
      $candidate = Get-Item -LiteralPath $extractRoot
    }
    if (-not $candidate) {
      throw "El ZIP descargado no trae game-manifest.json en la raiz."
    }
    $UpdateRoot = $candidate.FullName
  } else {
    Write-Host ""
    Write-Host "Pega la ruta de la carpeta nueva de Pokemon Anil Live."
    Write-Host "No pegues la misma carpeta instalada ni un ZIP directo."
    $UpdateRoot = Read-Host "Ruta"
  }
}

$updatePath = [System.IO.Path]::GetFullPath($UpdateRoot.Trim('"'))
if (-not (Test-Path -LiteralPath $updatePath)) {
  throw "No existe la carpeta de actualizacion: $updatePath"
}

$incomingManifestPath = Join-Path $updatePath "game-manifest.json"
if (-not (Test-Path -LiteralPath $incomingManifestPath)) {
  throw "La actualizacion no trae game-manifest.json"
}

$incomingManifest = Read-JsonFile $incomingManifestPath
if ($currentManifest -and $currentManifest.gameId -and $incomingManifest.gameId -and $currentManifest.gameId -ne $incomingManifest.gameId) {
  throw "La actualizacion es de otro juego. Actual: $($currentManifest.gameId), update: $($incomingManifest.gameId)"
}

$config = Read-JsonFile $configPath
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$updateBackupRoot = Resolve-AppDataPath $config.updateBackupRoot
if (-not $updateBackupRoot) {
  $updateBackupRoot = Join-Path (Join-Path (Join-Path $env:APPDATA "Pokemon Anil Live") "backups") "updates"
}
$backupRoot = Join-Path $updateBackupRoot "update-$timestamp"
New-Item -ItemType Directory -Force -Path $backupRoot | Out-Null

$protected = @($config.protectedPaths) | Where-Object { $_ }
$mergeFiles = @($config.mergeConfigFiles) | Where-Object { $_ }
$updatable = @($config.updatablePaths) | Where-Object { $_ }

Write-Host ""
Write-Host "Instalacion: $installPath" -ForegroundColor White
Write-Host "Actualizacion: $updatePath" -ForegroundColor White
Write-Host "Backup de archivos reemplazados: $backupRoot" -ForegroundColor White
Write-Host ""
Write-Host "No se tocaran partidas en: $(Join-Path $env:APPDATA 'Pokemon Anil Live')" -ForegroundColor Green
Write-Host ""

foreach ($relative in $mergeFiles) {
  $source = Resolve-LocalPath $updatePath $relative
  if (-not (Test-Path -LiteralPath $source)) {
    Write-Host "No viene merge config, se deja igual: $relative"
    continue
  }
  $target = Resolve-LocalPath $installPath $relative
  Backup-ExistingPath $target $backupRoot $relative
  Merge-ActionsConfig $target $source
  Write-Host "Config fusionada sin pisar opciones locales: $relative" -ForegroundColor Green
}

foreach ($relative in $updatable) {
  if ($mergeFiles -contains $relative) { continue }
  if ($protected -contains $relative) {
    Write-Host "Saltando protegido: $relative" -ForegroundColor Yellow
    continue
  }

  $source = Resolve-LocalPath $updatePath $relative
  if (-not (Test-Path -LiteralPath $source)) {
    Write-Host "No viene en update, se deja igual: $relative"
    continue
  }

  $target = Resolve-LocalPath $installPath $relative
  Backup-ExistingPath $target $backupRoot $relative
  Copy-UpdatePath $source $target
  Write-Host "Actualizado: $relative" -ForegroundColor Green
}

Write-Host ""
Write-Host "Listo. Se actualizaron archivos del juego sin borrar saves/configs protegidas." -ForegroundColor Green
Write-Host "Backups de seguridad del update:" -ForegroundColor White
Write-Host "  $backupRoot"
Write-Host ""
Write-Host "Abre INICIAR POKEMON ANIL LIVE.cmd para probar." -ForegroundColor Cyan

if ($tempUpdateRoot -and (Test-Path -LiteralPath $tempUpdateRoot)) {
  Remove-Item -LiteralPath $tempUpdateRoot -Recurse -Force -ErrorAction SilentlyContinue
}
