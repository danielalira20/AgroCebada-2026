"""Guía de uso (assets/js/guia.js):  python tests/frontend/test_guia.py  (desde app/).

No corre el navegador: comprueba que cada paso del tour apunte a algo que la app de verdad dibuja (la llave de su
contenedor existe en el código), que cada vista tenga su recorrido y que los textos no prometan lo que el método no hace.
"""
import re
import sys
from pathlib import Path

APP = Path(__file__).resolve().parents[2]
JS = (APP / "assets" / "js" / "guia.js").read_text(encoding="utf-8")
FUENTES = "\n".join(p.read_text(encoding="utf-8") for p in (APP / "agrocebada_app").rglob("*.py"))

# --- cada llave que el tour busca existe como texto entre comillas en el código de la app (key="...", f"..." o la que
# se pasa a un componente, como la de la ficha)
llaves = sorted(set(re.findall(r"st-key-([A-Za-z0-9_]+)", JS)))
assert llaves, "no se encontró ninguna llave en guia.js"
for llave in llaves:
    assert re.search(r"[\"']" + re.escape(llave), FUENTES), f"guia.js busca st-key-{llave} y la app no la dibuja"
print(f"{len(llaves)} llaves del tour existen en la app")

# --- cada vista que detecta tiene recorrido, y los recorridos se alcanzan desde vistaActual()
pasos = re.search(r"const PASOS = \{(.*?)\n  \};", JS, re.S).group(1)
vistas = set(re.findall(r"^    (\w+): \[", pasos, re.M))
assert vistas == {"agricultor", "analista", "rapida"}, vistas
detectadas = set(re.findall(r'\? "(\w+)"', JS.split("const vistaActual")[1].split("const hayDialogo")[0]))
assert detectadas == vistas, (detectadas, vistas)

# --- lo nuevo está en la guía del agricultor y de la consulta rápida
for texto in ("Dos formas de consultar", "Pregúntale a Cebi", "Mi parcela", "Mi cuenta", "punto de equilibrio",
              "Estás en Consulta rápida", "La referencia de tu municipio"):
    assert texto in JS, texto
assert "st-key-cebi_launcher" in pasos and "st-key-glass_recorrido_agricultor" in pasos
assert "agricultor: \"_2\"" in JS, "la guía del agricultor cambió: debe volver a mostrarse una vez"

# --- lo que Cebi y la guía no pueden prometer
for frase in ("vas a perder cosecha", "conviene revisar", "se recomienda sembrar", "será buena", "será mala",
              "predice tu cosecha", "garantiza"):
    assert frase not in JS, frase
print("OK")
