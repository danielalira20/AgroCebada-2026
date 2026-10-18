"""T13 · extensión (D025): los índices que T06 calculó en sus series pero no resumió por parcela.

Paso 1, sin rendimiento: resume los índices con las reglas de T06 (importando sus funciones) y guarda
registro/t13/variables_indices_extra.csv (197 filas). Se detiene si no reproduce exactamente las
columnas de T06 que ya están en la tabla común.
Paso 2: mismo estimador, casos y regla que T13 (D024, T11-v2.1), con las 7 configuraciones de D025.
Se detiene si el control (NDVI S2 solo) no reproduce las predicciones de t13_c3.

Uso:
    python scripts/t13_extension_indices.py                      # series en data/interim/t06/
    python scripts/t13_extension_indices.py --series OTRA/RUTA
"""
import argparse
import importlib.util
import itertools
import time
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
CODIGO_T06 = RAIZ / "scripts" / "t06_satelite.py"
CODIGO_T11 = RAIZ / "scripts" / "t11_aporte_satelital.py"
SERIES = RAIZ / "data" / "interim" / "t06"
SALIDA = RAIZ / "registro" / "t13"
OOF_T13 = SALIDA / "predicciones_oof_t13.csv"
VARIABLES = SALIDA / "variables_indices_extra.csv"
VERSION = "T13e-v1"
ESTIMADOR_ESPERADO = "T11-v2.1"

# ---------------------------------------------------------------- índices (D025)
# Sentinel-2: valor alrededor del máximo de NDVI (regla de ndwi_en_maximo). Planet: máximo de la curva
# (regla de lai2_max). Se quita uno de cada par casi idéntico: LAI (=SAVI), MSI (=NDWI), EMSI (=ENDWI),
# DSWI2 (=MCRC), DSWI3 (=NDSVI), STI (=NDTI).
S2_EXTRA = ["evi", "savi", "fapar", "mra", "endwi", "dswi4", "dswi5",
            "crc", "mcrc", "srndi", "nddi", "enddi", "ndti", "ndsvi"]
S2_QUITADOS = {"lai": "savi", "msi": "ndwi", "emsi": "endwi", "dswi2": "mcrc", "dswi3": "ndsvi", "sti": "ndti"}
PL_EXTRA = ["evi", "msavi"]


def s2(i):
    return f"s2_{i}_en_maximo_abr_oct"


def pl(i):
    return f"pl_{i}_max_abr_oct"


NDVI_S2 = "s2_ndvi_max_abr_oct"
RESIDUOS = [s2(i) for i in ["crc", "mcrc", "srndi", "nddi", "enddi"]]
CONFIGS = {
    1: dict(cols=[s2(i) for i in ["evi", "savi", "fapar", "mra"]], centrar=False),
    2: dict(cols=[s2(i) for i in ["endwi", "dswi4", "dswi5"]], centrar=False),
    3: dict(cols=RESIDUOS, centrar=False),
    4: dict(cols=[s2(i) for i in ["ndti", "ndsvi"]], centrar=False),
    5: dict(cols=[pl(i) for i in PL_EXTRA], centrar=False),
    6: dict(cols=[NDVI_S2] + RESIDUOS, centrar=False),
    7: dict(cols=[NDVI_S2], centrar=False),
}
CANDIDATOS = {
    0: "media_mun__resp_grupo",
    1: "t13e_c1_verdor_s2",
    2: "t13e_c2_agua_estres_s2",
    3: "t13e_c3_residuos_sequia_s2",
    4: "t13e_c4_labranza_senescencia_s2",
    5: "t13e_c5_verdor_planet",
    6: "t13e_c6_ndvi_s2_mas_residuos",
    7: "t13e_c7_ndvi_s2_control",
}
COMPARACIONES = [(n, 0, "promocion") for n in range(1, 8)] + [
    (6, 7, "aporte de residuos y sequía sobre NDVI S2"),
]


def cargar(nombre, ruta):
    spec = importlib.util.spec_from_file_location(nombre, ruta)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def cargar_estimador():
    """Copia independiente del código de T11 con las configuraciones de D025."""
    m = cargar("t11_para_t13e", CODIGO_T11)
    if m.VERSION != ESTIMADOR_ESPERADO:
        raise ValueError(f"D025 usa {ESTIMADOR_ESPERADO} y el código de T11 es {m.VERSION}")
    m.CONFIGS, m.CANDIDATOS, m.COMPARACIONES = CONFIGS, CANDIDATOS, COMPARACIONES
    m.VERSION, m.SALIDA = VERSION, SALIDA
    return m


