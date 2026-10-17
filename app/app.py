"""AgroCebada 2026 · App de estimación de rendimiento (T17).

Ejecuta el mismo procedimiento que T08 (valor típico del municipio con respaldo por grupo de registro y luego global)
con las 138 parcelas con rendimiento y estima las 59 reservadas. Dos vistas:
  - Agricultor: una parcela, su estimación en t/ha, el error observado, su mapa 3D, su verdor, su clima y su ficha PDF.
  - Analista: mapa 3D de las 197, las 59 con verificación y exportación, ficha técnica y comparación de parcelas,
    validación por escenario y municipio, información insuficiente y análisis de un dataset propio (carga segura).

Datos: lee el paquete compacto `datos_app/` (lo arma preparar_datos.py); si no está, las fuentes del repo.
El mapa 3D pone las parcelas sobre el relieve real (Terrain Tiles de AWS) con imagen Sentinel-2 sin nubes (EOX).

Uso (desde esta carpeta):  streamlit run app.py
"""
import hashlib
import html
from pathlib import Path

import altair as alt
import numpy as np
import pandas as pd
import pydeck as pdk
import streamlit as st

import agro_carga as K
import agro_datos as A
import agro_ficha as F

AQUI = Path(__file__).resolve().parent
MODELO_OFICIAL = "media_mun__resp_grupo"          # cambiar aquí si T16 elige la mediana
MODELOS = {"media_mun__resp_grupo": "Media · oficial", "mediana_mun__resp_grupo": "Mediana · PR #23"}
CORTE_TXT = "31 de octubre de 2025"
INDICES = {"NDVI (verdor)": "ndvi_promedio", "EVI": "evi_promedio", "LAI (área foliar)": "lai_promedio"}
MESES = dict(enumerate(["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"], 1))

# Mapa 3D: relieve público (sin clave) e imagen Sentinel-2 sin nubes (sin clave; uso no comercial con atribución).
RELIEVE = "https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png"
SATELITE = "https://tiles.maps.eox.at/wmts/1.0.0/s2cloudless-2021_3857/default/g/{z}/{y}/{x}.jpg"
CREDITOS = ("Imagen: Sentinel-2 cloudless 2021 de EOX IT Services GmbH (s2maps.eu), contiene datos Copernicus Sentinel "
            "modificados, CC BY-NC-SA 4.0 · Relieve: Terrain Tiles, AWS Open Data · Mapa base: CARTO, OpenStreetMap")
AYUDA_MAPA = ("Clic en una parcela para seleccionarla · pasa el ratón para ver su detalle · rueda o pellizco para "
              "acercar (alejar tiene un límite) · arrastra para mover · en 3D, Shift + arrastrar para girar")
TOOLTIP = {"text": "{id} · {municipio}\n{detalle}",
           "style": {"backgroundColor": "rgba(12,20,16,0.92)", "color": "#E7EFE9", "fontSize": "12px",
                     "lineHeight": "1.5", "maxWidth": "330px", "borderRadius": "10px", "padding": "9px 11px",
                     "border": "1px solid rgba(255,255,255,0.14)"}}

