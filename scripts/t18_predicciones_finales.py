"""T18 · Predicciones finales de las 59 parcelas reservadas (mediana municipal).

Procedimiento congelado en T16 (D_T16_DECISION_001): `mediana_mun__resp_grupo`.
Cada parcela reservada recibe la mediana del rendimiento de las parcelas con cosecha
(las 138 de ENTRENAMIENTO) de su mismo municipio. No hay entrenamiento ni parámetros.

Uso (desde la raíz del repo, mejor con ./ejecutar.sh --amd64):
    python -m scripts.t18_predicciones_finales
    python -m scripts.t18_predicciones_finales --datos RUTA/DATASET_RETO_AGRO_2026 --salida registro/t18

Genera en --salida:
    predicciones_finales.csv          archivo de entrega: ID_POLIGONO, AREA_HA, RENDIMIENTO_T_HA, CONJUNTO
                                      (59 filas, mismo orden que el CSV oficial)
    detalle_predicciones_59.csv       por parcela: municipio, n de etiquetas del municipio, fuente, advertencia
    trazabilidad.json                 commit, huellas SHA256 de entradas/salidas, entorno, validaciones

Si alguna validación falla, el script termina con error y no escribe nada.
"""
import argparse
import hashlib
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from scripts.t08_referencias import cargar, referencia

VERSION = "T18-v1"
CANDIDATO = "mediana_mun__resp_grupo"
ENCABEZADO = ["ID_POLIGONO", "AREA_HA", "RENDIMIENTO_T_HA", "CONJUNTO"]
DECIMALES = 2
N_RESERVADAS = 59
N_ETIQUETADAS = 138
TOLERANCIA_T08 = 1e-9
RAIZ = Path(__file__).resolve().parent.parent
CSV_OFICIAL = "ID_area_rendimiento_70_30_Reto_AgroCebada.csv"
ZIP_PARCELAS = "Parcelas_Reto_AGC_CONJUNTO_70_30.zip"


class ValidacionError(SystemExit):
    pass


