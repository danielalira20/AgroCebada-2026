"""Pruebas de aislamiento, degeneraciones, H3 y puente con el método publicado."""
import copy
import json
from pathlib import Path
import unittest

import numpy as np
import pandas as pd
from sklearn.base import clone

from scripts import evaluacion_comun_centrado_loo as v3
from scripts.evaluacion_comun_modelo import preparar_contexto, residuos_loo
from scripts.t15_e1_modelo import ModeloE1, PreparadorE1, VALUE, FLAG, ajustar
from scripts.t15_e1_estabilidad import perturbar
from scripts import t15_ndwi_factibilidad as d1

ROOT = Path(__file__).resolve().parents[1]


def fixture():
    ids=[f'p{i}' for i in range(8)]
    X=pd.DataFrame(dict(municipio=['a']*3+['b']*2+['c','d','e'],
        cultivo_origen=['Cebada']*6+['CEBADA']*2,
        celda_chirps=[str(i) for i in range(8)], x=[1.,2,5,40,45,10,20,23],
        e1_ndwi_post15_45=[-.1,np.nan,-.2,.1,np.nan,0.,.2,.3],
        e1_no_utilizable=[0,1,0,0,1,0,0,0]),index=ids)
    return X,pd.Series([2.,2.3,2.8,4.,3.7,3.1,2.6,2.9],index=ids)


