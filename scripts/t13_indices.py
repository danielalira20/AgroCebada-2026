"""T13: ¿qué índice es más importante en la predicción? (bonus 1 de las bases; D024).

Ablación por índices con el MISMO estimador, casos y particiones que T11-v2.1:
referencia media_mun__resp_grupo + Ridge sobre el residuo (calculado sin la propia fila),
α elegido dentro de cada entrenamiento (4 particiones internas, criterio cuadrático),
escenarios A y B × 5 repeticiones. Ventana abr_oct fija.

Para no copiar el estimador, este script carga una copia propia del código de T11 y sólo le
cambia las configuraciones, los nombres y la carpeta de salida. El módulo de T11 que usan sus
propias pruebas no se toca.

Uso:
    python scripts/t13_indices.py
"""
import importlib.util
import time
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
CODIGO_T11 = RAIZ / "scripts" / "t11_aporte_satelital.py"
SALIDA = RAIZ / "registro" / "t13"
VERSION = "T13-v1"
ESTIMADOR_ESPERADO = "T11-v2.1"  # si T11 cambia de versión, hay que revisar y volver a correr

# ---------------------------------------------------------------- configuraciones (D024)
# Un resumen por índice, una columna cada uno, todos en abr_oct.
INDICES = {
    1: ("NDVI Planet", "pl_ndvi_max_abr_oct"),
    2: ("LAI2 Planet", "pl_lai2_max_abr_oct"),
    3: ("NDVI Sentinel-2", "s2_ndvi_max_abr_oct"),
    4: ("NDWI Sentinel-2", "s2_ndwi_en_maximo_abr_oct"),
    5: ("VI6T Landsat", "ls_vi6t_mediana_abr_oct"),
}
CINCO = [col for _, col in INDICES.values()]
NDVI = ["pl_ndvi_max_abr_oct", "s2_ndvi_max_abr_oct"]
VI6T = ["ls_vi6t_mediana_abr_oct"]

CONFIGS = {n: dict(cols=[col], centrar=False) for n, (_, col) in INDICES.items()}
CONFIGS[6] = dict(cols=CINCO, centrar=False)
CONFIGS[7] = dict(cols=[c for c in CINCO if c not in NDVI], centrar=False)
CONFIGS[8] = dict(cols=[c for c in CINCO if c not in VI6T], centrar=False)

CANDIDATOS = {
    0: "media_mun__resp_grupo",
    1: "t13_c1_ndvi_planet",
    2: "t13_c2_lai2_planet",
    3: "t13_c3_ndvi_s2",
    4: "t13_c4_ndwi_s2",
    5: "t13_c5_vi6t_landsat",
    6: "t13_c6_cinco_indices",
    7: "t13_c7_cinco_sin_ndvi",
    8: "t13_c8_cinco_sin_vi6t",
}

# Signo: Δ = error(candidato) − error(frente_a); negativo = el candidato tiene menos error.
COMPARACIONES = [(n, 0, "promocion") for n in range(1, 9)] + [
    (6, 7, "aporte del NDVI: cinco frente a cinco sin NDVI"),
    (6, 8, "aporte de VI6T: cinco frente a cinco sin VI6T"),
]


def cargar_estimador():
    """Copia independiente del código de T11 con las configuraciones de T13."""
    spec = importlib.util.spec_from_file_location("t11_para_t13", CODIGO_T11)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    if m.VERSION != ESTIMADOR_ESPERADO:
        raise ValueError(f"T13 se diseñó con {ESTIMADOR_ESPERADO} y el código de T11 es {m.VERSION}; "
                         "revisar qué cambió antes de correr")
    m.CONFIGS, m.CANDIDATOS, m.COMPARACIONES = CONFIGS, CANDIDATOS, COMPARACIONES
    m.VERSION, m.SALIDA = VERSION, SALIDA
    return m


