"""Validación del modelo (M12): las poblaciones con su nombre completo, la tabla por municipio con su confianza, la
regla de confianza escrita y el contraste del caso de información insuficiente. Es lógica sin Streamlit: la pantalla
la dibuja frontend/vistas/analista/pestanas/validacion.py. Ninguna cifra se escribe a mano: todo sale de la validación."""
import numpy as np
import pandas as pd

from agrocebada_app.backend.dominio.confianza import MIN_ALTA, MIN_MEDIA, confianza_parcela
from agrocebada_app.backend.modelo.metricas import metricas

ESCENARIOS = {"A": "A · municipio conocido", "B": "B · zona de lluvia nueva"}
SUBCONJUNTOS = {"sin respaldo": "sin respaldo", "todas": "todas las predicciones"}
# La primera es la principal: son las predicciones cuyo municipio sí tenía parcelas con cosecha, como las 59.
POBLACIONES = [("A", "sin respaldo"), ("A", "todas"), ("B", "sin respaldo"), ("B", "todas")]
COLUMNAS_POBLACIONES = ["poblacion", "parcelas", "predicciones", "MAE", "RMSE", "sesgo", "R2", "principal"]
COLUMNAS_MUNICIPIOS = ["municipio", "n_cosecha", "mae_municipio", "dentro", "confianza"]


def _etiqueta(nivel):
    return str(nivel).capitalize()


def poblaciones(O):
    """Una fila por población validada (nombre completo, parcelas distintas, predicciones y métricas). La primera es
    la principal (A · sin respaldo). `parcelas` cuenta parcelas distintas; `predicciones`, las filas de las 5 × 5."""
    filas = []
    for esc, sub in POBLACIONES:
        x = O[O.escenario == esc]
        if sub == "sin respaldo":
            x = x[x.fuente == "municipio"]
        if x.empty:
            continue
        filas.append({"poblacion": f"{ESCENARIOS[esc]} · {SUBCONJUNTOS[sub]}", "parcelas": int(x.ID_POLIGONO.nunique()),
                      "predicciones": len(x), **metricas(x).to_dict(), "principal": (esc, sub) == POBLACIONES[0]})
    return pd.DataFrame(filas, columns=COLUMNAS_POBLACIONES)


def descripcion_principal(pob):
    """Frase que dice cuál es la población principal y de cuántas parcelas sale; vacía si no hay."""
    p = pob[pob.principal]
    if p.empty:
        return ""
    f = p.iloc[0]
    return f"{f.poblacion}: {f.parcelas} parcelas, la población que corresponde a las estimaciones reales."


def por_municipio(conf, cob_mun):
    """Tabla por municipio con su error, la parte de parcelas que cae dentro de ± su error y su confianza. `conf`: tabla
    de M01; `cob_mun`: parte (0–1) de predicciones dentro de ± el error del municipio. Los municipios sin validación
    propia (una sola parcela con cosecha) aparecen con la confianza que les toca y sin error."""
    t = conf[["municipio", "n_cosecha", "mae_municipio", "nivel"]].copy()
    cob = cob_mun.reindex(t.municipio).to_numpy(dtype=float)
    t["dentro"] = [f"{round(v * 100):.0f} %" if pd.notna(v) else "—" for v in cob]
    t["confianza"] = t.nivel.map(_etiqueta)
    t = t.sort_values(["n_cosecha", "municipio"], ascending=[False, True])
    return t[COLUMNAS_MUNICIPIOS].reset_index(drop=True)


def regla_confianza(mae_general=np.nan):
    """La regla de M01 en lenguaje simple, una frase por nivel. Los umbrales son los mismos de confianza.py."""
    error = f"{mae_general:.3f} t/ha" if pd.notna(mae_general) else "el error general"
    return [f"Alta: el municipio tiene {MIN_ALTA} o más parcelas con cosecha y su error (MAE) es igual o menor al "
            f"error general, {error}.",
            f"Media: tiene {MIN_ALTA} o más parcelas con cosecha pero su error es mayor al general, o tiene de "
            f"{MIN_MEDIA} a {MIN_ALTA - 1} parcelas.",
            f"Baja: tiene {MIN_MEDIA - 1} o menos parcelas con cosecha, o la estimación usa el valor del grupo o de "
            "toda la región."]


def contraste_respaldo(O, pred):
    """Cifras del caso de información insuficiente: qué pasó en la validación con las predicciones que no tuvieron
    parcelas con cosecha en su municipio (A, respaldo) y cuántas de las estimaciones reales usan respaldo."""
    A = O[O.escenario == "A"]
    resp, con = A[A.fuente != "municipio"], A[A.fuente == "municipio"]
    return {"predicciones": len(resp), "parcelas": int(resp.ID_POLIGONO.nunique()),
            "mae": float(resp.ae.mean()) if len(resp) else np.nan,
            "mae_municipio": float(con.ae.mean()) if len(con) else np.nan,
            "estimaciones": len(pred), "estimaciones_con_respaldo": int((pred.fuente != "municipio").sum())}


def frase_respaldo(c):
    """Dos frases con el contraste. No afirma que el respaldo sea mejor o peor: con pocas parcelas no se puede saber,
    y por eso la confianza es baja."""
    n = c["estimaciones"]
    if c["estimaciones_con_respaldo"]:
        reales = f"{c['estimaciones_con_respaldo']} de las {n} estimaciones reales usan respaldo."
    else:
        reales = (f"Ninguna de las {n} estimaciones reales usa respaldo: todas se apoyan en parcelas con cosecha de "
                  "su propio municipio.")
    if not c["predicciones"]:
        return ("En la validación todas las predicciones tuvieron parcelas con cosecha en su municipio. " + reales)
    uno = c["parcelas"] == 1
    parcelas = f"{c['parcelas']} parcela{'' if uno else 's'}"
    pocas = (f" Con {'sólo ' if c['parcelas'] < MIN_MEDIA else ''}{parcelas} no alcanza para comparar: la confianza es "
             "baja por falta de evidencia, no porque el error haya sido mayor.") if c["parcelas"] < MIN_ALTA else ""
    return (f"En la validación, {parcelas} no {'tuvo' if uno else 'tuvieron'} otras con cosecha en su municipio y "
            f"se {'estimó' if uno else 'estimaron'} con el valor del grupo ({c['predicciones']} predicciones, MAE "
            f"{c['mae']:.2f} t/ha, frente a {c['mae_municipio']:.2f} t/ha cuando sí había datos del "
            f"municipio).{pocas} {reales}")


def comparacion_oculto(pred, sim, conf, municipio):
    """(tabla, motivo) del municipio oculto: estimación y confianza normales, y las que tendría sin sus datos.
    `pred`: las 59 normales; `sim`: las 59 con el municipio fuera del entrenamiento (mismo índice)."""
    p = pred[pred.municipio == municipio]
    s = sim.loc[p.index]
    sin = [confianza_parcela(conf, municipio, f) for f in s.fuente]
    normal = [confianza_parcela(conf, municipio, f) for f in p.fuente]
    t = pd.DataFrame({"estimación normal": p.prediccion, "confianza normal": [_etiqueta(x["nivel"]) for x in normal],
                      "sin datos del municipio": s.prediccion, "fuente sin datos": s.fuente,
                      "confianza sin datos": [_etiqueta(x["nivel"]) for x in sin]}).round(2)
    return t, (sin[0]["motivo"] if sin else "")
