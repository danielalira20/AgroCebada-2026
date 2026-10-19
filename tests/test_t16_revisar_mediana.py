"""Controles de software; los ejemplos numéricos no son datos agrícolas del reto."""
import unittest
from fractions import Fraction
from pathlib import Path

from scripts.t16_revisar_mediana import ROOT, bootstrap_celdas, ejecutar, metricas, referencia, resumen


class RevisarMedianaTests(unittest.TestCase):
    def setUp(self):
        self.table={
            'a':dict(municipio='M',cultivo_origen='g',rendimiento_t_ha='1'),
            'b':dict(municipio='M',cultivo_origen='g',rendimiento_t_ha='2'),
            'c':dict(municipio='M',cultivo_origen='g',rendimiento_t_ha='9'),
            'objetivo':dict(municipio='M',cultivo_origen='g',rendimiento_t_ha='100'),
            'grupo':dict(municipio='N',cultivo_origen='g',rendimiento_t_ha=''),
            'global':dict(municipio='N',cultivo_origen='z',rendimiento_t_ha=''),
        }

    def test_media_y_mediana_exactas(self):
        self.assertEqual(referencia(['a','b','c'],'objetivo',self.table,'media')[0],Fraction(4))
        self.assertEqual(referencia(['a','b','c'],'objetivo',self.table,'mediana')[0],Fraction(2))

    def test_mediana_par_y_orden(self):
        self.assertEqual(referencia(['a','b'],'objetivo',self.table,'mediana')[0],Fraction(3,2))
        self.assertEqual(referencia(['b','a'],'objetivo',self.table,'mediana')[0],Fraction(3,2))

    def test_no_lee_etiqueta_objetivo(self):
        a=referencia(['a','b','c'],'objetivo',self.table,'mediana')
        self.table['objetivo']['rendimiento_t_ha']='-999999'
        self.assertEqual(a,referencia(['a','b','c'],'objetivo',self.table,'mediana'))

    def test_solo_lee_entrenamiento(self):
        a=referencia(['a','b'],'objetivo',self.table,'media')
        self.table['c']['rendimiento_t_ha']='-999999'
        self.assertEqual(a,referencia(['a','b'],'objetivo',self.table,'media'))

    def test_rechaza_objetivo_y_reservada_en_entrenamiento(self):
        for train in [['a','objetivo'],['a','grupo'],[],['a','a']]:
            with self.subTest(train=train),self.assertRaises(ValueError):
                referencia(train,'objetivo',self.table,'mediana')

    def test_respaldo_grupo_y_global(self):
        for pid,source in [('grupo','grupo'),('global','global')]:
            result,actual,pool=referencia(['a','b','c'],pid,self.table,'mediana')
            self.assertEqual((result,actual,pool),(Fraction(2),source,['a','b','c']))

    def test_una_etiqueta_municipal(self):
        self.assertEqual(referencia(['a'],'objetivo',self.table,'mediana'),(Fraction(1),'municipio',['a']))

    def test_metricas_a_mano(self):
        rows=[dict(real='0',prediccion='1'),dict(real='2',prediccion='3')]
        result=metricas(rows)
        self.assertEqual(result,dict(MAE=1.,RMSE=1.,R2=0.,sesgo=1.))

    def test_R2_constante_indefinido(self):
        self.assertIsNone(metricas([dict(real='1',prediccion='2')])['R2'])

    def test_id_y_registro_no_se_confunden(self):
        rows=[dict(ID_POLIGONO='a',repeticion='1',real='0',prediccion='0'),
              dict(ID_POLIGONO='a',repeticion='2',real='0',prediccion='0'),
              dict(ID_POLIGONO='b',repeticion='1',real='2',prediccion='4')]
        result=resumen(rows)
        self.assertEqual(result['MAE_por_parcela'],1.)
        self.assertEqual(result['MAE_media_repeticiones'],.5)

    def test_bootstrap_mantiene_celda_completa(self):
        _,draws=bootstrap_celdas({'a':1.,'b':1.,'c':-1.},{'a':'X','b':'X','c':'Y'},5000)
        self.assertEqual(set(round(float(v),9) for v in draws),{-1.,.333333333,1.})

    def test_salida_existente_y_protegida(self):
        with self.assertRaisesRegex(ValueError,'existe'):
            ejecutar(ROOT/'README.md')
        with self.assertRaisesRegex(ValueError,'reports'):
            ejecutar(ROOT/'registro/__no_crear_t16__')


if __name__=='__main__':
    unittest.main()
