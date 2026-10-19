"""Ficha de parcela en PDF (una página A4) para el agricultor. Sólo usa matplotlib; se arma en memoria."""
import io
import textwrap
from datetime import date

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.collections import PolyCollection
from matplotlib.figure import Figure
from matplotlib.patches import FancyBboxPatch

from agrocebada_app.backend.dominio.rangos import ANIO
from agrocebada_app.backend.ficha_pdf.dibujo import NARANJA, OSCURO, TENUE, TEXTO, _caja, _rgb, _texto_ajustado
from agrocebada_app.config import MESES, PALETA

ANCHO_TEXTO = 105           # caracteres por renglón de los textos de la ficha
INTERLINEA = 0.0158         # alto de un renglón de 9 pt, en fracción de la hoja
MAX_FILAS_CALCULADORA = 3
# nivel de confianza (M01) -> ícono y palabra: el nivel se lee sin depender del color
CONFIANZA = {"alta": ("✔", "alta", "#2F7D32", "#E6F2E3"), "media": ("▲", "media", "#8A5A00", "#FDF1D8"),
             "baja": ("⚠", "baja", "#A13A1F", "#FBE6DF")}
PIE = f"Estimación retrospectiva de la campaña {ANIO} · Orientativa, no es un dictamen"


def _alto(texto, ancho=ANCHO_TEXTO):
    return len(textwrap.wrap(texto, ancho)) * INTERLINEA


def ficha_pdf(info, poligonos, serie=None, clima=None, mascota=None, formato="pdf"):
    """Devuelve los bytes del PDF (o PNG con formato='png'). Los datos son los de figura_ficha."""
    fig = figura_ficha(info, poligonos, serie, clima, mascota)
    buf = io.BytesIO()
    fig.savefig(buf, format=formato, dpi=110 if formato == "png" else None)
    return buf.getvalue()


