"""Datos y procedimiento de T08 para la app, sin Streamlit (lo usan app.py, herramientas/preparar_datos.py y tests/frontend/test_app.py).

La app lee primero el paquete compacto `datos_app/` (parquet, ~1 MB) que arma `herramientas/preparar_datos.py`. Si no existe, lee
las fuentes originales del repo (dataset del reto, T08, T03 y T04), que es más lento.
"""
import os
import tempfile
import zipfile
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

AQUI = Path(__file__).resolve().parent
PAQ = AQUI / "datos_app"
MODELOS = ["media_mun__resp_grupo", "mediana_mun__resp_grupo"]
TEMPORADA = ("2025-03-01", "2025-10-31")
COLUMNAS_INDICES = ["ndvi_promedio", "evi_promedio", "lai_promedio"]
PALETA = [(2.0, (217, 164, 65)), (3.8, (140, 203, 94)), (5.6, (47, 224, 160))]   # t/ha: paja -> verde -> menta


def color_rgb(v):
    """Color de la escala de rendimiento (t/ha) como (r, g, b) 0-255."""
    (a, ca), (b, cb), (c, cc) = PALETA
    x, y, k = (ca, cb, (v - a) / (b - a)) if v <= b else (cb, cc, (v - b) / (c - b))
    k = float(np.clip(k, 0, 1))
    return tuple(int(x[i] + (y[i] - x[i]) * k) for i in range(3))


# ---------------------------------------------------------------- rutas de las fuentes originales
def raiz():
    """Raíz del repo: la primera carpeta hacia arriba con el dataset, `registro/` o `.git`."""
    for c in [AQUI, *AQUI.parents]:
        if any((c / m).exists() for m in ("DATASET_RETO_AGRO_2026", "registro", ".git")):
            return c
    return AQUI


def buscar(env, *candidatas):
    if os.environ.get(env):
        return Path(os.environ[env])
    r = raiz()
    for c in candidatas:
        if (r / c).exists():
            return r / c
    return None


CLAVE_DATASET = "ID_area_rendimiento_70_30_Reto_AgroCebada.csv"


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
            "t08": buscar("AGRO_T08", "registro/t08", "registro/t03", "entregas/T08"),
            "t03": buscar("AGRO_T03", "registro/t03", "entregas/T03"),
            "t04": buscar("AGRO_T04", "registro/t04/clima_parcela_mes.csv", "entregas/T04/clima_parcela_mes.csv")}


def usar_paquete():
    return (PAQ / "parcelas.parquet").exists() and not os.environ.get("AGRO_SIN_PAQUETE")


def hay_datos():
    return usar_paquete() or rutas()["datos"] is not None


# ---------------------------------------------------------------- lectura de las fuentes originales
def leer_parcelas(datos):
    datos = Path(datos)
    cat = pd.read_csv(datos / "ID_area_rendimiento_70_30_Reto_AgroCebada.csv", encoding="utf-8-sig")
    cat = cat.drop(columns=[c for c in cat.columns if c.startswith("Unnamed")])
    with tempfile.TemporaryDirectory() as tmp, zipfile.ZipFile(datos / "Parcelas_Reto_AGC_CONJUNTO_70_30.zip") as z:
        z.extractall(tmp)
        geo = gpd.read_file(Path(tmp) / "Parcelas_Reto_AGC_CONJUNTO.shp").to_crs(4326)
    geo = geo.rename(columns={"ID_POLIGON": "ID_POLIGONO", "Cultivo": "grupo_registro", "Municipio": "municipio"})
    d = cat.merge(geo[["ID_POLIGONO", "municipio", "grupo_registro", "Estado", "geometry"]], on="ID_POLIGONO",
                  validate="one_to_one").rename(columns={"RENDIMIENTO_T_HA": "real"}).set_index("ID_POLIGONO")
    return con_centroides(gpd.GeoDataFrame(d, geometry="geometry", crs=4326))


def con_centroides(d):
    c = d.geometry.to_crs(6372).centroid.to_crs(4326)       # centroides en proyección métrica de México
    return d.assign(lon_c=c.x, lat_c=c.y)


def leer_series(datos):
    datos = Path(datos)
    usar = ["ID_POLIGONO", "fecha_captura", "sensor", "porcentaje_nubosidad", *COLUMNAS_INDICES]
    x = pd.concat([pd.read_csv(datos / "Conjunto_datos_BASICO_AgroCebada2026.csv", usecols=usar),
                   pd.read_csv(datos / "Conjunto_datos_PRO_AgroCebada.csv", usecols=usar)], ignore_index=True)
    x["fecha"] = pd.to_datetime(x.fecha_captura, format="%d/%m/%Y")
    x = x[x.sensor.isin(["Sentinel-2", "Planet"]) & (x.porcentaje_nubosidad <= 20) & x.fecha.between(*TEMPORADA)]
    return x[["ID_POLIGONO", "fecha", "sensor", *COLUMNAS_INDICES]].reset_index(drop=True)


def leer_clima(t04):
    c = pd.read_csv(t04)
    c = c[c.periodo.between("2025-03", "2025-10")]
    return c.pivot_table(index=["id_parcela", "periodo"], columns="variable", values="media_ponderada").reset_index()


