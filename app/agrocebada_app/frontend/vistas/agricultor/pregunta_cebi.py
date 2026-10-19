"""Cebi flotante: preguntas guiadas, texto libre y voz, con historial por parcela y sesión.

Cebi elige, no redacta. Lo que se escribe o se dicta pasa por el enrutador, que lo empareja con una de las
respuestas que `respuestas.py` arma del dato; si no reconoce la pregunta lo dice en vez de inventar. Por eso no hay
modelo de lenguaje: uno que redacta podría afirmar lo que el método no hace, como que el clima mueve la estimación.
"""
import streamlit as st

from agrocebada_app.backend.dominio import transcribir as voz
from agrocebada_app.backend.dominio.enrutador import enrutar, no_entendi
from agrocebada_app.backend.dominio.respuestas import respuestas, saludo
from agrocebada_app.frontend.estado.cache import clima_normal
from agrocebada_app.frontend.tema.estilos import MASCOTA
from agrocebada_app.frontend.tema.html import e, h

TURNOS = 4          # cuántos intercambios se conservan a la vista


def _etiqueta(pregunta):
    """Accesos breves; la pregunta original sigue en la ayuda y en la conversación."""
    etiquetas = {
        "¿Por qué mi vecino tiene el mismo número?": "Mis vecinos",
        "¿Qué tanto puedo confiar?": "La confianza",
        "¿Me alcanza para mis costos?": "Mis costos",
        "¿Cómo estuvo el clima este año en mi zona?": "El clima",
        "¿Qué haría más precisa mi cifra?": "Más precisión",
        "¿Cómo le fue a mi parcela frente a las de mi municipio?": "Cómo me fue",
        "¿Cuántas toneladas me van a salir?": "Mi total",
        "¿Cuántas toneladas saqué en total?": "Mi total",
        "¿De cuánto puede fallar mi número?": "El margen",
        "¿Cómo se vio mi parcela desde el satélite?": "El satélite",
        "¿Entre qué valores quedaron las de mi municipio?": "Mi municipio",
        "¿Qué no sabe la app de mi parcela?": "Qué falta saber",
    }
    if pregunta.startswith("¿Por qué mi parcela tiene "):
        return "Mi estimación"
    return etiquetas.get(pregunta, pregunta)


def _preguntar(clave, indice):
    """Un botón: se guarda el índice, igual que antes, y si se repite se mueve al final."""
    hechas = st.session_state.setdefault(clave, [])
    if indice in hechas:
        hechas.remove(indice)
    hechas.append(indice)


def _decir(clave, texto, preguntas):
    """Texto escrito o dictado: se enruta a una respuesta conocida, o se admite que no se entendió."""
    st.session_state.setdefault(clave, []).append(("libre", str(texto).strip(), enrutar(texto, preguntas)))


def _reiniciar(clave):
    st.session_state[clave] = []


def _burbujas(turnos, lista):
    """Las burbujas de los últimos turnos. Un turno es el índice de un botón o una pregunta escrita."""
    mensajes = []
    for turno in turnos:
        if isinstance(turno, tuple):
            _, texto, indice = turno
            respuesta = lista[indice][1] if indice is not None else no_entendi(lista)
            pregunta = texto
        else:
            pregunta, respuesta = lista[turno]
        mensajes.append(f"<div class='cebi-pregunta'>{e(pregunta)}</div>")
        mensajes.append(f"<div class='cebi-respuesta'>{e(respuesta)}</div>")
    return mensajes


def _escuchar(clave, pid, lista):
    """Nota de voz: se graba aquí y se transcribe en el equipo de la app, para que funcione igual en cualquier
    teléfono. El micrófono va junto al campo de escribir, no escondido: es la otra forma de preguntar, no un extra.

    Si este equipo no puede transcribir no se dibuja el micrófono, para no ofrecer un botón que no lleva a nada."""
    if not voz.disponible():
        return
    audio = st.audio_input("Graba tu pregunta", key=f"{clave}_voz", label_visibility="collapsed")
    if audio is None:
        return
    huella = (pid, audio.size)
    if st.session_state.get(f"{clave}_voz_hecha") == huella:
        return
    st.session_state[f"{clave}_voz_hecha"] = huella
    with st.spinner("Escuchando tu pregunta…"):
        try:
            texto = voz.transcribir(audio.getvalue())
        except RuntimeError as ex:
            st.warning(str(ex))
            return
    if not texto:
        st.warning("No alcancé a entender la grabación. Intenta de nuevo, más cerca del micrófono.")
        return
    _decir(clave, texto, lista)
    st.rerun()


@st.fragment
def _platica(ctx, pid):
    lista = respuestas(ctx.d, ctx.pred, ctx.modelo, ctx.conf, pid, oof=ctx.oof_parcela,
                       precio=st.session_state.get("calc_precio"), costo=st.session_state.get("calc_costo"),
                       area=st.session_state.get(f"calc_area_{pid}"), clima=ctx.C, normal=clima_normal(),
                       series=ctx.S)
    clave = f"cebi_{pid}"
    hechas = st.session_state.setdefault(clave, [])
    with st.container(key="cebi_chat"):
        h(f"<div class='cebi-cabecera'><div class='cebi' aria-hidden='true'>{MASCOTA}</div>"
          f"<div><strong>Cebi<span class='cebi-hojita' aria-hidden='true'>✦</span></strong><span>Con los datos de tu parcela</span></div>"
          f"<span class='cebi-parcela'>Parcela {e(pid)}</span></div>")
        with st.container(height=220 if hechas else 150, border=False, autoscroll=True, key="cebi_mensajes"):
            mensajes = [f"<div class='cebi-respuesta'>{e(saludo(ctx.d, ctx.pred, ctx.modelo, ctx.conf, pid))}</div>"]
            mensajes.extend(_burbujas(hechas[-TURNOS:], lista))
            h("<div class='cebi-conversacion' role='log' aria-label='Conversación con Cebi' aria-live='polite'>"
              + "".join(mensajes) + "</div>")
        # Antes de la primera pregunta los botones invitan a explorar en rejilla; después se encogen a una fila que
        # se desliza, para dejarle la pantalla a la conversación. El cambio es sólo de clase: si aquí cambiara la
        # llave del contenedor o el número de columnas, Streamlit rehace el bloque y el popover se cierra solo.
        h(f"<div class='cebi-sugerencias{' cebi-fila' if hechas else ''}'>"
          f"<span>{'Más preguntas' if hechas else 'Explora tu parcela'}</span></div>")
        with st.container(key="cebi_preguntas"):
            columnas = st.columns(len(lista), gap="small")
            for indice, (pregunta, _) in enumerate(lista):
                columnas[indice].button(_etiqueta(pregunta), help=pregunta, key=f"{clave}_{indice}", width="stretch",
                                        wrap=True, on_click=_preguntar, args=(clave, indice))
        with st.container(horizontal=True, vertical_alignment="center", key="cebi_compositor"):
            escrito = st.chat_input("Escribe tu pregunta…", key=f"{clave}_texto")
            _escuchar(clave, pid, lista)
        if escrito:
            _decir(clave, escrito, lista)
            st.rerun()
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
