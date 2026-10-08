"""Casos de integridad para el inventario, sin datos del concurso."""

import io
from pathlib import Path
import tempfile
import unittest
import zipfile

import numpy as np
from rasterio.io import MemoryFile
from rasterio.transform import from_origin

from scripts.inventariar_clima import inventariar


def mapa(valores):
    with MemoryFile() as memoria:
        with memoria.open(driver="GTiff", height=1, width=2, count=1,
                          dtype="float32", crs="EPSG:4326", nodata=-9999,
                          transform=from_origin(-99, 20, 0.05, 0.05)) as raster:
            raster.write(np.array([valores], dtype="float32"), 1)
        return memoria.read()


class InventarioTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.valido = mapa([100, -9999])
        cls.negativo = mapa([-1, -9999])
        cls.vacio = mapa([-9999, -9999])

    def paquete(self, omitir=None, duplicar=False, primer_mapa=None):
        archivo = Path(self.directorio.name) / "ejemplo.zip"
        anidado = io.BytesIO()
        with zipfile.ZipFile(anidado, "w") as interior:
            for variable in ("PREC", "Tmin", "Tmax"):
                for anio in range(2022, 2026):
                    for mes in range(1, 13):
                        nombre = f"{variable}_{anio}_{mes:02}.tif"
                        if nombre == omitir:
                            continue
                        contenido = primer_mapa if nombre == "PREC_2022_01.tif" else None
                        interior.writestr(nombre, contenido or self.valido)
            if duplicar:
                interior.writestr("otra_copia/PREC_2022_01.tif", self.valido)
        with zipfile.ZipFile(archivo, "w") as exterior:
            exterior.writestr("clima.zip", anidado.getvalue())
        return archivo

    def setUp(self):
        self.directorio = tempfile.TemporaryDirectory()
        self.addCleanup(self.directorio.cleanup)

    def test_zip_anidado_completo_y_nodata(self):
        resultado = inventariar(self.paquete())
        self.assertEqual(resultado["capas_por_variable"], {"PREC": 48, "Tmin": 48, "Tmax": 48})
        self.assertEqual(resultado["archivos_finales"], 144)
        self.assertTrue(all(c["celdas_validas"] == 1 and c["celdas_nodata"] == 1
                            for c in resultado["capas"]))

    def test_mes_faltante(self):
        with self.assertRaisesRegex(ValueError, "faltantes=.*PREC.*2022.*1"):
            inventariar(self.paquete(omitir="PREC_2022_01.tif"))

    def test_mes_duplicado_en_otra_carpeta(self):
        with self.assertRaisesRegex(ValueError, "duplicados=.*PREC.*2022.*1"):
            inventariar(self.paquete(duplicar=True))

    def test_lluvia_negativa(self):
        with self.assertRaisesRegex(ValueError, "Precipitación válida negativa"):
            inventariar(self.paquete(primer_mapa=self.negativo))

    def test_mapa_sin_celdas_validas(self):
        with self.assertRaisesRegex(ValueError, "Sin valores válidos"):
            inventariar(self.paquete(primer_mapa=self.vacio))


if __name__ == "__main__":
    unittest.main()
