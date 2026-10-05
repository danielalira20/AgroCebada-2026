"""T03 · Evaluación común: particiones por ID y diagnóstico de soporte 59 vs 138.

Uso (desde la raíz del repositorio, con el entorno de requirements.txt):
    python scripts/t03_evaluacion.py --datos RUTA/DATASET_RETO_AGRO_2026

El paquete original de FIRA no se versiona: se pasa con --datos (fuera del
repositorio o bajo data/raw/). --salida es opcional; por omisión escribe en
registro/t03/.

Genera en --salida:
    particiones.csv          138 IDs etiquetados × 5 repeticiones, con partición del
                             escenario principal, del escenario espacial y municipio.
    soporte_parcelas.csv     197 IDs: soporte territorial, espacial y satelital.
                             No usa rendimientos salvo para contar etiquetas por municipio.
    soporte_resumen.csv      Comparación PREDICCION frente a ENTRENAMIENTO.

Dependencias: pandas, numpy, geopandas, rasterio, scikit-learn, scipy (fijadas en requirements.txt).
"""
import argparse
import warnings
import tempfile
import zipfile
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from rasterio.features import rasterize
from scipy.spatial import cKDTree
from sklearn.model_selection import StratifiedKFold

warnings.filterwarnings("ignore", message="The least populated class")

SEMILLAS = [20261001, 20261002, 20261003, 20261004, 20261005]
N_PARTICIONES = 5
RAIZ = Path(__file__).resolve().parents[1]
SALIDA_POR_OMISION = RAIZ / "registro" / "t03"
CORTE_INI, CORTE_FIN = "2025-04-01", "2025-10-31"  # corte provisional; T03 lo valida
VENTANA_CULTIVO_INI = "2025-06-01"                   # ventana candidata (O7)


def cargar(datos: Path, tmp: Path):
    with zipfile.ZipFile(datos / "Parcelas_Reto_AGC_CONJUNTO_70_30.zip") as z:
        z.extractall(tmp)
    cat = pd.read_csv(datos / "ID_area_rendimiento_70_30_Reto_AgroCebada.csv", encoding="utf-8-sig")
    cat = cat.drop(columns=[c for c in cat.columns if c.startswith("Unnamed")])
    geo = gpd.read_file(tmp / "Parcelas_Reto_AGC_CONJUNTO.shp").rename(columns={"ID_POLIGON": "ID_POLIGONO"})
    g = geo.merge(cat, on="ID_POLIGONO", suffixes=("_shp", ""), validate="one_to_one")
    assert len(g) == 197 and (g.CONJUNTO == g.CONJUNTO_shp).all()
    g = g.rename(columns={"Cultivo": "grupo_registro"})
    return g


def celdas_chirps(g, datos: Path, tmp: Path):
    """Celda CHIRPS del centroide y número de celdas que toca cada polígono."""
    zp = datos / "Reto_AgroCebada_CHIRPS_Precipitacion_2022_2025.zip"
    nombre = "Reto_AgroCebada_CHIRPS_Precipitacion_2022_2025/Precipitacion_mensual/2025/PREC_2025_07.tif"
    with zipfile.ZipFile(zp) as z:
        z.extract(nombre, tmp)
    with rasterio.open(tmp / nombre) as r:
        T, shape = r.transform, (r.height, r.width)
    cen = g.to_crs(6372).geometry.centroid.to_crs(4326)
    filas, cols = rasterio.transform.rowcol(T, cen.x.values, cen.y.values)
    celda = [f"{a}_{b}" for a, b in zip(filas, cols)]
    n_tocadas = [int(rasterize([(geom, 1)], out_shape=shape, transform=T, all_touched=True).sum())
                 for geom in g.geometry]
    return celda, n_tocadas


