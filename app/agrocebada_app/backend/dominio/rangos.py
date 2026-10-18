"""Rango de cosechas reales por municipio: percentiles 10 y 90 (o mínimo y máximo si hay pocas parcelas) del
rendimiento registrado en 2025, calculados sólo con las parcelas con cosecha. Es contexto: no usa las estimaciones
del modelo y no cambia al cambiar de modelo."""
import numpy as np
import pandas as pd

from agrocebada_app.backend.modelo.estimador import estadistico
from agrocebada_app.config import TEMPORADA

MIN_PERCENTILES = 10   # con 10 o más parcelas con cosecha: P10–P90
MIN_EXTREMOS = 3       # de 3 a 9: mínimo–máximo; con menos no alcanza para dar un rango
COLUMNAS = ["municipio", "n_cosecha", "tipo_rango", "bajo", "alto", "dentro", "texto"]
ANIO = TEMPORADA[0][:4]
_TOL = 1e-9            # para que un valor justo en el extremo cuente como dentro pese al redondeo de coma flotante


def _t(x):
    """Cifra para el texto, con dos decimales."""
    return f"{x:.2f}"


def _fila(municipio, r):
    r = pd.Series(r).dropna().astype(float)
    n = len(r)
    if n >= MIN_PERCENTILES:
        tipo, (bajo, alto) = "P10–P90", np.percentile(r, [10, 90])
    elif n >= MIN_EXTREMOS:
        tipo, bajo, alto = "mínimo–máximo", r.min(), r.max()
    else:
        tipo, bajo, alto = "sin rango", np.nan, np.nan
    if tipo == "sin rango":
        dentro = 0
        if n == 0:
            texto = f"{municipio} no tiene parcelas con cosecha registrada: no alcanza para dar un rango."
        else:
            texto = (f"{municipio} sólo tiene {n} parcela{'s' if n > 1 else ''} con cosecha: "
                     "no alcanza para dar un rango.")
        return {"municipio": municipio, "n_cosecha": n, "tipo_rango": tipo, "bajo": np.nan, "alto": np.nan,
                "dentro": dentro, "texto": texto}
    dentro = int(((r >= bajo - _TOL) & (r <= alto + _TOL)).sum())
    igual = _t(bajo) == _t(alto)
    cifras = f"{float(_t(bajo)):g} t/ha" if igual else f"entre {_t(bajo)} y {_t(alto)} t/ha"
    if dentro == n:
        texto = f"Las {n} parcelas con cosecha de {municipio} dieron {cifras} en {ANIO}."
    else:
        texto = f"En {municipio}, {dentro} de {n} parcelas con cosecha dieron {cifras} en {ANIO}."
    return {"municipio": municipio, "n_cosecha": n, "tipo_rango": tipo, "bajo": float(bajo), "alto": float(alto),
            "dentro": dentro, "texto": texto}


def rangos_municipio(d, col="real"):
    """Tabla por municipio (columnas: municipio, n_cosecha, tipo_rango, bajo, alto, dentro, texto) con las parcelas
    de `d` que tienen rendimiento registrado en `col`. Pasa sólo las parcelas con cosecha (ENTRENAMIENTO)."""
    x = d[["municipio", col]].dropna()
    filas = [_fila(m, g[col]) for m, g in x.groupby("municipio", sort=True)]
    return pd.DataFrame(filas, columns=COLUMNAS)


def rango_de(d, municipio, col="real"):
    """Fila del municipio como diccionario; si no tiene parcelas con cosecha, una fila 'sin rango' que lo explica."""
    return _fila(municipio, d.loc[d.municipio == municipio, col])


def cerca_del_municipio(d, modelo, distancia, estricto=True, col="real"):
    """(porcentaje, frase): qué parte de las parcelas con cosecha queda cerca del valor de su municipio, o sea de la
    media o la mediana (según `modelo`) de las parcelas con cosecha de ese municipio. `estricto` = 'a menos de';
    si no, 'a X o menos'. Porcentaje en 0–100, sin redondear; None si no hay parcelas."""
    x = d[["municipio", col]].dropna()
    if x.empty:
        return None, "No hay parcelas con cosecha para comparar."
    valor = x.groupby("municipio")[col].transform(estadistico(modelo))
    dif = (x[col] - valor).abs().round(9)
    cerca = dif < distancia if estricto else dif <= distancia
    pct = float(cerca.mean() * 100)
    nombre = "mediana" if modelo.startswith("mediana") else "media"
    corte = f"a menos de {distancia:g} t/ha" if estricto else f"a {distancia:g} t/ha o menos"
    frase = (f"El {pct:.0f} % de las parcelas con cosecha quedó {corte} de la {nombre} de su municipio "
             f"(corte {'estricto' if estricto else 'incluyente'}).")
    return pct, frase
