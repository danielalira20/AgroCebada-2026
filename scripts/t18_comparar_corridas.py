"""T18 · Compara dos corridas de scripts/t18_predicciones_finales.py.

Uso:
    python -m scripts.t18_comparar_corridas --a registro/t18 --b reports/t18_corrida2

Falla (código 1) si difiere cualquier archivo de entrega o algo que debería ser igual:
    predicciones_finales.csv y detalle_predicciones_59.csv   byte a byte
    trazabilidad.json: controles, entradas, código, salidas, formato, etiquetas por municipio,
                       versiones de Python/pandas/numpy/geopandas y arquitectura
Sólo informa, sin fallar: commit, rama y fecha (cambian entre corridas sin afectar el resultado).
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

ARCHIVOS = ["predicciones_finales.csv", "detalle_predicciones_59.csv"]
DEBEN_SER_IGUALES = ["procedimiento", "version", "controles", "etiquetas_por_municipio", "entradas_sha256",
                     "codigo_sha256", "salidas_sha256", "formato_entrega"]
ENTORNO_IGUAL = ["python", "pandas", "numpy", "geopandas", "arquitectura"]
SOLO_INFORMA = ["git", "generado_utc"]


def huella(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def comparar(a: Path, b: Path):
    """Devuelve (diferencias, informativos)."""
    dif, info = [], []
    for nombre in ARCHIVOS:
        pa, pb = a / nombre, b / nombre
        if not pa.exists() or not pb.exists():
            dif.append(f"{nombre}: falta en {'A' if not pa.exists() else 'B'}")
        elif pa.read_bytes() != pb.read_bytes():
            dif.append(f"{nombre}: difiere byte a byte ({huella(pa)[:12]} vs {huella(pb)[:12]})")
    ta, tb = (json.loads((x / "trazabilidad.json").read_text(encoding="utf-8")) for x in (a, b))
    for k in DEBEN_SER_IGUALES:
        if ta.get(k) != tb.get(k):
            dif.append(f"trazabilidad.{k}: difiere")
    for k in ENTORNO_IGUAL:
        if ta["entorno"].get(k) != tb["entorno"].get(k):
            dif.append(f"entorno.{k}: {ta['entorno'].get(k)} vs {tb['entorno'].get(k)}")
    for k in SOLO_INFORMA:
        if ta.get(k) != tb.get(k):
            info.append(f"{k}: A={ta.get(k)} | B={tb.get(k)}")
    return dif, info


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--a", type=Path, required=True)
    ap.add_argument("--b", type=Path, required=True)
    x = ap.parse_args()
    dif, info = comparar(x.a, x.b)
    for linea in info:
        print("informativo ->", linea)
    if dif:
        print("DIFERENCIAS:")
        for linea in dif:
            print(" -", linea)
        sys.exit(1)
    print(f"IGUALES: {', '.join(ARCHIVOS)} idénticos byte a byte; trazabilidad y entorno coinciden.")


if __name__ == "__main__":
    main()
