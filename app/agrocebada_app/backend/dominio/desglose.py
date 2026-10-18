"""Desglose de una estimación (M04): de dónde sale el número de una parcela por estimar. Parte del valor de toda la
región (el mismo estadístico del modelo: media o mediana de las parcelas con cosecha), suma lo que cambia por el
municipio y llega a la estimación. Nada se escribe a mano: todo sale del modelo vigente, así que al cambiar de modelo
cambian la base y la diferencia. No dibuja nada: la pantalla y la pregunta a Cebi (M16) leen este mismo resultado."""
from agrocebada_app.backend.dominio.confianza import confianza_parcela
from agrocebada_app.backend.dominio.rangos import rango_de
from agrocebada_app.backend.modelo.estimador import estadistico

NO_VE = "fecha de siembra, variedad y manejo"
NO_ENTRA = "El área, la altitud, la lluvia y el verdor son contexto: no entran al cálculo."


def valor_base(d, modelo):
    """Valor de toda la región: el estadístico del modelo sobre las parcelas con cosecha (sin redondear)."""
    return float(estadistico(modelo)(d.loc[d.CONJUNTO == "ENTRENAMIENTO", "real"].dropna()))


def _signo(x):
    return "0.00" if x == 0 else f"{x:+.2f}"


def _frase(nombre, base, ajuste, estimacion, fuente, motivo_ajuste):
    if fuente == "global":
        return (f"Como no hay cosechas de su municipio ni de su grupo de registro, se usa el valor de la región: "
                f"{estimacion:.2f} t/ha.")
    de = "de la mediana" if nombre == "Mediana" else "del promedio"
    if ajuste == 0:
        cambio = f"{motivo_ajuste} no cambia"
    else:
        cambio = f"{motivo_ajuste} se {'suma' if ajuste > 0 else 'resta'} {abs(ajuste):.2f}"
    return f"Se parte {de} de la región ({base:.2f} t/ha); {cambio} y queda en {estimacion:.2f} t/ha."


def desglose(d, pred, modelo, conf, pid):
    """Desglose de la estimación de `pid`, o None si esa parcela ya tiene su cosecha registrada. `conf`: tabla de
    confianza por municipio (M01). La diferencia se calcula con las cifras ya redondeadas (estimación menos base) para
    que lo que se ve siempre sume. Devuelve un diccionario:
      base, ajuste, estimacion  cifras redondeadas a dos decimales (t/ha)
      filas                     [(etiqueta, texto)] en orden: base, ajuste (si hay) y estimación
      frase                     el mismo desglose en una oración
      nivel, motivo             confianza de M01 (en minúscula) y su motivo
      rango                     frase del rango del municipio (M02)
      no_ve, no_entra           lo que el método no ve y lo que es sólo contexto
      fuente                    municipio, grupo o global"""
    r = d.loc[pid]
    if r.CONJUNTO != "PREDICCION":
        return None
    p = pred.loc[pid]
    fuente = str(p.fuente)
    nombre = "Mediana" if modelo.startswith("mediana") else "Promedio"
    base = round(valor_base(d, modelo), 2)
    estimacion = round(float(p.prediccion), 2)
    ajuste = round(estimacion - base, 2)
    motivo_ajuste = {"municipio": f"por estar en {r.municipio}", "grupo": "por su grupo de registro"}.get(fuente)
    etiqueta = motivo_ajuste and "P" + motivo_ajuste[1:]
    filas = [(f"{nombre} de la región", f"{base:.2f} t/ha")]
    if etiqueta:
        filas.append((etiqueta, _signo(ajuste)))
    filas.append(("Estimación", f"{estimacion:.2f} t/ha"))
    c = confianza_parcela(conf, r.municipio, fuente)
    return {"base": base, "ajuste": ajuste, "estimacion": estimacion, "filas": filas,
            "frase": _frase(nombre, base, ajuste, estimacion, fuente, motivo_ajuste),
            "nivel": c["nivel"], "motivo": c["motivo"], "rango": rango_de(d, r.municipio)["texto"],
            "no_ve": NO_VE, "no_entra": NO_ENTRA, "fuente": fuente}
