"""Respuestas de «Pregúntale a Cebi» (M19). Preguntas fijas con respuestas armadas de plantillas: reúnen en lenguaje
simple lo que está repartido en la pantalla (desglose M04, confianza M01, rango M02, calculadora M05, clima M07) y
añaden lo que la pantalla no dice: por qué el vecino tiene el mismo número, cómo quedó la parcela frente a su
municipio y qué haría más precisa la cifra. Todo sale del dato: no hay cifras escritas a mano ni modelo de lenguaje."""
from agrocebada_app.backend.dominio.calculadora import cuentas, equilibrio, frase_equilibrio
from agrocebada_app.backend.dominio.clima_anomalia import comparar, frases
from agrocebada_app.backend.dominio.desglose import NO_ENTRA, NO_VE, desglose
from agrocebada_app.backend.dominio.rangos import ANIO, rango_de

P_CLIMA = "¿Cómo estuvo el clima este año en mi zona?"
P_MEJORAR = "¿Qué haría más precisa mi cifra?"
P_NO_SABE = "¿Qué no sabe la app de mi parcela?"
CONTEXTO = (P_CLIMA, P_MEJORAR, P_NO_SABE)   # las únicas que hablan de clima o de lo que no entra al cálculo
_TOL = 1e-9


def _dinero(x):
    return f"-${abs(x):,.0f}" if x < 0 else f"${x:,.0f}"


def _costos(d, municipio, rend, precio, costo, area):
    """Respuesta de costos con la misma cuenta que la calculadora (M05). Sin precio o costo, pide escribirlos."""
    if not precio or not costo or not area:
        return ("Escribe tu precio por tonelada y tu costo por hectárea en la calculadora «¿Me alcanza?» de esta "
                "página y te hago la cuenta.")
    c = cuentas([("x", rend)], area, precio, costo)["x"]
    dif = c["Ingreso menos costo"]
    if c["¿Cubre costos?"] == "Sí":
        cierre = f"sí cubre tus costos y quedan {_dinero(dif)}."
    else:
        cierre = f"no cubre tus costos: faltarían {_dinero(-dif)}."
    return (f"Con {rend:.2f} t/ha en {area:.2f} ha, el ingreso sería {_dinero(c['Ingreso'])} contra un costo de "
            f"{_dinero(c['Costo'])}: {cierre} {frase_equilibrio(d, municipio, equilibrio(precio, costo))} "
            "Es orientativo; no es un dictamen de crédito.")


def _como(municipio, p, modelo):
    """De dónde salió la estimación (municipio, grupo o región)."""
    estad = "mediana" if modelo.startswith("mediana") else "promedio"
    if p.fuente == "municipio":
        n = int(p.n_municipio)
        if n == 1:
            return f"Se tomó el rendimiento de la única parcela con cosecha registrada de {municipio} en {ANIO}."
        return f"Se tomó la {estad} de las {n} parcelas con cosecha registrada de {municipio} en {ANIO}."
    de = "su grupo de registro" if p.fuente == "grupo" else "toda la región"
    return (f"Tu municipio no tiene parcelas con cosecha suficientes, así que se tomó la {estad} de las parcelas "
            f"con cosecha de {de} en {ANIO}.")


def _vecinos(d, pred, pid, est):
    """Por qué las parcelas por estimar del mismo municipio tienen el mismo número."""
    m = d.loc[pid, "municipio"]
    mismas = [i for i in pred.index if d.loc[i, "municipio"] == m]
    iguales = sum(round(float(pred.loc[i, "prediccion"]), 2) == est for i in mismas)
    if len(mismas) == 1:
        return (f"Tu parcela es la única por estimar en {m}. Si hubiera otras, recibirían el mismo número: el método "
                "sólo usa las cosechas registradas de tu municipio y no distingue una parcela de otra.")
    if iguales == len(mismas):
        return (f"Porque las {len(mismas)} parcelas por estimar de {m} reciben el mismo número, {est:.2f} t/ha. "
                "El método sólo usa las cosechas registradas de tu municipio: no distingue una parcela de otra.")
    return (f"De las {len(mismas)} parcelas por estimar de {m}, {iguales} reciben {est:.2f} t/ha. El método usa las "
            "cosechas registradas de tu municipio, no datos de cada parcela.")


