"""Controles espaciales: bordes, NoData, áreas físicas y reutilización de pesos."""
import unittest
import numpy as np
from affine import Affine
from pyproj import Transformer
from rasterio.io import MemoryFile
from shapely import segmentize
from shapely.geometry import box, Polygon, MultiPolygon, GeometryCollection, Point, LineString
from shapely.ops import transform

from scripts.t04_espacio import area_fisica, preparar_pesos, aplicar_pesos

T = Affine(0.05,0,-99,0,-0.05,20)


class EspacioTests(unittest.TestCase):
    def raster(self, valores, t=T, crs="EPSG:4326"):
        memoria = MemoryFile()
        self.addCleanup(memoria.close)
        datos=np.asarray(valores,dtype="float32")
        r=memoria.open(driver="GTiff",height=datos.shape[0],width=datos.shape[1],
                       count=1,dtype="float32",crs=crs,nodata=-9999,transform=t)
        self.addCleanup(r.close)
        r.write(datos,1)
        return r

    def calcular(self, geom, valores):
        r=self.raster(valores)
        return aplicar_pesos(preparar_pesos(geom,"EPSG:4326",r),r)

    def test_ponderacion_80_20_fisica(self):
        # Misma franja latitudinal: 0.04° y 0.01°, no promedio simple 150.
        s=self.calcular(box(-98.99,19.955,-98.94,19.995),[[100,200]])
        self.assertAlmostEqual(s["media_ponderada"],120,places=5)
        self.assertAlmostEqual(s["cobertura_valida"],1,places=6)

    def test_nodata_parcial_no_equivale_a_cero(self):
        s=self.calcular(box(-98.99,19.955,-98.94,19.995),[[100,-9999]])
        self.assertEqual(s["media_ponderada"],100)
        self.assertAlmostEqual(s["cobertura_valida"],.8,places=6)
        self.assertEqual(s["celdas"][1]["valor"],None)
        self.assertEqual(s["celdas"][1]["peso_valido"],0)

    def test_contacto_lineal_no_aporta_area(self):
        s=self.calcular(box(-99,19.95,-98.95,20),[[100,900]])
        self.assertEqual([c["celda"] for c in s["celdas"]],["0_0"])
        self.assertEqual(s["media_ponderada"],100)

    def test_contacto_vertice_no_aporta_area(self):
        geom=Polygon([(-98.99,19.96),(-98.96,19.96),(-98.95,19.95)])
        s=self.calcular(geom,[[100,900],[700,500]])
        self.assertEqual([c["celda"] for c in s["celdas"]],["0_0"])

    def test_multiples_celdas(self):
        s=self.calcular(box(-99,19.90,-98.90,20),[[10,20],[30,40]])
        self.assertEqual(len(s["celdas"]),4)
        self.assertAlmostEqual(sum(c["peso_valido"] for c in s["celdas"]),1)
        self.assertAlmostEqual(s["cobertura_valida"],1,places=6)
        self.assertGreater(s["media_ponderada"],25) # Franja sur tiene mayor área física.

    def test_cobertura_espacial_parcial(self):
        s=self.calcular(box(-99.025,19.955,-98.975,19.995),[[100,200]])
        self.assertAlmostEqual(s["cobertura_valida"],.5,places=6)
        self.assertEqual(s["media_ponderada"],100)

    def test_sin_cobertura_rechazado(self):
        r=self.raster([[100,200]])
        with self.assertRaisesRegex(ValueError,"sin cobertura espacial"):
            preparar_pesos(box(-98,19,-97,20),4326,r)

    def test_todo_nodata_rechazado(self):
        with self.assertRaisesRegex(ValueError,"todo NoData"):
            self.calcular(box(-99,19.95,-98.9,20),[[-9999,-9999]])

    def test_crs_incompatible_rechazado(self):
        r=self.raster([[100,200]])
        with self.assertRaisesRegex(ValueError,"CRS incompatible"):
            preparar_pesos(box(-99,19.95,-98.9,20),3857,r)

    def test_cuadricula_desplazada_no_reutiliza_pesos(self):
        geom=box(-99,19.95,-98.9,20)
        r=self.raster([[100,200]])
        soporte=preparar_pesos(geom,4326,r)
        distinto=self.raster([[100,200]],Affine(.05,0,-99,0,-.05,20-2.980232238769531e-7))
        with self.assertRaisesRegex(ValueError,"Cuadrícula distinta"):
            aplicar_pesos(soporte,distinto)

    def test_reutilizacion_revisa_nodata_del_mes(self):
        geom=box(-98.99,19.955,-98.94,19.995)
        r=self.raster([[100,200]])
        soporte=preparar_pesos(geom,4326,r)
        s=aplicar_pesos(soporte,self.raster([[-9999,200]]))
        self.assertEqual(s["media_ponderada"],200)
        self.assertAlmostEqual(s["cobertura_valida"],.2,places=6)
        self.assertNotIn("valida",soporte["celdas"][0])

    def test_huecos_multipoligonos_y_colecciones(self):
        externo=box(-99,19.95,-98.95,20)
        hueco=box(-98.99,19.96,-98.96,19.99)
        con_hueco=Polygon(externo.exterior.coords,[hueco.exterior.coords])
        esperado=area_fisica(externo)-area_fisica(hueco)
        self.assertAlmostEqual(area_fisica(con_hueco),esperado,places=2)
        otro=box(-98.94,19.96,-98.93,19.97)
        esperado+=area_fisica(otro)
        self.assertAlmostEqual(area_fisica(MultiPolygon([con_hueco,otro])),esperado,places=2)
        coleccion=GeometryCollection([con_hueco,otro,Point(-99,20),LineString([(-99,20),(-98,20)])])
        self.assertAlmostEqual(area_fisica(coleccion),esperado,places=2)
        r=self.raster([[100,200]])
        s=aplicar_pesos(preparar_pesos(con_hueco,4326,r),r)
        self.assertAlmostEqual(s["cobertura_valida"],1,places=6)

    def test_area_contraste_proyeccion_equivalente(self):
        # Método independiente: proyección LAEA elipsoidal con bordes densificados.
        geom=Polygon([(-99,19.95),(-98.95,19.96),(-98.96,20)])
        tr=Transformer.from_crs(4326,"+proj=laea +lat_0=20 +lon_0=-99 +ellps=WGS84 +units=m",always_xy=True)
        referencia=transform(tr.transform,segmentize(geom,0.0001)).area
        self.assertLess(abs(area_fisica(geom)-referencia)/referencia,1e-6)

    def test_geometria_invalida_no_se_repara_silenciosamente(self):
        geom=Polygon([(-99,20),(-98.9,19.9),(-99,19.9),(-98.9,20)])
        with self.assertRaisesRegex(ValueError,"Geometría parcelaria"):
            preparar_pesos(geom,4326,self.raster([[100,200]]))

    def test_valor_no_finito_rechazado(self):
        with self.assertRaisesRegex(ValueError,"no finito"):
            self.calcular(box(-99,19.95,-98.95,20),[[float('nan'),100]])


if __name__ == "__main__":
    unittest.main()
