"""Vista del agricultor: su parcela, su mapa, su verdor y su clima."""
import streamlit as st

from agrocebada_app.backend.dominio.geometria import vecinas
from agrocebada_app.backend.dominio.resumen import resumen_parcela
from agrocebada_app.config import AYUDA_MAPA, CREDITOS
from agrocebada_app.frontend.componentes.mapa.mapa import mapa
from agrocebada_app.frontend.componentes.paneles.explicacion import explicacion_cebi
from agrocebada_app.frontend.componentes.paneles.leyenda import leyenda
from agrocebada_app.frontend.estado.cache import elevaciones
from agrocebada_app.frontend.tema.html import chips, e, h
from agrocebada_app.frontend.vistas.agricultor.panel_parcela import panel_parcela
from agrocebada_app.frontend.vistas.agricultor.seleccion import clic_agricultor
from agrocebada_app.frontend.vistas.agricultor.verdor_clima import verdor_clima
from agrocebada_app.frontend.vistas.agricultor.calculadora import calculadora
from agrocebada_app.frontend.vistas.agricultor.bitacora import bitacora
from agrocebada_app.frontend.vistas.agricultor.pregunta_cebi import pregunta_cebi


def mostrar(ctx):
    d = ctx.d
    S = ctx.S
    C = ctx.C
    satelite = ctx.satelite
    pred = ctx.pred
    DET = ctx.DET
    with st.container(key="hero_agricultor"):
        pid, encuadre = panel_parcela(ctx)
        with st.container(key="glass_leyenda"):
            arriba, modo_color = leyenda()
        rc = d.loc[encuadre]
        mapa(d, pred, vecinas(d, encuadre), (rc.lon_c - 0.018, rc.lat_c), 13.2, resaltar=pid, altura=700,
                escala=30, satelite=satelite, arriba=arriba, modo_color=modo_color,
                detalle=DET, conf=ctx.conf, clave=f"mapa-agri-{encuadre}",
                al_clic=lambda clave: clic_agricultor(clave, d))
        with st.container(key="glass_chips"):
            chips(resumen_parcela(d, pid, elevaciones(), C, S))
    h(f"<div class='creditos'>Tu parcela en naranja; las vecinas a ~6 km. {AYUDA_MAPA} · {e(CREDITOS)}</div>")

    pregunta_cebi(ctx, pid)
    verdor_clima(ctx, pid)
    calculadora(ctx, pid)
    bitacora(ctx, pid)
    explicacion_cebi()
