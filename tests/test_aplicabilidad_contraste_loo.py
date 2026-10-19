"""Reglas heredadas, exclusión de fila y denominadores del complemento LOO."""
from pathlib import Path
import tempfile
import unittest

from scripts import aplicabilidad_contraste_loo as c


class ContrastTest(unittest.TestCase):
    def setUp(self):
        self.rep = {'id': 'prueba', 'columnas': ['x']}
        self.table = {'a': {'municipio': 'M', 'x': '1'},
                      'b': {'municipio': 'M', 'x': '2'},
                      'q': {'municipio': 'M', 'x': '4'}}

    def inspect(self, table=None, train=None):
        return c.diagnose(table or self.table, 'q', train or ['a', 'b'], self.rep, 'prueba')

    def test_own_ID_rejected(self):
        with self.assertRaises(ValueError): self.inspect(train=['a', 'q'])

    def test_duplicate_reference_rejected(self):
        with self.assertRaises(ValueError): self.inspect(train=['a', 'a'])

    def test_two_local_references_allow_q95(self):
        r = self.inspect()
        self.assertEqual(r['n_referencia_distancia'], 2)
        self.assertTrue(r['supera_q95_local'])

    def test_no_local_references_stays_missing(self):
        table = {k: dict(v) for k, v in self.table.items()};table['q']['municipio'] = 'otro'
        r = self.inspect(table)
        self.assertIsNone(r['q95_local']);self.assertIsNone(r['supera_q95_local'])
        self.assertTrue(r['fuera_rango_global'])

    def test_singleton_local_stays_missing(self):
        r = self.inspect(train=['a'])
        self.assertIsNone(r['percentil_local_estricto']);self.assertIsNone(r['supera_q95_local'])

    def test_zero_ties_not_false_alerts(self):
        table = {k: {'municipio': 'M', 'x': '0'} for k in self.table}
        r = self.inspect(table)
        self.assertEqual(r['distancia_municipio'], 0.)
        self.assertFalse(r['supera_q95_local']);self.assertEqual(r['percentil_local_estricto'], 0.)
        self.assertEqual(r['entradas_ausentes'], '')

    def test_heldout_X_does_not_fit_reference(self):
        state = c.anterior.fit_space(self.table, ['a', 'b'], ['x'])
        before = (state['mean'].copy(), state['sd'].copy())
        self.table['q']['x'] = '1000'
        c.anterior.inspect_space(self.table, 'q', state)
        self.assertEqual(state['mean'].tolist(), before[0].tolist())
        self.assertEqual(state['sd'].tolist(), before[1].tolist())

    def test_y_not_accessed(self):
        class Row(dict):
            def __getitem__(self, key):
                if key == 'rendimiento_t_ha': raise RuntimeError('No leer y')
                return super().__getitem__(key)
        table = {k: Row(v, rendimiento_t_ha='NO_LEER') for k, v in self.table.items()}
        self.assertEqual(self.inspect(table), self.inspect())

    def test_slope_missing_uses_only_reference_median(self):
        table = {'a': {'municipio': 'M', c.anterior.PEND: ''},
                 'b': {'municipio': 'M', c.anterior.PEND: '2'},
                 'q': {'municipio': 'M', c.anterior.PEND: '100'}}
        state = c.anterior.fit_space(table, ['a', 'b'], [c.anterior.PEND])
        self.assertEqual(state['median'], 2.)
        self.assertEqual(state['z'].shape[1], 2)

    def test_original_rain_tolerance_preserved(self):
        table = {'a': {'municipio': 'M', 'prec_x': '0'},
                 'b': {'municipio': 'M', 'prec_x': '1'},
                 'q': {'municipio': 'M', 'prec_x': '1.0000005'}}
        rep = {'id': 'C', 'columnas': ['prec_x']}
        self.assertEqual(c.diagnose(table, 'q', ['a', 'b'], rep, 'prueba')['fuera_rango_global'], '')
        table['q']['prec_x'] = '1.000002'
        self.assertEqual(c.diagnose(table, 'q', ['a', 'b'], rep, 'prueba')['fuera_rango_global'], 'prec_x')

    def test_unknown_not_counted_as_negative(self):
        r = c.statistics_flags([True, False, None])
        self.assertEqual([r[k] for k in ['n_parcelas_total', 'n_parcelas_evaluables',
                                        'n_parcelas_con_aviso', 'n_parcelas_sin_diagnostico']], [3, 2, 1, 1])
        self.assertEqual(r['proporcion_aviso_observado_sobre_total'], 1/3)
        self.assertEqual(r['proporcion_aviso_sobre_evaluables'], .5)

    def test_empty_group_rates_are_missing(self):
        r = c.statistics_flags([])
        self.assertIsNone(r['proporcion_aviso_sobre_evaluables'])
        self.assertIsNone(r['proporcion_aviso_observado_sobre_total'])

    def test_union_three_states(self):
        self.assertIsNone(c.union_flags([None, False]))
        self.assertTrue(c.union_flags([True, None]))
        self.assertFalse(c.union_flags([False, False]))
        with self.assertRaises(ValueError): c.union_flags([])
        with self.assertRaises(ValueError): c.union_flags(['no'])

    def test_profiles_need_all_representations(self):
        r = self.inspect();r['representacion'] = 'uno'
        with self.assertRaises(ValueError): c.profiles([r], [{'id': 'uno'}, {'id': 'dos'}])

    def test_duplicate_profiles_rejected(self):
        r = self.inspect()
        with self.assertRaises(ValueError): c.profiles([r, r], [self.rep])

    def test_union_counts_parcels_once(self):
        reps = [{'id': f'R{i}'} for i in range(15)]
        records = []
        for rep in reps:
            r = self.inspect();r['cohorte'] = 'etiquetadas_LOO';r['representacion'] = rep['id']
            records.append(r)
        united = c.profiles(records, reps)
        result = c.summaries(records, united, reps)[0]
        row = next(r for r in result if r['representacion'] == 'alguna_de_15' and r['regla'] == 'fuera_rango_global')
        self.assertEqual(row['etiquetadas_n_parcelas_total'], 1)
        self.assertEqual(row['etiquetadas_n_parcelas_con_aviso'], 1)

    def test_existing_output_is_preserved(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp);(p/'dato').write_text('conservar')
            with self.assertRaises(ValueError): c.run(c.ROOT, p)
            self.assertEqual((p/'dato').read_text(), 'conservar')

    def test_existing_detail_is_preserved(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp);detail = p/'detalle';detail.mkdir();(detail/'dato').write_text('conservar')
            with self.assertRaises(ValueError): c.run(c.ROOT, p/'nuevo', detail)
            self.assertFalse((p/'nuevo').exists())
            self.assertEqual((detail/'dato').read_text(), 'conservar')

    def test_loaded_X_has_no_objective(self):
        _, _, table, known, reserved = c.load(c.ROOT)
        self.assertEqual((len(table), len(known), len(reserved)), (197, 138, 59))
        self.assertFalse(any('rendimiento' in col for row in table.values() for col in row))


if __name__ == '__main__': unittest.main()
