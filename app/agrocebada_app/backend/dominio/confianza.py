"""Confianza de la estimación por municipio y por parcela (M01): una etiqueta alta / media / baja con su motivo en
una frase. Sólo usa resultados de validación (escenario A · sin respaldo) y el conteo de parcelas con cosecha: no mira
las 59 estimaciones. Los MAE salen del modelo vigente, así que al cambiar de modelo cambian ellos y no el conteo.
La etiqueta habla de la estimación, nunca de la parcela ni de quien la cultiva."""
import numpy as np
import pandas as pd

from agrocebada_app.backend.modelo.metricas import metricas

# Umbrales de la regla. Se fijan antes de recalcular con el modelo final y no se ajustan por municipio.
MIN_ALTA = 10    # con 10 o más parcelas con cosecha el error del municipio se compara con el error general
MIN_MEDIA = 3    # de 3 a 9 parcelas: media; con 1 o 2: baja

# D2 (pendiente de decidir): excepciones puntuales. Cada municipio puede cambiar su `nivel` y/o sumar una `nota` al
# motivo. La regla general queda intacta: para bajar a Calpulalpan a media, agregar "nivel": "media" a su entrada.
EXCEPCIONES = {
    "Calpulalpan": {"nota": "Sus cosechas vienen redondeadas a medias toneladas, así que el error medido se lee con cuidado."},
}

NIVELES = ("alta", "media", "baja")
COLUMNAS = ["municipio", "n_cosecha", "mae_municipio", "mae_general", "nivel", "motivo", "motivo_detallado"]
_TOL = 1e-9      # un MAE igual al general cuenta como "menor o igual" pese al redondeo de coma flotante


def _parcelas(n):
    return f"{n} parcela{'s' if n != 1 else ''}"


def _regla(n, mae_mun, mae_gen, dentro=np.nan):
    """(nivel, motivo, motivo_detallado) de un municipio con `n` parcelas con cosecha, su MAE, el error general y la
    parte de sus predicciones que quedó dentro de ± su propio MAE (pueden ser NaN). `motivo` es la frase breve, para
    el agricultor y la ficha PDF; `motivo_detallado` agrega el MAE, el % de diferencia contra el promedio general y
    ese `dentro` (la misma cifra que ya muestra Validación, no una nueva), para la vista Analista. Sin un MAE que
    comparar, las dos frases son la misma: no hay número que mostrar de más."""
    if n == 0:
        m = ("Confianza baja: tu municipio no tiene parcelas con cosecha registrada; la estimación se apoya "
            "en otras zonas.")
        return "baja", m, m
    if n < MIN_MEDIA:
        m = f"Confianza baja: tu municipio tiene sólo {_parcelas(n)} con cosecha."
        return "baja", m, m
    if n < MIN_ALTA:
        m = (f"Confianza media: tu municipio tiene sólo {_parcelas(n)} con cosecha; con pocas parcelas "
            "la estimación es menos firme.")
        return "media", m, m
    if pd.isna(mae_mun) or pd.isna(mae_gen):
        m = (f"Confianza media: tu municipio tiene {_parcelas(n)} con cosecha, pero no hay validación "
            "suficiente para medir el error ahí.")
        return "media", m, m
    if mae_mun <= mae_gen + _TOL:
        nivel = "alta"
        motivo = (f"Confianza alta: tu municipio tiene {_parcelas(n)} con cosecha y ahí el error fue igual o "
                 "menor que el promedio.")
    else:
        nivel = "media"
        motivo = (f"Confianza media: tu municipio tiene {_parcelas(n)} con cosecha, pero ahí el error fue mayor "
                 "que el promedio.")
    if abs(mae_mun - mae_gen) < _TOL:
        cambio = "fue igual al promedio general"
    else:
        pct = abs(mae_mun - mae_gen) / mae_gen * 100
        cambio = f"fue {pct:.0f}% {'menor' if mae_mun < mae_gen else 'mayor'} que el promedio general"
    extra = f", y el {dentro * 100:.0f}% de esas parcelas quedó dentro de ese margen" if pd.notna(dentro) else ""
    detallado = (f"Confianza {nivel}: tu municipio tiene {_parcelas(n)} con cosecha; su error ({mae_mun:.2f} t/ha) "
                f"{cambio}{extra}.")
    return nivel, motivo, detallado


def confianza_municipios(d, OA, col="real"):
    """Tabla por municipio (columnas: municipio, n_cosecha, mae_municipio, mae_general, nivel, motivo).
    `d`: las parcelas (se cuentan las que tienen rendimiento registrado en `col`). `OA`: validación del modelo vigente
    en A · sin respaldo (con columnas municipio, ae, repeticion, e, real), o None si no hay. mae_municipio queda vacío
    si el municipio no aparece en la validación; mae_general es el MAE de A · sin respaldo, igual que en las métricas."""
    n = d.groupby("municipio")[col].count()
    tiene = OA is not None and not OA.empty
    mae_mun = OA.groupby("municipio").ae.mean() if tiene else pd.Series(dtype=float)
    mae_gen = float(metricas(OA)["MAE"]) if tiene else np.nan
    dentro_mun = (OA.assign(dentro=OA.ae <= OA.municipio.map(mae_mun)).groupby("municipio").dentro.mean()
                 if tiene else pd.Series(dtype=float))
    filas = []
    for m in sorted(n.index):
        mm = float(mae_mun.get(m, np.nan))
        dm = float(dentro_mun.get(m, np.nan))
        nivel, motivo, motivo_detallado = _regla(int(n[m]), mm, mae_gen, dm)
        ex = EXCEPCIONES.get(m, {})
        nivel = ex.get("nivel", nivel)
        if ex.get("nota"):
            motivo = f"{motivo} {ex['nota']}"
            motivo_detallado = f"{motivo_detallado} {ex['nota']}"
        filas.append({"municipio": m, "n_cosecha": int(n[m]), "mae_municipio": mm, "mae_general": mae_gen,
                      "nivel": nivel, "motivo": motivo, "motivo_detallado": motivo_detallado})
    return pd.DataFrame(filas, columns=COLUMNAS)


def confianza_parcela(tabla, municipio, fuente="municipio"):
    """{'nivel', 'motivo', 'motivo_detallado'} de una estimación según su municipio y su fuente (municipio, grupo o
    global). Si la estimación usa el respaldo del grupo o global, es baja sin importar el municipio."""
    if fuente in ("grupo", "global"):
        de = "su grupo de registro" if fuente == "grupo" else "toda la región"
        m = ("Confianza baja: tu municipio no tiene parcelas con cosecha suficientes "
            f"y la estimación usa el valor de {de}.")
        return {"nivel": "baja", "motivo": m, "motivo_detallado": m}
    fila = tabla[tabla.municipio == municipio]
    if fila.empty:
        nivel, motivo, motivo_detallado = _regla(0, np.nan, np.nan)
        return {"nivel": nivel, "motivo": motivo, "motivo_detallado": motivo_detallado}
    f = fila.iloc[0]
    return {"nivel": f.nivel, "motivo": f.motivo, "motivo_detallado": f.motivo_detallado}


def confianza_de_parcelas(pred, tabla):
    """DataFrame (nivel, motivo, motivo_detallado) con el índice de `pred` (municipio y fuente de cada parcela)."""
    filas = [confianza_parcela(tabla, r.municipio, r.fuente) for r in pred.itertuples()]
    return pd.DataFrame(filas, index=pred.index, columns=["nivel", "motivo", "motivo_detallado"])
