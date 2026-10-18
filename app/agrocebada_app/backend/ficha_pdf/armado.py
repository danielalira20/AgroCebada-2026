"""Arma los datos de la ficha de una parcela a partir de las tablas de la app y genera el PDF."""
from dataclasses import dataclass

import pandas as pd

from agrocebada_app.backend.dominio.geometria import anillo, vecinas
from agrocebada_app.backend.dominio.notas import nota_de
from agrocebada_app.backend.ficha_pdf.ficha import ficha_pdf
from agrocebada_app.config import APP, CORTE_TXT


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


def armar_ficha(pid, ctx):
    """PDF de una página con la parcela, su cifra, su mapa, su verdor y su clima."""
    d, pred, oof_parcela, cob_mun, C, S = ctx.d, ctx.pred, ctx.oof_parcela, ctx.cob_mun, ctx.clima, ctx.series
    r = d.loc[pid]
    est = r.CONJUNTO == "PREDICCION"
    p = pred.loc[pid] if est else None
    info = dict(id=pid, municipio=r.municipio, estado=r.Estado, grupo=r.grupo_registro, area=r.AREA_HA,
                tipo="estimacion" if est else "registrado", valor=float(p.prediccion) if est else float(r.real),
                produccion=float(p.prediccion) * r.AREA_HA if est else None,
                error=float(p.error_tipico) if est and pd.notna(p.error_tipico) else None,
                oof=float(oof_parcela[pid]) if (not est and pid in oof_parcela.index) else None,
                nota=nota_de(d, pred, cob_mun, pid), aviso=p.aviso if est else "", corte=CORTE_TXT)
    pol = [dict(coords=anillo(d.loc[i].geometry),
                valor=float(pred.prediccion[i]) if d.loc[i, "CONJUNTO"] == "PREDICCION" else float(d.loc[i, "real"]),
                sel=i == pid, reservada=d.loc[i, "CONJUNTO"] == "PREDICCION") for i in vecinas(d, pid)]
    c = None
    if C is not None:
        c = C[C.id_parcela == pid].assign(mes=lambda x: x.periodo.str[5:].astype(int)).sort_values("mes")
    icono = APP / "assets" / "mascota" / "cebi.png"
    return ficha_pdf(info, pol, S[S.ID_POLIGONO == pid], c, str(icono) if icono.exists() else None)
