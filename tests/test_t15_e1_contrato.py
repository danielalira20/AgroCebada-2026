"""Contrato y sus contraejemplos; sin entrenar ni crear etiquetas."""
import copy
from pathlib import Path
import tempfile
import unittest
from scripts.t15_e1_contrato import (ROOT,CONFIG,VALUE,FLAG,read_json,read_csv,validate,
                                     classify,boolean,require_execution,population,run)


class ContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract=read_json(ROOT/CONFIG)
        cls.profiles=read_csv(ROOT/'registro/t15_d1/perfil_ndwi_postpico.csv')
        cls.full=next(r for r in cls.profiles if r['calculable']=='True' and r['intervalo_truncado']=='False')
        cls.partial=next(r for r in cls.profiles if r['calculable']=='True' and r['intervalo_truncado']=='True')
        cls.missing=next(r for r in cls.profiles if r['calculable']=='False')

    def altered(self,*path,value):
        d=copy.deepcopy(self.contract);target=d
        for p in path[:-1]:target=target[p]
        target[path[-1]]=value
        return d

    def test_valid_proposal(self):
        self.assertEqual(validate(self.contract)['estado'],'propuesta_valida_no_ejecutable')

    def test_cannot_execute(self):
        with self.assertRaisesRegex(RuntimeError,'no ejecutar'):require_execution(self.contract)

    def test_cannot_enable_by_flag(self):
        with self.assertRaises(ValueError):validate(self.altered('ejecutable',value=True))

    def test_cannot_claim_accepted(self):
        with self.assertRaises(ValueError):validate(self.altered('inscripcion_experimental_aceptada',value=True))

    def test_cannot_impute_with197(self):
        with self.assertRaises(ValueError):validate(self.altered('preprocesamiento','mediana',value='mediana_197'))

    def test_fixed_indicator_required(self):
        with self.assertRaises(ValueError):validate(self.altered('preprocesamiento','indicador',value='solo_si_falta_en_fit'))

    def test_n_all_training_rows(self):
        with self.assertRaises(ValueError):validate(self.altered('preprocesamiento','conteo_alpha',value='solo_106'))

    def test_main_budget_preserved(self):
        with self.assertRaises(ValueError):validate(self.altered('presupuesto','T15_principal_sin_cambios','opciones',value=76))

    def test_control_budget_not_hidden(self):
        with self.assertRaises(ValueError):validate(self.altered('presupuesto','E1_mas_control_propuesto','Ridge_internos_max',value=1600))

    def test_Q_not_promoted_automatically(self):
        with self.assertRaises(ValueError):validate(self.altered('comparaciones','Q',value='ganador_si_sale_mejor'))

    def test_full_observation_preserved(self):
        r=classify(self.full)
        self.assertEqual(r[VALUE],self.full['contraste_ndwi']);self.assertEqual(r[FLAG],0)
        self.assertTrue(r['conservar_fila'])

    def test_partial_is_preserved_but_not_used(self):
        r=classify(self.partial)
        self.assertEqual(r['valor_observado_D1'],self.partial['contraste_ndwi'])
        self.assertEqual(r[VALUE],'');self.assertEqual(r[FLAG],1)

    def test_missing_never_becomes_zero(self):
        r=classify(self.missing)
        self.assertEqual(r[VALUE],'');self.assertEqual(r[FLAG],1)

    def test_true_zero_observation(self):
        d=dict(self.full,contraste_ndwi='0',ndwi_media_post=self.full['ndwi_ancla'])
        r=classify(d);self.assertEqual(r[VALUE],'0');self.assertEqual(r[FLAG],0)

    def test_string_False_is_false(self):
        self.assertFalse(boolean('False'))
        with self.assertRaises(ValueError):boolean('false')

    def test_inconsistent_truncation_rejected(self):
        with self.assertRaises(ValueError):classify(dict(self.full,intervalo_truncado='True'))

    def test_empty_valid_contrast_rejected(self):
        with self.assertRaises(ValueError):classify(dict(self.full,contraste_ndwi=''))

    def test_nonfinite_rejected(self):
        with self.assertRaises(ValueError):classify(dict(self.full,contraste_ndwi='inf'))

    def test_future_peak_rejected(self):
        with self.assertRaises(ValueError):classify(dict(self.full,fecha_maximo='2025-11-01'))

    def test_post_dates_must_be_distinct(self):
        d=dict(self.full);dates=d['fechas_post'].split(';');dates[-1]=dates[0];d['fechas_post']=';'.join(dates)
        with self.assertRaises(ValueError):classify(d)

    def test_y_is_not_accessed(self):
        class Row(dict):
            def __getitem__(self,key):
                if 'rendimiento' in key:raise RuntimeError('No leer y')
                return super().__getitem__(key)
        d=Row(self.full);d['rendimiento_t_ha']='texto_que_no_debe_leerse'
        self.assertEqual(classify(d),classify(self.full))

    def test_population_complete(self):population(self.profiles)

    def test_population_cannot_drop_missing(self):
        with self.assertRaises(ValueError):population([r for r in self.profiles if r['calculable']=='True'])

    def test_duplicate_ids_rejected(self):
        with self.assertRaises(ValueError):population(self.profiles+[self.profiles[0]])

    def test_old_destination_preserved(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);(p/'conservar').write_text('dato')
            with self.assertRaises(ValueError):run(p)
            self.assertEqual((p/'conservar').read_text(),'dato')

    def test_json_duplicate_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'d.json';p.write_text('{"a":1,"a":2}')
            with self.assertRaises(ValueError):read_json(p)

    def test_real_counts(self):
        rows=[classify(r) for r in self.profiles if r['ventana']=='abr_oct']
        self.assertEqual(sum(r[FLAG]==0 for r in rows),151)
        self.assertEqual(sum(r[FLAG] for r in rows),46)
        self.assertEqual(sum(r[FLAG]==0 and r['conjunto']=='PREDICCION' for r in rows),45)


if __name__=='__main__':unittest.main()
