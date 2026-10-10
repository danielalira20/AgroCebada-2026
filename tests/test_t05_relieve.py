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


class _DatasetTemporal:
    """Herramientas comunes, sin pruebas propias: shapefile y TIFF diminutos en una carpeta temporal."""

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


class ExtraccionDePuntaAPunta(_DatasetTemporal, unittest.TestCase):
    """Lectura de archivos, cambio de ID y escritura de CSV."""

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


class PublicacionYVerificacion(_DatasetTemporal, unittest.TestCase):
    """Extraer, publicar y verificar en una carpeta temporal, con T02 sintético."""

    def preparar(self, cobertura_pendiente_t02="0.8"):
        from scripts.t05_relieve import extraer
        self.tiff("Elevacion_INEGI_CEM4_120m.tif", [[2500, 2600], [2700, 2800]])
        self.tiff("Pendiente_INEGI_CEM4_120m_grados.tif", [[1, -9999], [3, 4]])
        self.shapefile([box(X0+24, Y0-100, X0+144, Y0-20), box(X0+130, Y0-230, X0+230, Y0-130)],
                       ["AGC_002", "AGC_001"])
        t02 = self.raiz / "t02"
        t02.mkdir()
        (t02 / "catalogo.csv").write_text(
            "id_parcela,conjunto_origen\nAGC_001,PREDICCION\nAGC_002,ENTRENAMIENTO\n", encoding="utf-8")
        (t02 / "soporte.csv").write_text(
            "id_parcela,cobertura_elevacion,cobertura_pendiente\nAGC_001,1.0,1.0\n"
            f"AGC_002,1.0,{cobertura_pendiente_t02}\n", encoding="utf-8")
        self.origen = self.raiz / "extraccion"
        extraer(self.dataset, self.origen)
        self.t02 = (t02 / "soporte.csv", t02 / "catalogo.csv")
        self.destino = self.raiz / "registro_t05"

    def test_publicar_y_verificar_con_reproduccion(self):
        from scripts.t05_relieve import publicar, verificar
        self.preparar()
        c = publicar(self.dataset, self.origen, self.destino, *self.t02)
        self.assertEqual(c["resultado"], "aprobado")
        self.assertEqual(sorted(p.name for p in self.destino.iterdir()),
                         ["controles.json", "manifest.json", "procedencia.json",
                          "relieve_celdas.csv", "relieve_parcela.csv"])
        r = verificar(self.destino, reproducir=True, dataset=self.dataset)
        self.assertEqual((r["resultado"], r["reproduccion"]), ("integridad_aprobada", "aprobada"))
        for p in self.destino.iterdir():
            self.assertNotIn(b"\r", p.read_bytes(), p.name)

    def test_archivo_alterado_falla(self):
        from scripts.t05_relieve import publicar, verificar
        self.preparar()
        publicar(self.dataset, self.origen, self.destino, *self.t02)
        with open(self.destino / "relieve_parcela.csv", "a", encoding="utf-8") as f:
            f.write(" ")
        with self.assertRaisesRegex(ValueError, "Huella distinta: relieve_parcela.csv"):
            verificar(self.destino)

    def test_conversion_a_crlf_falla(self):
        # Lo que hace un checkout de Windows sin .gitattributes: por eso registro/t05/* va con eol=lf.
        from scripts.t05_relieve import publicar, verificar
        self.preparar()
        publicar(self.dataset, self.origen, self.destino, *self.t02)
        ruta = self.destino / "controles.json"
        ruta.write_bytes(ruta.read_bytes().replace(b"\n", b"\r\n"))
        with self.assertRaisesRegex(ValueError, "Huella distinta: controles.json"):
            verificar(self.destino)

    def test_reproduccion_distinta_falla(self):
        from scripts.t05_relieve import publicar, verificar
        self.preparar()
        publicar(self.dataset, self.origen, self.destino, *self.t02)
        self.tiff("Pendiente_INEGI_CEM4_120m_grados.tif", [[1.5, -9999], [3, 4]])  # Cambia la fuente.
        with self.assertRaisesRegex(ValueError, "Reproducción distinta"):
            verificar(self.destino, reproducir=True, dataset=self.dataset)

    def test_discrepancia_t02_publica_pero_no_cierra(self):
        from scripts.t05_relieve import publicar, verificar
        self.preparar(cobertura_pendiente_t02="0.7")
        c = publicar(self.dataset, self.origen, self.destino, *self.t02)
        self.assertEqual(c["resultado"], "aprobado_con_avisos_t05_no_cerrada")
        self.assertEqual(verificar(self.destino)["resultado_controles"], "aprobado_con_avisos_t05_no_cerrada")

    def test_extraccion_antigua_con_fuente_nueva_no_se_publica(self):
        # Auditoría del 9 de octubre: extraer, cambiar un valor del TIFF (misma cuadrícula y
        # cobertura) y publicar las tablas viejas aprobaba y guardaba la huella del TIFF nuevo.
        from scripts.t05_relieve import publicar
        self.preparar()
        self.tiff("Pendiente_INEGI_CEM4_120m_grados.tif", [[1.5, -9999], [3, 4]])
        with self.assertRaisesRegex(ValueError, "no corresponde al dataset actual"):
            publicar(self.dataset, self.origen, self.destino, *self.t02)
        self.assertFalse(self.destino.exists())

    def test_publicacion_guarda_las_huellas_de_las_fuentes_usadas(self):
        import json
        from scripts.t05_relieve import huella, publicar
        self.preparar()
        publicar(self.dataset, self.origen, self.destino, *self.t02)
        fuentes = json.loads((self.destino / "procedencia.json").read_text(encoding="utf-8"))["fuentes"]
        pend = next(f for f in fuentes if f["rol"] == "pendiente")
        self.assertEqual(pend["sha256"], huella(self.dataset / pend["archivo"]))

    def test_destino_con_contenido_no_se_sobrescribe(self):
        from scripts.t05_relieve import publicar
        self.preparar()
        self.destino.mkdir()
        (self.destino / "otro.txt").write_text("x")
        with self.assertRaisesRegex(ValueError, "carpeta nueva"):
            publicar(self.dataset, self.origen, self.destino, *self.t02)


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


