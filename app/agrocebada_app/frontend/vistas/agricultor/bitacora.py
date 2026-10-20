"""«Tu libreta»: el productor anota lo que de verdad cosechó cada año y ve qué tan cerca estuvo la app.

Se lee como una libreta, no como un formulario: un renglón por año, el más reciente abajo, con lo que levantó y lo
que la app había estimado. Debajo, dos cosas que sólo aparecen cuando ya hay algo escrito: cuántos vecinos le faltan
a su municipio para subir de confianza —la regla de M01 leída hacia adelante— y un tablero para quien quiera las
cifras. Nada sale de su navegador: la libreta vive en la sesión y se descarga como un archivo suyo.
"""
import altair as alt
import pandas as pd
import streamlit as st

from agrocebada_app.backend.dominio import bitacora as bit
from agrocebada_app.backend.dominio import transcribir as voz
from agrocebada_app.backend.modelo.estimador import estadistico
from agrocebada_app.frontend.componentes.graficas.base import grafica_base
from agrocebada_app.frontend.tema.estilos import MASCOTA
from agrocebada_app.frontend.tema.html import e, h, titulo

_PENDIENTE = "lib_audio_%s"      # la grabación que todavía no se anota
_VUELTA = "lib_voz_n_%s"         # cuántas veces se ha anotado: renueva la grabadora

GUIA = [("Anota lo que levantaste", "Sólo necesitas el año y cuántas toneladas sacaste de toda la parcela. El "
                                    "rendimiento por hectárea lo saca la app con tu superficie."),
        ("Compara con lo que dijo la app", "Cada renglón te muestra lo que la app había estimado y por cuánto le "
                                           "atinó o le falló. Así sabes qué tanto fiarte de ella."),
        ("Guarda tu libreta", "Descárgala cuando termines. Es tuya: no se queda en ningún servidor. La próxima vez "
                              "la vuelves a subir y sigues anotando. El archivo lleva lo escrito; las notas de voz "
                              "sólo viven mientras tengas esta pantalla abierta.")]


def _estado(pid):
    libretas = st.session_state.setdefault("bitacora", {})
    return libretas.setdefault(pid, bit.vacia())


def _guardar(pid, libreta):
    st.session_state.setdefault("bitacora", {})[pid] = libreta


def _guia():
    pasos = "".join(f"<li><b>{e(t)}</b><span>{e(x)}</span></li>" for t, x in GUIA)
    h(f"<div class='mascota'><div class='cebi'>{MASCOTA}</div><div><ol class='lib-guia'>{pasos}</ol></div></div>")


def _renglones(libreta, area):
    """La libreta: un renglón por año, el más reciente abajo, como se escribe a mano.

    Se dibuja renglón por renglón y no de un tirón porque el que trae nota de voz lleva su reproductor: así cada
    grabación se queda con su año en vez de perderse cuando se graba la siguiente."""
    with st.container(key="lib_hoja"):
        for x in libreta.itertuples():
            if pd.notna(x.diferencia):
                arriba = float(x.diferencia) >= 0
                comp = (f"<span class='lib-dif {'arriba' if arriba else 'abajo'}'>"
                        f"{'▲' if arriba else '▼'} {abs(float(x.diferencia)):.2f} t/ha "
                        f"{'arriba' if arriba else 'abajo'} de lo que estimó la app</span>")
            else:
                comp = "<span class='lib-dif sin'>la app no tenía estimación para este año</span>"
            nota = f"<div class='lib-nota'>{e(x.nota)}</div>" if isinstance(x.nota, str) and x.nota else ""
            audio = getattr(x, bit.AUDIO, None)
            with st.container(key=f"lib_renglon_{int(x.anio)}"):
                h(f"<div class='lib-renglon'><div class='lib-anio'>{int(x.anio)}</div><div class='lib-cuerpo'>"
                  f"<div class='lib-cifra'>{float(x.toneladas):,.2f} <small>t en toda la parcela</small>"
                  f"<b>{float(x.rendimiento):.2f} <small>t/ha</small></b></div>{comp}{nota}"
                  f"{'<div class=\'lib-voz\'>Tu nota de voz</div>' if audio else ''}</div></div>")
                if audio:
                    st.audio(bytes(audio), format="audio/wav")


