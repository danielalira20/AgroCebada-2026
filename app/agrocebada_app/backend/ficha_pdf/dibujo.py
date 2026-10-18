"""Estilo y piezas de dibujo de la ficha en PDF (matplotlib, sin estado global de figuras)."""
import textwrap

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402  (sólo imread y FuncFormatter; la figura no usa el estado global)
from matplotlib.patches import FancyBboxPatch  # noqa: E402

from agrocebada_app.backend.dominio.colores import color_rgb  # noqa: E402

OSCURO, TEXTO, TENUE, NARANJA = "#12261B", "#1C2420", "#5D6B63", "#E8662E"
plt.rcParams.update({"font.family": "DejaVu Sans", "axes.edgecolor": "#C9D3CB", "axes.labelcolor": TENUE,
                     "xtick.color": TENUE, "ytick.color": TENUE, "axes.titlesize": 10, "axes.titleweight": "bold",
                     "axes.titlecolor": TEXTO, "axes.titlelocation": "left"})


def _rgb(v, a=1.0):
    return tuple(c / 255 for c in color_rgb(v)) + (a,)


def _caja(fig, x, y, w, h, fondo="#F3F6F2", borde="#DCE5DD"):
    fig.patches.append(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.012",
                                      transform=fig.transFigure, facecolor=fondo, edgecolor=borde, linewidth=0.8))


def _texto_ajustado(fig, x, y, texto, ancho, **kw):
    fig.text(x, y, textwrap.fill(texto, ancho), va="top", linespacing=1.45, **kw)
