"""Cebi flotante: preguntas guiadas, texto libre y voz, con historial por parcela y sesión.

Cebi elige, no redacta. Lo que se escribe o se dicta pasa por el enrutador, que lo empareja con una de las
respuestas que `respuestas.py` arma del dato; si no reconoce la pregunta lo dice en vez de inventar. Por eso no hay
modelo de lenguaje: uno que redacta podría afirmar lo que el método no hace, como que el clima mueve la estimación.
"""
import streamlit as st

from agrocebada_app.backend.dominio import transcribir as voz
from agrocebada_app.backend.dominio.enrutador import enrutar, no_entendi
from agrocebada_app.backend.dominio.respuestas import respuestas, respuestas_cuenta, saludo
from agrocebada_app.frontend.estado.cache import clima_normal
from agrocebada_app.frontend.tema.estilos import MASCOTA
from agrocebada_app.frontend.tema.html import e, h

TURNOS = 4          # cuántos intercambios se conservan a la vista
TEMA_PARCELA, TEMA_CUENTA = "parcela", "cuenta"     # de dónde salen las preguntas que se ofrecen


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
        "¿Cómo me fue en los años que anoté?": "Mi libreta",
        "¿Cuánto necesito sacar para no perder?": "Mi equilibrio",
        "¿Qué pasa si el año sale bajo o alto?": "Año bajo o alto",
        "¿Qué hago si no me alcanza?": "Si no alcanza",
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


def _guardado(indice, de_cuenta, total):
    """Cómo se guarda un índice de la lista completa [parcela + cuenta]. Las de «Mi cuenta» van contadas desde el
    final (negativas): siempre son tres, así el historial no se corre si a la parcela le aparece una pregunta más."""
    return indice if indice is None or indice < total - de_cuenta else indice - total


def _decir(clave, texto, preguntas, de_cuenta=0):
    """Texto escrito o dictado: se enruta a una respuesta conocida, o se admite que no se entendió."""
    indice = enrutar(texto, preguntas)
    st.session_state.setdefault(clave, []).append(
        ("libre", str(texto).strip(), _guardado(indice, de_cuenta, len(preguntas))))


def _elegir_tema(clave, tema):
    st.session_state[f"{clave}_tema"] = tema


def _reiniciar(clave):
    st.session_state[clave] = []
    st.session_state.pop(f"{clave}_tema", None)


def _cerrar():
    """La ✕ del encabezado. Streamlit no deja cerrar un popover desde Python, así que se le cambia la llave y el
    popover vuelve a nacer, cerrado. La conversación no se pierde: vive en la sesión, no en el popover."""
    st.session_state["cebi_cerrar"] = True


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


def _escuchar(clave, pid, lista, de_cuenta=0):
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
    _decir(clave, texto, lista, de_cuenta)
    st.rerun()


