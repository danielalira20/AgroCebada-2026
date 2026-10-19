"""Cartera por municipio: producción estimada de las 59 parcelas por estimar, con un escenario bajo y uno alto que salen
del rango de cosechas reales del municipio (M02). Es una demostración retrospectiva: no cambia las estimaciones."""
import numpy as np
import pandas as pd

COLUMNAS = ["municipio", "parcelas", "hectareas", "estimacion", "tipo_rango", "rango_bajo", "rango_alto",
            "produccion_t", "escenario_bajo_t", "escenario_alto_t", "confianza", "escenario_nota"]
NOTA_SIN_RANGO = "Sin rango: los dos escenarios usan la producción estimada."


def cartera_municipios(d, pred, rangos, confianza=None):
    """Tabla por municipio (columnas en COLUMNAS) sólo con las parcelas por estimar.
    d: las parcelas (CONJUNTO, municipio, AREA_HA); pred: estimaciones vigentes (índice = ID, columna prediccion);
    rangos: tabla de rangos_municipio (M02); confianza: opcional, tabla de M01 (municipio, nivel, motivo)."""
    p = d[d.CONJUNTO == "PREDICCION"]
    p = p.assign(prediccion=pred.prediccion.reindex(p.index))
    if p.prediccion.isna().any():
        raise ValueError("Faltan estimaciones para parcelas por estimar.")
    p = p.assign(produccion_t=p.prediccion * p.AREA_HA)
    t = p.groupby("municipio").agg(parcelas=("AREA_HA", "size"), hectareas=("AREA_HA", "sum"),
                                   produccion_t=("produccion_t", "sum")).reset_index()
    t["estimacion"] = t.produccion_t / t.hectareas
    r = rangos.set_index("municipio")
    t["tipo_rango"] = t.municipio.map(r.tipo_rango).fillna("sin rango")
    t["rango_bajo"] = t.municipio.map(r.bajo)
    t["rango_alto"] = t.municipio.map(r.alto)
    con_rango = t.rango_bajo.notna() & t.rango_alto.notna()
    t["escenario_bajo_t"] = np.where(con_rango, t.rango_bajo * t.hectareas, t.produccion_t)
    t["escenario_alto_t"] = np.where(con_rango, t.rango_alto * t.hectareas, t.produccion_t)
    t["escenario_nota"] = np.where(con_rango, "", NOTA_SIN_RANGO)
    t["confianza"] = t.municipio.map(confianza.set_index("municipio").nivel) if confianza is not None else None
    return t[COLUMNAS].sort_values("produccion_t", ascending=False).reset_index(drop=True)


def totales_cartera(t):
    """Parcelas, hectáreas, producción, escenario bajo y alto de toda la cartera y, si la tabla trae confianza, cuántas
    parcelas hay en cada nivel (mezcla_confianza, o None si no hay M01)."""
    mezcla = None
    if t.confianza.notna().any():
        mezcla = t.groupby("confianza").parcelas.sum().astype(int).to_dict()
    return {"parcelas": int(t.parcelas.sum()), "hectareas": float(t.hectareas.sum()),
            "produccion_t": float(t.produccion_t.sum()), "escenario_bajo_t": float(t.escenario_bajo_t.sum()),
            "escenario_alto_t": float(t.escenario_alto_t.sum()), "mezcla_confianza": mezcla}
