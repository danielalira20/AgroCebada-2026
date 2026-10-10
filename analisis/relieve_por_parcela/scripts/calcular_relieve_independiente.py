"""Cálculo independiente de relieve por parcela, para conciliar con T05.

Evidencia, no parte de la entrega. Sigue el mismo método (media ponderada por
área válida en EPSG:6372), pero por un camino de código distinto al de
scripts/t05_relieve.py:
- lee el shapefile con pyogrio directamente, sin geopandas;
- reproyecta los vértices con pyproj a mano;
- calcula todas las intersecciones de una parcela de una vez (shapely vectorizado);
- lee cada valor por la COORDENADA del centro de su celda (rasterio.sample), no
  por fila y columna, para delatar un desfase de índices.

Uso, desde la raíz del repositorio:
    python analisis/relieve_por_parcela/scripts/calcular_relieve_independiente.py \\
        --t05 data/processed/t05/primera_extraccion/relieve_parcela.csv \\
        --salida analisis/relieve_por_parcela/tablas/conciliacion_calculo_independiente.csv
"""
import argparse
import csv
import math
from pathlib import Path

import numpy as np
import pyogrio.raw
import rasterio
import shapely
from pyproj import Transformer

DATASET = Path("data/raw/DATASET_RETO_AGRO_2026")


def unico(nombre):
    r = sorted(DATASET.rglob(nombre))
    assert len(r) == 1, nombre
    return r[0]


def parcelas():
    meta, _, geometria, campos = pyogrio.raw.read(unico("Parcelas_Reto_AGC_CONJUNTO.shp"))
    ids = campos[list(meta["fields"]).index("ID_POLIGON")]
    tr = Transformer.from_crs(meta["crs"], "EPSG:6372", always_xy=True)
    for id_, wkb in zip(ids, geometria):
        g = shapely.from_wkb(wkb)
        g = shapely.transform(g, lambda xy: np.column_stack(tr.transform(xy[:, 0], xy[:, 1])))
        yield str(id_), g


def resumir(r, g):
    t = r.transform
    xmin, ymin, xmax, ymax = g.bounds
    cols = np.arange(math.floor((xmin - t.c) / t.a) - 1, math.floor((xmax - t.c) / t.a) + 2)
    fils = np.arange(math.floor((ymax - t.f) / t.e) - 1, math.floor((ymin - t.f) / t.e) + 2)
    cc, ff = np.meshgrid(cols, fils)
    x0 = t.c + cc.ravel() * t.a
    y0 = t.f + ff.ravel() * t.e
    cajas = shapely.box(x0, y0 + t.e, x0 + t.a, y0)
    areas = shapely.area(shapely.intersection(g, cajas))
    m = areas > 0
    centros = list(zip(x0[m] + t.a / 2, y0[m] + t.e / 2))
    muestras = [v[0] for v in r.sample(centros, masked=True)]
    validas = np.array([not np.ma.is_masked(v) for v in muestras], dtype=bool)
    valores = np.array([float(v) if ok else 0.0 for v, ok in zip(muestras, validas)])
    a = areas[m]
    av = a[validas].sum()
    media = float((valores[validas] * a[validas]).sum() / av) if av > 0 else None
    return media, float(av / g.area), int(m.sum()), int(validas.sum())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--t05", required=True)
    ap.add_argument("--salida", required=True)
    a = ap.parse_args()
    with open(a.t05, encoding="utf-8") as f:
        t05 = {r["id_parcela"]: r for r in csv.DictReader(f)}
    filas = []
    with rasterio.open(unico("Elevacion_INEGI_CEM4_120m.tif")) as re_, \
         rasterio.open(unico("Pendiente_INEGI_CEM4_120m_grados.tif")) as rp:
        for id_, g in parcelas():
            fila = {"id_parcela": id_}
            for var, r, col in (("elevacion", re_, "elevacion_media_m"),
                                ("pendiente", rp, "pendiente_media_grados")):
                media, cob, n, nv = resumir(r, g)
                o = t05[id_]
                fila |= {f"{var}_media_indep": media, f"{var}_media_t05": float(o[col]),
                         f"{var}_dif_media": media - float(o[col]),
                         f"{var}_cobertura_indep": cob,
                         f"{var}_dif_cobertura": cob - float(o[f"{var}_cobertura_valida"]),
                         f"{var}_celdas_coinciden": (n == int(o[f"{var}_celdas_intersectadas"])
                                                     and nv == int(o[f"{var}_celdas_validas"]))}
            filas.append(fila)
    filas.sort(key=lambda f: f["id_parcela"])
    Path(a.salida).parent.mkdir(parents=True, exist_ok=True)
    with open(a.salida, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(filas[0]), lineterminator="\n")
        w.writeheader()
        w.writerows({k: (repr(v) if isinstance(v, float) else v) for k, v in fl.items()} for fl in filas)
    for var in ("elevacion", "pendiente"):
        dm = np.max(np.abs([f[f"{var}_dif_media"] for f in filas]))  # NaN se propaga y se ve.
        dc = np.max(np.abs([f[f"{var}_dif_cobertura"] for f in filas]))
        ok = all(f[f"{var}_celdas_coinciden"] for f in filas)
        print(f"{var}: parcelas {len(filas)} · máx |dif media| {dm:.3e} · máx |dif cobertura| {dc:.3e} · celdas coinciden: {ok}")


if __name__ == "__main__":
    main()
