"""Reglas de borde/ausencia del centroide y auditoría independiente de CSV."""
import csv
import json
from pathlib import Path
import tempfile
import unittest

from affine import Affine
import numpy as np
from rasterio.crs import CRS
from shapely.geometry import box, MultiPolygon

from scripts.extraer_clima import (Cuadricula, Mapa, VARIABLES, PERIODOS, UNIDADES,
    extraer, preparar_soportes, publicar_local)
from scripts.t04_espacio import firma_cuadricula, huella_json
from scripts.t04_control import (celda_punto, preparar_centroides, comparar_centroide,
    seleccionar_piloto, controlar_medias, validar_exportacion)

Q = Cuadricula(CRS.from_epsg(4326), Affine(.05,0,-99,0,-.05,20), 2,2)
G = box(-98.99,19.955,-98.94,19.995)


class ControlTests(unittest.TestCase):
    def mapas(self, mask=False):
        return {(v,"2025-07"): Mapa(Q,np.ma.array([[100,200],[300,400]],mask=mask),
                   {"variable":v,"periodo":"2025-07","unidad":UNIDADES[v],
                    "cuadricula_id":huella_json(firma_cuadricula(Q)),"sha256_raster":v,"celdas_validas":4}) for v in VARIABLES}

    def parcelas(self):
        return [{"id_parcela":"A","geometria":G,"area_ha_origen":7.44},
                {"id_parcela":"B","geometria":box(-98,19,-97,20),"area_ha_origen":8.0}]

    def test_bordes_internos_derecha_abajo_sin_mover_punto(self):
        x,y=Q.transform@(1,1)
        self.assertEqual(celda_punto(x,y,Q),(1,1))
        self.assertEqual(celda_punto(np.nextafter(x,-np.inf),np.nextafter(y,np.inf),Q),(0,0))
        self.assertEqual(celda_punto(np.nextafter(x,np.inf),np.nextafter(y,-np.inf),Q),(1,1))

    def test_limites_exteriores_superior_izquierdo_incluidos(self):
        x,y=Q.transform@(0,0)
        self.assertEqual(celda_punto(x,y,Q),(0,0))
        x,y=Q.transform@(2,2)
        self.assertEqual(celda_punto(x,y,Q),(2,2))
        self.assertEqual(celda_punto(np.nextafter(-99,-np.inf),20,Q),(0,-1))

    def test_borde_transformacion_no_representable_sin_epsilon(self):
        q=Cuadricula(Q.crs,Affine(.05000000074505806,0,-99.94999880716205,0,-.05000000074505806,21.39999957382679),65,72)
        for f,c in [(1,1),(31,33),(72,65)]:
            x,y=q.transform@(c,f)
            self.assertEqual(celda_punto(x,y,q),(f,c))

    def test_centroide_nodata_fuera_mapa_y_no_finito(self):
        m=self.mapas()["PREC","2025-07"]
        c={"fila_centroide":0,"columna_centroide":0,"centroide_en_mapa":True}
        self.assertEqual(comparar_centroide(c,m,120)["diferencia_media_menos_centroide"],20)
        m.datos.mask=np.array([[True,False],[False,False]])
        a=comparar_centroide(c,m,120)
        self.assertEqual(a["estado_centroide"],"nodata")
        self.assertIsNone(a["diferencia_abs_centroide"])
        c["centroide_en_mapa"]=False
        self.assertEqual(comparar_centroide(c,m,None)["estado_centroide"],"fuera_raster")
        m.datos=np.ma.array([[float('nan'),1],[2,3]],mask=False)
        c["centroide_en_mapa"]=True
        with self.assertRaisesRegex(ValueError,"no finito"):
            comparar_centroide(c,m,120)

    def test_multiparte_centroide_fuera_no_se_sustituye(self):
        g=MultiPolygon([box(-98.999,19.951,-98.989,19.961),box(-98.921,19.951,-98.911,19.961)])
        ps=[{"id_parcela":"A","geometria":g,"area_ha_origen":1}]
        cen=preparar_centroides(ps,self.mapas())["A",huella_json(firma_cuadricula(Q))]
        self.assertFalse(cen["centroide_dentro_parcela"])
        self.assertGreater(cen["centroide_lon"],-98.989)
        self.assertLess(cen["centroide_lon"],-98.921)

    def escenario(self,d):
        ps,ms=self.parcelas(),self.mapas()
        s,c=preparar_soportes(ps,ms)
        filas,valores=extraer(ps,ms,s,["A","B"],["2025-07"])
        man={"alcance":"prueba sintética","modo":"muestra","mapas":[m.meta for m in ms.values()],
             "seleccion":{"ids":["A","B"],"periodos":["2025-07"]}}
        destino=Path(d)/"prueba"
        publicar_local(destino,man,s,c,filas,valores,verificar=True,mapas=ms,
                       controles_medias=controlar_medias(ps,ms,s,c,filas))
        return destino,ms

    def test_exportacion_reconstruye_y_contrasta_originales(self):
        with tempfile.TemporaryDirectory() as d:
            p,m=self.escenario(d)
            c=validar_exportacion(p,m)
            self.assertEqual(c["filas_clima"],6)
            self.assertEqual(c["max_error_reconstruccion"],0)
            self.assertTrue(c["mascaras_valores_contrastados_original"])
            self.assertEqual(c["estados"]["sin_cobertura_espacial"],3)

    def modificar(self,p,campo,valor):
        with p.open() as f:filas=list(csv.DictReader(f))
        filas[0][campo]=valor
        with p.open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(filas[0]));w.writeheader();w.writerows(filas)

    def test_media_modificada_en_csv_se_detecta(self):
        with tempfile.TemporaryDirectory() as d:
            p,m=self.escenario(d)
            self.modificar(p/'clima_parcela_mes.csv','media_ponderada','999')
            with self.assertRaisesRegex(ValueError,"Reconstrucción"):
                validar_exportacion(p,m)

    def test_valor_de_celda_modificado_se_detecta_con_fuente(self):
        with tempfile.TemporaryDirectory() as d:
            p,m=self.escenario(d)
            self.modificar(p/'valores_celdas.csv','valor','999')
            with self.assertRaisesRegex(ValueError,"Reconstrucción"):
                validar_exportacion(p,m)

    def test_clave_duplicada_o_perdida_exportada_se_detecta(self):
        with tempfile.TemporaryDirectory() as d:
            p,m=self.escenario(d)
            self.modificar(p/'clima_parcela_mes.csv','id_parcela','B')
            with self.assertRaisesRegex(ValueError,"claves"):
                validar_exportacion(p,m)

    def test_mapa_constante_con_celdas_multiples_y_nodata_parcial(self):
        ps=self.parcelas()
        ms=self.mapas()
        for m in ms.values():
            m.datos=np.ma.array([[11.25,11.25],[11.25,11.25]],mask=[[False,True],[False,False]])
        s,c=preparar_soportes(ps,ms)
        filas,_=extraer(ps,ms,s,["A"],["2025-07"])
        self.assertTrue(all(abs(r["media_ponderada"]-11.25)<1e-12 for r in filas))
        self.assertTrue(all(r["estado"]=="cobertura_parcial" for r in filas))
        self.assertEqual(controlar_medias(ps,ms,s,c,filas)["filas_comprobadas"],3)

    def test_piloto_no_depende_de_valores(self):
        ps=self.parcelas();base=self.mapas();ms={}
        for v in VARIABLES:
            for periodo in PERIODOS:
                m=base[v,"2025-07"]
                ms[v,periodo]=Mapa(Q,m.datos.copy(),{**m.meta,"periodo":periodo})
        s,_=preparar_soportes(ps,ms);cen=preparar_centroides(ps,ms)
        antes=seleccionar_piloto(ps,ms,s,cen)
        for m in ms.values():m.datos.data[:]=999999
        self.assertEqual(antes,seleccionar_piloto(ps,ms,s,cen))
        self.assertIn("sin cobertura espacial",antes[2]["razones_por_id"]["B"])


if __name__ == '__main__':
    unittest.main()
