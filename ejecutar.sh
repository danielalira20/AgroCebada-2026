#!/usr/bin/env bash
# Ejecuta un comando del proyecto dentro del entorno Docker común (Mac, Linux o Git Bash en Windows).
#
#   ./ejecutar.sh                         -> 240 pruebas (python -m unittest discover -s tests)
#   ./ejecutar.sh python -m scripts.t07_verificar --entrega registro/t07 --clima reports/...
#   ./ejecutar.sh --amd64 ...             -> plataforma fija linux/amd64 (T18, T21 y comparación entre equipos)
#
# Antes de cada comando construye la imagen (usa caché) y comprueba los datos originales.
set -euo pipefail
cd "$(dirname "$0")"

PLATAFORMA=()
IMAGEN="agrocebada-entorno"
if [[ "${1:-}" == "--amd64" ]]; then
  PLATAFORMA=(--platform linux/amd64)
  IMAGEN="agrocebada-entorno:amd64"
  shift
fi
if [[ $# -eq 0 ]]; then
  set -- python -m unittest discover -s tests
fi

# Git Bash en Windows: ruta en formato Windows y sin conversión automática de /proyecto.
CARPETA="$(pwd)"
case "$(uname -s)" in
  MINGW*|MSYS*|CYGWIN*) CARPETA="$(pwd -W)"; export MSYS_NO_PATHCONV=1 ;;
esac

docker build "${PLATAFORMA[@]}" -q -t "$IMAGEN" . > /dev/null
EJECUTAR=(docker run --rm "${PLATAFORMA[@]}" -v "$CARPETA:/proyecto" -w /proyecto "$IMAGEN")
"${EJECUTAR[@]}" python scripts/comprobar_datos.py
exec "${EJECUTAR[@]}" "$@"
