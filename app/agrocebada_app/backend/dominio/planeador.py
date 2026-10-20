"""Referencias municipales y preparación de cuentas sin depender de una parcela."""
from numbers import Real

import numpy as np

from agrocebada_app.backend.dominio.calculadora import _TOL, columnas, cuentas, equilibrio, rango_municipio
from agrocebada_app.backend.modelo.estimador import estadistico
from agrocebada_app.config import MODELOS_CANDIDATOS, TEMPORADA


def _finito(valor):
    if isinstance(valor, (bool, np.bool_)) or not isinstance(valor, Real):
        return False
    try:
        return bool(np.isfinite(valor))
    except (TypeError, OverflowError):
        return False


def _entrenamiento(d):
    tr = d[d.CONJUNTO == "ENTRENAMIENTO"]
    if any(not _finito(v) or v <= 0 for v in tr.real):
        raise ValueError("Las cosechas registradas deben ser números finitos y positivos.")
    return tr


def municipios_disponibles(d):
    """Catálogo con cosechas locales válidas, independiente de las parcelas por estimar."""
    return sorted(_entrenamiento(d).municipio.dropna().unique())


def estimacion_municipio(d, municipio, modelo):
    """Referencia histórica local; sin cosechas devuelve sin_soporte, sin respaldo de otras zonas."""
    if modelo not in MODELOS_CANDIDATOS:
        raise ValueError("El modelo no es uno de los candidatos del proyecto.")
    tr = _entrenamiento(d)
    cosechas = tr.loc[tr.municipio == municipio, "real"]
    n = len(cosechas)
    rendimiento = float(estadistico(modelo)(cosechas)) if n else None
    if rendimiento is not None and not np.isfinite(rendimiento):
        raise ValueError("No se pudo calcular una referencia municipal finita.")
    return {"estado": "disponible" if n else "sin_soporte", "municipio": municipio,
            "campania_base": int(TEMPORADA[0][:4]), "modelo": modelo,
            "rendimiento_t_ha": rendimiento, "fuente": "municipio" if n else None,
            "n_cosecha_municipio": n, "n_cosecha_fuente": n}


def evaluar_cuenta(d, municipio, rendimiento, etiqueta, area, precio, costo):
    """Valida captura y compone las cuentas existentes; no formatea ni modifica los datos."""
    errores = {}
    pendiente = False
    for campo, valor in (("area", area), ("precio", precio), ("costo", costo)):
        if valor is None:
            pendiente = True
        elif not _finito(valor):
            errores[campo] = "Escribe un número finito válido."
        elif valor < 0 or (campo == "area" and valor < 0.01):
            errores[campo] = "La superficie mínima es 0.01 ha." if campo == "area" else "Escribe un valor mayor que cero."
        elif valor == 0:
            pendiente = True
    resultado = {"estado": "invalida" if errores else "pendiente", "errores": errores,
                 "tabla": None, "rango": None, "umbral": None}
    if errores or pendiente:
        return resultado
    if not _finito(rendimiento) or rendimiento <= 0:
        raise ValueError("La referencia de rendimiento debe ser finita y positiva.")
    _entrenamiento(d)
    rango = rango_municipio(d, municipio)
    with np.errstate(over="ignore", invalid="ignore"):
        tabla = cuentas(columnas(rendimiento, etiqueta, rango), area, precio, costo)
        umbral = equilibrio(precio, costo)
    if not np.isfinite(tabla.iloc[:5].to_numpy(dtype=float)).all() or not np.isfinite(umbral):
        resultado.update(estado="invalida", errores={"cuenta": "Los valores son demasiado grandes para calcular la cuenta."})
        return resultado
    return {"estado": "calculada", "errores": {}, "tabla": tabla, "rango": rango, "umbral": umbral}


def cobertura_saldo(saldo):
    if not _finito(saldo):
        raise ValueError("El saldo debe ser finito.")
    return "equilibrio" if abs(saldo) <= _TOL else "falta" if saldo < 0 else "cubre"


def importe(valor):
    """Pesos con signo; conserva centavos y evita presentar un faltante pequeño como cero."""
    if not _finito(valor):
        raise ValueError("El importe debe ser finito.")
    magnitud = abs(valor)
    if magnitud <= _TOL:
        return "$0"
    if magnitud < 0.005:
        return "entre -$0.01 y $0" if valor < 0 else "menos de $0.01"
    return f"{'-' if valor < 0 else ''}${magnitud:,.2f}" if magnitud < 1 else f"{'-' if valor < 0 else ''}${magnitud:,.0f}"