def _posicion(d, pid):
    """Cómo quedó una parcela con cosecha frente a las demás con cosecha de su municipio."""
    r = d.loc[pid]
    otras = d.loc[(d.municipio == r.municipio) & (d.CONJUNTO == "ENTRENAMIENTO") & (d.index != pid), "real"].dropna()
    base = f"Tu parcela dio {r.real:.2f} t/ha en {ANIO}."
    if otras.empty:
        return f"{base} Es la única con cosecha registrada en {r.municipio}, así que no hay con quién compararla."
    menos = int((otras < r.real - _TOL).sum())
    mas = int((otras > r.real + _TOL).sum())
    return f"{base} De las otras {len(otras)} parcelas con cosecha de {r.municipio}, {menos} dieron menos y {mas} dieron más."


def _clima(clima, normal, pid):
    """Frases de clima de M07, aclarando que no cambian la estimación."""
    t = comparar(clima, normal, pid)
    if t is None:
        return "No tengo el clima de tu zona para comparar."
    lista = frases(t) or ["La lluvia y la temperatura quedaron cerca del promedio 2022–2024 en tu zona."]
    return " ".join(lista) + " Es contexto: no cambia tu estimación."


def _mejorar(d, municipio):
    """Qué no conoce la app y qué haría más precisa la cifra."""
    n = int(d.loc[(d.municipio == municipio) & (d.CONJUNTO == "ENTRENAMIENTO"), "real"].notna().sum())
    return (f"La app no conoce tu {NO_VE}. Lo que más ayudaría es registrar tu cosecha al terminar la temporada: hoy "
            f"{municipio} tiene {n} parcela{'s' if n != 1 else ''} con cosecha registrada. Con más cosechas registradas "
            "la cifra de tu municipio se vuelve más firme, y con datos de cada parcela se podría distinguir la tuya "
            "de la de tus vecinos.")


def saludo(d, pred, modelo, conf, pid):
    """Primera burbuja de Cebi: el resumen de la parcela en una frase."""
    r = d.loc[pid]
    if r.CONJUNTO == "PREDICCION":
        x = desglose(d, pred, modelo, conf, pid)
        return (f"Hola, soy Cebi. Tu parcela {pid} tiene una estimación de {x['estimacion']:.2f} t/ha, con confianza "
                f"{x['nivel']}. ¿Qué quieres saber?")
    return f"Hola, soy Cebi. Tu parcela {pid} tiene su cosecha registrada: {r.real:.2f} t/ha en {ANIO}. ¿Qué quieres saber?"


def respuestas(d, pred, modelo, conf, pid, oof=None, precio=None, costo=None, area=None, clima=None, normal=None):
    """Lista [(pregunta, respuesta)] para `pid`. Cambia si la parcela está por estimar o ya tiene cosecha.
    `precio`, `costo` y `area` vienen de la calculadora (M05); `clima` y `normal`, de M07."""
    r = d.loc[pid]
    area = area or float(r.AREA_HA)
    if r.CONJUNTO == "PREDICCION":
        x = desglose(d, pred, modelo, conf, pid)
        p = pred.loc[pid]
        est = x["estimacion"]
        return [
            (f"¿Por qué mi parcela tiene {est:.2f}?", f"{_como(r.municipio, p, modelo)} {x['frase']}"),
            ("¿Por qué mi vecino tiene el mismo número?", _vecinos(d, pred, pid, est)),
            ("¿Qué tanto puedo confiar?", f"{x['motivo']} {x['rango']}"),
            ("¿Me alcanza para mis costos?", _costos(d, r.municipio, float(p.prediccion), precio, costo, area)),
            (P_CLIMA, _clima(clima, normal, pid)),
            (P_MEJORAR, _mejorar(d, r.municipio)),
        ]
    dio = _posicion(d, pid)
    if oof is not None and pid in oof.index:
        dio += f" Si no la conociera, el método habría estimado {oof[pid]:.2f} t/ha ({oof[pid] - r.real:+.2f})."
    return [
        ("¿Cómo le fue a mi parcela frente a las de mi municipio?", dio),
        ("¿Entre qué valores quedaron las de mi municipio?", rango_de(d, r.municipio)["texto"]),
        ("¿Me alcanza para mis costos?", _costos(d, r.municipio, float(r.real), precio, costo, area)),
        (P_CLIMA, _clima(clima, normal, pid)),
        (P_NO_SABE, f"No conoce tu {NO_VE}: sólo usa las cosechas registradas. {NO_ENTRA}"),
    ]