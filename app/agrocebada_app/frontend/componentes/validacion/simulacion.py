"""Comparación resumida de la simulación y detalle completo por parcela."""
import streamlit as st

from agrocebada_app.frontend.componentes.validacion.formato import insignia, resumen_estimacion
from agrocebada_app.frontend.tema.html import e, h

FUENTES = {"municipio": "Municipio", "grupo": "Grupo de registro", "global": "Toda la región"}


def _estimacion(titulo, resumen):
    fuentes = ", ".join(FUENTES.get(f, str(f)) for f in resumen["fuentes"]) or "Sin información"
    return (f"<section class='val-escenario'><h3>{e(titulo)}</h3>"
            f"<p class='val-cifra'>{e(resumen['valor'])}<small>{e(resumen['unidad'])}</small></p>"
            "<div class='val-niveles'>" + "".join(insignia(n) for n in resumen["niveles"]) + "</div>"
            f"<p class='val-fuente'>Fuente: {e(fuentes)}</p></section>")


def comparacion(tabla, normal, sim, bloques, motivo):
    if tabla.empty:
        st.info("No hay parcelas por estimar en este municipio para comparar.")
        return
    antes = resumen_estimacion(normal.prediccion, normal.fuente, tabla["confianza normal"])
    despues = resumen_estimacion(sim.prediccion, sim.fuente, tabla["confianza sin datos"])
    h("<div class='val-comparacion'>" + _estimacion("Con datos del municipio", antes)
      + _estimacion("Sin datos del municipio", despues) + "</div>")
    h(f"<p class='nota'>{len(tabla)} parcelas por estimar en esta comparación. "
      "El detalle conserva el resultado de cada una.</p>")
    h("<div class='aviso val-alerta'><b>Confianza baja por falta de evidencia.</b> "
      "No demuestra que el error vaya a ser mayor.</div>")
    h("<div class='val-conclusiones'><section><h3>Qué pasó en la validación</h3>"
      f"<p>{e(bloques['validacion'])}</p>"
      + (f"<p>{e(bloques['limite'])}</p>" if bloques["limite"] else "")
      + "</section><section><h3>Qué ocurre con las estimaciones reales</h3>"
      f"<p>{e(bloques['estimaciones'])}</p></section></div>")
    with st.expander(f"Ver detalle de las {len(tabla)} parcelas", expanded=False):
        st.caption("El respaldo usa el grupo de registro y, si no hay cosechas en él, toda la región.")
        detalle = tabla.rename_axis("Parcela").reset_index().rename(columns={
            "estimación normal": "Con datos (t/ha)", "confianza normal": "Confianza con datos",
            "sin datos del municipio": "Sin datos (t/ha)", "fuente sin datos": "Fuente sin datos",
            "confianza sin datos": "Confianza sin datos"})
        st.dataframe(detalle, hide_index=True, width="stretch",
                     column_config={c: st.column_config.NumberColumn(format="%.2f")
                                    for c in ["Con datos (t/ha)", "Sin datos (t/ha)"]})
        st.caption(motivo if sim.fuente.nunique() == 1 else
                   "El respaldo varía entre parcelas; consulta la fuente y la confianza en cada fila.")
