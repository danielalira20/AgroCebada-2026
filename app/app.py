"""AgroCebada 2026 · App de estimación de rendimiento (T17).

Ejecuta el mismo procedimiento que T08 (valor típico del municipio con respaldo por grupo de registro y luego global)
con las 138 parcelas con rendimiento y estima las 59 reservadas. Dos vistas:
  - Agricultor: una parcela, su estimación en t/ha, el error observado, su mapa 3D, su verdor, su clima y su ficha PDF.
  - Analista: mapa 3D de las 197, las 59 con verificación y exportación, ficha técnica y comparación de parcelas,
    validación por escenario y municipio, información insuficiente y análisis de un dataset propio (carga segura).

Datos: lee el paquete compacto `datos_app/` (lo arma herramientas/preparar_datos.py); si no está, las fuentes del repo.
El mapa 3D pone las parcelas sobre el relieve real (Terrain Tiles de AWS) con imagen Sentinel-2 sin nubes (EOX).

Uso (desde esta carpeta):  streamlit run app.py
"""
import hashlib

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

import agro_carga as K
import agro_datos as A
from agrocebada_app.backend.dominio.avisos import avisos_de
from agrocebada_app.backend.dominio.geometria import vecinas, zoom_para
from agrocebada_app.backend.dominio.notas import nota_de
from agrocebada_app.backend.dominio.resumen import detalles, resumen_parcela
from agrocebada_app.backend.ficha_pdf.armado import ContextoFicha
from agrocebada_app.backend.modelo.estimador import predecir
from agrocebada_app.backend.modelo.metricas import metricas
from agrocebada_app.config import AYUDA_MAPA, CREDITOS, INDICES, MESES, MODELO_OFICIAL, MODELOS
from agrocebada_app.frontend.componentes.descargas.boton_ficha import boton_ficha
from agrocebada_app.frontend.componentes.graficas.base import grafica_base
from agrocebada_app.frontend.componentes.graficas.clima import curva_clima
from agrocebada_app.frontend.componentes.graficas.indices import curva_indice
from agrocebada_app.frontend.componentes.mapa.interaccion import parcela_clicada
from agrocebada_app.frontend.componentes.mapa.mapa import mapa
from agrocebada_app.frontend.componentes.paneles.leyenda import leyenda
from agrocebada_app.frontend.estado.cache import cargar, clima, elevaciones, oficial, oof, series, soporte
from agrocebada_app.frontend.tema.estilos import ESTILO, ICONO, MARCA, MASCOTA
from agrocebada_app.frontend.tema.html import chips, e, h, titulo


# ---------------------------------------------------------------- selección en el mapa
def clic_agricultor(clave):
    pid = parcela_clicada(clave)
    if pid in d.index:                  # se cambia la parcela elegida, no el encuadre del mapa
        st.session_state["agri_muni"], st.session_state["agri_parcela"] = d.loc[pid, "municipio"], pid


def clic_analista(clave):
    pid = parcela_clicada(clave)
    if pid in d.index:
        st.session_state["buscar_id"] = pid


def primera_reservada(muni):
    ids = sorted(d.index[d.municipio == muni])
    res = [i for i in ids if d.loc[i, "CONJUNTO"] == "PREDICCION"]
    return res[0] if res else ids[0]


# ---------------------------------------------------------------- datos propios
def analizar_subido(res, modelo, satelite):
    du = res.datos
    pu = predecir(du, modelo)
    v = A.validacion_dejando_uno(du, modelo)
    m = metricas(v)
    err = v[v.fuente == "municipio"].groupby("municipio").ae.mean()
    pu["error_tipico"] = pu.municipio.map(err)
    with st.container(key="glass_revision"):
        titulo("Revisión del archivo", "El archivo pasó todas las reglas de formato y seguridad.")
        h("".join(f"<span class='chk ok'>✓ {e(x)}</span>" for x in res.revisiones))
        for a in res.avisos:
            h(f"<div class='aviso'>{e(a)}</div>")
    with st.container(key="glass_resultado_subido"):
        titulo("Resultado", f"Mismo procedimiento de T08 ({'mediana' if modelo.startswith('mediana') else 'media'} "
                            "del municipio, respaldo por grupo y luego general).")
        kp = [("Parcelas por estimar", f"{len(pu)}", ""), ("Municipios", f"{du.municipio.nunique()}", ""),
              ("MAE dejando una fuera", f"{m.MAE:.3f}", "t/ha"), ("R² dejando una fuera", f"{m.R2:.3f}", "")]
        h("<div class='fila'>" + "".join(f"<div class='mini'><span>{e(k)}</span><b class='kv'>{v_}<small>{u}</small>"
                                         f"</b></div>" for k, v_, u in kp) + "</div>")
        h("<div class='nota'>Validación rápida: cada parcela con cosecha se estima sin ella misma. Sirve como "
          "referencia; la validación oficial del proyecto es la 5 × 5 de T03.</div>")
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