# ---------------------------------------------------------------- redundancia (sin rendimiento)
def redundancia(tabla):
    """Correlación entre los cinco índices en las 197 y en las 138. No usa el rendimiento."""
    filas = []
    entr = tabla[tabla.conjunto_origen == "ENTRENAMIENTO"]
    for poblacion, t in [("197", tabla), ("138", entr)]:
        for metodo in ["spearman", "pearson"]:
            c = t[CINCO].corr(method=metodo)
            for i, a in enumerate(CINCO):
                for b in CINCO[i + 1:]:
                    filas.append(dict(poblacion=poblacion, metodo=metodo, indice_a=a, indice_b=b,
                                      correlacion=c.loc[a, b], n=len(t)))
    return pd.DataFrame(filas)


# ---------------------------------------------------------------- orden y estabilidad de los índices
def orden_indices(oof, coefs, t11):
    """Para los cinco índices por separado (c1–c5): error por repetición en sin_respaldo (D019),
    lugar que ocupa cada índice en esa repetición y signo del coeficiente. Es descriptivo:
    la decisión es la regla de T03 frente a la referencia."""
    d = oof[(oof.fuente == "municipio") & oof.config.isin([0, *INDICES])]
    filas = []
    for (esc, rep, cfg), g in d.groupby(["escenario", "repeticion", "config"]):
        m = t11.metricas(g.real.values, g.prediccion.values)
        filas.append(dict(escenario=esc, repeticion=rep, config=cfg, MAE=m["MAE"], RMSE=m["RMSE"], R2=m["R2"]))
    r = pd.DataFrame(filas)
    ref = r[r.config == 0].set_index(["escenario", "repeticion"])
    r = r[r.config != 0].copy()
    clave = pd.MultiIndex.from_frame(r[["escenario", "repeticion"]])
    for met in ["MAE", "RMSE"]:
        r["d" + met] = r[met].values - ref[met].reindex(clave).values
        r["orden_" + met] = r.groupby(["escenario", "repeticion"])[met].rank(method="min")
    r["dR2"] = r.R2.values - ref.R2.reindex(clave).values
    r.insert(3, "indice", r.config.map({n: nombre for n, (nombre, _) in INDICES.items()}))
    r.insert(4, "candidato", r.config.map(CANDIDATOS))

    signo = (coefs[coefs.config.isin(list(INDICES))].assign(positivo=lambda x: x.coef > 0)
             .groupby(["escenario", "config"]).positivo.mean().rename("prop_coef_positivo"))
    resumen = (r.groupby(["escenario", "config", "indice", "candidato"])
               .agg(dMAE_medio=("dMAE", "mean"), dRMSE_medio=("dRMSE", "mean"), dR2_medio=("dR2", "mean"),
                    orden_MAE_medio=("orden_MAE", "mean"),
                    veces_primero_MAE=("orden_MAE", lambda s: int((s == 1).sum())),
                    veces_ultimo_MAE=("orden_MAE", lambda s: int((s == len(INDICES)).sum())),
                    orden_RMSE_medio=("orden_RMSE", "mean"),
                    veces_primero_RMSE=("orden_RMSE", lambda s: int((s == 1).sum())),
                    reps_mejoran_MAE=("dMAE", lambda s: int((s < 0).sum())))
               .reset_index()
               .join(signo, on=["escenario", "config"]))
    resumen["version"] = VERSION
    return r, resumen


