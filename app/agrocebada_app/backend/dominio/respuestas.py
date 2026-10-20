"""Respuestas de «Pregúntale a Cebi» (M19). Preguntas fijas con respuestas armadas de plantillas: reúnen en lenguaje
simple lo que está repartido en la pantalla (desglose M04, confianza M01, rango M02, calculadora M05, clima M07,
«Tu libreta») y añaden lo que la pantalla no dice: por qué el vecino tiene el mismo número, cuántas toneladas son
en toda la parcela, de cuánto puede fallar el número en su cosecha, cómo quedó frente a su municipio y qué haría
más precisa la cifra. Todo sale del dato: no hay cifras escritas a mano ni modelo de lenguaje."""
from agrocebada_app.backend.dominio.bitacora import faltan_para_subir
from agrocebada_app.backend.dominio.bitacora import resumen as resumen_libreta
from agrocebada_app.backend.dominio.calculadora import frase_equilibrio
from agrocebada_app.backend.dominio.clima_anomalia import comparar, frases
from agrocebada_app.backend.dominio.desglose import NO_ENTRA, NO_VE, desglose
from agrocebada_app.backend.dominio.franja_verdor import frase_verdor
from agrocebada_app.backend.dominio.planeador import escenarios_cuenta, evaluar_cuenta, importe, plan_si_sale_mal
from agrocebada_app.backend.dominio.rangos import ANIO, rango_de
from agrocebada_app.backend.modelo.estimador import estadistico

P_CLIMA = "¿Cómo estuvo el clima este año en mi zona?"
P_MEJORAR = "¿Qué haría más precisa mi cifra?"
P_NO_SABE = "¿Qué no sabe la app de mi parcela?"
P_SATELITE = "¿Cómo se vio mi parcela desde el satélite?"
P_MARGEN = "¿De cuánto puede fallar mi número?"
P_LIBRETA = "¿Cómo me fue en los años que anoté?"
# las tres de «Mi cuenta»: salen de la misma cuenta que la calculadora «¿Me alcanza?» (planeador)
P_EQUILIBRIO = "¿Cuánto necesito sacar para no perder?"
P_ESCENARIOS = "¿Qué pasa si el año sale bajo o alto?"
P_PLAN = "¿Qué hago si no me alcanza?"
# las únicas que hablan de clima, de verdor o de lo que no entra al cálculo
CONTEXTO = (P_CLIMA, P_MEJORAR, P_NO_SABE, P_SATELITE)
_TOL = 1e-9


def _dinero(x):
    return f"-${abs(x):,.0f}" if x < 0 else f"${x:,.0f}"


_PIDE_DATOS = ("Escribe tu precio por tonelada y tu costo por hectárea en la calculadora «¿Me alcanza?» de esta "
               "página y te hago la cuenta.")
_PIDE_AREA = "Escribe tu superficie en la calculadora «¿Me alcanza?» de esta página y te hago la cuenta."
_REVISA = "Revísalo en la calculadora «¿Me alcanza?» de esta página."


def _referencia_parcela(d, pred, pid):
    """(t/ha, etiqueta de la cuenta, cómo se llama) con lo que usa la calculadora para esa parcela."""
    r = d.loc[pid]
    if r.CONJUNTO == "PREDICCION":
        return float(pred.loc[pid, "prediccion"]), "Con la estimación", "tu estimación"
    return float(r.real), "Con tu cosecha registrada", "tu cosecha registrada"


def _cuenta(d, municipio, rend, etiqueta, area, precio, costo, area_pendiente=False):
    """La misma cuenta que la calculadora (evaluar_cuenta). Devuelve (mensaje, None) si todavía no hay cuenta que
    contar, o (None, (resultado, escenarios)). La superficie borrada en la calculadora cuenta como pendiente."""
    if not precio or not costo:
        return _PIDE_DATOS, None
    if area_pendiente:
        return _PIDE_AREA, None
    try:
        resultado = evaluar_cuenta(d, municipio, rend, etiqueta, area, precio, costo)
    except ValueError:
        return f"No pude hacer la cuenta con los datos que tengo. {_REVISA}", None
    if resultado["estado"] == "pendiente":
        return _PIDE_DATOS, None
    if resultado["estado"] == "invalida":
        return f"{' '.join(resultado['errores'].values())} {_REVISA}", None
    return None, (resultado, escenarios_cuenta(resultado, "Referencia"))


def _queda(s):
    """Qué le pasa al bolsillo en un escenario, con las palabras de la tarjeta de la calculadora."""
    if s["cobertura"] == "falta":
        return f"te faltarían {importe(-s['saldo'])}"
    if s["cobertura"] == "equilibrio":
        return "justo cubrirías tus costos"
    return f"te quedarían {importe(s['saldo'])}"


def _escenario(escenarios, sid):
    return next(s for s in escenarios if s["id"] == sid)


