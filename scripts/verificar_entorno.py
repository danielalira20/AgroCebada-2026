"""Comprueba las bibliotecas geoespaciales con datos sintéticos, sin tocar FIRA."""

from platform import machine, system

import numpy as np
import rasterio
from rasterio.io import MemoryFile
from rasterio.transform import from_origin
from shapely.geometry import box


def main() -> None:
    # La parcela cubre el 80 % de una celda y el 20 % de la siguiente.
    valores = np.array([[100.0, 200.0]], dtype="float32")
    parcela = box(0.2, 0.0, 1.2, 1.0)
    with MemoryFile() as memoria:
        with memoria.open(
            driver="GTiff",
            height=1,
            width=2,
            count=1,
            dtype="float32",
            transform=from_origin(0, 1, 1, 1),
        ) as archivo:
            archivo.write(valores, 1)
            leidos = archivo.read(1)
            areas = [
                parcela.intersection(box(columna, 0, columna + 1, 1)).area
                for columna in range(2)
            ]
            promedio = sum(areas[i] * float(leidos[0, i]) for i in range(2)) / sum(areas)
    if not np.isclose(promedio, 120.0):
        raise RuntimeError(f"Promedio de comprobación incorrecto: {promedio}")
    print(f"Entorno geoespacial listo para prueba sintética: {system()} {machine()}; valor {promedio:.1f}")


if __name__ == "__main__":
    main()
