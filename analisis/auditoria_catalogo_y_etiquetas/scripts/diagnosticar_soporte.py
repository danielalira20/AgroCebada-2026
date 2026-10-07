"""Diagnóstico de soporte: qué tan respaldada está cada parcela por las parcelas conocidas.

Uso (después de construir_catalogo.py, con el mismo entorno):
    python scripts/diagnosticar_soporte.py --datos RUTA/DATASET_RETO_AGRO_2026

Lee el catálogo y la tabla de precisión de tablas/, y del dataset original: el shapefile,
un mapa de lluvia, los dos mapas de relieve y las dos tablas satelitales. Solo lee.

Escribe en tablas/:
    soporte_por_parcela.csv               197 filas, una por parcela.
    soporte_resumen_por_municipio.csv     Reservadas frente a conocidas, por municipio.
    huellas_archivos_leidos_soporte.csv   Huella SHA-256 de cada archivo original leído.

«Conocida» es una parcela con rendimiento. No usa el valor del rendimiento de ninguna parcela.
No extrae valores de clima ni de relieve y no entrena ningún modelo.
"""
import argparse
import hashlib
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import pyproj
import rasterio
from rasterio.windows import Window
from shapely.geometry import box
from shapely.geometry.polygon import orient

CARPETA = Path(__file__).resolve().parents[1]
TABLAS_POR_OMISION = CARPETA / "tablas"

SHAPEFILE = "Parcelas_Reto_AGC_CONJUNTO_70_30/Parcelas_Reto_AGC_CONJUNTO.shp"
MAPA_LLUVIA = "PREC_2025_04.tif"                    # los 21 mapas de clima comparten la cuadrícula
MAPA_ELEVACION = "Elevacion_INEGI_CEM4_120m.tif"
MAPA_PENDIENTE = "Pendiente_INEGI_CEM4_120m_grados.tif"
TABLA_BASICO = "Conjunto_datos_BASICO_AgroCebada2026.csv"
TABLA_PRO = "Conjunto_datos_PRO_AgroCebada.csv"

VENTANA = ("2025-04-01", "2025-10-31")              # para contar observaciones y meses
VENTANA_HUECO = ("2025-06-01", "2025-10-31")        # para medir el hueco más largo
SENSORES = {"Sentinel-2": ("s2", "ndvi_promedio"), "Planet": ("planet", "ndvi_promedio"),
            "Landsat": ("landsat", "vi6t_promedio")}

POCAS_CONOCIDAS = 5
RADIO_AVISO_M = 1000
COBERTURA_COMPLETA = 0.99

GEOD = pyproj.Geod(ellps="WGS84")


