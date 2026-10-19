"""Alcance del método (M15): los cuatro pasos con el modelo final, la tabla «¿A qué parcelas sirve?» y los límites. Es lógica sin Streamlit: la pantalla la dibuja frontend/vistas/analista/pestanas/metodo_limites.py. Ninguna cifra
se escribe a mano: los errores salen de la misma validación de Validación (M12), los umbrales de la regla de confianza
(M01) y los conteos de las estimaciones reales."""
import pandas as pd

from agrocebada_app.backend.dominio.confianza import MIN_ALTA, MIN_MEDIA
from agrocebada_app.backend.dominio.desglose import NO_ENTRA, NO_VE
from agrocebada_app.backend.dominio.validacion import ESCENARIOS, SUBCONJUNTOS, contraste_respaldo, poblaciones
from agrocebada_app.config import MODELO_OFICIAL

SI, CAUTELA, MUCHA, PARCIAL, NO = "✔ Sí", "▲ Con cautela", "⚠ Con mucha cautela", "▲ Parcialmente", "✖ No"
COLUMNAS = ["situacion", "sirve", "error", "estimaciones", "nota"]


def pasos(d, oficial=MODELO_OFICIAL):
    """Los cuatro pasos del método, descritos con el modelo final (no con el que el analista tenga elegido)."""
    tr = d[d.CONJUNTO == "ENTRENAMIENTO"]
    estad = "mediana" if oficial.startswith("mediana") else "media"
    return [("Datos", f"{len(tr)} parcelas con cosecha registrada en 2025, de {tr.municipio.nunique()} municipios."),
            ("Valor típico del municipio", f"Para cada municipio se calcula la {estad} del rendimiento de esas parcelas."),
            ("Asignación", "Cada parcela por estimar recibe el valor de su municipio. Si no hubiera datos del municipio, "
                           "se usa el de su grupo de registro y, al final, el de toda la región."),
            ("Validación", "Se repite el cálculo dejando fuera parcelas conocidas (validación cruzada 5 × 5, escenario A) "
                           "y zonas de lluvia completas (escenario B), con un procedimiento definido antes de ver los "
                           "resultados.")]


def _fila_poblacion(pob, esc, sub):
    f = pob[pob.poblacion == f"{ESCENARIOS[esc]} · {SUBCONJUNTOS[sub]}"]
    return None if f.empty else f.iloc[0]


def error_principal(O):
    """Errores de la validación que muestra «Qué tan bien funciona», de las mismas poblaciones que Validación (M12):
    A · sin respaldo (la que corresponde a las 59) y B · sin respaldo. None si no hay validación."""
    if O is None or O.empty:
        return None
    pob = poblaciones(O)
    a, b = _fila_poblacion(pob, "A", "sin respaldo"), _fila_poblacion(pob, "B", "sin respaldo")
    if a is None:
        return None
    return {"a_mae": float(a.MAE), "a_r2": float(a.R2), "a_parcelas": int(a.parcelas),
            "b_mae": None if b is None else float(b.MAE), "b_parcelas": None if b is None else int(b.parcelas)}


def por_que_simple(oficial=MODELO_OFICIAL):
    """Por qué un modelo simple, sin decir cuántas variantes se probaron: eso está en la pestaña Evidencia."""
    base = ("Se compararon alternativas con más información (índices de satélite, clima, relieve y área) y ninguna pasó la "
            "regla de promoción frente al valor típico del municipio.")
    if oficial.startswith("mediana"):
        base += (" La mediana tampoco la pasó: se adoptó como excepción explícita por tener el menor error, no como una "
                 "mejora confirmada.")
    else:
        base += " Se conserva el promedio del municipio."
    return base + " El detalle está en la pestaña Evidencia."


