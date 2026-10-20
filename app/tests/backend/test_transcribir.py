"""Pruebas de la transcripción de notas de voz:  python tests/backend/test_transcribir.py  (desde app/).

La transcripción es opcional: si faster-whisper no está instalado, lo que se vigila es que la app no se rompa y que
el aviso se entienda. Si sí está, se comprueba la cadena completa con una grabación de verdad.
"""
import io
import math
import struct
import sys
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np  # noqa: E402

from agrocebada_app.backend.dominio import transcribir as voz  # noqa: E402
from agrocebada_app.backend.dominio.enrutador import enrutar  # noqa: E402


def wav(segundos=1.0, tasa=44100, canales=1, ancho=2, hz=440.0):
    """Un WAV sintético, para probar la decodificación sin depender de un archivo externo."""
    n = int(tasa * segundos)
    b = io.BytesIO()
    with wave.open(b, "wb") as w:
        w.setnchannels(canales)
        w.setsampwidth(ancho)
        w.setframerate(tasa)
        pico = 2 ** (8 * ancho - 1) - 1
        marcos = []
        for i in range(n):
            v = int(pico * 0.3 * math.sin(2 * math.pi * hz * i / tasa))
            marcos.append(struct.pack("<h" if ancho == 2 else "<i", v) * canales)
        w.writeframes(b"".join(marcos))
    return b.getvalue()


# --- decodificación: siempre sale mono, 16 kHz y coma flotante, venga como venga
for tasa, canales in [(44100, 1), (48000, 2), (16000, 1), (8000, 1)]:
    m = voz.muestras(wav(segundos=0.5, tasa=tasa, canales=canales))
    assert m.dtype == np.float32, (tasa, canales, m.dtype)
    assert m.ndim == 1, "debe quedar en mono"
    assert abs(len(m) - 0.5 * voz.TASA) <= 2, (tasa, canales, len(m))
    assert abs(float(np.abs(m).max()) - 0.3) < 0.05, "no debe cambiar el volumen"
print("decodificación: 44.1k, 48k estéreo, 16k y 8k llegan a mono de 16 kHz")

# --- una grabación más larga que el tope se recorta en vez de crecer sin límite
largo = voz.muestras(wav(segundos=2.0, tasa=16000))
assert len(largo) <= voz.TASA * voz.MAX_SEGUNDOS

# --- un formato que no se reconoce lo dice en lugar de reventar con jerga
try:
    voz.muestras(wav(segundos=0.2, ancho=1))      # 8 bits sí se admite
except Exception as ex:                            # pragma: no cover
    raise AssertionError(f"8 bits debería admitirse: {ex}")

# --- sin audio no hay texto, y sin motor la app lo explica en su idioma
assert "instalado" in voz.por_que_no() and "audio" in voz.por_que_no()

if not voz.disponible():
    print("faster-whisper no está instalado: la app seguiría guardando la nota de voz sin transcribir")
    print("OK")
    raise SystemExit

assert voz.transcribir(b"") == ""

# --- la cadena completa, con una grabación real del sistema si se puede generar
import subprocess  # noqa: E402
import tempfile  # noqa: E402

FRASE = "me alcanza para mis gastos con lo que voy a cosechar"
with tempfile.TemporaryDirectory() as tmp:
    aiff, onda = Path(tmp) / "v.aiff", Path(tmp) / "v.wav"
    try:
        subprocess.run(["say", "-o", str(aiff), FRASE], check=True, capture_output=True, timeout=60)
        subprocess.run(["afconvert", "-f", "WAVE", "-d", "LEI16@44100", str(aiff), str(onda)],
                       check=True, capture_output=True, timeout=60)
    except Exception:
        print("sin 'say'/'afconvert' en este equipo: me salto la prueba de voz real")
        print("OK")
        raise SystemExit
    dicho = voz.transcribir(onda.read_bytes())

assert dicho, "no transcribió nada"
assert "alcanza" in dicho.lower() and "gastos" in dicho.lower(), dicho
print(f"transcripción real: {dicho!r}")

# --- y lo transcrito llega a la respuesta correcta de Cebi
PREGUNTAS = [("¿Por qué mi parcela tiene 4.52?", "r0"), ("¿Me alcanza para mis costos?", "r1"),
             ("¿Cómo estuvo el clima este año en mi zona?", "r2")]
assert enrutar(dicho, PREGUNTAS) == 1, f"«{dicho}» debió enrutar a los costos"
print("voz -> texto -> respuesta conocida: la cadena completa funciona")
print("OK")
