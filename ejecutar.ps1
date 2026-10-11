# Ejecuta un comando del proyecto dentro del entorno Docker común (PowerShell en Windows).
#
#   .\ejecutar.ps1                        -> 240 pruebas (python -m unittest discover -s tests)
#   .\ejecutar.ps1 python -m scripts.t07_verificar --entrega registro/t07 --clima reports/...
#   .\ejecutar.ps1 --amd64 ...            -> plataforma fija linux/amd64 (T18, T21 y comparación entre equipos)
#
# Si Windows bloquea scripts: powershell -ExecutionPolicy Bypass -File .\ejecutar.ps1 ...
# Antes de cada comando construye la imagen (usa caché) y comprueba los datos originales.
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

$comando = @($args)
$plataforma = @()
$imagen = 'agrocebada-entorno'
if ($comando.Count -gt 0 -and $comando[0] -eq '--amd64') {
    $plataforma = @('--platform', 'linux/amd64')
    $imagen = 'agrocebada-entorno:amd64'
    $comando = @($comando | Select-Object -Skip 1)
}
if ($comando.Count -eq 0) {
    $comando = @('python', '-m', 'unittest', 'discover', '-s', 'tests')
}

docker build @plataforma -q -t $imagen . | Out-Null
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$volumen = "${PSScriptRoot}:/proyecto"
docker run --rm @plataforma -v $volumen -w /proyecto $imagen python scripts/comprobar_datos.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

docker run --rm @plataforma -v $volumen -w /proyecto $imagen @comando
exit $LASTEXITCODE