@st.fragment
def _platica(ctx, pid):
    if st.session_state.pop("cebi_cerrar", False):
        st.session_state["cebi_vuelta"] = st.session_state.get("cebi_vuelta", 0) + 1
        st.rerun(scope="app")        # la llave vive fuera del fragmento, así que hay que rehacer la página entera
    precio, costo = st.session_state.get("calc_precio"), st.session_state.get("calc_costo")
    area = st.session_state.get(f"calc_area_{pid}")
    # La calculadora deja la superficie en blanco si la persona la borra; para Cebi eso es «cuenta pendiente», igual
    # que allá, y no «usa la superficie del catálogo».
    area_vacia = f"calc_area_{pid}" in st.session_state and area is None
    lista = respuestas(ctx.d, ctx.pred, ctx.modelo, ctx.conf, pid, oof=ctx.oof_parcela, precio=precio, costo=costo,
                       area=area, clima=ctx.C, normal=clima_normal(), series=ctx.S,
                       libreta=st.session_state.get("bitacora", {}).get(pid), area_pendiente=area_vacia)
    cuenta = respuestas_cuenta(ctx.d, ctx.pred, pid, precio=precio, costo=costo, area=area, area_pendiente=area_vacia)
    todas = lista + cuenta          # lo que el enrutador y el historial ven: las de la parcela y las de la cuenta
    clave = f"cebi_{pid}"
    hechas = st.session_state.setdefault(clave, [])
    tema = st.session_state.get(f"{clave}_tema")
    with st.container(key="cebi_chat"):
        h(f"<div class='cebi-cabecera'><div class='cebi' aria-hidden='true'>{MASCOTA}</div>"
          f"<div><strong>Cebi<span class='cebi-hojita' aria-hidden='true'>✦</span></strong><span>Con los datos de tu parcela</span></div>"
          f"<span class='cebi-parcela'>Parcela {e(pid)}</span></div>")
        st.button("✕", key="cebi_cerrar_chat", on_click=_cerrar, type="tertiary",
                  help="Cerrar la conversación")
        with st.container(height=220 if hechas else 150, border=False, autoscroll=True, key="cebi_mensajes"):
            mensajes = [f"<div class='cebi-respuesta'>{e(saludo(ctx.d, ctx.pred, ctx.modelo, ctx.conf, pid))}</div>"]
            mensajes.extend(_burbujas(hechas[-TURNOS:], todas))
            h("<div class='cebi-conversacion' role='log' aria-label='Conversación con Cebi' aria-live='polite'>"
              + "".join(mensajes) + "</div>")
        # Antes de la primera pregunta los botones invitan a explorar en rejilla; después se encogen a una fila que
        # se desliza, para dejarle la pantalla a la conversación. El cambio es sólo de clase: si aquí cambiara la
        # llave del contenedor o el número de columnas, Streamlit rehace el bloque y el popover se cierra solo.
        # Al empezar se pregunta de qué se quiere hablar (dos pastillas); al escoger, salen las de ese tema. Las
        # columnas son siempre las mismas, y las que no llevan pastilla las esconde el CSS.
        rotulo = ("¿Qué quieres explorar?" if tema is None else "Más preguntas" if hechas
                  else "Explora tu parcela" if tema == TEMA_PARCELA else "Tu cuenta")
        h(f"<div class='cebi-sugerencias{' cebi-fila' if hechas else ''}'><span>{rotulo}</span></div>")
        with st.container(key="cebi_preguntas"):
            columnas = st.columns(max(len(lista), len(cuenta), 2), gap="small")
            if tema is None:
                columnas[0].button("Mi parcela", key=f"{clave}_t_parcela", width="stretch", wrap=True,
                                   help="Tu estimación, tus vecinos, el clima y el satélite",
                                   on_click=_elegir_tema, args=(clave, TEMA_PARCELA))
                columnas[1].button("Mi cuenta", key=f"{clave}_t_cuenta", width="stretch", wrap=True,
                                   help="Cuánto necesitas sacar, qué pasa en un año bajo o alto y qué hacer "
                                        "si no alcanza",
                                   on_click=_elegir_tema, args=(clave, TEMA_CUENTA))
            elif tema == TEMA_PARCELA:
                for indice, (pregunta, _) in enumerate(lista):
                    columnas[indice].button(_etiqueta(pregunta), help=pregunta, key=f"{clave}_{indice}",
                                            width="stretch", wrap=True, on_click=_preguntar, args=(clave, indice))
            else:
                for j, (pregunta, _) in enumerate(cuenta):
                    columnas[j].button(_etiqueta(pregunta), help=pregunta, key=f"{clave}_c{j}", width="stretch",
                                       wrap=True, on_click=_preguntar, args=(clave, j - len(cuenta)))
        with st.container(horizontal=True, vertical_alignment="center", key="cebi_compositor"):
            escrito = st.chat_input("Escribe tu pregunta…", key=f"{clave}_texto")
            _escuchar(clave, pid, todas, len(cuenta))
        if escrito:
            _decir(clave, escrito, todas, len(cuenta))
            st.rerun()
        with st.container(horizontal=True, horizontal_alignment="right"):
            st.button("Cambiar de tema", key=f"{clave}_cambiar", type="tertiary", disabled=tema is None,
                      on_click=_elegir_tema, args=(clave, None), width="content", wrap=True)
            st.button("Empezar de nuevo", key=f"{clave}_borrar", type="tertiary", disabled=not hechas,
                      on_click=_reiniciar, args=(clave,), width="content", wrap=True)


def pregunta_cebi(ctx, pid):
    """Acceso persistente abajo a la derecha y conversación en un popover nativo."""
    with st.container(key="cebi_launcher"):
        h(f"<div class='cebi-acceso' aria-hidden='true'><span>¿Te ayudo?</span>"
          f"<div class='cebi'>{MASCOTA}</div></div>")
        # La llave lleva una vuelta: cambiarla es lo único que cierra un popover desde Python (lo rehace).
        with st.popover("Pregúntale a Cebi", key=f"cebi_popover_{st.session_state.get('cebi_vuelta', 0)}", width=72):
            _platica(ctx, pid)
