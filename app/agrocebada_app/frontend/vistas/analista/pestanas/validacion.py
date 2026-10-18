"""Pestaña «Validación»: métricas por escenario y municipio, dispersión e información insuficiente."""
import altair as alt
import pandas as pd
import streamlit as st

from agrocebada_app.backend.modelo.estimador import predecir
from agrocebada_app.backend.modelo.metricas import metricas
from agrocebada_app.frontend.componentes.graficas.base import grafica_base
from agrocebada_app.frontend.tema.html import h, titulo


def validacion(ctx):
    d = ctx.d
    modelo = ctx.modelo
    pred = ctx.pred
    O = ctx.O
    OA = ctx.OA
    cob_mun = ctx.cob_mun
    if O is None:
        st.info("No encontré las predicciones de validación de T08.")
    else:
        with st.container(key="glass_val"):
            titulo("Resultados fuera del entrenamiento",
                   "Validación cruzada 5 × 5. «Sin respaldo» son las predicciones cuyo municipio sí estaba en el "
                   "entrenamiento, que es el caso de las 59.")
            filas = []
            for esc, nom in [("A", "A · municipio conocido (principal)"), ("B", "B · zona de lluvia nueva")]:
                for sub, x in [("todas", O[O.escenario == esc]),
                               ("sin respaldo", O[(O.escenario == esc) & (O.fuente == "municipio")])]:
                    filas.append({"escenario": nom, "predicciones": sub, **metricas(x).to_dict()})
            st.dataframe(pd.DataFrame(filas).rename(columns={"MAE": "MAE (t/ha)", "RMSE": "RMSE (t/ha)",
                                                             "sesgo": "sesgo (t/ha)", "R2": "R²"}),
                         hide_index=True, width="stretch",
                         column_config={c: st.column_config.NumberColumn(format="%.3f")
                                        for c in ["MAE (t/ha)", "RMSE (t/ha)", "sesgo (t/ha)", "R²"]})
        v1, v2 = st.columns([2, 3])
        with v1, st.container(key="glass_mun"):
            titulo("Por municipio", "Escenario A, sin respaldo.")
            pm = OA.groupby("municipio").agg(parcelas=("ID_POLIGONO", "nunique"), MAE=("ae", "mean"))
            pm["dentro de ± MAE"] = (cob_mun * 100).round(0).astype(int).astype(str) + " %"
            st.dataframe(pm.reset_index().rename(columns={"MAE": "MAE (t/ha)"}), hide_index=True, width="stretch",
                         column_config={"MAE (t/ha)": st.column_config.NumberColumn(format="%.3f")})
        with v2, st.container(key="glass_disp_val"):
            titulo("Registrado contra estimado",
                   "Cada punto es una de las 138 parcelas; sobre la diagonal la estimación sería perfecta.")
            sc = OA.groupby("ID_POLIGONO").agg(real=("real", "first"), estimacion=("prediccion", "mean"),
                                               municipio=("municipio", "first")).reset_index()
            dom = alt.Scale(domain=[2, 6])
            puntos = alt.Chart(sc).mark_circle(size=55, opacity=0.85).encode(
                x=alt.X("real:Q", title="registrado (t/ha)", scale=dom),
                y=alt.Y("estimacion:Q", title="estimado sin conocerlo (t/ha)", scale=dom),
                color=alt.Color("municipio:N", title=None,
                                legend=alt.Legend(orient="bottom", direction="horizontal", columns=2, labelLimit=220,
                                                  labelFontSize=11, columnPadding=12, rowPadding=6)),
                tooltip=["ID_POLIGONO", "municipio", "real", alt.Tooltip("estimacion", format=".2f")])
            diag = alt.Chart(pd.DataFrame({"x": [2, 6], "y": [2, 6]})).mark_line(
                color="rgba(255,255,255,0.35)", strokeDash=[4, 4]).encode(
                x=alt.X("x:Q", scale=dom), y=alt.Y("y:Q", scale=dom))
            st.altair_chart(grafica_base(diag + puntos, 300), width="stretch")
        with st.container(key="glass_insuf"):
            titulo("Caso de información insuficiente",
                   "Simula que un municipio no tuviera parcelas con cosecha y mira qué valor aplicaría la app.")
            oculto = st.selectbox("Municipio a ocultar", sorted(pred.municipio.unique()))
            sim = predecir(d, modelo, ocultar=oculto)
            comp = pd.DataFrame({"municipio": pred.municipio, "estimación normal": pred.prediccion,
                                 "sin datos del municipio": sim.prediccion, "fuente": sim.fuente})
            st.dataframe(comp[comp.municipio == oculto].round(2).reset_index(), hide_index=True, width="stretch")
            resp = O[(O.escenario == "A") & (O.fuente != "municipio")]
            if len(resp):
                h(f"<div class='nota'>La app aplica el respaldo evaluado (valor del grupo de registro y luego el "
                  f"general) y lo indica en la columna fuente. En la validación ocurrió en {len(resp)} "
                  f"predicciones, con MAE {resp.ae.mean():.2f} t/ha. En las 59 reales no ocurre.</div>")
