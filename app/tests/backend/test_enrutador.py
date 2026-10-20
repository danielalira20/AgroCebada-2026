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
             ("¿Cuántas toneladas me van a salir?", "r1"),
             ("¿Por qué mi vecino tiene el mismo número?", "r2"),
             ("¿Qué tanto puedo confiar?", "r3"),
             ("¿De cuánto puede fallar mi número?", "r4"),
             ("¿Me alcanza para mis costos?", "r5"),
             ("¿Cómo se vio mi parcela desde el satélite?", "r6"),
             ("¿Cómo estuvo el clima este año en mi zona?", "r7"),
             ("¿Qué haría más precisa mi cifra?", "r8")]

# --- normalizar: acentos y mayúsculas no deben cambiar el resultado
assert normalizar("¿CUÁNTO Saqué?") == "¿cuanto saque?"
assert normalizar("LLOVIÓ") == "llovio"

# --- cómo lo preguntaría quien cultiva
casos = [
    ("por que me sale ese numero", 0), ("de donde sale esa cifra", 0), ("cuanto voy a sacar", 0),
    ("cuantas toneladas me van a salir", 1), ("cuanto me sale en total", 1),
    ("cuantos camiones voy a llenar", 1), ("cuanta produccion tendre", 1),
    ("mi vecino tiene lo mismo, por que", 2), ("por que mi compadre de al lado tiene igual", 2),
    ("que tanto le puedo creer", 3), ("es seguro ese dato", 3),
    ("se equivoca mucho", 4), ("de cuanto puede fallar", 4), ("que tanto error tiene", 4),
    ("me alcanza para los gastos", 5), ("cuanto dinero saco", 5), ("sirve para un credito", 5),
    ("como se vio mi parcela desde el satelite", 6), ("se veia verde mi milpa", 6),
    ("salio en las fotos del satelite", 6),
    ("como estuvo la lluvia", 7), ("llovio poco este año", 7), ("hubo helada", 7),
    ("como mejoro mi cifra", 8), ("que puedo hacer para que sea mas exacta", 8),
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
               ("¿Cuántas toneladas saqué en total?", "b"),
               ("¿Entre qué valores quedaron las de mi municipio?", "c"),
               ("¿Me alcanza para mis costos?", "d"),
               ("¿Cómo se vio mi parcela desde el satélite?", "e")]
assert enrutar("como me fue comparado con el municipio", con_cosecha) == 0
assert enrutar("cuantas toneladas saque en total", con_cosecha) == 1
assert enrutar("entre que valores quedaron", con_cosecha) == 2
assert enrutar("cuanto gane de dinero", con_cosecha) == 3
assert enrutar("como se veia desde el satelite", con_cosecha) == 4
# el margen sólo existe donde hay estimación: aquí la cosecha ya se conoce y no hay a qué arrimarlo
assert enrutar("de cuanto puede fallar", con_cosecha) is None

# --- el mensaje de «no entendí» admite que no sabe y ofrece lo que sí
m = no_entendi(PREGUNTAS)
assert "no entendí" in m.lower() and "inventar" in m.lower(), m
assert "por qué mi parcela tiene 4.52" in m.lower(), m      # ofrece ejemplos reales de lo que sí sabe

# --- «Mi cuenta»: el enrutador ve la lista completa (parcela + las tres de la cuenta), como en pregunta_cebi.py
CUENTA = [("¿Cuánto necesito sacar para no perder?", "c0"),
          ("¿Qué pasa si el año sale bajo o alto?", "c1"),
          ("¿Qué hago si no me alcanza?", "c2")]
TODAS = PREGUNTAS + CUENTA
casos_cuenta = [
    ("cuanto necesito sacar para no perder", 9), ("cual es mi punto de equilibrio", 9),
    ("cuanto debo sacar para cubrir mis costos", 9), ("lo minimo para empatar", 9),
    ("que pasa si el año sale bajo", 10), ("y si me va mal este año", 10), ("que pasaria en un año malo", 10),
    ("como seria el peor escenario", 10),
    ("que hago si no me alcanza", 11), ("y si no alcanza el dinero que hago", 11), ("hay algun apoyo", 11),
    ("necesito un plan b", 11),
    # lo de antes sigue donde estaba: «alcanza» solo sigue siendo «¿Me alcanza para mis costos?»
    ("me alcanza para los gastos", 5), ("cuanto dinero saco", 5), ("como estuvo la lluvia", 7),
]
for frase, esperado in casos_cuenta:
    assert enrutar(frase, TODAS) == esperado, (frase, enrutar(frase, TODAS), esperado)
# sin las de la cuenta (otra lista) esas frases no caen en cualquiera
assert enrutar("que pasa si el año sale bajo", PREGUNTAS) != 10
print(f"{len(casos_cuenta)} frases de «Mi cuenta» enrutadas a la respuesta correcta")
print("OK")
