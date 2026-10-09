"""T05: pruebas sintéticas de extracción de relieve (docs/t05_relieve.md).

Cada prueba fabrica un ráster diminuto en EPSG:6372 (celdas de 120 m) con
valores elegidos, de modo que el resultado correcto se calcula a mano.
"""
import unittest
from pathlib import Path

import numpy as np
from affine import Affine
from rasterio.io import MemoryFile
from shapely.geometry import MultiPolygon, Polygon, box

from scripts.t05_relieve import (
    PISO_PENDIENTE_T10, avisos, comprobar_areas, pendiente_para_t10,
    preparar_soporte, resumir_variable, valor_en_punto,
)

X0, Y0 = 2800000.0, 800000.0
T = Affine(120, 0, X0, 0, -120, Y0)
CRS = "EPSG:6372"


class Base(unittest.TestCase):
    def raster(self, valores, t=T, crs=CRS):
        memoria = MemoryFile()
        self.addCleanup(memoria.close)
        datos = np.asarray(valores, dtype="float32")
        r = memoria.open(driver="GTiff", height=datos.shape[0], width=datos.shape[1],
                         count=1, dtype="float32", crs=crs, nodata=-9999, transform=t)
        self.addCleanup(r.close)
        r.write(datos, 1)
        return r

    def calcular(self, geom, valores):
        r = self.raster(valores)
        soporte = preparar_soporte(geom, CRS, r)
        comprobar_areas(soporte)
        return soporte, resumir_variable(soporte, r)


class AreasYBordes(Base):
    def test_ponderacion_80_20(self):
        # 96 m en la celda de 100 y 24 m en la de 200: 120, no el promedio simple 150.
        _, r = self.calcular(box(X0+24, Y0-100, X0+144, Y0-20), [[100, 200]])
        self.assertAlmostEqual(r["media"], 120, places=9)
        self.assertAlmostEqual(r["cobertura_valida"], 1, places=12)
        self.assertEqual(r["estado"], "cobertura_completa")
        self.assertEqual((r["minimo"], r["maximo"]), (100, 200))

    def test_contacto_lineal_no_aporta_area(self):
        _, r = self.calcular(box(X0, Y0-120, X0+120, Y0), [[100, 900]])
        self.assertEqual([(c["fila"], c["columna"]) for c in r["celdas"]], [(0, 0)])
        self.assertEqual(r["media"], 100)

    def test_contacto_vertice_no_aporta_area(self):
        geom = Polygon([(X0+10, Y0-10), (X0+110, Y0-10), (X0+120, Y0-120)])
        _, r = self.calcular(geom, [[100, 900], [700, 500]])
        self.assertEqual(r["celdas_intersectadas"], 1)

    def test_multiples_celdas(self):
        _, r = self.calcular(box(X0+60, Y0-180, X0+180, Y0-60), [[10, 20], [30, 40]])
        self.assertEqual(r["celdas_intersectadas"], 4)
        self.assertAlmostEqual(r["media"], 25, places=9)

    def test_parcela_menor_a_una_celda(self):
        s, r = self.calcular(box(X0+10, Y0-50, X0+50, Y0-10), [[100, 200]])
        self.assertEqual(r["celdas_intersectadas"], 1)
        self.assertEqual(r["media"], 100)
        self.assertAlmostEqual(s["area_parcela_m2"], 1600, places=9)

    def test_multipoligono_con_hueco(self):
        con_hueco = Polygon(box(X0+10, Y0-110, X0+110, Y0-10).exterior.coords,
                            [box(X0+40, Y0-80, X0+80, Y0-40).exterior.coords])
        geom = MultiPolygon([con_hueco, box(X0+130, Y0-110, X0+150, Y0-90)])
        s, r = self.calcular(geom, [[100, 200]])
        self.assertAlmostEqual(s["area_parcela_m2"], 8800, places=9)
        self.assertAlmostEqual(r["media"], (8400*100 + 400*200) / 8800, places=9)


class ComprobacionDeAreas(Base):
    def soporte(self):
        r = self.raster([[100, 200]])
        return preparar_soporte(box(X0+24, Y0-100, X0+144, Y0-20), CRS, r)

    def test_soporte_correcto_pasa(self):
        comprobar_areas(self.soporte())

    def test_celda_omitida_detectada(self):
        s = self.soporte()
        s["celdas"] = s["celdas"][:1]
        s["area_celdas_m2"] = s["celdas"][0]["area_m2"]
        with self.assertRaisesRegex(ValueError, "área directa"):
            comprobar_areas(s)

    def test_celda_duplicada_detectada(self):
        s = self.soporte()
        s["celdas"].append(dict(s["celdas"][0]))
        with self.assertRaisesRegex(ValueError, "duplicada"):
            comprobar_areas(s)

    def test_total_guardado_alterado_detectado(self):
        s = self.soporte()
        s["celdas"] = s["celdas"][:1]  # Se omite una celda sin actualizar el total.
        with self.assertRaisesRegex(ValueError, "alterado"):
            comprobar_areas(s)


