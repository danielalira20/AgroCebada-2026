import copy
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np

from scripts import diagnostico_aplicabilidad59 as c


def fixture():
    return {
        'a': {'municipio':'M', 'cultivo_origen':'C', 'v':'0', 'area_ha_origen':'1', c.PEND:'1'},
        'b': {'municipio':'M', 'cultivo_origen':'C', 'v':'2', 'area_ha_origen':'4', c.PEND:''},
        'd': {'municipio':'N', 'cultivo_origen':'C', 'v':'4', 'area_ha_origen':'9', c.PEND:'3'},
        'q': {'municipio':'M', 'cultivo_origen':'C', 'v':'1', 'area_ha_origen':'2', c.PEND:'2'},
        'z': {'municipio':'U', 'cultivo_origen':'Z', 'v':'8', 'area_ha_origen':'3', c.PEND:'5'},
    }


class SupportTests(unittest.TestCase):
    def test_training_statistics_hand_calculation(self):
        state=c.fit_space(fixture(), ['a','b'], ['v'])
        self.assertEqual(state['mean'].tolist(), [1.])
        self.assertEqual(state['sd'].tolist(), [1.])
        result=c.inspect_space(fixture(), 'q', state)
        self.assertEqual(result['distancia_municipio'], 1.)
        self.assertEqual(result['q95_local'], 2.)
        self.assertFalse(result['supera_q95_local'])

    def test_self_id_excluded(self):
        table=fixture();state=c.fit_space(table,['a','b'],['v'])
        with self.assertRaisesRegex(ValueError,'entrenamiento'): c.inspect_space(table,'a',state)

    def test_duplicate_train_rejected(self):
        with self.assertRaises(ValueError): c.fit_space(fixture(),['a','a'],['v'])

    def test_zero_distance_ties_not_false_p95(self):
        t=fixture()
        for row in t.values():row['v']='0'
        state=c.fit_space(t,['a','b'],['v']);r=c.inspect_space(t,'q',state)
        self.assertEqual(r['distancia_municipio'],0.)
        self.assertEqual(r['percentil_local_estricto'],0.)
        self.assertFalse(r['supera_q95_local'])

    def test_singleton_has_no_percentile(self):
        state=c.fit_space(fixture(),['a'],['v']);r=c.inspect_space(fixture(),'q',state)
        self.assertEqual(r['n_municipio'],1)
        self.assertIsNone(r['percentil_local_estricto'])
        self.assertIsNone(r['supera_q95_local'])
        self.assertEqual(r['motivo_percentil_ausente'],'sin_dos_etiquetas_locales')

    def test_new_municipality_has_no_local_distance(self):
        state=c.fit_space(fixture(),['a','b'],['v']);r=c.inspect_space(fixture(),'z',state)
        self.assertEqual(r['n_municipio'],0)
        self.assertIsNone(r['distancia_municipio'])
        self.assertEqual(r['vecino_atributos_municipio'],'')

    def test_y_unused_and_support_does_not_change(self):
        t=fixture();a=c.fit_space(t,['a','b','d'],['v'])
        for row in t.values():row['rendimiento_t_ha']='999999'
        b=c.fit_space(t,['a','b','d'],['v'])
        np.testing.assert_array_equal(a['z'],b['z'])
        self.assertEqual(c.inspect_space(t,'q',a),c.inspect_space(t,'q',b))

    def test_validation_X_cannot_change_state(self):
        t=fixture();state=c.fit_space(t,['a','b','d'],['v']);before=copy.deepcopy(state)
        t['q']['v']='1000000';c.inspect_space(t,'q',state)
        for k in ['raw','mean','sd','z']: np.testing.assert_array_equal(state[k],before[k])
        self.assertEqual(state['ids'],before['ids'])

    def test_order_invariant_and_no_input_mutation(self):
        t=fixture();old=copy.deepcopy(t)
        a=c.fit_space(t,['a','b','d'],['v']);b=c.fit_space(t,['d','b','a'],['v'])
        np.testing.assert_array_equal(a['z'],b['z']);self.assertEqual(t,old)

    def test_unallowed_missing_rejected(self):
        t=fixture();t['a']['v']=''
        with self.assertRaisesRegex(ValueError,'Faltante'): c.fit_space(t,['a','b'],['v'])

    def test_non_finite_rejected(self):
        t=fixture();t['a']['v']='nan'
        with self.assertRaises(ValueError): c.fit_space(t,['a','b'],['v'])

    def test_area_zero_rejected(self):
        t=fixture();t['a']['area_ha_origen']='0'
        with self.assertRaises(ValueError):c.fit_space(t,['a','b'],['area_ha_origen'])

    def test_area_log_and_missing_indicator(self):
        t=fixture();state=c.fit_space(t,['a','b','d'],['area_ha_origen',c.PEND])
        self.assertEqual(state['median'],2.)
        self.assertEqual(state['raw'].shape,(3,2))
        self.assertEqual(state['z'].shape,(3,3))
        self.assertAlmostEqual(state['mean'][0],np.log([1,4,9]).mean())
        self.assertEqual(t['b'][c.PEND],'')

    def test_missing_slope_does_not_become_marginal_measurement(self):
        t=fixture();state=c.fit_space(t,['a','d'],[c.PEND]);r=c.inspect_space(t,'b',state)
        self.assertEqual(r['entradas_ausentes'],c.PEND)
        self.assertEqual(r['fuera_rango_global'],'')

    def test_no_finite_training_slope_rejected(self):
        t=fixture();t['a'][c.PEND]=''
        with self.assertRaises(ValueError):c.fit_space(t,['a','b'],[c.PEND])

    def test_municipal_range_not_substituted_by_global(self):
        t=fixture();state=c.fit_space(t,['a','b','d'],['v']);t['q']['v']='3'
        r=c.inspect_space(t,'q',state)
        self.assertEqual(r['fuera_rango_global'],'')
        self.assertEqual(r['fuera_rango_municipio'],'v')

    def test_climate_rounding_tolerance_not_out_of_range(self):
        t=fixture();col='prec_acumulada_mm_abr_oct'
        for row in t.values():row[col]='100'
        t['q'][col]='100.0000000001'
        r=c.inspect_space(t,'q',c.fit_space(t,['a','b'],[col]))
        self.assertEqual(r['fuera_rango_global'],'')
        t['q'][col]='100.01'
        r=c.inspect_space(t,'q',c.fit_space(t,['a','b'],[col]))
        self.assertEqual(r['fuera_rango_global'],col)

    def test_geographical_neighbors_only_from_training(self):
        t=fixture();ids=tuple(t);pos={v:k for k,v in enumerate(ids)}
        a=np.array([[0 if i==j else abs(i-j)*20 for j in range(5)] for i in range(5)],float)
        geo={'ids':ids,'positions':pos,'edges':a,'centers':a}
        cell={v:'c' for v in ids}
        r=c.geo_support(t,'q',['a','b','d'],geo,cell)
        self.assertEqual(r['n_vecinas20_general'],0)  # Exactly20 excluded.
        self.assertIn(r['conocida_mas_cercana_orilla'],['a','b','d'])
        with self.assertRaises(ValueError):c.geo_support(t,'q',['q','a'],geo,cell)

    def test_group_and_global_backups(self):
        t=fixture();ids=tuple(t);pos={v:k for k,v in enumerate(ids)}
        a=np.ones((5,5));np.fill_diagonal(a,0)
        geo={'ids':ids,'positions':pos,'edges':a,'centers':a};cell={v:'c' for v in ids}
        self.assertEqual(c.geo_support(t,'a',['d'],geo,cell)['fuente_referencia'],'grupo')
        self.assertEqual(c.geo_support(t,'z',['a'],geo,cell)['fuente_referencia'],'global')

    def test_output_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError,'Destino existente'):c.run('/invalid',tmp)

    def test_csv_absence_distinguished_from_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'sample.csv';c.csv_out(p,[dict(n=0,p=None,flag=False)])
            r=c.rows(p)[0]
            self.assertEqual(r,dict(n='0',p='',flag='no'))

    def test_duplicate_keys_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'sample.csv';c.csv_out(p,[dict(id_parcela='a',n=0),dict(id_parcela='a',n=1)])
            with self.assertRaises(ValueError):c.indexed(p)

    def test_descriptive_error_counts_repeat_not_new_labels(self):
        rs=[dict(escenario='A',id_parcela='a',fuente_referencia='municipio',error_historico=x,k=True)
            for x in [1.,-1.]]
        out=c.breakdown(rs,['k'])
        self.assertEqual(out[0]['n_registros_oof'],2)
        self.assertEqual(out[0]['n_parcelas'],1)
        self.assertEqual(out[0]['MAE_historico'],1.)


if __name__=='__main__':unittest.main()
