"""Tabla única de cifras (M03): una sola fuente de números para la app, el informe y el video, para que nunca
aparezcan cifras distintas entre documentos. No calcula nada nuevo: reúne lo que ya calculan confianza.py (M01),
rangos.py y cartera.py (M02/M10) y validacion.py (M12). cifras_parcelas trae una fila por cada una de las 197
parcelas; las 138 con cosecha llevan su valor registrado, sin confianza ni escenario porque no son una estimación."""
from pathlib import Path

import pandas as pd

from agrocebada_app.backend.dominio.cartera import cartera_municipios
from agrocebada_app.backend.dominio.confianza import confianza_de_parcelas
from agrocebada_app.backend.dominio.rangos import rangos_municipio
from agrocebada_app.backend.dominio.validacion import COLUMNAS_POBLACIONES, poblaciones

COLUMNAS_PARCELAS = ["ID_POLIGONO", "municipio", "conjunto", "area_ha", "estimacion", "modelo", "fuente",
                     "confianza", "motivo", "motivo_detallado", "rango_bajo", "rango_alto", "produccion_t",
                     "produccion_baja_t", "produccion_alta_t"]
NOMBRES = ("cifras_parcelas.csv", "cifras_municipios.csv", "cifras_validacion.csv")


def cifras_parcelas(d, pred, conf, modelo):
    """Una fila por cada una de las 197 parcelas (columnas en COLUMNAS_PARCELAS). `d`: las 197 parcelas; `pred`:
    estimaciones vigentes de las 59 (índice ID_POLIGONO); `conf`: tabla de confianza por municipio (M01); `modelo`:
    nombre del modelo vigente."""
    rangos = rangos_municipio(d[d.CONJUNTO == "ENTRENAMIENTO"]).set_index("municipio")

    pre = pred.reset_index()[["ID_POLIGONO", "municipio", "area_ha", "prediccion", "fuente"]].rename(
        columns={"prediccion": "estimacion"})
    pre["estimacion"] = pre.estimacion.round(2)   # 2 decimales, igual que el desglose (M04) y la entrega de T18
    pre["conjunto"], pre["modelo"] = "PREDICCION", modelo
    c = confianza_de_parcelas(pred, conf).reset_index(drop=True)
    pre["confianza"], pre["motivo"], pre["motivo_detallado"] = c.nivel, c.motivo, c.motivo_detallado
    pre["rango_bajo"] = pre.municipio.map(rangos.bajo)
    pre["rango_alto"] = pre.municipio.map(rangos.alto)
    pre["produccion_t"] = pre.estimacion * pre.area_ha
    con_rango = pre.rango_bajo.notna() & pre.rango_alto.notna()
    pre["produccion_baja_t"] = pre.rango_bajo.where(con_rango, pre.estimacion) * pre.area_ha
    pre["produccion_alta_t"] = pre.rango_alto.where(con_rango, pre.estimacion) * pre.area_ha

    tr = d[d.CONJUNTO == "ENTRENAMIENTO"].reset_index()[["ID_POLIGONO", "municipio", "AREA_HA", "real"]].rename(
        columns={"AREA_HA": "area_ha", "real": "estimacion"})
    tr["conjunto"], tr["modelo"], tr["fuente"] = "ENTRENAMIENTO", None, None
    tr["confianza"], tr["motivo"], tr["motivo_detallado"] = None, None, None
    tr["rango_bajo"] = tr.municipio.map(rangos.bajo)
    tr["rango_alto"] = tr.municipio.map(rangos.alto)
    tr["produccion_t"] = tr.estimacion * tr.area_ha
    tr["produccion_baja_t"], tr["produccion_alta_t"] = None, None

    t = pd.concat([pre, tr], ignore_index=True)
    return t[COLUMNAS_PARCELAS].sort_values("ID_POLIGONO").reset_index(drop=True)


def cifras_municipios(d, pred, conf):
    """Cartera por municipio con confianza y rango: la misma tabla que arma la pestaña Cartera (M10)."""
    rangos = rangos_municipio(d[d.CONJUNTO == "ENTRENAMIENTO"])
    return cartera_municipios(d, pred, rangos, conf)


def cifras_validacion(O):
    """Métricas por población validada (A/B × sin respaldo/todas); vacía si no hay validación disponible."""
    if O is None or O.empty:
        return pd.DataFrame(columns=COLUMNAS_POBLACIONES)
    return poblaciones(O)


def tablas(d, pred, conf, modelo, O):
    """Las tres tablas en un diccionario {nombre de archivo: DataFrame}, en el mismo orden que NOMBRES."""
    return {NOMBRES[0]: cifras_parcelas(d, pred, conf, modelo), NOMBRES[1]: cifras_municipios(d, pred, conf),
           NOMBRES[2]: cifras_validacion(O)}


def exportar_todo(d, pred, conf, modelo, O, carpeta):
    """Escribe las tres tablas como CSV en `carpeta` (se crea si no existe) y regresa {nombre: ruta}."""
    carpeta = Path(carpeta)
    carpeta.mkdir(parents=True, exist_ok=True)
    rutas = {}
    for nombre, tabla in tablas(d, pred, conf, modelo, O).items():
        ruta = carpeta / nombre
        tabla.to_csv(ruta, index=False)
        rutas[nombre] = ruta
    return rutas
