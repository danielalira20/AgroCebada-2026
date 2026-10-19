"""Controles de v3: datos reales y alteraciones aisladas, sin nueva entrega T15."""
import copy
from fractions import Fraction
import io
import json
import unittest
from unittest.mock import patch

import joblib
import numpy as np
import pandas as pd
from sklearn.base import clone

from scripts import evaluacion_comun_centrado_loo as v3
from scripts import evaluacion_comun_centrado_loo_auditar as auditor
from scripts import evaluacion_comun_modelo as base


class CentroLOO(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.e = v3.cargar_entradas()
        cls.x, cls.y, cls.q = base.preparar_contexto(cls.e, 'A', 1, 0)
        cls.cols = ['elevacion_media_m', base.NULLABLE, 'area_ha_origen']
        cls.propuesta = json.loads((v3.RAIZ/'registro/evaluacion_comun/propuesta_t15_centrado_loo_v3.json').read_text())

    def fit_real(self, cols=None):
        return v3.CorreccionComunCentradaLOO(self.cols if cols is None else cols, .1).fit(self.x, self.y)

    def test_identidad_y_poblacion(self):
        self.assertEqual((len(self.e['conocidos']), len(self.e['reservados'])), (138, 59))
        self.assertEqual(self.fit_real().estado()['version'], v3.VERSION)

    def test_propuesta_protegida_no_ejecutable(self):
        with self.assertRaisesRegex(ValueError, 'pendiente'):
            v3.validar_experimento(self.propuesta, self.e)

    def test_identidad_v2_no_acredita_v3(self):
        for key, val in [('schema', 'experimento_comun_centrado_v2'),
                         ('sha_procedimiento', v3.v2.DISENO_SHA)]:
            p = copy.deepcopy(self.propuesta)
            p[key], p['estado'] = val, 'registrado_antes_de_ejecutar'
            with self.subTest(key=key), self.assertRaises(ValueError):
                v3.validar_experimento(p, self.e)

    def test_estructura_ocho_sesenta_solo_en_memoria(self):
        p = copy.deepcopy(self.propuesta)
        p['estado'] = 'registrado_antes_de_ejecutar'
        self.assertEqual(v3.validar_experimento(p, self.e)['opciones_con_variables'], 60)
        self.assertNotEqual(self.propuesta['estado'], p['estado'])

    def test_contrastes_no_reutilizan_nombres_v2(self):
        p = copy.deepcopy(self.propuesta)
        p['estado'] = 'registrado_antes_de_ejecutar'
        p['contrastes_planificados'][0]['candidato'] = 'comun_centrado_v2_C'
        with self.assertRaisesRegex(ValueError, 'Contraste'):
            v3.validar_experimento(p, self.e)

    def test_pools_y_residuos_eliminacion_explicita(self):
        m = self.fit_real()
        for pid in self.x.index:
            r = self.x.loc[pid]
            rest = self.x.drop(index=pid)
            sel = rest.municipio == r.municipio
            src = 'municipio'
            if not sel.any():
                sel, src = rest.cultivo_origen == r.cultivo_origen, 'grupo'
            if not sel.any():
                sel, src = pd.Series(True, index=rest.index), 'global'
            ids = tuple(rest.loc[sel].sort_index().index)
            self.assertEqual(m.pools_sin_fila_[pid], (src, ids))
            self.assertNotIn(pid, ids)
            ref = sum(Fraction(str(self.y.loc[i])) for i in ids)/len(ids)
            actual = m.residuos_[list(m.ids_entrenamiento_).index(pid)]
            self.assertAlmostEqual(actual, float(Fraction(str(self.y.loc[pid]))-ref), places=12)

    def test_identidad_factor_n_sobre_n_menos_uno(self):
        m = self.fit_real()
        z = m.escalador_.transform(m._valores(self.x.sort_index()))
        frame = pd.DataFrame(z, index=m.ids_entrenamiento_)
        for mun, g in self.x.groupby('municipio'):
            n = len(g)
            if n >= 2:
                z_g = frame.loc[g.index].to_numpy()
                d = z_g - m.centros_sin_fila_.loc[g.index].to_numpy()
                np.testing.assert_allclose(d, n/(n-1)*(z_g-z_g.mean(0)), atol=1e-12, rtol=0)
                np.testing.assert_allclose(d.mean(0), 0, atol=1e-12, rtol=0)

    def test_matriz_independiente_y_transformaciones(self):
        a = auditor.independiente(self.x, self.y, self.q, self.cols)
        m = self.fit_real()
        np.testing.assert_allclose(m.predict(self.q), a['pred'], atol=1e-12, rtol=0)
        np.testing.assert_allclose(m.ridge_.coef_, a['coef'], atol=1e-12, rtol=0)
        np.testing.assert_allclose(m.centros_sin_fila_, a['centers'], atol=1e-12, rtol=0)
        self.assertEqual(m.alpha_, len(self.x)*.1)
        self.assertIn(base.NULLABLE+'__faltante', m.nombres_)

    def test_dos_filas_municipales_y_singleton_respaldado(self):
        x = self.x.iloc[:3].copy()
        x['municipio'] = ['par', 'par', 'unico']
        x['cultivo_origen'] = 'Cebada'
        y = self.y.loc[x.index]
        m = v3.CorreccionComunCentradaLOO(['elevacion_media_m'], .1).fit(x, y)
        self.assertEqual(m.pools_sin_fila_[x.index[0]], ('municipio', (x.index[1],)))
        self.assertEqual(m.pools_sin_fila_[x.index[2]], ('grupo', tuple(x.index[:2])))
        self.assertEqual(m.n_, 3)
        self.assertEqual(m.predict_with_details(x).correccion.iloc[2], 0)

    def test_singleton_grupo_recurre_global_sin_fila(self):
        x = self.x.iloc[:3].copy()
        x['municipio'] = ['unico', 'par', 'par']
        x['cultivo_origen'] = ['Cebada', 'CEBADA', 'CEBADA']
        m = v3.CorreccionComunCentradaLOO(['elevacion_media_m'], .1).fit(x, self.y.loc[x.index])
        self.assertEqual(m.pools_sin_fila_[x.index[0]], ('global', tuple(x.index[1:])))

    def test_correccion_una_fila_rechaza_y_ref_sola_admite(self):
        x = self.x.iloc[:1]
        with self.assertRaisesRegex(ValueError, 'dos filas'):
            v3.CorreccionComunCentradaLOO(['elevacion_media_m'], .1).fit(x, self.y.loc[x.index])
        m = v3.CorreccionComunCentradaLOO().fit(x, self.y.loc[x.index])
        np.testing.assert_array_equal(m.predict(x), self.y.loc[x.index])

    def test_cero_filas_rechaza(self):
        with self.assertRaises(ValueError):
            v3.CorreccionComunCentradaLOO().fit(self.x.iloc[:0], self.y.iloc[:0])

    def test_predict_municipio_ausente_grupo_global(self):
        x = self.x.loc[self.x.cultivo_origen == 'Cebada']
        m = v3.CorreccionComunCentradaLOO(['area_ha_origen'], .1).fit(x, self.y.loc[x.index])
        q = x.iloc[:2].copy()
        q['municipio'] = 'ausente'
        q.loc[q.index[1], 'cultivo_origen'] = 'CEBADA'
        p = m.predict_with_details(q)
        self.assertEqual(p.fuente.tolist(), ['grupo', 'global'])
        self.assertEqual(p.fuente.tolist(), p.fuente_centrado.tolist())

    def test_constantes_no_generan_correccion(self):
        x = self.x.copy()
        x['elevacion_media_m'] = 100
        m = v3.CorreccionComunCentradaLOO(['elevacion_media_m'], .1).fit(x, self.y)
        np.testing.assert_array_equal(m.ridge_.coef_, 0)
        np.testing.assert_array_equal(m.predict_with_details(self.q).correccion, 0)

    def test_predict_train_conserva_media_municipal_cero(self):
        m = self.fit_real()
        self.assertLess(m.predict_with_details(self.x).correccion.groupby(self.x.municipio).mean().abs().max(), 1e-12)

    def test_validacion_no_se_fuerza_cero(self):
        m = self.fit_real(['elevacion_media_m'])
        q = self.q.copy()
        q['elevacion_media_m'] += 1000
        self.assertGreater(m.predict_with_details(q).correccion.abs().max(), 1e-8)

    def test_lote_orden_y_estado_congelados(self):
        m = self.fit_real()
        state = json.dumps(m.estado(), sort_keys=True)
        p = m.predict(self.q)
        single = [m.predict(self.q.loc[[pid]])[0] for pid in self.q.index]
        np.testing.assert_allclose(p, single, atol=1e-12, rtol=0)
        np.testing.assert_allclose(p, m.predict(self.q.iloc[::-1])[::-1], atol=1e-12, rtol=0)
        self.assertEqual(json.dumps(m.estado(), sort_keys=True), state)

    def test_clone_joblib_y_estado_profundo(self):
        m = self.fit_real()
        n = clone(m).fit(self.x, self.y)
        b = io.BytesIO()
        joblib.dump(m, b)
        b.seek(0)
        np.testing.assert_array_equal(m.predict(self.q), joblib.load(b).predict(self.q))
        np.testing.assert_array_equal(m.predict(self.q), n.predict(self.q))
        state = m.estado()
        state['pools_sin_fila'].clear()
        state['centros_Z_sin_fila'].clear()
        self.assertTrue(m.pools_sin_fila_)

    def test_fit_fallido_limpia_y_parametros_exigen_reajustar(self):
        m = self.fit_real()
        m.set_params(lambda_reg=10)
        with self.assertRaisesRegex(ValueError, 'Reajustar'):
            m.predict(self.q)
        bad = self.x.copy()
        bad[base.NULLABLE] = np.nan
        with self.assertRaisesRegex(ValueError, 'totalmente ausente'):
            m.fit(bad, self.y)
        self.assertFalse(hasattr(m, 'pools_sin_fila_'))
        with self.assertRaisesRegex(ValueError, 'sin ajustar'):
            m.predict(self.q)

    def test_roles_etiquetas_bool_y_ids_invalidos(self):
        for mode in ['target', 'bool', 'duplicate', 'misaligned']:
            x, y, cols = self.x.copy(), self.y.copy(), self.cols
            if mode == 'target':
                x['rendimiento_t_ha'] = y
                cols = ['rendimiento_t_ha']
            if mode == 'bool':y = y > 0
            if mode == 'duplicate':
                x.index = [x.index[0]]*len(x)
                y.index = x.index
            if mode == 'misaligned':y = y.iloc[::-1]
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                v3.CorreccionComunCentradaLOO(cols, .1).fit(x, y)

    def test_internas_refit_pools_sin_externos(self):
        options = [dict(nombre=f'l{l}', columnas=['prec_acumulada_mm_jun_oct'],
                        ventana='jun_oct', lambda_reg=l) for l in base.LAMBDA]
        original, seen = v3.CorreccionComunCentradaLOO.fit, []
        def monitor(model, x, y):
            result = original(model, x, y)
            seen.append(set(model.ids_entrenamiento_))
            if model.ridge_ is not None:
                for pid, (_, ids) in model.pools_sin_fila_.items():
                    self.assertNotIn(pid, ids)
                    self.assertLessEqual(set(ids), set(x.index))
            return result
        with patch.object(v3.CorreccionComunCentradaLOO, 'fit', monitor):
            chosen = v3.seleccionar(self.x, self.y, options)
        self.assertEqual(chosen['n_ajustes'], 20)
        self.assertTrue(all(ids < set(self.x.index) and not ids & set(self.q.index)
                            and not ids & self.e['reservados'] for ids in seen))

    def test_etiquetas_externas_no_cambian_seleccion_ni_prediccion(self):
        exp = copy.deepcopy(self.propuesta)
        exp['estado'], exp['id'] = 'registrado_antes_de_ejecutar', 'SOLO_TEST_EN_MEMORIA'
        candidate = exp['procedimientos'][0]['candidato']
        before = v3.seleccionar_registrado(self.e, exp, candidate, 'A', 1, 0)
        changed = copy.deepcopy(self.e)
        for pid in self.q.index:
            changed['tabla'][(pid,)]['rendimiento_t_ha'] = '9999'
            changed['tabla'][(pid,)]['prec_acumulada_mm_jun_oct'] = '999999'
        after = v3.seleccionar_registrado(changed, exp, candidate, 'A', 1, 0)
        self.assertEqual(before['seleccion'], after['seleccion'])
        self.assertEqual(before['modelo'].estado(), after['modelo'].estado())
        # Las nuevas X externas pueden cambiar su predicción, pero jamás el ajuste.
        unchanged_x_pred = after['modelo'].predict(self.q)
        np.testing.assert_array_equal(before['prediccion'], unchanged_x_pred)


class FrecuenciaReferencia(unittest.TestCase):
    def row(self, fold=0, only=True):
        return dict(candidato='control', escenario='A', repeticion=1, particion=fold,
                    nombre_opcion='referencia_sola' if only else 'lambda_1',
                    referencia_sola=only, lambda_reg=None if only else 1., version=v3.VERSION)

    def test_denominador_y_estado_parcial(self):
        r = v3.frecuencia_referencia_sola([self.row(), self.row(1, False)])[0]
        self.assertEqual((r['n_contextos'], r['n_referencia_sola'], r['estado']), (2, 1, 'parcial'))
        self.assertEqual(r['fraccion_referencia_sola'], .5)

    def test_25_contextos_completos(self):
        rows = [dict(self.row(), repeticion=rep, particion=fold) for rep in range(1, 6) for fold in range(5)]
        self.assertEqual(v3.frecuencia_referencia_sola(rows)[0]['estado'], 'completo')

    def test_vacio_duplicado_bandera_version_invalidos(self):
        bad = dict(self.row(), referencia_sola=False)
        old = dict(self.row(), version='comun-centrado-v2')
        for rows in [[], [self.row(), self.row()], [bad], [old]]:
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                v3.frecuencia_referencia_sola(rows)

    def test_contextos_y_lambda_bool_invalidos(self):
        for changes in [dict(particion=True), dict(repeticion=6), dict(escenario='C'),
                        dict(nombre_opcion='lambda', referencia_sola=False, lambda_reg=True)]:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                v3.frecuencia_referencia_sola([dict(self.row(), **changes)])


if __name__ == '__main__':
    unittest.main()