class E1Tests(unittest.TestCase):
    def test_median_only_training(self):
        X,y=fixture();p=PreparadorE1(('x',),'E1').fit(X.iloc[:5])
        self.assertEqual(p.mediana_,-.1)
        q=X.iloc[5:].copy();q[VALUE]=1.9
        before=p.estado();p.transform(q)
        self.assertEqual(before,p.estado())

    def test_q_never_learns_value(self):
        X,y=fixture();a=ModeloE1(['x'],.1,'Q').fit(X,y)
        q=X.copy();q.loc[q[FLAG]==0,VALUE]=1.7
        b=ModeloE1(['x'],.1,'Q').fit(q,y)
        self.assertEqual(a.estado(),b.estado())
        np.testing.assert_array_equal(a.predict(X),b.predict(q))

    def test_fixed_indicator_when_training_complete(self):
        X,y=fixture();X[VALUE]=.2;X[FLAG]=0
        m=ModeloE1(['x'],.1,'E1').fit(X,y)
        q=X.iloc[:2].copy();q.iloc[0,q.columns.get_loc(VALUE)]=np.nan;q.iloc[0,q.columns.get_loc(FLAG)]=1
        self.assertEqual(m.estado()['nombres_transformados'],['x',VALUE,FLAG])
        self.assertTrue(np.isfinite(m.predict(q)).all())

    def test_all_missing_fit_never_reactivates(self):
        X,y=fixture();X[VALUE]=np.nan;X[FLAG]=1
        for mode in ['Q','E1']:
            m=ModeloE1(['x'],.1,mode).fit(X,y)
            baseline=v3.CorreccionComunCentradaLOO(['x'],.1).fit(X,y)
            q=X.copy();q[VALUE]=np.linspace(-1,1,len(q));q[FLAG]=0
            self.assertFalse(m.estado()['preprocesamiento_E1']['extension_activa'])
            self.assertIsNone(m.estado()['preprocesamiento_E1']['mediana_E1'])
            np.testing.assert_allclose(m.predict(q),baseline.predict(q),rtol=0,atol=1e-12)

    def test_zero_observed_is_not_absence(self):
        X,y=fixture();X[VALUE]=0.;X[FLAG]=0
        p=PreparadorE1(['x'],'E1').fit(X)
        self.assertEqual(len(p.ids_admisibles_),8);self.assertEqual(p.mediana_,0.)

    def test_contradictory_flag_rejected(self):
        X,y=fixture();X.loc['p0',FLAG]=1
        with self.assertRaises(ValueError):ModeloE1(['x'],.1,'E1').fit(X,y)

    def test_infinity_rejected(self):
        X,y=fixture();X.loc['p0',VALUE]=float('inf')
        with self.assertRaises(ValueError):ModeloE1(['x'],.1,'E1').fit(X,y)

    def test_nonbinary_flag_rejected(self):
        X,y=fixture();X.loc['p0',FLAG]=2
        with self.assertRaises(ValueError):ModeloE1(['x'],.1,'Q').fit(X,y)

    def test_no_external_label_access(self):
        X,y=fixture();m=ModeloE1(['x'],.1,'E1').fit(X,y)
        q=X.copy();q['rendimiento_t_ha']=999999.
        np.testing.assert_array_equal(m.predict(X),m.predict(q))

    def test_batch_order_invariance(self):
        X,y=fixture();m=ModeloE1(['x'],.1,'E1').fit(X,y);state=m.estado()
        a=m.predict(X);b=m.predict(X.iloc[::-1])[::-1]
        np.testing.assert_allclose(a,b,rtol=0,atol=1e-12)
        np.testing.assert_allclose([m.predict(X.loc[[i]])[0] for i in X.index],a,rtol=0,atol=1e-12)
        self.assertEqual(m.estado(),state)

    def test_training_order_invariance(self):
        X,y=fixture();a=ModeloE1(['x'],.1,'E1').fit(X,y)
        b=ModeloE1(['x'],.1,'E1').fit(X.iloc[::-1],y.iloc[::-1])
        self.assertEqual(a.estado(),b.estado())

    def test_unknown_municipality_and_group_fallback(self):
        X,y=fixture();m=ModeloE1(['x'],.1,'E1').fit(X.iloc[:6],y.iloc[:6]);q=X.iloc[6:].copy()
        q.municipio='new';d=m.predict_with_details(q)
        self.assertEqual(set(d.fuente),{'global'});self.assertEqual(set(d.fuente_centrado),{'global'})
        q.cultivo_origen='Cebada';d=m.predict_with_details(q)
        self.assertEqual(set(d.fuente),{'grupo'});self.assertTrue(np.isfinite(d.prediccion).all())

    def test_same_pool_centers_and_residual(self):
        X,y=fixture();m=ModeloE1(['x'],.1,'E1').fit(X,y);s=m.estado()
        prep=m.pipeline_['E1'].transform(X)
        core=m.pipeline_['v3']
        # Array with names removed to avoid sklearn feature-name warnings.
        z=core.escalador_.transform(prep[s['columnas']].to_numpy(float))
        for i,pid in enumerate(X.index):
            pool=s['pools_sin_fila'][pid]['ids'];self.assertNotIn(pid,pool)
            np.testing.assert_allclose(s['centros_Z_sin_fila'][pid],z[[X.index.get_loc(j) for j in pool]].mean(0),atol=1e-12,rtol=0)
            self.assertAlmostEqual(core.residuos_[i],y.loc[pid]-y.loc[pool].mean(),places=12)

    def test_h3_no_correction_at_saved_center(self):
        X,y=fixture();X[VALUE]=np.linspace(-.4,.3,8);X[FLAG]=0
        m=ModeloE1(['x'],.1,'E1').fit(X,y)
        q=X.copy()
        for mun in X.municipio.unique():
            ids=X.index[X.municipio==mun]
            q.loc[ids,'x']=X.loc[ids,'x'].mean();q.loc[ids,VALUE]=X.loc[ids,VALUE].mean()
        np.testing.assert_allclose(m.predict_with_details(q).correccion,0,atol=1e-12,rtol=0)

    def test_alpha_counts_all_training(self):
        X,y=fixture();m=ModeloE1(['x'],.1,'E1').fit(X,y)
        self.assertEqual(m.estado()['alpha'],.8)

    def test_trace_is_portable_json(self):
        X,y=fixture();tr=X.iloc[:5];q=X.iloc[5:]
        o=dict(nombre='abr_oct__lambda_0.1',columnas=['x'],lambda_reg=.1,ventana='abr_oct')
        _,_,t=ajustar(tr,y.loc[tr.index],q,o,'E1',tuple(False for _ in q.index))
        self.assertTrue(json.dumps(t,allow_nan=False))

    def test_clone_preparator(self):
        p=PreparadorE1(['x'],'E1');self.assertEqual(clone(p).get_params(),p.get_params())

    def test_no_fit_and_failed_refit(self):
        X,y=fixture();m=ModeloE1(['x'],.1,'E1')
        with self.assertRaises(ValueError):m.predict(X)
        m.fit(X,y);bad=X.copy();bad.loc['p0',VALUE]=5.
        with self.assertRaises(ValueError):m.fit(bad,y)
        with self.assertRaises(ValueError):m.predict(X)

    def test_parameter_mutation_rejected(self):
        X,y=fixture();m=ModeloE1(['x'],.1,'E1').fit(X,y);m.lambda_reg=1.
        with self.assertRaises(ValueError):m.predict(X)

    def test_duplicate_ids_rejected(self):
        X,y=fixture();X.index=['same']*8;y.index=X.index
        with self.assertRaises(ValueError):ModeloE1(['x'],.1,'E1').fit(X,y)

    def test_target_cannot_be_predictor(self):
        X,y=fixture();X['real']=y
        with self.assertRaises(ValueError):ModeloE1(['real'],.1,'E1').fit(X,y)

    def test_bridge_actual_S_all_parameters(self):
        e=v3.cargar_entradas(ROOT)
        c=json.loads((ROOT/'registro/t15_contrato/contrato_v1.json').read_text())
        opts=next(p['opciones'] for p in c['principal']['procedimientos'] if p['bloques']==['S'])
        for esc in ['A','B']:
            X,y,q=preparar_contexto(e,esc,1,0)
            for o in opts:
                a=ModeloE1(o['columnas'],o['lambda_reg'],'S').fit(X,y)
                b=v3.CorreccionComunCentradaLOO(o['columnas'],o['lambda_reg']).fit(X,y)
                np.testing.assert_array_equal(a.predict(q),b.predict(q))
                s=a.estado();s.pop('extension');s.pop('preprocesamiento_E1')
                self.assertEqual(s,b.estado())

    def test_stability_uses_only_pre_cut_observations(self):
        from datetime import date,timedelta
        start=date(2025,6,1)
        obs=[d1.Obs('p',start+timedelta(days=i*10),.1+i*.02,.3-i*.01,0.) for i in range(12)]
        a=perturbar(obs,start)
        obs.append(d1.Obs('p',date(2025,12,1),.99,-.99,0.))
        self.assertEqual(a,perturbar(obs,start))


if __name__=='__main__':unittest.main()