ESTILO = """
:root { --vidrio: rgba(13, 21, 17, 0.58); --borde: rgba(255,255,255,0.10); --tenue: #9DB0A5; --acento: #9BE15D; }
.stApp { background:
  radial-gradient(1100px 520px at 0% -10%, rgba(155,225,93,.13), transparent 60%),
  radial-gradient(900px 480px at 100% 0%, rgba(47,224,160,.10), transparent 60%),
  radial-gradient(900px 600px at 50% 115%, rgba(47,224,160,.07), transparent 60%), #0A110E; }
header[data-testid="stHeader"], [data-testid="stDecoration"] { display: none; }
.block-container { padding-top: 1rem; padding-bottom: 2rem; max-width: 1500px; }

/* vidrio */
[class*="st-key-glass"] { background: linear-gradient(180deg, rgba(255,255,255,.035), rgba(255,255,255,.01)), var(--vidrio);
  border: 1px solid var(--borde); border-radius: 18px; padding: 14px 16px;
  box-shadow: 0 14px 34px rgba(0,0,0,.38), inset 0 1px 0 rgba(255,255,255,.06); }
/* el desenfoque va sólo en lo que flota sobre el mapa: en las tarjetas encerraría la pantalla completa */
.st-key-glass_top, .st-key-glass_panel, .st-key-glass_kpis, .st-key-glass_chips, .st-key-glass_filtros,
.st-key-glass_leyenda { backdrop-filter: blur(18px) saturate(150%); -webkit-backdrop-filter: blur(18px) saturate(150%); }

.st-key-glass_top { padding: 10px 16px; }

/* QA: espacio y adaptación de la tarjeta informativa */
.st-key-glass_explica {
    padding: 18px 20px 26px;
}

.st-key-glass_explica .mascota > div:last-child {
    flex: 1;
    min-width: 0;
}

.st-key-glass_explica .nota {
    line-height: 1.55;
    margin-bottom: 4px;
    overflow-wrap: break-word;
}

/* mapa protagonista con paneles flotantes */
.st-key-hero { position: relative; gap: 0; }
.st-key-hero [data-testid="stDeckGlJsonChart"] { border-radius: 22px; overflow: hidden;
  border: 1px solid var(--borde); box-shadow: 0 20px 50px rgba(0,0,0,.45); }
.st-key-glass_panel, .st-key-glass_kpis { position: absolute; top: 16px; left: 16px; width: 350px; z-index: 5; }
.st-key-glass_chips, .st-key-glass_filtros { position: absolute; top: 16px; right: 62px; width: 280px; z-index: 5; }
.st-key-glass_leyenda { position: absolute; bottom: 16px; right: 16px; width: 300px; z-index: 5; padding: 10px 14px; }
@media (max-width: 900px) {
  .st-key-glass_panel, .st-key-glass_kpis, .st-key-glass_chips, .st-key-glass_filtros, .st-key-glass_leyenda {
    position: relative; top: auto; left: auto; right: auto; bottom: auto; width: auto; margin-top: 10px; }
}

/* texto */
.marca { display: flex; align-items: center; gap: 12px; }
.marca-t { font-weight: 800; font-size: 1.15rem; color: #fff; letter-spacing: -.01em; line-height: 1.1; }
.marca-s { font-size: .76rem; color: var(--tenue); }
.eyebrow { font-size: .7rem; letter-spacing: .09em; text-transform: uppercase; color: var(--tenue); font-weight: 600; }
.big { font-size: 3.1rem; font-weight: 800; letter-spacing: -.035em; line-height: 1; color: #fff; margin: 6px 0 2px; }
.big small, .kv small { font-size: .95rem; font-weight: 600; color: var(--tenue); margin-left: 6px; letter-spacing: 0; }
.fila { display: flex; gap: 8px; margin-top: 12px; }
.mini { flex: 1; background: rgba(255,255,255,.05); border: 1px solid rgba(255,255,255,.07); border-radius: 12px;
  padding: 8px 10px; }
.mini span { display: block; font-size: .68rem; color: var(--tenue); }
.mini b { font-size: 1.02rem; color: #fff; font-weight: 700; }
.kpis { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-top: 8px; }
.kv { font-size: 1.45rem !important; letter-spacing: -.02em; }
.nota { font-size: .78rem; color: var(--tenue); margin-top: 10px; line-height: 1.4; }
.aviso { margin-top: 10px; font-size: .78rem; color: #F5D08A; background: rgba(245,181,68,.12);
  border: 1px solid rgba(245,181,68,.30); border-radius: 10px; padding: 8px 10px; line-height: 1.35; }
.chips { display: flex; flex-direction: column; gap: 9px; }
.chip { display: flex; justify-content: space-between; align-items: baseline; gap: 12px; font-size: .78rem;
  color: var(--tenue); }
.chip b { color: #fff; font-size: .95rem; font-weight: 700; }
.ley-bar { height: 8px; border-radius: 6px; background: linear-gradient(90deg, rgb(217,164,65), rgb(140,203,94),
  rgb(47,224,160)); }
.ley-txt { display: flex; justify-content: space-between; font-size: .7rem; color: var(--tenue); margin-top: 4px; }
.ley-nota { font-size: .7rem; color: var(--tenue); margin-top: 4px; }
.tit { font-weight: 700; font-size: 1.02rem; color: #fff; }
.sub { font-size: .8rem; color: var(--tenue); margin: 2px 0 8px; }
.chk { display: inline-flex; gap: 6px; align-items: center; padding: 5px 11px; border-radius: 999px; font-size: .78rem;
  margin: 0 6px 6px 0; }
.chk.ok { background: rgba(47,224,160,.12); color: #7EF0C4; border: 1px solid rgba(47,224,160,.30); }
.chk.mal { background: rgba(255,99,99,.12); color: #FF9C9C; border: 1px solid rgba(255,99,99,.30); }
.creditos { font-size: .66rem; color: #66796e; margin: 8px 4px 16px; }
.encontrada { font-size: .8rem; color: #fff; margin-top: 4px; }
.mascota { display: flex; gap: 14px; align-items: flex-start; }
.mascota .cebi { flex: 0 0 64px; width: 64px; height: 64px; }

/* Cebi animado: llega, parpadea, mece el brote y da saltitos (sólo CSS) */
.cebi svg { width: 100%; height: 100%; overflow: visible; }
.cebi .cebi-todo { transform-box: view-box; transform-origin: 50% 92%; animation: cebi-salto 7s ease-in-out 2.2s infinite; }
.cebi .cebi-ojos { transform-box: fill-box; transform-origin: center; animation: cebi-parpadeo 4.8s ease-in-out 1.2s infinite; }
.cebi .cebi-brote { transform-box: view-box; transform-origin: 50% 30%; animation: cebi-brote 2.8s ease-in-out infinite alternate; }
.cebi .cebi-pie { transform-box: fill-box; transform-origin: center bottom; }
.marca .cebi { animation: cebi-llega .9s cubic-bezier(.2, .9, .3, 1.25) both; }
.mascota .cebi { animation: cebi-camina 1.8s ease-out both; }
.mascota .cebi .cebi-pie-i { animation: cebi-paso .3s ease-in-out 6 alternate; }
.mascota .cebi .cebi-pie-d { animation: cebi-paso .3s ease-in-out .15s 6 alternate; }
.mascota .cebi .cebi-torso { animation: cebi-bamboleo .3s ease-in-out 6 alternate; transform-box: view-box;
  transform-origin: 50% 90%; }
@keyframes cebi-llega { 0% { opacity: 0; transform: translateY(-22px) scale(.4); } 60% { opacity: 1; }
  100% { opacity: 1; transform: none; } }
@keyframes cebi-camina { 0% { opacity: 0; transform: translateX(-70px); } 15% { opacity: 1; }
  100% { opacity: 1; transform: none; } }
@keyframes cebi-paso { from { transform: translateY(0); } to { transform: translateY(-28%); } }
@keyframes cebi-bamboleo { from { transform: rotate(-4deg); } to { transform: rotate(4deg); } }
@keyframes cebi-parpadeo { 0%, 88%, 100% { transform: scaleY(1); } 92% { transform: scaleY(.08); } 96% { transform: scaleY(1); } }
@keyframes cebi-brote { from { transform: rotate(-8deg); } to { transform: rotate(8deg); } }
@keyframes cebi-salto { 0%, 82%, 100% { transform: translateY(0) scale(1, 1); } 85% { transform: translateY(0) scale(1.07, .9); }
  90% { transform: translateY(-12%) scale(.95, 1.06); } 95% { transform: translateY(0) scale(1.05, .94); } }
@media (prefers-reduced-motion: reduce) { .cebi, .cebi * { animation: none !important; } }
.pasos { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin-top: 10px; }
.paso { background: rgba(255,255,255,.04); border: 1px solid rgba(255,255,255,.08); border-radius: 14px; padding: 12px; }
.paso .n { width: 26px; height: 26px; border-radius: 50%; background: rgba(155,225,93,.18); color: var(--acento);
  display: grid; place-items: center; font-weight: 800; font-size: .85rem; }
.paso b { display: block; color: #fff; margin: 8px 0 4px; font-size: .92rem; }
.paso p { margin: 0; font-size: .8rem; color: var(--tenue); line-height: 1.4; }
.etiquetas { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 8px; }
.etiqueta { background: rgba(255,255,255,.05); border: 1px solid rgba(255,255,255,.09); border-radius: 999px;
  padding: 6px 12px; font-size: .78rem; color: #E7EFE9; }
.etiqueta span { color: var(--tenue); }
.limites { display: grid; grid-template-columns: 1fr 1fr; gap: 8px 18px; margin-top: 8px; }
.limite { display: flex; gap: 10px; font-size: .82rem; color: #E7EFE9; line-height: 1.4; }
.limite::before { content: "!"; flex: 0 0 20px; height: 20px; border-radius: 50%; background: rgba(245,181,68,.16);
  color: #F5B544; font-weight: 800; font-size: .72rem; display: grid; place-items: center; margin-top: 1px; }
@media (max-width: 900px) { .pasos { grid-template-columns: 1fr 1fr; } .limites { grid-template-columns: 1fr; } }

/* pestañas tipo píldora */
.stTabs [role="tablist"] { gap: 6px; background: rgba(255,255,255,.04); border: 1px solid var(--borde) !important;
  padding: 6px; border-radius: 14px; width: fit-content; max-width: 100%; overflow-x: auto; box-shadow: none !important; }
.stTabs [role="tab"] { height: auto; padding: 8px 16px !important; border-radius: 10px; border: none !important;
  box-shadow: none !important; }
.stTabs [role="tab"][aria-selected="true"] { background: rgba(155,225,93,.16); }
.stTabs [role="tab"]::after, .stTabs [role="tab"]::before, .stTabs [role="tablist"]::after { display: none !important; }
.stTabs > div { border-bottom: none !important; box-shadow: none !important; }

/* controles */
[data-testid="stWidgetLabel"] p { font-size: .74rem; color: var(--tenue); }
.stApp [data-baseweb="select"] > div { background: rgba(255,255,255,.06); border-color: rgba(255,255,255,.12); }
.stDownloadButton button[kind="primary"] { color: #0A110E; font-weight: 600; }
"""

