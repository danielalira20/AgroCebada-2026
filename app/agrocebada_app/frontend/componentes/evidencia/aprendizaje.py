"""Variación observada y límites del método, con la validación de apoyo plegada."""
import streamlit as st

from agrocebada_app.backend.dominio.evidencia import lo_que_falta, variacion_ubicacion
from agrocebada_app.frontend.componentes.graficas.dispersion_validacion import dispersion
from agrocebada_app.frontend.tema.html import e, h, titulo


def aprendizaje(ctx, ajuste):
    ubic = variacion_ubicacion(ctx.d)
    with st.container(key="glass_evid_aprende"):
        titulo("Lo que aprendimos", "La ubicación resume diferencias; aún falta información de cada cultivo.")
        if ubic["pct"] is not None:
            pct = ubic["pct"]
            h("<div class='evid-aprendizajes'><section><h3>La ubicación pesa</h3>"
              f"<p class='evid-porcentaje'>≈ {pct}<small>%</small></p>"
              f"<div class='evid-barra' role='img' aria-label='{e(str(pct))} % entre municipios y {100-pct} % dentro de ellos'>"
              f"<span style='width:{pct}%'></span></div><div class='evid-barra-leyenda'>"
              f"<span>{pct} % entre municipios</span><span>{100-pct} % dentro</span></div>"
              f"<p class='nota'>Variación observada en {ubic['parcelas']} parcelas de {ubic['municipios']} municipios. "
              "Es descriptivo: no es porcentaje de aciertos ni demuestra causalidad.</p></section>"
              "<section><h3>Lo que el método no ve</h3><div class='evid-ausencias'>"
              + "".join(f"<span>{e(n)}</span>" for n, _ in lo_que_falta()) + "</div>"
              "<p class='nota'>Estos datos ayudarían a distinguir parcelas de un mismo municipio.</p></section></div>")
        else:
            st.info("No hay variación suficiente para describir su reparto entre municipios.")
        with st.expander("Qué información falta y por qué importa", expanded=False):
            for nombre, motivo in lo_que_falta():
                h(f"<p class='evid-texto'><b>{e(nombre)}</b> · {e(motivo)}</p>")
        with st.expander("Ver ajuste del modelo consultado", expanded=False):
            if ajuste:
                st.caption(f"{ajuste['modelo']} · MAE {ajuste['mae']:.4f} t/ha · {ajuste['parcelas']} parcelas · "
                           f"{ajuste['poblacion']}. El error no garantiza otra cosecha.")
            if ctx.OA is not None and not ctx.OA.empty:
                dispersion(ctx, clave="glass_disp_evid")
            else:
                st.info("No hay validación de la población principal para el modelo consultado.")
