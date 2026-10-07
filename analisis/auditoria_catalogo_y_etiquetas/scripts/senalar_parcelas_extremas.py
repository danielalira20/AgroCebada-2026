"""Señala las parcelas cuyo rendimiento se aleja mucho del de su municipio, con su contexto.

Uso (después de construir_catalogo.py, con el mismo entorno):
    python scripts/senalar_parcelas_extremas.py

Lee tablas/catalogo_parcelas.csv y escribe en tablas/:
    desviacion_municipal_por_parcela.csv   138 filas: desviación, si es extrema y su contexto.
    desviacion_por_tamano.csv              Desviación según el tamaño de la parcela.

«Extrema» es una parcela a más de 1 t/ha del promedio de las demás conocidas de su municipio.
Señalar una parcela no la excluye ni la corrige. No entrena ningún modelo: solo usa promedios.
"""
import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyproj

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from cruzar_contorno_y_rendimiento import desviacion_municipal  # noqa: E402

CARPETA = Path(__file__).resolve().parents[1]
TABLAS_POR_OMISION = CARPETA / "tablas"

UMBRAL_EXTREMA_T_HA = 1.0
RADIO_VECINAS_M = 1000
MINIMO_PARA_DESGLOSE = 10
TRAMOS = [("menos de 2 ha", 0, 2), ("2 a 5 ha", 2, 5), ("mas de 5 ha", 5, np.inf)]


def guardar(tabla, ruta):
    tabla.to_csv(ruta, index=False, encoding="utf-8-sig", lineterminator="\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tablas", type=Path, default=TABLAS_POR_OMISION)
    a = ap.parse_args()

    catalogo = pd.read_csv(a.tablas / "catalogo_parcelas.csv", dtype=str, keep_default_na=False,
                           encoding="utf-8-sig")
    k = catalogo[catalogo.rendimiento_t_ha != ""].reset_index(drop=True)
    assert len(k) == 138, "Se esperaban 138 parcelas con rendimiento"
    y = k.rendimiento_t_ha.astype(float)
    k["desviacion"] = desviacion_municipal(k)
    k["n_municipio"] = y.groupby(k.municipio).transform("count")
    k["promedio_demas"] = y - k.desviacion
    k["extrema"] = np.where(k.desviacion.isna(), "",
                            np.where(k.desviacion > UMBRAL_EXTREMA_T_HA, "alta",
                                     np.where(k.desviacion < -UMBRAL_EXTREMA_T_HA, "baja", "no")))

    # Vecinas conocidas: distancia geodésica entre centros.
    geod = pyproj.Geod(ellps="WGS84")
    lon = k.centroide_lon.astype(float).values
    lat = k.centroide_lat.astype(float).values
    n = len(k)
    dist = np.full((n, n), np.inf)
    for i in range(n):
        for j in range(i + 1, n):
            dist[i, j] = dist[j, i] = geod.inv(lon[i], lat[i], lon[j], lat[j])[2]
    cercana = dist.argmin(axis=1)
    dentro = dist < RADIO_VECINAS_M
    yv = y.values
    promedio_cerca = [yv[dentro[i]].mean() if dentro[i].any() else np.nan for i in range(n)]

    por_parcela = pd.DataFrame({
        "id_parcela": k.id_parcela, "municipio": k.municipio, "cultivo_origen": k.cultivo_origen,
        "rendimiento_t_ha": k.rendimiento_t_ha, "conocidas_en_municipio": k.n_municipio,
        "promedio_demas_municipio": k.promedio_demas.round(3), "desviacion_municipal": k.desviacion.round(3),
        "extrema": k.extrema, "area_ha_origen": k.area_ha_origen,
        "contorno_categoria": k.contorno_categoria,
        "contorno_angosta_o_muy_pequena": k.contorno_angosta_o_muy_pequena,
        "conocida_mas_cercana": k.id_parcela.values[cercana],
        "distancia_conocida_mas_cercana_m": dist.min(axis=1).round(0).astype(int),
        "rendimiento_conocida_mas_cercana": yv[cercana],
        "conocidas_a_menos_de_1_km": dentro.sum(axis=1),
        "promedio_conocidas_a_menos_de_1_km": np.round(promedio_cerca, 3),
    })
    guardar(por_parcela, a.tablas / "desviacion_municipal_por_parcela.csv")

    # Desviación según el tamaño, en los municipios con suficientes parcelas y en conjunto.
    k["area"] = k.area_ha_origen.astype(float)
    con = k[k.desviacion.notna()]
    grandes = [m for m, c in con.municipio.value_counts().items() if c >= MINIMO_PARA_DESGLOSE]
    filas = []
    for nombre, parte in [(m, con[con.municipio == m]) for m in sorted(grandes, key=lambda m: -(con.municipio == m).sum())] + [("todos", con)]:
        for tramo, desde, hasta in TRAMOS:
            g = parte[(parte.area >= desde) & (parte.area < hasta)]
            ga = g[g.contorno_categoria == "A"]
            filas.append(dict(municipio=nombre, tramo_area=tramo, parcelas=len(g),
                              desviacion_media=round(g.desviacion.mean(), 3) if len(g) else "",
                              desviacion_mediana=round(g.desviacion.median(), 3) if len(g) else "",
                              alejamiento_medio=round(g.desviacion.abs().mean(), 3) if len(g) else "",
                              extremas_altas=int((g.extrema == "alta").sum()),
                              extremas_bajas=int((g.extrema == "baja").sum()),
                              parcelas_en_a=len(ga),
                              desviacion_media_en_a=round(ga.desviacion.mean(), 3) if len(ga) else ""))
    por_tamano = pd.DataFrame(filas)
    guardar(por_tamano, a.tablas / "desviacion_por_tamano.csv")

    pd.set_option("display.width", 250)
    print("Parcelas extremas:")
    print(por_parcela[por_parcela.extrema.isin(["alta", "baja"])].sort_values("desviacion_municipal").to_string(index=False))
    print("\nSin desviación municipal (únicas conocidas de su municipio):")
    print(por_parcela[por_parcela.extrema == ""][["id_parcela", "municipio", "rendimiento_t_ha", "conocida_mas_cercana",
                                                   "distancia_conocida_mas_cercana_m", "rendimiento_conocida_mas_cercana"]].to_string(index=False))
    print()
    print(por_tamano.to_string(index=False))


if __name__ == "__main__":
    main()
