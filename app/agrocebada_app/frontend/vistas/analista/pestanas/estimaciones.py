"""Pestaña «Las 59 estimaciones»: verificaciones, descarga y tabla."""
import numpy as np
import streamlit as st

from agrocebada_app.frontend.estado.cache import oficial
from agrocebada_app.frontend.tema.html import e, h, titulo


def estimaciones(ctx):
    modelo = ctx.modelo
    pred = ctx.pred
    with st.container(key="glass_tabla"):
        of = oficial(modelo)
        checks = [("59 IDs", len(pred) == 59), ("Sin IDs duplicados", pred.index.is_unique),
                  ("Valores finitos", bool(np.isfinite(pred.prediccion).all()))]
        if of is not None:
            checks.append(("Coinciden con el archivo de referencia",
                           bool((pred.prediccion - of.reindex(pred.index)).abs().max() < 1e-9)))
        a, b = st.columns([3, 1], vertical_alignment="center")
        with a:
            titulo("Las 59 parcelas reservadas",
                   "Estimación, producción derivada (t/ha × ha) y error observado en su municipio.")
            h("".join(f"<span class='chk {'ok' if ok else 'mal'}'>{'✓' if ok else '✗'} {e(n)}</span>"
                      for n, ok in checks))
        export = pred.reset_index()[["ID_POLIGONO", "prediccion"]].rename(columns={"prediccion": "RENDIMIENTO_T_HA"})
        b.download_button("Descargar CSV de las 59", export.to_csv(index=False).encode("utf-8"),
                          file_name=f"predicciones_59_{modelo}.csv", mime="text/csv", type="primary", width="stretch")
        tabla = pred.reset_index()
        tabla["produccion_t"] = tabla.prediccion * tabla.area_ha
        st.dataframe(tabla[["ID_POLIGONO", "municipio", "prediccion", "area_ha", "produccion_t", "error_tipico",
                            "fuente", "n_municipio", "aviso"]].rename(columns={
                                "prediccion": "estimación (t/ha)", "area_ha": "área (ha)",
                                "produccion_t": "producción (t)", "error_tipico": "MAE del municipio (t/ha)",
                                "n_municipio": "parcelas con cosecha en el municipio"}),
                     hide_index=True, width="stretch", height=420,
                     column_config={c: st.column_config.NumberColumn(format="%.2f") for c in
                                    ["estimación (t/ha)", "área (ha)", "producción (t)", "MAE del municipio (t/ha)"]})
        h("<div class='nota'>El MAE del municipio es el error observado en la validación, no un intervalo garantizado."
          "</div>")
