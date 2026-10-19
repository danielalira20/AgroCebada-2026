"""Enruta lo que el productor escribe o dicta hacia una de las respuestas que Cebi ya sabe dar.

La regla del módulo es que Cebi nunca redacta: sólo elige. Esto empareja el texto libre con las preguntas que
`respuestas.py` arma a partir del dato, y si nada empareja lo bastante devuelve None para que Cebi diga que no sabe
en vez de inventar. Por eso no hay modelo de lenguaje aquí: un modelo que redacta puede afirmar lo que el método no
hace —por ejemplo, que el clima influye en la estimación— y eso es justo lo que no queremos.

Las palabras son las que usaría quien cultiva, no las de la pantalla: «me alcanza», «cuánto saco», «llovió».
"""
import re
import unicodedata

# Cada tema junta cómo reconocer su pregunta y las palabras con que la gente la pediría. Las «fuertes» son las que
# casi sólo aparecen en ese tema y por eso deciden: «dinero» manda a costos aunque la frase también diga «cuánto
# saco», que por sí solo hablaría del rendimiento.
TEMAS = [
    {"prefijo": "¿Por qué mi parcela tiene",
     # «cifra» y «número» los usa también quien pregunta por sus vecinos o por mejorar: son de apoyo, no deciden
     "fuertes": {"estimacion", "estima", "rendimiento", "calculo", "calcula"},
     "claves": {"por que", "porque", "de donde", "sale", "cuanto", "cuanta", "da", "dara", "saco", "sacar",
                "tonelada", "toneladas", "cifra", "numero"}},
    {"prefijo": "¿Cuántas toneladas",
     "fuertes": {"total", "totales", "produccion", "produzco", "produce", "camion", "camiones", "costales", "bultos"},
     "claves": {"toneladas", "tonelada", "cuantas", "hectareas", "salen", "saldra", "saldran", "juntar", "cosechar",
                "cosecho", "levanto", "levantar"}},
    {"prefijo": "¿Por qué mi vecino",
     "fuertes": {"vecino", "vecinos", "compadre", "iguales", "mismo", "misma"},
     "claves": {"igual", "parecido", "lado", "junto", "otros", "repetido"}},
    {"prefijo": "¿Qué tanto puedo confiar",
     "fuertes": {"confiar", "confianza", "fiar", "seguro", "segura", "garantia", "creer"},
     "claves": {"cierto", "creo", "dato", "fiable"}},
    {"prefijo": "¿De cuánto puede fallar",
     "fuertes": {"fallar", "falla", "falle", "error", "equivoca", "equivocar", "margen", "desviacion"},
     "claves": {"tanto", "lejos", "diferencia", "corto", "arriba", "abajo"}},
    {"prefijo": "¿Me alcanza",
     "fuertes": {"dinero", "peso", "pesos", "costo", "costos", "cuesta", "alcanza", "credito", "prestamo",
                 "ganancia", "ganancias", "precio", "vender", "venta", "gasto", "gastos", "invertir", "inversion"},
     "claves": {"gastar", "gano", "ganar", "negocio", "pierdo", "perder", "sirve"}},
    {"prefijo": "¿Cómo estuvo el clima",
     "fuertes": {"clima", "lluvia", "lluvias", "llovio", "llover", "sequia", "helada", "heladas", "granizo",
                 "temperatura"},
     "claves": {"agua", "seco", "seca", "calor", "frio", "tiempo", "temporal"}},
    {"prefijo": "¿Qué haría más precisa",
     "fuertes": {"mejorar", "mejoro", "mejora", "mejore", "precisa", "preciso", "exacta", "exacto", "afinar",
                 "registrar", "apuntar", "anotar", "libreta"},
     "claves": {"mejor", "ayudar", "ayudo", "hacer", "falta", "datos"}},
    {"prefijo": "¿Cómo le fue a mi parcela",
     "fuertes": {"comparo", "comparar", "comparado", "comparacion", "frente", "contra", "resulto"},
     "claves": {"como", "fue", "quede", "quedo", "arriba", "abajo", "municipio"}},
    {"prefijo": "¿Entre qué valores",
     "fuertes": {"valores", "rango", "minimo", "maximo", "dieron"},
     "claves": {"entre", "menos", "dio", "municipio", "normal", "quedaron"}},
    {"prefijo": "¿Cómo se vio mi parcela",
     "fuertes": {"satelite", "satelites", "verdor", "verde", "ndvi", "imagen", "imagenes", "foto", "fotos",
                 "se vio", "se veia"},
     "claves": {"vio", "ver", "veia", "arriba", "crecio", "crecer", "mes", "color", "cielo"}},
    {"prefijo": "¿Qué no sabe la app",
     "fuertes": {"no sabe", "ignora", "desconoce", "siembra", "variedad", "manejo", "limite", "limites"},
     "claves": {"sabe", "falta", "ve"}},
]
FUERTE, DEBIL = 3, 1
MINIMO = 2          # una palabra decisiva basta, o dos de apoyo; con menos, Cebi dice que no sabe en vez de
                    # arrimar la pregunta al tema más parecido («cuánto vale el dólar» no es su estimación)
_PALABRA = re.compile(r"[a-z0-9ñ]+")


def normalizar(texto):
    """Minúsculas y sin acentos, para que «cuánto» y «cuanto» sean lo mismo."""
    t = unicodedata.normalize("NFD", str(texto).lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def _coincidencias(plano, sueltas, palabras):
    """Cuántas de `palabras` aparecen. Las de una se comparan completas, para que «ve» no empate con «vecino»; las
    de dos («no sabe») se buscan tal cual dentro de la frase."""
    de_una = {c for c in palabras if " " not in c}
    return len(sueltas & de_una) + sum(1 for c in palabras - de_una if c in plano)


def _puntos(texto, tema):
    """Peso del tema para esa frase: las palabras decisivas valen más que las de apoyo."""
    plano = normalizar(texto)
    sueltas = set(_PALABRA.findall(plano))
    return (FUERTE * _coincidencias(plano, sueltas, tema["fuertes"])
            + DEBIL * _coincidencias(plano, sueltas, tema["claves"]))


def enrutar(texto, preguntas):
    """Índice de la pregunta de `preguntas` que mejor responde a `texto`, o None si ninguna alcanza.

    `preguntas` es la lista [(pregunta, respuesta)] que arma respuestas.py para esa parcela: sólo se enruta a lo que
    de verdad está disponible, así que nunca se ofrece una respuesta que esa parcela no tiene."""
    if not texto or not str(texto).strip():
        return None
    mejor, mejor_puntos = None, 0
    for indice, (pregunta, _) in enumerate(preguntas):
        tema = next((t for t in TEMAS if pregunta.startswith(t["prefijo"])), None)
        if tema is None:
            continue
        p = _puntos(texto, tema)
        if p > mejor_puntos:
            mejor, mejor_puntos = indice, p
    return mejor if mejor_puntos >= MINIMO else None


def no_entendi(preguntas):
    """Lo que Cebi contesta cuando no reconoce la pregunta: dice que no sabe y ofrece lo que sí puede contar."""
    temas = ", ".join(p.rstrip("?").lstrip("¿").lower() for p, _ in preguntas[:3])
    return ("No entendí esa pregunta, y prefiero decírtelo a inventarte una respuesta. Puedo contarte, por ejemplo, "
            f"{temas}. Toca uno de los botones o pregúntamelo con otras palabras.")
