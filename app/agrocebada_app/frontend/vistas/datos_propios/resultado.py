"""Resultado del análisis de un dataset propio: revisión, estimaciones, mapa y descarga."""
import streamlit as st

from agrocebada_app.backend.dominio.geometria import zoom_para
from agrocebada_app.backend.modelo.estimador import predecir
from agrocebada_app.backend.modelo.metricas import metricas, validacion_dejando_uno
from agrocebada_app.frontend.componentes.mapa.mapa import mapa
from agrocebada_app.frontend.tema.html import e, h, titulo


def analizar_subido(res, modelo, satelite):
    du = res.datos
    pu = predecir(du, modelo)
    v = validacion_dejando_uno(du, modelo)
    m = metricas(v)
    err = v[v.fuente == "municipio"].groupby("municipio").ae.mean()
    pu["error_tipico"] = pu.municipio.map(err)
    with st.container(key="glass_revision"):
        titulo("Revisión del archivo", "El archivo pasó todas las reglas de formato y seguridad.")
        h("".join(f"<span class='chk ok'>✓ {e(x)}</span>" for x in res.revisiones))
        for a in res.avisos:
            h(f"<div class='aviso'>{e(a)}</div>")
    with st.container(key="glass_resultado_subido"):
        titulo("Resultado", f"Estimaciones basadas en la {'mediana' if modelo.startswith('mediana') else 'media'} "
                            "del rendimiento del municipio. Si no hay datos suficientes, "
                            "se utiliza el valor del grupo de registro y, como última opción, el valor general."
                        )
        kp = [("Parcelas por estimar", f"{len(pu)}", ""), ("Municipios", f"{du.municipio.nunique()}", ""),
              ("MAE dejando una fuera", f"{m.MAE:.3f}", "t/ha"), ("R² dejando una fuera", f"{m.R2:.3f}", "")]
        h("<div class='fila'>" + "".join(f"<div class='mini'><span>{e(k)}</span><b class='kv'>{v_}<small>{u}</small>"
                                         f"</b></div>" for k, v_, u in kp) + "</div>")
        h("<div class='nota'>Validación rápida: cada parcela con cosecha se estima sin utilizar su propio rendimiento. "
            "Este resultado sirve como referencia para los datos que subiste. "
            "La evaluación principal del proyecto utiliza una validación cruzada de 5 × 5 repeticiones.</div>")
        if res.con_mapa:
            det = {i: (f"Estimación: {pu.prediccion[i]:.2f} t/ha · área {du.AREA_HA[i]:.2f} ha" if i in pu.index
                       else f"Registrado: {du.real[i]:.2f} t/ha · área {du.AREA_HA[i]:.2f} ha") for i in du.index}
            mapa(du, pu, list(du.index), (du.lon_c.mean(), du.lat_c.mean()), zoom_para(du), altura=480,
                 satelite=satelite, arriba=True, detalle=det, con_relieve=False, clave="mapa-subido")
        tabla = pu.reset_index()[["ID_POLIGONO", "municipio", "prediccion", "area_ha", "error_tipico", "fuente"]]
        st.dataframe(tabla.rename(columns={"prediccion": "estimación (t/ha)", "area_ha": "área (ha)",
                                           "error_tipico": "MAE del municipio (t/ha)"}), hide_index=True,
                     width="stretch", height=320,
                     column_config={c: st.column_config.NumberColumn(format="%.2f")
                                    for c in ["estimación (t/ha)", "área (ha)", "MAE del municipio (t/ha)"]})
        st.download_button("Descargar estimaciones (CSV)",
                           pu.reset_index()[["ID_POLIGONO", "prediccion"]].rename(
                               columns={"prediccion": "RENDIMIENTO_T_HA"}).to_csv(index=False).encode("utf-8"),
                           file_name="estimaciones_dataset_propio.csv", mime="text/csv", type="primary",
                           on_click="ignore", key="descarga_subido")
