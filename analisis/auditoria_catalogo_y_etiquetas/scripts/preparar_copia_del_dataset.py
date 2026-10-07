"""Prepara la copia descomprimida del dataset que leen los scripts de esta auditoría.

Uso (desde la raíz del repositorio):
    python analisis/auditoria_catalogo_y_etiquetas/scripts/preparar_copia_del_dataset.py --origen data/raw/DATASET_RETO_AGRO_2026 --destino data/DATASET_RETO_AGRO_2026

--origen   Carpeta con el paquete original de FIRA, tal como se recibió. Solo se lee.
--destino  Carpeta nueva donde queda la copia lista para usar. No debe existir todavía.

Qué hace:
    1. Copia al destino los archivos sueltos del origen (tablas CSV, documentos y los ZIP).
    2. Descomprime cada ZIP del origen en una carpeta con el mismo nombre del ZIP.
    3. Comprueba que estén los archivos que necesitan los scripts, una sola vez cada uno.

No modifica el origen. No hace falta si ya tienes una copia descomprimida con esa estructura.
"""
import argparse
import shutil
import sys
import zipfile
from pathlib import Path

sys.dont_write_bytecode = True

EN_SU_LUGAR = [
    "ID_area_rendimiento_70_30_Reto_AgroCebada.csv",
    "Conjunto_datos_BASICO_AgroCebada2026.csv",
    "Conjunto_datos_PRO_AgroCebada.csv",
    "Parcelas_Reto_AGC_CONJUNTO_70_30/Parcelas_Reto_AGC_CONJUNTO.shp",
    "Parcelas_Reto_AGC_CONJUNTO_70_30/Parcelas_Reto_AGC_CONJUNTO.dbf",
    "Parcelas_Reto_AGC_CONJUNTO_70_30/Parcelas_Reto_AGC_CONJUNTO.shx",
    "Parcelas_Reto_AGC_CONJUNTO_70_30/Parcelas_Reto_AGC_CONJUNTO.prj",
    "Parcelas_Reto_AGC_CONJUNTO_70_30/Parcelas_Reto_AGC_CONJUNTO.cpg",
]
EN_CUALQUIER_SUBCARPETA = [          # los scripts los buscan por nombre
    "PREC_2025_04.tif",
    "PREC_2025_07.tif",
    "Elevacion_INEGI_CEM4_120m.tif",
    "Pendiente_INEGI_CEM4_120m_grados.tif",
]


def comprobar_estructura(datos: Path):
    """Devuelve la lista de problemas encontrados; vacía si la carpeta sirve para los scripts."""
    problemas = [f"falta {nombre}" for nombre in EN_SU_LUGAR if not (datos / nombre).is_file()]
    for nombre in EN_CUALQUIER_SUBCARPETA:
        hallados = len(list(datos.rglob(nombre)))
        if hallados != 1:
            problemas.append(f"se esperaba un solo {nombre} y hay {hallados}")
    return problemas


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--origen", type=Path, required=True)
    ap.add_argument("--destino", type=Path, required=True)
    a = ap.parse_args()

    if not a.origen.is_dir():
        raise SystemExit(f"No existe la carpeta de origen: {a.origen}")
    if a.destino.exists():
        raise SystemExit(f"El destino ya existe y no se toca: {a.destino}. Indica una carpeta nueva.")
    if a.origen.resolve() in a.destino.resolve().parents:
        raise SystemExit("El destino no puede estar dentro del origen.")

    a.destino.mkdir(parents=True)
    sueltos = sorted(r for r in a.origen.iterdir() if r.is_file())
    for ruta in sueltos:
        shutil.copy2(ruta, a.destino / ruta.name)
    comprimidos = [r for r in sueltos if r.suffix.lower() == ".zip"]
    for ruta in comprimidos:
        with zipfile.ZipFile(ruta) as z:
            z.extractall(a.destino / ruta.stem)
    print(f"Copiados {len(sueltos)} archivos sueltos y descomprimidos {len(comprimidos)} ZIP en {a.destino}")

    problemas = comprobar_estructura(a.destino)
    if problemas:
        raise SystemExit("La copia no quedó lista:\n  " + "\n  ".join(problemas))
    print("Estructura comprobada: están los archivos que necesitan los scripts.")


if __name__ == "__main__":
    main()
