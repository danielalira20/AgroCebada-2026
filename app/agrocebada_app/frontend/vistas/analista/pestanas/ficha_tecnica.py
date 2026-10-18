"""Pestaña «Ficha técnica»: estimación, disponibilidad de datos, curvas y comparación."""
import pandas as pd
import streamlit as st

from agrocebada_app.config import INDICES
from agrocebada_app.frontend.componentes.descargas.boton_ficha import boton_ficha
from agrocebada_app.frontend.componentes.graficas.clima import curva_clima
from agrocebada_app.frontend.componentes.graficas.indices import curva_indice
from agrocebada_app.frontend.tema.html import e, h, titulo
from agrocebada_app.frontend.vistas.analista.pestanas.comparar import comparar


def ficha_tecnica(ctx):
    d = ctx.d
    sop = ctx.sop
    S = ctx.S
    C = ctx.C
    modelo = ctx.modelo
    pred = ctx.pred
    oof_parcela = ctx.oof_parcela
    FICHA = ctx.FICHA
    pid = st.selectbox("Parcela (ID)", sorted(d.index), index=sorted(d.index).index(pred.index[0]))
    r = d.loc[pid]
    with st.container(key="glass_ficha"):
        titulo(f"{pid} · {r.municipio}, {r.Estado}", f"{r.AREA_HA:.2f} ha · grupo de registro {r.grupo_registro}")
        if r.CONJUNTO == "PREDICCION":
            p = pred.loc[pid]
            kp = [("Estimación (modelo final)", f"{p.prediccion:.2f}", "t/ha"),
                  ("Referencia territorial", f"{p.fuente}", f"{int(p.n_municipio)} parcelas")]
            if pd.notna(p.error_tipico):
                kp.append(("MAE del municipio", f"{p.error_tipico:.2f}", "t/ha"))
        else:
            kp = [("Rendimiento registrado", f"{r.real:.2f}", "t/ha")]
            if pid in oof_parcela.index:
                kp += [("Estimación fuera del entrenamiento", f"{oof_parcela[pid]:.2f}", "t/ha"),
                       ("Error", f"{oof_parcela[pid] - r.real:+.2f}", "t/ha")]
        h("<div class='fila'>" + "".join(
            f"<div class='mini'><span>{e(k)}</span><b class='kv'>{e(v)}<small>{e(u)}</small></b></div>"
            for k, v, u in kp) + "</div>")
        if r.CONJUNTO == "PREDICCION" and pred.loc[pid, "aviso"]:
            h(f"<div class='aviso'>Aviso: {e(pred.loc[pid, 'aviso'])}.</div>")
        b1, _ = st.columns([1, 3])
        with b1:
            boton_ficha(pid, "ficha_analista", modelo, FICHA)
    f1, f2 = st.columns([1, 1])
    with f1, st.container(key="glass_disp"):
        titulo("Disponibilidad de datos", "Temporada junio–octubre de 2025.")
        if sop is not None and pid in sop.index:
            s0 = sop.loc[pid]
            st.dataframe(pd.DataFrame({
                "sensor": ["Sentinel-2", "Planet", "Landsat"],
                "con dato": [s0.s2_capturas_con_dato, s0.pl_capturas_con_dato, s0.ls_capturas_con_dato],
                "despejadas": [s0.s2_capturas_despejadas, s0.pl_capturas_despejadas, s0.ls_capturas_despejadas],
                "meses sin despejada": [s0.s2_meses_sin_despejada, s0.pl_meses_sin_despejada,
                                        s0.ls_meses_sin_despejada],
                "hueco máx. (días)": [s0.s2_hueco_max_dias_jun_oct, s0.pl_hueco_max_dias_jun_oct,
                                      s0.ls_hueco_max_dias_jun_oct]}),
                hide_index=True, width="stretch")
        else:
            st.info("No encontré el soporte de T03 para esta parcela.")
    with f2, st.container(key="glass_indice"):
        nombre = st.segmented_control("Índice", list(INDICES), default=list(INDICES)[0],
                                      label_visibility="collapsed") or list(INDICES)[0]
        curva_indice(S, pid, INDICES[nombre], nombre, alto=220)
        h("<div class='nota'>Cada punto es una captura con nubosidad ≤ 20 %; los tramos sin puntos son huecos. "
          "Contexto: los índices no entran al modelo final.</div>")
    if C is not None:
        with st.container(key="glass_clima_ficha"):
            titulo("Clima mensual", "Ponderado por área (CHIRPS y temperatura). Contexto: no entra al modelo final.")
            curva_clima(C, pid, alto=220)
    comparar(ctx, pid)
