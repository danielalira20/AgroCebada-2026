"""Pruebas de «Pregúntale a Cebi» (M19):  python tests/backend/test_respuestas.py  (desde app/)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from agrocebada_app.backend.dominio.confianza import confianza_municipios  # noqa: E402
from agrocebada_app.backend.dominio.desglose import desglose  # noqa: E402
from agrocebada_app.backend.dominio.rangos import ANIO  # noqa: E402
from agrocebada_app.backend.dominio.respuestas import (CONTEXTO, P_CLIMA, P_MEJORAR, _cuanto_falta,  # noqa: E402
                                                       respuestas, saludo)

MOD = "mediana_mun__resp_grupo"
# --- datos inventados: municipio M con 10 parcelas con cosecha (1 a 10 t/ha) y dos por estimar
d = pd.DataFrame({"municipio": ["M"] * 12, "CONJUNTO": ["ENTRENAMIENTO"] * 10 + ["PREDICCION"] * 2,
                  "real": [float(i) for i in range(1, 11)] + [np.nan, np.nan], "AREA_HA": [5.0] * 12},
                 index=[f"M{i}" for i in range(1, 11)] + ["P1", "P2"])
pred = pd.DataFrame({"prediccion": [5.5, 5.5], "fuente": ["municipio"] * 2, "n_municipio": [10, 10]}, index=["P1", "P2"])
conf = confianza_municipios(d, None)
x = desglose(d, pred, MOD, conf, "P1")

# --- saludo con el resumen
assert saludo(d, pred, MOD, conf, "P1") == ("Hola, soy Cebi. Tu parcela P1 tiene una estimación de 5.50 t/ha, "
                                            f"con confianza {x['nivel']}. ¿Qué quieres saber?")

# --- parcela por estimar
lista = respuestas(d, pred, MOD, conf, "P1")
res = dict(lista)
assert [p for p, _ in lista] == ["¿Por qué mi parcela tiene 5.50?", "¿Por qué mi vecino tiene el mismo número?",
                                 "¿Qué tanto puedo confiar?", "¿Me alcanza para mis costos?", P_CLIMA, P_MEJORAR]
assert res["¿Por qué mi parcela tiene 5.50?"] == (f"Se tomó el valor típico (la mediana) de las 10 parcelas con cosecha registrada de M "
                                                  f"en {ANIO}. {x['frase']}")
assert res["¿Qué tanto puedo confiar?"] == f"{x['motivo']} {x['rango']}"         # lo mismo que M01 y M02
assert res["¿Por qué mi vecino tiene el mismo número?"].startswith(
    "Porque las 2 parcelas por estimar de M reciben el mismo número, 5.50 t/ha.")
assert "Escribe tu precio" in res["¿Me alcanza para mis costos?"]               # sin datos no inventa nada
assert res[P_CLIMA] == "No tengo el clima de tu zona para comparar."
assert "Hoy M tiene 10 parcelas con cosecha registrada" in res[P_MEJORAR]
assert "«Tu libreta»" in res[P_MEJORAR]

# --- una sola parcela por estimar en el municipio
assert dict(respuestas(d, pred.loc[["P1"]], MOD, conf, "P1"))["¿Por qué mi vecino tiene el mismo número?"].startswith(
    "Tu parcela es la única por estimar en M.")

# --- costos: la misma cuenta que la calculadora (5.5 t/ha × 5 ha × $6,000 = $165,000 contra $90,000)
c = dict(respuestas(d, pred, MOD, conf, "P1", precio=6000, costo=18000, area=5))["¿Me alcanza para mis costos?"]
assert c.startswith("Con 5.50 t/ha en 5.00 ha, el ingreso sería $165,000 contra un costo de $90,000: "
                    "sí cubre tus costos y quedan $75,000."), c
c2 = dict(respuestas(d, pred, MOD, conf, "P1", precio=6000, costo=40000, area=5))["¿Me alcanza para mis costos?"]
assert "no cubre tus costos: faltarían $35,000." in c2, c2

# --- clima de M07: agosto 25 % más seco que el promedio
clima = pd.DataFrame({"id_parcela": "P1", "periodo": ["2025-08"], "PREC": [75.0], "Tmax": [24.0], "Tmin": [10.0]})
normal = pd.DataFrame({"id_parcela": "P1", "mes": [8], "PREC": [100.0], "Tmax": [24.0], "Tmin": [10.0]})
rc = dict(respuestas(d, pred, MOD, conf, "P1", clima=clima, normal=normal))[P_CLIMA]
assert rc == "Agosto fue 25 % más seco que el promedio 2022–2024 en tu zona. Es contexto: no cambia tu estimación.", rc

# --- fuera de las preguntas de contexto, nada presenta clima, verdor ni área como factores
for preg, texto in lista:
    if preg not in CONTEXTO:
        for palabra in ("clima", "lluvia", "verdor", "el área"):
            assert palabra not in texto.lower(), (preg, palabra)

# --- parcela con cosecha registrada: cómo quedó frente a su municipio
reg = respuestas(d, pred, MOD, conf, "M3", oof=pd.Series({"M3": 3.4}))
assert reg[0] == ("¿Cómo le fue a mi parcela frente a las de mi municipio?",
                  f"Tu parcela dio 3.00 t/ha en {ANIO}. De las otras 9 parcelas con cosecha de M, 2 dieron menos y "
                  "7 dieron más. Si no la conociera, el método habría estimado 3.40 t/ha (+0.40)."), reg[0]
assert len(reg) == 5
assert saludo(d, pred, MOD, conf, "M3") == (f"Hola, soy Cebi. Tu parcela M3 tiene su cosecha registrada: 3.00 t/ha "
                                            f"en {ANIO}. ¿Qué quieres saber?")
# --- cuánto falta para subir de confianza (usa faltan_para_subir de «Tu libreta»)
assert _cuanto_falta(1, "N") == "Con 2 parcelas más con cosecha registrada, N pasaría de confianza baja a media."
assert _cuanto_falta(2, "N").startswith("Con 1 parcela más con cosecha registrada")
assert _cuanto_falta(5, "C") == ("Con 5 parcelas más con cosecha registrada, C pasaría de confianza media a alta, "
                                 "siempre que el error ahí quede igual o por debajo del promedio.")
assert _cuanto_falta(71, "Ch").startswith("Ch ya tiene parcelas suficientes")
print("OK")