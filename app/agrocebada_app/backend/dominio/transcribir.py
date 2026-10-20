"""Pasa a texto una nota de voz, con Whisper corriendo en el mismo equipo que la app.

Por qué del lado del servidor y no en el navegador: el reconocimiento de voz del navegador no existe en Firefox, es
impredecible en los navegadores que traen WhatsApp o Facebook —por donde mucha gente abre un enlace— y dentro de
Streamlit el micrófono queda bloqueado por el iframe. Grabando aquí, el teléfono sólo tiene que grabar, que eso sí
lo hace cualquiera, y la transcripción sale igual en todos los aparatos.

Es opcional a propósito: si `faster-whisper` no está instalado, la app no se rompe ni se queja; la nota de voz se
guarda igual y sólo se avisa que no se puede pasar a texto. El audio siempre manda sobre el texto: la transcripción
es una interpretación y se ofrece para que la persona la corrija, nunca se guarda a sus espaldas.
"""
import io
import os
import wave

import numpy as np

MODELO = os.environ.get("AGRO_WHISPER", "base")      # base da buen español sin pedir mucha máquina
IDIOMA = "es"
TASA = 16000                                         # lo que Whisper espera
MAX_SEGUNDOS = 180
_cargado = {}


def disponible():
    """True si se puede transcribir en este equipo."""
    try:
        import faster_whisper  # noqa: F401
    except Exception:
        return False
    return True


def por_que_no():
    """Qué decirle a quien no puede transcribir, en su idioma y sin jerga."""
    return ("En este equipo no está instalado el reconocimiento de voz, así que tu nota se guarda como audio y la "
            "puedes volver a oír cuando quieras. Para pasarla a texto hay que instalar faster-whisper.")


def _modelo():
    if "m" not in _cargado:
        from faster_whisper import WhisperModel
        _cargado["m"] = WhisperModel(MODELO, device="cpu", compute_type="int8")
    return _cargado["m"]


def muestras(audio):
    """El WAV que graba el navegador, convertido a mono de 16 kHz en coma flotante, que es lo que Whisper espera.

    Se decodifica con la biblioteca estándar a propósito: la ruta normal de faster-whisper pasa por PyAV, y esa
    versión no siempre tiene binario para el equipo de cada quien. Así la transcripción depende de menos cosas."""
    with wave.open(io.BytesIO(audio)) as w:
        canales, ancho, tasa = w.getnchannels(), w.getsampwidth(), w.getframerate()
        crudo = w.readframes(w.getnframes())
    if ancho == 1:                                   # 8 bits viene sin signo, centrado en 128
        x = np.frombuffer(crudo, dtype=np.uint8).astype(np.float32) - 128.0
        x /= 128.0
    else:
        tipo = {2: np.int16, 4: np.int32}.get(ancho)
        if tipo is None:
            raise RuntimeError("No reconozco el formato de la grabación.")
        x = np.frombuffer(crudo, dtype=tipo).astype(np.float32) / float(np.iinfo(tipo).max)
    if canales > 1:
        x = x.reshape(-1, canales).mean(axis=1)
    if tasa != TASA:
        destino = int(round(len(x) * TASA / tasa))
        x = np.interp(np.linspace(0, len(x), destino, endpoint=False), np.arange(len(x)), x).astype(np.float32)
    return np.ascontiguousarray(x[:TASA * MAX_SEGUNDOS], dtype=np.float32)


def transcribir(audio):
    """Texto de una nota de voz (`audio`: bytes del WAV grabado). Devuelve "" si no se entendió nada.

    Lanza RuntimeError si no se puede transcribir en este equipo, para que la pantalla lo cuente con `por_que_no`."""
    if not disponible():
        raise RuntimeError(por_que_no())
    if not audio:
        return ""
    partes, _ = _modelo().transcribe(muestras(audio), language=IDIOMA, vad_filter=True)
    return " ".join(p.text.strip() for p in partes).strip()
