"""Pruebas de «Pregúntale a Cebi» (M19):  python tests/backend/test_respuestas.py  (desde app/)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from agrocebada_app.backend.dominio import bitacora as bit  # noqa: E402
from agrocebada_app.backend.dominio.confianza import confianza_municipios  # noqa: E402
from agrocebada_app.backend.dominio.desglose import desglose  # noqa: E402
from agrocebada_app.backend.dominio.rangos import ANIO  # noqa: E402
from agrocebada_app.backend.dominio.respuestas import (CONTEXTO, P_CLIMA, P_EQUILIBRIO, P_ESCENARIOS,  # noqa: E402
                                                       P_LIBRETA, P_MARGEN, P_MEJORAR, P_PLAN, P_SATELITE,
                                                       _cuanto_falta, respuestas, respuestas_cuenta, saludo)

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
assert [p for p, _ in lista] == ["¿Por qué mi parcela tiene 5.50?", "¿Cuántas toneladas me van a salir?",
                                 "¿Por qué mi vecino tiene el mismo número?", "¿Qué tanto puedo confiar?",
                                 P_MARGEN, "¿Me alcanza para mis costos?", P_SATELITE, P_CLIMA, P_MEJORAR]
assert res["¿Por qué mi parcela tiene 5.50?"] == (f"Se tomó el valor típico (la mediana) de las 10 parcelas con "
                                                  f"cosecha registrada de M en {ANIO}. {x['frase']}")
assert res["¿Qué tanto puedo confiar?"].startswith(f"{x['motivo']} {x['rango']}")   # lo mismo que M01 y M02
assert "parcelas suficientes" in res["¿Qué tanto puedo confiar?"]                  # y lo que falta (M tiene 10)
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

# --- la cosecha en toneladas: 5.5 t/ha × 5 ha, y la superficie de la calculadora manda sobre la de la parcela
assert res["¿Cuántas toneladas me van a salir?"].startswith(
    "Con 5.50 t/ha en 5.00 ha, te saldrían unas 27.50 toneladas en total."), res["¿Cuántas toneladas me van a salir?"]
tot = dict(respuestas(d, pred, MOD, conf, "P1", area=2))["¿Cuántas toneladas me van a salir?"]
assert tot.startswith("Con 5.50 t/ha en 2.00 ha, te saldrían unas 11.00 toneladas en total."), tot

# --- el margen: sin error medido no inventa un número
assert res[P_MARGEN].startswith("No tengo medido el error del método en M,"), res[P_MARGEN]
pe = pred.assign(error_tipico=[0.40, 0.40])
m = dict(respuestas(d, pe, MOD, conf, "P1"))[P_MARGEN]
assert m.startswith("En M el método se equivoca en promedio 0.40 t/ha, que en tus 5.00 ha son unas "
                    "2.00 toneladas arriba o abajo."), m
assert "A $6,000 por tonelada, eso es como $12,000." in dict(
    respuestas(d, pe, MOD, conf, "P1", precio=6000))[P_MARGEN]
assert "No es un tope, es un promedio" in m

# --- el satélite: sin series de verdor lo dice en lugar de suponer
assert res[P_SATELITE] == "No tengo imágenes de satélite de tu parcela para decirte cómo se vio."

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
assert reg[1] == ("¿Cuántas toneladas saqué en total?",
                  "Con 3.00 t/ha en 5.00 ha, fueron unas 15.00 toneladas en total. Las t/ha son por hectárea; el "
                  "total es lo que acabas subiendo al camión. Si sembraste otra superficie, cámbiala en la "
                  "calculadora «¿Me alcanza?» de esta página y te rehago la cuenta."), reg[1]
assert reg[0] == ("¿Cómo le fue a mi parcela frente a las de mi municipio?",
                  f"Tu parcela dio 3.00 t/ha en {ANIO}. De las otras 9 parcelas con cosecha de M, 2 dieron menos y "
                  "7 dieron más. Si no la conociera, el método habría estimado 3.40 t/ha (+0.40)."), reg[0]
assert len(reg) == 7
assert saludo(d, pred, MOD, conf, "M3") == (f"Hola, soy Cebi. Tu parcela M3 tiene su cosecha registrada: 3.00 t/ha "
                                            f"en {ANIO}. ¿Qué quieres saber?")

# --- cuánto falta para subir de confianza (usa faltan_para_subir de «Tu libreta»)
assert _cuanto_falta(1, "N") == "Con 2 parcelas más con cosecha registrada, N pasaría de confianza baja a media."
assert _cuanto_falta(2, "N").startswith("Con 1 parcela más con cosecha registrada")
assert _cuanto_falta(5, "C") == ("Con 5 parcelas más con cosecha registrada, C pasaría de confianza media a alta, "
                                 "siempre que el error ahí quede igual o por debajo del promedio.")
assert _cuanto_falta(71, "tu municipio").startswith("Tu municipio ya tiene parcelas suficientes")

# --- lo que el agricultor anotó en «Tu libreta»: 2024 → 4.0 t/ha (la app dijo 3.5); 2025 → 4.5 t/ha (la app dijo 4.0)
lib = bit.agregar(None, bit.nueva_entrada(2024, 20, 5, 3.5))
lib = bit.agregar(lib, bit.nueva_entrada(2025, 22.5, 5, 4.0))
assert P_LIBRETA not in dict(respuestas(d, pred, MOD, conf, "P1"))                 # sin anotaciones no aparece
rl = dict(respuestas(d, pred, MOD, conf, "P1", libreta=lib))[P_LIBRETA]
assert rl == ("Anotaste 2 años. Tu promedio fue 4.25 t/ha; tu mejor año fue 2025 con 4.50 t/ha y el más bajo, 2024 "
              "con 4.00 t/ha. Lo que estimó la app quedó, en promedio, a 0.50 t/ha de lo que anotaste. Tu promedio "
              f"está 1.25 t/ha abajo del valor típico de las parcelas con cosecha de M en {ANIO} (5.50 t/ha)."), rl
assert P_LIBRETA in dict(respuestas(d, pred, MOD, conf, "M3", libreta=lib))         # también en parcelas registradas

# --- «Mi cuenta»: siempre tres preguntas, con la misma cuenta que la calculadora «¿Me alcanza?» (planeador)
nombres = [P_EQUILIBRIO, P_ESCENARIOS, P_PLAN]
sin = respuestas_cuenta(d, pred, "P1")
assert [p for p, _ in sin] == nombres
assert all("Escribe tu precio por tonelada y tu costo por hectárea" in t for _, t in sin), sin   # sin datos no inventa
assert all("Escribe tu superficie" in t for _, t in respuestas_cuenta(d, pred, "P1", precio=6000, costo=18000,
                                                                      area_pendiente=True))    # superficie borrada
cu = dict(respuestas_cuenta(d, pred, "P1", precio=6000, costo=18000, area=5))
assert cu[P_EQUILIBRIO].startswith("Para cubrir el costo necesitas al menos 3.00 t/ha."), cu[P_EQUILIBRIO]
assert "Tu estimación (5.50 t/ha) queda por encima de ese punto." in cu[P_EQUILIBRIO]
assert cu[P_EQUILIBRIO].endswith("Es orientativo; no es un dictamen de crédito.")
assert cu[P_ESCENARIOS].startswith("En M, 8 de 10 parcelas con cosecha dieron entre 1.90 y 9.10 t/ha"), cu[P_ESCENARIOS]
assert "un rendimiento bajo de tu municipio (1.90 t/ha) te faltarían $33,000." in cu[P_ESCENARIOS]
assert "tu estimación (5.50 t/ha) te quedarían $75,000." in cu[P_ESCENARIOS]
assert "un rendimiento alto de tu municipio (9.10 t/ha) te quedarían $183,000." in cu[P_ESCENARIOS]
assert cu[P_ESCENARIOS].endswith(f"Son referencias de lo que pasó en {ANIO}; no dicen cuál te tocará.")
# con la misma cuenta que la calculadora: lo que dice «Mis costos» y lo que dice «Mi cuenta» coincide
assert "quedan $75,000" in dict(respuestas(d, pred, MOD, conf, "P1", precio=6000, costo=18000, area=5))[
    "¿Me alcanza para mis costos?"]
# el plan sale del escenario bajo (el que falta aun cuando la referencia cubre) y trae sus tres pasos y la nota
assert cu[P_PLAN].startswith("Con el escenario bajo") and "te faltarían $33,000." in cu[P_PLAN], cu[P_PLAN]
assert cu[P_PLAN].count("\n") == 4 and "\n1. " in cu[P_PLAN] and "\n3. " in cu[P_PLAN]
assert cu[P_PLAN].endswith("no garantiza apoyos ni resultados de cosecha.")
# si la referencia misma no alcanza, el equilibrio lo dice y queda por debajo
mal = dict(respuestas_cuenta(d, pred, "P1", precio=6000, costo=40000, area=5))
assert "necesitas al menos 6.67 t/ha" in mal[P_EQUILIBRIO] and "queda por debajo de ese punto" in mal[P_EQUILIBRIO]
assert "(5.50 t/ha) te faltarían $35,000." in mal[P_ESCENARIOS]
# nada de lo prohibido en el método: ni predicciones del año ni recomendaciones de siembra
for _, t in list(cu.items()) + list(mal.items()):
    for frase in ("vas a perder cosecha", "conviene revisar", "se recomienda sembrar", "será buena", "será mala"):
        assert frase not in t, frase
# parcela con cosecha registrada: la cuenta parte de lo que sacó
assert "Tu cosecha registrada (3.00 t/ha)" in dict(respuestas_cuenta(d, pred, "M3", precio=6000, costo=40000,
                                                                      area=5))[P_EQUILIBRIO]
# la superficie borrada en la calculadora también deja pendiente «Mis costos»
assert "Escribe tu superficie" in dict(respuestas(d, pred, MOD, conf, "P1", precio=6000, costo=18000,
                                                  area_pendiente=True))["¿Me alcanza para mis costos?"]
print("OK")
