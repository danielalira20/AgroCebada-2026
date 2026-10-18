"""Panel «Tu parcela»: selectores, cifra estimada (o registrada), nota y botón de la ficha."""
import pandas as pd
import streamlit as st

from agrocebada_app.backend.dominio.notas import nota_de
from agrocebada_app.frontend.componentes.descargas.boton_ficha import boton_ficha
from agrocebada_app.frontend.tema.html import e, h
from agrocebada_app.frontend.vistas.agricultor.seleccion import primera_reservada


def panel_parcela(ctx):
    """Dibuja el panel y devuelve (parcela elegida, parcela en la que se centra el mapa)."""
    d = ctx.d
    modelo = ctx.modelo
    pred = ctx.pred
    cob_mun = ctx.cob_mun
    oof_parcela = ctx.oof_parcela
    FICHA = ctx.FICHA
    with st.container(key="glass_panel"):
        h("<div class='eyebrow'>Tu parcela</div>")
        st.session_state.setdefault("agri_muni", "Chignahuapan")
        munis = sorted(d.municipio.unique())

        def otro_municipio():
            st.session_state["agri_parcela"] = primera_reservada(d, st.session_state.agri_muni)
            st.session_state["encuadre_agri"] = st.session_state["agri_parcela"]

        muni = st.selectbox("Municipio", munis, key="agri_muni", on_change=otro_municipio)
        ids = sorted(d.index[d.municipio == muni])
        if st.session_state.get("agri_parcela") not in ids:
            st.session_state["agri_parcela"] = primera_reservada(d, muni)
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
    return pid, encuadre