# ---------------------------------------------------------------- arranque
st.set_page_config(page_title="AgroCebada · Rendimiento de cebada", page_icon=ICONO, layout="wide",
                   initial_sidebar_state="collapsed")
h(f"<style>{ESTILO}</style>")
if not A.hay_datos():
    st.error("No encontré los datos de la app. Corre herramientas/preparar_datos.py o fija la ruta del dataset con AGRO_DATOS.")
    st.stop()

d = cargar()
sop = soporte()
S = series()
C = clima()
centro_total = (d.lon_c.mean(), d.lat_c.mean())
for k, v in {"vista": "Agricultor", "modelo": MODELO_OFICIAL, "capa": "Todas", "vista_mapa": "3D"}.items():
    st.session_state.setdefault(k, v)

with st.container(key="glass_top"):
    c1, c2, c3, c4 = st.columns([4.4, 2.1, 2.3, 1.3], vertical_alignment="center")
    with c1:
        h(MARCA)
    vista = c2.segmented_control("Vista", ["Agricultor", "Analista"], key="vista", label_visibility="collapsed")
    agricultor = (vista or "Agricultor") == "Agricultor"
    modelo = MODELO_OFICIAL
    if not agricultor:
        modelo = c3.segmented_control("Modelo", list(MODELOS), format_func=MODELOS.get, key="modelo",
                                      label_visibility="collapsed",
                                      help="La media es la referencia oficial de T08. La mediana se propuso en el PR #23.")
        modelo = modelo or MODELO_OFICIAL
    satelite = c4.toggle("Satélite", value=True, key="satelite",
                         help="Imagen Sentinel-2 sobre el relieve. Apágalo si tu conexión es lenta.")

pred = predecir(d, modelo)
O = oof(modelo, d.municipio)
OA = O[(O.escenario == "A") & (O.fuente == "municipio")] if O is not None else None
OAT = O[O.escenario == "A"] if O is not None else None                        # todas las predicciones de A
err_mun = OA.groupby("municipio").ae.mean() if OA is not None else pd.Series(dtype=float)
cob_mun = (OA.assign(dentro=OA.ae <= OA.municipio.map(err_mun)).groupby("municipio").dentro.mean()
           if OA is not None else pd.Series(dtype=float))
pred["error_tipico"] = pred.municipio.map(err_mun)
pred["aviso"] = avisos_de(pred, sop)
oof_parcela = OAT.groupby("ID_POLIGONO").prediccion.mean() if OAT is not None else pd.Series(dtype=float)
DET = detalles(d, pred, oof_parcela)
FICHA = ContextoFicha(d=d, pred=pred, oof_parcela=oof_parcela, cob_mun=cob_mun, clima=C, series=S)

