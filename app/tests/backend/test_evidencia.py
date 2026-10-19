"""Pruebas de la evidencia (M13):  python tests/backend/test_evidencia.py  (desde app/)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from agrocebada_app.backend.datos.experimentos import experimentos  # noqa: E402
from agrocebada_app.backend.dominio import evidencia as ev  # noqa: E402
from agrocebada_app.backend.dominio.desglose import NO_VE  # noqa: E402

MEDIA, MEDIANA = "media_mun__resp_grupo", "mediana_mun__resp_grupo"
PROHIBIDAS = ["no sirve", "tu parcela dará", "de cada 10"]
RAIZ = Path(__file__).resolve().parents[3]

e = experimentos()
reg = e[e.estado == "registrada"]
comp = e[e.estado == "complementaria"]

# --- la tabla: 27 pruebas registradas y 3 complementarias, repartidas en las tres preguntas
assert len(e) == 30 and len(reg) == 27 and len(comp) == 3, (len(e), len(reg), len(comp))
assert e.groupby("pregunta").size().to_dict() == {1: 10, 2: 4, 3: 16}
assert set(e.pregunta) == set(ev.PREGUNTAS) == {1, 2, 3}

# --- cada fila registrada tiene su registro y su fuente, y ambos existen en el repo
assert reg.registro.notna().all() and reg.fuente.notna().all()
if (RAIZ / "registro").exists():
    ids = set(pd.read_csv(RAIZ / "registro/experimentos.csv").id) | set(pd.read_csv(RAIZ / "registro/decisiones.csv").id)
    faltan = sorted(set(reg.registro) - ids)
    assert not faltan, faltan
    for f in e.fuente.unique():
        assert (RAIZ / f.split(" §")[0]).exists(), f

# --- las complementarias se marcan como tal, sin registro ni intervalo, con su fuente del documento
assert comp.registro.isna().all() and comp.ic_inf.isna().all() and comp.pasa_regla.isna().all()
assert comp.fuente.str.startswith("docs/t16_procedimiento_final.md").all()
assert sorted(comp.mae.round(4)) == [0.3148, 0.3170, 0.3177]

# --- ninguna prueba registrada pasó la regla; el cambio es MAE menos referencia (con redondeo)
assert not reg.pasa_regla.astype(bool).any()
assert ((reg.mae - reg.mae_referencia) - reg.delta_mae).abs().max() < 2.5e-4

# --- cifras clave que deben coincidir con el informe (T16)
m = reg[reg.tarea == "T16"].iloc[0]
assert (round(m.mae, 4), round(m.mae_referencia, 4), round(m.delta_mae, 4)) == (0.3126, 0.3205, -0.0079)
assert (round(m.ic_inf, 4), round(m.ic_sup, 4), int(m.reps_mejoran)) == (-0.0163, 0.0058, 5)

# --- tabla para mostrar: icono y palabra, orden y etiquetas
t = ev.tabla(e)
assert len(t) == 30 and set(t.resultado) == {ev.MEJ, ev.SUBE, ev.COMP}
assert not t.resultado.str.contains("sirve").any() and (t.resultado.str[:1].isin(["✔", "▲", "⚠", "P"])).all()
t1 = ev.tabla(e, 1)
assert list(t1.estado[:8]) == ["registrada"] * 8 and list(t1.estado[8:]) == ["complementaria"] * 2
assert t1.cambio[:8].is_monotonic_increasing
assert ev.tabla(e, 3).iloc[0].prueba == "Mediana del municipio (modelo final)"
assert ev.tabla(e, 3, MEDIA).iloc[0].prueba == "Mediana del municipio (alternativa evaluada)"
assert t.loc[t.estado == "complementaria", "intervalo"].eq("—").all()

# --- respuestas: salen de las cifras
r1, r2, r3 = (ev.resumen(e, p) for p in (1, 2, 3))
assert (r1["n"], r1["pasan"], r2["n"], r3["n"]) == (8, 0, 4, 15)
assert "Ninguna de las 8" in r1["frase"] and "+0.0009 a +0.0035" in r1["frase"]
assert "+0.0008 a +0.0030" in r2["frase"]
assert "5 bajaron el error" in r3["frase"] and r3["mejor"] == "Mediana del municipio (modelo final)"
for p in (1, 2, 3):
    f = ev.resumen(e, p)["frase"].lower()
    assert not any(x in f for x in PROHIBIDAS), f

assert ev.referencia(e) == 0.3205

# --- el cierre cambia con el modelo oficial: nunca se escribe «mediana adoptada» a mano
c1, c2 = ev.cierre_modelo_final(e, MEDIANA), ev.cierre_modelo_final(e, MEDIA)
assert "0.3205 a 0.3126" in c1 and "excepción explícita" in c1 and "no pasó la regla" in c1
assert "Se conserva el promedio" in c2 and "excepción" not in c2
assert "no demuestra" in ev.CAUTELA and "inútiles" in ev.CAUTELA

# --- cuánto explica la ubicación: parte entre municipios sobre la total (datos inventados a mano)
d = pd.DataFrame({"municipio": ["A", "A", "B", "B", "C"], "CONJUNTO": ["ENTRENAMIENTO"] * 4 + ["PREDICCION"],
                  "real": [4.0, 6.0, 2.0, 4.0, np.nan]}, index=list("abcde"))
v = ev.variacion_ubicacion(d)   # medias A=5 y B=3, media general 4: entre = 2·1 + 2·1 = 4; total = 0 + 4 + 4 + 0 = 8
y = np.array([4.0, 6.0, 2.0, 4.0]); total = ((y - 4) ** 2).sum(); entre = 2 * 1 + 2 * 1
assert abs(v["parte"] - entre / total) < 1e-12 and v["parcelas"] == 4 and v["municipios"] == 2
assert v["pct"] == round(100 * entre / total) and f"{v['pct']} %" in v["frase"] and "dentro de cada municipio" in v["frase"]
assert ev.variacion_ubicacion(d.assign(real=3.0))["pct"] is None

# --- lo que falta coincide con lo que el método declara que no ve
assert [n for n, _ in ev.lo_que_falta()] == ["Fecha de siembra", "Variedad", "Manejo"]
for palabra in ("siembra", "variedad", "manejo"):
    assert palabra in NO_VE and any(palabra in n.lower() for n, _ in ev.lo_que_falta())

# --- error del modelo vigente: sale de la validación (población principal)
O = pd.DataFrame({"escenario": "A", "fuente": "municipio", "ID_POLIGONO": ["p1", "p2"] * 2, "repeticion": [1, 1, 2, 2],
                  "real": [4.0, 5.0, 4.0, 5.0], "ae": [0.2, 0.4, 0.4, 0.2], "e": [0.2, -0.4, -0.4, 0.2]})
a = ev.ajuste_final(O, MEDIANA)
assert a["parcelas"] == 2 and a["predicciones"] == 4 and abs(a["mae"] - 0.3) < 1e-12 and a["modelo"] == "Mediana · oficial"
assert ev.ajuste_final(None) is None
assert ev.ajuste_final(O.assign(escenario="B"), MEDIANA) is None, "B no debe presentarse como población principal"

# filtros: sin cambiar cifras, orden ni trazabilidad; complementarias explícitas
antes = e.copy(deep=True)
for p, n in [(1, 8), (2, 4), (3, 15)]:
    todas = ev.filtrar_pruebas(e, p)
    bajan = ev.filtrar_pruebas(e, p, "bajan")
    no_bajan = ev.filtrar_pruebas(e, p, "no_bajan")
    assert len(todas) == n and set(todas.estado) == {"registrada"}
    assert set(bajan.index).isdisjoint(no_bajan.index)
    assert set(bajan.index) | set(no_bajan.index) == set(todas.index)
    pd.testing.assert_frame_equal(todas, e.loc[todas.index])
    assert ev.filtrar_pruebas(e, p, complementarias=True).shape[0] == {1: 10, 2: 4, 3: 16}[p]
assert ev.filtrar_pruebas(e, 1, "bajan").empty
pd.testing.assert_frame_equal(e, antes)
sin_registro = e[e.estado == "complementaria"]
assert ev.resumen(sin_registro, 1)["n"] == 0
assert ev.referencia(sin_registro) is None
assert "No hay una decisión" in ev.cierre_modelo_final(sin_registro)
try:
    ev.filtrar_pruebas(e, 1, "inventado")
except ValueError:
    pass
else:
    raise AssertionError("Un filtro desconocido no debe devolver todas las filas en silencio")

print("OK")
