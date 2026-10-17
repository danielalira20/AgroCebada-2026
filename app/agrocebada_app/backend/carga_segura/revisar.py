"""Punto de entrada de la carga segura: decide el formato y devuelve el resultado o rechaza con un motivo."""
from pathlib import Path

from agrocebada_app.backend.carga_segura.errores import Rechazo, Resultado
from agrocebada_app.backend.carga_segura.reglas import MAX_MB
from agrocebada_app.backend.carga_segura.tabla import desde_csv_simple
from agrocebada_app.backend.carga_segura.zip_seguro import desde_zip


def revisar(nombre: str, contenido: bytes) -> Resultado:
    ext = Path(nombre or "").suffix.lower()
    if ext not in {".zip", ".csv"}:
        raise Rechazo(f"Tipo de archivo no permitido ({ext or 'sin extensión'}). Sólo se aceptan .zip o .csv.")
    if len(contenido) > MAX_MB * 1024 * 1024:
        raise Rechazo(f"El archivo pesa {len(contenido) / 1e6:.0f} MB; el máximo es {MAX_MB} MB.")
    if not contenido:
        raise Rechazo("El archivo está vacío.")
    if ext == ".zip":
        return desde_zip(contenido)
    return desde_csv_simple(contenido)