# ---------------------------------------------------------------- principal
def main():
    t11 = cargar_estimador()
    tabla = pd.read_csv(t11.TABLA)
    part = pd.read_csv(t11.PARTICIONES)
    t11.revisar_datos(tabla, part)
    d = t11.preparar(tabla, part)
    t11.comprobar_referencia(d)

    SALIDA.mkdir(parents=True, exist_ok=True)
    pd.set_option("display.width", 200)

    print("\nredundancia entre los cinco índices (sin rendimiento):")
    red = redundancia(tabla)
    red.to_csv(SALIDA / "redundancia_indices_t13.csv", index=False)
    print(red[(red.poblacion == "197") & (red.metodo == "spearman")]
          .round(2).to_string(index=False))

    print(f"\ncorriendo referencia + 8 configs con el estimador {ESTIMADOR_ESPERADO}...")
    t0 = time.time()
    oof, coefs = t11.evaluar_todo(d)
    print(f"listo en {time.time() - t0:.0f} s")
    oof["estimador"] = ESTIMADOR_ESPERADO
    oof.to_csv(SALIDA / "predicciones_oof_t13.csv", index=False)
    coefs.to_csv(SALIDA / "coeficientes_t13.csv", index=False)
    res = t11.resumir(oof)
    res.to_csv(SALIDA / "metricas_t13.csv", index=False)

    print("\nalfa elegido (veces por config, ambos escenarios):")
    print(oof[oof.config > 0].drop_duplicates(["config", "escenario", "repeticion", "particion"])
          .groupby("config").alfa.value_counts().unstack(fill_value=0))
    print("\nmétricas en sin_respaldo (config 0 = referencia):")
    print(res[res.subconjunto == "sin_respaldo"].round(4).to_string(index=False))

    print("\ncomparación emparejada (bootstrap por celdas, puede tardar un poco)...")
    celda = d.drop_duplicates("ID_POLIGONO").set_index("ID_POLIGONO").celda_chirps
    comp = t11.comparaciones(oof, celda)
    comp.to_csv(SALIDA / "comparacion_emparejada_t13.csv", index=False)
    cols = ["escenario", "subconjunto", "candidato", "dMAE", "IC95_celdas_MAE_inf", "IC95_celdas_MAE_sup",
            "reps_mejoran_MAE", "dRMSE", "IC95_celdas_RMSE_sup", "reps_mejoran_RMSE", "dR2",
            "cumple_regla_MAE", "cumple_regla_RMSE"]
    print("\nfrente a la referencia, sin_respaldo (aquí se decide, D019):")
    sel = (comp.tipo == "promocion") & (comp.subconjunto == "sin_respaldo")
    print(comp.loc[sel, cols].round(4).to_string(index=False))
    print("\nablación (descriptiva), sin_respaldo:")
    sel = (comp.tipo != "promocion") & (comp.subconjunto == "sin_respaldo")
    print(comp.loc[sel, ["tipo"] + cols].round(4).to_string(index=False))
    prom = comp[comp.tipo == "promocion"]
    print("\n¿algún índice o combinación cumple la regla frente a la referencia?")
    print("  con MAE:", prom.cumple_regla_MAE.any(), "| con RMSE:", prom.cumple_regla_RMSE.any())

    print("\norden de los cinco índices por repetición (sin_respaldo; 1 = menor error):")
    por_rep, resumen = orden_indices(oof, coefs, t11)
    por_rep.to_csv(SALIDA / "orden_indices_por_repeticion_t13.csv", index=False)
    resumen.to_csv(SALIDA / "orden_indices_t13.csv", index=False)
    print(resumen.drop(columns=["candidato", "version"]).round(4).to_string(index=False))

    print("\ndesgloses del error (T03 §4 y §4 bis)...")
    des = t11.desgloses(oof, part)
    des.to_csv(SALIDA / "desglose_error_t13.csv", index=False)
    print(f"  {len(des)} filas en desglose_error_t13.csv")

    print("\nsensibilidad sin las 24 parcelas con alerta de contorno (T03 §4 bis):")
    sens = t11.sensibilidad_sin_alerta(oof)
    sens.to_csv(SALIDA / "sensibilidad_sin_alerta_t13.csv", index=False)
    cols = ["escenario", "candidato", "dMAE", "dMAE_sin24", "orden_MAE", "orden_MAE_sin24",
            "dRMSE", "dRMSE_sin24", "orden_RMSE", "orden_RMSE_sin24"]
    print(sens.loc[sens.subconjunto == "sin_respaldo", cols].round(4).to_string(index=False))


if __name__ == "__main__":
    main()