class NoDataYCobertura(Base):
    def test_nodata_parcial_no_equivale_a_cero(self):
        _, r = self.calcular(box(X0+24, Y0-100, X0+144, Y0-20), [[100, -9999]])
        self.assertEqual(r["media"], 100)
        self.assertAlmostEqual(r["cobertura_valida"], .8, places=12)
        self.assertEqual(r["estado"], "cobertura_parcial")
        self.assertEqual((r["celdas_intersectadas"], r["celdas_validas"]), (2, 1))
        self.assertIsNone(r["celdas"][1]["valor"])

    def test_todo_nodata_estado_y_vacios(self):
        _, r = self.calcular(box(X0+24, Y0-100, X0+144, Y0-20), [[-9999, -9999]])
        self.assertEqual(r["estado"], "todo_nodata")
        self.assertEqual((r["media"], r["minimo"], r["maximo"]), (None, None, None))
        self.assertEqual(r["cobertura_valida"], 0)

    def test_mitad_fuera_de_la_cuadricula(self):
        s, r = self.calcular(box(X0-60, Y0-100, X0+60, Y0-20), [[100, 200]])
        self.assertAlmostEqual(s["cobertura_espacial"], .5, places=12)
        self.assertAlmostEqual(s["area_fuera_mapa_m2"], 4800, places=9)
        self.assertAlmostEqual(r["cobertura_valida"], .5, places=12)
        self.assertEqual(r["estado"], "cobertura_parcial")

    def test_totalmente_fuera(self):
        s, r = self.calcular(box(X0-500, Y0-100, X0-300, Y0-20), [[100, 200]])
        self.assertEqual(r["estado"], "sin_cobertura_espacial")
        self.assertEqual(s["cobertura_espacial"], 0)
        self.assertIsNone(r["media"])

    def test_completa_tolera_aritmetica_pero_no_mas(self):
        r = self.raster([[100, 200]])
        s = preparar_soporte(box(X0+24, Y0-100, X0+144, Y0-20), CRS, r)
        casi = dict(s, area_parcela_m2=s["area_parcela_m2"] * (1 + 1e-12))
        self.assertEqual(resumir_variable(casi, r)["estado"], "cobertura_completa")
        menos = dict(s, area_parcela_m2=s["area_parcela_m2"] * (1 + 1e-6))
        self.assertEqual(resumir_variable(menos, r)["estado"], "cobertura_parcial")


class PisoDePendiente(unittest.TestCase):
    def t10(self, cobertura, media=3.0):
        return pendiente_para_t10({"media": media, "cobertura_valida": cobertura})

    def test_limites(self):
        self.assertEqual(PISO_PENDIENTE_T10, .5)
        self.assertIsNone(self.t10(.5 - 1e-12))
        self.assertEqual(self.t10(.5), 3.0)
        self.assertEqual(self.t10(.5 + 1e-12), 3.0)

    def test_se_aplica_sin_redondear(self):
        # 0.49996 redondea a 0.5 con cuatro decimales, pero está bajo el piso.
        self.assertIsNone(self.t10(.49996))

    def test_sin_media_queda_vacio(self):
        self.assertIsNone(self.t10(1.0, media=None))


class Centroide(Base):
    def test_valido_sin_dato_y_fuera(self):
        r = self.raster([[100, -9999]])
        d = r.read(1, masked=True)
        self.assertEqual(valor_en_punto(r, d, X0+60, Y0-60), (100.0, "valido"))
        self.assertEqual(valor_en_punto(r, d, X0+180, Y0-60), (None, "sin_dato"))
        self.assertEqual(valor_en_punto(r, d, X0-10, Y0-60), (None, "fuera_de_cuadricula"))

    def test_punto_en_borde_toma_la_celda_siguiente(self):
        # Regla fija, sin interpolar: x exactamente en el borde pertenece a la celda de la derecha.
        r = self.raster([[100, 200]])
        self.assertEqual(valor_en_punto(r, r.read(1, masked=True), X0+120, Y0-60), (200.0, "valido"))


