"""Contrato T02: tablas para compatibilidad; archivos auxiliares para procedencia."""
import re

DATOS_T02 = frozenset({"tablas/catalogo_parcelas.csv", "tablas/soporte_por_parcela.csv"})
PROCEDENCIA_T02 = frozenset({"tablas/huellas_archivos_leidos.csv",
                           "scripts/construir_catalogo.py", "scripts/diagnosticar_soporte.py"})
LEGADO_T02 = DATOS_T02 | PROCEDENCIA_T02


def separar_huellas(archivos, procedencia=None, schema=None):
    """Lee v1 (cinco huellas juntas) o v2 (dos tablas + tres huellas aparte).

    La procedencia identifica la revisión documentada, no una condición de
    igualdad de los scripts actuales. Las tablas y originales siguen protegidos.
    """
    if not isinstance(archivos, dict):
        raise ValueError("Contrato T02 sin las dos tablas requeridas")
    if set(archivos) == LEGADO_T02 and procedencia is None:
        datos = {n: archivos[n] for n in sorted(DATOS_T02)}
        audit = {n: archivos[n] for n in sorted(PROCEDENCIA_T02)}
        version = "t04_referencia_t02_v1"
    elif set(archivos) == DATOS_T02 and isinstance(procedencia, dict) and set(procedencia) == PROCEDENCIA_T02:
        datos, audit = dict(archivos), dict(procedencia)
        version = "t04_referencia_t02_v2"
    else:
        raise ValueError("Contrato T02 requiere dos tablas y procedencia completa, sin archivos adicionales")
    if schema is not None and schema != version:
        raise ValueError("Esquema de referencia T02 desconocido o contradictorio")
    if any(not isinstance(h, str) or re.fullmatch(r"[0-9a-f]{64}", h) is None
           for h in (*datos.values(), *audit.values())):
        raise ValueError("Huella SHA256 T02 inválida")
    return datos, audit
