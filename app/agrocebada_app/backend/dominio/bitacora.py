"""Bitácora de cosecha del productor: lo que de verdad levantó cada año, anotado por él mismo.

Es la pieza que ataca la causa del error del modelo. Lo que no explicamos es siembra, variedad y manejo; un historial
por parcela es la forma de empezar a reunir esa información, y es justo el «historial confiable» que falta para
evaluar un crédito. Nada se guarda en un servidor: la bitácora vive en la sesión de quien la escribe y se descarga
como un archivo suyo, así que no hay datos personales en custodia de nadie.

Aquí sólo está el cálculo. La pantalla (los renglones, el tablero y la guía) la dibuja frontend/vistas/agricultor.
"""
import io

import pandas as pd

from agrocebada_app.backend.carga_segura.reglas import RENDIMIENTO   # qué rendimiento es creíble, una sola fuente
from agrocebada_app.backend.dominio.confianza import MIN_ALTA, MIN_MEDIA

COLUMNAS = ["anio", "toneladas", "rendimiento", "estimacion_app", "diferencia", "nota"]
ANIO = (2000, 2100)          # un año fuera de esto es un dedazo, no una cosecha
MAX_NOTA = 140


class Dato(ValueError):
    """Lo que el productor anotó no se puede usar; el mensaje dice por qué, en su idioma."""


def vacia():
    return pd.DataFrame(columns=COLUMNAS)


def nueva_entrada(anio, toneladas, area_ha, estimacion_app=None, nota=""):
    """Una anotación a partir de lo que el productor sabe: el año y cuántas toneladas levantó en toda la parcela.
    El rendimiento por hectárea se deriva de su superficie, no se le pide. `estimacion_app` es lo que la app había
    estimado para esa parcela, para poder contrastar después."""
    try:
        anio = int(anio)
    except (TypeError, ValueError):
        raise Dato("El año debe ser un número, por ejemplo 2025.")
    if not ANIO[0] <= anio <= ANIO[1]:
        raise Dato(f"El año debe estar entre {ANIO[0]} y {ANIO[1]}.")
    try:
        toneladas, area_ha = float(toneladas), float(area_ha)
    except (TypeError, ValueError):
        raise Dato("Las toneladas deben ser un número.")
    if toneladas <= 0:
        raise Dato("Las toneladas deben ser mayores que cero.")
    if area_ha <= 0:
        raise Dato("La parcela no tiene superficie registrada, así que no puedo sacar el rendimiento.")
    rendimiento = toneladas / area_ha
    if not RENDIMIENTO[0] <= rendimiento <= RENDIMIENTO[1]:
        raise Dato(f"Con {toneladas:,.2f} t en {area_ha:,.2f} ha salen {rendimiento:,.2f} t/ha, fuera de lo "
                   f"creíble para cebada ({RENDIMIENTO[0]} a {RENDIMIENTO[1]} t/ha). Revisa el dato.")
    dif = rendimiento - float(estimacion_app) if estimacion_app is not None and pd.notna(estimacion_app) else None
    return {"anio": anio, "toneladas": round(toneladas, 2), "rendimiento": round(rendimiento, 2),
            "estimacion_app": None if estimacion_app is None or pd.isna(estimacion_app) else round(float(estimacion_app), 2),
            "diferencia": None if dif is None else round(dif, 2), "nota": str(nota or "").strip()[:MAX_NOTA]}


def agregar(libreta, entrada):
    """Suma la anotación y devuelve la bitácora ordenada por año. Anotar dos veces el mismo año reemplaza: una
    parcela tiene una cosecha por año, y corregir un dedazo no debe dejar dos verdades."""
    libreta = vacia() if libreta is None or libreta.empty else libreta[libreta.anio != entrada["anio"]]
    return (pd.concat([libreta, pd.DataFrame([entrada], columns=COLUMNAS)], ignore_index=True)
            .sort_values("anio").reset_index(drop=True))


def quitar(libreta, anio):
    if libreta is None or libreta.empty:
        return vacia()
    return libreta[libreta.anio != int(anio)].reset_index(drop=True)


