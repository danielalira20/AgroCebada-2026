"""AgroCebada 2026 · App de estimación de rendimiento (T17).

Ejecuta el mismo procedimiento que T08 (valor típico del municipio con respaldo por grupo de registro y luego global)
con las 138 parcelas con rendimiento y estima las 59 reservadas. Dos vistas:
  - Agricultor: una parcela, su estimación en t/ha, el error observado, su mapa 3D, su verdor, su clima y su ficha PDF.
  - Analista: mapa 3D de las 197, las 59 con verificación y exportación, ficha técnica y comparación de parcelas,
    validación por escenario y municipio, información insuficiente y análisis de un dataset propio (carga segura).

Datos: lee el paquete compacto `datos_app/` (lo arma herramientas/preparar_datos.py); si no está, las fuentes del repo.
El mapa 3D pone las parcelas sobre el relieve real (Terrain Tiles de AWS) con imagen Sentinel-2 sin nubes (EOX).

Uso (desde esta carpeta):  streamlit run app.py
"""
import streamlit as st

from agrocebada_app.backend.datos.paquete import FALTA_DATASET, hay_datos
from agrocebada_app.frontend.componentes.paneles.cabecera import cabecera
from agrocebada_app.frontend.estado.cache import cargar, clima, series, soporte
from agrocebada_app.frontend.estado.contexto import calcular
from agrocebada_app.frontend.estado.sesion import iniciar_sesion
from agrocebada_app.frontend.tema.estilos import estilo_actual, ICONO
from agrocebada_app.frontend.tema.html import h
from agrocebada_app.frontend.vistas.agricultor import vista as vista_agricultor
from agrocebada_app.frontend.vistas.analista import vista as vista_analista
from agrocebada_app.frontend.vistas.bienvenida import mostrar_bienvenida

st.set_page_config(page_title="AgroCebada · Rendimiento de cebada", page_icon=ICONO, layout="wide",
                   initial_sidebar_state="collapsed")
iniciar_sesion()
h(f"<style>{estilo_actual()}</style>")
if not hay_datos():
    st.error(FALTA_DATASET)
    st.stop()

if st.session_state.get("bienvenida_completada", False):
    vista_elegida = st.session_state.pop("bienvenida_vista_elegida", None)
    if vista_elegida is not None:
        st.session_state["vista"] = vista_elegida

d, sop, S, C = cargar(), soporte(), series(), clima()
agricultor, modelo, satelite = cabecera()
ctx = calcular(d, sop, S, C, modelo, satelite)

(vista_agricultor if agricultor else vista_analista).mostrar(ctx)

if not st.session_state["bienvenida_completada"]:
    mostrar_bienvenida()
