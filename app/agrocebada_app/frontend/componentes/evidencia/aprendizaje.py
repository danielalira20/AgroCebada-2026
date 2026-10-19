"""«Lo que aprendimos»: error del modelo, peso de la ubicación y lo que el método no ve."""
import streamlit as st

from agrocebada_app.backend.dominio.evidencia import lo_que_falta, variacion_ubicacion
from agrocebada_app.frontend.componentes.graficas.dispersion_validacion import dispersion
from agrocebada_app.frontend.tema.html import e, h, titulo


def aprendizaje(ctx, ajuste):
    ubic = variacion_ubicacion(ctx.d)
    with st.container(key="evid_aprende"):
        izq, der = st.columns([2, 3])
        with izq:
            with st.container(key="glass_evid_aprende"):
                titulo("Lo que aprendimos", "Qué logra el método y qué se queda fuera.")
                if ajuste:
                    h(f"<div class='eyebrow'>{e(ajuste['modelo'])}</div><div class='fila'>"
                      f"<div class='mini'><span>Error medio (MAE)</span><b class='kv'>{ajuste['mae']:.3f}<small>t/ha</small></b></div>"
                      f"<div class='mini'><span>Parcelas validadas</span><b class='kv'>{ajuste['parcelas']}</b></div></div>")
                    h("<p class='evid-texto'>Es el error de estimar cada parcela sin usar su propia cosecha; "
                      "no garantiza el rendimiento de otra parcela.</p>")
                if ubic["pct"] is not None:
                    h(f"<div class='eyebrow'>La ubicación pesa</div><div class='mini'><span>Diferencias entre parcelas que se "
                      f"reparten entre municipios</span><b class='kv'>≈ {ubic['pct']}<small>%</small></b></div>"
                      f"<p class='evid-texto'>{e(ubic['frase'])}</p>")
                items = "".join(f"<li><b>{e(n)}</b> · {e(t)}</li>" for n, t in lo_que_falta())
                h(f"<div class='eyebrow'>Lo que el método no ve</div><ul class='evid-falta'>{items}</ul>"
                  "<p class='nota'>Con esa información se podría separar mejor una parcela de otra dentro de su municipio.</p>")
        with der:
            if ctx.OA is not None and not ctx.OA.empty:
                dispersion(ctx, clave="glass_disp_evid")