def particiones(g):
    t = g[g.CONJUNTO == "ENTRENAMIENTO"].sort_values("ID_POLIGONO").reset_index(drop=True)
    filas = []
    for rep, semilla in enumerate(SEMILLAS, start=1):
        # Escenario principal: municipio conocido, estratificado por municipio.
        principal = np.empty(len(t), int)
        skf = StratifiedKFold(N_PARTICIONES, shuffle=True, random_state=semilla)
        for k, (_, te) in enumerate(skf.split(t, t.Municipio)):
            principal[te] = k
        # Escenario espacial: celdas CHIRPS completas asignadas a particiones.
        rng = np.random.RandomState(semilla)
        celdas = np.array(sorted(t.celda_chirps.unique()))
        rng.shuffle(celdas)
        # Asignación codiciosa para equilibrar tamaños de partición.
        tam = t.celda_chirps.value_counts()
        carga = np.zeros(N_PARTICIONES)
        asign = {}
        for c in sorted(celdas, key=lambda c: -tam[c]):
            k = int(np.argmin(carga))
            asign[c] = k
            carga[k] += tam[c]
        espacial = t.celda_chirps.map(asign).values
        for i, r in t.iterrows():
            filas.append(dict(ID_POLIGONO=r.ID_POLIGONO, repeticion=rep, semilla=semilla,
                              particion_principal=int(principal[i]), particion_espacial=int(espacial[i]),
                              celda_chirps=r.celda_chirps, municipio=r.Municipio,
                              grupo_registro=r.grupo_registro))
    return pd.DataFrame(filas)


def cobertura_satelital(datos: Path):
    """Capturas con dato (nubosidad < 100) y despejadas (≤ 20 %) por parcela y sensor."""
    b = pd.read_csv(datos / "Conjunto_datos_BASICO_AgroCebada2026.csv", encoding="utf-8-sig",
                    usecols=["ID_POLIGONO", "fecha_captura", "sensor", "ndvi_promedio", "vi6t_promedio",
                             "porcentaje_nubosidad"])
    p = pd.read_csv(datos / "Conjunto_datos_PRO_AgroCebada.csv", encoding="utf-8-sig",
                    usecols=["ID_POLIGONO", "fecha_captura", "sensor", "ndvi_promedio", "porcentaje_nubosidad"])
    d = pd.concat([b, p], ignore_index=True)
    d["fecha"] = pd.to_datetime(d.fecha_captura, format="%d/%m/%Y")
    d["valor"] = d.ndvi_promedio.where(d.sensor != "Landsat", d.vi6t_promedio)
    d = d[(d.fecha >= CORTE_INI) & (d.fecha <= CORTE_FIN) & d.valor.notna()]
    abrev = {"Sentinel-2": "s2", "Planet": "pl", "Landsat": "ls"}
    out = {}
    for sensor, x in d.groupby("sensor"):
        s = abrev[sensor]
        desp = x[x.porcentaje_nubosidad <= 20]
        out[f"{s}_capturas_con_dato"] = x.groupby("ID_POLIGONO").size()
        out[f"{s}_capturas_despejadas"] = desp.groupby("ID_POLIGONO").size()
        meses = desp.assign(m=desp.fecha.dt.month).groupby("ID_POLIGONO").m.nunique()
        out[f"{s}_meses_sin_despejada"] = 7 - meses
        cult = desp[desp.fecha >= VENTANA_CULTIVO_INI].sort_values("fecha")
        hueco = cult.groupby("ID_POLIGONO").fecha.apply(
            lambda f: f.diff().dt.days.max() if len(f) > 1 else np.nan)
        out[f"{s}_hueco_max_dias_jun_oct"] = hueco
    return pd.DataFrame(out)