# ---------------------------------------------------------------- paso 1: resumen sin rendimiento
def resumir_indices(series=SERIES):
    """Una fila por parcela con las reglas de T06 (funciones importadas, sin cambios)."""
    t06 = cargar("t06_para_t13e", CODIGO_T06)
    ini = t06.VENTANAS["abr_oct"]
    filas = {}
    for sensor, archivo in [("Sentinel-2", "serie_sentinel2.csv"), ("Planet", "serie_planet.csv")]:
        x = t06.validas(pd.read_csv(series / archivo), sensor, ini)
        for pid, p in x.groupby("ID_POLIGONO"):
            r = filas.setdefault(pid, {})
            if len(p) < 5:  # misma condición que resumen_parcela de T06
                continue
            f = pd.DatetimeIndex(p.f.values)
            sv, k, _, _ = t06.curva(p.ndvi_promedio.values)
            if sensor == "Sentinel-2":
                cerca = (f >= f[k] - t06.ALREDEDOR_MAXIMO) & (f <= f[k] + t06.ALREDEDOR_MAXIMO)
                r[NDVI_S2] = sv[k]
                for i in ["ndwi", *S2_EXTRA, *S2_QUITADOS]:
                    r[s2(i)] = np.median(p[f"{i}_promedio"].values[cerca])
            else:
                r["pl_ndvi_max_abr_oct"] = sv[k]
                for i in ["lai2", *PL_EXTRA]:
                    r[pl(i)] = t06.curva(p[f"{i}_promedio"].values)[0].max()
    out = pd.DataFrame.from_dict(filas, orient="index").sort_index()
    out.index.name = "id_parcela"
    return out.reset_index()


def comprobar_resumen(var, tabla):
    """Las columnas que T06 ya resumió deben salir idénticas a la tabla común."""
    t = tabla.set_index("id_parcela")
    v = var.set_index("id_parcela").reindex(t.index)
    pares = {NDVI_S2: NDVI_S2, s2("ndwi"): "s2_ndwi_en_maximo_abr_oct",
             "pl_ndvi_max_abr_oct": "pl_ndvi_max_abr_oct", pl("lai2"): "pl_lai2_max_abr_oct"}
    for mia, de_t06 in pares.items():
        dif = (v[mia] - t[de_t06]).abs().max()
        print(f"  {mia} frente a la tabla común: diferencia máxima {dif:.1e}")
        if not dif < 1e-9:
            raise ValueError(f"El resumen no reproduce {de_t06} de T06 (diferencia {dif})")
    usadas = sorted({c for cfg in CONFIGS.values() for c in cfg["cols"]})
    if len(v) != 197 or v[usadas].isna().any().any():
        raise ValueError("Faltan parcelas o hay faltantes en las variables de D025")


def redundancia(var):
    """Spearman entre los índices de Sentinel-2 en las 197 parcelas (sin rendimiento)."""
    cols = [NDVI_S2, s2("ndwi")] + [s2(i) for i in [*S2_EXTRA, *S2_QUITADOS]]
    c = var[cols].corr(method="spearman")
    filas = [dict(indice_a=a, indice_b=b, spearman=c.loc[a, b],
                  par_casi_identico=abs(c.loc[a, b]) >= 0.99)
             for a, b in itertools.combinations(cols, 2)]
    return pd.DataFrame(filas)


