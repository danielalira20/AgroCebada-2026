"""Referencias municipales y preparación de cuentas sin depender de una parcela."""
from numbers import Real

import numpy as np

from agrocebada_app.backend.dominio.calculadora import columnas, cuentas, equilibrio, rango_municipio
from agrocebada_app.backend.modelo.estimador import estadistico
from agrocebada_app.config import MODELOS_CANDIDATOS, TEMPORADA


def _finito(valor):
    if isinstance(valor, (bool, np.bool_)) or not isinstance(valor, Real):
        return False
    try:
        return bool(np.isfinite(valor))
    except (TypeError, OverflowError):
        return False


def _entrenamiento(d):
    tr = d[d.CONJUNTO == "ENTRENAMIENTO"]
    if any(not _finito(v) or v <= 0 for v in tr.real):
        raise ValueError("Las cosechas registradas deben ser números finitos y positivos.")
    return tr


def estimacion_municipio(d, municipio, modelo):
    """Referencia histórica local; sin cosechas devuelve sin_soporte, sin respaldo de otras zonas."""
    if modelo not in MODELOS_CANDIDATOS:
        raise ValueError("El modelo no es uno de los candidatos del proyecto.")
    tr = _entrenamiento(d)
    cosechas = tr.loc[tr.municipio == municipio, "real"]
    n = len(cosechas)
    rendimiento = float(estadistico(modelo)(cosechas)) if n else None
    if rendimiento is not None and not np.isfinite(rendimiento):
        raise ValueError("No se pudo calcular una referencia municipal finita.")
    return {"estado": "disponible" if n else "sin_soporte", "municipio": municipio,
            "campania_base": int(TEMPORADA[0][:4]), "modelo": modelo,
            "rendimiento_t_ha": rendimiento, "fuente": "municipio" if n else None,
            "n_cosecha_municipio": n, "n_cosecha_fuente": n}


def evaluar_cuenta(d, municipio, rendimiento, etiqueta, area, precio, costo):
    """Valida captura y compone las cuentas existentes; no formatea ni modifica los datos."""
    errores = {}
    pendiente = False
    for campo, valor in (("area", area), ("precio", precio), ("costo", costo)):
        if valor is None:
            pendiente = True
        elif not _finito(valor):
            errores[campo] = "Escribe un número finito válido."
        elif valor < 0 or (campo == "area" and valor < 0.01):
            errores[campo] = "La superficie mínima es 0.01 ha." if campo == "area" else "Escribe un valor mayor que cero."
        elif valor == 0:
            pendiente = True
    resultado = {"estado": "invalida" if errores else "pendiente", "errores": errores,
                 "tabla": None, "rango": None, "umbral": None}
    if errores or pendiente:
        return resultado
    if not _finito(rendimiento) or rendimiento <= 0:
        raise ValueError("La referencia de rendimiento debe ser finita y positiva.")
    _entrenamiento(d)
    rango = rango_municipio(d, municipio)
    with np.errstate(over="ignore", invalid="ignore"):
        tabla = cuentas(columnas(rendimiento, etiqueta, rango), area, precio, costo)
        umbral = equilibrio(precio, costo)
    if not np.isfinite(tabla.iloc[:5].to_numpy(dtype=float)).all() or not np.isfinite(umbral):
        resultado.update(estado="invalida", errores={"cuenta": "Los valores son demasiado grandes para calcular la cuenta."})
        return resultado
    return {"estado": "calculada", "errores": {}, "tabla": tabla, "rango": rango, "umbral": umbral}
