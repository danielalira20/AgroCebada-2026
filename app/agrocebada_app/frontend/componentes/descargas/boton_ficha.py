"""Botón para descargar la ficha de una parcela en PDF (se arma al hacer clic)."""
import streamlit as st

from agrocebada_app.backend.dominio.planeador import evaluar_cuenta
from agrocebada_app.backend.ficha_pdf.armado import armar_ficha


@st.cache_data(show_spinner=False)
def ficha_bytes(pid, modelo, _ctx, confianza=None, calculadora=None):
    """Clave de caché: parcela, modelo y lo opcional (el contexto no se hashea, igual que antes con las variables
    globales). `confianza` (M01) y `calculadora` (M05) son opcionales: sin ellos la ficha sale igual que siempre."""
    return armar_ficha(pid, _ctx, modelo, confianza, calculadora)


def _dinero(x):
    return f"-${abs(x):,.0f}" if x < 0 else f"${x:,.0f}"


def filas_calculadora(pid, ctx):
    """Filas (concepto, valor) de la calculadora (M05) con lo que el usuario escribió en esta sesión, o None si no
    llenó el precio y el costo. Es la misma cuenta de la vista: estimación (o cosecha registrada) y año bajo."""
    precio, costo = st.session_state.get("calc_precio"), st.session_state.get("calc_costo")
    if not precio or not costo:
        return None
    r = ctx.d.loc[pid]
    est = r.CONJUNTO == "PREDICCION"
    rend = float(ctx.pred.loc[pid, "prediccion"]) if est else float(r.real)
    area = st.session_state.get(f"calc_area_{pid}", float(r.AREA_HA))
    resultado = evaluar_cuenta(ctx.d, r.municipio, rend, "Con la estimación" if est else "Con tu cosecha registrada",
                               area, precio, costo)
    if resultado["estado"] != "calculada":
        return None
    t = resultado["tabla"]
    base = t.columns[0]
    filas = [(f"Producción en {area:.2f} ha", f"{t.loc['Producción (t)', base]:.1f} t"),
             ("Ingreso menos costo" + (" · cubre costos" if t.loc["¿Cubre costos?", base] == "Sí" else " · no cubre costos"),
              _dinero(t.loc["Ingreso menos costo", base]))]
    if len(t.columns) == 3:
        filas.append((t.columns[1], _dinero(t.loc["Ingreso menos costo", t.columns[1]])))
    return filas


def boton_ficha(pid, clave, modelo, ctx, confianza=None, calculadora=None):
    """`calculadora`: si no llega, se toma de lo que el usuario llenó en la calculadora (session_state)."""
    if calculadora is None:
        calculadora = filas_calculadora(pid, ctx)
    st.download_button("Descargar ficha (PDF)", data=lambda: ficha_bytes(pid, modelo, ctx, confianza, calculadora),
                       file_name=f"ficha_{pid}.pdf", mime="application/pdf", on_click="ignore", key=clave,
                       type="primary", width="stretch", help="Una página con la cifra, el rango de su municipio, el mapa, el verdor y el clima.")