def limites():
    """Límites de la estimación, sin suavizar."""
    return ["Es el valor típico del municipio: dos parcelas vecinas del mismo municipio reciben la misma cifra.",
            f"El método no ve {NO_VE}; sin esa información no puede distinguir una parcela de otra dentro de su municipio.",
            NO_ENTRA + " Tampoco son mediciones de campo.",
            "El clima viene en píxeles de ~5.5 km: no distingue parcelas cercanas.",
            "Algunos rendimientos registrados vienen redondeados.",
            "El rendimiento no indica calidad maltera ni capacidad de pago.",
            "Toda cifra es una estimación retrospectiva de 2025, validada con las mismas cosechas: no es una predicción "
            "de otra temporada.",
            "La app no conoce el rendimiento real de las 59 parcelas por estimar; el error que muestra sale de las parcelas "
            "con cosecha registrada."]


def _cuantas(n, total):
    if n == 0:
        return f"Ninguna de las {total}"
    return f"{n} de las {total}" if n != total else f"Las {total}"


def tabla_alcance(O, conf, pred):
    """Cinco filas: a qué parcelas sirve la cifra y a cuáles no. `O`: validación del modelo vigente; `conf`: confianza
    por municipio (M01); `pred`: las estimaciones reales. Los umbrales son los de la regla de confianza. Devuelve una
    lista de diccionarios con las columnas de COLUMNAS, o [] si no hay validación."""
    if O is None or O.empty:
        return []
    pob = poblaciones(O)
    a, b = _fila_poblacion(pob, "A", "sin respaldo"), _fila_poblacion(pob, "B", "sin respaldo")
    b_todas = _fila_poblacion(pob, "B", "todas")
    if a is None:
        return []
    total = len(pred)
    n = pred.municipio.map(conf.set_index("municipio").n_cosecha).fillna(0).astype(int)
    respaldo = contraste_respaldo(O, pred)
    err_a = f"{a.MAE:.3f} t/ha en municipios con cosechas conocidas (A · sin respaldo)"
    if b is None:
        err_b = "No se pudo medir en la validación."
    else:
        mas = f" Contando todas las predicciones de B sube a {b_todas.MAE:.3f} t/ha." if (
            b_todas is not None and b_todas.MAE > b.MAE) else ""
        err_b = f"{b.MAE:.3f} t/ha en zonas de lluvia nuevas (B · sin respaldo).{mas}"
    err_r = (f"{respaldo['mae']:.3f} t/ha cuando el municipio no tenía cosechas conocidas" if pd.notna(respaldo["mae"])
             else "Sin validación propia: no hay otras parcelas para comparar.")
    ninguno = int((n == 0).sum())
    return [
        {"situacion": f"Misma temporada (2025), cebada de temporal y un municipio con {MIN_ALTA} o más parcelas con cosecha",
         "sirve": SI, "error": err_a, "estimaciones": _cuantas(int((n >= MIN_ALTA).sum()), total),
         "nota": "La confianza baja a media si el error de ese municipio fue mayor al general."},
        {"situacion": f"Municipio con {MIN_MEDIA} a {MIN_ALTA - 1} parcelas con cosecha", "sirve": CAUTELA,
         "error": f"El error general es {a.MAE:.3f} t/ha, pero con pocas parcelas el valor del municipio es menos firme.",
         "estimaciones": _cuantas(int(((n >= MIN_MEDIA) & (n < MIN_ALTA)).sum()), total),
         "nota": "Una parcela atípica mueve el valor de todo el municipio."},
        {"situacion": f"Municipio con {MIN_MEDIA - 1} o menos parcelas con cosecha", "sirve": MUCHA, "error": err_r,
         "estimaciones": _cuantas(int(((n > 0) & (n < MIN_MEDIA)).sum()), total),
         "nota": "No alcanza para comparar: la confianza es baja por falta de evidencia."},
        {"situacion": "Municipio nuevo dentro de la región, sin cosechas propias", "sirve": PARCIAL, "error": err_b,
         "estimaciones": _cuantas(ninguno, total),
         "nota": "Se usa el valor de otras zonas; el error es mayor que cuando hay datos del municipio."},
        {"situacion": "Otro año, otro estado, riego u otro cultivo", "sirve": NO,
         "error": "No se validó: el método sólo usa cosechas de 2025.", "estimaciones": "—",
         "nota": "No hay evidencia para decir qué tan cerca estaría la cifra."},
    ]
