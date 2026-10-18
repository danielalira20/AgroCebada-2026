"""Vista del analista: mapa de las 197 parcelas, resumen y seis pestañas."""
import streamlit as st

from agrocebada_app.backend.dominio.geometria import vecinas
from agrocebada_app.config import AYUDA_MAPA, CREDITOS, MODELOS
from agrocebada_app.frontend.componentes.mapa.mapa import mapa
from agrocebada_app.frontend.componentes.paneles.leyenda import leyenda
from agrocebada_app.frontend.tema.html import e, h
from agrocebada_app.frontend.vistas.analista.pestanas.cartera import cartera
from agrocebada_app.frontend.vistas.analista.pestanas.estimaciones import estimaciones
from agrocebada_app.frontend.vistas.analista.pestanas.ficha_tecnica import ficha_tecnica
from agrocebada_app.frontend.vistas.analista.pestanas.metodo_limites import metodo_limites
from agrocebada_app.frontend.vistas.analista.pestanas.validacion import validacion
from agrocebada_app.frontend.vistas.analista.seleccion import clic_analista
from agrocebada_app.frontend.vistas.datos_propios.vista import datos_propios


def mostrar(ctx):
    d = ctx.d
    modelo = ctx.modelo
    satelite = ctx.satelite
    pred = ctx.pred
    DET = ctx.DET
    centro_total = ctx.centro_total
    mA = ctx.mA
    with st.container(key="hero"):
        with st.container(key="glass_filtros"):
            capa = st.segmented_control("Mostrar", ["Todas", "Las 59", "Las 138"], key="capa") or "Todas"
            muni_f = st.selectbox("Municipio", ["Todos"] + sorted(d.municipio.unique()))
            buscado = st.selectbox("Buscar parcela por ID", ["(ninguna)"] + sorted(d.index), key="buscar_id",
                                   help="También puedes hacer clic en una parcela del mapa.",
                                   on_change=lambda: st.session_state.update(encuadre_an=st.session_state.buscar_id))
            encuadre = st.session_state.get("encuadre_an", "(ninguna)")     # el mapa se acerca sólo con el buscador
            if buscado != "(ninguna)":
                rb = d.loc[buscado]
                valor = (f"estimación {pred.loc[buscado, 'prediccion']:.2f} t/ha" if rb.CONJUNTO == "PREDICCION"
                         else f"registrado {rb.real:.2f} t/ha")
                h(f"<div class='encontrada'><b>{e(buscado)}</b> · {e(rb.municipio)} · {valor}</div>")
        with st.container(key="glass_leyenda"):
            arriba = leyenda()
        resaltar = buscado if buscado != "(ninguna)" else None
        if encuadre != "(ninguna)":
            re_ = d.loc[encuadre]
            mapa(d, pred, vecinas(d, encuadre), (re_.lon_c, re_.lat_c), 13.2, resaltar=resaltar, altura=700,
                 escala=30, satelite=satelite, arriba=arriba, detalle=DET, clave=f"mapa-an-{encuadre}",
                 al_clic=lambda clave: clic_analista(clave, d))
        else:
            ids = [i for i in d.index if (muni_f == "Todos" or d.loc[i, "municipio"] == muni_f) and not (
                (capa == "Las 59" and d.loc[i, "CONJUNTO"] != "PREDICCION") or
                (capa == "Las 138" and d.loc[i, "CONJUNTO"] == "PREDICCION"))]
            if not ids:
                ids = list(d.index[d.municipio == muni_f]) if muni_f != "Todos" else list(d.index)
            c0 = (d.loc[ids].lon_c.mean(), d.loc[ids].lat_c.mean()) if muni_f != "Todos" else centro_total
            mapa(d, pred, ids, c0, 11.2 if muni_f != "Todos" else 9.9, altura=700, resaltar=resaltar,
                 escala=250 if muni_f != "Todos" else 450, satelite=satelite, arriba=arriba, detalle=DET,
                 clave=f"mapa-an-{muni_f}-{capa}", al_clic=lambda clave: clic_analista(clave, d))
        with st.container(key="glass_kpis"):
            kp = [("Parcelas estimadas", f"{len(pred)}", ""), ("Estimación promedio", f"{pred.prediccion.mean():.2f}", "t/ha")]
            if mA is not None:
                kp += [
                    ("MAE · A sin respaldo", f"{mA.MAE:.3f}", "t/ha"),
                    ("R² · A sin respaldo", f"{mA.R2:.3f}", ""),
                ]
            h(f"<div class='eyebrow'>Resumen · {e(MODELOS[modelo])}</div><div class='kpis'>" + "".join(
                f"<div class='mini'><span>{k}</span><b class='kv'>{v}<small>{u}</small></b></div>" for k, v, u in kp)
              + "</div>")
    h(f"<div class='creditos'>{AYUDA_MAPA} · {e(CREDITOS)}</div>")

    t0, t1, t2, t3, t4, t5 = st.tabs(["Cartera", "Las 59 estimaciones", "Ficha técnica", "Validación",
                                      "Método y límites", "Analizar tus datos"])

    with t0:
        cartera(ctx)
    with t1:
        estimaciones(ctx)
    with t2:
        ficha_tecnica(ctx)
    with t3:
        validacion(ctx)
    with t4:
        metodo_limites(ctx)
    with t5:
        datos_propios(ctx)
