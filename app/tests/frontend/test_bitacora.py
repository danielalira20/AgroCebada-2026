"""Prueba de «Tu libreta» sin navegador:  python tests/frontend/test_bitacora.py  (desde app/)."""
import sys
from pathlib import Path

APP = Path(__file__).resolve().parents[2]       # app/
sys.path.insert(0, str(APP))

from streamlit.testing.v1 import AppTest  # noqa: E402

from agrocebada_app.backend.datos import paquete  # noqa: E402
from agrocebada_app.backend.dominio import transcribir as voz  # noqa: E402
from agrocebada_app.config import MODELO_OFICIAL  # noqa: E402

paquete.exigir_datos()


def pantalla(pid, modelo, entradas):
    """Dibuja la libreta de una parcela con las cosechas ya anotadas que se le pasen."""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]) if "__file__" in dir() else ".")
    import streamlit as st

    from agrocebada_app.backend.datos import paquete as pq
    from agrocebada_app.backend.dominio import bitacora as bit
    from agrocebada_app.frontend.estado.contexto import calcular
    from agrocebada_app.frontend.vistas.agricultor.bitacora import bitacora

    ctx = calcular(pq.parcelas(), pq.soporte(), pq.series(), pq.clima(), modelo, False)
    if "bitacora" not in st.session_state:          # sembrar una sola vez: lo que se anote después debe sobrevivir
        libreta = bit.vacia()
        area = float(ctx.d.loc[pid, "AREA_HA"])
        est = float(ctx.pred.loc[pid, "prediccion"]) if pid in ctx.pred.index else None
        for anio, ton in entradas:
            libreta = bit.agregar(libreta, bit.nueva_entrada(anio, ton, area, est))
        st.session_state["bitacora"] = {pid: libreta}
    bitacora(ctx, pid)


PID = "AGC_011"      # Chignahuapan, una de las 59: la app sí tiene estimación para ella

# --- libreta vacía: invita a escribir, no muestra tablero ni progreso
at = AppTest.from_function(pantalla, args=(PID, MODELO_OFICIAL, []), default_timeout=300).run()
assert not at.exception, at.exception
texto = " ".join(x.value for x in at.markdown)
assert "Tu libreta" in texto and PID in texto
assert "Todavía no has anotado" in texto, "la libreta vacía debe invitar a escribir"
assert "lib-renglon" not in texto and "lib-meta" not in texto
assert "¿Cómo uso mi libreta?" in " ".join(e.label for e in at.expander), [e.label for e in at.expander]
print("libreta vacía: invita a anotar y esconde tablero y progreso")

# --- con cosechas anotadas: renglones, comparación con la app, progreso y tablero
at = AppTest.from_function(pantalla, args=(PID, MODELO_OFICIAL, [(2023, 28.0), (2024, 31.0), (2025, 32.0)]),
                           default_timeout=300).run()
assert not at.exception, at.exception
texto = " ".join(x.value for x in at.markdown)
assert texto.count("lib-renglon") == 3, texto.count("lib-renglon")
for anio in ("2023", "2024", "2025"):
    assert f">{anio}<" in texto, anio
assert "de lo que estimó la app" in texto, "cada renglón compara contra la estimación"
assert "lib-meta" in texto and "Chignahuapan" in texto
# Chignahuapan tiene 71 parcelas: ya pasó el tope de la regla, así que no promete subir de nivel
assert "suficientes para la regla" in texto and "está a" not in texto
etiquetas = [e.label for e in at.expander]
assert "Ver mi tablero" in etiquetas, etiquetas
assert "Años anotados" in texto and "Tu promedio" in texto
assert "no se guarda en ningún servidor" in texto, "debe quedar claro que la libreta no se almacena"
print("libreta con 3 cosechas: renglones, comparación con la app, progreso y tablero")

# --- un municipio con pocas cosechas sí muestra cuántos vecinos faltan
d = paquete.parcelas()
chico = d[(d.CONJUNTO == "PREDICCION") & (d.municipio == "Nanacamilpa de Mariano Arista")]
if len(chico):
    pid_chico = chico.index[0]
    at = AppTest.from_function(pantalla, args=(pid_chico, MODELO_OFICIAL, [(2025, 18.0)]), default_timeout=300).run()
    assert not at.exception, at.exception
    texto = " ".join(x.value for x in at.markdown)
    assert "está a" in texto and "vecino" in texto, "con 1 parcela debe decir cuántos faltan"
    assert "confianza baja a media" in texto, texto[-400:]
    print(f"{pid_chico} (Nanacamilpa): dice cuántos vecinos faltan para subir de confianza")

# --- dictar la nota: el micrófono vive fuera del formulario, porque dentro Streamlit no entrega el audio hasta
# enviar y la transcripción se guardaría sin que nadie pudiera corregirla
at = AppTest.from_function(pantalla, args=(PID, MODELO_OFICIAL, []), default_timeout=300).run()
assert not at.exception, at.exception
assert len(at.get("audio_input")) == (1 if voz.disponible() else 0)
assert not [x for x in at.expander if "dicta" in x.label.lower()], "el micrófono no se esconde"
assert f"lib_nota_{PID}" in at.session_state, "el campo de la nota tiene que ser escribible desde fuera"

# lo que se transcribe cae en el campo, se puede corregir, y al anotar queda en la libreta
at.session_state[f"lib_nota_{PID}"] = "granizo en julio"
at.run()
assert at.text_input(key=f"lib_nota_{PID}").value == "granizo en julio", "la nota dictada debe verse en el campo"
at.number_input[1].set_value(30.0)
at.button[0].click().run()
assert not at.exception, at.exception
guardada = at.session_state["bitacora"][PID]
assert list(guardada.nota) == ["granizo en julio"], list(guardada.nota)
print("la nota dictada llega al campo, se puede corregir y queda anotada en la libreta")
print("OK")
