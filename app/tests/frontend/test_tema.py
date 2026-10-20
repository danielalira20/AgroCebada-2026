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


def has_anidado(css):
    """Selectores con un :has() dentro de otro :has(). El navegador no los rechaza a gritos: tira esa parte y deja
    una regla que no empareja con nada, así que el estilo simplemente no se aplica y nadie se entera. Pasó con la
    grabadora de voz, que por eso se salía del panel."""
    css = re.sub(r"/\*.*?\*/", " ", css, flags=re.S)      # los comentarios hablan de selectores, no son selectores
    malos, i = [], css.find(":has(")
    while i != -1:
        hondo, j = 0, i + len(":has(")
        while j < len(css):                       # hasta cerrar el paréntesis de este :has(
            if css[j] == "(":
                hondo += 1
            elif css[j] == ")":
                if hondo == 0:
                    break
                hondo -= 1
            j += 1
        if ":has(" in css[i + len(":has("):j]:
            malos.append(css[max(0, i - 90):j + 1].replace("\n", " "))
        i = css.find(":has(", i + 1)
    return malos


def luminancia(hexadecimal):
    rgb = [int(hexadecimal[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    rgb = [v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in rgb]
    return sum(v * peso for v, peso in zip(rgb, (.2126, .7152, .0722)))


def contraste(a, b):
    mayor, menor = sorted((luminancia(a), luminancia(b)), reverse=True)
    return (mayor + .05) / (menor + .05)


# --- ningún selector con :has() dentro de otro :has(): esos el navegador los descarta sin avisar
for hoja in sorted((APP / "assets" / "css").glob("*.css")):
    malos = has_anidado(hoja.read_text(encoding="utf-8"))
    assert not malos, f"{hoja.name}: :has() anidado en {len(malos)} selector(es)\n" + "\n".join(malos[:3])
print("CSS: sin :has() anidados, que el navegador descartaría en silencio")

# --- el borde de los controles: lo que se puede tocar necesita 3:1 contra su fondo, o el botón deja de
# leerse como botón. Es distinto de --borde, que dibuja superficies y debe seguir siendo discreto.
CONTROL = {"claro": ("#fffef8", "#fafbf9", "#f1f4ee", "#f6faf0", "#eaf0e0"),
           "oscuro": ("#0A110E", "#0c1310", "#15201B", "#14251e")}
for hoja, fondos in (("claro.css", CONTROL["claro"]), ("tema.css", CONTROL["oscuro"])):
    texto = (APP / "assets" / "css" / hoja).read_text(encoding="utf-8")
    hallado = re.findall(r"--borde-control:\s*(#[\da-fA-F]{6})", texto)
    assert hallado, f"{hoja} debe definir --borde-control"
    for fondo in fondos:
        assert contraste(hallado[-1], fondo) >= 3, (hoja, hallado[-1], fondo, contraste(hallado[-1], fondo))
print("CSS: el borde de los controles llega a 3:1 en los dos temas")

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
