"""Casos de transferencia, cobertura y auditoría independiente de las celdas reales."""
from copy import deepcopy
from pathlib import Path
import unittest

from scripts.t07_fuentes import leer_csv, validar_catalogo
from scripts.t07_preparar import T02
from scripts.t07_relieve import validar, incorporar, CANDIDATAS, CALIDAD, diccionario
from scripts.t07_auditar_relieve import auditar

RAIZ=Path(__file__).resolve().parents[1]


class Relieve(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _,cat=leer_csv(RAIZ/T02/'tablas/catalogo_parcelas.csv')
        cls.cat=validar_catalogo(cat)
        cls.cols,cls.resumen=leer_csv(RAIZ/'registro/t05/relieve_parcela.csv')
        _,cls.celdas=leer_csv(RAIZ/'registro/t05/relieve_celdas.csv')

    def unir(self,resumen=None):
        indice,q=validar(self.cols,resumen or self.resumen,self.cat)
        return incorporar(tuple(self.cat[0]),self.cat,indice)[1],q

    def test_universo_literal_calidad_y_dos_ausencias(self):
        tabla,q=self.unir()
        self.assertEqual(len(tabla),197);self.assertEqual(len(q),197)
        ausentes=[r['id_parcela'] for r in tabla if r['pendiente_media_t10_grados']=='']
        self.assertEqual(ausentes,['AGC_023','AGC_170'])
        reservadas=[r for r in tabla if r['conjunto_origen']=='PREDICCION']
        self.assertEqual(len(reservadas),59)
        self.assertTrue(all(r['rendimiento_t_ha']=='' for r in reservadas))
        outside=next(r for r in q if r['id_parcela']=='AGC_182')
        self.assertEqual(outside['centroide_dentro_parcela'],'False')
        self.assertIn('centroide',outside['avisos'])

    def test_orden_fuente_no_cambia_tabla(self):
        self.assertEqual(self.unir(),self.unir(list(reversed(self.resumen))))

    def test_claves_duplicadas_ausentes_ajenas_rechazadas(self):
        for rows in [self.resumen[:-1],self.resumen[:-1]+[self.resumen[0]],
                     [{**self.resumen[0],'id_parcela':'AJENA'},*self.resumen[1:]]]:
            with self.subTest():
                with self.assertRaisesRegex(ValueError,'IDs T05'):validar(self.cols,rows,self.cat)

    def test_no_rellena_pendiente_bajo_piso(self):
        rows=deepcopy(self.resumen);r=next(r for r in rows if r['id_parcela']=='AGC_023')
        r['pendiente_media_t10_grados']=r['pendiente_media_grados']
        with self.assertRaisesRegex(ValueError,'D020'):validar(self.cols,rows,self.cat)

    def test_tolerancia_solo_al_redondeo_de_cobertura(self):
        rows=deepcopy(self.resumen);rows[0]['cobertura_espacial']='1.00000001'
        with self.assertRaisesRegex(ValueError,'cobertura espacial'):validar(self.cols,rows,self.cat)

    def test_no_finito_rechazado(self):
        rows=deepcopy(self.resumen);rows[0]['elevacion_media_m']='nan'
        with self.assertRaises(ValueError):validar(self.cols,rows,self.cat)

    def test_colision_y_union_incompleta_rechazadas(self):
        idx,_=validar(self.cols,self.resumen,self.cat)
        with self.assertRaisesRegex(ValueError,'Colisión'):incorporar(CANDIDATAS,self.cat,idx)
        with self.assertRaisesRegex(ValueError,'claves'):incorporar(tuple(self.cat[0]),self.cat[:-1],idx)

    def test_auditoria_decimal_394_medias_y_2253_celdas(self):
        tabla,q=self.unir();a=auditar(tabla,q,self.resumen,self.celdas)
        self.assertEqual(a['medias_recalculadas'],394);self.assertEqual(a['celdas'],2253)
        self.assertEqual(a['controles']['reservadas_incompletas'],[])
        self.assertEqual(a, auditar(list(reversed(tabla)),list(reversed(q)),list(reversed(self.resumen)),list(reversed(self.celdas))))

    def test_auditoria_detecta_media_alterada_aun_si_copia_coincide(self):
        rows=deepcopy(self.resumen);rows[0]['elevacion_media_m']=str(float(rows[0]['elevacion_media_m'])+0.1)
        tabla,q=self.unir(rows)
        with self.assertRaisesRegex(ValueError,'media ponderada'):auditar(tabla,q,rows,self.celdas)

    def test_auditoria_detecta_celda_duplicada_y_peso_cambiado(self):
        tabla,q=self.unir()
        with self.assertRaisesRegex(ValueError,'duplicada'):auditar(tabla,q,self.resumen,self.celdas+[self.celdas[0]])
        c=deepcopy(self.celdas);c[0]['area_interseccion_m2']=str(float(c[0]['area_interseccion_m2'])*2)
        with self.assertRaisesRegex(ValueError,'balance espacial'):auditar(tabla,q,self.resumen,c)

    def test_auditoria_detecta_mascara_contradictoria(self):
        tabla,q=self.unir();c=deepcopy(self.celdas);c[0]['elevacion_valida']='False'
        with self.assertRaisesRegex(ValueError,'máscara y dato'):auditar(tabla,q,self.resumen,c)

    def test_auditoria_detecta_transferencia_y_calidad_alteradas(self):
        tabla,q=self.unir();tabla[0]['elevacion_media_m']='0'
        with self.assertRaisesRegex(ValueError,'candidato alterado'):auditar(tabla,q,self.resumen,self.celdas)
        tabla,q=self.unir();q[0]['cobertura_espacial']='0'
        with self.assertRaisesRegex(ValueError,'calidad alterada'):auditar(tabla,q,self.resumen,self.celdas)

    def test_etiquetas_no_intervienen_en_candidatas(self):
        indice,_=validar(self.cols,self.resumen,self.cat)
        cat=[{**r,'rendimiento_t_ha':'999'} for r in self.cat]
        _,a=incorporar(tuple(self.cat[0]),self.cat,indice);_,b=incorporar(tuple(cat[0]),cat,indice)
        self.assertEqual([{c:r[c] for c in CANDIDATAS} for r in a],[{c:r[c] for c in CANDIDATAS} for r in b])

    def test_diccionario_separa_original_y_candidata(self):
        d=diccionario();self.assertEqual(len(d),26)
        self.assertEqual({r['columna'] for r in d if r['archivo']=='calidad_relieve.csv'},set(CALIDAD))
        self.assertEqual({r['columna'] for r in d if r['funcion']=='predictor_candidato'},set(CANDIDATAS))
        self.assertTrue(all(r['significado_vacio']=='No permitido' for r in d if r['columna'].endswith('_celdas_validas')))


if __name__=='__main__':unittest.main()
