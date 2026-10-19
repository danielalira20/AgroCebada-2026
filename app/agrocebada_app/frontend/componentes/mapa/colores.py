"""Color de una parcela en el mapa."""
from agrocebada_app.backend.dominio.colores import color_rgb


def color(v, alfa=235):
    return list(color_rgb(v)) + [alfa]

COLORES_CONFIANZA = {
    "alta": [34, 197, 94, 235],
    "media": [245, 158, 11, 235],
    "baja": [239, 68, 68, 235],
}
# Gris para parcelas sin una estimación de confianza.
COLOR_SIN_CONFIANZA = [140, 148, 148, 210]


def color_confianza(nivel):
    """Devuelve el color correspondiente a un nivel de M01."""
    return COLORES_CONFIANZA.get(nivel, COLOR_SIN_CONFIANZA).copy()