class Avisos(unittest.TestCase):
    def var(self, estado="cobertura_completa", cobertura=1.0, validas=10):
        return {"estado": estado, "cobertura_valida": cobertura, "celdas_validas": validas}

    def test_parcela_sin_problemas(self):
        self.assertEqual(avisos(50000, self.var(), self.var(), True, "valido", "valido"), [])

    def test_cada_umbral(self):
        lista = avisos(14399, self.var("cobertura_parcial", .9, 4),
                       self.var("cobertura_parcial", .3, 3), False, "sin_dato", "fuera_de_cuadricula")
        self.assertEqual(lista, ["pendiente_bajo_piso_50", "cobertura_parcial_elevacion",
                                 "cobertura_parcial_pendiente", "pocas_celdas_validas",
                                 "parcela_menor_a_una_celda", "centroide_fuera_de_parcela",
                                 "centroide_sin_dato_elevacion", "centroide_sin_dato_pendiente"])

    def test_limites_de_celdas_y_area(self):
        self.assertEqual(avisos(14400, self.var(validas=5), self.var(validas=5), True, "valido", "valido"), [])


class Errores(Base):
    def test_crs_incompatible(self):
        with self.assertRaisesRegex(ValueError, "CRS incompatible"):
            preparar_soporte(box(X0+10, Y0-50, X0+50, Y0-10), "EPSG:4326", self.raster([[1, 2]]))

    def test_cuadricula_geografica_rechazada(self):
        r = self.raster([[1, 2]], t=Affine(.05, 0, -99, 0, -.05, 20), crs="EPSG:4326")
        with self.assertRaisesRegex(ValueError, "proyectada"):
            preparar_soporte(box(-98.99, 19.96, -98.96, 19.99), "EPSG:4326", r)

    def test_cuadricula_rotada(self):
        r = self.raster([[1, 2]], t=Affine(120, 10, X0, 0, -120, Y0))
        with self.assertRaisesRegex(ValueError, "rotada"):
            preparar_soporte(box(X0+10, Y0-50, X0+50, Y0-10), CRS, r)

    def test_geometria_invalida_no_se_repara(self):
        geom = Polygon([(X0, Y0), (X0+100, Y0-100), (X0, Y0-100), (X0+100, Y0)])
        with self.assertRaisesRegex(ValueError, "Geometría parcelaria"):
            preparar_soporte(geom, CRS, self.raster([[1, 2]]))

    def test_cuadricula_distinta_no_reutiliza_soporte(self):
        geom = box(X0+10, Y0-50, X0+50, Y0-10)
        s = preparar_soporte(geom, CRS, self.raster([[1, 2]]))
        otra = self.raster([[1, 2]], t=Affine(120, 0, X0+0.001, 0, -120, Y0))
        with self.assertRaisesRegex(ValueError, "Cuadrícula distinta"):
            resumir_variable(s, otra)

    def test_valor_no_finito(self):
        with self.assertRaisesRegex(ValueError, "no finito"):
            self.calcular(box(X0+10, Y0-50, X0+50, Y0-10), [[float("nan"), 1]])

    def test_datos_de_otra_forma(self):
        r = self.raster([[1, 2]])
        s = preparar_soporte(box(X0+10, Y0-50, X0+50, Y0-10), CRS, r)
        with self.assertRaisesRegex(ValueError, "no corresponden"):
            resumir_variable(s, r, datos=np.ma.masked_array(np.zeros((3, 3))))


