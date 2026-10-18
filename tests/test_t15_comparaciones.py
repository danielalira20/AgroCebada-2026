"""Contrato, divisiones reales y selección trazada; no produce OOF completas."""
import copy
import json
import unittest
import warnings
from unittest.mock import patch

import numpy as np

from scripts import t15_comparaciones_contrato as contrato
from scripts import t15_comparaciones_traza as traza
from scripts import evaluacion_comun_centrado_loo as v3
from scripts.evaluacion_comun_modelo import preparar_contexto, divisiones_internas, clave_opcion, NULLABLE


class ContratoComparaciones(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.c, cls.e = contrato.cargar()
        cls.pre = contrato.preflight(cls.e)

    def test_identidad_y_presupuesto(self):
        r = contrato.validar(self.c, self.e)
        self.assertEqual((r['procedimientos'], r['opciones_con_variables']), (8, 60))
        self.assertEqual((self.pre['etiquetadas'], self.pre['reservadas'],
                          self.pre['divisiones_internas'], self.pre['modelos_ajustados']), (138,59,200,0))

    def test_nunca_habilita_por_booleano(self):
        c = copy.deepcopy(self.c)
        c['ejecucion_habilitada'] = True
        with self.assertRaises(ValueError): contrato.validar(c, self.e)
        with self.assertRaisesRegex(ValueError, 'no habilitada'): contrato.exigir_ejecucion(c)

    def test_fuente_alterada_falla(self):
        c=copy.deepcopy(self.c)
        c['fuentes_sha256']['registro/t03/particiones.csv']='0'*64
        with self.assertRaisesRegex(ValueError,'Fuente'): contrato.validar(c,self.e)

    def test_mutaciones_reglas_poblacion_parametros_rechazadas(self):
        casos=[('decision','promocion',{'dMAE_max':-.001}),
               ('poblacion','reservadas',58),('poblacion','corte','2025-12-31'),
               ('metodo','lambda',[.001,.01,.1,1.,10.]),
               ('principal','desempate',['mayor_lambda']),
               ('principal','escenarios',['A']),
               ('principal','referencia_sola_por_procedimiento',False)]
        for seccion, llave, valor in casos:
            c=copy.deepcopy(self.c); c[seccion][llave]=valor
            with self.subTest(llave=llave), self.assertRaises(ValueError): contrato.validar(c,self.e)

    def test_menu_columnas_y_ventanas_no_se_amplian(self):
        for cambio in ['columna','ventana','bloque','contraste']:
            c=copy.deepcopy(self.c)
            if cambio=='columna':c['principal']['procedimientos'][0]['opciones'][0]['columnas'].append('rendimiento_t_ha')
            elif cambio=='ventana':c['principal']['procedimientos'][0]['opciones'][0]['ventana']='nov_dic'
            elif cambio=='bloque':c['principal']['procedimientos'].append(copy.deepcopy(c['principal']['procedimientos'][0]))
            else:c['principal']['contrastes_planificados']=[]
            with self.subTest(cambio=cambio),self.assertRaises(ValueError):contrato.validar(c,self.e)

    def test_extensiones_no_habilitadas_y_SG_exacto(self):
        for nombre in ['SG','Q_E1','cuantil']:
            c=copy.deepcopy(self.c);c['extensiones_no_incluidas_en_principal'][nombre]['ejecutable']=True
            with self.subTest(nombre=nombre),self.assertRaises(ValueError):contrato.validar(c,self.e)
        self.assertEqual(len(self.c['extensiones_no_incluidas_en_principal']['SG']['opciones']),8)

    def test_propuesta_historica_sigue_no_ejecutable(self):
        with self.assertRaisesRegex(ValueError,'pendiente'):
            v3.validar_experimento(contrato.experimento_para_revision(self.c),self.e)

    def test_no_se_inventan_aprobaciones(self):
        c=copy.deepcopy(self.c);c['puertas_pendientes'][0]['estado']='aprobado'
        with self.assertRaises(ValueError):contrato.validar(c,self.e)

    def test_200_divisiones_cubren_50_contextos(self):
        groups={}
        for t in self.pre['trazas']:
            key=(t['escenario'],t['repeticion'],t['particion'])
            groups.setdefault(key,[]).append(t)
            self.assertTrue(set(t['ids_entrenamiento']).isdisjoint(t['ids_validacion']))
            self.assertTrue(set(t['ids_entrenamiento']).isdisjoint(t['ids_evaluacion_externa']))
            self.assertTrue(set(t['ids_validacion']).isdisjoint(t['ids_evaluacion_externa']))
            self.assertTrue(set(t['ids_validacion']).isdisjoint(self.e['reservados']))
            self.assertEqual(t['n_elegibles']+t['n_respaldados'],t['n_validacion'])
            self.assertGreater(t['n_pendientes_observadas'],0)
        self.assertEqual(len(groups),50)
        for values in groups.values():
            self.assertEqual(len(values),4)
            valid=[i for t in values for i in t['ids_validacion']]
            union=set(values[0]['ids_entrenamiento'])|set(values[0]['ids_validacion'])
            self.assertEqual(len(valid),len(set(valid)))
            self.assertEqual(set(valid),union)

    def test_preflight_independiente_de_rendimientos(self):
        e=copy.deepcopy(self.e)
        for row in e['tabla'].values():
            if row['rendimiento_t_ha']:row['rendimiento_t_ha']='99999'
        self.assertEqual(self.pre,contrato.preflight(e))

    def test_B_sin_celda_compartida(self):
        mapa={r['ID_POLIGONO']:r['celda_chirps'] for r in self.e['particiones']}
        for t in self.pre['trazas']:
            if t['escenario']=='B':
                a={mapa[i] for i in t['ids_entrenamiento']};b={mapa[i] for i in t['ids_validacion']}
                self.assertFalse(a&b)


class SeleccionTrazada(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.c,cls.e=contrato.cargar()
        cls.proc=next(p for p in cls.c['principal']['procedimientos'] if p['bloques']==['G'])
        cls.opciones=[dict(o,nombre=f"{o['ventana']}__lambda_{o['lambda_reg']:g}") for o in cls.proc['opciones']]
        cls.X,cls.y,cls.ext=preparar_contexto(cls.e,'A',1,0)

    def un_fit(self):
        d=divisiones_internas(self.X,'A')[0]
        tr,va=self.X.loc[list(d.entrenamiento)],self.X.loc[list(d.validacion)]
        return tr,va,d

    def test_selector_A_B_identico_v3(self):
        for esc in ['A','B']:
            X,y,_=preparar_contexto(self.e,esc,1,0)
            a=v3.seleccionar(X,y,self.opciones,esc)
            b=traza.seleccionar_con_traza(X,y,self.opciones,esc)
            self.assertEqual(a,{k:v for k,v in b.items() if k!='trazas'})
            self.assertEqual(len(b['trazas']),20)
            for t in b['trazas']:
                self.assertTrue(set(self.c['traza_obligatoria_por_fit'])<=set(t))
                self.assertEqual(sum(t['fuentes_referencia'].values()),t['n_validacion'])
                self.assertEqual(t['fuentes_referencia']['municipio'],t['n_elegibles'])
                self.assertEqual(t['alpha'],None if t['referencia_sola'] else t['n_entrenamiento']*t['lambda_reg'])

    def test_selector_temporal_ocho_opciones_identico(self):
        proc=next(p for p in self.c['principal']['procedimientos'] if p['bloques']==['S'])
        opciones=[dict(o,nombre=f"{o['ventana']}__lambda_{o['lambda_reg']:g}") for o in proc['opciones']]
        a=v3.seleccionar(self.X,self.y,opciones,'A')
        b=traza.seleccionar_con_traza(self.X,self.y,opciones,'A')
        self.assertEqual(a,{k:v for k,v in b.items() if k!='trazas'})
        self.assertEqual(len(b['trazas']),36)

    def test_fit_aislado_de_X_validacion_y_etiquetas_externas(self):
        tr,va,d=self.un_fit();op=self.opciones[0]
        m,p,t=traza.ajustar_y_trazar(tr,self.y.loc[tr.index],va,op,d.elegibles)
        alterada=va.copy();alterada['elevacion_media_m']+=10000;alterada['area_ha_origen']*=1000
        alterada[NULLABLE]=np.nan
        n,_,u=traza.ajustar_y_trazar(tr,self.y.loc[tr.index],alterada,op,d.elegibles)
        self.assertEqual(t['estado_modelo_sha256'],u['estado_modelo_sha256'])
        self.assertEqual(m.estado(),n.estado())
        self.assertAlmostEqual(t['mediana_pendiente'],float(tr[NULLABLE].median()))
        # y externa cambia en la tabla original; preparar_contexto nunca la entrega al fit.
        e=copy.deepcopy(self.e)
        for pid in self.ext.index:e['tabla'][(pid,)]['rendimiento_t_ha']='12345'
        X,y,ext=preparar_contexto(e,'A',1,0)
        self.assertTrue(X.equals(self.X));self.assertTrue(y.equals(self.y));self.assertTrue(ext.equals(self.ext))

    def test_lote_orden_estado_inmutables(self):
        tr,va,d=self.un_fit()
        m,p,t=traza.ajustar_y_trazar(tr,self.y.loc[tr.index],va,self.opciones[0],d.elegibles)
        estado=traza.huella(m.estado())
        individual=np.array([m.predict(va.loc[[pid]])[0] for pid in va.index])
        np.testing.assert_allclose(individual,p.prediccion,atol=1e-12,rtol=0)
        np.testing.assert_allclose(m.predict(va.iloc[::-1])[::-1],p.prediccion,atol=1e-12,rtol=0)
        self.assertEqual(estado,traza.huella(m.estado()))

    def test_pendiente_totalmente_ausente_es_fallo_explicito(self):
        tr,va,d=self.un_fit();tr=tr.copy();tr[NULLABLE]=np.nan
        with self.assertRaises(traza.ErrorAjuste) as cm:
            traza.ajustar_y_trazar(tr,self.y.loc[tr.index],va,self.opciones[0],d.elegibles)
        self.assertEqual(cm.exception.traza['estado'],'fallido')
        self.assertIn('totalmente ausente',cm.exception.traza['error'])

    def test_advertencia_detiene_y_queda_registrada(self):
        tr,va,d=self.un_fit()
        real=v3.CorreccionComunCentradaLOO.fit
        def advertir(model,X,y):
            warnings.warn('advertencia de prueba',RuntimeWarning)
            return real(model,X,y)
        with patch.object(v3.CorreccionComunCentradaLOO,'fit',advertir):
            with self.assertRaises(traza.ErrorAjuste) as cm:
                traza.ajustar_y_trazar(tr,self.y.loc[tr.index],va,self.opciones[0],d.elegibles)
        self.assertTrue(cm.exception.traza['advertencias'])

    def test_elegibles_falseados_rechazados(self):
        tr,va,d=self.un_fit()
        mask=tuple(not v for v in d.elegibles)
        with self.assertRaisesRegex(traza.ErrorAjuste,'Elegibles'):
            traza.ajustar_y_trazar(tr,self.y.loc[tr.index],va,self.opciones[0],mask)

    def test_fallo_no_se_omite_en_selector(self):
        with patch.object(v3.CorreccionComunCentradaLOO,'fit',side_effect=ValueError('fallo de prueba')):
            with self.assertRaisesRegex(traza.ErrorAjuste,'fallo de prueba'):
                traza.seleccionar_con_traza(self.X,self.y,self.opciones,'A')

    def test_empate_prioridades(self):
        base=dict(MAE=.3,referencia_sola=False,lambda_reg=.1,ventana='abr_oct',nombre='z')
        ref=dict(base,referencia_sola=True,lambda_reg=None,nombre='referencia_sola')
        self.assertLess(clave_opcion(ref),clave_opcion(base))
        self.assertLess(clave_opcion(dict(base,lambda_reg=10)),clave_opcion(base))
        self.assertLess(clave_opcion(dict(base,ventana='jun_oct')),clave_opcion(base))
        self.assertLess(clave_opcion(dict(base,nombre='a')),clave_opcion(base))
        self.assertLess(clave_opcion(dict(ref,MAE=.30000001)),clave_opcion(base))


if __name__=='__main__':unittest.main()
