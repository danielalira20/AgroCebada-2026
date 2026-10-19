"""Pestaña «Analizar tus datos»: carga segura de un dataset propio."""
import hashlib

import streamlit as st

from agrocebada_app.backend.carga_segura import MAX_MB, REQUISITOS, Rechazo, plantilla_csv, revisar
from agrocebada_app.frontend.tema.html import titulo
from agrocebada_app.frontend.vistas.datos_propios.resultado import analizar_subido


def datos_propios(ctx):
    modelo = ctx.modelo
    satelite = ctx.satelite
    mA = ctx.mA                      # métricas del proyecto, sólo como referencia en el detalle técnico
    with st.container(key="glass_subir"):
        titulo("Analiza tu propio dataset",
                "Sube tus parcelas y la aplicación calculará las estimaciones ""utilizando el mismo procedimiento que se aplica a los datos del proyecto. "
                "Revisa los requisitos antes de continuar."
            )
        st.markdown(REQUISITOS)
        p1, p2 = st.columns([3, 1], vertical_alignment="bottom")
        archivo = p1.file_uploader(f"Sube un .zip o un .csv (máximo {MAX_MB} MB)", type=["zip", "csv"],
                                   accept_multiple_files=False, key="carga")
        p2.download_button("Plantilla CSV", plantilla_csv(), file_name="plantilla_parcelas.csv",
                           mime="text/csv", on_click="ignore", width="stretch",
                           help="Ejemplo del formato 2 con datos inventados.")
    if archivo is not None:
        contenido = archivo.getvalue()
        huella = hashlib.sha256(contenido).hexdigest()
        guardado = st.session_state.get("carga_resultado")
        if not guardado or guardado[0] != huella:
            try:
                guardado = (huella, revisar(archivo.name, contenido), None)
            except Rechazo as ex:
                guardado = (huella, None, str(ex))
            except Exception:
                guardado = (huella, None, "No pude leer el archivo; revisa que cumpla el formato de arriba.")
            st.session_state["carga_resultado"] = guardado      # sólo en esta sesión; no se guarda en disco
        _, res, motivo = guardado
        if motivo:
            st.error(f"Archivo rechazado. {motivo}")
        else:
            analizar_subido(res, modelo, satelite, mA)
