"""Calculadora «¿me alcanza?» (M05): con el precio por tonelada y el costo por hectárea que escribe el usuario,
cuánto deja la cosecha con la estimación y en un año bajo y uno alto de su municipio (rango de M02).
Es orientativa: no es un dictamen de crédito. No trae precios precargados."""
import pandas as pd

from agrocebada_app.backend.dominio.rangos import ANIO, rango_de

AGROCOSTOS = "https://www.fira.gob.mx/Nd/Agrocostos.jsp"
FILAS = ["Rendimiento (t/ha)", "Producción (t)", "Ingreso", "Costo", "Ingreso menos costo", "¿Cubre costos?"]
_TOL = 1e-9


def rango_municipio(d, municipio):
    """Rango de M02 del municipio, calculado sólo con las parcelas con cosecha."""
    return rango_de(d[d.CONJUNTO == "ENTRENAMIENTO"], municipio)


def columnas(rendimiento, etiqueta, rango):
    """Escenarios [(nombre, t/ha)]: la estimación (o la cosecha registrada) y, si el municipio tiene rango,
    su parte baja y su parte alta."""
    cols = [(etiqueta, float(rendimiento))]
    if rango["tipo_rango"] == "P10–P90":
        cols += [("Año bajo en tu municipio", rango["bajo"]), ("Año alto en tu municipio", rango["alto"])]
    elif rango["tipo_rango"] == "mínimo–máximo":
        cols += [("La más baja de tu municipio", rango["bajo"]), ("La más alta de tu municipio", rango["alto"])]
    return cols


def cuentas(cols, area, precio, costo_ha):
    """Tabla con FILAS como índice y una columna por escenario. Números, salvo '¿Cubre costos?' ('Sí' o 'No')."""
    costo = costo_ha * area
    datos = {}
    for nombre, rend in cols:
        produccion = rend * area
        ingreso = produccion * precio
        datos[nombre] = [rend, produccion, ingreso, costo, ingreso - costo,
                         "Sí" if ingreso >= costo - _TOL else "No"]
    return pd.DataFrame(datos, index=FILAS)


def equilibrio(precio, costo_ha):
    """Rendimiento que apenas paga el costo: costo por ha ÷ precio por t. None si el precio no es positivo."""
    return costo_ha / precio if precio and precio > 0 else None


def frase_equilibrio(d, municipio, umbral):
    """Rendimiento de equilibrio y cuántas parcelas con cosecha del municipio llegaron a él en la temporada."""
    base = f"Para cubrir el costo necesitas al menos {umbral:.2f} t/ha."
    reales = d.loc[(d.municipio == municipio) & (d.CONJUNTO == "ENTRENAMIENTO"), "real"].dropna()
    n = len(reales)
    k = int((reales >= umbral - _TOL).sum())
    if n == 0:
        return f"{base} {municipio} no tiene parcelas con cosecha para comparar."
    if n == 1:
        return f"{base} En {ANIO}, la única parcela con cosecha de {municipio} {'sí' if k else 'no'} llegó a ese rendimiento."
    if k == n:
        return f"{base} En {ANIO}, las {n} parcelas con cosecha de {municipio} llegaron a ese rendimiento."
    if k == 0:
        return f"{base} En {ANIO}, ninguna de las {n} parcelas con cosecha de {municipio} llegó a ese rendimiento."
    decimos = round(10 * k / n)
    if n >= 10 and 0 < decimos < 10:     # «de cada 10» sólo si no redondea a todas o a ninguna
        return f"{base} En {ANIO}, {decimos} de cada 10 parcelas con cosecha de {municipio} llegaron a ese rendimiento."
    return f"{base} En {ANIO}, {k} de las {n} parcelas con cosecha de {municipio} llegaron a ese rendimiento."