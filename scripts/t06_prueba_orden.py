"""T06 · Prueba de orden: las salidas no dependen del orden de las filas de entrada.

Uso (desde la raíz del repositorio, después de regenerar registro/t06/ con t06_satelite.py):
    python scripts/t06_prueba_orden.py --datos RUTA/DATASET_RETO_AGRO_2026

Copia el Básico, el PRO y el catálogo a una carpeta temporal con las filas desordenadas
(semilla fija; los valores se copian como texto, sin reescribir números), corre
t06_satelite.py sobre esa copia y compara por md5 cada archivo de salida con los de
registro/t06/ y con las series de data/interim/t06/. Sale con código 1 si alguno difiere.
"""
import argparse
import hashlib
import subprocess
import sys
import tempfile
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
ENTRADAS = ["Conjunto_datos_BASICO_AgroCebada2026.csv", "Conjunto_datos_PRO_AgroCebada.csv",
            "ID_area_rendimiento_70_30_Reto_AgroCebada.csv"]


def md5(ruta: Path) -> str:
    return hashlib.md5(ruta.read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--datos", type=Path, required=True)
    ap.add_argument("--semilla", type=int, default=20261006)
    ap.add_argument("--referencia", type=Path, default=RAIZ / "registro" / "t06")
    ap.add_argument("--series", type=Path, default=RAIZ / "data" / "interim" / "t06")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        (tmp / "datos").mkdir()
        for nombre in ENTRADAS:
            x = pd.read_csv(a.datos / nombre, encoding="utf-8-sig", dtype=str, keep_default_na=False)
            x.sample(frac=1, random_state=a.semilla).to_csv(tmp / "datos" / nombre, index=False,
                                                             encoding="utf-8-sig")
        subprocess.run([sys.executable, str(RAIZ / "scripts" / "t06_satelite.py"), "--datos", str(tmp / "datos"),
                        "--salida", str(tmp / "salida"), "--series", str(tmp / "series")],
                       check=True, stdout=subprocess.DEVNULL)
        distintos = []
        for ref, nuevo in [(a.referencia, tmp / "salida"), (a.series, tmp / "series")]:
            nombres = sorted({p.name for p in ref.iterdir()} | {p.name for p in nuevo.iterdir()})
            for n in nombres:
                igual = (ref / n).exists() and (nuevo / n).exists() and md5(ref / n) == md5(nuevo / n)
                print(f"{'idéntico ' if igual else 'DISTINTO '} {ref.name}/{n}")
                if not igual:
                    distintos.append(n)
    print(f"semilla {a.semilla}: {len(distintos)} archivos distintos")
    sys.exit(1 if distintos else 0)


if __name__ == "__main__":
    main()