def soporte(g):
    gm = g.to_crs(6372)
    xy = np.c_[gm.geometry.centroid.x, gm.geometry.centroid.y]
    es_tr = (g.CONJUNTO == "ENTRENAMIENTO").values
    arbol = cKDTree(xy[es_tr])
    ids_tr = g.ID_POLIGONO.values[es_tr]
    d, idx = arbol.query(xy, k=2)
    # Para una parcela etiquetada, su vecino más cercano no puede ser ella misma.
    propio = ids_tr[idx[:, 0]] == g.ID_POLIGONO.values
    dist = np.where(propio, d[:, 1], d[:, 0])
    n_mun = g[es_tr].Municipio.value_counts()
    n_grp = g[es_tr].grupo_registro.value_counts()
    celdas_tr = g[es_tr].celda_chirps.value_counts()
    s = pd.DataFrame({
        "ID_POLIGONO": g.ID_POLIGONO, "CONJUNTO": g.CONJUNTO, "municipio": g.Municipio,
        "estado": g.Estado, "grupo_registro": g.grupo_registro, "area_ha": g.AREA_HA,
        "etiquetas_municipio": g.Municipio.map(n_mun).fillna(0).astype(int),
        "etiquetas_grupo_registro": g.grupo_registro.map(n_grp).fillna(0).astype(int),
        "dist_etiquetada_mas_cercana_m": dist.round(1),
        "celda_chirps": g.celda_chirps, "celdas_chirps_tocadas": g.celdas_tocadas,
        "etiquetadas_en_misma_celda": g.celda_chirps.map(celdas_tr).fillna(0).astype(int),
    })
    # Excluir a la propia parcela etiquetada del conteo de su municipio y su celda.
    s.loc[es_tr, "etiquetas_municipio"] -= 1
    s.loc[es_tr, "etiquetas_grupo_registro"] -= 1
    s.loc[es_tr, "etiquetadas_en_misma_celda"] -= 1
    return s


def resumen(s):
    num = [c for c in s.columns if s[c].dtype.kind in "if" and c != "area_ha"] + ["area_ha"]
    filas = []
    for c in num:
        for conj, x in s.groupby("CONJUNTO"):
            filas.append(dict(variable=c, conjunto=conj, n=x[c].notna().sum(), minimo=x[c].min(),
                              p25=x[c].quantile(.25), mediana=x[c].median(), p75=x[c].quantile(.75),
                              maximo=x[c].max()))
    r = pd.DataFrame(filas).round(2)
    extra = pd.DataFrame([
        dict(variable="pred_en_municipio_sin_etiquetas", conjunto="PREDICCION",
             n=int(((s.CONJUNTO == "PREDICCION") & (s.etiquetas_municipio == 0)).sum())),
        dict(variable="pred_en_municipio_con_1_etiqueta", conjunto="PREDICCION",
             n=int(((s.CONJUNTO == "PREDICCION") & (s.etiquetas_municipio == 1)).sum())),
        dict(variable="pred_en_celda_sin_etiquetadas", conjunto="PREDICCION",
             n=int(((s.CONJUNTO == "PREDICCION") & (s.etiquetadas_en_misma_celda == 0)).sum())),
    ])
    return pd.concat([r, extra], ignore_index=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--datos", type=Path, required=True)
    ap.add_argument("--salida", type=Path, default=SALIDA_POR_OMISION)
    a = ap.parse_args()
    a.salida.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        g = cargar(a.datos, tmp)
        g["celda_chirps"], g["celdas_tocadas"] = celdas_chirps(g, a.datos, tmp)
    part = particiones(g)
    part.to_csv(a.salida / "particiones.csv", index=False)
    s = soporte(g).merge(cobertura_satelital(a.datos), left_on="ID_POLIGONO", right_index=True, how="left")
    s.to_csv(a.salida / "soporte_parcelas.csv", index=False)
    r = resumen(s)
    r.to_csv(a.salida / "soporte_resumen.csv", index=False)

    # Comprobaciones mínimas que el revisor puede repetir.
    assert part.groupby("repeticion").ID_POLIGONO.nunique().eq(138).all()
    assert not part.duplicated(["ID_POLIGONO", "repeticion"]).any()
    print("particiones.csv:", part.shape, "| tamaño de partición principal por repetición:",
          part.groupby(["repeticion", "particion_principal"]).size().unstack().to_dict("index"))
    print("tamaño de partición espacial por repetición:",
          part.groupby(["repeticion", "particion_espacial"]).size().unstack().to_dict("index"))
    print(r.to_string(index=False))


if __name__ == "__main__":
    main()
