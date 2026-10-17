"""Pruebas de la carga segura de datasets:  python tests/backend/test_carga_segura.py  (desde app/)."""
import io
import sys
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))      # app/
from agrocebada_app.backend import carga_segura as K  # noqa: E402
from agrocebada_app.backend.datos import paquete  # noqa: E402
from agrocebada_app.backend.modelo.estimador import predecir  # noqa: E402
from agrocebada_app.backend.modelo.metricas import validacion_dejando_uno  # noqa: E402
from agrocebada_app.config import PAQ  # noqa: E402



def zip_de(archivos, comprimir=zipfile.ZIP_DEFLATED):
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w", comprimir) as z:
        for n, c in archivos.items():
            z.writestr(n, c)
    return b.getvalue()


def debe_rechazar(nombre, contenido, motivo):
    try:
        K.revisar(nombre, contenido)
    except K.Rechazo as e:
        print(f"  rechazado ✓ {motivo}: {e}")
        return
    raise AssertionError(f"debió rechazar: {motivo}")


def archivos_del_reto():
    """Tabla y shapefile con el mismo formato del reto, armados desde los datos de la app."""
    import tempfile
    from pathlib import Path
    d = paquete.parcelas()
    tabla = d[["AREA_HA", "real", "CONJUNTO"]].rename(columns={"real": "RENDIMIENTO_T_HA"}).reset_index()
    geo = d[["municipio", "grupo_registro", "Estado", "geometry"]].reset_index().rename(
        columns={"ID_POLIGONO": "ID_POLIGON", "municipio": "Municipio", "grupo_registro": "Cultivo"})
    with tempfile.TemporaryDirectory() as tmp:
        geo.to_file(Path(tmp) / "Parcelas.shp")
        shp = {f.name: f.read_bytes() for f in Path(tmp).iterdir()}
    return tabla.to_csv(index=False).encode(), zip_de(shp)


TABLA, SHPZIP = archivos_del_reto()

# ---- válidos
r = K.revisar("reto.zip", zip_de({"ID_area.csv": TABLA, "Parcelas.zip": SHPZIP}))
assert r.con_mapa and len(r.datos) == 197
pred = predecir(r.datos, "media_mun__resp_grupo")
of = pd.read_csv(PAQ / "oficial_59.csv").query("candidato == 'media_mun__resp_grupo'").set_index("ID_POLIGONO")
assert len(pred) == 59 and np.allclose(pred.prediccion, of.prediccion.reindex(pred.index)), "no coincide con T08"
print("ZIP del reto: 197 parcelas, las 59 estimaciones idénticas a T08 ✓")

with zipfile.ZipFile(io.BytesIO(SHPZIP)) as z:
    sueltos = {n: z.read(n) for n in z.namelist()}
r = K.revisar("sueltos.zip", zip_de({"tabla.csv": TABLA, **{f"carpeta/{n}": b for n, b in sueltos.items()}}))
assert r.con_mapa and len(r.datos) == 197
print("ZIP con el shapefile suelto en una carpeta ✓")

d = r.datos
simple = pd.DataFrame({"ID_POLIGONO": d.index, "MUNICIPIO": d.municipio.values, "GRUPO": d.grupo_registro.values,
                       "AREA_HA": d.AREA_HA.values, "RENDIMIENTO_T_HA": d.real.values, "CONJUNTO": d.CONJUNTO.values})
r = K.revisar("simple.csv", simple.to_csv(index=False).encode())
assert not r.con_mapa and len(predecir(r.datos, "media_mun__resp_grupo")) == 59
print("CSV simple: sin mapa, 59 estimaciones ✓")
v = validacion_dejando_uno(r.datos, "media_mun__resp_grupo")
print(f"validación dejando uno fuera: MAE {v.ae.mean():.3f} t/ha con {len(v)} parcelas ✓")

# ---- rechazos
print("rechazos:")
debe_rechazar("datos.xlsx", b"PK\x03\x04xxxx", "Excel")
debe_rechazar("foto.png", b"\x89PNG....", "imagen")
debe_rechazar("falso.zip", b"esto no es un zip", "ZIP falso")
debe_rechazar("malo.csv", b"%PDF-1.7\x00\x00binario", "PDF renombrado a .csv")
debe_rechazar("random.csv", b"a,b,c\n1,2,3\n", "CSV cualquiera")
debe_rechazar("programa.zip", zip_de({"tabla.csv": TABLA, "instalar.exe": b"MZ..."}), "programa dentro del ZIP")
debe_rechazar("script.zip", zip_de({"tabla.csv": TABLA, "abrir.py": b"import os"}), "script dentro del ZIP")
debe_rechazar("ruta.zip", zip_de({"../../etc/tabla.csv": TABLA}), "ruta que sale de la carpeta")
debe_rechazar("bomba.zip", zip_de({"tabla.csv": b"0" * 30_000_000}), "bomba zip")
debe_rechazar("muchos.zip", zip_de({f"t{i}.csv": b"x" for i in range(40)}), "demasiados archivos")
debe_rechazar("sinshape.zip", zip_de({"tabla.csv": TABLA}), "tabla sin polígonos")
otro = TABLA.replace(b"AGC_001,", b"XYZ_999,")
debe_rechazar("ids.zip", zip_de({"tabla.csv": otro, "Parcelas.zip": SHPZIP}), "IDs que no coinciden")
fuera = simple.assign(RENDIMIENTO_T_HA=np.where(simple.CONJUNTO == "ENTRENAMIENTO", 80, np.nan))
debe_rechazar("rango.csv", fuera.to_csv(index=False).encode(), "rendimientos fuera de rango")
dup = pd.concat([simple, simple.head(1)])
debe_rechazar("dup.csv", dup.to_csv(index=False).encode(), "IDs repetidos")
inyeccion = simple.copy(); inyeccion.loc[0, "ID_POLIGONO"] = "<script>alert(1)</script>"
debe_rechazar("xss.csv", inyeccion.to_csv(index=False).encode(), "ID con código")
debe_rechazar("plantilla.csv", K.plantilla_csv(), "la plantilla sola (sólo 2 parcelas con cosecha)")
debe_rechazar("grande.csv", b"x" * (K.MAX_MB * 1024 * 1024 + 1), "más de 50 MB")
print("OK")
