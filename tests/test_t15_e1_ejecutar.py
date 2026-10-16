"""Contrato, unión y separación de y antes de correr la extensión completa."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

from scripts import t15_e1_ejecutar as run
from scripts import t15_e1_modelo as model
from scripts.t15_e1_auditar import Auditor
from tests.test_t15_e1_modelo import fixture

ROOT=Path(__file__).resolve().parents[1]


class EjecutorE1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.cfg,cls.e,cls.side,cls.baseline=run.cargar(ROOT)

    def test_population_and_observed_counts(self):
        self.assertEqual(len(self.side),197)
        self.assertEqual(int(self.side[model.FLAG].sum()),46)
        reserved=self.e['reservados']
        self.assertEqual(len(reserved),59)
        self.assertEqual(int(self.side.loc[sorted(reserved),model.FLAG].sum()),14)

    def test_sidecar_index_order_irrelevant(self):
        a=run.contexto(self.e,self.side,'B',1,0)
        b=run.contexto(self.e,self.side.iloc[::-1],'B',1,0)
        for u,v in zip(a,b):
            if isinstance(u,pd.Series):pd.testing.assert_series_equal(u,v)
            else:pd.testing.assert_frame_equal(u,v)

    def test_held_out_labels_not_in_training(self):
        X,y,q=run.contexto(self.e,self.side,'A',1,0)
        changed=copy.deepcopy(self.e)
        for key,row in changed['tabla'].items():
            if row['id_parcela'] in q.index:row['rendimiento_t_ha']='999999'
        a,b,c=run.contexto(changed,self.side,'A',1,0)
        pd.testing.assert_frame_equal(X,a);pd.testing.assert_series_equal(y,b);pd.testing.assert_frame_equal(q,c)
        self.assertNotIn('rendimiento_t_ha',X);self.assertNotIn('rendimiento_t_ha',q)

    def test_sidecar_cannot_overwrite_existing_columns(self):
        bad=self.side.copy();bad['municipio']='bad'
        with self.assertRaises(ValueError):run.contexto(self.e,bad,'A',1,0)

    def test_schema_guard_does_not_accept_modified_source(self):
        with patch.object(run,'sha',return_value='alterado'):
            with self.assertRaises(ValueError):run.cargar(ROOT)

    def test_complete_needs_explicit_confirmation(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):run.ejecutar(ROOT,Path(d)/'new','completa')

    def test_complete_needs_test_evidence(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):run.ejecutar(ROOT,Path(d)/'new','completa',confirmar_completa=True)

    def test_existing_destination_is_preserved(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'keep';p.mkdir();(p/'marker').write_text('keep')
            with self.assertRaises(ValueError):run.ejecutar(ROOT,p)
            self.assertEqual((p/'marker').read_text(),'keep')

    def test_independent_equations_fixture(self):
        X,y=fixture();a=Auditor(ROOT)
        a.table={i:{'municipio':r.municipio,'cultivo_origen':r.cultivo_origen,'x':r.x,
                    'rendimiento_t_ha':str(y.loc[i])} for i,r in X.iterrows()}
        a.side={i:{model.VALUE:'' if np.isnan(r[model.VALUE]) else str(r[model.VALUE]),
                   model.FLAG:str(int(r[model.FLAG]))} for i,r in X.iterrows()}
        for mode in ['Q','E1']:
            m=model.ModeloE1(['x'],.1,mode).fit(X,y)
            p,s,b=a.predict(list(X.index),list(X.index),['x'],.1,mode)
            np.testing.assert_allclose(m.predict(X),p,rtol=0,atol=1e-12)
            np.testing.assert_allclose(m.estado()['coeficientes'],b,rtol=0,atol=1e-12)


if __name__=='__main__':unittest.main()
