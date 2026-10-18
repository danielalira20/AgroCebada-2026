"""Estilo común de las gráficas (fondo transparente, rejilla tenue)."""


def grafica_base(ch, alto):
    return ch.properties(height=alto, background="transparent").configure_view(strokeWidth=0).configure_axis(
        gridColor="rgba(255,255,255,0.07)", domainColor="rgba(255,255,255,0.18)", tickColor="rgba(255,255,255,0.18)")
