"""Comprueba ráster y geometría con ejemplos sintéticos, sin datos de FIRA."""

import argparse
import json
from importlib.metadata import version
from pathlib import Path
from platform import machine, python_version, system

import numpy as np
import rasterio
from rasterio.crs import CRS
from rasterio.io import MemoryFile
from rasterio.transform import from_origin
from rasterio.windows import Window, bounds
from shapely.geometry import box


def extraer_ejemplo(valores, parcela, crs_parcela="EPSG:3857"):
    """Prueba de integración: el caso real requiere extracción geográfica aparte."""
    matriz = np.asarray([valores], dtype="float32")
    with MemoryFile() as memoria:
        with memoria.open(
            driver="GTiff",
            height=1,
            width=2,
            count=1,
            dtype="float32",
            nodata=-9999.0,
            crs="EPSG:3857",
            transform=from_origin(0, 1, 1, 1),
        ) as archivo:
            archivo.write(matriz, 1)
            if archivo.crs != CRS.from_user_input(crs_parcela):
                raise ValueError("El CRS de la parcela no coincide con el del ráster")
            leidos = archivo.read(1, masked=True)
            suma = 0.0
            area_valida = 0.0
            for columna in range(archivo.width):
                celda = box(*bounds(Window(columna, 0, 1, 1), archivo.transform))
                area = parcela.intersection(celda).area
                if area <= 0 or np.ma.is_masked(leidos[0, columna]):
                    continue
                suma += area * float(leidos[0, columna])
                area_valida += area
            if area_valida == 0:
                raise ValueError("La parcela no tiene cobertura válida")
            return suma / area_valida, area_valida / parcela.area


def comprobar() -> dict:
    parcela = box(0.2, 0.0, 1.2, 1.0)
    promedio, cobertura = extraer_ejemplo([100, 200], parcela)
    if not (np.isclose(promedio, 120.0) and np.isclose(cobertura, 1.0)):
        raise AssertionError(f"Ponderación incorrecta: {promedio}, cobertura {cobertura}")

    sin_dato, cobertura_parcial = extraer_ejemplo([100, -9999], parcela)
    if not (np.isclose(sin_dato, 100.0) and np.isclose(cobertura_parcial, 0.8)):
        raise AssertionError(f"NoData incorrecto: {sin_dato}, cobertura {cobertura_parcial}")

    borde, cobertura_borde = extraer_ejemplo([100, 200], box(0, 0, 1, 1))
    if not (np.isclose(borde, 100.0) and np.isclose(cobertura_borde, 1.0)):
        raise AssertionError(f"Borde incorrecto: {borde}, cobertura {cobertura_borde}")

    for caso, parametros in {
        "sin_cobertura": ([100, 200], box(3, 0, 4, 1), "EPSG:3857"),
        "todo_nodata": ([-9999, -9999], parcela, "EPSG:3857"),
        "crs_incompatible": ([100, 200], parcela, "EPSG:4326"),
    }.items():
        try:
            extraer_ejemplo(*parametros)
        except ValueError:
            pass
        else:
            raise AssertionError(f"El caso {caso} debió fallar")

    return {
        "resultado": "aprobado",
        "sistema": system(),
        "arquitectura": machine(),
        "python": python_version(),
        "versiones": {paquete: version(paquete) for paquete in ("numpy", "shapely", "rasterio")},
        "comprobaciones": [
            "ponderacion_80_20_120",
            "nodata_y_cobertura_80_pct",
            "borde_sin_doble_conteo",
            "sin_cobertura_rechazado",
            "todo_nodata_rechazado",
            "crs_incompatible_rechazado",
        ],
    }


if __name__ == "__main__":
    argumentos = argparse.ArgumentParser(description=__doc__)
    argumentos.add_argument("--salida", type=Path, help="Guardar evidencia JSON en UTF-8")
    salida = argumentos.parse_args().salida
    resultado = json.dumps(comprobar(), ensure_ascii=False, indent=2)
    if salida is not None:
        salida.parent.mkdir(parents=True, exist_ok=True)
        salida.write_text(resultado + "\n", encoding="utf-8")
    print(resultado)