def huella(ruta: Path) -> str:
    h = hashlib.sha256()
    with ruta.open("rb") as f:
        for bloque in iter(lambda: f.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()


def buscar(datos: Path, nombre: str) -> Path:
    """Encuentra un archivo por nombre dentro de las carpetas descomprimidas del dataset."""
    hallados = sorted(datos.rglob(nombre))
    if len(hallados) != 1:
        raise FileNotFoundError(f"Se esperaba un solo {nombre} bajo {datos}; se hallaron {len(hallados)}")
    return hallados[0]


def area_geodesica(geometria) -> float:
    """Superficie sobre el elipsoide WGS84, en metros cuadrados. Admite una o varias piezas."""
    if geometria.is_empty:
        return 0.0
    piezas = [geometria] if geometria.geom_type == "Polygon" else [p for p in geometria.geoms if p.geom_type == "Polygon"]
    return sum(abs(GEOD.geometry_area_perimeter(orient(p, 1.0))[0]) for p in piezas)


def celdas_de_clima(geoms, ruta: Path):
    """Para cada contorno, las celdas del mapa de lluvia que toca y qué parte del contorno cae en cada una."""
    with rasterio.open(ruta) as r:
        assert r.crs.to_epsg() == 4326, "El mapa de lluvia debe estar en latitud/longitud WGS84"
        transformacion = r.transform
    resultado = []
    for g in geoms:
        x0, y0, x1, y1 = g.bounds
        col0, fila1 = ~transformacion * (x0, y0)
        col1, fila0 = ~transformacion * (x1, y1)
        total = area_geodesica(g)
        partes = {}
        for fila in range(int(np.floor(fila0)), int(np.floor(fila1)) + 1):
            for col in range(int(np.floor(col0)), int(np.floor(col1)) + 1):
                izq, arriba = transformacion * (col, fila)
                der, abajo = transformacion * (col + 1, fila + 1)
                superficie = area_geodesica(g.intersection(box(izq, abajo, der, arriba)))
                if superficie > 0:
                    partes[f"{fila}_{col}"] = superficie / total
        resultado.append(partes)
    return resultado


def cobertura_de_mapa(geoms_6372, ruta: Path):
    """Parte de cada contorno que cae sobre celdas con dato en un mapa de relieve."""
    coberturas = []
    with rasterio.open(ruta) as r:
        assert r.crs.to_epsg() == 6372, "Los mapas de relieve deben estar en EPSG:6372"
        for g in geoms_6372:
            # Ventana de celdas que cubre todo el contorno, con una celda de margen por cada lado.
            x0, y0, x1, y1 = g.bounds
            col0, fila1 = ~r.transform * (x0, y0)
            col1, fila0 = ~r.transform * (x1, y1)
            c0, f0 = int(np.floor(col0)) - 1, int(np.floor(fila0)) - 1
            ventana = Window(c0, f0, int(np.floor(col1)) + 2 - c0, int(np.floor(fila1)) + 2 - f0)
            datos = r.read(1, window=ventana, boundless=True, fill_value=r.nodata)
            t = r.window_transform(ventana)
            valida = 0.0
            for i in range(datos.shape[0]):
                for j in range(datos.shape[1]):
                    if datos[i, j] == r.nodata or np.isnan(datos[i, j]):
                        continue
                    izq, arriba = t * (j, i)
                    der, abajo = t * (j + 1, i + 1)
                    valida += g.intersection(box(izq, abajo, der, arriba)).area
            coberturas.append(min(valida / g.area, 1.0))
    return coberturas


def disponibilidad_satelital(datos: Path, ids):
    """Observaciones con dato, meses con dato y hueco más largo, por parcela y sensor."""
    columnas = ["ID_POLIGONO", "fecha_captura", "sensor"]
    basico = pd.read_csv(datos / TABLA_BASICO, encoding="utf-8-sig", usecols=columnas + ["ndvi_promedio", "vi6t_promedio"])
    pro = pd.read_csv(datos / TABLA_PRO, encoding="utf-8-sig", usecols=columnas + ["ndvi_promedio"])
    d = pd.concat([basico, pro], ignore_index=True)
    assert set(d.sensor) == set(SENSORES), f"Sensores inesperados: {set(d.sensor)}"
    d["fecha"] = pd.to_datetime(d.fecha_captura, format="%d/%m/%Y")
    salida = pd.DataFrame(index=pd.Index(ids, name="id_parcela"))
    ini, fin = pd.Timestamp(VENTANA[0]), pd.Timestamp(VENTANA[1])
    ini_h, fin_h = pd.Timestamp(VENTANA_HUECO[0]), pd.Timestamp(VENTANA_HUECO[1])
    for sensor, (abreviatura, indice) in SENSORES.items():
        x = d[(d.sensor == sensor) & d[indice].notna() & (d.fecha >= ini) & (d.fecha <= fin)]
        salida[f"{abreviatura}_observaciones_con_dato"] = x.groupby("ID_POLIGONO").size().reindex(ids, fill_value=0)
        salida[f"{abreviatura}_meses_con_dato"] = x.groupby("ID_POLIGONO").fecha.apply(
            lambda f: f.dt.month.nunique()).reindex(ids, fill_value=0)
        h = x[(x.fecha >= ini_h) & (x.fecha <= fin_h)]

        def hueco(fechas):
            puntos = [ini_h] + sorted(set(fechas)) + [fin_h]
            return max((b - a).days for a, b in zip(puntos[:-1], puntos[1:]))
        salida[f"{abreviatura}_hueco_maximo_dias"] = h.groupby("ID_POLIGONO").fecha.apply(hueco).reindex(
            ids, fill_value=(fin_h - ini_h).days)
    return salida.astype(int)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--datos", type=Path, required=True, help="Carpeta DATASET_RETO_AGRO_2026")
    ap.add_argument("--tablas", type=Path, default=TABLAS_POR_OMISION)
    a = ap.parse_args()

    cat = pd.read_csv(a.tablas / "catalogo_parcelas.csv", dtype=str, keep_default_na=False, encoding="utf-8-sig")
    assert len(cat) == 197
    ids = list(cat.id_parcela)
    conocida = (cat.rendimiento_t_ha != "").values
    municipio = cat.municipio.values
    n = len(cat)

    precision = pd.read_csv(a.tablas / "precision_etiqueta_por_municipio.csv", dtype=str, keep_default_na=False,
                            encoding="utf-8-sig")
    escalon = dict(precision[precision.agrupacion == "municipio"][["grupo", "paso_comun"]].values)

    ruta_shp = a.datos / SHAPEFILE
    g = gpd.read_file(ruta_shp, encoding="utf-8").set_index("ID_POLIGON").loc[ids]
    geoms = list(g.geometry)
    planos = list(g.geometry.to_crs(32614))        # metros, para distancias entre orillas
    relieve = list(g.geometry.to_crs(6372))        # proyección de los mapas de relieve

    # --- Municipio compartido
    conocidas_mun = np.array([int(((municipio == municipio[i]) & conocida).sum()) - int(conocida[i]) for i in range(n)])

    # --- Cercanía: centros (geodésica) y orillas (UTM 14 N), siempre hacia otra parcela conocida
    lon = cat.centroide_lon.astype(float).values
    lat = cat.centroide_lat.astype(float).values
    indices_conocidas = np.flatnonzero(conocida)
    cerca_centro, d_centro, cerca_orilla, d_orilla, a500, a1000 = [], [], [], [], [], []
    for i in range(n):
        otras = indices_conocidas[indices_conocidas != i]
        dc = np.array([GEOD.inv(lon[i], lat[i], lon[j], lat[j])[2] for j in otras])
        do = np.array([planos[i].distance(planos[j]) for j in otras])
        cerca_centro.append(otras[dc.argmin()]); d_centro.append(dc.min())
        cerca_orilla.append(otras[do.argmin()]); d_orilla.append(do.min())
        a500.append(int((dc < 500).sum())); a1000.append(int((dc < RADIO_AVISO_M).sum()))
    cerca_centro = np.array(cerca_centro); cerca_orilla = np.array(cerca_orilla)

    # --- Clima compartido: celdas del mapa de lluvia, por superficie de intersección
    ruta_lluvia = buscar(a.datos, MAPA_LLUVIA)
    celdas = celdas_de_clima(geoms, ruta_lluvia)
    principal = [max(p.items(), key=lambda kv: (kv[1], kv[0])) for p in celdas]
    comparten = []
    for i in range(n):
        mias = set(celdas[i])
        comparten.append(int(sum(1 for j in indices_conocidas if j != i and mias & set(celdas[j]))))

    # --- Disponibilidad de entradas
    satelite = disponibilidad_satelital(a.datos, ids)
    ruta_elev, ruta_pend = buscar(a.datos, MAPA_ELEVACION), buscar(a.datos, MAPA_PENDIENTE)
    cob_elev = cobertura_de_mapa(relieve, ruta_elev)
    cob_pend = cobertura_de_mapa(relieve, ruta_pend)

    # --- Calidad de observación
    mezcla = (cat.contorno_categoria.isin(["B", "C"]) | (cat.contorno_arboles_dentro == "si")
              | (cat.contorno_construccion_dentro == "si") | (cat.contorno_angosta_o_muy_pequena == "si")).values

    s = pd.DataFrame({
        "id_parcela": ids, "conjunto_origen": cat.conjunto_origen, "municipio": municipio,
        "area_ha_origen": cat.area_ha_origen,
        "conocidas_en_municipio": conocidas_mun,
        "escalon_etiqueta_municipio": [escalon.get(m, "") for m in municipio],
        "conocida_mas_cercana": np.array(ids)[cerca_centro],
        "distancia_centros_m": np.round(d_centro, 1),
        "mas_cercana_en_su_municipio": np.where(municipio[cerca_centro] == municipio, "si", "no"),
        "conocida_mas_cercana_por_orilla": np.array(ids)[cerca_orilla],
        "distancia_orillas_m": np.round(d_orilla, 2),
        "conocidas_a_menos_de_500_m": a500, "conocidas_a_menos_de_1_km": a1000,
        "celdas_clima_tocadas": [len(p) for p in celdas],
        "celda_clima_principal": [c for c, _ in principal],
        "fraccion_en_celda_principal": [round(f, 4) for _, f in principal],
        "conocidas_que_comparten_celda": comparten,
    })
    s = pd.concat([s, satelite.reset_index(drop=True)], axis=1)
    s["cobertura_elevacion"] = np.round(cob_elev, 4)
    s["cobertura_pendiente"] = np.round(cob_pend, 4)
    s["contorno_categoria"] = cat.contorno_categoria.values
    s["contorno_mezcla_senal"] = np.where(mezcla, "si", "no")

    reglas = [
        ("pocas_conocidas_en_municipio", s.conocidas_en_municipio < POCAS_CONOCIDAS),
        ("sin_conocida_a_menos_de_1_km", s.conocidas_a_menos_de_1_km == 0),
        ("celda_clima_sin_conocidas", s.conocidas_que_comparten_celda == 0),
        ("etiqueta_gruesa_en_municipio", s.escalon_etiqueta_municipio == "0.5"),
        ("relieve_incompleto", (np.array(cob_elev) < COBERTURA_COMPLETA) | (np.array(cob_pend) < COBERTURA_COMPLETA)),
        ("contorno_b_o_c", s.contorno_categoria.isin(["B", "C"])),
        ("angosta_o_muy_pequena", (cat.contorno_angosta_o_muy_pequena == "si").values),
    ]
    s["avisos"] = ["; ".join(nombre for nombre, marca in reglas if np.asarray(marca)[i]) for i in range(n)]
    s["numero_de_avisos"] = [sum(bool(np.asarray(marca)[i]) for _, marca in reglas) for i in range(n)]
    s.to_csv(a.tablas / "soporte_por_parcela.csv", index=False, encoding="utf-8-sig", lineterminator="\n")

    # --- Resumen: reservadas frente a conocidas
    def fila(nombre, conjunto, x):
        return dict(
            municipio=nombre, conjunto_origen=conjunto, parcelas=len(x),
            distancia_centros_mediana_m=round(x.distancia_centros_m.median(), 1),
            distancia_centros_maxima_m=round(x.distancia_centros_m.max(), 1),
            distancia_orillas_mediana_m=round(x.distancia_orillas_m.median(), 1),
            sin_conocida_a_menos_de_1_km=int((x.conocidas_a_menos_de_1_km == 0).sum()),
            celda_clima_sin_conocidas=int((x.conocidas_que_comparten_celda == 0).sum()),
            s2_observaciones_mediana=x.s2_observaciones_con_dato.median(),
            planet_observaciones_mediana=x.planet_observaciones_con_dato.median(),
            landsat_observaciones_mediana=x.landsat_observaciones_con_dato.median(),
            relieve_incompleto=int(x.avisos.str.contains("relieve_incompleto").sum()),
            contorno_b_o_c=int(x.contorno_categoria.isin(["B", "C"]).sum()),
            contorno_mezcla_senal=int((x.contorno_mezcla_senal == "si").sum()),
            con_algun_aviso=int((x.numero_de_avisos > 0).sum()))
    orden = sorted(set(municipio), key=lambda m: (-(municipio == m).sum(), m))
    filas = []
    for nombre in orden + ["todos"]:
        parte = s if nombre == "todos" else s[s.municipio == nombre]
        for conjunto in ("PREDICCION", "ENTRENAMIENTO"):
            x = parte[parte.conjunto_origen == conjunto]
            if len(x):
                filas.append(fila(nombre, conjunto, x))
    resumen = pd.DataFrame(filas)
    resumen.to_csv(a.tablas / "soporte_resumen_por_municipio.csv", index=False, encoding="utf-8-sig", lineterminator="\n")

    leidos = [ruta_shp, ruta_lluvia, ruta_elev, ruta_pend, a.datos / TABLA_BASICO, a.datos / TABLA_PRO]
    pd.DataFrame([dict(archivo=r.relative_to(a.datos).as_posix(), bytes=r.stat().st_size, sha256=huella(r))
                  for r in leidos]).to_csv(a.tablas / "huellas_archivos_leidos_soporte.csv", index=False,
                                           encoding="utf-8-sig", lineterminator="\n")

    pd.set_option("display.width", 250)
    print(resumen.to_string(index=False))
    print("\nAvisos entre las 59 reservadas:")
    r = s[s.conjunto_origen == "PREDICCION"]
    for nombre, _ in reglas:
        print(f"  {nombre}: {int(r.avisos.str.contains(nombre).sum())}")
    print(f"  sin ningún aviso: {int((r.numero_de_avisos == 0).sum())}")


if __name__ == "__main__":
    main()
