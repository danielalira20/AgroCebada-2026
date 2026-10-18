"""Pestaña «Validación»: métricas por población, confianza por municipio, dispersión e información insuficiente.
Las cifras y los textos salen de backend/dominio/validacion.py; aquí sólo se dibujan."""
import altair as alt
import pandas as pd
import streamlit as st

from agrocebada_app.backend.dominio.validacion import (
    comparacion_oculto, contraste_respaldo, descripcion_principal, frase_respaldo, poblaciones, por_municipio,
    regla_confianza)
from agrocebada_app.backend.modelo.estimador import predecir
from agrocebada_app.frontend.componentes.graficas.base import grafica_base
from agrocebada_app.frontend.tema.html import e, h, titulo

TRES_DECIMALES = ["MAE (t/ha)", "RMSE (t/ha)", "Sesgo (t/ha)", "R²"]


def _tarjetas(items):
    h("<div class='fila'>" + "".join(f"<div class='mini'><span>{e(k)}</span><b class='kv'>{e(v)}<small>{e(u)}</small></b></div>"
                                     for k, v, u in items) + "</div>")


def _poblaciones(ctx):
    """Tabla principal: A · sin respaldo destacada y las demás poblaciones como apoyo, cada una con su nombre."""
    pob = poblaciones(ctx.O)
    with st.container(key="glass_val"):
        titulo("Resultados fuera del entrenamiento",
               "Validación cruzada 5 × 5. «Sin respaldo» son las predicciones cuyo municipio sí estaba en el "
               "entrenamiento, que es el caso de las 59.")
        if pob.principal.any():
            p = pob[pob.principal].iloc[0]
            h(f"<div class='nota'><b>Población principal.</b> {e(descripcion_principal(pob))}</div>")
            _tarjetas([("MAE", f"{p.MAE:.3f}", "t/ha"), ("RMSE", f"{p.RMSE:.3f}", "t/ha"),
                       ("Sesgo", f"{p.sesgo:+.3f}", "t/ha"), ("R²", f"{p.R2:.3f}", "")])
        h("<div class='nota'>Las demás poblaciones, como apoyo. Las parcelas son distintas en cada una: no se "
          "comparan cifras de poblaciones distintas sin decir cuál es cuál.</div>")
        vista = pob.assign(poblacion=pob.poblacion + pob.principal.map({True: " (principal)", False: ""})).drop(
            columns="principal").rename(columns={"poblacion": "Población", "parcelas": "Parcelas",
                                                 "predicciones": "Predicciones", "MAE": "MAE (t/ha)",
                                                 "RMSE": "RMSE (t/ha)", "sesgo": "Sesgo (t/ha)", "R2": "R²"})
        st.dataframe(vista, hide_index=True, width="stretch",
                     column_config={c: st.column_config.NumberColumn(format="%.3f") for c in TRES_DECIMALES})


def _por_municipio(ctx):
    """Error y confianza de cada municipio, con la regla escrita debajo."""
    conf = ctx.conf
    mae_general = float(conf.mae_general.iloc[0]) if len(conf) else float("nan")
    with st.container(key="glass_mun"):
        titulo("Por municipio", "Escenario A, sin respaldo. La confianza sale de la regla de abajo.")
        pm = por_municipio(conf, ctx.cob_mun).rename(columns={
            "municipio": "Municipio", "n_cosecha": "Parcelas con cosecha", "mae_municipio": "MAE (t/ha)",
            "dentro": "Dentro de ± MAE", "confianza": "Confianza"})
        st.dataframe(pm, hide_index=True, width="stretch",
                     column_config={"MAE (t/ha)": st.column_config.NumberColumn(format="%.3f")})
        reglas = "<br>".join(f"<b>{e(n)}:</b> {e(t)}" for n, t in (x.split(": ", 1) for x in regla_confianza(mae_general)))
        h(f"<div class='nota'><b>Cómo se decide la confianza</b><br>{reglas}</div>")


def _dispersion(ctx):
    """Registrado contra estimado, con las parcelas de A · sin respaldo."""
    OA = ctx.OA
    with st.container(key="glass_disp_val"):
        titulo("Registrado contra estimado",
               f"Cada punto es una de las {OA.ID_POLIGONO.nunique()} parcelas de A · sin respaldo; sobre la "
               "diagonal la estimación sería perfecta.")
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


def _insuficiente(ctx):
    """Oculta un municipio y muestra qué valor y qué confianza tendría la estimación sin sus datos."""
    pred = ctx.pred
    with st.container(key="glass_insuf"):
        titulo("Caso de información insuficiente",
               "Simula que un municipio no tuviera parcelas con cosecha y mira qué valor aplicaría la app y con qué "
               "confianza.")
        oculto = st.selectbox("Municipio a ocultar", sorted(pred.municipio.unique()))
        sim = predecir(ctx.d, ctx.modelo, ocultar=oculto)
        tabla, motivo = comparacion_oculto(pred, sim, ctx.conf, oculto)
        st.dataframe(tabla.reset_index(), hide_index=True, width="stretch")
        h(f"<div class='nota'>{e(motivo)}</div>")
        h("<div class='nota'>La app aplica el respaldo evaluado (valor del grupo de registro y luego el general), lo "
          "indica en la columna fuente y lo marca siempre con confianza baja. "
          f"{e(frase_respaldo(contraste_respaldo(ctx.O, pred)))}</div>")


def validacion(ctx):
    if ctx.O is None or ctx.OA is None or ctx.OA.empty:
        st.info("No se encontraron los resultados de validación del modelo.")
        return
    _poblaciones(ctx)
    v1, v2 = st.columns([2, 3])
    with v1:
        _por_municipio(ctx)
    with v2:
        _dispersion(ctx)
    _insuficiente(ctx)
