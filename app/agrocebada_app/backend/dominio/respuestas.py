"""Respuestas de «Pregúntale a Cebi» (M19). Preguntas fijas con respuestas armadas de plantillas: reúnen en lenguaje
simple lo que está repartido en la pantalla (desglose M04, confianza M01, rango M02, calculadora M05, clima M07,
«Tu libreta») y añaden lo que la pantalla no dice: por qué el vecino tiene el mismo número, cuántas toneladas son
en toda la parcela, de cuánto puede fallar el número en su cosecha, cómo quedó frente a su municipio y qué haría
más precisa la cifra. Todo sale del dato: no hay cifras escritas a mano ni modelo de lenguaje."""
from agrocebada_app.backend.dominio.bitacora import faltan_para_subir
from agrocebada_app.backend.dominio.bitacora import resumen as resumen_libreta
from agrocebada_app.backend.dominio.calculadora import cuentas, equilibrio, frase_equilibrio
from agrocebada_app.backend.dominio.clima_anomalia import comparar, frases
from agrocebada_app.backend.dominio.desglose import NO_ENTRA, NO_VE, desglose
from agrocebada_app.backend.dominio.franja_verdor import frase_verdor
from agrocebada_app.backend.dominio.rangos import ANIO, rango_de
from agrocebada_app.backend.modelo.estimador import estadistico

