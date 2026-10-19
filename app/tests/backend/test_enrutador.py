"""Pruebas del enrutador de Cebi:  python tests/backend/test_enrutador.py  (desde app/).

Lo que se vigila: que una pregunta escrita con las palabras del productor llegue a la respuesta correcta, y que lo
que Cebi no sabe se quede sin respuesta en vez de caer en cualquiera. Cebi elige; no redacta.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agrocebada_app.backend.dominio.enrutador import enrutar, no_entendi, normalizar  # noqa: E402

# Las preguntas tal como las arma respuestas.py para una parcela por estimar.
PREGUNTAS = [("¿Por qué mi parcela tiene 4.52?", "r0"),
             ("¿Por qué mi vecino tiene el mismo número?", "r1"),
             ("¿Qué tanto puedo confiar?", "r2"),
             ("¿Me alcanza para mis costos?", "r3"),
             ("¿Cómo estuvo el clima este año en mi zona?", "r4"),
             ("¿Qué haría más precisa mi cifra?", "r5")]

# --- normalizar: acentos y mayúsculas no deben cambiar el resultado
assert normalizar("¿CUÁNTO Saqué?") == "¿cuanto saque?"
assert normalizar("LLOVIÓ") == "llovio"

# --- cómo lo preguntaría quien cultiva
casos = [
    ("por que me sale ese numero", 0), ("de donde sale esa cifra", 0), ("cuanto voy a sacar", 0),
    ("mi vecino tiene lo mismo, por que", 1), ("por que mi compadre de al lado tiene igual", 1),
    ("que tanto le puedo creer", 2), ("es seguro ese dato", 2), ("se equivoca mucho", 2),
    ("me alcanza para los gastos", 3), ("cuanto dinero saco", 3), ("sirve para un credito", 3),
    ("como estuvo la lluvia", 4), ("llovio poco este año", 4), ("hubo helada", 4),
    ("como mejoro mi cifra", 5), ("que puedo hacer para que sea mas exacta", 5),
]
for texto, esperado in casos:
    obtenido = enrutar(texto, PREGUNTAS)
    assert obtenido == esperado, f"«{texto}» -> {obtenido} (esperaba {esperado}: {PREGUNTAS[esperado][0]})"
print(f"{len(casos)} frases de productor enrutadas a la respuesta correcta")

# --- lo que NO sabe: se queda sin respuesta en vez de caer en cualquiera
for texto in ["¿cuándo debo sembrar?", "qué fertilizante uso", "hola", "", "   ",
              "cuánto vale el dólar", "asdfgh"]:
    assert enrutar(texto, PREGUNTAS) is None, f"«{texto}» no debería enrutar a nada"
print("preguntas fuera de su conocimiento: devuelve None, no una respuesta cualquiera")

# --- sólo enruta a lo que esa parcela tiene disponible
solo_clima = [("¿Cómo estuvo el clima este año en mi zona?", "r")]
assert enrutar("como estuvo la lluvia", solo_clima) == 0
assert enrutar("me alcanza para los gastos", solo_clima) is None, "no puede ofrecer una respuesta que no existe"

# --- preguntas de una parcela con cosecha registrada (otro juego de preguntas)
con_cosecha = [("¿Cómo le fue a mi parcela frente a las de mi municipio?", "a"),
               ("¿Entre qué valores quedaron las de mi municipio?", "b"),
               ("¿Me alcanza para mis costos?", "c")]
assert enrutar("como me fue comparado con el municipio", con_cosecha) == 0
assert enrutar("entre que valores quedaron", con_cosecha) == 1
assert enrutar("cuanto gane de dinero", con_cosecha) == 2

# --- el mensaje de «no entendí» admite que no sabe y ofrece lo que sí
m = no_entendi(PREGUNTAS)
assert "no entendí" in m.lower() and "inventar" in m.lower(), m
assert "por qué mi parcela tiene 4.52" in m.lower(), m      # ofrece ejemplos reales de lo que sí sabe
print("OK")
