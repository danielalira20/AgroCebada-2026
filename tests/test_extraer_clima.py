"""Contratos del extractor: ausencia ≠ fallo; identidad; memoria y exportación."""
import csv
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from affine import Affine
import geopandas as gpd
import numpy as np
import pandas as pd
from rasterio.io import MemoryFile
from rasterio.crs import CRS
from shapely.geometry import box, Polygon

from scripts.extraer_clima import (Cuadricula, Mapa, ESPERADOS, PERIODOS, VARIABLES, FUENTES, UNIDADES, ETIQUETAS_VARIABLE,
    area_laea, extraer, leer_mapa, publicar_local, preparar_soportes, validar_catalogo, validar_claves_mapas)
from scripts.t04_espacio import (area_fisica, aplicar_pesos, firma_cuadricula, huella_json,
                               preparar_pesos, identidad_soporte)

T = Affine(.05, 0, -99, 0, -.05, 20)
Q = Cuadricula(CRS.from_epsg(4326), T, 2, 1)
G = box(-98.99, 19.955, -98.94, 19.995)


class ExtractorTests(unittest.TestCase):
    def parcela(self, idp="A", geom=G):
        return {"id_parcela": idp, "geometria": geom, "area_ha_origen": 7.44}

    def mapas(self, valores=(100, 200), mascara=(False, False)):
        datos = np.ma.array([valores], mask=[mascara], dtype=float)
        return {(v, "2025-07"): Mapa(Q, datos.copy(), {"variable": v, "periodo": "2025-07",
                "cuadricula_id": huella_json(firma_cuadricula(Q)),
                "sha256_raster": v+"-huella", "unidad": UNIDADES[v]}) for v in VARIABLES}

    def soportes(self, parcelas, mapas):
        return preparar_soportes(parcelas, mapas)[0]

    def test_faltantes_preservan_claves_y_no_equivalen_a_cero(self):
        parcelas = [self.parcela(), self.parcela("B", box(-98, 19, -97, 20))]
        mapas = self.mapas(mascara=(True, True))
        filas, _ = extraer(parcelas, mapas, self.soportes(parcelas, mapas), ["A", "B"], ["2025-07"])
        self.assertEqual(len(filas), 6)
        self.assertTrue(all(r["media_ponderada"] is None and r["cobertura_valida"] == 0 for r in filas))
        self.assertEqual({r["estado"] for r in filas if r["id_parcela"] == "A"}, {"todo_nodata"})
        self.assertEqual({r["estado"] for r in filas if r["id_parcela"] == "B"}, {"sin_cobertura_espacial"})

    def test_completa_se_decide_por_geometria_y_mascara(self):
        parcelas = [self.parcela(), self.parcela("B", box(-99.025, 19.955, -98.975, 19.995))]
        mapas = self.mapas()
        filas, _ = extraer(parcelas, mapas, self.soportes(parcelas, mapas), ["A", "B"], ["2025-07"])
        self.assertEqual({r["estado"] for r in filas if r["id_parcela"] == "A"}, {"cobertura_completa"})
        self.assertEqual({r["estado"] for r in filas if r["id_parcela"] == "B"}, {"cobertura_parcial"})

    def test_lectura_precalculada_no_abre_raster_por_parcela(self):
        soporte = preparar_pesos(G, 4326, Q)
        # Cuadricula no tiene read(): fallaría si se repite la lectura.
        s = aplicar_pesos(soporte, Q, datos=np.ma.array([[100, 200]], mask=False))
        self.assertAlmostEqual(s["media_ponderada"], 120, places=5)

    def test_mascara_del_mes_cambia_pesos_sin_mutar_soporte(self):
        parcelas, mapas = [self.parcela()], self.mapas(mascara=(False, True))
        soportes = self.soportes(parcelas, mapas)
        copia = json.dumps(list(soportes.values()), sort_keys=True)
        filas, celdas = extraer(parcelas, mapas, soportes, ["A"], ["2025-07"])
        self.assertTrue(all(r["media_ponderada"] == 100 and r["estado"] == "cobertura_parcial" for r in filas))
        self.assertTrue(all(c["peso_valido"] == 0 and c["valor"] is None for c in celdas if not c["valida"]))
        self.assertEqual(copia, json.dumps(list(soportes.values()), sort_keys=True))

    def test_geometria_y_parametro_invalidan_identidad(self):
        soporte = preparar_pesos(G, 4326, Q)
        self.assertNotEqual(soporte["soporte_id"], identidad_soporte(G.buffer(.00001), 4326, Q))
        self.assertNotEqual(soporte["soporte_id"], identidad_soporte(G, 4326, Q, .00025))
        mapas = self.mapas()
        soportes = self.soportes([self.parcela()], mapas)
        with self.assertRaisesRegex(ValueError, "Identidad"):
            extraer([self.parcela(geom=G.buffer(.00001))], mapas, soportes, ["A"], ["2025-07"])

    def test_catalogo_une_por_id_y_rechaza_duplicados(self):
        geo = gpd.GeoDataFrame({"ID_POLIGON": ["A", "B"]}, geometry=[G, G], crs=4326)
        cat = pd.DataFrame({"ID_POLIGONO": ["B", "A"], "AREA_HA": [22, 11]})
        self.assertEqual([p["area_ha_origen"] for p in validar_catalogo(geo, cat, cantidad=2)], [11, 22])
        cat.loc[1, "ID_POLIGONO"] = "B"
        with self.assertRaisesRegex(ValueError, "duplicado"):
            validar_catalogo(geo, cat, cantidad=2)

    def test_catalogo_con_id_diferente_se_detiene(self):
        geo = gpd.GeoDataFrame({"ID_POLIGON": ["A"]}, geometry=[G], crs=4326)
        cat = pd.DataFrame({"ID_POLIGONO": ["B"], "AREA_HA": [1]})
        with self.assertRaisesRegex(ValueError, "no corresponden"):
            validar_catalogo(geo, cat, cantidad=1)

    def test_claves_mapas_compara_conjunto_no_solo_conteo(self):
        validar_claves_mapas(ESPERADOS)
        for claves in (list(ESPERADOS)[:-1], list(ESPERADOS)+[next(iter(ESPERADOS))], list(ESPERADOS)+[("PREC", "2026-01")]):
            with self.assertRaisesRegex(ValueError, "Mapas:"):
                validar_claves_mapas(claves)

    def tif(self, valores, variable="PREC", periodo="2025-07", crs=4326, etiquetas=None):
        with MemoryFile() as m:
            with m.open(driver="GTiff", width=2, height=1, count=1, dtype="float32", nodata=-9999,
                        crs=crs, transform=T) as r:
                r.write(np.array([valores], dtype="float32"), 1)
                r.update_tags(Variable=ETIQUETAS_VARIABLE[variable], Periodo=periodo, Unidad=UNIDADES[variable],
                              Fuente=FUENTES[variable], Agregacion="Suma de precipitación diaria" if variable == "PREC" else "Promedio mensual")
                if etiquetas:
                    r.update_tags(**etiquetas)
            return m.read()

    def test_mapa_todo_nodata_es_ausencia_legitima(self):
        m = leer_mapa(self.tif([-9999, -9999]), "PREC", "2025-07", "ejemplo")
        self.assertEqual(m.meta["celdas_validas"], 0)
        self.assertIsNone(m.meta["minimo"])

    def test_no_finito_y_negativo_validos_detienen(self):
        for valores, mensaje in (([float("nan"), 1], "no finito"), ([float("inf"), 1], "no finito"), ([-1, 2], "negativa")):
            with self.assertRaisesRegex(ValueError, mensaje):
                leer_mapa(self.tif(valores), "PREC", "2025-07", "ejemplo")
        with self.assertRaisesRegex(ValueError, "no finito"):
            aplicar_pesos(preparar_pesos(G, 4326, Q), Q, datos=np.ma.array([[1, float("nan")]], mask=False), permitir_sin_cobertura=True)

    def test_metadatos_y_crs_erroneos_no_se_convierten_en_faltantes(self):
        for contenido in (self.tif([1, 2], crs=3857), self.tif([1, 2], etiquetas={"Periodo": "2024-01"}),
                          self.tif([1, 2], etiquetas={"Unidad": "mm/dia"})):
            with self.assertRaises(ValueError):
                leer_mapa(contenido, "PREC", "2025-07", "ejemplo")
        with self.assertRaises(Exception):  # GDAL rechaza archivo corrupto antes de cualquier media.
            leer_mapa(b"archivo corrupto", "PREC", "2025-07", "ejemplo")

    def test_exportacion_conserva_precision_y_faltantes(self):
        parcelas = [self.parcela(), self.parcela("B", box(-98, 19, -97, 20))]
        mapas = self.mapas(mascara=(False, True))
        soportes, controles = preparar_soportes(parcelas, mapas)
        filas, celdas = extraer(parcelas, mapas, soportes, ["A", "B"], ["2025-07"])
        with tempfile.TemporaryDirectory() as d:
            destino = Path(d)/"ejecucion"
            publicar_local(destino, {"alcance": "prueba sintética"}, soportes, controles, filas, celdas)
            with (destino/"clima_parcela_mes.csv").open() as f:
                exportadas = list(csv.DictReader(f))
            self.assertEqual(len(exportadas), 6)
            self.assertTrue(all(r["media_ponderada"] == "" for r in exportadas if r["id_parcela"] == "B"))
            self.assertEqual(float(exportadas[0]["media_ponderada"]), filas[0]["media_ponderada"])
            with self.assertRaises(FileExistsError):
                publicar_local(destino, {"alcance": "prueba"}, soportes, controles, filas, celdas)

    def test_error_de_escritura_no_deja_entrega_parcial(self):
        with tempfile.TemporaryDirectory() as d:
            salida = Path(d)/"fallo"
            with patch("scripts.extraer_clima.escribir_csv", side_effect=OSError("disco lleno")):
                with self.assertRaisesRegex(OSError, "disco lleno"):
                    publicar_local(salida, {"alcance": "prueba"}, {}, [])
            self.assertFalse(salida.exists())
            self.assertEqual(list(Path(d).iterdir()), [])

    def test_producto_completo_sintetico_197_por_48_por_3(self):
        # Verifica el universo de salida sin ejecutar la producción real.
        parcelas = [self.parcela(f"AGC_{i:03d}") for i in range(1, 197)]
        parcelas.append(self.parcela("AGC_197", box(-98, 19, -97, 20)))
        base = self.mapas()
        mapas = {(v, p): Mapa(Q, base[v, "2025-07"].datos,
                    {**base[v, "2025-07"].meta, "periodo": p}) for v, p in ESPERADOS}
        soportes = self.soportes(parcelas, mapas)
        ids = [p["id_parcela"] for p in parcelas]
        filas, _ = extraer(parcelas, mapas, soportes, ids, PERIODOS)
        claves = {(r["id_parcela"], r["periodo"], r["variable"]) for r in filas}
        self.assertEqual(len(filas), 28368)
        self.assertEqual(len(claves), 28368)
        self.assertEqual({r["periodo"] for r in filas}, set(PERIODOS))
        ausentes = [r for r in filas if r["id_parcela"] == "AGC_197"]
        self.assertEqual(len(ausentes), 144)
        self.assertTrue(all(r["estado"] == "sin_cobertura_espacial" and r["media_ponderada"] is None for r in ausentes))

    def test_interseccion_milimetros_no_se_elimina_ni_pierde_precision(self):
        # Regresión: intersección real AGC_174/PREC, 0.0016 m². No es contacto.
        g = Polygon([(-98.30603791771509, 19.899999551475048),
                     (-98.30603861533469, 19.899999551475048),
                     (-98.3060387099906, 19.8999999535217)])
        area = area_fisica(g)
        independiente = area_laea(g)
        self.assertGreater(area, 0)
        self.assertLess(area, .002)
        self.assertLess(abs(area-independiente)/independiente, 1e-6)
        self.assertLess(abs(area-area_fisica(g, .00025))/area, 1e-6)

    def test_parametros_manipulados_del_soporte_se_rechazan(self):
        soporte = preparar_pesos(G, 4326, Q)
        soporte["paso_area_grados"] = .00025
        with self.assertRaisesRegex(ValueError, "alterados"):
            aplicar_pesos(soporte, Q, datos=np.ma.array([[1, 2]], mask=False))

    def test_selecciones_erroneas_no_pierden_filas(self):
        parcelas, mapas = [self.parcela()], self.mapas()
        soportes = self.soportes(parcelas, mapas)
        for ids, periodos in ((["A", "A"], ["2025-07"]), (["Z"], ["2025-07"]), (["A"], ["2026-01"]), ([], ["2025-07"])):
            with self.assertRaises(ValueError):
                extraer(parcelas, mapas, soportes, ids, periodos)


if __name__ == "__main__":
    unittest.main()
