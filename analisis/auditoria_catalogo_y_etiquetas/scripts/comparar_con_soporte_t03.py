"""Compara el diagnóstico de soporte de esta auditoría con el de T03, columna por columna.

Uso (después de diagnosticar_soporte.py, con el mismo entorno):
    python scripts/comparar_con_soporte_t03.py --datos RUTA/DATASET_RETO_AGRO_2026

--t03 es opcional: por omisión busca registro/t03/soporte_parcelas.csv en la raíz del repositorio.

Escribe en tablas/:
    comparacion_con_t03.csv               Una fila por columna de la tabla de T03.
    comparacion_con_t03_por_parcela.csv   Parcelas donde un conteo o una categoría no coincide.
    huellas_archivos_leidos_comparacion.csv

Cuando una columna se define distinto en cada tabla, el script repite aquí la definición de T03
para comprobar que la diferencia se debe a la definición y no a un error. No modifica nada de T03.
"""
import argparse
import hashlib
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from rasterio.features import rasterize
from scipy.spatial import cKDTree

CARPETA = Path(__file__).resolve().parents[1]
TABLAS_POR_OMISION = CARPETA / "tablas"
T03_POR_OMISION = CARPETA.parents[1] / "registro" / "t03" / "soporte_parcelas.csv"

SHAPEFILE = "Parcelas_Reto_AGC_CONJUNTO_70_30/Parcelas_Reto_AGC_CONJUNTO.shp"
TOLERANCIA = 0.05
SENSORES = {"s2": ("s2", "Sentinel-2", "ndvi_promedio"), "pl": ("planet", "Planet", "ndvi_promedio"),
            "ls": ("landsat", "Landsat", "vi6t_promedio")}


def huella(ruta: Path) -> str:
    """Huella del contenido sin los retornos de carro, para que no dependa de si Git guardó
    el archivo con fin de línea de Windows o de Mac/Linux."""
    return hashlib.sha256(ruta.read_bytes().replace(b"\r", b"")).hexdigest()


