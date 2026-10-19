"""Botón «Descargar cifras» (M03): las tres tablas de agrocebada_app.backend.datos.exportar en un solo ZIP, para
que la app, el informe y el video partan siempre de los mismos números."""
import io
import zipfile

import streamlit as st

from agrocebada_app.backend.datos.exportar import tablas


@st.cache_data(show_spinner=False)
def cifras_zip_bytes(modelo, _d, _pred, _conf, _O):
    """Clave de caché: el modelo (las tablas no se hashean, igual que el resto de la caché de la app)."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for nombre, tabla in tablas(_d, _pred, _conf, modelo, _O).items():
            z.writestr(nombre, tabla.to_csv(index=False))
    return buf.getvalue()


def boton_cifras(ctx):
    datos = cifras_zip_bytes(ctx.modelo, ctx.d, ctx.pred, ctx.conf, ctx.O)
    st.download_button("Descargar cifras", data=datos, file_name=f"cifras_{ctx.modelo}.zip", mime="application/zip",
                       type="secondary", width="stretch",
                       help="cifras_parcelas.csv, cifras_municipios.csv y cifras_validacion.csv: la misma fuente "
                            "que usa el informe.")
