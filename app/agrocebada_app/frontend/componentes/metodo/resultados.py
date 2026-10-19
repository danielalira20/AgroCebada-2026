"""Qué tan bien funciona: el error de la validación y por qué un modelo simple."""
import streamlit as st

from agrocebada_app.frontend.tema.html import e, h, titulo


def resultados(error, por_que, modelo):
    with st.container(key="glass_resultados"):
        titulo("Qué tan bien funciona", f"{modelo} · error al estimar parcelas que el método no vio.")
        if error is None:
            st.info("No se encontraron los resultados de validación del modelo.")
        else:
            kp = [("MAE · municipio conocido (A)", f"{error['a_mae']:.3f}", "t/ha"), ("R² · municipio conocido (A)", f"{error['a_r2']:.3f}", "")]
            if error["b_mae"] is not None:
                kp.append(("MAE · zona de lluvia nueva (B)", f"{error['b_mae']:.3f}", "t/ha"))
            h("<div class='fila'>" + "".join(
                f"<div class='mini'><span>{e(k)}</span><b class='kv'>{v}<small>{u}</small></b></div>" for k, v, u in kp) + "</div>")
            b = f" y B · sin respaldo ({error['b_parcelas']} parcelas)" if error["b_mae"] is not None else ""
            h(f"<div class='nota'>Poblaciones de Validación: A · sin respaldo ({error['a_parcelas']} parcelas){e(b)}.</div>")
        h(f"<div class='nota'><b>¿Por qué se usa un modelo simple?</b> {e(por_que)}</div>")


def fuentes():
    with st.container(key="glass_fuentes"):
        titulo("Fuentes")
        lista = [("FIRA", "polígonos y rendimientos"), ("Sentinel-2, Landsat y Planet", "índices por parcela"),
                 ("CHIRPS", "lluvia mensual"), ("Temperatura", "máxima y mínima mensual"), ("INEGI", "elevación y pendiente"),
                 ("Mapa", "EOX Sentinel-2 cloudless, Terrain Tiles de AWS y CARTO, sólo como fondo")]
        h("<div class='etiquetas'>" + "".join(f"<div class='etiqueta'>{e(a)} <span>· {e(b)}</span></div>"
                                              for a, b in lista) + "</div>")
