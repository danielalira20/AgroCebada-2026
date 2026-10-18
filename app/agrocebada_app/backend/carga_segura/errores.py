"""Tipos que comparte la carga segura."""
from dataclasses import dataclass, field

import pandas as pd


class Rechazo(Exception):
    """El archivo no cumple el formato o las reglas de seguridad; el mensaje dice por qué."""


@dataclass
class Resultado:
    datos: pd.DataFrame                               # índice ID_POLIGONO; GeoDataFrame si trae polígonos
    con_mapa: bool
    revisiones: list = field(default_factory=list)    # lo que se comprobó
    avisos: list = field(default_factory=list)        # lo que se ajustó sin rechazar
