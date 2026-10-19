"""Cambio de apariencia, aislamiento de sesión y contraste: ejecutar desde cualquier carpeta."""
import re
import sys
import tomllib
from pathlib import Path

APP = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(APP))

from streamlit.testing.v1 import AppTest

from agrocebada_app.backend.datos.experimentos import experimentos
from agrocebada_app.backend.dominio.evidencia import REDUCCION_MINIMA, filtrar_pruebas
from agrocebada_app.config import MODELO_OFICIAL
from agrocebada_app.frontend.componentes.evidencia.comparacion import especificacion


def luminancia(hexadecimal):
    rgb = [int(hexadecimal[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    rgb = [v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in rgb]
    return sum(v * peso for v, peso in zip(rgb, (.2126, .7152, .0722)))


def contraste(a, b):
    mayor, menor = sorted((luminancia(a), luminancia(b)), reverse=True)
    return (mayor + .05) / (menor + .05)


css = (APP / "assets/css/claro.css").read_text(encoding="utf-8")
tokens = dict(re.findall(r"--([\w-]+):\s*(#[\da-fA-F]{6})", css))
for token in ("texto-fuerte", "texto", "texto-suave", "tenue", "aviso-texto", "exito", "error",
              "conf-alta", "conf-baja", "mejora", "sin-mejora", "complementaria", "no-disponible"):
    for fondo in ("#fffef8", "#f1f4e9", "#f1f4ee", "#f6f8f2"):
        assert contraste(tokens[token], fondo) >= 4.5, (token, fondo)
assert contraste("#ffffff", tokens["acento"]) >= 4.5

# Incluso sobre un mapa negro, el vidrio debe permitir leer el texto secundario.
fondo_vidrio = "#" + "".join(f"{round(v * .78):02x}" for v in (248, 252, 240))
for texto in ("#384b32", tokens["texto"], tokens["texto-fuerte"]):
    assert contraste(texto, fondo_vidrio) >= 4.5
config = tomllib.loads((APP / ".streamlit/config.toml").read_text(encoding="utf-8"))["theme"]
assert contraste(config["dataframeHeaderTextColor"], config["dataframeHeaderBackgroundColor"]) >= 4.5

seleccion = filtrar_pruebas(experimentos(), 1, complementarias=True)
claro = especificacion(seleccion, MODELO_OFICIAL, REDUCCION_MINIMA, "claro")
oscuro = especificacion(seleccion, MODELO_OFICIAL, REDUCCION_MINIMA, "oscuro")
assert claro["datasets"] == oscuro["datasets"], "El tema no debe modificar los datos"
assert claro["config"] != oscuro["config"], "La caché debe distinguir el tema"
assert claro == especificacion(seleccion, MODELO_OFICIAL, REDUCCION_MINIMA, "claro")

for vista in ("Agricultor", "Analista"):
    at = AppTest.from_file(str(APP / "app.py"), default_timeout=300)
    for clave, valor in {"vista": vista, "bienvenida_completada": True, "satelite": False}.items():
        at.session_state[clave] = valor
    at.run()
    assert not at.exception, at.exception
    assert at.session_state["tema"] == "claro"
    antes = [(m.value) for m in at.markdown if "class='big'" in m.value or "class='kpis'" in m.value]
    at.button(key="alternar_tema").click().run()
    assert not at.exception, at.exception
    assert at.session_state["tema"] == "oscuro"
    assert at.session_state["vista"] == vista and not at.session_state["satelite"]
    assert antes == [m.value for m in at.markdown if "class='big'" in m.value or "class='kpis'" in m.value]
    assert "Modo claro" == at.button(key="alternar_tema").label
    at.button(key="alternar_tema").click().run()
    assert not at.exception, at.exception
    assert at.session_state["tema"] == "claro"
    assert at.session_state["vista"] == vista

print("OK: contraste AA de textos y botones, cambio de tema en ambas vistas y conservación de cifras y filtros")
