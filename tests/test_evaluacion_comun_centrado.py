"""Regresiones H3: datos reales y casos aislados; ninguna entrega T15 simulada."""
import copy
import io
import json
import unittest
from unittest.mock import patch

import joblib
import numpy as np
import pandas as pd
from sklearn.base import clone

from scripts import evaluacion_comun_centrado as v2
from scripts import evaluacion_comun_modelo as v1


class CentradoH3(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.e=v2.cargar_entradas()
        cls.x,cls.y,cls.te=v1.preparar_contexto(cls.e,'A',1,0)
        cls.cols=['elevacion_media_m',v1.NULLABLE,'area_ha_origen']
        cls.propuesta=json.loads((v2.RAIZ/'registro/evaluacion_comun/propuesta_t15_centrado_v2.json').read_text())

    def fit_real(self,cols=None):
        return v2.CorreccionComunCentrada(self.cols if cols is None else cols,.1).fit(self.x,self.y)

    def test_entradas_reales_no_entrenan(self):
        self.assertEqual((len(self.e['conocidos']),len(self.e['reservados']),len(self.e['contextos'])),(138,59,1380))
        self.assertEqual(self.e['config']['version'],v2.VERSION)

    def test_historico_requires_opt_in(self):
        with self.assertRaisesRegex(ValueError,'histórico'):
            v1.seleccionar_registrado(self.e,self.propuesta,'nada','A',1,0)

    def test_propuesta_pendiente_rechazada(self):
        with self.assertRaisesRegex(ValueError,'pendiente'):
            v2.validar_experimento(self.propuesta,self.e)

    def test_identidad_v1_no_acredita_v2(self):
        e=copy.deepcopy(self.propuesta);e['estado']='registrado_antes_de_ejecutar'
        for key,val in [('schema','experimento_comun_v1'),('sha_procedimiento','da633adf27c7f1cf2d7760dc2f190abe38d9a912f80a976717fc6213c48f76d3')]:
            p=copy.deepcopy(e);p[key]=val
            with self.subTest(key=key),self.assertRaises(ValueError):v2.validar_experimento(p,self.e)

    def test_estructura_ocho_sesenta_sin_registrar_entrega(self):
        # Sólo copia en memoria para comprobar el contrato; no ejecutar ni escribir registro.
        exp=copy.deepcopy(self.propuesta);exp['estado']='registrado_antes_de_ejecutar'
        self.assertEqual(v2.validar_experimento(exp,self.e)['opciones_con_variables'],60)
        self.assertNotEqual(self.propuesta['estado'],'registrado_antes_de_ejecutar')

    def test_no_disminuir_busqueda_o_roles(self):
        for mode in ['una_lambda','objetivo','bool','ventana']:
            e=copy.deepcopy(self.propuesta);e['estado']='registrado_antes_de_ejecutar';p=e['procedimientos'][0]
            if mode=='una_lambda':p['opciones']=p['opciones'][:1]
            if mode=='objetivo':p['opciones'][0]['columnas']=['rendimiento_t_ha']
            if mode=='bool':p['opciones'][0]['lambda_reg']=True
            if mode=='ventana':p['opciones'][0]['ventana']='estatica'
            with self.subTest(mode=mode),self.assertRaises(ValueError):v2.validar_experimento(e,self.e)

    def test_matriz_independiente_log_imputacion_indicador(self):
        x,y=self.x,self.y
        a=x[self.cols].to_numpy(float).copy();a[:,2]=np.log(a[:,2]);miss=np.isnan(a[:,1]);med=np.median(a[~miss,1]);a[miss,1]=med
        a=np.column_stack([a,miss.astype(float)]);mu=a.mean(0);sd=a.std(0);sd[sd==0]=1
        z=(a-mu)/sd;mun=x.municipio.to_numpy();centers={m:z[mun==m].mean(0) for m in set(mun)}
        d=z-np.stack([centers[m] for m in mun])
        residual=[]
        for pid,row in x.iterrows():
            rest=x.drop(index=pid);labels=y.loc[rest.index]
            sel=rest.municipio==row.municipio
            if not sel.any():sel=rest.cultivo_origen==row.cultivo_origen
            if not sel.any():sel=pd.Series(True,index=rest.index)
            residual.append(y.loc[pid]-labels.loc[sel].mean())
        beta=np.linalg.lstsq(np.vstack([d,np.sqrt(len(x)*.1)*np.eye(d.shape[1])]),np.r_[residual,np.zeros(d.shape[1])],rcond=None)[0]
        model=self.fit_real()
        np.testing.assert_allclose(model.ridge_.coef_,beta,atol=1e-12,rtol=0)
        np.testing.assert_allclose(model.escalador_.scale_,sd,atol=1e-12,rtol=1e-12)
        self.assertEqual(model.alpha_,len(x)*.1)
        self.assertIn(v1.NULLABLE+'__faltante',model.nombres_)

    def test_correccion_cero_en_media_municipal_train(self):
        model=self.fit_real();p=model.predict_with_details(self.x)
        self.assertLess(p.correccion.groupby(self.x.municipio).mean().abs().max(),1e-12)

    def test_indicador_centrado_y_escala_global_conservada(self):
        model=self.fit_real();a=model._valores(self.x);z=model.escalador_.transform(a)
        d=z-model.centros_mun_.loc[self.x.municipio].to_numpy()
        f=pd.DataFrame(d,index=self.x.index).groupby(self.x.municipio).mean()
        self.assertLess(np.abs(f.to_numpy()).max(),1e-12)
        np.testing.assert_allclose(model.escalador_.mean_,a.mean(0),atol=1e-12,rtol=1e-12)
        self.assertFalse(model.estado()['reescalar_intramunicipal'])

    def test_validacion_no_se_fuerza_media_cero(self):
        model=self.fit_real(['elevacion_media_m']);q=self.te.copy();q['elevacion_media_m']+=1000
        p=model.predict_with_details(q)
        self.assertGreater(p.correccion.abs().max(),1e-8)
        self.assertGreater(p.correccion.groupby(q.municipio).mean().abs().max(),1e-8)

    def test_invariante_a_lote_y_orden_validacion(self):
        model=self.fit_real();state=json.dumps(model.estado(),sort_keys=True);p=model.predict(self.te)
        singles=np.array([model.predict(self.te.loc[[pid]])[0] for pid in self.te.index])
        np.testing.assert_allclose(p,singles,atol=1e-12,rtol=0)
        np.testing.assert_allclose(p,model.predict_with_details(self.te.iloc[::-1]).loc[self.te.index,'prediccion'],atol=1e-12,rtol=0)
        self.assertEqual(json.dumps(model.estado(),sort_keys=True),state)

    def test_respaldo_grupo_global_solo_train(self):
        x=self.x.loc[self.x.cultivo_origen=='Cebada'];y=self.y.loc[x.index]
        model=v2.CorreccionComunCentrada(['area_ha_origen'],1).fit(x,y)
        q=x.iloc[:2].copy();q['municipio']='municipio_ausente';q.loc[q.index[1],'cultivo_origen']='CEBADA'
        p=model.predict_with_details(q)
        self.assertEqual(p.fuente.tolist(),['grupo','global'])
        self.assertEqual(p.fuente.tolist(),p.fuente_centrado.tolist())
        cs,s=model._centros(q)
        np.testing.assert_allclose(cs[0],model.centros_grupo_.loc['Cebada'])
        np.testing.assert_allclose(cs[1],model.centro_global_)

    def test_singleton_no_elimina_fila(self):
        x=self.x.copy();x.loc[x.index[0],'municipio']='unica';model=v2.CorreccionComunCentrada(['elevacion_media_m'],.1).fit(x,self.y)
        self.assertEqual(model.n_,len(x));self.assertEqual(model.alpha_,.1*len(x))
        self.assertEqual(model.predict_with_details(x).correccion.iloc[0],0)

    def test_variables_constantes_en_municipio_no_crean_ajuste(self):
        x=self.x.copy();x['elevacion_media_m']=x.groupby('municipio')['elevacion_media_m'].transform('mean')
        model=v2.CorreccionComunCentrada(['elevacion_media_m'],.1).fit(x,self.y)
        np.testing.assert_allclose(model.predict_with_details(x).correccion,0,atol=1e-12,rtol=0)

    def test_unidades_equivalentes_misma_prediccion(self):
        x=self.x.copy();q=self.te.copy();x['elevacion_media_m']/=1000;q['elevacion_media_m']/=1000
        m1=self.fit_real(['elevacion_media_m']);m2=v2.CorreccionComunCentrada(['elevacion_media_m'],.1).fit(x,self.y)
        np.testing.assert_allclose(m1.predict(self.te),m2.predict(q),atol=1e-12,rtol=0)

    def test_clone_y_joblib_conservan_centros(self):
        m=self.fit_real();n=clone(m).fit(self.x,self.y);buff=io.BytesIO();joblib.dump(m,buff);buff.seek(0);reloaded=joblib.load(buff)
        np.testing.assert_array_equal(m.predict(self.te),reloaded.predict(self.te))
        np.testing.assert_array_equal(m.predict(self.te),n.predict(self.te))

    def test_estado_no_modifica_modelo(self):
        m=self.fit_real();before=m.predict(self.te);e=m.estado();e['municipio'].clear();e['centros_Z_municipio'].clear();e['nombres_transformados'].clear()
        np.testing.assert_array_equal(before,m.predict(self.te))

    def test_parametros_cambiados_exigen_fit(self):
        m=self.fit_real();m.set_params(lambda_reg=10)
        with self.assertRaisesRegex(ValueError,'Reajustar'):m.predict(self.te)
        m.fit(self.x,self.y);self.assertEqual(m.alpha_,len(self.x)*10)

    def test_fit_fallido_invalida_estado_anterior(self):
        m=self.fit_real();x=self.x.copy();x[v1.NULLABLE]=np.nan
        with self.assertRaisesRegex(ValueError,'totalmente ausente'):m.fit(x,self.y)
        self.assertFalse(hasattr(m,'mediana_pendiente_'))
        with self.assertRaisesRegex(ValueError,'sin ajustar'):m.predict(self.te)

    def test_objetivo_duplicado_desalineado_bool_rechazado(self):
        for mode in ['bool','reversed','columna_y','dup']:
            x=self.x.copy();y=self.y.copy();cols=self.cols
            if mode=='bool':y=y>0
            if mode=='reversed':y=y.iloc[::-1]
            if mode=='columna_y':x['real']=y;cols=['real']
            if mode=='dup':x.index=[x.index[0]]*len(x);y.index=x.index
            with self.subTest(mode=mode),self.assertRaises(ValueError):v2.CorreccionComunCentrada(cols,1).fit(x,y)

    def test_referencia_sola_no_ridge(self):
        m=v2.CorreccionComunCentrada().fit(self.x,self.y)
        np.testing.assert_array_equal(m.predict(self.te),v1.CorreccionComun().fit(self.x,self.y).predict(self.te))
        self.assertIsNone(m.ridge_);self.assertEqual(m.estado()['version'],v2.VERSION)

    def test_seleccion_interna_usa_centros_solo_en_fit(self):
        options=[dict(nombre=f'l{l}',columnas=['prec_acumulada_mm_jun_oct'],ventana='jun_oct',lambda_reg=l) for l in v1.LAMBDA]
        original=v2.CorreccionComunCentrada.fit;seen=[]
        def monitor(m,x,y):
            result=original(m,x,y);seen.append(set(m.ids_entrenamiento_))
            if m.ridge_ is not None:self.assertLess(m.predict_with_details(x).correccion.groupby(x.municipio).mean().abs().max(),1e-12)
            return result
        with patch.object(v2.CorreccionComunCentrada,'fit',monitor):s=v2.seleccionar(self.x,self.y,options,'A')
        self.assertEqual(len(seen),20);self.assertEqual(s['n_ajustes'],20)
        self.assertTrue(all(ids<set(self.x.index) for ids in seen))
        self.assertTrue(all(not ids&set(self.te.index) and not ids&self.e['reservados'] for ids in seen))

    def test_seleccion_registrada_no_usa_etiquetas_externas(self):
        exp=copy.deepcopy(self.propuesta);exp['id']='SOLO_TEST_EN_MEMORIA';exp['estado']='registrado_antes_de_ejecutar';exp['procedimientos']=exp['procedimientos'][:1]
        candidate=exp['procedimientos'][0]['candidato'];before=v2.seleccionar_registrado(self.e,exp,candidate,'A',1,0)
        other=copy.deepcopy(self.e)
        for pid in self.te.index:other['tabla'][(pid,)]['rendimiento_t_ha']='9999'
        after=v2.seleccionar_registrado(other,exp,candidate,'A',1,0)
        self.assertEqual(before['seleccion'],after['seleccion'])
        np.testing.assert_array_equal(before['prediccion'],after['prediccion'])
        self.assertFalse(set(before['ids_entrenamiento'])&set(before['ids_evaluacion']))
        self.assertFalse(set(before['ids_entrenamiento'])&self.e['reservados'])

    def test_todos_contextos_reales_y_internas_separados(self):
        for esc in ['A','B']:
            for rep in range(1,6):
                for fold in range(5):
                    x,y,q=v1.preparar_contexto(self.e,esc,rep,fold)
                    self.assertNotIn('rendimiento_t_ha',q)
                    for split in v1.divisiones_internas(x,esc):
                        self.assertFalse(set(split.entrenamiento)&set(q.index))
                        self.assertFalse(set(split.entrenamiento)&set(split.validacion))
                        if esc=='B':self.assertFalse(set(x.loc[list(split.entrenamiento),'celda_chirps'])&set(x.loc[list(split.validacion),'celda_chirps']))


if __name__=='__main__':unittest.main()