class ComparadorNumerico(unittest.TestCase):
    """Auditoría de 2026-10-08: el comparador aceptaba infinito frente a un número normal."""

    def test_infinitos_y_nan_nunca_son_iguales(self):
        from scripts.t05_relieve import _iguales
        for raro in ("inf", "-inf", "nan", "Infinity"):
            self.assertFalse(_iguales("2500", raro), raro)
            self.assertFalse(_iguales(raro, "2500"), raro)
            self.assertFalse(_iguales(raro, raro), raro)
        self.assertFalse(_iguales("inf", "-inf"))

    def test_numeros_y_textos_normales(self):
        from scripts.t05_relieve import _iguales
        self.assertTrue(_iguales("2500.0", "2500.0000000001"))
        self.assertFalse(_iguales("2500.0", "2500.1"))
        self.assertTrue(_iguales("", ""))
        self.assertTrue(_iguales("True", "True"))
        self.assertFalse(_iguales("True", "False"))
        self.assertTrue(_iguales("AGC_001", "AGC_001"))


class ReproduccionEntreEquipos(_DatasetTemporal, unittest.TestCase):
    """Revisión del PR por Dani (9 de octubre): en Mac ARM cuatro áreas diferían ~1.3e-9 m² de las
    publicadas en Intel por la conversión de coordenadas (PROJ). Se toleran diferencias de área de
    hasta 1e-5 m² entre equipos; lo discreto debe coincidir exacto y lo demás conserva su tolerancia."""

    def setUp(self):
        super().setUp()
        import shutil
        from scripts.t05_relieve import extraer
        self.tiff("Elevacion_INEGI_CEM4_120m.tif", [[2500, 2600], [2700, 2800]])
        self.tiff("Pendiente_INEGI_CEM4_120m_grados.tif", [[1, -9999], [3, 4]])
        self.shapefile([box(X0+24, Y0-100, X0+144, Y0-20), box(X0+130, Y0-230, X0+230, Y0-130)],
                       ["AGC_002", "AGC_001"])
        self.a = self.raiz / "publicada"
        extraer(self.dataset, self.a)
        self.b = self.raiz / "otro_equipo"
        shutil.copytree(self.a, self.b)

    def cambiar(self, archivo, columna, funcion, fila=0):
        import csv
        ruta = self.b / archivo
        with open(ruta, encoding="utf-8", newline="") as f:
            filas = list(csv.DictReader(f))
        filas[fila][columna] = funcion(filas[fila][columna])
        with open(ruta, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(filas[0]), lineterminator="\n")
            w.writeheader()
            w.writerows(filas)

    def fila_area_minima(self):
        import csv
        with open(self.a / "relieve_celdas.csv", encoding="utf-8", newline="") as f:
            areas = [float(r["area_interseccion_m2"]) for r in csv.DictReader(f)]
        return areas.index(min(areas))   # Celda chica: ahí el criterio relativo es más estricto (AGC_038).

    def comparar(self, mismo_equipo=False):
        from scripts.t05_relieve import comparar_extracciones
        comparar_extracciones(self.a, self.b, mismo_equipo)

    def test_extracciones_identicas_pasan(self):
        self.comparar()
        self.comparar(mismo_equipo=True)

    def test_area_con_diferencia_de_redondeo_entre_equipos_pasa(self):
        self.cambiar("relieve_celdas.csv", "area_interseccion_m2", lambda v: repr(float(v) + 5e-6),
                     self.fila_area_minima())
        self.cambiar("relieve_parcela.csv", "elevacion_area_valida_m2", lambda v: repr(float(v) + 1e-6))
        self.comparar()

    def test_la_misma_diferencia_no_pasa_en_el_mismo_equipo(self):
        self.cambiar("relieve_celdas.csv", "area_interseccion_m2", lambda v: repr(float(v) + 5e-6),
                     self.fila_area_minima())
        with self.assertRaisesRegex(ValueError, "area_interseccion_m2"):
            self.comparar(mismo_equipo=True)

    def test_area_alterada_por_encima_del_margen_falla(self):
        self.cambiar("relieve_celdas.csv", "area_interseccion_m2", lambda v: repr(float(v) + 1e-3))
        with self.assertRaisesRegex(ValueError, "Reproducción distinta"):
            self.comparar()

    def test_area_no_finita_falla(self):
        self.cambiar("relieve_celdas.csv", "area_interseccion_m2", lambda v: "inf")
        with self.assertRaisesRegex(ValueError, "Reproducción distinta"):
            self.comparar()

    def test_la_tolerancia_de_area_no_se_extiende_a_las_medias(self):
        self.cambiar("relieve_parcela.csv", "elevacion_media_m", lambda v: repr(float(v) + 1e-3))
        with self.assertRaisesRegex(ValueError, "elevacion_media_m"):
            self.comparar()

    def test_diferencia_con_centroide_no_es_mas_estricta_que_la_media(self):
        # La media admite 1e-9 relativo (~2.6e-6 m en 2600 m); la diferencia, que sale de ella,
        # admite el mismo error absoluto aunque su propio valor sea pequeño.
        self.cambiar("relieve_parcela.csv", "diferencia_elevacion_centroide_m", lambda v: repr(float(v) + 2e-6), 1)
        self.comparar()
        self.cambiar("relieve_parcela.csv", "diferencia_elevacion_centroide_m", lambda v: repr(float(v) + 1e-3), 1)
        with self.assertRaisesRegex(ValueError, "diferencia_elevacion_centroide_m"):
            self.comparar()

    def test_discretas_deben_coincidir_exactas(self):
        casos = [("relieve_parcela.csv", "estado_pendiente", lambda v: "cobertura_completa"),
                 ("relieve_parcela.csv", "elevacion_celdas_validas", lambda v: v + ".0"),
                 ("relieve_parcela.csv", "avisos", lambda v: v + ";pocas_celdas_validas"),
                 ("relieve_celdas.csv", "pendiente_valida", lambda v: "False" if v == "True" else "True")]
        import shutil
        for archivo, columna, funcion in casos:
            with self.subTest(columna):
                shutil.rmtree(self.b)
                shutil.copytree(self.a, self.b)
                fila = 1 if archivo == "relieve_parcela.csv" else 0
                self.cambiar(archivo, columna, funcion, fila)
                with self.assertRaisesRegex(ValueError, "Reproducción distinta"):
                    self.comparar()

    def test_celda_de_mas_o_de_menos_falla(self):
        ruta = self.b / "relieve_celdas.csv"
        lineas = ruta.read_text(encoding="utf-8").splitlines(keepends=True)
        ruta.write_text("".join(lineas[:-1]), encoding="utf-8", newline="")
        with self.assertRaisesRegex(ValueError, "número de filas"):
            self.comparar()

    def test_procedencia_registra_el_entorno_de_calculo(self):
        from scripts.t05_relieve import procedencia
        e = procedencia(self.dataset)["entorno"]
        for clave in ("arquitectura", "sistema", "proj", "geos", "gdal"):
            self.assertTrue(e.get(clave), clave)

    def test_codigo_coincide_con_procedencia(self):
        from scripts.t05_relieve import codigo_coincide, procedencia
        p = procedencia(self.dataset)
        self.assertTrue(codigo_coincide(p))
        p["codigo_sha256"]["scripts/t05_relieve.py"] = "0" * 64   # p. ej., copia de trabajo en CRLF
        self.assertFalse(codigo_coincide(p))
        self.assertFalse(codigo_coincide({}))


