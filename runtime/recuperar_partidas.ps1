param(
  [Parameter(Mandatory = $true)]
  [string]$ImportDir,

  [Parameter(Mandatory = $true)]
  [string]$SaveDir
)

$ErrorActionPreference = "Stop"

function Ensure-Dir([string]$path) {
  if (-not (Test-Path -LiteralPath $path)) {
    New-Item -ItemType Directory -Force -Path $path | Out-Null
  }
}

function Get-NextSavePath([string]$saveDir) {
  for ($slot = 1; $slot -le 999; $slot++) {
    $candidate = Join-Path $saveDir ("Partida {0}.rxdata" -f $slot)
    if (-not (Test-Path -LiteralPath $candidate)) {
      return $candidate
    }
  }
  throw "No quedan slots libres entre Partida 1 y Partida 999."
}

Ensure-Dir $ImportDir
Ensure-Dir $SaveDir
Ensure-Dir (Join-Path $SaveDir "backups")
Ensure-Dir (Join-Path $SaveDir "backups\manual")
Ensure-Dir (Join-Path $SaveDir "backups\autosaves")
Ensure-Dir (Join-Path $SaveDir "backups\updates")

$imports = Get-ChildItem -LiteralPath $ImportDir -Filter "*.rxdata" -File -ErrorAction SilentlyContinue |
  Where-Object { $_.Length -gt 0 } |
  Sort-Object Name

Write-Host ""
Write-Host "Carpeta para meter partidas:" -ForegroundColor Cyan
Write-Host "  $ImportDir"
Write-Host "Carpeta real de partidas Live:" -ForegroundColor Cyan
Write-Host "  $SaveDir"
Write-Host ""

if (-not $imports -or $imports.Count -eq 0) {
  Write-Host "No encontre archivos .rxdata para recuperar." -ForegroundColor Yellow
  Write-Host "Pon tus partidas dentro de MeterPartidasGuardadas y vuelve a ejecutar este BAT."
  exit 0
}

$copied = 0
foreach ($source in $imports) {
  $target = Get-NextSavePath $SaveDir
  Copy-Item -LiteralPath $source.FullName -Destination $target -Force
  Write-Host ("Recuperada: {0} -> {1}" -f $source.Name, [System.IO.Path]::GetFileName($target)) -ForegroundColor Green
  $copied++
}

Write-Host ""
Write-Host ("Listo. Se recuperaron {0} partida(s) sin reemplazar las existentes." -f $copied) -ForegroundColor Green
Write-Host "Abre INICIAR POKEMON ANIL LIVE.cmd para probarlas."