def _progreso(n_cosecha, municipio):
    """Cuántos vecinos faltan para que el municipio suba de nivel. Es la regla de M01 contada hacia adelante: el
    conteo abre la puerta a «alta», pero el error del municipio es el que decide."""
    f = bit.faltan_para_subir(n_cosecha)
    if not f["faltan"]:
        h(f"<div class='lib-meta'><div class='lib-meta-txt'>{e(municipio)} ya tiene {f['n']} parcelas con cosecha: "
          "suficientes para la regla. Tu registro sigue sumando al historial de tu parcela.</div></div>")
        return
    puntos = "".join(f"<span class='{'lleno' if i < f['n'] else 'vacio'}'></span>" for i in range(f["tope"]))
    falta = f"{f['faltan']} vecino{'s' if f['faltan'] != 1 else ''}"
    cola = (" si además el error de tu municipio queda por debajo del promedio" if f["condicionado"] else "")
    h(f"<div class='lib-meta'><div class='lib-puntos'>{puntos}</div><div class='lib-meta-txt'>"
      f"<b>{e(municipio)} está a {e(falta)}</b> de pasar de confianza {e(f['nivel'])} a {e(f['siguiente'])}"
      f"{e(cola)}. Hoy tiene {f['n']} de {f['tope']} parcelas con cosecha registrada.</div></div>")


def _tablero(r, libreta, valor_municipio):
    """Para quien sí quiere las cifras: promedio, mejor y peor año, qué tanto le atinó la app y la gráfica."""
    kp = [("Años anotados", f"{r['anios']}", ""), ("Tu promedio", f"{r['promedio']:.2f}", "t/ha"),
          (f"Mejor año ({r['mejor']['anio']})", f"{r['mejor']['rendimiento']:.2f}", "t/ha"),
          ("Total levantado", f"{r['total_toneladas']:,.2f}", "t")]
    if r["error_app"] is not None:
        kp.append(("La app se equivocó por", f"{r['error_app']:.2f}", "t/ha en promedio"))
    if r["vs_municipio"] is not None:
        signo = "+" if r["vs_municipio"] >= 0 else ""
        kp.append(("Contra el valor de tu municipio", f"{signo}{r['vs_municipio']:.2f}", "t/ha"))
    h("<div class='fila lib-tablero'>" + "".join(
        f"<div class='mini'><span>{e(k)}</span><b class='kv'>{e(v)}<small>{e(u)}</small></b></div>"
        for k, v, u in kp) + "</div>")
    x = libreta.assign(anio_txt=libreta.anio.astype(int).astype(str))
    barras = alt.Chart(x).mark_bar(color="#9BE15D", opacity=.75, cornerRadiusTopLeft=4, cornerRadiusTopRight=4,
                                   size=34).encode(
        x=alt.X("anio_txt:N", title=None), y=alt.Y("rendimiento:Q", title="t/ha"),
        tooltip=[alt.Tooltip("anio_txt:N", title="Año"), alt.Tooltip("rendimiento:Q", title="t/ha", format=".2f"),
                 alt.Tooltip("toneladas:Q", title="toneladas", format=".2f")])
    capas = [barras]
    if valor_municipio is not None:
        linea = alt.Chart(pd.DataFrame({"v": [float(valor_municipio)]})).mark_rule(
            color="#E8EEE9", strokeDash=[4, 4], strokeWidth=2).encode(y="v:Q")
        capas.append(linea)
    st.altair_chart(grafica_base(alt.layer(*capas), 240), width="stretch")
    if valor_municipio is not None:
        h(f"<div class='nota'>La raya punteada es el valor típico de tu municipio ({float(valor_municipio):.2f} "
          "t/ha), que es lo que la app usa para estimar. Tus barras son lo que de verdad levantaste.</div>")


def _dictar(pid, clave):
    """Dictar la nota del año: la grabación se guarda para anotarla con su renglón y, de paso, se pasa a texto en
    el campo para poder corregirlo.

    Va fuera del formulario a propósito: dentro, Streamlit no entrega el audio hasta que se envía, y la nota se
    guardaría sin que nadie hubiera podido leerla. Si este equipo no puede transcribir, no se dibuja el micrófono."""
    if not voz.disponible():
        return
    with st.container(horizontal=True, vertical_alignment="center", horizontal_alignment="right", key="lib_dictado"):
        h("<span class='lib-dictar'>¿Prefieres dictarla? La escribo por ti</span>")
        # la llave cambia después de anotar para que la grabadora salga limpia y nadie anote dos veces el mismo audio
        audio = st.audio_input("Dicta tu nota", key=f"lib_voz_{pid}_{st.session_state.get(_VUELTA % pid, 0)}",
                               label_visibility="collapsed")
    if audio is None:
        st.session_state.pop(_PENDIENTE % pid, None)      # si borró la grabación, se va con ella
        return
    datos = audio.getvalue()
    if st.session_state.get(_PENDIENTE % pid) == datos:   # ya la oí; no la vuelvo a transcribir en cada vuelta
        return
    st.session_state[_PENDIENTE % pid] = datos            # se guarda aunque no se pueda transcribir: el audio manda
    with st.spinner("Escuchando tu nota…"):
        try:
            texto = voz.transcribir(datos)
        except RuntimeError as ex:
            st.warning(str(ex))
            return
    if not texto:
        st.warning("No alcancé a entender la grabación, pero tu nota de voz se guarda igual al anotar.")
        return
    st.session_state[clave] = texto[:bit.MAX_NOTA]
    st.rerun()


