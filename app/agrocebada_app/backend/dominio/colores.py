"""Escala de color del rendimiento (t/ha), la usan el mapa y la ficha."""
import numpy as np

from agrocebada_app.config import PALETA


def color_rgb(v):
    """Color de la escala de rendimiento (t/ha) como (r, g, b) 0-255."""
    (a, ca), (b, cb), (c, cc) = PALETA
    x, y, k = (ca, cb, (v - a) / (b - a)) if v <= b else (cb, cc, (v - b) / (c - b))
    k = float(np.clip(k, 0, 1))
    return tuple(int(x[i] + (y[i] - x[i]) * k) for i in range(3))