MASCOTA = (AQUI / "assets" / "cebi.svg").read_text(encoding="utf-8") if (AQUI / "assets" / "cebi.svg").exists() else ""
ICONO = str(AQUI / "assets" / "cebi.png") if (AQUI / "assets" / "cebi.png").exists() else "🌾"
MARCA = """<div class="marca"><div class="cebi" style="width:44px;height:44px;flex:0 0 44px">""" + MASCOTA + """</div>
<div><div class="marca-t">AgroCebada</div><div class="marca-s">Rendimiento de cebada · campaña 2025 ·
información al 31 de octubre de 2025</div></div></div>"""


# ---------------------------------------------------------------- datos (paquete datos_app/ o fuentes del repo)
@st.cache_data(show_spinner="Leyendo parcelas…")
def cargar():
    return A.parcelas()


@st.cache_data
def elevaciones():
    return A.elevaciones()


@st.cache_data(show_spinner="Leyendo series de satélite…")
def series():
    return A.series()


@st.cache_data
def clima():
    return A.clima()


@st.cache_data
def soporte():
    return A.soporte()


@st.cache_data
def oficial(modelo):
    return A.oficial(modelo)


@st.cache_data
def oof(modelo, municipios):
    return A.validacion(modelo, municipios)


predecir, metricas = A.predecir, A.metricas