def bitacora(ctx, pid):
    d, pred = ctx.d, ctx.pred
    r = d.loc[pid]
    area = float(r.AREA_HA)
    entrena = d[d.CONJUNTO == "ENTRENAMIENTO"]
    cosechas_mun = entrena.real[entrena.municipio == r.municipio].dropna()
    valor_municipio = float(estadistico(ctx.modelo)(cosechas_mun)) if len(cosechas_mun) else None
    if r.CONJUNTO == "PREDICCION":
        estimacion = float(pred.loc[pid, "prediccion"])
    else:
        estimacion = float(ctx.oof_parcela[pid]) if pid in ctx.oof_parcela.index else None

    with st.container(key="glass_bitacora"):
        titulo(f"Tu libreta · {pid}",
               "Anota lo que cosechaste cada año. Es tuya y no se guarda en ningún servidor: al final la descargas.")
        with st.expander("¿Cómo uso mi libreta?"):
            _guia()

        libreta = _estado(pid)
        if libreta.empty:
            h("<div class='lib-vacia'>Todavía no has anotado ninguna cosecha. Empieza por la del año pasado: "
              "sólo necesitas cuántas toneladas levantaste.</div>")
        else:
            _renglones(libreta, area)

        nota_clave = f"lib_nota_{pid}"
        _dictar(pid, nota_clave)
        with st.form(key=f"lib_form_{pid}", clear_on_submit=True, border=False):
            c1, c2, c3 = st.columns([1, 1, 2])
            anio = c1.number_input("¿De qué año?", min_value=bit.ANIO[0], max_value=bit.ANIO[1], value=2025, step=1)
            ton = c2.number_input("¿Cuántas toneladas levantaste?", min_value=0.0, value=None, step=0.5,
                                  placeholder="de toda la parcela",
                                  help=f"De toda tu parcela, que mide {area:,.2f} ha. La app saca sola el t/ha.")
            nota = c3.text_input("¿Algo que recordar de ese año? (opcional)", placeholder="granizo en julio, "
                                 "sembré tarde, cambié de semilla…", max_chars=bit.MAX_NOTA, key=nota_clave)
            if st.form_submit_button("Anotar en mi libreta", type="primary"):
                if not ton:
                    st.warning("Escribe cuántas toneladas levantaste para poder anotarlo.")
                else:
                    try:
                        libreta = bit.agregar(libreta, bit.nueva_entrada(
                            anio, ton, area, estimacion, nota, audio=st.session_state.get(_PENDIENTE % pid)))
                        _guardar(pid, libreta)
                        st.session_state.pop(_PENDIENTE % pid, None)
                        st.session_state[_VUELTA % pid] = st.session_state.get(_VUELTA % pid, 0) + 1
                        st.rerun()
                    except bit.Dato as ex:
                        st.warning(str(ex))

        if not libreta.empty:
            n_cosecha = int(ctx.conf.set_index("municipio").n_cosecha.get(r.municipio, len(cosechas_mun)))
            _progreso(n_cosecha, r.municipio)
            with st.expander("Ver mi tablero"):
                _tablero(bit.resumen(libreta, valor_municipio), libreta, valor_municipio)

        st.download_button("Descargar mi libreta", bit.a_csv(libreta, pid, r.municipio),
                           file_name=f"libreta_{pid}.csv", mime="text/csv", on_click="ignore",
                           width="stretch", disabled=libreta.empty, key=f"lib_baja_{pid}",
                           help="Guárdala en tu teléfono. La próxima vez la vuelves a subir aquí y sigues anotando. Lleva lo escrito; las notas de voz no caben en el archivo.")
        with st.expander("¿Ya tienes una libreta guardada? Súbela aquí"):
            subido = st.file_uploader("Elige el archivo que descargaste", type=["csv"], key=f"lib_sube_{pid}")
        if subido is not None and st.session_state.get("lib_ultimo") != (pid, subido.name, subido.size):
            st.session_state["lib_ultimo"] = (pid, subido.name, subido.size)
            try:
                _guardar(pid, bit.desde_csv(subido.getvalue()))
                st.rerun()
            except bit.Dato as ex:
                st.warning(str(ex))
