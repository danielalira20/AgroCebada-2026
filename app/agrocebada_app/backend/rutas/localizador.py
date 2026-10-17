"""Dónde están las fuentes originales: dataset del reto, T08, T03 y T04 (con variables de entorno como respaldo)."""
import os
from pathlib import Path

from agrocebada_app.config import APP, CLAVE_DATASET


def raiz():
    """Raíz del repo: la primera carpeta hacia arriba con el dataset, `registro/` o `.git`."""
    for c in [APP, *APP.parents]:
        if any((c / m).exists() for m in ("DATASET_RETO_AGRO_2026", "registro", ".git")):
            return c
    return APP


def buscar(env, *candidatas):
    if os.environ.get(env):
        return Path(os.environ[env])
    r = raiz()
    for c in candidatas:
        if (r / c).exists():
            return r / c
    return None


def buscar_con(env, archivo, *candidatas):
    """Primera carpeta candidata que tenga `archivo`; si ninguna lo tiene, busca dentro de registro/ y entregas/."""
    if os.environ.get(env):
        return Path(os.environ[env])
    r = raiz()
    for c in candidatas:
        if (r / c / archivo).exists():
            return r / c
    for base in ("registro", "entregas"):
        if (r / base).is_dir():
            for f in sorted((r / base).glob(f"*/{archivo}")):
                return f.parent
    return None


def buscar_dataset():
    """Carpeta del dataset del reto: AGRO_DATOS, o la primera que tenga la tabla de parcelas en la raíz del repo,
    en datos/ o en data/ (también una carpeta adentro, p. ej. data/DATASET_RETO_AGRO_2026)."""
    if os.environ.get("AGRO_DATOS"):
        return Path(os.environ["AGRO_DATOS"])
    r = raiz()
    for c in ["DATASET_RETO_AGRO_2026", "datos/DATASET_RETO_AGRO_2026", "data/DATASET_RETO_AGRO_2026", "datos", "data"]:
        if (r / c / CLAVE_DATASET).exists():
            return r / c
    for base in ("data", "datos"):
        if (r / base).is_dir():
            for f in sorted((r / base).glob(f"*/{CLAVE_DATASET}")):
                return f.parent
    return None


def rutas():
    return {"datos": buscar_dataset(),
            "t08": buscar_con("AGRO_T08", "predicciones_59_referencias.csv", "registro/t08", "registro/t03", "entregas/T08"),
            "t03": buscar_con("AGRO_T03", "soporte_parcelas.csv", "registro/t03", "entregas/T03"),
            "t04": buscar("AGRO_T04", "registro/t04/clima_parcela_mes.csv", "entregas/T04/clima_parcela_mes.csv")}