def vecinas(d, pid, radio=0.06):
    """Parcelas a ~6 km de la elegida (distancia en grados, suficiente para encuadrar el mapa)."""
    r = d.loc[pid]
    return d.index[np.hypot(d.lon_c - r.lon_c, d.lat_c - r.lat_c) < radio]


# ---------------------------------------------------------------- mapa 3D
def color(v, alfa=235):
    return list(A.color_rgb(v)) + [alfa]


def anillo(geom):
    g = max(geom.geoms, key=lambda p: p.area) if geom.geom_type == "MultiPolygon" else geom
    g = g.simplify(0.00003)                      # ~3 m: menos vértices, bordes 3D más limpios
    return [(round(c[0], 6), round(c[1], 6)) for c in g.exterior.coords]


def mapa(d, pred, ids, centro, zoom, resaltar=None, altura=660, escala=600, satelite=True, arriba=False,
         detalle=None, con_relieve=True, clave="mapa", al_clic=None):
    """Parcelas sobre el relieve real con imagen Sentinel-2. En 3D son bloques (altura y color = t/ha); desde arriba
    son polígonos de color con borde, como un mapa de cultivos. El zoom se limita alrededor de la vista inicial y la
    rueda del ratón no hace zoom, para que el scroll mueva la página."""
    E = elevaciones() if con_relieve else None
    relieve = E is not None
    base = 0.0
    if relieve:
        base = float(E[resaltar]) if resaltar in E.index else float(E.reindex(list(ids)).median())
    filas = []
    for pid in ids:
        r = d.loc[pid]
        reservada = r.CONJUNTO == "PREDICCION"
        v = float(pred.prediccion.get(pid) if reservada else r.real)
        sel = pid == resaltar
        # desde arriba el terreno va plano (el relieve no se nota y su brillo taparía la imagen)
        z = round(float(E.get(pid, base)) - base + 3, 1) if (relieve and not arriba) else 2.0
        if arriba:                        # de lejos las parcelas son chicas: bordes más finos para que no sean puntos
            cerca = zoom >= 12
            linea, ancho = (([255, 255, 255, 255], 2.5 if cerca else 1.0) if (reservada or sel)
                            else ([255, 255, 255, 120], 1.0 if cerca else 0.0))
        else:
            linea, ancho = ([255, 255, 255, 235] if (reservada or sel) else [0, 0, 0, 0]), 1.0
        filas.append(dict(id=pid, municipio=r.municipio, tipo="estimación" if reservada else "registrado",
                          detalle=(detalle or {}).get(pid, f"{'Estimación' if reservada else 'Registrado'}: {v:.2f} t/ha"),
                          valor=round(v, 2), poligono=[[x, y, z] for x, y in anillo(r.geometry)],
                          color=[255, 122, 69, 240] if sel else color(v, 205 if arriba else 235),
                          linea=linea, ancho=ancho))
    capas = []
    if relieve or satelite:            # sin relieve (datos subidos) la imagen va sobre un terreno plano
        plano = {"rScaler": 0, "gScaler": 0, "bScaler": 0, "offset": 0}
        real = {"rScaler": 256, "gScaler": 1, "bScaler": 1 / 256, "offset": -32768 - base}
        capas.append(pdk.Layer("TerrainLayer", id="relieve-plano" if arriba else "relieve", elevation_data=RELIEVE,
                               texture=SATELITE if satelite else None, max_zoom=13, color=[44, 56, 50],
                               elevation_decoder=real if (relieve and not arriba) else plano,
                               material=relieve and not arriba))
    capas.append(pdk.Layer("PolygonLayer", filas, id="parcelas", get_polygon="poligono", get_fill_color="color",
                           get_line_color="linea", get_line_width="ancho", line_width_units=pdk.types.String("pixels"),
                           extruded=not arriba, wireframe=not arriba, stroked=arriba, get_elevation="valor",
                           elevation_scale=escala, pickable=True, auto_highlight=True,
                           highlight_color=[255, 236, 140, 240]))          # amarillo claro al pasar el ratón
    vista = pdk.View(type="MapView", controller={"scrollZoom": True, "doubleClickZoom": True, "touchZoom": True,
                                                 "dragRotate": not arriba, "touchRotate": not arriba, "keyboard": True})
    estado = pdk.ViewState(latitude=centro[1], longitude=centro[0], zoom=zoom, min_zoom=zoom - 1.2, max_zoom=18.5,
                           pitch=0 if arriba else 58, bearing=0 if arriba else -18, max_pitch=0 if arriba else 72)
    # La clave sólo cambia con la vista (3D o desde arriba) y el encuadre elegido en los selectores. Un clic en el mapa
    # no la cambia: el mapa no se vuelve a crear, conserva el zoom y sólo se recolorea la parcela elegida (Streamlit,
    # además, atenúa las demás).
    clave = f"{clave}-{'arriba' if arriba else '3d'}"
    st.pydeck_chart(pdk.Deck(layers=capas, views=[vista], map_provider="carto", map_style="dark", tooltip=TOOLTIP,
                             initial_view_state=estado), height=altura, key=clave,
                    on_select=(lambda: al_clic(clave)) if al_clic else "ignore", selection_mode="single-object")


