"""Mapa 3D (o desde arriba) de las parcelas sobre el relieve real con imagen Sentinel-2."""
import json

import pydeck as pdk
import streamlit as st

from agrocebada_app.backend.dominio.geometria import anillo
from agrocebada_app.backend.dominio.confianza import confianza_de_parcelas
from agrocebada_app.config import RELIEVE, SATELITE, TOOLTIP
from agrocebada_app.frontend.componentes.mapa.colores import color, color_confianza
from agrocebada_app.frontend.estado.cache import elevaciones
from agrocebada_app.frontend.tema.paleta import color as color_tema


class _DeckCompacto(pdk.Deck):
    """Deck que manda su JSON sin sangrías ni espacios (pydeck lo sangra: ~2.8 veces más grande, y se reenvía en
    cada recarga). Lo que se dibuja no cambia."""

    def to_json(self):
        return json.dumps(json.loads(super().to_json()), separators=(",", ":"))


def mapa(d, pred, ids, centro, zoom, resaltar=None, altura=660, escala=600, satelite=True, arriba=False,
         detalle=None, con_relieve=True, clave="mapa", al_clic=None, modo_color="Rendimiento", conf=None):
    """Parcelas sobre el relieve real con imagen Sentinel-2. En 3D son bloques (altura y color = t/ha); desde arriba
    son polígonos de color con borde, como un mapa de cultivos. El zoom se limita alrededor de la vista inicial y la
    rueda del ratón no hace zoom, para que el scroll mueva la página."""
    E = elevaciones() if con_relieve else None
    relieve = E is not None
    base = 0.0
    if relieve:
        base = float(E[resaltar]) if resaltar in E.index else float(E.reindex(list(ids)).median())

    niveles_confianza = None
    if modo_color == "Confianza" and conf is not None:
        niveles_confianza = confianza_de_parcelas(pred, conf)["nivel"]

    filas = []
    for pid in ids:
        r = d.loc[pid]
        reservada = r.CONJUNTO == "PREDICCION"
        v = float(pred.prediccion.get(pid) if reservada else r.real)
        sel = pid == resaltar
        # desde arriba el terreno va plano (el relieve no se nota y su brillo taparía la imagen)
        z = round(float(E.get(pid, base)) - base + 3, 1) if (relieve and not arriba) else 2.0
        if sel:
            linea, ancho = [255, 255, 255, 255], 4.0
        elif arriba:
            linea, ancho = (
                ([255, 255, 255, 110], 0.7)
                if reservada
                else ([255, 255, 255, 70], 0.5)
            )
        else:
            linea, ancho = (
                [255, 255, 255, 235] if reservada else [0, 0, 0, 0]
            ), 1.0
        filas.append(dict(id=pid, municipio=r.municipio, tipo="estimación" if reservada else "registrado",
                          detalle=(detalle or {}).get(pid, f"{'Estimación' if reservada else 'Registrado'}: {v:.2f} t/ha"),
                          valor=round(v, 2), poligono=[[x, y, z] for x, y in anillo(r.geometry)],
                          color=(
                                color_confianza(niveles_confianza.get(pid))
                                if niveles_confianza is not None
                                else color(v, 205 if arriba else 235)
                            ),
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
    st.pydeck_chart(_DeckCompacto(layers=capas, views=[vista], map_provider="carto", map_style=color_tema("light", "dark"), tooltip=TOOLTIP,
                             initial_view_state=estado), height=altura, key=clave,
                    on_select=(lambda: al_clic(clave)) if al_clic else "ignore", selection_mode="single-object")
