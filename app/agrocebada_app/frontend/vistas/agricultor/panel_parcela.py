"""Panel «Tu parcela»: selectores, cifra estimada (o registrada) con su desglose, y botón de la ficha."""
import streamlit as st

from agrocebada_app.backend.dominio.confianza import confianza_parcela
from agrocebada_app.backend.dominio.desglose import desglose
from agrocebada_app.backend.dominio.notas import nota_de
from agrocebada_app.frontend.componentes.descargas.boton_ficha import boton_ficha
from agrocebada_app.frontend.componentes.paneles.explicacion import explicacion_corta_html
from agrocebada_app.frontend.tema.html import e, h
from agrocebada_app.frontend.vistas.agricultor.seleccion import primera_reservada

# mismos íconos que la ficha PDF: el nivel de confianza se lee con palabra e ícono, sin depender del color
_ICONO = {"alta": "✔", "media": "▲", "baja": "⚠"}


def _caja(corto, valor, largo):
    return f"<div class='mini' title='{e(largo)}'><span>{e(corto)}</span><b>{e(valor)}</b></div>"


def _ecuacion(x):
    """Base de la región, lo que cambia por el municipio y la estimación, en tres recuadros: 4.34 − 1.84 = 2.50. El
    nombre completo de cada uno sale al pasar el ratón."""
    filas = x["filas"]
    cifra = lambda t: t.replace(" t/ha", "").lstrip("+-")           # sin unidad (va en la cifra grande) y sin signo
    partes = [_caja("Región", cifra(filas[0][1]), f"{filas[0][0]}: {filas[0][1]}")]
    if len(filas) == 3:                                                # sin esta fila cuando no hay ajuste (valor global)
        corto = "Tu municipio" if x["fuente"] == "municipio" else "Tu grupo"
        partes += [f"<span class='op'>{'−' if x['ajuste'] < 0 else '+'}</span>",
                   _caja(corto, cifra(filas[1][1]), f"{filas[1][0]}: {filas[1][1]}")]
    partes += ["<span class='op'>=</span>", _caja("Estimación", cifra(filas[-1][1]), f"{filas[-1][0]}: {filas[-1][1]}")]
    return "<div class='fila eq'>" + "".join(partes) + "</div>"


def _mas(x):
    """Plegable «Cómo leer esta estimación»: el desglose en una frase, lo que el método no ve y la explicación breve."""
    return ("<details class='mas'><summary>Cómo leer esta estimación</summary>"
            f"<div class='nota'>{e(x['frase'])}</div>"
            f"<div class='nota'>Lo que el método no ve: {e(x['no_ve'])}. {e(x['no_entra'])}</div>"
            f"{explicacion_corta_html()}</details>")


def _estimada(ctx, pid, r):
    """Parcela por estimar: cifra, producción, confianza con su motivo, ecuación, rango, aviso y el plegable."""
    p = ctx.pred.loc[pid]
    x = desglose(ctx.d, ctx.pred, ctx.modelo, ctx.conf, pid)
    partes = [f"<div class='eyebrow' style='margin-top:6px'>Rendimiento estimado</div>"
              f"<div class='big'>{p.prediccion:.2f}<small>t/ha</small></div><div class='fila'>"
              f"<div class='mini'><span>Producción estimada</span><b>{p.prediccion * r.AREA_HA:.1f} t</b></div>"
              f"<div class='mini'><span>Confianza</span><b>{_ICONO[x['nivel']]} {e(x['nivel'].capitalize())}</b></div>"
              f"</div>", _ecuacion(x), f"<div class='nota'>{e(x['motivo'])}</div>", f"<div class='nota'>{e(x['rango'])}</div>"]
    if p.aviso:
        partes.append(f"<div class='aviso'>Tómalo con más cuidado: {e(p.aviso)}.</div>")
    partes.append(_mas(x))
    return "".join(partes)


def _registrada(ctx, pid, r):
    """Parcela con cosecha registrada: su cifra y lo que habría estimado el método sin conocerla."""
    partes = [f"<div class='eyebrow' style='margin-top:6px'>Rendimiento registrado</div>"
              f"<div class='big'>{r.real:.2f}<small>t/ha</small></div>"]
    if pid in ctx.oof_parcela.index:
        partes.append(f"<div class='fila'><div class='mini'><span>Lo que estimó el método sin conocerla</span>"
                      f"<b>{ctx.oof_parcela[pid]:.2f} t/ha</b></div><div class='mini'><span>Diferencia</span>"
                      f"<b>{ctx.oof_parcela[pid] - r.real:+.2f} t/ha</b></div></div>")
    partes.append(f"<div class='nota'>{e(nota_de(ctx.d, ctx.pred, ctx.cob_mun, pid))}</div>")
    return "".join(partes)


def panel_parcela(ctx):
    """Dibuja el panel y devuelve (parcela elegida, parcela en la que se centra el mapa)."""
    d = ctx.d
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
        h(_estimada(ctx, pid, r) if r.CONJUNTO == "PREDICCION" else _registrada(ctx, pid, r))
        confianza = (confianza_parcela(ctx.conf, r.municipio, ctx.pred.loc[pid, "fuente"])
                     if r.CONJUNTO == "PREDICCION" else None)
        boton_ficha(pid, "ficha_agricultor", ctx.modelo, ctx.FICHA, confianza=confianza)
    return pid, encuadre
