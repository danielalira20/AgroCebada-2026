"""Casos de contrato: identidad, redondeo del umbral y ausencia real."""
import copy
import unittest
from scripts.t07_calidad_parcelas import validar


class CalidadParcelas(unittest.TestCase):
    def datos(self):
        cat=[dict(id_parcela=p,municipio='Municipio',rendimiento_t_ha=y,
                  contorno_categoria='A',contorno_angosta_o_muy_pequena='no')
             for p,y in [('a','1'),('b','2'),('c','')]]
        sup=[dict(id_parcela=p,municipio='Municipio',escalon_etiqueta_municipio='') for p in ('a','b','c')]
        pares=[dict(id_parcela_a='a',id_parcela_b='c',distancia_orillas_m='20.00',ambas_conocidas='no')]
        precision=[dict(agrupacion='municipio',grupo='Municipio',paso_comun='')]
        return cat,sup,pares,precision

    def test_umbral_seleccionado_antes_del_redondeo_y_sin_autovecina(self):
        filas,c=validar(*self.datos());idx={r['id_parcela']:r for r in filas}
        self.assertEqual(idx['a']['numero_vecinas_etiquetadas_menos_20m'],0)
        self.assertEqual(idx['c']['numero_vecinas_etiquetadas_menos_20m'],1)
        self.assertEqual(c['escalon_ausente'],['a','b','c'])

    def test_no_depende_de_valores_de_rendimiento_ni_orden(self):
        datos=self.datos();antes=validar(*datos)
        datos[0][0]['rendimiento_t_ha']='999'
        for filas in datos: filas.reverse()
        self.assertEqual(validar(*datos),antes)

    def test_pares_propios_duplicados_o_ajenos_rechazados(self):
        for a,b in [('a','a'),('c','a'),('a','ajena')]:
            datos=self.datos();datos[2].append(dict(id_parcela_a=a,id_parcela_b=b,distancia_orillas_m='1',ambas_conocidas='no'))
            with self.subTest(par=(a,b)),self.assertRaisesRegex(ValueError,'Par cercano'):
                validar(*datos)

    def test_precision_no_imputada_y_fuentes_contradictorias_rechazadas(self):
        datos=self.datos();datos[1][0]['escalon_etiqueta_municipio']='0.5'
        with self.assertRaisesRegex(ValueError,'Escalón T02 contradictorio'):validar(*datos)
        datos=self.datos();datos[3].append(copy.copy(datos[3][0]))
        with self.assertRaisesRegex(ValueError,'Precisión municipal'):validar(*datos)

    def test_soporte_ajeno_y_etiquetas_de_par_rechazados(self):
        datos=self.datos();datos[1].pop()
        with self.assertRaisesRegex(ValueError,'Soporte de calidad'):validar(*datos)
        datos=self.datos();datos[2][0]['ambas_conocidas']='si'
        with self.assertRaisesRegex(ValueError,'Condición de etiquetas'):validar(*datos)


if __name__=='__main__':unittest.main()