def parcela_clicada(clave):
    """ID de la parcela que se acaba de clicar en el mapa `clave`, o None."""
    try:
        objetos = st.session_state[clave].selection.objects.get("parcelas") or []
        return objetos[0]["id"] if objetos else None
    except (KeyError, AttributeError, TypeError, IndexError):
        return None


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


# ---------------------------------------------------------------- piezas de interfaz
def h(s):
    st.markdown(s, unsafe_allow_html=True)        # sólo HTML propio; los textos de datos pasan por e()


def e(s):
    return html.escape(str(s))


def leyenda():
    """Selector de vista del mapa y escala de color. Devuelve True si se eligió la vista desde arriba."""
    arriba = (st.segmented_control("Vista del mapa", ["3D", "Desde arriba"], key="vista_mapa",
                                   label_visibility="collapsed") or "3D") == "Desde arriba"
    nota = "Color = t/ha · borde grueso = por estimar" if arriba else "Altura y color = t/ha · borde blanco = por estimar"
    h("<div class='eyebrow' style='margin-top:4px'>Rendimiento</div><div class='ley-bar' style='margin-top:6px'></div>"
      "<div class='ley-txt'><span>2.0</span><span>3.8</span><span>5.6 t/ha</span></div>"
      f"<div class='ley-nota'>{nota}</div>")
    return arriba