class TablasReconstruidas(_DatasetTemporal, unittest.TestCase):
    """comprobar_tablas rehace los resúmenes desde las celdas (auditoría de 2026-10-08)."""

    def setUp(self):
        super().setUp()
        from scripts.t05_relieve import extraer, leer_csv
        self.tiff("Elevacion_INEGI_CEM4_120m.tif", [[2500, 2600], [2700, 2800]])
        self.tiff("Pendiente_INEGI_CEM4_120m_grados.tif", [[1, -9999], [3, 4]])
        self.shapefile([box(X0+24, Y0-100, X0+144, Y0-20),           # AGC_002: dos celdas, pendiente parcial.
                        box(X0+130, Y0-230, X0+230, Y0-130),         # AGC_001: completa.
                        box(X0+1000, Y0-50, X0+1050, Y0-10)],        # AGC_003: fuera del mapa.
                       ["AGC_002", "AGC_001", "AGC_003"])
        self.origen = self.raiz / "extraccion"
        extraer(self.dataset, self.origen)
        self.filas = leer_csv(self.origen / "relieve_parcela.csv")
        self.celdas = leer_csv(self.origen / "relieve_celdas.csv")

    def fila(self, id_parcela):
        return next(f for f in self.filas if f["id_parcela"] == id_parcela)

    def comprobar(self):
        from scripts.t05_relieve import comprobar_tablas
        return comprobar_tablas(self.filas, self.celdas)

    def test_entrega_correcta_pasa_incluida_parcela_fuera_del_mapa(self):
        self.assertEqual(self.fila("AGC_003")["estado_elevacion"], "sin_cobertura_espacial")
        self.assertFalse(any(c["id_parcela"] == "AGC_003" for c in self.celdas))
        self.assertLessEqual(self.comprobar()["max_diferencia_area_relativa"], 1e-6)

    def test_media_de_elevacion_alterada_se_detecta(self):
        self.fila("AGC_002")["elevacion_media_m"] = "99999"
        with self.assertRaisesRegex(ValueError, "reconstruido distinto: AGC_002 elevacion_media_m"):
            self.comprobar()

    def test_columna_para_t10_alterada_se_detecta(self):
        self.fila("AGC_001")["pendiente_media_t10_grados"] = "99"
        with self.assertRaisesRegex(ValueError, "pendiente_media_t10_grados"):
            self.comprobar()

    def test_t10_con_valor_donde_el_piso_exige_vacio_se_detecta(self):
        f = self.fila("AGC_002")
        f["pendiente_cobertura_valida"] = "0.3"           # Contradice las celdas.
        with self.assertRaisesRegex(ValueError, "pendiente_cobertura_valida"):
            self.comprobar()

    def test_valores_no_finitos_se_rechazan(self):
        for raro in ("inf", "-inf", "nan"):
            with self.subTest(raro):
                f = self.fila("AGC_001")
                original = f["elevacion_media_m"]
                f["elevacion_media_m"] = raro
                with self.assertRaisesRegex(ValueError, "no finito"):
                    self.comprobar()
                f["elevacion_media_m"] = original

    def test_celda_alterada_se_detecta(self):
        c = next(c for c in self.celdas if c["id_parcela"] == "AGC_001")
        c["elevacion_m"] = "5000.0"
        with self.assertRaisesRegex(ValueError, "AGC_001"):
            self.comprobar()

    def test_celda_con_infinito_se_rechaza(self):
        c = next(c for c in self.celdas if c["id_parcela"] == "AGC_001")
        c["pendiente_grados"] = "inf"
        with self.assertRaisesRegex(ValueError, "no finito"):
            self.comprobar()

    def test_bandera_de_validez_incoherente(self):
        c = next(c for c in self.celdas if c["id_parcela"] == "AGC_001")
        c["elevacion_valida"] = "False"                   # Con valor presente.
        with self.assertRaisesRegex(ValueError, "incoherentes"):
            self.comprobar()

    def test_celdas_faltantes_de_parcela_con_cobertura_se_detectan(self):
        self.celdas = [c for c in self.celdas if c["id_parcela"] != "AGC_001"]
        with self.assertRaisesRegex(ValueError, "Celdas distintas entre tablas: AGC_001"):
            self.comprobar()

    def test_parcela_vacia_solo_si_el_resumen_lo_declara(self):
        f = self.fila("AGC_003")
        f["estado_elevacion"] = "cobertura_completa"      # Dice completa pero no hay celdas.
        with self.assertRaisesRegex(ValueError, "AGC_003 estado_elevacion"):
            self.comprobar()

    def test_celdas_de_parcela_desconocida(self):
        extra = dict(self.celdas[0], id_parcela="AGC_999")
        self.celdas.append(extra)
        with self.assertRaisesRegex(ValueError, "no están en el resumen"):
            self.comprobar()

    def test_celda_duplicada(self):
        self.celdas.append(dict(self.celdas[0]))
        with self.assertRaisesRegex(ValueError, "duplicada"):
            self.comprobar()

    def test_publicar_rechaza_una_extraccion_alterada(self):
        from scripts.t05_relieve import publicar
        ruta = self.origen / "relieve_parcela.csv"
        t02 = self.raiz / "t02"
        t02.mkdir()
        (t02 / "catalogo.csv").write_text(
            "id_parcela,conjunto_origen\nAGC_001,PREDICCION\nAGC_002,ENTRENAMIENTO\nAGC_003,ENTRENAMIENTO\n",
            encoding="utf-8")
        (t02 / "soporte.csv").write_text(
            "id_parcela,cobertura_elevacion,cobertura_pendiente\nAGC_001,1.0,1.0\nAGC_002,1.0,0.8\nAGC_003,0.0,0.0\n",
            encoding="utf-8")
        texto = ruta.read_text(encoding="utf-8").replace("2800.0", "99999.0", 1)
        ruta.write_text(texto, encoding="utf-8", newline="")
        destino = self.raiz / "registro_t05"
        with self.assertRaisesRegex(ValueError, "reconstruido distinto|no finito"):
            publicar(self.dataset, self.origen, destino, t02 / "soporte.csv", t02 / "catalogo.csv")
        self.assertFalse(destino.exists())


if __name__ == "__main__":
    unittest.main()
