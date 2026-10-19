"""Selector de vista del mapa y escala de color."""
import streamlit as st

from agrocebada_app.frontend.tema.html import h


def leyenda():
    """Selector de vista del mapa y escala de color. Devuelve True si se eligió la vista desde arriba."""
    arriba = (st.segmented_control("Vista del mapa", ["3D", "Desde arriba"], key="vista_mapa",
                                   label_visibility="collapsed") or "3D") == "Desde arriba"
    modo_color = st.segmented_control(
        "Colorear por",
        ["Rendimiento", "Confianza"],
        default="Rendimiento",
        key="modo_color_mapa",
    )
    nota = (
        "Color = t/ha · borde grueso = por estimar"
        if arriba
        else "Altura y color = t/ha · borde blanco = por estimar"
    )
    if modo_color == "Confianza":
        h(
            "<div class='eyebrow' style='margin-top:10px'>Confianza de la estimación</div>"
            "<div class='ley-nota' style='margin-top:8px'>"
            "<span style='color:#22C55E'>●</span> Alta · estimación con mayor respaldo</div>"
            "<div class='ley-nota'>"
            "<span style='color:#F59E0B'>●</span> Media · respaldo moderado</div>"
            "<div class='ley-nota'>"
            "<span style='color:#EF4444'>●</span> Baja · información limitada</div>"
            "<div class='nota' style='margin-top: 16px; margin-bottom: 14px; line-height: 1.55;'>"
            "La confianza indica el respaldo de la estimación, no garantiza el rendimiento.</div>"
        )
    else:
        h(
            "<div class='eyebrow' style='margin-top:4px'>Rendimiento</div>"
            "<div class='ley-bar' style='margin-top:6px'></div>"
            "<div class='ley-txt'><span>2.0</span><span>3.8</span><span>5.6 t/ha</span></div>"
            f"<div class='ley-nota'>{nota}</div>"
        )
    return arriba, modo_color
