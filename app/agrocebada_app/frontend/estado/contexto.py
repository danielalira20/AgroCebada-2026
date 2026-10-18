"""Datos y resultados que comparten las vistas en cada ejecución (antes eran variables globales de app.py)."""
from dataclasses import dataclass

import pandas as pd

from agrocebada_app.backend.dominio.avisos import avisos_de
from agrocebada_app.backend.dominio.confianza import confianza_municipios
from agrocebada_app.backend.dominio.resumen import detalles
from agrocebada_app.backend.ficha_pdf.armado import ContextoFicha
from agrocebada_app.backend.modelo.estimador import predecir
from agrocebada_app.backend.modelo.metricas import metricas
from agrocebada_app.frontend.estado.cache import oof


@dataclass
class Contexto:
    d: pd.DataFrame            # las 197 parcelas
    sop: pd.DataFrame | None   # soporte de datos por parcela (T03)
    S: pd.DataFrame            # series de índices 2025
    C: pd.DataFrame | None     # clima mensual
    modelo: str
    satelite: bool
    pred: pd.DataFrame         # estimaciones de las 59
    O: pd.DataFrame | None     # validación del modelo
    OA: pd.DataFrame | None    # escenario A, predicciones con respaldo por municipio
    OAT: pd.DataFrame | None   # todas las predicciones del escenario A
    err_mun: pd.Series
    cob_mun: pd.Series
    oof_parcela: pd.Series
    DET: dict                  # texto del recuadro de cada parcela en el mapa
    FICHA: ContextoFicha
    centro_total: tuple
    mA: pd.Series | None       # métricas del escenario A (igual que metricas_referencias.csv de T08)
    conf: pd.DataFrame         # confianza por municipio (M01): municipio, n_cosecha, mae_municipio, mae_general, nivel, motivo


def calcular(d, sop, S, C, modelo, satelite):
    centro_total = (d.lon_c.mean(), d.lat_c.mean())
    pred = predecir(d, modelo)
    O = oof(modelo, d.municipio)
    OA = O[(O.escenario == "A") & (O.fuente == "municipio")] if O is not None else None
    OAT = O[O.escenario == "A"] if O is not None else None                        # todas las predicciones de A
    err_mun = OA.groupby("municipio").ae.mean() if OA is not None else pd.Series(dtype=float)
    cob_mun = (OA.assign(dentro=OA.ae <= OA.municipio.map(err_mun)).groupby("municipio").dentro.mean()
               if OA is not None else pd.Series(dtype=float))
    pred["error_tipico"] = pred.municipio.map(err_mun)
    pred["aviso"] = avisos_de(pred, sop)
    oof_parcela = OAT.groupby("ID_POLIGONO").prediccion.mean() if OAT is not None else pd.Series(dtype=float)
    DET = detalles(d, pred, oof_parcela)
    FICHA = ContextoFicha(d=d, pred=pred, oof_parcela=oof_parcela, cob_mun=cob_mun, clima=C, series=S)
    mA = metricas(OA) if OA is not None and not OA.empty else None
    conf = confianza_municipios(d, OA)
    return Contexto(d=d, sop=sop, S=S, C=C, modelo=modelo, satelite=satelite, pred=pred, O=O, OA=OA, OAT=OAT,
                    err_mun=err_mun, cob_mun=cob_mun, oof_parcela=oof_parcela, DET=DET, FICHA=FICHA,
                    centro_total=centro_total, mA=mA, conf=conf)