# ================================================================= VISTA AGRICULTOR
if agricultor:
    with st.container(key="hero"):
        with st.container(key="glass_panel"):
            h("<div class='eyebrow'>Tu parcela</div>")
            st.session_state.setdefault("agri_muni", "Chignahuapan")
            munis = sorted(d.municipio.unique())

            def otro_municipio():
                st.session_state["agri_parcela"] = primera_reservada(st.session_state.agri_muni)
                st.session_state["encuadre_agri"] = st.session_state["agri_parcela"]

            muni = st.selectbox("Municipio", munis, key="agri_muni", on_change=otro_municipio)
            ids = sorted(d.index[d.municipio == muni])
            if st.session_state.get("agri_parcela") not in ids:
                st.session_state["agri_parcela"] = primera_reservada(muni)
            pid = st.selectbox("Parcela", ids, key="agri_parcela",
                               on_change=lambda: st.session_state.update(encuadre_agri=st.session_state.agri_parcela),
                               format_func=lambda i: f"{i} · {'por estimar' if d.loc[i, 'CONJUNTO'] == 'PREDICCION' else 'con cosecha registrada'}")
            encuadre = st.session_state.setdefault("encuadre_agri", pid)       # parcela en la que se centra el mapa
            r = d.loc[pid]
            if r.CONJUNTO == "PREDICCION":
                p = pred.loc[pid]
                partes = [f"<div class='eyebrow' style='margin-top:6px'>Rendimiento estimado</div>"
                          f"<div class='big'>{p.prediccion:.2f}<small>t/ha</small></div><div class='fila'>"
                          f"<div class='mini'><span>Producción estimada</span><b>{p.prediccion * r.AREA_HA:.1f} t</b></div>"]
                if pd.notna(p.error_tipico):
                    partes.append(f"<div class='mini'><span>Error típico</span><b>± {p.error_tipico:.2f} t/ha</b></div>")
                partes.append("</div>")
                partes.append(f"<div class='nota'>{e(nota_de(d, pred, cob_mun, pid))}</div>")
                if p.aviso:
                    partes.append(f"<div class='aviso'>Tómalo con más cuidado: {e(p.aviso)}.</div>")
                h("".join(partes))
            else:
                partes = [f"<div class='eyebrow' style='margin-top:6px'>Rendimiento registrado</div>"
                          f"<div class='big'>{r.real:.2f}<small>t/ha</small></div>"]
                if pid in oof_parcela.index:
                    partes.append(f"<div class='fila'><div class='mini'><span>Lo que estimó el método sin conocerla</span>"
                                  f"<b>{oof_parcela[pid]:.2f} t/ha</b></div><div class='mini'><span>Diferencia</span>"
                                  f"<b>{oof_parcela[pid] - r.real:+.2f} t/ha</b></div></div>")
                partes.append(f"<div class='nota'>{e(nota_de(d, pred, cob_mun, pid))}</div>")
                h("".join(partes))
            boton_ficha(pid, "ficha_agricultor", modelo, FICHA)
        with st.container(key="glass_leyenda"):
            arriba = leyenda()
        rc = d.loc[encuadre]
        mapa(d, pred, vecinas(d, encuadre), (rc.lon_c - 0.018, rc.lat_c), 13.2, resaltar=pid, altura=700,
             escala=30, satelite=satelite, arriba=arriba, detalle=DET, clave=f"mapa-agri-{encuadre}",
             al_clic=clic_agricultor)
        with st.container(key="glass_chips"):
            chips(resumen_parcela(d, pid, elevaciones(), C, S))
    h(f"<div class='creditos'>Tu parcela en naranja; las vecinas a ~6 km. {AYUDA_MAPA} · {e(CREDITOS)}</div>")

    g1, g2 = st.columns(2)
    with g1, st.container(key="glass_ndvi"):
        titulo("Verdor de tu parcela en 2025", "Sube cuando el cultivo crece y baja al madurar o cosechar.")
        curva_indice(S, pid, "ndvi_promedio", "NDVI")
    with g2, st.container(key="glass_clima"):
        titulo("Lluvia y temperatura", "Promedio mensual de la zona (pixel de ~5.5 km).")
        if C is not None:
            curva_clima(C, pid)
        else:
            st.info("No encontré la tabla de clima de T04.")
    with st.container(key="glass_explica"):
        h(f"<div class='mascota'><div class='cebi'>{MASCOTA}</div><div><div class='tit'>Cómo leer esta estimación</div>"
          "<div class='nota' style='margin-top:4px'>La cifra sale de las parcelas de tu municipio que ya tienen cosecha "
          "registrada. El verdor y el clima se muestran para seguimiento: no cambian la estimación y un color o una "
          "curva no son una recomendación agronómica. El rendimiento no indica calidad maltera ni capacidad de pago."
          "</div></div></div>")

