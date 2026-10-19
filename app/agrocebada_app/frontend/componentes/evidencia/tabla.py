"""Tabla completa de pruebas, con su registro y su fuente."""
import streamlit as st

from agrocebada_app.backend.dominio.evidencia import tabla
from agrocebada_app.frontend.tema.html import titulo

COLUMNAS = {"pregunta": "Pregunta", "tarea": "Tarea", "prueba": "Prueba", "mae": "MAE (t/ha)", "cambio": "Cambio (t/ha)",
            "intervalo": "Intervalo 95 %", "repeticiones": "Repeticiones que mejoran", "resultado": "Resultado",
            "registro": "Registro", "fuente": "Fuente"}


def tabla_completa(exp, oficial):
    with st.container(key="glass_evid_tabla"):
        titulo("Todas las pruebas, con su registro", f"{len(exp)} pruebas · cada fila apunta a su registro y a su documento.")
        t = tabla(exp, None, oficial)[list(COLUMNAS)].rename(columns=COLUMNAS)
        st.dataframe(t, hide_index=True, width="stretch", height=460, column_config={
            "MAE (t/ha)": st.column_config.NumberColumn(format="%.4f"),
            "Cambio (t/ha)": st.column_config.NumberColumn(format="%+.4f")})
