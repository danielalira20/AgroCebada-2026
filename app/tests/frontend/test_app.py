"""Prueba rápida de la app sin navegador:  python tests/frontend/test_app.py  (desde app/)."""
import sys
from pathlib import Path

APP = Path(__file__).resolve().parents[2]       # app/
sys.path.insert(0, str(APP))

from streamlit.testing.v1 import AppTest

from agrocebada_app.backend.datos import paquete

paquete.exigir_datos()    # mensaje claro si falta el dataset del reto


def nueva(**estado):
    at = AppTest.from_file(str(APP / "app.py"), default_timeout=300)
    for k, v in estado.items():
        at.session_state[k] = v
    return at.run()


def caja(at, etiqueta):
    return next(x for x in at.selectbox if x.label == etiqueta)


def html(at, marca):
    return [m.value for m in at.markdown if marca in m.value]


# ---- vista agricultor
at = nueva()
assert not at.exception, at.exception
assert html(at, "class='big'"), "vista agricultor sin estimación"
for m in caja(at, "Municipio").options:                      # cada municipio con su parcela por defecto
    caja(at, "Municipio").set_value(m).run()
    assert not at.exception, (m, at.exception)
    assert html(at, "class='big'"), m
print("agricultor: los", len(caja(at, "Municipio").options), "municipios sin errores")

# ---- vista analista, con los dos modelos
for modelo in ["media_mun__resp_grupo", "mediana_mun__resp_grupo"]:
    at = nueva(vista="Analista", modelo=modelo)
    assert not at.exception, (modelo, at.exception)
    checks = html(at, "class='chk")
    assert checks and checks[0].count("✓") == 4 and "✗" not in checks[0], (modelo, checks)
    kpis = html(at, "class='kpis'")[0]
    print(f"analista ({modelo}): 4 verificaciones en verde ·",
        "MAE", kpis.split("MAE · A sin respaldo</span><b class='kv'>")[1][:5],
        "· R²", kpis.split("R² · A sin respaldo</span><b class='kv'>")[1][:5])

caja(at, "Buscar parcela por ID").set_value("AGC_120").run()
assert not at.exception, at.exception
assert html(at, "AGC_120</b>"), "el buscador no muestra la parcela"
caja(at, "Buscar parcela por ID").set_value("(ninguna)").run()
for m in caja(at, "Municipio").options:
    caja(at, "Municipio").set_value(m).run()
    assert not at.exception, (m, at.exception)
for m in caja(at, "Municipio a ocultar").options:
    caja(at, "Municipio a ocultar").set_value(m).run()
    assert not at.exception, (m, at.exception)
print("buscador, filtro por municipio y simulación de información insuficiente sin errores")

# ---- vista del mapa desde arriba, en las dos vistas
for vista in ["Agricultor", "Analista"]:
    at = nueva(vista=vista, vista_mapa="Desde arriba")
    assert not at.exception, (vista, at.exception)
print("mapa desde arriba sin errores en las dos vistas")

# ---- comparación de parcelas y pestaña de datos propios (se dibujan sin errores)
at = nueva(vista="Analista")
assert any(x.label == "Parcelas" for x in at.multiselect), "falta la comparación de parcelas"
assert any("Analiza tu propio dataset" in m.value for m in at.markdown), "falta la pestaña de datos propios"
print("comparación de parcelas y pestaña «Analizar tus datos» presentes")

# ---- ficha PDF (se arma igual que en la app)
import numpy as np  # noqa: E402
from agrocebada_app.backend.datos import paquete  # noqa: E402
from agrocebada_app.backend.ficha_pdf.ficha import ficha_pdf  # noqa: E402
from agrocebada_app.backend.modelo.estimador import predecir  # noqa: E402
d, S, C = paquete.parcelas(), paquete.series(), paquete.clima()
pred = predecir(d, "media_mun__resp_grupo")
for pid in ["AGC_011", "AGC_120", "AGC_002"]:
    r = d.loc[pid]
    est = r.CONJUNTO == "PREDICCION"
    cerca = d.index[np.hypot(d.lon_c - r.lon_c, d.lat_c - r.lat_c) < 0.06]
    pol = [dict(coords=list(d.loc[i].geometry.geoms[0].exterior.coords if d.loc[i].geometry.geom_type == "MultiPolygon"
                            else d.loc[i].geometry.exterior.coords),
                valor=float(pred.prediccion.get(i, d.loc[i].real)), sel=i == pid,
                reservada=d.loc[i].CONJUNTO == "PREDICCION") for i in cerca]
    info = dict(id=pid, municipio=r.municipio, estado=r.Estado, grupo=r.grupo_registro, area=r.AREA_HA,
                tipo="estimacion" if est else "registrado", valor=float(pred.prediccion[pid]) if est else r.real,
                produccion=float(pred.prediccion[pid]) * r.AREA_HA if est else None, error=0.3, oof=4.4,
                nota="nota", aviso="", corte="31 de octubre de 2025")
    c = C[C.id_parcela == pid].assign(mes=lambda x: x.periodo.str[5:].astype(int))
    pdf = ficha_pdf(info, pol, S[S.ID_POLIGONO == pid], c, str(APP / "assets" / "mascota" / "cebi.png"))
    assert pdf[:5] == b"%PDF-" and len(pdf) > 20000, pid
print("ficha PDF generada para 3 parcelas")
print("OK")