# ================================================================= VISTA ANALISTA
else:
    mA = metricas(OAT) if O is not None else None          # igual que metricas_referencias.csv de T08
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
                 al_clic=clic_analista)
        else:
            ids = [i for i in d.index if (muni_f == "Todos" or d.loc[i, "municipio"] == muni_f) and not (
                (capa == "Las 59" and d.loc[i, "CONJUNTO"] != "PREDICCION") or
                (capa == "Las 138" and d.loc[i, "CONJUNTO"] == "PREDICCION"))]
            if not ids:
                ids = list(d.index[d.municipio == muni_f]) if muni_f != "Todos" else list(d.index)
            c0 = (d.loc[ids].lon_c.mean(), d.loc[ids].lat_c.mean()) if muni_f != "Todos" else centro_total
            mapa(d, pred, ids, c0, 11.2 if muni_f != "Todos" else 9.9, altura=700, resaltar=resaltar,
                 escala=250 if muni_f != "Todos" else 450, satelite=satelite, arriba=arriba, detalle=DET,
                 clave=f"mapa-an-{muni_f}-{capa}", al_clic=clic_analista)
        with st.container(key="glass_kpis"):
            kp = [("Parcelas estimadas", f"{len(pred)}", ""), ("Estimación promedio", f"{pred.prediccion.mean():.2f}", "t/ha")]
            if mA is not None:
                kp += [("MAE validación A", f"{mA.MAE:.3f}", "t/ha"), ("R² validación A", f"{mA.R2:.3f}", "")]
            h(f"<div class='eyebrow'>Resumen · {e(MODELOS[modelo])}</div><div class='kpis'>" + "".join(
                f"<div class='mini'><span>{k}</span><b class='kv'>{v}<small>{u}</small></b></div>" for k, v, u in kp)
              + "</div>")
    h(f"<div class='creditos'>{AYUDA_MAPA} · {e(CREDITOS)}</div>")

    t1, t2, t3, t4, t5 = st.tabs(["Las 59 estimaciones", "Ficha técnica", "Validación", "Método y límites",
                                  "Analizar tus datos"])

    with t1, st.container(key="glass_tabla"):
        of = oficial(modelo)
        checks = [("59 IDs", len(pred) == 59), ("Sin IDs duplicados", pred.index.is_unique),
                  ("Valores finitos", bool(np.isfinite(pred.prediccion).all()))]
        if of is not None:
            checks.append(("Coinciden con el archivo de T08",
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

    with t2:
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

    with t3:
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
                    color=alt.Color("municipio:N", title=None, legend=alt.Legend(orient="bottom", columns=3)),
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

    with t4:
        n_tr = int((d.CONJUNTO == "ENTRENAMIENTO").sum())
        n_mun = d[d.CONJUNTO == "ENTRENAMIENTO"].municipio.nunique()
        estad = "mediana" if modelo.startswith("mediana") else "media"
        with st.container(key="glass_metodo"):
            titulo("Cómo se calcula", "Es el mismo procedimiento de T08; la app lo ejecuta cada vez que se abre.")
            pasos = [("Datos", f"{n_tr} parcelas con cosecha registrada en 2025, de {n_mun} municipios."),
                     ("Valor típico del municipio", f"Para cada municipio se calcula la {estad} del rendimiento de "
                                                    "esas parcelas."),
                     ("Asignación", "Cada parcela reservada recibe el valor de su municipio. Si no hubiera datos del "
                                    "municipio, se usa el de su grupo de registro y, al final, el general."),
                     ("Validación", "Se repite el cálculo escondiendo parcelas conocidas: validación cruzada 5 × 5 "
                                    "(escenario A) y por zonas de lluvia completas (escenario B), con la regla de T03 "
                                    "escrita antes de ver resultados.")]
            h("<div class='pasos'>" + "".join(f"<div class='paso'><div class='n'>{i}</div><b>{e(t)}</b><p>{e(x)}</p></div>"
                                              for i, (t, x) in enumerate(pasos, 1)) + "</div>")
        r1, r2 = st.columns([3, 2])
        with r1, st.container(key="glass_resultados"):
            titulo("Qué tan bien funciona", "Error al estimar parcelas que el método no vio.")
            if O is not None:
                mB = metricas(O[O.escenario == "B"])
                kp = [("MAE · municipio conocido (A)", f"{mA.MAE:.3f}", "t/ha"), ("R² · escenario A", f"{mA.R2:.3f}", ""),
                      ("MAE · zona de lluvia nueva (B)", f"{mB.MAE:.3f}", "t/ha")]
                h("<div class='fila'>" + "".join(
                    f"<div class='mini'><span>{e(k)}</span><b class='kv'>{v}<small>{u}</small></b></div>"
                    for k, v, u in kp) + "</div>")
            h("<div class='nota'>Por qué un modelo simple: se probaron cerca de 20 variantes con satélite, clima, "
              "relieve, vecinas, árbol con poda, PCA y red neuronal, y ninguna redujo el error de forma confiable "
              "frente a este valor típico.</div>")
        with r2, st.container(key="glass_fuentes"):
            titulo("Fuentes")
            fuentes = [("FIRA", "polígonos y rendimientos"), ("Sentinel-2, Landsat y Planet", "índices por parcela"),
                       ("CHIRPS", "lluvia mensual"), ("Temperatura", "máxima y mínima mensual"),
                       ("INEGI", "elevación y pendiente"),
                       ("Mapa", "EOX Sentinel-2 cloudless, Terrain Tiles de AWS y CARTO, sólo como fondo")]
            h("<div class='etiquetas'>" + "".join(f"<div class='etiqueta'>{e(a)} <span>· {e(b)}</span></div>"
                                                  for a, b in fuentes) + "</div>")
        with st.container(key="glass_limites"):
            titulo("Límites", "Lo que esta estimación no puede decir.")
            limites = ["Es el valor típico del municipio: dos parcelas vecinas del mismo municipio reciben la misma cifra.",
                       "Faltan fecha de siembra, variedad, manejo y suelo, que explican buena parte de las diferencias.",
                       "El clima viene en pixeles de ~5.5 km: no distingue parcelas cercanas.",
                       "Algunos rendimientos registrados vienen redondeados.",
                       "El rendimiento no indica calidad maltera ni capacidad de pago.",
                       "Los índices de satélite y el clima son contexto: no son mediciones de campo ni recomendaciones."]
            h("<div class='limites'>" + "".join(f"<div class='limite'>{e(x)}</div>" for x in limites) + "</div>")


    with t5:
        with st.container(key="glass_subir"):
            titulo("Analiza tu propio dataset",
                   "Sube tus parcelas y la app les aplica el mismo procedimiento de T08. Lee qué necesitamos antes.")
            st.markdown(K.REQUISITOS)
            p1, p2 = st.columns([3, 1], vertical_alignment="bottom")
            archivo = p1.file_uploader(f"Sube un .zip o un .csv (máximo {K.MAX_MB} MB)", type=["zip", "csv"],
                                       accept_multiple_files=False, key="carga")
            p2.download_button("Plantilla CSV", K.plantilla_csv(), file_name="plantilla_parcelas.csv",
                               mime="text/csv", on_click="ignore", width="stretch",
                               help="Ejemplo del formato 2 con datos inventados.")
        if archivo is not None:
            contenido = archivo.getvalue()
            huella = hashlib.sha256(contenido).hexdigest()
            guardado = st.session_state.get("carga_resultado")
            if not guardado or guardado[0] != huella:
                try:
                    guardado = (huella, K.revisar(archivo.name, contenido), None)
                except K.Rechazo as ex:
                    guardado = (huella, None, str(ex))
                except Exception:
                    guardado = (huella, None, "No pude leer el archivo; revisa que cumpla el formato de arriba.")
                st.session_state["carga_resultado"] = guardado      # sólo en esta sesión; no se guarda en disco
            _, res, motivo = guardado
            if motivo:
                st.error(f"Archivo rechazado. {motivo}")
            else:
                analizar_subido(res, modelo, satelite)