# ---------------------------------------------------------------- paso 2: modelo
def comprobar_control(oof):
    """El control (NDVI S2 solo) debe dar las mismas predicciones que t13_c3."""
    t13 = pd.read_csv(OOF_T13)
    t13 = t13[t13.candidato == "t13_c3_ndvi_s2"]
    mia = oof[oof.config == 7]
    m = mia.merge(t13, on=["ID_POLIGONO", "repeticion", "escenario"], suffixes=("", "_t13"),
                  validate="one_to_one")
    dif = (m.prediccion - m.prediccion_t13).abs().max()
    print(f"  control frente a t13_c3: {len(m)} predicciones, diferencia máxima {dif:.1e}")
    if len(m) != 1380 or not dif < 1e-9:
        raise ValueError(f"El control no reproduce t13_c3 (filas {len(m)}, diferencia {dif})")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--series", type=Path, default=SERIES)
    a = ap.parse_args()
    pd.set_option("display.width", 220)
    SALIDA.mkdir(parents=True, exist_ok=True)
    t11 = cargar_estimador()
    tabla = pd.read_csv(t11.TABLA)

    print("paso 1: resumen de los índices con las reglas de T06 (sin rendimiento)")
    var = resumir_indices(a.series)
    comprobar_resumen(var, tabla)
    var.to_csv(VARIABLES, index=False)
    red = redundancia(var)
    red.to_csv(SALIDA / "redundancia_indices_extra_t13e.csv", index=False)
    print("  pares casi idénticos (|Spearman| ≥ 0.99):")
    print(red[red.par_casi_identico].round(3).to_string(index=False))
    con_ndvi = red[(red.indice_a == NDVI_S2)].set_index("indice_b").spearman.sort_values()
    print("  Spearman con NDVI S2:\n", con_ndvi.round(2).to_string())

    print("\npaso 2: modelo (mismo estimador que T13)")
    extra = var.drop(columns=[c for c in var.columns if c in tabla.columns and c != "id_parcela"])
    tabla = tabla.merge(extra, on="id_parcela", how="left", validate="one_to_one")
    part = pd.read_csv(t11.PARTICIONES)
    t11.revisar_datos(tabla, part)
    d = t11.preparar(tabla, part)
    t11.comprobar_referencia(d)

    t0 = time.time()
    oof, coefs = t11.evaluar_todo(d)
    print(f"listo en {time.time() - t0:.0f} s")
    comprobar_control(oof)
    oof["estimador"] = ESTIMADOR_ESPERADO
    oof.to_csv(SALIDA / "predicciones_oof_t13e.csv", index=False)
    coefs.to_csv(SALIDA / "coeficientes_t13e.csv", index=False)
    res = t11.resumir(oof)
    res.to_csv(SALIDA / "metricas_t13e.csv", index=False)

    print("\nalfa elegido (veces por config, ambos escenarios):")
    print(oof[oof.config > 0].drop_duplicates(["config", "escenario", "repeticion", "particion"])
          .groupby("config").alfa.value_counts().unstack(fill_value=0))
    print("\nmétricas en sin_respaldo (config 0 = referencia):")
    print(res[res.subconjunto == "sin_respaldo"].round(4).to_string(index=False))

    print("\ncomparación emparejada (bootstrap por celdas)...")
    celda = d.drop_duplicates("ID_POLIGONO").set_index("ID_POLIGONO").celda_chirps
    comp = t11.comparaciones(oof, celda)
    comp.to_csv(SALIDA / "comparacion_emparejada_t13e.csv", index=False)
    cols = ["escenario", "candidato", "dMAE", "IC95_celdas_MAE_inf", "IC95_celdas_MAE_sup",
            "reps_mejoran_MAE", "dRMSE", "IC95_celdas_RMSE_sup", "reps_mejoran_RMSE", "dR2",
            "cumple_regla_MAE", "cumple_regla_RMSE"]
    print("\nfrente a la referencia, sin_respaldo (aquí se decide, D019):")
    sel = (comp.tipo == "promocion") & (comp.subconjunto == "sin_respaldo")
    print(comp.loc[sel, cols].round(4).to_string(index=False))
    print("\nresiduos y sequía sobre NDVI S2 (descriptiva), sin_respaldo:")
    sel = (comp.tipo != "promocion") & (comp.subconjunto == "sin_respaldo")
    print(comp.loc[sel, cols].round(4).to_string(index=False))
    prom = comp[comp.tipo == "promocion"]
    print("\n¿alguna familia cumple la regla frente a la referencia?")
    print("  con MAE:", prom.cumple_regla_MAE.any(), "| con RMSE:", prom.cumple_regla_RMSE.any())

    print("\ndesgloses y sensibilidad (T03 §4 y §4 bis)...")
    t11.desgloses(oof, part).to_csv(SALIDA / "desglose_error_t13e.csv", index=False)
    sens = t11.sensibilidad_sin_alerta(oof)
    sens.to_csv(SALIDA / "sensibilidad_sin_alerta_t13e.csv", index=False)
    cols = ["escenario", "candidato", "dMAE", "dMAE_sin24", "orden_MAE", "orden_MAE_sin24",
            "dRMSE", "dRMSE_sin24"]
    print(sens.loc[sens.subconjunto == "sin_respaldo", cols].round(4).to_string(index=False))


if __name__ == "__main__":
    main()