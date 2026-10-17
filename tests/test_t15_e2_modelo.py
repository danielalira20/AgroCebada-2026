"""Aislamiento y H3 E2; perturbaciones de control sobre copias, sin cambiar datos."""
import ast
import copy
import json
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
import pandas as pd
from scripts import t15_e2_entradas as e
from scripts import t15_e2_modelo as m
from scripts import t15_e2_registrar as registro
from scripts import t15_e1_modelo as anterior
from scripts.evaluacion_comun_modelo import divisiones_internas

ROOT=Path(__file__).resolve().parents[1]


class E2ModeloTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=e.cargar(ROOT);cls.options=e.opciones(cls.data)
        cls.X,cls.y,cls.q=e.contexto(cls.data,'A',1,0)
        cls.columns=cls.options[0]['columnas']

    def model(self,mode='E12',X=None,y=None):
        return m.ModeloE2(self.columns,.1,mode).fit(self.X if X is None else X,self.y if y is None else y)

    def test_source_197_no_quality_in_side(self):
        self.assertEqual(self.data['side'].shape,(197,5))
        self.assertEqual(set(self.data['side']),{*e.E2,anterior.VALUE,anterior.FLAG})
        self.assertEqual(len(self.data['fuentes_reutilizadas']),4140)
        self.assertTrue(np.isfinite(self.data['side'][list(e.E2)]).all().all())

    def test_join_by_id_not_position(self):
        d=dict(self.data,side=self.data['side'].iloc[::-1])
        X,y,q=e.contexto(d,'A',1,0)
        pd.testing.assert_frame_equal(self.X,X);pd.testing.assert_frame_equal(self.q,q)

    def test_reserved_features_cannot_change_training(self):
        side=self.data['side'].copy();reserved=side.index.difference(self.data['entradas']['conocidos'])
        self.assertEqual(len(reserved),59);side.loc[reserved,e.E2[0]]=1e6
        X,y,q=e.contexto(dict(self.data,side=side),'A',1,0)
        pd.testing.assert_frame_equal(X,self.X);pd.testing.assert_frame_equal(q,self.q)
        self.assertEqual(self.model(X=X,y=y).estado(),self.model().estado())

    def test_missing_side_row_blocks(self):
        d=dict(self.data,side=self.data['side'].drop(self.X.index[0]))
        with self.assertRaises(ValueError):e.contexto(d,'A',1,0)

    def test_side_duplicate_id_blocks(self):
        d=dict(self.data,side=pd.concat([self.data['side'],self.data['side'].iloc[:1]]))
        with self.assertRaises(ValueError):e.contexto(d,'A',1,0)

    def test_collision_with_T07_blocks(self):
        side=self.data['side'].copy();side['municipio']='otro'
        with self.assertRaises(ValueError):e.contexto(dict(self.data,side=side),'A',1,0)

    def test_canonical_files_and_manifest_are_pinned(self):
        real=e.sha
        for name in [e.ENTREGA,e.DISENO,'registro/t15_e2_extraccion/atributos_parcela.csv',
                     'registro/t15_e2_extraccion/calidad.csv']:
            with self.subTest(name=name),patch.object(e,'sha',side_effect=lambda p: '0'*64 if Path(p)==ROOT/name else real(p)):
                with self.assertRaises(ValueError):e.cargar(ROOT)

    def test_exact_dimensions_and_indicator(self):
        for mode,n in [('E2',8),('E12',10),('E2Q',9)]:
            s=self.model(mode).estado()
            self.assertEqual(len(s['columnas']),n);self.assertEqual(s['nombres_transformados'],s['columnas'])
            self.assertEqual(s['diagnostico_sin_promocion'],mode=='E2Q')
            self.assertEqual(s['alpha'],len(self.X)*.1)

    def test_quality_or_target_columns_rejected(self):
        for col in ['rendimiento_t_ha','cobertura_tpi_fraccion','area_ha_origen']:
            with self.assertRaises(ValueError):m.ModeloE2(self.columns[:-1]+[col],.1,'E2').fit(self.X,self.y)

    def test_nan_and_inf_E2_rejected(self):
        for col in e.E2:
            for value in [np.nan,np.inf]:
                X=self.X.copy();X.loc[X.index[0],col]=value
                with self.assertRaises(ValueError):self.model(X=X)

    def test_orientation_domain_rejected(self):
        X=self.X.copy();X.loc[X.index[0],list(e.E2[1:])]=[.9,.9]
        with self.assertRaises(ValueError):self.model(X=X)

    def test_observed_flat_zeros_are_retained(self):
        X=self.X.copy();X[list(e.E2)]=0.
        a=self.model('E2',X=X);s=a.estado();self.assertEqual(s['columnas'][-3:],list(e.E2))
        np.testing.assert_array_equal(s['escala'][-3:],[1.,1.,1.])

    def test_scale_and_median_only_training(self):
        a=self.model();s=a.estado();prep=a.modelo_.pipeline_['E1'].transform(self.X)
        np.testing.assert_allclose(s['media'],prep[s['columnas']].mean().to_numpy(),atol=1e-12,rtol=0)
        valid=self.X.loc[self.X[anterior.FLAG]==0,anterior.VALUE]
        self.assertEqual(s['preprocesamiento_E1']['mediana_E1'],float(valid.median()))
        q=self.q.copy();q[e.E2[0]]=1e6;q.loc[q[anterior.FLAG]==0,anterior.VALUE]=1.7
        a.predict(q);self.assertEqual(a.estado(),s)

    def test_Q_does_not_learn_NDWI_value(self):
        X=self.X.copy();q=self.q.copy()
        X.loc[X[anterior.FLAG]==0,anterior.VALUE]=1.8;q.loc[q[anterior.FLAG]==0,anterior.VALUE]=-1.8
        a=self.model('E2Q');b=self.model('E2Q',X=X)
        self.assertEqual(a.estado(),b.estado());np.testing.assert_array_equal(a.predict(self.q),b.predict(q))

    def test_all_missing_fit_does_not_reactivate(self):
        X=self.X.copy();X[anterior.VALUE]=np.nan;X[anterior.FLAG]=1
        q=self.q.copy();q[anterior.VALUE]=.2;q[anterior.FLAG]=0
        base=self.model('E2',X=X)
        for mode in ['E12','E2Q']:
            a=self.model(mode,X=X);self.assertFalse(a.estado()['preprocesamiento_E1']['extension_activa'])
            np.testing.assert_allclose(a.predict(q),base.predict(q),atol=1e-12,rtol=0)

    def test_H3_all_columns_and_same_LOO_pool(self):
        for mode in e.MODOS:
            a=self.model(mode);s=a.estado();core=a.modelo_.pipeline_['v3']
            prepared=a.modelo_.pipeline_['E1'].transform(self.X)
            z=core.escalador_.transform(prepared[s['columnas']].to_numpy(float))
            # Core sorts rows; use its saved order, never positional assumptions.
            order=list(core.ids_entrenamiento_);positions={pid:i for i,pid in enumerate(self.X.index)}
            for n,pid in enumerate(order):
                pool=s['pools_sin_fila'][pid]['ids'];self.assertNotIn(pid,pool)
                np.testing.assert_allclose(s['centros_Z_sin_fila'][pid],z[[positions[i] for i in pool]].mean(0),atol=1e-12,rtol=0)
                self.assertAlmostEqual(core.residuos_[n],self.y.loc[pid]-math.fsum(self.y.loc[pool])/len(pool),places=12)
            correction=a.predict_with_details(self.X).correccion
            np.testing.assert_allclose(correction.groupby(self.X.municipio).mean(),0,atol=1e-12,rtol=0)

    def test_singleton_group_and_global_POOLS(self):
        for fallback in ['grupo','global']:
            X=self.X.iloc[:8].copy();y=self.y.loc[X.index]
            X['cultivo_origen']='Cebada';pid=X.index[0];X.loc[pid,'municipio']='singleton_control'
            if fallback=='global':X.loc[pid,'cultivo_origen']='CEBADA'
            s=self.model('E12',X=X,y=y).estado()
            pool=s['pools_sin_fila'][pid];self.assertEqual(pool['fuente'],fallback);self.assertNotIn(pid,pool['ids'])

    def test_unknown_query_uses_training_global_center(self):
        X=self.X.loc[self.X.cultivo_origen=='Cebada'].copy();y=self.y.loc[X.index]
        a=self.model('E12',X=X,y=y);q=self.q.copy();q['municipio']='municipio_control_desconocido';q['cultivo_origen']='CEBADA'
        d=a.predict_with_details(q);self.assertTrue((d.fuente=='global').all());self.assertTrue((d.fuente_centrado=='global').all())

    def test_model_failed_refit_invalidates_previous_fit(self):
        a=self.model();bad=self.X.copy();bad.iloc[0,bad.columns.get_loc(e.E2[0])]=np.nan
        with self.assertRaises(ValueError):a.fit(bad,self.y)
        with self.assertRaises(ValueError):a.predict(self.q)

    def test_parameter_mutation_blocks(self):
        a=self.model();a.modo='E2'
        with self.assertRaises(ValueError):a.predict(self.q)

    def test_overlapping_ids_rejected(self):
        o=self.options[0]
        with self.assertRaises(ValueError):m.ajustar(self.X,self.y,self.X.iloc[:2],o,'E12',(True,True))

    def test_full_inner_menu_same_choice_as_existing_method(self):
        traces=[]
        a=m.seleccionar(self.X,self.y,self.options,'E2','A',traces.append)
        b=anterior.v3.seleccionar(self.X,self.y,self.options,'A')
        self.assertEqual(a['elegida'],b['elegida']);self.assertEqual(a['puntuaciones'],b['puntuaciones'])
        self.assertEqual(a['n_ajustes'],36);self.assertEqual(len(traces),36)
        self.assertEqual(sum(t['referencia_sola'] for t in traces),4)
        outer=set(self.q.index)
        for t in traces:self.assertFalse(outer&set(t['ids_entrenamiento']+t['ids_validacion']))

    def test_menu_malformed_blocks(self):
        for change in ['lambda','duplicate','window','column']:
            options=copy.deepcopy(self.options)
            if change=='lambda':options[0]['lambda_reg']=True
            elif change=='duplicate':options[-1]=copy.deepcopy(options[0])
            elif change=='window':options[0]['ventana']='jul_oct'
            else:options[0]['columnas'].append('calidad')
            with self.assertRaises(ValueError):m.validar_menu(options)

    def test_inner_spatial_group_splits(self):
        X,y,q=e.contexto(self.data,'B',1,0)
        for split in divisiones_internas(X,'B'):
            self.assertFalse(set(X.loc[list(split.entrenamiento),'celda_chirps']) &
                             set(X.loc[list(split.validacion),'celda_chirps']))

    def test_auditor_imports_no_producer_or_sklearn(self):
        for name in ['scripts/t15_e2_auditar_modelo.py','scripts/t15_e1_auditar.py']:
            tree=ast.parse((ROOT/name).read_text())
            imports=[n.module or '' for n in ast.walk(tree) if isinstance(n,ast.ImportFrom)]
            imports += [a.name for n in ast.walk(tree) if isinstance(n,ast.Import) for a in n.names]
            self.assertFalse(any('sklearn' in x or x.endswith('t15_e2_modelo') or x.endswith('t15_e1_modelo') for x in imports))

    def test_existing_registration_not_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'r.json';out.write_text('{}')
            with self.assertRaises(ValueError):registro.registrar(ROOT,Path(tmp),Path(tmp),out)

    def test_registration_dangerous_changes_rejected(self):
        c=self.data['diseno']
        r=dict(schema='agrocebada_E2_ejecucion_v1',evaluacion_completa_autorizada=False,
            predicciones_finales59_autorizadas=False,metodo=self.data['antecedente']['metodo'],
            procedimientos=[dict(modo=n,dimension=d,promocion=p) for n,d,p in [('E2',8,True),('E12',10,True),('E2Q',9,False)]],
            opciones_base=self.options,presupuesto=c['presupuesto'],decision=c['decision'],
            poblacion=dict(total=197,etiquetadas=138,reservadas=59,excluir_por_error=False,corte='2025-10-31'),
            referencia_sola_compite=True,tolerancia_OOF_mismo_CSV=1e-12,contrastes=c['contrastes'],
            aprendizaje_solo_train=True,H3_centrar_todas_columnas=True)
        self.assertTrue(registro.validar(r))
        for case in ['authorize','control','budget','tolerance','H3','family']:
            bad=copy.deepcopy(r)
            if case=='authorize':bad['evaluacion_completa_autorizada']=True
            elif case=='control':bad['procedimientos'][-1]['promocion']=True
            elif case=='budget':bad['presupuesto']['trazas_sin_cache']=100
            elif case=='tolerance':bad['tolerancia_OOF_mismo_CSV']=1e-6
            elif case=='H3':bad['H3_centrar_todas_columnas']=False
            else:bad['decision']['guardia_familia_E2']['percentiles']=[2.5,97.5]
            with self.subTest(case=case),self.assertRaises(ValueError):registro.validar(bad)


if __name__=='__main__':unittest.main()