def leer_validacion(t08):
    partes = [pd.read_csv(Path(t08) / f"predicciones_oof_referencias_{m}.csv") for m in MODELOS
              if (Path(t08) / f"predicciones_oof_referencias_{m}.csv").exists()]
    return pd.concat(partes, ignore_index=True) if partes else None


def leer_oficial(t08):
    f = Path(t08) / "predicciones_59_referencias.csv"
    return pd.read_csv(f) if f.exists() else None


def leer_soporte(t03):
    f = Path(t03) / "soporte_parcelas.csv"
    return pd.read_csv(f).set_index("ID_POLIGONO") if f.exists() else None


# ---------------------------------------------------------------- lo que usa la app (paquete o fuentes)
def parcelas():
    if usar_paquete():
        return gpd.read_parquet(PAQ / "parcelas.parquet")
    return leer_parcelas(rutas()["datos"])


def series():
    if usar_paquete():
        return pd.read_parquet(PAQ / "series.parquet")
    return leer_series(rutas()["datos"])


def clima():
    if usar_paquete():
        f = PAQ / "clima.parquet"
        return pd.read_parquet(f) if f.exists() else None
    t04 = rutas()["t04"]
    return leer_clima(t04) if t04 else None


def validacion(modelo, municipios):
    if usar_paquete():
        f = PAQ / "validacion.parquet"
        o = pd.read_parquet(f) if f.exists() else None
    else:
        t08 = rutas()["t08"]
        o = leer_validacion(t08) if t08 else None
    if o is None or not (o.candidato == modelo).any():
        return None
    o = o[o.candidato == modelo].copy()
    o["municipio"] = o.ID_POLIGONO.map(municipios)
    return o.assign(ae=(o.prediccion - o.real).abs(), e=o.prediccion - o.real)


def oficial(modelo):
    if usar_paquete():
        f = PAQ / "oficial_59.csv"
        o = pd.read_csv(f) if f.exists() else None
    else:
        t08 = rutas()["t08"]
        o = leer_oficial(t08) if t08 else None
    return None if o is None else o[o.candidato == modelo].set_index("ID_POLIGONO").prediccion


def soporte():
    if usar_paquete():
        f = PAQ / "soporte.parquet"
        return pd.read_parquet(f) if f.exists() else None
    t03 = rutas()["t03"]
    return leer_soporte(t03) if t03 else None


def elevaciones():
    f = AQUI / "datos_estaticos" / "elevacion_parcelas.csv"
    return pd.read_csv(f).set_index("ID_POLIGONO").elev_max_m if f.exists() else None


# ---------------------------------------------------------------- procedimiento de T08
def estadistico(modelo):
    return np.median if modelo.startswith("mediana") else np.mean


def predecir(d, modelo, ocultar=None):
    """Mismo procedimiento que T08: estadístico del municipio -> grupo de registro -> global, con las parcelas con
    cosecha. `ocultar` quita un municipio del entrenamiento (para mostrar el caso de información insuficiente)."""
    f = estadistico(modelo)
    tr, te = d[d.CONJUNTO == "ENTRENAMIENTO"], d[d.CONJUNTO == "PREDICCION"]
    if ocultar:
        tr = tr[tr.municipio != ocultar]
    mun, grp = tr.groupby("municipio").real.agg(f), tr.groupby("grupo_registro").real.agg(f)
    p = te.municipio.map(mun)
    fuente = np.where(p.notna(), "municipio", np.where(te.grupo_registro.map(grp).notna(), "grupo", "global"))
    p = p.fillna(te.grupo_registro.map(grp)).fillna(f(tr.real))
    n_mun = te.municipio.map(tr.municipio.value_counts()).fillna(0).astype(int)
    return pd.DataFrame({"municipio": te.municipio, "prediccion": p, "fuente": fuente, "n_municipio": n_mun,
                         "area_ha": te.AREA_HA})


def metricas(o):
    """MAE, RMSE, sesgo y R² promediados por repetición (igual que metricas_referencias.csv de T08)."""
    reps = []
    for _, g in o.groupby("repeticion"):
        reps.append(dict(MAE=g.ae.mean(), RMSE=np.sqrt((g.e ** 2).mean()), sesgo=g.e.mean(),
                         R2=1 - (g.e ** 2).sum() / ((g.real - g.real.mean()) ** 2).sum()))
    return pd.DataFrame(reps).mean()


def validacion_dejando_uno(d, modelo):
    """Validación rápida para datos subidos: cada parcela con cosecha se estima sin ella misma (mismo respaldo)."""
    f = estadistico(modelo)
    tr = d[d.CONJUNTO == "ENTRENAMIENTO"]
    y = tr.real.to_numpy(float)
    filas = []
    for i, (pid, r) in enumerate(tr.iterrows()):
        resto = tr.drop(index=pid)
        m = resto.real[resto.municipio == r.municipio]
        g = resto.real[resto.grupo_registro == r.grupo_registro]
        p, fuente = ((f(m), "municipio") if len(m) else (f(g), "grupo") if len(g) else (f(resto.real), "global"))
        filas.append((pid, r.municipio, y[i], p, fuente))
    o = pd.DataFrame(filas, columns=["ID_POLIGONO", "municipio", "real", "prediccion", "fuente"])
    return o.assign(ae=(o.prediccion - o.real).abs(), e=o.prediccion - o.real, repeticion=1)