def resumen(libreta, valor_municipio=None):
    """Las cifras del tablero: cuántos años lleva anotados, su promedio, su mejor y peor año, qué tanto le atinó la
    app y cómo se compara con el valor típico de su municipio. Devuelve None si todavía no hay anotaciones."""
    if libreta is None or libreta.empty:
        return None
    r = libreta.rendimiento.astype(float)
    mejor, peor = libreta.loc[r.idxmax()], libreta.loc[r.idxmin()]
    con_dif = libreta[libreta.diferencia.notna()]
    return {"anios": int(len(libreta)), "promedio": float(r.mean()),
            "mejor": {"anio": int(mejor.anio), "rendimiento": float(mejor.rendimiento)},
            "peor": {"anio": int(peor.anio), "rendimiento": float(peor.rendimiento)},
            "total_toneladas": float(libreta.toneladas.astype(float).sum()),
            "error_app": float(con_dif.diferencia.astype(float).abs().mean()) if len(con_dif) else None,
            "vs_municipio": None if valor_municipio is None else float(r.mean() - float(valor_municipio)),
            "cambio": None if len(libreta) < 2 else float(r.iloc[-1] - r.iloc[0])}


def faltan_para_subir(n_cosecha):
    """Cuántas parcelas con cosecha le faltan al municipio para subir de nivel de confianza, con la misma regla de
    M01 leída hacia adelante. `condicionado` avisa que llegar a 10 habilita «alta» sólo si además su error queda
    por debajo del promedio general: el conteo abre la puerta, no la garantiza."""
    n = int(n_cosecha)
    if n < MIN_MEDIA:
        return {"faltan": MIN_MEDIA - n, "nivel": "baja", "siguiente": "media", "condicionado": False,
                "tope": MIN_MEDIA, "n": n}
    if n < MIN_ALTA:
        return {"faltan": MIN_ALTA - n, "nivel": "media", "siguiente": "alta", "condicionado": True,
                "tope": MIN_ALTA, "n": n}
    return {"faltan": 0, "nivel": None, "siguiente": None, "condicionado": False, "tope": MIN_ALTA, "n": n}


def a_csv(libreta, parcela="", municipio=""):
    """La bitácora como archivo del productor: se la lleva y la vuelve a cargar cuando quiera."""
    x = (vacia() if libreta is None else libreta).copy()
    x.insert(0, "ID_POLIGONO", parcela)
    x.insert(1, "MUNICIPIO", municipio)
    return x.to_csv(index=False).encode("utf-8")


def desde_csv(contenido):
    """Vuelve a abrir una bitácora descargada. Se queda sólo con las columnas conocidas y descarta renglones rotos:
    es el archivo de quien lo subió, pero igual no se confía en su contenido."""
    try:
        x = pd.read_csv(io.BytesIO(contenido), encoding="utf-8-sig")
    except Exception:
        raise Dato("No pude leer el archivo; debe ser la bitácora que descargaste de aquí.")
    faltan = [c for c in ("anio", "toneladas", "rendimiento") if c not in x.columns]
    if faltan:
        raise Dato(f"Al archivo le faltan columnas: {', '.join(faltan)}.")
    for c in COLUMNAS:
        if c not in x.columns:
            x[c] = None
    x = x[COLUMNAS].copy()
    for c in ("anio", "toneladas", "rendimiento", "estimacion_app", "diferencia"):
        x[c] = pd.to_numeric(x[c], errors="coerce")
    x = x[x.anio.between(*ANIO) & x.toneladas.gt(0) & x.rendimiento.between(*RENDIMIENTO)]
    if x.empty:
        raise Dato("El archivo no trae ninguna cosecha que se pueda usar.")
    x["anio"] = x.anio.astype(int)
    x["nota"] = x.nota.fillna("").astype(str).str.slice(0, MAX_NOTA)
    return x.drop_duplicates("anio", keep="last").sort_values("anio").reset_index(drop=True)