def exigir(cond, mensaje):
    if not cond:
        raise ValidacionError(f"T18 VALIDACIÓN FALLÓ: {mensaje}")
    return True


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for bloque in iter(lambda: f.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()


def git(*args):
    try:
        r = subprocess.run(["git", *args], cwd=RAIZ, capture_output=True, text=True, check=True)
        return r.stdout.strip()
    except Exception:
        return None


def leer_oficial_crudo(datos: Path) -> pd.DataFrame:
    """CSV oficial como texto (conserva AREA_HA tal cual) sin la columna vacía de la coma final."""
    c = pd.read_csv(datos / CSV_OFICIAL, encoding="utf-8-sig", dtype=str, keep_default_na=False)
    return c.drop(columns=[x for x in c.columns if x.startswith("Unnamed")])


def predecir(datos: Path, t08_csv: Path):
    crudo = leer_oficial_crudo(datos)
    d = cargar(datos)  # misma carga y mismo cruce de municipio que T08
    exigir(list(crudo.columns) == ENCABEZADO, f"encabezado oficial inesperado: {list(crudo.columns)}")
    exigir(len(crudo) == 197 and crudo.ID_POLIGONO.is_unique, "el CSV oficial debe tener 197 IDs únicos")
    exigir(list(d.index) == list(crudo.ID_POLIGONO), "el orden de IDs cambió al cruzar con el shapefile")

    tr = d[d.CONJUNTO == "ENTRENAMIENTO"]
    te = d[d.CONJUNTO == "PREDICCION"]
    exigir(len(tr) == N_ETIQUETADAS and len(te) == N_RESERVADAS, f"conjuntos {len(tr)}/{len(te)}, se esperaba 138/59")
    exigir(tr.real.notna().all() and np.isfinite(tr.real).all(), "hay etiquetas de entrenamiento vacías o no finitas")
    exigir(te.real.isna().all(), "alguna reservada trae rendimiento: no se usa ni se mezcla")
    exigir(d.municipio.notna().all(), "hay parcelas sin municipio")

    # Ruta A (independiente): mediana municipal con pandas simple.
    n_mun = tr.groupby("municipio").real.size()
    med = tr.groupby("municipio").real.median()
    sin_etiquetas = sorted(set(te.municipio) - set(med.index))
    exigir(not sin_etiquetas, f"municipios sin etiquetas (se necesitaría respaldo): {sin_etiquetas}")
    pred_a = te.municipio.map(med)

    # Ruta B: el estimador de T08 tal cual (con su respaldo, que aquí no debe activarse).
    valores_b, fuente_b = referencia("mediana", "grupo")(tr, te)
    pred_b = pd.Series(valores_b, index=te.index)
    exigir(set(fuente_b) == {"municipio"}, f"se activó un respaldo: {sorted(set(fuente_b))}")
    dif_ab = float(np.max(np.abs(pred_a.values - pred_b.values)))
    exigir(dif_ab == 0.0, f"ruta A (pandas) y ruta B (T08) difieren en {dif_ab}")

    pred = pred_a
    exigir(len(pred) == N_RESERVADAS and pred.index.is_unique, "no son exactamente 59 IDs únicos")
    exigir(np.isfinite(pred.values).all(), "alguna predicción no es finita")
    exigir((pred > 0).all(), "alguna predicción no es positiva")
    redondeo = float(np.max(np.abs(pred.values - pred.round(DECIMALES).values)))
    exigir(redondeo < 1e-9, f"las medianas no caben en {DECIMALES} decimales (pérdida {redondeo})")

    # Cruce con las predicciones de referencia de T08 (misma versión de procedimiento).
    t08 = pd.read_csv(t08_csv)
    t08 = t08[t08.candidato == CANDIDATO].set_index("ID_POLIGONO").prediccion
    exigir(len(t08) == N_RESERVADAS and set(t08.index) == set(pred.index), "T08 no trae las mismas 59 parcelas")
    dif_t08 = float(np.max(np.abs(t08.reindex(pred.index).values - pred.values)))
    exigir(dif_t08 <= TOLERANCIA_T08, f"las predicciones difieren de T08 en {dif_t08}")

    # Archivo de entrega: orden y AREA_HA del CSV oficial; sólo cambia RENDIMIENTO_T_HA.
    filas = crudo[crudo.CONJUNTO == "PREDICCION"].copy()
    exigir(list(filas.ID_POLIGONO) == list(pred.index), "el orden de las 59 no coincide con el CSV oficial")
    exigir((filas.RENDIMIENTO_T_HA == "").all(), "el CSV oficial trae rendimiento en alguna reservada")
    filas["RENDIMIENTO_T_HA"] = [f"{pred[i]:.{DECIMALES}f}" for i in filas.ID_POLIGONO]
    exigir(filas.RENDIMIENTO_T_HA.map(lambda s: np.isfinite(float(s))).all(), "valor escrito no finito")

    detalle = pd.DataFrame({
        "ID_POLIGONO": pred.index,
        "municipio": te.municipio.values,
        "n_etiquetas_municipio": te.municipio.map(n_mun).astype(int).values,
        "prediccion": [f"{v:.{DECIMALES}f}" for v in pred.values],
        "fuente": fuente_b,
    })
    detalle["advertencia"] = np.where(detalle.n_etiquetas_municipio == 1, "una_sola_etiqueta_en_el_municipio", "")
    controles = {
        "n_reservadas": int(len(pred)),
        "n_etiquetadas": int(len(tr)),
        "ids_unicos": True,
        "predicciones_finitas": True,
        "respaldos_activados": 0,
        "dif_max_ruta_pandas_vs_t08_estimador": dif_ab,
        "dif_max_vs_predicciones_59_referencias_t08": dif_t08,
        "perdida_por_redondeo": redondeo,
        "orden_igual_al_csv_oficial": True,
        "reservadas_sin_rendimiento_en_oficial": True,
        "parcelas_con_advertencia_una_sola_etiqueta": sorted(detalle.loc[detalle.advertencia != "", "ID_POLIGONO"]),
    }
    return filas, detalle, controles, n_mun


def bytes_csv(filas: pd.DataFrame) -> bytes:
    """UTF-8 con BOM y saltos CRLF, como el CSV oficial (sin la coma final vacía)."""
    lineas = [",".join(ENCABEZADO)] + [",".join(r) for r in filas[ENCABEZADO].itertuples(index=False, name=None)]
    return ("\r\n".join(lineas) + "\r\n").encode("utf-8-sig")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--datos", type=Path, default=RAIZ / "data" / "DATASET_RETO_AGRO_2026")
    ap.add_argument("--t08", type=Path, default=RAIZ / "registro" / "t03" / "predicciones_59_referencias.csv")
    ap.add_argument("--salida", type=Path, default=RAIZ / "registro" / "t18")
    a = ap.parse_args()

    filas, detalle, controles, n_mun = predecir(a.datos, a.t08)

    a.salida.mkdir(parents=True, exist_ok=True)
    destino = a.salida / "predicciones_finales.csv"
    destino.write_bytes(bytes_csv(filas))
    detalle.to_csv(a.salida / "detalle_predicciones_59.csv", index=False, lineterminator="\n")

    import geopandas
    traza = {
        "schema": "agrocebada_T18_trazabilidad_v1",
        "version": VERSION,
        "procedimiento": CANDIDATO,
        "decision": "D_T16_DECISION_001 (excepción explícita a T03; ver registro/decisiones.csv)",
        "metrica_validacion_de_referencia": {
            "fuente": "docs/t16_procedimiento_final.md §4 (A/sin_respaldo, 675 predicciones fuera de entrenamiento)",
            "MAE_mediana": 0.312585, "MAE_media": 0.320490,
        },
        "nota": "La salida no se puede evaluar contra rendimiento real: FIRA resguarda el de las 59.",
        "controles": controles,
        "etiquetas_por_municipio": {k: int(v) for k, v in n_mun.items()},
        "entradas_sha256": {
            CSV_OFICIAL: sha256(a.datos / CSV_OFICIAL),
            ZIP_PARCELAS: sha256(a.datos / ZIP_PARCELAS),
            "registro/t03/predicciones_59_referencias.csv": sha256(a.t08),
        },
        "codigo_sha256": {
            "scripts/t18_predicciones_finales.py": sha256(Path(__file__)),
            "scripts/t08_referencias.py": sha256(RAIZ / "scripts" / "t08_referencias.py"),
        },
        "salidas_sha256": {
            "predicciones_finales.csv": sha256(destino),
            "detalle_predicciones_59.csv": sha256(a.salida / "detalle_predicciones_59.csv"),
        },
        "formato_entrega": {"columnas": ENCABEZADO, "codificacion": "utf-8-sig", "saltos": "CRLF",
                            "decimales": DECIMALES, "filas": int(len(filas))},
        "git": {"commit": git("rev-parse", "HEAD"), "rama": git("rev-parse", "--abbrev-ref", "HEAD"),
                "cambios_en_archivos_rastreados": bool(git("status", "--porcelain", "--untracked-files=no"))},
        "entorno": {"python": sys.version.split()[0], "pandas": pd.__version__, "numpy": np.__version__,
                    "geopandas": geopandas.__version__, "plataforma": platform.platform(),
                    "arquitectura": platform.machine()},
        "generado_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    (a.salida / "trazabilidad.json").write_text(
        json.dumps(traza, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")

    print(f"T18 {VERSION}: {len(filas)} predicciones escritas en {destino}")
    print(detalle.groupby(["municipio", "n_etiquetas_municipio", "prediccion"]).size().rename("parcelas").to_string())
    if controles["parcelas_con_advertencia_una_sola_etiqueta"]:
        print("ADVERTENCIA (no bloquea):", controles["parcelas_con_advertencia_una_sola_etiqueta"],
              "tienen una sola etiqueta en su municipio")


if __name__ == "__main__":
    main()