def reproducir_t03(datos: Path, ids, conocida):
    """Repite las definiciones de T03 que difieren de las de esta auditoría."""
    g = gpd.read_file(datos / SHAPEFILE, encoding="utf-8").set_index("ID_POLIGON").loc[ids]
    rep = pd.DataFrame(index=pd.Index(ids, name="id_parcela"))

    # Distancia entre centros medida en la proyección plana EPSG:6372, con el centro calculado ahí.
    centros = g.geometry.to_crs(6372).centroid
    xy = np.c_[centros.x, centros.y]
    arbol = cKDTree(xy[conocida])
    d, idx = arbol.query(xy, k=2)
    propio = np.array(ids)[conocida][idx[:, 0]] == np.array(ids)
    rep["dist_etiquetada_mas_cercana_m"] = np.where(propio, d[:, 1], d[:, 0]).round(1)

    # Celda del centro, y celdas tocadas contando también las que el contorno solo roza.
    ruta = sorted(datos.rglob("PREC_2025_07.tif"))[0]
    with rasterio.open(ruta) as r:
        t, forma = r.transform, (r.height, r.width)
    c4326 = centros.to_crs(4326)
    filas, cols = rasterio.transform.rowcol(t, c4326.x.values, c4326.y.values)
    rep["celda_chirps"] = [f"{a}_{b}" for a, b in zip(filas, cols)]
    rep["celdas_chirps_tocadas"] = [int(rasterize([(geom, 1)], out_shape=forma, transform=t, all_touched=True).sum())
                                    for geom in g.geometry]
    en_celda = rep.celda_chirps[conocida].value_counts()
    rep["etiquetadas_en_misma_celda"] = rep.celda_chirps.map(en_celda).fillna(0).astype(int) - conocida.astype(int)

    # Hueco más largo entre observaciones con nubosidad de 20 % o menos, de junio a octubre, sin contar los extremos.
    col = ["ID_POLIGONO", "fecha_captura", "sensor", "porcentaje_nubosidad"]
    b = pd.read_csv(datos / "Conjunto_datos_BASICO_AgroCebada2026.csv", encoding="utf-8-sig",
                    usecols=col + ["ndvi_promedio", "vi6t_promedio"])
    p = pd.read_csv(datos / "Conjunto_datos_PRO_AgroCebada.csv", encoding="utf-8-sig", usecols=col + ["ndvi_promedio"])
    x = pd.concat([b, p], ignore_index=True)
    x["fecha"] = pd.to_datetime(x.fecha_captura, format="%d/%m/%Y")
    for abrev, (_, sensor, indice) in SENSORES.items():
        s = x[(x.sensor == sensor) & x[indice].notna() & (x.fecha >= "2025-06-01") & (x.fecha <= "2025-10-31")
              & (x.porcentaje_nubosidad <= 20)].sort_values("fecha")
        rep[f"{abrev}_hueco_max_dias_jun_oct"] = s.groupby("ID_POLIGONO").fecha.apply(
            lambda f: f.diff().dt.days.max() if len(f) > 1 else np.nan).reindex(ids)
    return rep


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--datos", type=Path, required=True, help="Carpeta DATASET_RETO_AGRO_2026")
    ap.add_argument("--t03", type=Path, default=T03_POR_OMISION, help="Tabla soporte_parcelas.csv de T03")
    ap.add_argument("--tablas", type=Path, default=TABLAS_POR_OMISION)
    a = ap.parse_args()

    cat = pd.read_csv(a.tablas / "catalogo_parcelas.csv", dtype=str, keep_default_na=False, encoding="utf-8-sig")
    sop = pd.read_csv(a.tablas / "soporte_por_parcela.csv", dtype={"escalon_etiqueta_municipio": str},
                      keep_default_na=False, encoding="utf-8-sig")
    t03 = pd.read_csv(a.t03, encoding="utf-8-sig")
    ids = list(cat.id_parcela)
    assert set(t03.ID_POLIGONO) == set(ids) and len(t03) == 197, "La tabla de T03 no tiene las mismas 197 parcelas"
    t03 = t03.set_index("ID_POLIGONO").loc[ids]
    mia = sop.set_index("id_parcela").loc[ids]
    mia["cultivo_origen"] = cat.set_index("id_parcela").cultivo_origen
    mia["estado"] = cat.set_index("id_parcela").estado
    mia["area_num"] = mia.area_ha_origen.astype(float)
    conocida = (cat.rendimiento_t_ha != "").values
    rep = reproducir_t03(a.datos, ids, conocida)

    # (columna de T03, columna de esta auditoría, misma definición, explicación)
    pares = [
        ("CONJUNTO", "conjunto_origen", "si", "Mismo dato del dataset."),
        ("municipio", "municipio", "si", "Mismo dato del shapefile."),
        ("estado", "estado", "si", "Mismo dato del shapefile."),
        ("grupo_registro", "cultivo_origen", "si",
         "Mismo dato (campo Cultivo del shapefile). Cambia el nombre: T03 lo llama grupo de registro; aquí se guarda como escritura original, sin afirmar cómo se registró."),
        ("area_ha", "area_num", "si", "Mismo dato del CSV de rendimiento."),
        ("etiquetas_municipio", "conocidas_en_municipio", "si",
         "Parcelas con rendimiento en el mismo municipio, sin contar a la propia."),
        ("etiquetas_grupo_registro", "", "sin equivalente",
         "Parcelas con rendimiento de la misma escritura. Esta auditoría no lo calcula como medida de soporte."),
        ("dist_etiquetada_mas_cercana_m", "distancia_centros_m", "no",
         "T03 mide sobre la proyección plana EPSG:6372; esta auditoría mide sobre el elipsoide (geodésica). La proyección encoge las distancias de esta zona cerca de 0.3 %."),
        ("celda_chirps", "celda_clima_principal", "no",
         "T03 toma la celda donde cae el centro del contorno; esta auditoría, la celda donde cae la mayor parte de su superficie."),
        ("celdas_chirps_tocadas", "celdas_clima_tocadas", "no",
         "T03 cuenta también las celdas que el contorno solo roza; esta auditoría cuenta las celdas con alguna superficie del contorno."),
        ("etiquetadas_en_misma_celda", "conocidas_que_comparten_celda", "no",
         "T03 cuenta las parcelas con rendimiento cuyo centro cae en la misma celda; esta auditoría, las que comparten al menos una celda tocada. La segunda nunca es menor."),
    ]
    for abrev, (mio, _, _) in SENSORES.items():
        pares += [
            (f"{abrev}_capturas_con_dato", f"{mio}_observaciones_con_dato", "si",
             "Observaciones con índice no vacío del 1 de abril al 31 de octubre de 2025."),
            (f"{abrev}_capturas_despejadas", "", "sin equivalente",
             "Observaciones con nubosidad de 20 % o menos. Esta auditoría no aplica corte de nubosidad, porque el plan lo deja como candidato."),
            (f"{abrev}_meses_sin_despejada", "", "sin equivalente",
             "Meses sin observación con nubosidad de 20 % o menos. Misma razón."),
            (f"{abrev}_hueco_max_dias_jun_oct", f"{mio}_hueco_maximo_dias", "no",
             "T03 mide el hueco entre observaciones con nubosidad de 20 % o menos y no cuenta el tramo antes de la primera ni después de la última; esta auditoría usa todas las observaciones con dato y sí cuenta esos tramos."),
        ]
    assert {p[0] for p in pares} == set(t03.columns), "Hay columnas de T03 sin revisar"

    filas, detalle = [], []
    for col_t03, col_mia, misma, explicacion in pares:
        f = dict(columna_t03=col_t03, columna_auditoria=col_mia.replace("area_num", "area_ha_origen"),
                 misma_definicion=misma, parcelas_comparadas="", parcelas_iguales="", diferencia_mediana="",
                 diferencia_maxima="", iguales_al_reproducir_t03="", explicacion=explicacion)
        if col_mia:
            x, y = t03[col_t03], mia[col_mia]
            ambos = x.notna() & y.notna() & (y.astype(str) != "")
            f["parcelas_comparadas"] = int(ambos.sum())
            numerica = pd.api.types.is_numeric_dtype(x) and pd.api.types.is_numeric_dtype(y)
            if numerica:
                dif = (x - y)[ambos]
                igual = dif.abs() <= TOLERANCIA
                f["diferencia_mediana"] = round(float(dif.median()), 2)
                f["diferencia_maxima"] = round(float(dif.abs().max()), 2)
            else:
                igual = (x.astype(str) == y.astype(str))[ambos]
            f["parcelas_iguales"] = int(igual.sum())
            if col_t03 != "dist_etiquetada_mas_cercana_m":
                for ident in igual.index[~igual]:
                    detalle.append(dict(id_parcela=ident, conjunto_origen=mia.conjunto_origen[ident],
                                        municipio=mia.municipio[ident], columna_t03=col_t03, valor_t03=x[ident],
                                        columna_auditoria=f["columna_auditoria"], valor_auditoria=y[ident]))
        if misma == "no" and col_t03 in rep.columns:
            x, r = t03[col_t03], rep[col_t03]
            if pd.api.types.is_numeric_dtype(x):
                iguales = ((x - r).abs() <= TOLERANCIA) | (x.isna() & r.isna())
            else:
                iguales = x.astype(str) == r.astype(str)
            f["iguales_al_reproducir_t03"] = int(iguales.sum())
        filas.append(f)

    comparacion = pd.DataFrame(filas)
    comparacion.to_csv(a.tablas / "comparacion_con_t03.csv", index=False, encoding="utf-8-sig", lineterminator="\n")
    por_parcela = pd.DataFrame(detalle, columns=["id_parcela", "conjunto_origen", "municipio", "columna_t03",
                                                 "valor_t03", "columna_auditoria", "valor_auditoria"])
    por_parcela.to_csv(a.tablas / "comparacion_con_t03_por_parcela.csv", index=False, encoding="utf-8-sig",
                       lineterminator="\n")
    pd.DataFrame([dict(archivo="registro/t03/soporte_parcelas.csv", bytes=len(a.t03.read_bytes().replace(b"\r", b"")), sha256=huella(a.t03))]
                 ).to_csv(a.tablas / "huellas_archivos_leidos_comparacion.csv", index=False, encoding="utf-8-sig",
                          lineterminator="\n")

    pd.set_option("display.width", 250)
    print(comparacion.drop(columns="explicacion").to_string(index=False))
    print(f"\nFilas de detalle por parcela: {len(por_parcela)}")
    print(por_parcela.groupby("columna_t03").size().to_string())


if __name__ == "__main__":
    main()
