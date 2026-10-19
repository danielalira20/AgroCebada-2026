"""Pestaña «Las 59 estimaciones»: verificaciones, descarga y tabla, con confianza (M01) y rango del municipio (M02)
junto a cada cifra (M11). La tabla ancha es para escritorio/tablet; en pantallas angostas se esconde y en su lugar
se muestran tarjetas, el mismo patrón que ya usa la pestaña Validación para no depender sólo del scroll horizontal."""
import numpy as np
import pandas as pd
import streamlit as st

from agrocebada_app.backend.datos.exportar import cifras_parcelas
from agrocebada_app.config import MODELO_OFICIAL
from agrocebada_app.frontend.componentes.validacion.formato import etiqueta_confianza, insignia, numero
from agrocebada_app.frontend.estado.cache import entrega_final, oficial
from agrocebada_app.frontend.tema.html import e, h, titulo


def _rango_texto(bajo, alto):
    if pd.isna(bajo) or pd.isna(alto):
        return "Sin rango"
    if round(float(bajo), 2) == round(float(alto), 2):
        return f"{float(bajo):.2f} t/ha"
    return f"{float(bajo):.2f}–{float(alto):.2f} t/ha"


def _tarjetas(tabla):
    filas = []
    for r in tabla.itertuples():
        nota = f"<p class='est-aviso'>{e(r.aviso)}</p>" if isinstance(r.aviso, str) and r.aviso else ""
        filas.append(
            f"<article class='est-tarjeta'><div class='est-tarjeta-titulo'><h3>{e(r.ID_POLIGONO)}</h3>"
            f"{insignia(r.confianza)}</div><dl>"
            f"<div><dt>Municipio</dt><dd>{e(r.municipio)}</dd></div>"
            f"<div><dt>Estimación</dt><dd>{r.prediccion:.2f} t/ha</dd></div>"
            f"<div><dt>Producción</dt><dd>{r.produccion_t:.2f} t</dd></div>"
            f"<div><dt>Rango del municipio</dt><dd>{e(r.rango)}</dd></div></dl>{nota}</article>")
    h("<div class='est-movil'>" + "".join(filas) + "</div>")


def estimaciones(ctx):
    modelo = ctx.modelo
    pred = ctx.pred
    cp = cifras_parcelas(ctx.d, pred, ctx.conf, modelo).set_index("ID_POLIGONO")
    cp = cp.loc[pred.index, ["confianza", "motivo", "rango_bajo", "rango_alto"]]
    with st.container(key="glass_tabla"):
        checks = [("59 IDs", len(pred) == 59), ("Sin IDs duplicados", pred.index.is_unique),
                  ("Valores finitos", bool(np.isfinite(pred.prediccion).all()))]
        if modelo == MODELO_OFICIAL:
            ent = entrega_final()
            if ent is not None:
                checks.append(("Coinciden con la entrega final",
                               bool((pred.prediccion - ent.reindex(pred.index)).abs().max() < 1e-9)))
        else:
            of = oficial(modelo)
            if of is not None:
                checks.append(("Coinciden con el archivo de referencia",
                               bool((pred.prediccion - of.reindex(pred.index)).abs().max() < 1e-9)))
        a, b = st.columns([3, 1], vertical_alignment="center")
        with a:
            titulo("Las 59 parcelas reservadas",
                   "Estimación, producción derivada (t/ha × ha), confianza y rango de su municipio.")
            h("".join(f"<span class='chk {'ok' if ok else 'mal'}'>{'✓' if ok else '✗'} {e(n)}</span>"
                      for n, ok in checks))
        tabla = pred.reset_index()
        tabla["produccion_t"] = tabla.prediccion * tabla.area_ha
        tabla = tabla.merge(cp, left_on="ID_POLIGONO", right_index=True)
        tabla["rango"] = [_rango_texto(f.rango_bajo, f.rango_alto) for f in tabla.itertuples()]
        tabla["confianza_txt"] = tabla.confianza.map(etiqueta_confianza)
        tabla["mae_txt"] = tabla.error_tipico.map(lambda v: numero(v, 2))   # NaN -> "—", nunca "None"

        export = tabla[["ID_POLIGONO", "prediccion", "confianza", "motivo", "rango_bajo", "rango_alto"]].rename(
            columns={"prediccion": "RENDIMIENTO_T_HA", "rango_bajo": "rango_municipio_bajo",
                    "rango_alto": "rango_municipio_alto"})
        b.download_button("Descargar CSV de las 59", export.to_csv(index=False).encode("utf-8"),
                          file_name=f"predicciones_59_{modelo}.csv", mime="text/csv", type="primary", width="stretch")

        with st.container(key="tabla_59_ancha"):
            st.dataframe(tabla[["ID_POLIGONO", "municipio", "confianza_txt", "prediccion", "produccion_t", "rango",
                                "area_ha", "motivo", "mae_txt", "fuente", "n_municipio", "aviso"]].rename(columns={
                                    "prediccion": "estimación (t/ha)", "area_ha": "área (ha)",
                                    "produccion_t": "producción (t)", "confianza_txt": "confianza",
                                    "rango": "rango del municipio", "motivo": "motivo de la confianza",
                                    "mae_txt": "MAE del municipio (t/ha)",
                                    "n_municipio": "parcelas con cosecha en el municipio"}),
                         hide_index=True, width="stretch", height=420, row_height=148,
                         column_config={
                            "ID_POLIGONO": st.column_config.TextColumn(pinned=True),
                            "municipio": st.column_config.TextColumn(pinned=True),
                            "confianza": st.column_config.TextColumn(pinned=True),
                            "aviso": st.column_config.TextColumn(width=220),
                            "motivo de la confianza": st.column_config.TextColumn(width=460),
                            **{c: st.column_config.NumberColumn(format="%.2f") for c in
                               ["estimación (t/ha)", "área (ha)", "producción (t)"]}})
        _tarjetas(tabla)
        h("<div class='nota'>El MAE del municipio es el error observado en la validación, no un intervalo "
          "garantizado. La confianza y el rango del municipio son de M01 y M02: no cambian ninguna estimación.</div>")
