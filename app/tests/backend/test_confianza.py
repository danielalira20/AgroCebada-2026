"""Pruebas de la confianza por municipio y por parcela (M01):  python tests/backend/test_confianza.py  (desde app/)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from agrocebada_app.backend.dominio import confianza as conf  # noqa: E402
from agrocebada_app.backend.dominio.confianza import (  # noqa: E402
    COLUMNAS, MIN_ALTA, MIN_MEDIA, confianza_de_parcelas, confianza_municipios, confianza_parcela)
from agrocebada_app.backend.modelo.metricas import metricas  # noqa: E402

PALABRAS_PROHIBIDAS = ["tu parcela", "productor", "dará", "tu cosecha", "tu terreno"]   # la etiqueta habla de la estimación


def val(mae):
    """Validación inventada: por cada municipio {nombre: error}, 2 repeticiones de 4 filas con rendimientos 4 y 2."""
    filas = [dict(municipio=m, ae=ae, e=ae, real=4.0 if k % 2 == 0 else 2.0, repeticion=rep)
             for rep in (1, 2) for m, ae in mae.items() for k in range(4)]
    return pd.DataFrame(filas)


def parcelas(n):
    """Parcelas inventadas: por cada municipio {nombre: cuántas tienen cosecha}; con 0 queda una sin rendimiento."""
    filas = [{"municipio": m, "real": 3.0 if c > 0 else np.nan} for m, c in n.items() for _ in range(max(c, 1))]
    return pd.DataFrame(filas)


# --- umbrales de la regla (fijos antes de recalcular con el modelo final)
assert (MIN_ALTA, MIN_MEDIA) == (10, 3)

# --- la regla con datos inventados: 1 y 2 parcelas -> baja; 3 a 9 -> media; 10 o más según el error
d = parcelas({"U": 1, "V": 2, "T": 3, "N": 9, "A": 10, "B": 10, "Z": 0})
OA = val({"A": 0.1, "B": 0.9, "N": 0.1, "T": 0.1})
t = confianza_municipios(d, OA)
assert list(t.columns) == COLUMNAS == ["municipio", "n_cosecha", "mae_municipio", "mae_general", "nivel", "motivo",
                                       "motivo_detallado"]
f = t.set_index("municipio")
assert f.n_cosecha.to_dict() == {"A": 10, "B": 10, "N": 9, "T": 3, "U": 1, "V": 2, "Z": 0}, f.n_cosecha.to_dict()
assert f.nivel.to_dict() == {"A": "alta", "B": "media", "N": "media", "T": "media", "U": "baja", "V": "baja", "Z": "baja"}
assert set(f.nivel) <= {"alta", "media", "baja"}
assert abs(f.mae_general.iloc[0] - 0.3) < 1e-9 and (f.mae_general == f.mae_general.iloc[0]).all()
assert abs(f.mae_general.iloc[0] - metricas(OA)["MAE"]) < 1e-12          # el error general es el mismo de las métricas
assert abs(f.loc["A", "mae_municipio"] - 0.1) < 1e-9 and np.isnan(f.loc["U", "mae_municipio"])
assert f.loc["A", "motivo"] == "Confianza alta: tu municipio tiene 10 parcelas con cosecha y ahí el error fue igual o menor que el promedio."
assert f.loc["B", "motivo"] == "Confianza media: tu municipio tiene 10 parcelas con cosecha, pero ahí el error fue mayor que el promedio."
assert f.loc["A", "motivo_detallado"] == ("Confianza alta: tu municipio tiene 10 parcelas con cosecha; su error (0.10 t/ha) fue "
                                          "67% menor que el promedio general, y el 100% de esas parcelas quedó dentro de ese margen.")
assert f.loc["B", "motivo_detallado"] == ("Confianza media: tu municipio tiene 10 parcelas con cosecha; su error (0.90 t/ha) fue "
                                          "200% mayor que el promedio general, y el 100% de esas parcelas quedó dentro de ese margen.")
assert f.loc["N", "motivo"].startswith("Confianza media: tu municipio tiene sólo 9 parcelas con cosecha;")
assert f.loc["U", "motivo"] == "Confianza baja: tu municipio tiene sólo 1 parcela con cosecha."
assert f.loc["V", "motivo"] == "Confianza baja: tu municipio tiene sólo 2 parcelas con cosecha."
assert "no tiene parcelas con cosecha registrada" in f.loc["Z", "motivo"]
# un error igual al general cuenta como "menor o igual"
assert confianza_municipios(parcelas({"E": 10}), val({"E": 0.4})).nivel.tolist() == ["alta"]
# sin validación: no se rompe, no se inventa un error y con 10 o más parcelas queda en media
s = confianza_municipios(parcelas({"A": 10, "U": 1}), None).set_index("municipio")
assert s.nivel.to_dict() == {"A": "media", "U": "baja"} and s.mae_municipio.isna().all() and s.mae_general.isna().all()
assert "no hay validación suficiente" in s.loc["A", "motivo"]

# --- el motivo dice % de diferencia contra el promedio y qué parte de las parcelas quedó dentro de ese margen
# C: 5 filas con ae 0.1 y 5 con ae 0.3 (mae_municipio 0.2, sólo la mitad cae dentro); D: 10 filas con ae 0.1 constante
c_oa = pd.DataFrame({"municipio": ["C"] * 10 + ["D"] * 10, "ae": [0.1] * 5 + [0.3] * 5 + [0.1] * 10,
                     "e": [0.1] * 5 + [0.3] * 5 + [0.1] * 10, "real": [3.0] * 20, "repeticion": 1})
c_t = confianza_municipios(parcelas({"C": 10, "D": 10}), c_oa).set_index("municipio")
assert abs(c_t.loc["C", "mae_municipio"] - 0.2) < 1e-9 and abs(c_t.loc["C", "mae_general"] - 0.15) < 1e-9
assert c_t.loc["C", "nivel"] == "media"
# "motivo" (agricultor/ficha PDF) se queda breve, sin números nuevos; "motivo_detallado" (analista) sí los trae
assert c_t.loc["C", "motivo"] == "Confianza media: tu municipio tiene 10 parcelas con cosecha, pero ahí el error fue mayor que el promedio."
assert c_t.loc["C", "motivo_detallado"] == ("Confianza media: tu municipio tiene 10 parcelas con cosecha; su error (0.20 t/ha) "
                                            "fue 33% mayor que el promedio general, y el 50% de esas parcelas quedó dentro de ese margen.")
assert c_t.loc["D", "nivel"] == "alta" and "33% menor" in c_t.loc["D", "motivo_detallado"] \
    and "100% de esas parcelas" in c_t.loc["D", "motivo_detallado"] and "%" not in c_t.loc["D", "motivo"]
# error igual al general: no dice "0% menor/mayor", dice que es igual (sólo en el detallado)
e_t = confianza_municipios(parcelas({"E": 10}), val({"E": 0.4})).set_index("municipio")
assert "fue igual al promedio general" in e_t.loc["E", "motivo_detallado"] and "% menor" not in e_t.loc["E", "motivo_detallado"]
assert "%" not in e_t.loc["E", "motivo"]

# --- por parcela: la fuente de respaldo manda sobre el municipio
assert confianza_parcela(t, "A", "municipio")["nivel"] == "alta"
assert confianza_parcela(t, "A", "municipio")["motivo"] == f.loc["A", "motivo"]
assert confianza_parcela(t, "A", "municipio")["motivo_detallado"] == f.loc["A", "motivo_detallado"]
g, gl = confianza_parcela(t, "A", "grupo"), confianza_parcela(t, "A", "global")
assert g["nivel"] == gl["nivel"] == "baja" and "su grupo de registro" in g["motivo"] and "toda la región" in gl["motivo"]
assert g["motivo_detallado"] == g["motivo"] and gl["motivo_detallado"] == gl["motivo"]   # sin MAE, las dos son iguales
assert confianza_parcela(t, "Desconocido", "municipio")["nivel"] == "baja"
pred = pd.DataFrame({"municipio": ["A", "U", "B", "A"], "fuente": ["municipio", "municipio", "municipio", "grupo"]},
                    index=["p1", "p2", "p3", "p4"])
cp = confianza_de_parcelas(pred, t)
assert list(cp.index) == list(pred.index) and list(cp.columns) == ["nivel", "motivo", "motivo_detallado"]
assert cp.nivel.tolist() == ["alta", "baja", "media", "baja"]

# --- D2: una excepción cambia el nivel y/o suma una nota al motivo; la regla general no se toca
viejo = dict(conf.EXCEPCIONES)
try:
    conf.EXCEPCIONES.clear()
    conf.EXCEPCIONES["A"] = {"nivel": "media", "nota": "Nota de prueba."}
    ex = confianza_municipios(d, OA).set_index("municipio")
    assert ex.loc["A", "nivel"] == "media" and ex.loc["A", "motivo"].endswith(" Nota de prueba.")
    assert ex.loc["B", "nivel"] == "media" and ex.loc["N", "nivel"] == "media"
    conf.EXCEPCIONES["A"] = {"nota": "Solo nota."}
    assert confianza_municipios(d, OA).set_index("municipio").loc["A", "nivel"] == "alta"
finally:
    conf.EXCEPCIONES.clear()
    conf.EXCEPCIONES.update(viejo)

# --- las palabras: sólo hablan de la estimación, nunca de la parcela ni de quien la cultiva (las dos versiones)
motivos = list(f.motivo) + list(s.motivo) + list(cp.motivo) + list(f.motivo_detallado) + list(s.motivo_detallado) \
    + list(cp.motivo_detallado)
for m in motivos:
    assert m.startswith("Confianza "), m
    assert not any(p in m.lower() for p in PALABRAS_PROHIBIDAS), m

# --- con los datos reales (necesita el paquete de datos o el registro de T08, como las demás pruebas)
from agrocebada_app.backend.datos import lectura, paquete  # noqa: E402
from agrocebada_app.backend.modelo.estimador import predecir  # noqa: E402
from agrocebada_app.backend.rutas.localizador import rutas  # noqa: E402

p = lectura.leer_parcelas(rutas()["datos"])
entrena = p[p.CONJUNTO == "ENTRENAMIENTO"]
NIVEL_ESPERADO = {"Chignahuapan": "media", "Calpulalpan": "alta", "Singuilucan": "media", "Almoloya": "alta",
                  "Cuautepec de Hinojosa": "media", "Nanacamilpa de Mariano Arista": "baja"}
N_COSECHA = {"Chignahuapan": 71, "Calpulalpan": 30, "Singuilucan": 16, "Almoloya": 10, "Cuautepec de Hinojosa": 5,
             "Nanacamilpa de Mariano Arista": 1}
tablas = {}
for modelo, mae_general in [("media_mun__resp_grupo", 0.3205), ("mediana_mun__resp_grupo", 0.3126)]:
    O = paquete.validacion(modelo, p.municipio)
    assert O is not None, f"no encontré la validación de {modelo} (ni en datos_app/ ni en registro/t08)"
    OA = O[(O.escenario == "A") & (O.fuente == "municipio")]            # A · sin respaldo, igual que en la app
    t = tablas[modelo] = confianza_municipios(p, OA)
    f = t.set_index("municipio")
    assert abs(f.mae_general.iloc[0] - mae_general) < 5e-4, (modelo, f.mae_general.iloc[0])
    assert {m: f.loc[m, "n_cosecha"] for m in N_COSECHA} == N_COSECHA, f.n_cosecha.to_dict()
    assert {m: f.loc[m, "nivel"] for m in NIVEL_ESPERADO} == NIVEL_ESPERADO, f.nivel.to_dict()
    # las 59: 18 alta · 40 media · 1 baja con cualquiera de los dos modelos (con Calpulalpan en alta, D2)
    pred = predecir(p, modelo)
    cp = confianza_de_parcelas(pred, t)
    assert len(cp) == 59 and cp.nivel.value_counts().to_dict() == {"media": 40, "alta": 18, "baja": 1}, \
        (modelo, cp.nivel.value_counts().to_dict())          # si D2 baja Calpulalpan a media: 4 alta · 54 media · 1 baja
    assert pred.loc[pred.municipio == "Nanacamilpa de Mariano Arista", "fuente"].tolist() == ["municipio"]
    assert confianza_parcela(t, "Nanacamilpa de Mariano Arista", "municipio")["nivel"] == "baja"
    assert "redondeadas" in f.loc["Calpulalpan", "motivo"] and "redondeadas" in f.loc["Calpulalpan", "motivo_detallado"]
    # Chignahuapan (media) y Calpulalpan (alta) sí tienen MAE que comparar: el detallado trae el % y Dani lo pidió
    # para Analista, no para el agricultor
    assert f.loc["Chignahuapan", "motivo"] != f.loc["Chignahuapan", "motivo_detallado"]
    assert "%" not in f.loc["Chignahuapan", "motivo"] and "%" in f.loc["Chignahuapan", "motivo_detallado"]
    for m in list(t.motivo) + list(t.motivo_detallado):
        assert not any(w in m.lower() for w in PALABRAS_PROHIBIDAS), m
    # la regla no mira las 59: sin ellas la tabla de los municipios con cosecha es la misma
    sin59 = confianza_municipios(entrena, OA).set_index("municipio")
    assert sin59.equals(f.loc[sin59.index]), modelo

# --- cambiar de modelo cambia el error, no el número de parcelas
a, b = tablas["media_mun__resp_grupo"].set_index("municipio"), tablas["mediana_mun__resp_grupo"].set_index("municipio")
assert (a.n_cosecha == b.n_cosecha).all()
assert abs(a.loc["Chignahuapan", "mae_municipio"] - 0.380) < 6e-4 and abs(b.loc["Chignahuapan", "mae_municipio"] - 0.368) < 6e-4
assert abs(a.loc["Calpulalpan", "mae_municipio"] - 0.287) < 6e-4 and abs(b.loc["Calpulalpan", "mae_municipio"] - 0.267) < 6e-4
assert abs(a.loc["Singuilucan", "mae_municipio"] - 0.347) < 6e-4 and abs(b.loc["Singuilucan", "mae_municipio"] - 0.374) < 6e-4
assert a.mae_general.iloc[0] != b.mae_general.iloc[0]
print("OK")