def figura_ficha(info, poligonos, serie=None, clima=None, mascota=None):
    """Figura A4 de la ficha. info: id, municipio, estado, grupo, area, tipo ('estimacion' o 'registrado'), valor,
    produccion, oof, nota, aviso, corte; y, opcionales, modelo (etiqueta legible), rango (frase del rango del
    municipio), confianza (dict nivel, motivo) y calculadora (lista de (concepto, valor)). poligonos: lista de
    dict(coords, valor, sel, reservada). serie: fecha, sensor, ndvi_promedio. clima: mes (3-10), PREC, Tmax, Tmin."""
    fig = Figure(figsize=(8.27, 11.69))          # figura propia: segura si varias personas descargan a la vez
    FigureCanvasAgg(fig)
    fig.patch.set_facecolor("white")

    # encabezado
    fig.patches.append(FancyBboxPatch((0, 0.915), 1, 0.085, boxstyle="square,pad=0", transform=fig.transFigure,
                                      facecolor=OSCURO, edgecolor="none"))
    x0 = 0.06
    if mascota:
        ax = fig.add_axes([0.045, 0.924, 0.068, 0.068], zorder=5)          # encima de la franja del encabezado
        ax.imshow(plt.imread(mascota))
        ax.axis("off")
        x0 = 0.125
    fig.text(x0, 0.966, "AgroCebada · Ficha de parcela", color="white", fontsize=18, fontweight="bold", va="center")
    fig.text(x0, 0.937, f"Rendimiento de cebada · campaña {ANIO} · información al {info['corte']}", color="#BFD3C6",
             fontsize=9.5, va="center")

    # identificación
    fig.text(0.06, 0.872, info["id"], fontsize=22, fontweight="bold", color=TEXTO)
    lugar = info["municipio"] + (f", {info['estado']}" if info.get("estado") else "")
    fig.text(0.06, 0.848, f"{lugar} · {info['area']:.2f} ha · grupo de registro {info['grupo']}", fontsize=10,
             color=TENUE)

    if info.get("modelo"):
        fig.text(0.94, 0.872, f"Modelo: {info['modelo']}", fontsize=10, color=TENUE, ha="right", fontweight="bold")

    # cifra principal y tarjetas
    estimacion = info["tipo"] == "estimacion"
    _caja(fig, 0.06, 0.715, 0.40, 0.115, fondo="#EAF5E3", borde="#C6E2B4")
    fig.text(0.08, 0.805, "RENDIMIENTO ESTIMADO" if estimacion else "RENDIMIENTO REGISTRADO", fontsize=8.5,
             color=TENUE, fontweight="bold")
    cifra = fig.text(0.08, 0.735, f"{info['valor']:.2f}", fontsize=40, fontweight="bold", color=TEXTO)
    fin = cifra.get_window_extent(renderer=fig.canvas.get_renderer()).x1 / fig.bbox.width
    fig.text(fin + 0.012, 0.742, "t/ha", fontsize=14, color=TENUE)
    if estimacion:
        tarjetas = [("Producción estimada", f"{info['produccion']:.1f} t")]
    elif info.get("oof") is not None:
        tarjetas = [("Estimado sin conocerla", f"{info['oof']:.2f} t/ha"),
                    ("Diferencia", f"{info['oof'] - info['valor']:+.2f} t/ha")]
    else:
        tarjetas = []
    for i, (k, v) in enumerate(tarjetas):
        y = 0.775 - i * 0.06
        _caja(fig, 0.49, y, 0.45, 0.05)
        fig.text(0.51, y + 0.033, k, fontsize=8.5, color=TENUE)
        fig.text(0.51, y + 0.01, v, fontsize=13, fontweight="bold", color=TEXTO)
    y = 0.70                                             # los bloques opcionales se apilan: sin hueco si faltan
    nota = info.get("nota", "")
    _texto_ajustado(fig, 0.06, y, nota, ANCHO_TEXTO, fontsize=9, color=TEXTO)
    y -= _alto(nota) + 0.012
    if info.get("rango"):
        alto = 0.026 + _alto(info["rango"], 100)
        _caja(fig, 0.06, y - alto, 0.88, alto)
        fig.text(0.075, y - 0.005, "LO QUE DIERON LAS PARCELAS DE TU MUNICIPIO", fontsize=7.5, color=TENUE,
                 fontweight="bold", va="top")
        _texto_ajustado(fig, 0.075, y - 0.019, info["rango"], 100, fontsize=9, color=TEXTO)
        y -= alto + 0.01
    if info.get("aviso"):
        _caja(fig, 0.06, y - 0.032, 0.88, 0.032, fondo="#FDF1D8", borde="#F0D49A")
        fig.text(0.075, y - 0.016, "Tómalo con más cuidado: " + info["aviso"] + ".", fontsize=8.5, color="#7A5200",
                 va="center")
        y -= 0.042
    if info.get("confianza"):
        icono, palabra, tinta, fondo = CONFIANZA.get(str(info["confianza"].get("nivel", "")).lower(),
                                                     ("◆", str(info["confianza"].get("nivel", "")), TEXTO, "#F3F6F2"))
        motivo = info["confianza"].get("motivo") or ""
        alto = 0.032 + (_alto(motivo, 100) if motivo else 0)
        _caja(fig, 0.06, y - alto, 0.88, alto, fondo=fondo, borde="#DCE5DD")
        fig.text(0.075, y - 0.016, f"{icono}  Confianza {palabra}", fontsize=10, color=tinta, fontweight="bold",
                 va="center")
        if motivo:
            _texto_ajustado(fig, 0.075, y - 0.029, motivo, 100, fontsize=9, color=TEXTO)
        y -= alto + 0.01
    if info.get("calculadora"):
        filas = list(info["calculadora"])[:MAX_FILAS_CALCULADORA]
        alto = 0.027 + 0.017 * len(filas)
        _caja(fig, 0.06, y - alto, 0.88, alto)
        fig.text(0.075, y - 0.005, "CALCULADORA", fontsize=7.5, color=TENUE, fontweight="bold", va="top")
        for k, (concepto, valor) in enumerate(filas):
            yy = y - 0.027 - 0.017 * k
            fig.text(0.075, yy, str(concepto), fontsize=9, color=TEXTO, va="top")
            fig.text(0.925, yy, str(valor), fontsize=9, color=TEXTO, va="top", ha="right", fontweight="bold")
        y -= alto + 0.01

    # mapa de la parcela y sus vecinas
    base = 0.30                                           # parte baja del mapa; arriba, lo que deje el apilado
    ax = fig.add_axes([0.06, base, 0.88, max(0.09, y - 0.025 - base)])
    caras, colores, bordes, grosores = [], [], [], []
    for p in sorted(poligonos, key=lambda p: p["sel"]):
        caras.append([(c[0], c[1]) for c in p["coords"]])      # sin altura (Z)
        colores.append(NARANJA if p["sel"] else _rgb(p["valor"], 0.9))
        bordes.append(TEXTO if (p["sel"] or p["reservada"]) else "white")
        grosores.append(1.8 if p["sel"] else 0.9 if p["reservada"] else 0.4)
    ax.add_collection(PolyCollection(caras, facecolors=colores, edgecolors=bordes, linewidths=grosores))
    todos = np.vstack([np.asarray(c) for c in caras])
    (xa, ya), (xb, yb) = todos.min(0), todos.max(0)
    mx, my = (xb - xa) * 0.06 + 1e-3, (yb - ya) * 0.06 + 1e-3
    ax.set_xlim(xa - mx, xb + mx)
    ax.set_ylim(ya - my, yb + my)
    lat = (ya + yb) / 2
    ax.set_aspect(1 / np.cos(np.radians(lat)))
    ax.set_facecolor("#EEF2EC")
    ax.set_xticks([])
    ax.set_yticks([])
    fig.text(0.06, y - 0.005, "Tu parcela (naranja) y sus vecinas · color = t/ha · borde oscuro = por estimar",
             fontsize=10, fontweight="bold", color=TEXTO)
    km = 1 / (111.32 * np.cos(np.radians(lat)))
    x1, y1 = ax.get_xlim()[0] + mx * 0.4, ax.get_ylim()[0] + my * 0.5
    ax.plot([x1, x1 + km], [y1, y1], color=TEXTO, lw=2)
    ax.text(x1 + km / 2, y1 + my * 0.25, "1 km", ha="center", fontsize=7.5, color=TEXTO)
    cb = fig.add_axes([0.66, base - 0.012, 0.28, 0.008])
    cb.imshow([[_rgb(v)[:3] for v in np.linspace(PALETA[0][0], PALETA[-1][0], 120)]], aspect="auto")
    cb.set_xticks([0, 59.5, 119], [f"{PALETA[0][0]:.1f}", f"{PALETA[1][0]:.1f}", f"{PALETA[-1][0]:.1f} t/ha"],
                  fontsize=7)
    cb.set_yticks([])
    for s in cb.spines.values():
        s.set_visible(False)

    # verdor y clima
    a1 = fig.add_axes([0.08, 0.125, 0.38, 0.12])
    a1.set_title(f"Verdor (NDVI) en {ANIO}", pad=6)
    if serie is not None and len(serie):
        for sensor, c in [("Planet", "#5FA83A"), ("Sentinel-2", "#2E86AB")]:
            x = serie[serie.sensor == sensor].sort_values("fecha")
            if len(x):
                a1.plot(x.fecha, x.ndvi_promedio, color=c, lw=1.4, marker="o", ms=2.2, label=sensor)
        a1.legend(fontsize=7, frameon=False, loc="upper left")
        a1.xaxis.set_major_locator(mdates.MonthLocator())
        a1.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: MESES[mdates.num2date(v).month]))
    else:
        a1.text(0.5, 0.5, "Sin capturas despejadas", ha="center", va="center", transform=a1.transAxes, color=TENUE)
    a1.tick_params(labelsize=7.5)
    a1.grid(alpha=0.25)
    a2 = fig.add_axes([0.56, 0.125, 0.34, 0.12])
    a2.set_title("Lluvia y temperatura por mes", pad=6)
    if clima is not None and len(clima):
        meses = [MESES[m] for m in clima.mes]
        a2.bar(meses, clima.PREC, color="#8EC5E8")
        a2.set_ylabel("lluvia (mm)", fontsize=7.5)
        t = a2.twinx()
        t.plot(meses, clima.Tmax, color="#E0902F", marker="o", ms=3, lw=1.4, label="máx.")
        t.plot(meses, clima.Tmin, color="#4A7FD0", marker="o", ms=3, lw=1.4, label="mín.")
        t.set_ylabel("°C", fontsize=7.5, color=TENUE)
        t.tick_params(labelsize=7.5, colors=TENUE)
        t.legend(fontsize=7, frameon=False, loc="upper right")
    else:
        a2.text(0.5, 0.5, "Sin datos de clima", ha="center", va="center", transform=a2.transAxes, color=TENUE)
    a2.tick_params(labelsize=7.5)

    # pie
    _texto_ajustado(fig, 0.06, 0.094, "Cómo leer esta ficha: la cifra es el rendimiento típico de las parcelas de su "
                    "municipio con cosecha registrada. El verdor y el clima son contexto: no cambian la estimación, "
                    "no son una recomendación agronómica y el rendimiento no indica calidad maltera ni capacidad "
                    "de pago.", 128, fontsize=7.5, color=TENUE)
    fig.text(0.06, 0.036, PIE, fontsize=8, color=TEXTO, fontweight="bold")
    fig.text(0.06, 0.018, f"Generada el {date.today():%d/%m/%Y} con la app AgroCebada · Reto AgroCebada 2026 (FIRA)",
             fontsize=7, color=TENUE)
    return fig
