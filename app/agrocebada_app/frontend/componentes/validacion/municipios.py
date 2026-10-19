"""Tabla municipal adaptable y regla de confianza, sin duplicar sus umbrales."""
import streamlit as st

from agrocebada_app.frontend.tema.tablas import tabla as tabla_visual

from agrocebada_app.frontend.componentes.validacion.formato import etiqueta_confianza, insignia, numero
from agrocebada_app.frontend.tema.html import e, h, titulo


def municipios(pm):
    with st.container(key="glass_mun"):
        titulo("Error y confianza por municipio", "Escenario A · sin respaldo")
        vista = pm.rename(columns={"municipio": "Municipio", "n_cosecha": "Con cosecha",
                                   "mae_municipio": "MAE (t/ha)", "dentro": "Dentro de ± MAE (%)",
                                   "confianza": "Confianza"}).copy()
        vista["Confianza"] = vista["Confianza"].map(etiqueta_confianza)
        with st.container(key="val_tabla_municipal"):
            tabla_visual(vista, hide_index=True, width="stretch", height=352,
                         column_config={"Municipio": st.column_config.TextColumn(width=340),
                                        "MAE (t/ha)": st.column_config.NumberColumn(format="%.3f")})
        filas = []
        for r in pm.itertuples(index=False):
            filas.append(f"<article class='val-municipio'><div class='val-municipio-titulo'>"
                         f"<h3>{e(r.municipio)}</h3>{insignia(r.confianza)}</div><dl>"
                         f"<div><dt>Con cosecha</dt><dd>{int(r.n_cosecha)}</dd></div>"
                         f"<div><dt>MAE (t/ha)</dt><dd>{numero(r.mae_municipio)}</dd></div>"
                         f"<div><dt>Dentro de ± MAE</dt><dd>{e(r.dentro)}</dd></div></dl></article>")
        h("<div class='val-municipios-movil'>" + "".join(filas) + "</div>")
        h("<p class='nota'>Con cosecha: parcelas registradas. Dentro de ± MAE: porcentaje de predicciones, "
          "no de parcelas distintas. Sin validación propia, MAE y cobertura no están disponibles.</p>")


def reglas_confianza(reglas):
    with st.container(key="glass_reglas_val"):
        titulo("Cómo se decide la confianza", "La misma regla para todos los municipios.")
        filas = []
        for regla in reglas:
            nivel, criterio = regla.split(": ", 1)
            filas.append(f"<div class='val-regla'>{insignia(nivel)}<p>{e(criterio)}</p></div>")
        h("<div class='val-reglas'>" + "".join(filas) + "</div>")
        h("<p class='nota'>La confianza expresa la evidencia disponible; no garantiza una cosecha.</p>")