def escenarios_cuenta(resultado, etiqueta_referencia):
    """Adapta la tabla existente a tarjetas; no recalcula ni redondea sus cantidades."""
    if resultado["estado"] != "calculada":
        return []
    tabla, rango = resultado["tabla"], resultado["rango"]
    etiquetas = {"referencia": etiqueta_referencia}
    extremos = rango["tipo_rango"] == "mínimo–máximo"
    etiquetas.update(bajo="Menor rendimiento registrado" if extremos else "Rendimiento bajo",
                     alto="Mayor rendimiento registrado" if extremos else "Rendimiento alto")
    indices = [("bajo", 1), ("referencia", 0), ("alto", 2)] if len(tabla.columns) == 3 else [("referencia", 0)]
    escenarios = []
    for sid, i in indices:
        columna = tabla.columns[i]
        fila = tabla[columna]
        saldo = float(fila["Ingreso menos costo"])
        escenarios.append({"id": sid, "etiqueta": etiquetas[sid], "columna": columna,
                           "rendimiento_t_ha": float(fila["Rendimiento (t/ha)"]),
                           "produccion_t": float(fila["Producción (t)"]), "ingreso": float(fila["Ingreso"]),
                           "costo": float(fila["Costo"]), "saldo": saldo, "cobertura": cobertura_saldo(saldo)})
    return escenarios


def posiciones_barra(escenarios, umbral):
    """Posiciones reales 0–100; detecta marcas juntas para usar su alternativa textual."""
    if len(escenarios) < 3:
        return None
    if not _finito(umbral) or umbral < 0:
        raise ValueError("El equilibrio debe ser finito y no negativo.")
    marcas = [{"id": s["id"], "etiqueta": s["etiqueta"], "valor": s["rendimiento_t_ha"]} for s in escenarios]
    marcas.append({"id": "equilibrio", "etiqueta": "Punto de equilibrio", "valor": umbral})
    valores = [m["valor"] for m in marcas]
    if any(not _finito(v) or v < 0 for v in valores) or max(valores) <= 0:
        raise ValueError("Las marcas deben tener rendimientos finitos y no negativos.")
    escala = max(valores)
    minimo = min(v / escala for v in valores)
    amplitud = 1 - minimo
    for i, marca in enumerate(marcas, 1):
        marca.update(numero=i, posicion=50.0 if amplitud == 0 else
                     max(0.0, min(100.0, 100 * (marca["valor"] / escala - minimo) / amplitud)))
    posiciones = sorted(m["posicion"] for m in marcas)
    legible = all(b - a >= 6 for a, b in zip(posiciones, posiciones[1:]))
    return {"minimo": min(valores), "maximo": max(valores), "marcas": marcas, "legible": legible}


PASOS_FALTANTE = (
    "Anota el faltante calculado y los números de precio, costo y superficie que usaste.",
    "Revisa tus gastos y conserva tus registros de la campaña.",
    "Comenta estas cuentas con tu asesor técnico y revisa qué opciones existen para tu caso.",
)
NOTA_ORIENTACION = "Orientación general basada en tus supuestos; no garantiza apoyos ni resultados de cosecha."


def plan_si_sale_mal(escenarios):
    """Usa el escenario bajo disponible, o la referencia identificada si no hay rango."""
    if not escenarios:
        return None
    escenario = next((s for s in escenarios if s["id"] == "bajo"),
                     next(s for s in escenarios if s["id"] == "referencia"))
    saldo, estado = escenario["saldo"], escenario["cobertura"]
    inicio = ("Con el escenario bajo basado en parcelas de 2025" if escenario["id"] == "bajo"
              else "Con la única referencia disponible")
    cierre = (f"te faltarían {importe(-saldo)}." if estado == "falta" else
              "justo cubrirías tus costos." if estado == "equilibrio" else "cubrirías tus costos.")
    return {"estado": estado, "escenario_id": escenario["id"], "saldo": saldo,
            "faltante": max(0.0, -saldo) if estado == "falta" else 0.0, "abierto": estado == "falta",
            "titulo": "Si este escenario no cubre tus costos", "apertura": f"{inicio} y tus números, {cierre}",
            "pasos": list(PASOS_FALTANTE), "nota": NOTA_ORIENTACION}
