"""Color de una parcela en el mapa."""
from agrocebada_app.backend.dominio.colores import color_rgb


def color(v, alfa=235):
    return list(color_rgb(v)) + [alfa]
