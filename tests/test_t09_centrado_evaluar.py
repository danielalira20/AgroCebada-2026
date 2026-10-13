"""Regresiones de H3, aislamiento y consumidores v2; datos alterados sólo en memoria."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd
from sklearn.exceptions import NotFittedError

from scripts.t09_entradas import RAIZ, contexto_externo
from scripts.t09_estimadores import CLIMA, columnas_clima, crear_estimador
from scripts.t09_evaluar import contextos
from scripts.t09_seleccion import particiones_internas, _clave
from scripts.t09_centrado_evaluar import (contrato, seleccionar, evaluar_contexto,
                                        preparar_salida, reportes, ARCH_DISENO, ARCH_REGISTRO)
from scripts.t09_centrado_verificar import matriz
from scripts.t09_verificar_matrices import prepare


class ControlesAmpliados(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.e,cls.cfg,cls.reg=contrato()

    def test_todas_particiones_aislan_ids_reservadas_y_grupos(self):
        for esc,rep,fold in contextos(self.e):
            tr,_,te,_=contexto_externo(self.e,esc,rep,fold)
            partes=particiones_internas(tr,esc,self.e['configuracion'])
            vistos=[]
            self.assertFalse(set(tr.index)&set(te.index))
            self.assertFalse(set(tr.index)&set(self.e['reservadas'].index))
            for p in partes:
                a,b=tr.loc[list(p.entrenamiento)],tr.loc[list(p.validacion)]
                self.assertFalse(set(a.index)&set(b.index))
                self.assertFalse(set(a.index)&set(te.index));vistos.extend(b.index)
                esperado=np.ones(len(b),bool) if esc=='C' else b.municipio.isin(a.municipio)
                np.testing.assert_array_equal(p.elegibles,esperado)
                if esc!='A':
                    col='celda_chirps' if esc=='B' else 'municipio'
                    self.assertFalse(set(a[col])&set(b[col]))
            self.assertEqual(sorted(vistos),sorted(tr.index))

    def test_tres_escenarios_eligen_solo_ocho_opciones_registradas(self):
        for esc in ('A','B','C'):
            tr,y,_,_=contexto_externo(self.e,esc,1,0)
            s,_=seleccionar(tr,y,esc,self.cfg,self.e['configuracion'])
            self.assertEqual(s.n_ajustes,32)
            self.assertEqual(len(s.puntuaciones),8)
            q=min(s.puntuaciones.to_dict('records'),key=_clave)
            self.assertEqual((s.ventana,s.lambda_reg),(q['ventana'],q['lambda_reg']))
            self.assertEqual(set(s.puntuaciones.lambda_reg),{.01,.1,1,10})

    def test_contexto_externo_no_usa_sus_etiquetas_para_seleccion_ni_fit(self):
        r=evaluar_contexto(self.e,self.cfg,'A',1,0)
        e=dict(self.e);e['y']=self.e['y'].copy()
        _,_,te,_=contexto_externo(self.e,'A',1,0)
        e['y'].loc[te.index] += 1000
        alterado=evaluar_contexto(e,self.cfg,'A',1,0)
        self.assertEqual(r['estados'],alterado['estados'])
        pd.testing.assert_frame_equal(r['selecciones'],alterado['selecciones'])
        np.testing.assert_array_equal(r['oof'].prediccion,alterado['oof'].prediccion)
        self.assertFalse(np.array_equal(r['oof'].real,alterado['oof'].real))

    def test_centros_no_dependen_del_lote_predicho_ni_se_imponen_en_validacion(self):
        tr,y,te,_=contexto_externo(self.e,'A',1,0)
        m=crear_estimador('R_centrado','jun_oct',.01).fit(tr,y)
        original=m.predict(te.iloc[[0]])
        lote=te.copy();lote.loc[lote.index[1:],list(CLIMA)]+=100000
        np.testing.assert_array_equal(original,m.predict(lote)[:1])
        # Desplazar evaluación da una corrección legítima no necesariamente media cero.
        col=columnas_clima('jun_oct')[int(np.argmax(np.abs(m.coef_estandarizados_)))]
        moved=te.copy();moved[col]+=100
        esperado=100*m.coef_fisicos_[m.columnas_.index(col)]
        np.testing.assert_allclose(m.predict(moved)-m.predict(te),esperado,atol=1e-9,rtol=0)

    def test_unidades_fisicas_no_cambian_prediccion(self):
        tr,y,te,_=contexto_externo(self.e,'B',1,0)
        m=crear_estimador('R_centrado').fit(tr,y)
        a,b=tr.copy(),te.copy();c='prec_acumulada_mm_jun_oct'
        a[c]*=1000;b[c]*=1000
        q=crear_estimador('R_centrado').fit(a,y)
        np.testing.assert_allclose(m.predict(te),q.predict(b),atol=1e-9,rtol=0)

    def test_cambio_y_municipal_solo_cambia_referencia(self):
        tr,y,te,_=contexto_externo(self.e,'A',1,0)
        mun=tr.municipio.value_counts().index[0]
        cambiado=y.copy();cambiado.loc[tr.municipio.eq(mun)]+=20
        m=crear_estimador('R_centrado').fit(tr,y)
        q=crear_estimador('R_centrado').fit(tr,cambiado)
        np.testing.assert_allclose(m.coef_estandarizados_,q.coef_estandarizados_,atol=1e-10,rtol=0)
        tiene=te.municipio.eq(mun)
        np.testing.assert_allclose(q.predict(te[tiene])-m.predict(te[tiene]),20,atol=1e-9,rtol=0)

    def test_fallo_despues_del_escalado_borra_estado_parcial(self):
        tr,y,te,_=contexto_externo(self.e,'A',1,0)
        m=crear_estimador('R_centrado').fit(tr,y)
        with patch('scripts.t09_residual_centrado.Ridge.fit',side_effect=RuntimeError('fallo inducido')):
            with self.assertRaises(RuntimeError): m.fit(tr,y)
        with self.assertRaises(NotFittedError):m.predict(te)
        with self.assertRaises(NotFittedError):m.estado()

    def test_modificar_busqueda_registro_o_historico_es_rechazado(self):
        tr,y,_,_=contexto_externo(self.e,'A',1,0)
        cfg=copy.deepcopy(self.cfg);cfg['regularizacion']['lambda'].append(100)
        with self.assertRaises(ValueError):seleccionar(tr,y,'A',cfg,self.e['configuracion'])
        for name in [ARCH_DISENO,ARCH_REGISTRO,'registro/t09/predicciones_oof.csv']:
            with tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp)
                for p in [ARCH_DISENO,ARCH_REGISTRO,*self.reg['historicos_sha256']]:
                    dest=root/p;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes((RAIZ/p).read_bytes())
                target=root/name;target.write_bytes(target.read_bytes()+b'\n')
                with self.assertRaises(ValueError):contrato(root)

    def test_salida_nueva_y_datos_originales_protegidos(self):
        with self.assertRaises(ValueError):preparar_salida(RAIZ/'registro/t09/nueva',RAIZ)
        with self.assertRaises(ValueError):preparar_salida(RAIZ/'data/raw/nueva',RAIZ)
        with self.assertRaises(ValueError):preparar_salida(RAIZ/'reports/existe',RAIZ)
        self.assertEqual(preparar_salida(RAIZ/'reports/t09_centrado_20261013/ejecuciones/nueva',RAIZ),
                         RAIZ/'reports/t09_centrado_20261013/ejecuciones/nueva')

    def test_auditor_numpy_reconstruye_los_tres_escenarios(self):
        for esc in ['A','B','C']:
            tr,y,te,_=contexto_externo(self.e,esc,1,0)
            full=tr.assign(rendimiento_t_ha=y)
            for w in ['abr_oct','jun_oct']:
                p=prepare(full,te,w)
                beta,pred=matriz(p,.1)
                m=crear_estimador('R_centrado',w,.1).fit(tr,y)
                np.testing.assert_allclose(beta,m.coef_estandarizados_,atol=1e-10,rtol=0)
                np.testing.assert_allclose(pred,m.predict(te),atol=1e-9,rtol=0)

    def test_reportes_no_omiten_celda_vacia_ni_aceptan_texto_como_mascara(self):
        # Casos deliberadamente inválidos; no se calcula ningún reporte oficial.
        x=pd.DataFrame({'procedimiento':['T','R','TC','R_centrado'],
                        'celda_chirps':['c1','c1',None,'c1'],'sin_respaldo':[True]*4})
        with self.assertRaises(ValueError):reportes(x,self.cfg)
        x['celda_chirps']='c1';x['sin_respaldo']='True'
        with self.assertRaises(ValueError):reportes(x,self.cfg)


if __name__=='__main__':unittest.main()