def chips(items):
    h("<div class='chips'>" + "".join(f"<div class='chip'><span>{e(k)}</span><b>{e(v)}</b></div>"
                                      for k, v in items) + "</div>")


def titulo(t, sub=""):
    h(f"<div class='tit'>{e(t)}</div>" + (f"<div class='sub'>{e(sub)}</div>" if sub else ""))


def _grafica(ch, alto):
    return ch.properties(height=alto, background="transparent").configure_view(strokeWidth=0).configure_axis(
        gridColor="rgba(255,255,255,0.07)", domainColor="rgba(255,255,255,0.18)", tickColor="rgba(255,255,255,0.18)")


def curva_indice(s, pid, col, nombre, alto=240):
    x = s[(s.ID_POLIGONO == pid) & s[col].notna()][["fecha", "sensor", col]].sort_values("fecha")
    if x.empty:
        st.info("No hay capturas despejadas de este índice para la parcela.")
        return
    base = alt.Chart(x).encode(
        x=alt.X("fecha:T", title=None, axis=alt.Axis(format="%d/%m")),
        y=alt.Y(f"{col}:Q", title=nombre),
        color=alt.Color("sensor:N", title=None, scale=alt.Scale(domain=["Planet", "Sentinel-2"],
                                                                range=["#9BE15D", "#5ED1E8"]),
                        legend=alt.Legend(orient="top")),
        tooltip=[alt.Tooltip("fecha:T", format="%d/%m/%Y"), "sensor", alt.Tooltip(f"{col}:Q", format=".2f")])
    st.altair_chart(_grafica(base.mark_line(opacity=0.55, strokeWidth=2) + base.mark_circle(size=34, opacity=0.95),
                             alto), width="stretch")


