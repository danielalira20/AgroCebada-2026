"""Comprueba la base congelada de fase 0 sin escribir datos ni iniciar Streamlit.

Uso desde la raíz: python app/herramientas/verificar_base_planeador.py
La base se captura una sola vez al cerrar fase 0; esta herramienta no la regenera.
"""
import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "app"))

import pandas as pd  # noqa: E402

from agrocebada_app.backend.datos import paquete  # noqa: E402
from agrocebada_app.backend.dominio.calculadora import columnas, cuentas, equilibrio, rango_municipio  # noqa: E402
from agrocebada_app.backend.dominio.confianza import confianza_municipios  # noqa: E402
from agrocebada_app.backend.dominio.rangos import rangos_municipio  # noqa: E402
from agrocebada_app.backend.dominio.validacion import poblaciones  # noqa: E402
from agrocebada_app.backend.modelo.estimador import estadistico, predecir  # noqa: E402
from agrocebada_app.backend.rutas.localizador import rutas  # noqa: E402
from agrocebada_app.config import MODELO_OFICIAL, MODELOS_CANDIDATOS, PAQ, TEMPORADA  # noqa: E402

BASE = RAIZ / "docs/ai/planeador/fase-0/base.json"
SCHEMA = "agrocebada_planeador_fase0_v1"
SUPUESTOS = {"area_ha": 10.0, "precio_t": 5500.0, "costo_ha": 22000.0}


def normalizar(valor):
    """Convierte tablas y valores NumPy a JSON estricto, con ausencias como null."""
    if isinstance(valor, pd.DataFrame):
        return normalizar(valor.to_dict(orient="records"))
    if isinstance(valor, dict):
        return {str(k): normalizar(v) for k, v in valor.items()}
    if isinstance(valor, (list, tuple)):
        return [normalizar(v) for v in valor]
    if valor is None or pd.isna(valor):
        return None
    return valor.item() if hasattr(valor, "item") else valor


def observar():
    """Lee resultados del catálogo activo; no carga frontend ni módulos de Cebi."""
    d = paquete.parcelas()
    tr = d[d.CONJUNTO == "ENTRENAMIENTO"]
    modelos = {}
    for modelo in MODELOS_CANDIDATOS:
        pred = predecir(d, modelo)
        oof = paquete.validacion(modelo, d.municipio)
        if oof is None or oof.empty:
            raise ValueError(f"Falta validación para {modelo}; no se puede certificar la base.")
        oa = oof[(oof.escenario == "A") & (oof.fuente == "municipio")]
        conf = confianza_municipios(d, oa)
        referencias = tr.groupby("municipio").real.agg(estadistico(modelo))
        ejemplos = []
        for municipio, rendimiento in referencias.sort_index().items():
            tabla = cuentas(columnas(rendimiento, "Referencia municipal", rango_municipio(d, municipio)),
                            SUPUESTOS["area_ha"], SUPUESTOS["precio_t"], SUPUESTOS["costo_ha"])
            ejemplos.append({"municipio": municipio, "rendimiento": rendimiento,
                             "equilibrio_t_ha": equilibrio(SUPUESTOS["precio_t"], SUPUESTOS["costo_ha"]),
                             "cuentas": tabla.to_dict()})
        modelos[modelo] = {"predicciones_59": pred.sort_index().reset_index(),
                           "metricas": poblaciones(oof),
                           "confianza": conf.sort_values("municipio"),
                           "cuentas_ilustrativas": ejemplos}
    return normalizar({"modelo_oficial": MODELO_OFICIAL, "temporada": TEMPORADA,
                       "modo_fuentes": "paquete" if paquete.usar_paquete() else "originales",
                       "poblacion": {"total": len(d), "entrenamiento": len(tr),
                                     "prediccion": int((d.CONJUNTO == "PREDICCION").sum()),
                                     "municipios": int(d.municipio.nunique())},
                       "disponibilidad": {"clima": paquete.clima() is not None,
                                          "clima_normal": paquete.clima_normal() is not None,
                                          "calidad": paquete.calidad() is not None,
                                          "soporte": paquete.soporte() is not None},
                       "rangos": rangos_municipio(tr).sort_values("municipio"),
                       "supuestos_ilustrativos": SUPUESTOS, "modelos": modelos})


def huella(ruta):
    return hashlib.sha256(ruta.read_bytes()).hexdigest() if ruta.is_file() else None


def fuentes_activas():
    """Inventaría archivos del paquete y entregas; exige ubicaciones dentro del repo."""
    if not paquete.usar_paquete():
        raise ValueError("La captura fase 0 de este checkout requiere el paquete compacto activo.")
    archivos = [PAQ / n for n in ("parcelas.parquet", "series.parquet", "clima.parquet", "clima_normal.parquet",
                                  "validacion.parquet", "soporte.parquet", "calidad.parquet", "oficial_59.csv")]
    t18 = rutas()["t18"]
    if t18 is None:
        raise ValueError("No se encontró T18 para registrar la base de esta copia.")
    archivos += [Path(t18) / n for n in ("predicciones_finales.csv", "detalle_predicciones_59.csv", "trazabilidad.json")]
    return {p.resolve().relative_to(RAIZ).as_posix(): huella(p) for p in archivos}


def diferencias(esperado, actual, ruta="resultados"):
    """Compara estructura y cifras crudas; tolerancia 1e-12 absoluta y relativa."""
    if isinstance(esperado, dict) and isinstance(actual, dict):
        errores = []
        for clave in sorted(set(esperado) | set(actual)):
            if clave not in esperado or clave not in actual:
                errores.append(f"{ruta}.{clave}: campo ausente o adicional")
            else:
                errores.extend(diferencias(esperado[clave], actual[clave], f"{ruta}.{clave}"))
        return errores
    if isinstance(esperado, list) and isinstance(actual, list):
        if len(esperado) != len(actual):
            return [f"{ruta}: cambió la cantidad de elementos"]
        return [error for i, (a, b) in enumerate(zip(esperado, actual))
                for error in diferencias(a, b, f"{ruta}[{i}]")]
    if type(esperado) in (int, float) and type(actual) in (int, float):
        igual = math.isfinite(esperado) and math.isfinite(actual) and math.isclose(
            esperado, actual, rel_tol=1e-12, abs_tol=1e-12)
    else:
        igual = type(esperado) is type(actual) and esperado == actual
    return [] if igual else [f"{ruta}: difiere de la base congelada"]


def verificar(base):
    if base.get("schema") != SCHEMA:
        raise ValueError("Esquema de base desconocido.")
    errores = diferencias(base["fuentes_sha256"], fuentes_activas(), "fuentes_sha256")
    errores.extend(diferencias(base["resultados"], observar()))
    return errores


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=Path, default=BASE)
    args = parser.parse_args()
    try:
        base = json.loads(args.base.read_text(encoding="utf-8"))
        errores = verificar(base)
    except (OSError, ValueError, KeyError, TypeError) as ex:
        print(f"NO VERIFICADO: {ex}", file=sys.stderr)
        return 1
    if errores:
        print("NO COINCIDE:\n" + "\n".join(errores[:25]), file=sys.stderr)
        return 1
    print("OK: base fase 0 conservada (197/138/59, ambos modelos, métricas, rangos, confianza y cuentas).")
    print("La coincidencia no aprueba T16 ni certifica la huella histórica de T18; ver pendientes de fase 0.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