class ExtraccionDePuntaAPunta(unittest.TestCase):
    """Shapefile y TIFF diminutos en una carpeta temporal: lectura, cambio de ID y CSV."""

    def setUp(self):
        import tempfile
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.raiz = Path(self.tmp.name)
        self.dataset = self.raiz / "dataset"
        (self.dataset / "topo").mkdir(parents=True)

    def tiff(self, nombre, valores):
        import rasterio
        d = np.asarray(valores, dtype="float32")
        with rasterio.open(self.dataset / "topo" / nombre, "w", driver="GTiff",
                           height=d.shape[0], width=d.shape[1], count=1, dtype="float32",
                           crs=CRS, nodata=-9999, transform=T) as r:
            r.write(d, 1)

    def shapefile(self, geoms_6372, ids):
        import geopandas as gpd
        g = gpd.GeoDataFrame({"ID_POLIGON": ids}, geometry=geoms_6372, crs=CRS).to_crs("EPSG:4326")
        g.to_file(self.dataset / "Parcelas_Reto_AGC_CONJUNTO.shp")

    def test_extrae_y_escribe_csv(self):
        from scripts.t05_relieve import extraer
        self.tiff("Elevacion_INEGI_CEM4_120m.tif", [[2500, 2600], [2700, 2800]])
        self.tiff("Pendiente_INEGI_CEM4_120m_grados.tif", [[1, -9999], [3, 4]])
        self.shapefile([box(X0+24, Y0-100, X0+144, Y0-20), box(X0+130, Y0-230, X0+230, Y0-130)],
                       ["AGC_002", "AGC_001"])
        salida = self.raiz / "salida"
        filas, celdas = extraer(self.dataset, salida)
        self.assertEqual([f["id_parcela"] for f in filas], ["AGC_001", "AGC_002"])
        a2 = filas[1]
        self.assertAlmostEqual(a2["elevacion_media_m"], 2520, places=3)
        self.assertEqual(a2["pendiente_media_grados"], 1.0)
        self.assertAlmostEqual(a2["pendiente_cobertura_valida"], .8, places=6)
        self.assertEqual(a2["estado_pendiente"], "cobertura_parcial")
        self.assertIn("cobertura_parcial_pendiente", a2["avisos"])
        texto = (salida / "relieve_parcela.csv").read_bytes()
        self.assertNotIn(b"\r", texto)
        self.assertTrue(texto.startswith(b"id_parcela,area_parcela_6372_m2,"))
        self.assertEqual(len((salida / "relieve_celdas.csv").read_text().splitlines()), 1 + len(celdas))
        with self.assertRaisesRegex(ValueError, "carpeta nueva"):
            extraer(self.dataset, salida)

    def test_ids_duplicados_detienen(self):
        from scripts.t05_relieve import extraer
        self.tiff("Elevacion_INEGI_CEM4_120m.tif", [[1, 2]])
        self.tiff("Pendiente_INEGI_CEM4_120m_grados.tif", [[1, 2]])
        self.shapefile([box(X0+10, Y0-50, X0+50, Y0-10)] * 2, ["AGC_001", "AGC_001"])
        with self.assertRaisesRegex(ValueError, "duplicados"):
            extraer(self.dataset, self.raiz / "salida")
        self.assertFalse((self.raiz / "salida").exists())

    def test_cuadriculas_no_alineadas_detienen(self):
        from scripts.t05_relieve import extraer
        self.tiff("Elevacion_INEGI_CEM4_120m.tif", [[1, 2]])
        self.tiff("Pendiente_INEGI_CEM4_120m_grados.tif", [[1, 2, 3]])
        self.shapefile([box(X0+10, Y0-50, X0+50, Y0-10)], ["AGC_001"])
        with self.assertRaisesRegex(ValueError, "no alineadas"):
            extraer(self.dataset, self.raiz / "salida")


class Controles(unittest.TestCase):
    def fila(self, id_, ce, cp, ee="cobertura_completa", ep="cobertura_completa"):
        return {"id_parcela": id_, "elevacion_cobertura_valida": repr(ce),
                "pendiente_cobertura_valida": repr(cp), "estado_elevacion": ee, "estado_pendiente": ep}

    def test_t02_dentro_de_la_tolerancia_del_redondeo(self):
        from scripts.t05_relieve import conciliar_con_t02
        r = conciliar_con_t02([self.fila("A", .95064, .55274)], {"A": {"elevacion": .9506, "pendiente": .5527}})
        self.assertEqual(r["discrepancias"], [])

    def test_t02_fuera_de_tolerancia_se_reporta(self):
        from scripts.t05_relieve import conciliar_con_t02
        r = conciliar_con_t02([self.fila("A", .95066, 1.0)], {"A": {"elevacion": .9506, "pendiente": 1.0}})
        self.assertEqual([d["variable"] for d in r["discrepancias"]], ["elevacion"])

    def test_t02_ids_distintos_se_reportan(self):
        from scripts.t05_relieve import conciliar_con_t02
        r = conciliar_con_t02([self.fila("A", 1.0, 1.0)], {"B": {"elevacion": 1.0, "pendiente": 1.0}})
        self.assertEqual((r["ids_solo_en_t05"], r["ids_solo_en_t02"]), (["A"], ["B"]))

    def test_reservada_incompleta_se_reporta(self):
        from scripts.t05_relieve import comprobar_reservadas
        filas = [self.fila("A", 1, 1), self.fila("B", .9, .5, "cobertura_parcial", "cobertura_parcial"),
                 self.fila("C", .9, .5, "cobertura_parcial", "cobertura_parcial")]
        r = comprobar_reservadas(filas, {"A": "PREDICCION", "B": "PREDICCION", "C": "ENTRENAMIENTO"})
        self.assertEqual(r, {"reservadas": 2, "incompletas": ["B"]})


if __name__ == "__main__":
    unittest.main()
