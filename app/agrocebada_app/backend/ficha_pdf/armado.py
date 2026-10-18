"""Arma los datos de la ficha de una parcela a partir de las tablas de la app y genera el PDF."""
from dataclasses import dataclass

import pandas as pd

from agrocebada_app.backend.dominio.geometria import anillo, vecinas
from agrocebada_app.backend.dominio.notas import nota_de
from agrocebada_app.backend.dominio.rangos import rango_de
from agrocebada_app.backend.ficha_pdf.ficha import ficha_pdf
from agrocebada_app.config import APP, CORTE_TXT, MODELO_OFICIAL, MODELOS


@dataclass
class ContextoFicha:
    """Tablas que necesita la ficha: parcelas, estimaciones, predicción por parcela de la validación, cobertura
    por municipio, clima (puede ser None) y series."""
    d: pd.DataFrame
    pred: pd.DataFrame
    oof_parcela: pd.Series
    cob_mun: pd.Series
    clima: pd.DataFrame | None
    series: pd.DataFrame


def datos_ficha(pid, ctx, modelo=None, confianza=None, calculadora=None):
    """Lo que se manda a dibujar: (info, polígonos, serie, clima, mascota). `modelo`: clave del modelo con que se hizo
    (por omisión, el oficial). `confianza` (M01): dict con nivel y motivo, o None. `calculadora` (M05): lista de
    (concepto, valor) o dict, o None. Lo opcional que no llega no aparece en la ficha."""
    d, pred, oof_parcela, cob_mun, C, S = ctx.d, ctx.pred, ctx.oof_parcela, ctx.cob_mun, ctx.clima, ctx.series
    r = d.loc[pid]
    est = r.CONJUNTO == "PREDICCION"
    p = pred.loc[pid] if est else None
    modelo = modelo or MODELO_OFICIAL
    # la nota de la ficha no lleva la frase del error típico: en su lugar va el rango del municipio
    nota = nota_de(d, pred, cob_mun.iloc[0:0], pid)
    rango = rango_de(d[d.CONJUNTO == "ENTRENAMIENTO"], r.municipio)["texto"]
    if isinstance(calculadora, dict):
        calculadora = list(calculadora.items())
    info = dict(id=pid, municipio=r.municipio, estado=r.Estado, grupo=r.grupo_registro, area=r.AREA_HA,
                tipo="estimacion" if est else "registrado", valor=float(p.prediccion) if est else float(r.real),
                produccion=float(p.prediccion) * r.AREA_HA if est else None,
                oof=float(oof_parcela[pid]) if (not est and pid in oof_parcela.index) else None,
                nota=nota, aviso=p.aviso if est else "", corte=CORTE_TXT, modelo=MODELOS.get(modelo, modelo),
                rango=rango, confianza=confianza or None, calculadora=calculadora or None)
    pol = [dict(coords=anillo(d.loc[i].geometry),
                valor=float(pred.prediccion[i]) if d.loc[i, "CONJUNTO"] == "PREDICCION" else float(d.loc[i, "real"]),
                sel=i == pid, reservada=d.loc[i, "CONJUNTO"] == "PREDICCION") for i in vecinas(d, pid)]
    c = None
    if C is not None:
        c = C[C.id_parcela == pid].assign(mes=lambda x: x.periodo.str[5:].astype(int)).sort_values("mes")
    icono = APP / "assets" / "mascota" / "cebi.png"
    return info, pol, S[S.ID_POLIGONO == pid], c, str(icono) if icono.exists() else None


def armar_ficha(pid, ctx, modelo=None, confianza=None, calculadora=None):
    """PDF de una página con la parcela, su cifra, el rango de su municipio, su mapa, su verdor y su clima."""
    return ficha_pdf(*datos_ficha(pid, ctx, modelo, confianza, calculadora))
