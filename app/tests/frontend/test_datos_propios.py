"""Prueba de «Analizar tus datos» (M16):  python tests/frontend/test_datos_propios.py  (desde app/).

Lo que debe cumplirse: subir el ZIP del reto da las mismas 59 cifras, confianzas y rangos que la vista principal, y
la pantalla muestra la cifra, la confianza y el rango sin romper las reglas de la carga segura.
"""
import io
import sys
import tempfile
import zipfile
from pathlib import Path

APP = Path(__file__).resolve().parents[2]       # app/
sys.path.insert(0, str(APP))

import numpy as np  # noqa: E402
from streamlit.testing.v1 import AppTest  # noqa: E402

from agrocebada_app.backend.carga_segura import revisar  # noqa: E402
from agrocebada_app.backend.datos import paquete  # noqa: E402
from agrocebada_app.backend.dominio.confianza import confianza_de_parcelas, confianza_municipios  # noqa: E402
from agrocebada_app.backend.dominio.rangos import rango_texto, rangos_municipio  # noqa: E402
from agrocebada_app.backend.modelo.estimador import predecir  # noqa: E402
from agrocebada_app.backend.modelo.metricas import metricas, validacion_dejando_uno  # noqa: E402
from agrocebada_app.config import MODELO_OFICIAL  # noqa: E402

paquete.exigir_datos()


def zip_de(archivos):
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w", zipfile.ZIP_DEFLATED) as z:
        for n, c in archivos.items():
            z.writestr(n, c)
    return b.getvalue()


def zip_del_reto():
    """El dataset del reto con el formato que acepta la carga segura (igual que en test_carga_segura.py)."""
    d = paquete.parcelas()
    tabla = d[["AREA_HA", "real", "CONJUNTO"]].rename(columns={"real": "RENDIMIENTO_T_HA"}).reset_index()
    geo = d[["municipio", "grupo_registro", "Estado", "geometry"]].reset_index().rename(
        columns={"ID_POLIGONO": "ID_POLIGON", "municipio": "Municipio", "grupo_registro": "Cultivo"})
    with tempfile.TemporaryDirectory() as tmp:
        geo.to_file(Path(tmp) / "Parcelas.shp")
        shp = {f.name: f.read_bytes() for f in Path(tmp).iterdir()}
    return zip_de({"ID_area.csv": tabla.to_csv(index=False).encode(), "Parcelas.zip": zip_de(shp)})


# --- el archivo subido recibe la misma lectura que las 59 de la vista principal
res = revisar("reto.zip", zip_del_reto())
du = res.datos
entrena = du[du.CONJUNTO == "ENTRENAMIENTO"]
pu = predecir(du, MODELO_OFICIAL)
v = validacion_dejando_uno(du, MODELO_OFICIAL)
conf = confianza_municipios(du, v)                      # M01 con la validación del propio archivo
cp = confianza_de_parcelas(pu, conf)
rangos = rangos_municipio(entrena).set_index("municipio")

# las cifras: idénticas a las oficiales de T08
oficial = paquete.oficial(MODELO_OFICIAL)
assert oficial is not None, "no encontré las 59 oficiales (ni en datos_app/ ni en registro/t08)"
assert len(pu) == 59 and np.allclose(pu.prediccion, oficial.reindex(pu.index)), "las 59 no coinciden con T08"

# la confianza: la misma mezcla que la vista principal (18 alta · 40 media · 1 baja)
assert cp.nivel.value_counts().to_dict() == {"media": 40, "alta": 18, "baja": 1}, cp.nivel.value_counts().to_dict()
assert cp.motivo.notna().all() and cp.motivo_detallado.notna().all()

# el rango: el mismo que el de la vista principal, porque sale de las mismas cosechas
d_oficial = paquete.parcelas()
r_oficial = rangos_municipio(d_oficial[d_oficial.CONJUNTO == "ENTRENAMIENTO"]).set_index("municipio")
for m in ["Chignahuapan", "Calpulalpan", "Singuilucan"]:
    assert rango_texto(rangos.bajo[m], rangos.alto[m]) == rango_texto(r_oficial.bajo[m], r_oficial.alto[m]), m
assert rango_texto(rangos.bajo["Chignahuapan"], rangos.alto["Chignahuapan"]) == "3.91–5.07 t/ha"

# las métricas del archivo: MAE, RMSE y R² existen y son finitos (validación dejando una fuera, no la 5 × 5)
m = metricas(v)
assert all(np.isfinite([m.MAE, m.RMSE, m.R2, m.sesgo])), m.to_dict()
print(f"archivo subido: 59 cifras iguales a T08 · {cp.nivel.value_counts().to_dict()} · MAE {m.MAE:.2f} t/ha")

# un municipio sin rango (una sola cosecha) no rompe el texto corto
assert rango_texto(rangos.bajo.get("Nanacamilpa de Mariano Arista"),
                   rangos.alto.get("Nanacamilpa de Mariano Arista")) == "Sin rango"


# --- la pantalla: se dibuja sin errores y muestra cifra, confianza, rango y explicación
def pantalla(modelo, contenido):
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]) if "__file__" in dir() else ".")
    from agrocebada_app.backend.carga_segura import revisar as rev
    from agrocebada_app.frontend.vistas.datos_propios.resultado import analizar_subido
    analizar_subido(rev("reto.zip", contenido), modelo, False, None)


ZIP = zip_del_reto()
for modelo in ["media_mun__resp_grupo", MODELO_OFICIAL]:
    at = AppTest.from_function(pantalla, args=(modelo, ZIP), default_timeout=300).run()
    assert not at.exception, (modelo, at.exception)
    texto = " ".join(x.value for x in at.markdown)
    assert "Rendimiento estimado" in texto and "t/ha" in texto, modelo
    assert "Confianza" in texto, modelo
    assert "¿Qué estoy viendo?" in texto and "no es una promesa" in texto.lower(), modelo     # explicación de Cebi
    assert "Mediana" in texto or "Media" in texto, modelo                                     # nombra el modelo vigente
    assert len(at.dataframe) >= 1, modelo
    tabla = at.dataframe[0].value
    assert {"confianza", "rango del municipio"} <= set(tabla.columns), tabla.columns.tolist()
    assert len(tabla) == 59, len(tabla)
    print(f"pantalla ({modelo}): cifra, confianza, rango y explicación sin errores")
print("OK")