def curva_clima(c, pid, alto=240):
    x = c[c.id_parcela == pid]
    if x.empty:
        return
    orden = [MESES[m] for m in range(3, 11)]
    x = x.assign(mes=pd.to_datetime(x.periodo + "-01").dt.month.map(MESES))
    eje = alt.X("mes:O", sort=orden, title=None, axis=alt.Axis(labelAngle=0))
    lluvia = alt.Chart(x).mark_bar(color="#5ED1E8", opacity=0.45, cornerRadiusTopLeft=4, cornerRadiusTopRight=4).encode(
        x=eje, y=alt.Y("PREC:Q", title="lluvia (mm/mes)"), tooltip=["mes", alt.Tooltip("PREC:Q", format=".0f")])
    temp = alt.Chart(x.melt(id_vars=["mes"], value_vars=["Tmax", "Tmin"], var_name="variable", value_name="°C")).mark_line(
        point=True, strokeWidth=2).encode(
        x=eje, y=alt.Y("°C:Q", title="temperatura (°C)"),
        color=alt.Color("variable:N", title=None, scale=alt.Scale(domain=["Tmax", "Tmin"], range=["#F5B544", "#7FB2FF"]),
                        legend=alt.Legend(orient="top")))
    st.altair_chart(_grafica(alt.layer(lluvia, temp).resolve_scale(y="independent"), alto), width="stretch")


def avisos_de(pred, sop):
    out = {}
    for pid, r in pred.iterrows():
        a = []
        if r.n_municipio == 1:
            a.append("se basa en una sola parcela con cosecha de su municipio")
        if r.fuente != "municipio":
            a.append("su municipio no tiene parcelas con cosecha: se usó el respaldo")
        if sop is not None and pid in sop.index and sop.loc[pid, "etiquetadas_en_misma_celda"] == 0:
            a.append("está en una zona de lluvia sin parcelas con cosecha registrada")
        out[pid] = "; ".join(a)
    return pd.Series(out)


def resumen_parcela(pid):
    r, out = d.loc[pid], []
    out.append(("Área", f"{r.AREA_HA:.2f} ha"))
    E = elevaciones()
    if E is not None and pid in E.index:
        out.append(("Altitud", f"{E[pid]:,.0f} m"))
    if C is not None:
        x = C[C.id_parcela == pid]
        if len(x):
            out.append(("Lluvia mar–oct", f"{x.PREC.sum():,.0f} mm"))
    s = S[(S.ID_POLIGONO == pid) & S.ndvi_promedio.notna()]
    if len(s):
        top = s.sort_values("ndvi_promedio").iloc[-1]
        out.append(("Verdor máximo", f"{top.ndvi_promedio:.2f} · {MESES[top.fecha.month]}"))
    out.append(("Corte de información", "31 oct 2025"))
    return out


def detalles(d, pred, oof_parcela):
    """Texto del recuadro que aparece al pasar el ratón por cada parcela."""
    out = {}
    for pid, r in d.iterrows():
        if r.CONJUNTO == "PREDICCION" and pid in pred.index:
            p = pred.loc[pid]
            lin = [f"Estimación: {p.prediccion:.2f} t/ha" +
                   (f" (error típico ± {p.error_tipico:.2f})" if pd.notna(p.get("error_tipico")) else ""),
                   f"Área: {r.AREA_HA:.2f} ha · producción {p.prediccion * r.AREA_HA:.1f} t",
                   (f"Base: {int(p.n_municipio)} parcelas con cosecha de {r.municipio}" if p.fuente == "municipio"
                    else f"Base: respaldo por {p.fuente} (su municipio no tiene parcelas con cosecha)")]
            if p.get("aviso"):
                lin.append(f"Aviso: {p.aviso}")
        else:
            lin = [f"Rendimiento registrado: {r.real:.2f} t/ha"]
            if pid in oof_parcela.index:
                lin.append(f"Lo que estimó el método sin conocerla: {oof_parcela[pid]:.2f} t/ha")
            lin.append(f"Área: {r.AREA_HA:.2f} ha")
        out[pid] = "\n".join(lin)
    return out


