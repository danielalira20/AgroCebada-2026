import copy
import csv
from decimal import Decimal
import io
import os
from pathlib import Path
import tempfile
import unittest

from scripts import diagnostico_fase4 as f


class Guards(unittest.TestCase):
    def test_empty_not_zero(self):
        with self.assertRaises(ValueError):f.decimal('')
    def test_nan_rejected(self):
        with self.assertRaises(ValueError):f.decimal('NaN')
    def test_inf_rejected(self):
        with self.assertRaises(ValueError):f.decimal('Infinity')
    def test_exact_decimal_value(self):
        self.assertEqual(f.decimal('3.00'),Decimal(3))
        self.assertNotEqual(f.decimal('3.01'),Decimal(3))
    def test_small_group_unidentified(self):
        self.assertEqual(f.paso([Decimal('3'),Decimal('3.5')]),'')
    def test_coarse_grid(self):
        self.assertEqual(f.paso(list(map(Decimal,['2.5','3','3.5']))),'0.5')
    def test_tenth_grid(self):
        self.assertEqual(f.paso(list(map(Decimal,['2','3.1','3.7']))),'0.1')
    def test_hundredth_grid(self):
        self.assertEqual(f.paso(list(map(Decimal,['2.15','3.03','4.52']))),'0.01')
    def test_constant_compatible_not_accuracy(self):
        self.assertEqual(f.paso([Decimal('3.5')]*3),'0.5')
        self.assertTrue(all(Decimal('3.5')%h==0 for h in map(Decimal,['.5','.1','.01'])))
    def test_nonmatching_grid_missing(self):
        self.assertEqual(f.paso(list(map(Decimal,['.005','.01','.02']))),'')
    def test_duplicate_ids(self):
        with self.assertRaises(ValueError):f.indexed([{'id_parcela':'x'},{'id_parcela':'x'}])
    def test_empty_id(self):
        with self.assertRaises(ValueError):f.indexed([{'id_parcela':''}])
    def test_truncated_dbf(self):
        with self.assertRaises(ValueError):f.original_dbf(b'abc')
    def test_unknown_schema(self):
        with self.assertRaises(ValueError):f.original_csv(b'ID,area,y\nx,1,2\n')
    def test_source_extra_column_rejected(self):
        with self.assertRaises(ValueError):f.original_csv(b'ID_POLIGONO,AREA_HA,RENDIMIENTO_T_HA,CONJUNTO,\nx,1,3,ENTRENAMIENTO,extra\n')
    def test_csv_non_rectangular(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'x.csv';p.write_text('a,b\n1,2,3\n')
            with self.assertRaises(ValueError):f.leer(p)
    def test_written_missing_preserved(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'x.csv';f.csv_write(p,[{'id':'x','y':''}]);self.assertEqual(f.leer(p)[0]['y'],'')
    def test_nominal_area_not_target_correction(self):
        y=Decimal('5.46');a=Decimal('.38');da=Decimal('-.005')
        self.assertEqual(abs(y*da/(a+da)),Decimal('.0728'))


@unittest.skipUnless(os.getenv('AGRO_DIAG_LEDGER'),'Requiere ledger real fijado')
class FixedSources(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw,cls.table,cls.cat,cls.joins=f.cargar(Path(os.environ['AGRO_DIAG_LEDGER']))
        cls.ctx=f.leer(f.ROOT/'registro/diagnostico/fase0/mascaras_contextos.csv')
    def test_all_originals_join(self):
        self.assertEqual(len(self.joins),197);self.assertEqual(sum(r['n_OOF_comprobados'] for r in self.joins),71208)
    def test_reserved_labels_never_evaluated(self):
        rows=[r for r in self.joins if not r['y_presente']]
        self.assertEqual(len(rows),59);self.assertTrue(all(r['n_OOF_comprobados']==0 and r['rendimiento_literal']=='' for r in rows))
    def test_preserve_per_id_literal(self):
        self.assertTrue(all(r['rendimiento_literal']==self.raw[r['id_parcela']]['y'] for r in self.joins))
    def test_450_train_groups(self):
        rows,_=f.granularidad_entreno(self.raw,self.table,self.ctx)
        self.assertEqual(len(rows),450);self.assertTrue(all(not r['etiquetas_evaluacion_usadas'] for r in rows))
    def test_holdout_labels_cannot_change_training_granularity(self):
        _,base=f.granularidad_entreno(self.raw,self.table,self.ctx);modified=copy.deepcopy(self.raw)
        for r in self.ctx:
            if (r['escenario'],r['repeticion'],r['particion'])==('A','1','0'):modified[r['id_parcela']]['y']='123.4567'
        _,after=f.granularidad_entreno(modified,self.table,self.ctx)
        self.assertEqual({k:v for k,v in base.items() if k[:3]==('A',1,0)},{k:v for k,v in after.items() if k[:3]==('A',1,0)})
    def test_seven_extremes_not_ten_cases(self):
        rows,_=f.locales(self.raw,self.table,self.cat)
        self.assertEqual(sum(r['extrema_regla_historica_T02'] in ('alta','baja') for r in rows),7)
        self.assertEqual(next(r for r in rows if r['id_parcela']=='AGC_069')['extrema_regla_historica_T02'],'no')
    def test_no_singleton_loo_imputed(self):
        rows,_=f.locales(self.raw,self.table,self.cat);single=[r for r in rows if r['n_otras_etiquetas_municipio']==0]
        self.assertEqual(len(single),3);self.assertTrue(all(r['media_otras_municipio']==r['desviacion_LOO']=='' for r in single))
    def test_neighbor_repetition_not_duplicate(self):
        rows=f.pares_etiquetas(self.raw,self.table)
        self.assertEqual(len(rows),87);self.assertEqual(sum(r['ambas_etiquetadas'] for r in rows),45)
        self.assertEqual(sum(r['misma_etiqueta']=='si' for r in rows),9)
        self.assertFalse(any(r['duplicado_tecnico_confirmado'] for r in rows))
    def test_area_sensitivity_not_model(self):
        _,rows=f.locales(self.raw,self.table,self.cat)
        self.assertEqual(len(rows),276);self.assertFalse(any(r['nuevo_rendimiento_evaluado'] for r in rows))


if __name__=='__main__':unittest.main()
