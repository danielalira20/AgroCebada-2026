"""Cebi flotante: preguntas guiadas y respuestas con datos, con historial por parcela y sesión."""
import streamlit as st

from agrocebada_app.backend.dominio.respuestas import respuestas, saludo
from agrocebada_app.frontend.estado.cache import clima_normal
from agrocebada_app.frontend.tema.estilos import MASCOTA
from agrocebada_app.frontend.tema.html import e, h


def _etiqueta(pregunta):
    """Accesos breves; la pregunta original sigue en la ayuda y en la conversación."""
    etiquetas = {
        "¿Por qué mi vecino tiene el mismo número?": "Mis vecinos",
        "¿Qué tanto puedo confiar?": "La confianza",
        "¿Me alcanza para mis costos?": "Mis costos",
        "¿Cómo estuvo el clima este año en mi zona?": "El clima",
        "¿Qué haría más precisa mi cifra?": "Más precisión",
        "¿Cómo le fue a mi parcela frente a las de mi municipio?": "Mi cosecha",
        "¿Entre qué valores quedaron las de mi municipio?": "Mi municipio",
        "¿Qué no sabe la app de mi parcela?": "Qué falta saber",
    }
    if pregunta.startswith("¿Por qué mi parcela tiene "):
        return "Mi estimación"
    return etiquetas.get(pregunta, pregunta)


_COMPOSITOR = """<div class='cebi-compositor'>
<div class='cebi-escritura'>
<input type='text' placeholder='Escribe tu mensaje…' aria-label='Mensaje para Cebi, próximamente'
       aria-describedby='cebi-aviso-maqueta' disabled>
<button type='button' class='cebi-microfono' aria-label='Usar micrófono, próximamente' title='Voz, próximamente' disabled>
<svg viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='1.7' stroke-linecap='round' aria-hidden='true'>
<rect x='9' y='3' width='6' height='12' rx='3'/><path d='M5 11v1a7 7 0 0 0 14 0v-1M12 19v3m-3 0h6'/></svg></button>
<button type='button' class='cebi-enviar' aria-label='Enviar mensaje, próximamente' title='Mensajes, próximamente' disabled>
<svg viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='1.8' stroke-linecap='round' stroke-linejoin='round' aria-hidden='true'>
<path d='m7 11 5-5 5 5M12 6v12'/></svg></button>
</div><div class='cebi-proximamente' id='cebi-aviso-maqueta'>Texto y voz, próximamente</div></div>"""


def _preguntar(clave, indice):
    hechas = st.session_state.setdefault(clave, [])
    if indice in hechas:
        hechas.remove(indice)
    hechas.append(indice)


def _reiniciar(clave):
    st.session_state[clave] = []


@st.fragment
def _platica(ctx, pid):
    lista = respuestas(ctx.d, ctx.pred, ctx.modelo, ctx.conf, pid, oof=ctx.oof_parcela,
                       precio=st.session_state.get("calc_precio"), costo=st.session_state.get("calc_costo"),
                       area=st.session_state.get(f"calc_area_{pid}"), clima=ctx.C, normal=clima_normal())
    clave = f"cebi_{pid}"
    hechas = st.session_state.setdefault(clave, [])
    with st.container(key="cebi_chat"):
        h(f"<div class='cebi-cabecera'><div class='cebi' aria-hidden='true'>{MASCOTA}</div>"
          f"<div><strong>Cebi<span class='cebi-hojita' aria-hidden='true'>✦</span></strong><span>Con los datos de tu parcela</span></div>"
          f"<span class='cebi-parcela'>Parcela {e(pid)}</span></div>")
        with st.container(height=220 if hechas else 150, border=False, autoscroll=True, key="cebi_mensajes"):
            mensajes = [f"<div class='cebi-respuesta'>{e(saludo(ctx.d, ctx.pred, ctx.modelo, ctx.conf, pid))}</div>"]
            for indice in hechas[-4:]:
                pregunta, respuesta = lista[indice]
                mensajes.extend((f"<div class='cebi-pregunta'>{e(pregunta)}</div>",
                                 f"<div class='cebi-respuesta'>{e(respuesta)}</div>"))
            h("<div class='cebi-conversacion' role='log' aria-label='Conversación con Cebi' aria-live='polite'>"
              + "".join(mensajes) + "</div>")
        h("<div class='cebi-sugerencias'><span>Explora tu parcela</span><span>Elige una pregunta ↗</span></div>")
        with st.container(key="cebi_preguntas"):
            columnas = st.columns(3, gap="small")
            for indice, (pregunta, _) in enumerate(lista):
                columnas[indice % 3].button(_etiqueta(pregunta), help=pregunta, key=f"{clave}_{indice}", width="stretch",
                                            wrap=True, on_click=_preguntar, args=(clave, indice))
        h(_COMPOSITOR)
        with st.container(horizontal=True, horizontal_alignment="right"):
            st.button("Empezar de nuevo", key=f"{clave}_borrar", type="tertiary", disabled=not hechas,
                      on_click=_reiniciar, args=(clave,), width="content", wrap=True)


def pregunta_cebi(ctx, pid):
    """Acceso persistente abajo a la derecha y conversación en un popover nativo."""
    with st.container(key="cebi_launcher"):
        h(f"<div class='cebi-acceso' aria-hidden='true'><span>¿Te ayudo?</span>"
          f"<div class='cebi'>{MASCOTA}</div></div>")
        with st.popover("Pregúntale a Cebi", key="cebi_popover", width=72):
            _platica(ctx, pid)
