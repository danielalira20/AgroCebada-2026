"""Comprueba que los datos originales locales son el paquete FIRA identificado.

1. La huella SHA-256 de data/raw/DataSet.zip debe coincidir con la que T04
   registró en registro/t04/procedencia.json (sha256_paquete).
2. Cada archivo extraído en data/raw/DATASET_RETO_AGRO_2026 debe ser idéntico,
   byte a byte, a su miembro dentro del ZIP (incluidos los ZIP internos de
   geometrías, lluvia, temperatura y topografía).

Un archivo faltante, distinto o un ZIP distinto detienen la ejecución.
Los archivos adicionales en la carpeta extraída sólo se avisan.
No modifica ningún archivo.

    python scripts/comprobar_datos.py
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import sys
import zipfile

RAIZ = Path(__file__).resolve().parents[1]
PREFIJO = "DATASET_RETO_AGRO_2026/"


def sha_bytes(datos):
    return hashlib.sha256(datos).hexdigest()


def sha_archivo(ruta):
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        for bloque in iter(lambda: f.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()


def comparar_miembros(zipf, carpeta, prefijo_quitar, errores, esperados):
    """Compara cada miembro (no directorio) del ZIP con su archivo extraído."""
    for info in zipf.infolist():
        if info.is_dir() or not info.filename.startswith(prefijo_quitar):
            continue
        relativo = info.filename[len(prefijo_quitar):]
        ruta = carpeta / relativo
        esperados.add(ruta.resolve())
        datos = zipf.read(info)
        if not ruta.is_file():
            errores.append(f"falta: {ruta.relative_to(RAIZ_DATOS)}")
        elif sha_archivo(ruta) != sha_bytes(datos):
            errores.append(f"distinto del ZIP: {ruta.relative_to(RAIZ_DATOS)}")
        if info.filename.lower().endswith(".zip"):
            interior = zipfile.ZipFile(io.BytesIO(datos))
            subcarpeta = ruta.with_suffix("")
            if subcarpeta.is_dir():
                comparar_miembros(interior, subcarpeta, "", errores, esperados)
            else:
                errores.append(f"falta carpeta extraída: {subcarpeta.relative_to(RAIZ_DATOS)}")


def comprobar(raiz=RAIZ, solo_zip=False):
    global RAIZ_DATOS
    raiz = Path(raiz).resolve()
    RAIZ_DATOS = raiz / "data/raw"
    procedencia = json.loads((raiz / "registro/t04/procedencia.json").read_text(encoding="utf-8"))
    esperado = procedencia["sha256_paquete"]
    paquete = RAIZ_DATOS / "DataSet.zip"
    if not paquete.is_file():
        raise SystemExit(f"Datos no comprobados: falta {paquete.relative_to(raiz)}")
    obtenido = sha_archivo(paquete)
    if obtenido != esperado:
        raise SystemExit(f"Datos no comprobados: DataSet.zip distinto del paquete identificado por T04\n"
                         f"  esperado {esperado}\n  obtenido {obtenido}")
    resultado = dict(resultado="aprobado", dataset_zip_sha256=obtenido, carpeta_extraida="no revisada")
    if not solo_zip:
        carpeta = RAIZ_DATOS / "DATASET_RETO_AGRO_2026"
        if not carpeta.is_dir():
            resultado["carpeta_extraida"] = "ausente (las tareas que la usan fallarán)"
        else:
            errores, esperados = [], set()
            comparar_miembros(zipfile.ZipFile(paquete), carpeta, PREFIJO, errores, esperados)
            if errores:
                raise SystemExit("Datos no comprobados: la carpeta extraída no coincide con DataSet.zip\n  "
                                 + "\n  ".join(errores))
            extras = sorted(str(p.relative_to(RAIZ_DATOS)) for p in carpeta.rglob("*")
                            if p.is_file() and p.resolve() not in esperados)
            resultado.update(carpeta_extraida="idéntica al ZIP", archivos_comparados=len(esperados),
                             archivos_adicionales=extras)
    return resultado


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--solo-zip", action="store_true", help="Comprobar sólo la huella de DataSet.zip")
    a = p.parse_args()
    r = comprobar(solo_zip=a.solo_zip)
    print(json.dumps(r, ensure_ascii=False, indent=2))
    if r.get("archivos_adicionales"):
        print("Aviso: hay archivos adicionales en la carpeta extraída; no son del paquete FIRA.", file=sys.stderr)


if __name__ == "__main__":
    main()
