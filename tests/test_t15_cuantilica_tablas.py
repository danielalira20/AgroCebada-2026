"""Oráculos de denominadores: error por parcela y R² no definido."""
import math
import unittest
from scripts.t15_cuantilica_verificar_tablas import verificar_metricas


class TablasTests(unittest.TestCase):
    def test_errores_no_promedio_de_predicciones(self):
        rows=[dict(ID_POLIGONO=i,repeticion=r,real=y,prediccion=p) for i,r,y,p in [
            ('a',1,0,-2),('a',2,0,2),('b',1,2,2),('b',2,2,2)]]
        expected=dict(n_parcelas=2,n_predicciones=4,n_repeticiones=2,MAE_por_parcela=1,
            RMSE_igual_peso_parcela=math.sqrt(2),sesgo_por_parcela=0,R2_igual_peso_parcela=-1,
            MAE_media_repeticiones=1,RMSE_media_repeticiones=math.sqrt(2),R2_media_repeticiones=-1,
            p90_MAE_parcela=1.8,n_parcelas_MAE_mayor_1=1)
        verificar_metricas(rows,expected)
        expected['MAE_por_parcela']=0
        with self.assertRaises(ValueError):verificar_metricas(rows,expected)

    def test_desigual_numero_repeticiones_no_cambia_peso_por_ID(self):
        rows=[dict(ID_POLIGONO=i,repeticion=r,real=y,prediccion=p) for i,r,y,p in [
            ('a',1,0,2),('b',1,2,2),('b',2,2,2),('b',3,2,2)]]
        expected=dict(n_parcelas=2,n_predicciones=4,n_repeticiones=3,MAE_por_parcela=1,
            RMSE_igual_peso_parcela=math.sqrt(2),sesgo_por_parcela=1,R2_igual_peso_parcela=-1,
            MAE_media_repeticiones=1/3,RMSE_media_repeticiones=math.sqrt(2)/3,R2_media_repeticiones='',
            p90_MAE_parcela=1.8,n_parcelas_MAE_mayor_1=1)
        verificar_metricas(rows,expected)

    def test_R2_constante_vacio_no_cero_artificial(self):
        rows=[dict(ID_POLIGONO='a',repeticion=1,real=4.63,prediccion=4.83)]*7
        expected=dict(n=7,MAE=.2,RMSE=.2,sesgo=.2,R2='')
        verificar_metricas(rows,expected,individual=True)
        expected['R2']=0
        with self.assertRaises(ValueError):verificar_metricas(rows,expected,individual=True)


if __name__=='__main__':unittest.main()