P_CLIMA = "¿Cómo estuvo el clima este año en mi zona?"
P_MEJORAR = "¿Qué haría más precisa mi cifra?"
P_NO_SABE = "¿Qué no sabe la app de mi parcela?"
P_SATELITE = "¿Cómo se vio mi parcela desde el satélite?"
P_MARGEN = "¿De cuánto puede fallar mi número?"
P_LIBRETA = "¿Cómo me fue en los años que anoté?"
# las únicas que hablan de clima, de verdor o de lo que no entra al cálculo
CONTEXTO = (P_CLIMA, P_MEJORAR, P_NO_SABE, P_SATELITE)
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
    estad = "el valor típico (la mediana)" if modelo.startswith("mediana") else "el promedio"
    if p.fuente == "municipio":
        n = int(p.n_municipio)
        if n == 1:
            return f"Se tomó el rendimiento de la única parcela con cosecha registrada de {municipio} en {ANIO}."
        return f"Se tomó {estad} de las {n} parcelas con cosecha registrada de {municipio} en {ANIO}."
    de = "su grupo de registro" if p.fuente == "grupo" else "toda la región"
    return (f"Tu municipio no tiene parcelas con cosecha suficientes, así que se tomó {estad} de las parcelas "
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


def _n_cosecha(d, municipio):
    """Parcelas con cosecha registrada del municipio (lo mismo que cuenta M01)."""
    return int(d.loc[(d.municipio == municipio) & (d.CONJUNTO == "ENTRENAMIENTO"), "real"].notna().sum())


def _cuanto_falta(n, municipio):
    """Frase con lo que calcula «Tu libreta» (faltan_para_subir): la misma regla de M01, sin repetir la cuenta."""
    f = faltan_para_subir(n)
    if f["siguiente"] is None:
        return (f"{municipio[:1].upper() + municipio[1:]} ya tiene parcelas suficientes: su confianza depende de qué "
                "tan bien acierta el método ahí, no de sumar más parcelas.")
    parcelas = f"{f['faltan']} parcela{'s' if f['faltan'] != 1 else ''}"
    frase = (f"Con {parcelas} más con cosecha registrada, {municipio} pasaría de confianza {f['nivel']} a "
             f"{f['siguiente']}")
    if f["condicionado"]:
        frase += ", siempre que el error ahí quede igual o por debajo del promedio"
    return frase + "."


def _mejorar(d, municipio):
    """Qué no conoce la app, qué haría más precisa la cifra y cuánto le falta al municipio para subir de confianza."""
    n = _n_cosecha(d, municipio)
    return (f"La app no conoce tu {NO_VE}. Lo que más ayudaría es registrar tu cosecha al terminar la temporada; "
            f"puedes anotarla en «Tu libreta», más abajo en esta página. Hoy {municipio} tiene {n} "
            f"parcela{'s' if n != 1 else ''} con cosecha registrada. {_cuanto_falta(n, 'tu municipio')}")


def _libreta(d, modelo, municipio, libreta):
    """Resumen de lo que el agricultor anotó en «Tu libreta», con el mismo cálculo y la misma referencia que la libreta."""
    cosechas = d.loc[(d.municipio == municipio) & (d.CONJUNTO == "ENTRENAMIENTO"), "real"].dropna()
    valor = float(estadistico(modelo)(cosechas)) if len(cosechas) else None
    x = resumen_libreta(libreta, valor)
    n = x["anios"]
    partes = [f"Anotaste {n} año{'s' if n != 1 else ''}. Tu promedio fue {x['promedio']:.2f} t/ha"]
    if n > 1:
        partes[0] += (f"; tu mejor año fue {x['mejor']['anio']} con {x['mejor']['rendimiento']:.2f} t/ha y el más "
                      f"bajo, {x['peor']['anio']} con {x['peor']['rendimiento']:.2f} t/ha.")
    else:
        partes[0] += "."
    if x["error_app"] is not None:
        partes.append(f"Lo que estimó la app quedó, en promedio, a {x['error_app']:.2f} t/ha de lo que anotaste.")
    if x["vs_municipio"] is not None:
        dif = x["vs_municipio"]
        ref = f"valor típico de las parcelas con cosecha de {municipio} en {ANIO} ({valor:.2f} t/ha)"
        if abs(dif) < 0.005:
            partes.append(f"Tu promedio quedó igual que el {ref}.")
        else:
            partes.append(f"Tu promedio está {abs(dif):.2f} t/ha {'arriba' if dif > 0 else 'abajo'} del {ref}.")
    return " ".join(partes)


def _produccion(rend, area, estimada):
    """Toneladas de toda la parcela. La cosecha se piensa en toneladas, no en t/ha: con la misma cifra por hectárea,
    una parcela de 0.35 ha y una de 64 ha no se parecen en nada."""
    salen = "te saldrían" if estimada else "fueron"
    return (f"Con {rend:.2f} t/ha en {area:.2f} ha, {salen} unas {rend * area:.2f} toneladas en total. "
            "Las t/ha son por hectárea; el total es lo que acabas subiendo al camión. Si sembraste otra "
            "superficie, cámbiala en la calculadora «¿Me alcanza?» de esta página y te rehago la cuenta.")


def _margen(municipio, p, area, precio):
    """El error típico del municipio en las toneladas de esta parcela, y en pesos si ya hay precio.

    Es lo que «¿Qué tanto puedo confiar?» no dice: ahí va el nivel y el rango, aquí de cuánto puede ser el golpe."""
    err = p.get("error_tipico")
    if err is None or err != err:                       # NaN: el municipio no tiene con qué medirse
        return (f"No tengo medido el error del método en {municipio}, así que prefiero no darte un número. "
                "Eso mismo es lo que te baja la confianza; toca «¿Qué tanto puedo confiar?» y te cuento por qué.")
    err, dicho = float(err), f"En {municipio} el método se equivoca en promedio"
    texto = (f"{dicho} {err:.2f} t/ha, que en tus {area:.2f} ha son unas {err * area:.2f} toneladas arriba o abajo.")
    if precio:
        texto += f" A {_dinero(precio)} por tonelada, eso es como {_dinero(err * area * float(precio))}."
    return (f"{texto} No es un tope, es un promedio: se midió estimando una por una las parcelas de tu municipio "
            "que sí tienen cosecha registrada, tapándole al método la que le tocaba estimar.")


def _satelite(d, series, pid):
    """Cómo se vio la parcela desde arriba. Es la misma frase de la tarjeta de verdor, para no contradecirla."""
    if series is None:
        return "No tengo imágenes de satélite de tu parcela para decirte cómo se vio."
    return f"{frase_verdor(d, series, pid)} Lo mide el satélite por el verde de la planta, semana a semana. {NO_ENTRA}"


def saludo(d, pred, modelo, conf, pid):
    """Primera burbuja de Cebi: el resumen de la parcela en una frase."""
    r = d.loc[pid]
    if r.CONJUNTO == "PREDICCION":
        x = desglose(d, pred, modelo, conf, pid)
        return (f"Hola, soy Cebi. Tu parcela {pid} tiene una estimación de {x['estimacion']:.2f} t/ha, con confianza "
                f"{x['nivel']}. ¿Qué quieres saber?")
    return f"Hola, soy Cebi. Tu parcela {pid} tiene su cosecha registrada: {r.real:.2f} t/ha en {ANIO}. ¿Qué quieres saber?"


def respuestas(d, pred, modelo, conf, pid, oof=None, precio=None, costo=None, area=None, clima=None, normal=None,
               series=None, libreta=None):
    """Lista [(pregunta, respuesta)] para `pid`. Cambia si la parcela está por estimar o ya tiene cosecha.
    `precio`, `costo` y `area` vienen de la calculadora (M05); `clima` y `normal`, de M07; `series`, de M06;
    `libreta`, de «Tu libreta» (si el agricultor anotó cosechas aparece una pregunta más)."""
    r = d.loc[pid]
    area = area or float(r.AREA_HA)
    if r.CONJUNTO == "PREDICCION":
        x = desglose(d, pred, modelo, conf, pid)
        p = pred.loc[pid]
        est = x["estimacion"]
        sin_rango = rango_de(d, r.municipio)["tipo_rango"] == "sin rango"
        confiar = f"{x['motivo']} " + ("Por eso tampoco hay un rango de cosechas para comparar." if sin_rango
                                       else x["rango"])
        if x["nivel"] != "alta":
            confiar += f" {_cuanto_falta(_n_cosecha(d, r.municipio), 'tu municipio')}"
        lista = [
            (f"¿Por qué mi parcela tiene {est:.2f}?", f"{_como(r.municipio, p, modelo)} {x['frase']}"),
            ("¿Cuántas toneladas me van a salir?", _produccion(float(p.prediccion), area, True)),
            ("¿Por qué mi vecino tiene el mismo número?", _vecinos(d, pred, pid, est)),
            ("¿Qué tanto puedo confiar?", confiar),
            (P_MARGEN, _margen(r.municipio, p, area, precio)),
            ("¿Me alcanza para mis costos?", _costos(d, r.municipio, float(p.prediccion), precio, costo, area)),
            (P_SATELITE, _satelite(d, series, pid)),
            (P_CLIMA, _clima(clima, normal, pid)),
            (P_MEJORAR, _mejorar(d, r.municipio)),
        ]
    else:
        dio = _posicion(d, pid)
        if oof is not None and pid in oof.index:
            dio += f" Si no la conociera, el método habría estimado {oof[pid]:.2f} t/ha ({oof[pid] - r.real:+.2f})."
        lista = [
            ("¿Cómo le fue a mi parcela frente a las de mi municipio?", dio),
            ("¿Cuántas toneladas saqué en total?", _produccion(float(r.real), area, False)),
            ("¿Entre qué valores quedaron las de mi municipio?", rango_de(d, r.municipio)["texto"]),
            ("¿Me alcanza para mis costos?", _costos(d, r.municipio, float(r.real), precio, costo, area)),
            (P_SATELITE, _satelite(d, series, pid)),
            (P_CLIMA, _clima(clima, normal, pid)),
            (P_NO_SABE, f"No conoce tu {NO_VE}: sólo usa las cosechas registradas. {NO_ENTRA}"),
        ]
    if libreta is not None and not libreta.empty:
        lista.append((P_LIBRETA, _libreta(d, modelo, r.municipio, libreta)))
    return lista
