import unittest
from scripts.aplicabilidad_agregacion import aggregate


class AggregationTests(unittest.TestCase):
    def test_unequal_repetition_counts_do_not_reweight_parcels(self):
        rs=[dict(id_parcela='a',repeticion=str(k),error_historico=0.) for k in range(5)]
        rs.append(dict(id_parcela='b',repeticion='0',error_historico=2.))
        result=aggregate(rs)
        self.assertEqual(result['MAE_por_parcela_t_ha'],1.)
        self.assertAlmostEqual(result['MAE_por_registro_t_ha'],1/3)
        self.assertEqual(result['n_repeticiones_por_parcela_min'],1)

    def test_rmse_is_not_error_of_averaged_predictions(self):
        rs=[dict(id_parcela='a',repeticion=str(k),error_historico=e) for k,e in enumerate([1.,-1.])]
        r=aggregate(rs)
        self.assertEqual(r['RMSE_por_parcela_t_ha'],1.)
        self.assertEqual(r['sesgo_por_parcela_t_ha'],0.)

    def test_duplicate_repetition_rejected(self):
        r=dict(id_parcela='a',repeticion='1',error_historico=0.)
        with self.assertRaises(ValueError):aggregate([r,r])

    def test_empty_group_not_reported_as_zero(self):
        with self.assertRaises(ValueError):aggregate([])

    def test_nonfinite_error_rejected(self):
        with self.assertRaises(ValueError):aggregate([dict(id_parcela='a',repeticion='1',error_historico='nan')])


if __name__=='__main__':unittest.main()