def nota_de(pid):
    r = d.loc[pid]
    if r.CONJUNTO != "PREDICCION":
        return ("Esta parcela ya tiene su cosecha registrada. Sirve para comprobar el método: se estimó como si no se "
                "conociera y se comparó.")
    p, n = pred.loc[pid], int(pred.loc[pid, "n_municipio"])
    origen = (f"la única parcela de {r.municipio} con cosecha registrada" if n == 1 else
              f"las {n} parcelas de {r.municipio} con cosecha registrada")
    nota = f"Es el rendimiento típico de {origen} en 2025."
    if pd.notna(p.error_tipico) and r.municipio in cob_mun.index:
        nota += (f" Al probarlo con parcelas conocidas, {cob_mun[r.municipio] * 10:.0f} de cada 10 quedaron dentro "
                 f"de ± {p.error_tipico:.2f} t/ha.")
    return nota


@st.cache_data(show_spinner=False)
def ficha_bytes(pid, modelo):
    """PDF de una página con la parcela, su cifra, su mapa, su verdor y su clima (se arma al hacer clic)."""
    r = d.loc[pid]
    est = r.CONJUNTO == "PREDICCION"
    p = pred.loc[pid] if est else None
    info = dict(id=pid, municipio=r.municipio, estado=r.Estado, grupo=r.grupo_registro, area=r.AREA_HA,
                tipo="estimacion" if est else "registrado", valor=float(p.prediccion) if est else float(r.real),
                produccion=float(p.prediccion) * r.AREA_HA if est else None,
                error=float(p.error_tipico) if est and pd.notna(p.error_tipico) else None,
                oof=float(oof_parcela[pid]) if (not est and pid in oof_parcela.index) else None,
                nota=nota_de(pid), aviso=p.aviso if est else "", corte=CORTE_TXT)
    pol = [dict(coords=anillo(d.loc[i].geometry),
                valor=float(pred.prediccion[i]) if d.loc[i, "CONJUNTO"] == "PREDICCION" else float(d.loc[i, "real"]),
                sel=i == pid, reservada=d.loc[i, "CONJUNTO"] == "PREDICCION") for i in vecinas(d, pid)]
    c = None
    if C is not None:
        c = C[C.id_parcela == pid].assign(mes=lambda x: x.periodo.str[5:].astype(int)).sort_values("mes")
    icono = AQUI / "assets" / "cebi.png"
    return F.ficha_pdf(info, pol, S[S.ID_POLIGONO == pid], c, str(icono) if icono.exists() else None)


def boton_ficha(pid, clave):
    st.download_button("Descargar ficha (PDF)", data=lambda: ficha_bytes(pid, modelo),
                       file_name=f"ficha_{pid}.pdf", mime="application/pdf", on_click="ignore", key=clave,
                       type="primary", width="stretch", help="Una página con la cifra, el mapa, el verdor y el clima.")


def zoom_para(gdf):
    x0, y0, x1, y1 = gdf.total_bounds
    lado = max(x1 - x0, (y1 - y0) * 1.3, 0.01)
    return float(np.clip(np.log2(560 / lado), 5, 14))       # deja ~50 % de margen en un mapa de ~1200 px


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
    st.error(A.FALTA_DATASET)
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
                partes.append(f"<div class='nota'>{e(nota_de(pid))}</div>")
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
                partes.append(f"<div class='nota'>{e(nota_de(pid))}</div>")
                h("".join(partes))
            boton_ficha(pid, "ficha_agricultor")
        with st.container(key="glass_leyenda"):
            arriba = leyenda()
        rc = d.loc[encuadre]
        mapa(d, pred, vecinas(d, encuadre), (rc.lon_c - 0.018, rc.lat_c), 13.2, resaltar=pid, altura=700,
             escala=30, satelite=satelite, arriba=arriba, detalle=DET, clave=f"mapa-agri-{encuadre}",
             al_clic=clic_agricultor)
        with st.container(key="glass_chips"):
            chips(resumen_parcela(pid))
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
                boton_ficha(pid, "ficha_analista")
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
                    st.altair_chart(_grafica(base.mark_line(strokeWidth=2) + base.mark_circle(size=30), 260),
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
                st.altair_chart(_grafica(diag + puntos, 300), width="stretch")
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
