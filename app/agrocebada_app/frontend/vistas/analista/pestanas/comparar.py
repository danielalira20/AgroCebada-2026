"""Comparación de hasta 3 parcelas: curvas y tabla de datos principales."""
import altair as alt
import pandas as pd
import streamlit as st

from agrocebada_app.backend.dominio.geometria import vecinas
from agrocebada_app.config import INDICES, MESES
from agrocebada_app.frontend.componentes.graficas.base import grafica_base
from agrocebada_app.frontend.tema.html import titulo


def comparar(ctx, pid):
    d = ctx.d
    S = ctx.S
    C = ctx.C
    pred = ctx.pred
    with st.container(key="glass_comparar"):
        titulo("Comparar parcelas", "Hasta 3 parcelas: su curva y sus datos principales, lado a lado.")
        k1, k2, k3 = st.columns([3, 1.3, 1.2])
        sugeridas = [pid] + [i for i in vecinas(d, pid) if i != pid][:2]
        elegidas = k1.multiselect("Parcelas", sorted(d.index), default=sugeridas, max_selections=3,
                                  key=f"comparar-{pid}")
        ind = k2.selectbox("Índice", list(INDICES), key="comparar_indice")
        sensor = k3.selectbox("Sensor", ["Sentinel-2", "Planet"], key="comparar_sensor")
        if elegidas:
            col = INDICES[ind]
            x = S[S.ID_POLIGONO.isin(elegidas) & (S.sensor == sensor) & S[col].notna()][["ID_POLIGONO", "fecha", col]]
            if x.empty:
                st.info("No hay capturas despejadas de ese sensor para estas parcelas.")
            else:
                base = alt.Chart(x).encode(
                    x=alt.X("fecha:T", title=None, axis=alt.Axis(format="%d/%m")), y=alt.Y(f"{col}:Q", title=ind),
                    color=alt.Color("ID_POLIGONO:N", title=None, legend=alt.Legend(orient="top"),
                                    scale=alt.Scale(domain=elegidas, range=["#FF7A45", "#9BE15D", "#7FB2FF"])),
                    tooltip=["ID_POLIGONO", alt.Tooltip("fecha:T", format="%d/%m/%Y"),
                             alt.Tooltip(f"{col}:Q", format=".2f")])
                st.altair_chart(grafica_base(base.mark_line(strokeWidth=2) + base.mark_circle(size=30), 260),
                                width="stretch")
            filas = []
            for i in elegidas:
                ri, est = d.loc[i], d.loc[i, "CONJUNTO"] == "PREDICCION"
                s_i = S[(S.ID_POLIGONO == i) & S.ndvi_promedio.notna()]
                top = s_i.sort_values("ndvi_promedio").iloc[-1] if len(s_i) else None
                c_i = C[C.id_parcela == i] if C is not None else None
                filas.append({"parcela": i, "municipio": ri.municipio,
                              "rendimiento (t/ha)": float(pred.prediccion[i]) if est else float(ri.real),
                              "tipo": "estimación" if est else "registrado", "área (ha)": ri.AREA_HA,
                              "NDVI máximo": top.ndvi_promedio if top is not None else None,
                              "mes del máximo": MESES[top.fecha.month] if top is not None else "",
                              "lluvia mar–oct (mm)": c_i.PREC.sum() if c_i is not None and len(c_i) else None})
            st.dataframe(pd.DataFrame(filas), hide_index=True, width="stretch",
                         column_config={"rendimiento (t/ha)": st.column_config.NumberColumn(format="%.2f"),
                                        "área (ha)": st.column_config.NumberColumn(format="%.2f"),
                                        "NDVI máximo": st.column_config.NumberColumn(format="%.2f"),
                                        "lluvia mar–oct (mm)": st.column_config.NumberColumn(format="%.0f")})