def _costos(d, municipio, rend, precio, costo, area, area_pendiente=False, etiqueta="Con la estimación"):
    """Respuesta de costos con la misma cuenta que la calculadora (M05 y planeador). Sin precio o costo, pide escribirlos."""
    previo, cuenta = _cuenta(d, municipio, rend, etiqueta, area, precio, costo, area_pendiente)
    if previo:
        return previo
    resultado, escenarios = cuenta
    ref = _escenario(escenarios, "referencia")
    if ref["cobertura"] == "falta":
        cierre = f"no cubre tus costos: faltarían {importe(-ref['saldo'])}."
    elif ref["cobertura"] == "equilibrio":
        cierre = "justo cubre tus costos."
    else:
        cierre = f"sí cubre tus costos y quedan {importe(ref['saldo'])}."
    return (f"Con {rend:.2f} t/ha en {area:.2f} ha, el ingreso sería {importe(ref['ingreso'])} contra un costo de "
            f"{importe(ref['costo'])}: {cierre} {frase_equilibrio(d, municipio, resultado['umbral'])} "
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
               series=None, libreta=None, area_pendiente=False):
    """Lista [(pregunta, respuesta)] para `pid`. Cambia si la parcela está por estimar o ya tiene cosecha.
    `precio`, `costo` y `area` vienen de la calculadora (M05); `clima` y `normal`, de M07; `series`, de M06;
    `libreta`, de «Tu libreta» (si el agricultor anotó cosechas aparece una pregunta más). `area_pendiente` es True si
    borró la superficie de la calculadora: la cuenta queda pendiente, como allá."""
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
            ("¿Me alcanza para mis costos?", _costos(d, r.municipio, float(p.prediccion), precio, costo, area,
                                         area_pendiente)),
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
            ("¿Me alcanza para mis costos?", _costos(d, r.municipio, float(r.real), precio, costo, area,
                                         area_pendiente, "Con tu cosecha registrada")),
            (P_SATELITE, _satelite(d, series, pid)),
            (P_CLIMA, _clima(clima, normal, pid)),
            (P_NO_SABE, f"No conoce tu {NO_VE}: sólo usa las cosechas registradas. {NO_ENTRA}"),
        ]
    if libreta is not None and not libreta.empty:
        lista.append((P_LIBRETA, _libreta(d, modelo, r.municipio, libreta)))
    return lista


def respuestas_cuenta(d, pred, pid, precio=None, costo=None, area=None, area_pendiente=False):
    """Las tres preguntas de «Mi cuenta» para `pid`: cuánto necesita sacar, qué pasa en un año bajo o alto y qué
    hacer si no alcanza. Salen de la misma cuenta que la calculadora «¿Me alcanza?» (evaluar_cuenta, escenarios_cuenta
    y plan_si_sale_mal): no se recalcula nada ni se redacta nada aparte. Sin precio y costo, piden escribirlos.
    Siempre devuelve tres, para que el historial de Cebi cuente desde el final y no se corra."""
    r = d.loc[pid]
    rend, etiqueta, que = _referencia_parcela(d, pred, pid)
    area = area or float(r.AREA_HA)
    previo, cuenta = _cuenta(d, r.municipio, rend, etiqueta, area, precio, costo, area_pendiente)
    if previo:
        return [(P_EQUILIBRIO, previo), (P_ESCENARIOS, previo), (P_PLAN, previo)]
    resultado, escenarios = cuenta
    ref = _escenario(escenarios, "referencia")

    posicion = {"cubre": "queda por encima de ese punto", "equilibrio": "queda justo en ese punto",
                "falta": "queda por debajo de ese punto"}[ref["cobertura"]]
    equilibrio_txt = (f"{frase_equilibrio(d, r.municipio, resultado['umbral'])} {que.capitalize()} ({rend:.2f} t/ha) "
                      f"{posicion}. Es orientativo; no es un dictamen de crédito.")

    rango = resultado["rango"]
    if len(escenarios) == 1:
        escenarios_txt = (f"{rango['texto']} Por eso no puedo darte un rendimiento bajo ni uno alto; sólo la cuenta "
                          f"con {que}.")
    else:
        extremos = rango["tipo_rango"] == "mínimo–máximo"
        bajo, alto = _escenario(escenarios, "bajo"), _escenario(escenarios, "alto")
        escenarios_txt = " ".join([
            rango["texto"],
            f"Con {'el menor rendimiento registrado' if extremos else 'un rendimiento bajo'} de tu municipio "
            f"({bajo['rendimiento_t_ha']:.2f} t/ha) {_queda(bajo)}.",
            f"Con {que} ({rend:.2f} t/ha) {_queda(ref)}.",
            f"Con {'el mayor rendimiento registrado' if extremos else 'un rendimiento alto'} de tu municipio "
            f"({alto['rendimiento_t_ha']:.2f} t/ha) {_queda(alto)}.",
            f"Son referencias de lo que pasó en {ANIO}; no dicen cuál te tocará."])

    plan = plan_si_sale_mal(escenarios)
    intro = plan["apertura"] if plan["estado"] == "falta" else (
        f"{plan['apertura']} Si tus números cambian y llegara a faltarte, esto ayuda:")
    pasos = "\n".join(f"{i}. {paso}" for i, paso in enumerate(plan["pasos"], 1))
    return [(P_EQUILIBRIO, equilibrio_txt), (P_ESCENARIOS, escenarios_txt),
            (P_PLAN, f"{intro}\n{pasos}\n{plan['nota']}")]
