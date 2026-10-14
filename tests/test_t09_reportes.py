"""Comprobaciones independientes de métricas, remuestreo y máscara T09."""
import importlib.util
import json
from pathlib import Path
import unittest

import numpy as np
import pandas as pd

try:
    from scripts import t09_reportes as rep
except ImportError:
    spec = importlib.util.spec_from_file_location('t09_reportes_propuesta', Path(__file__).parents[1] / 'scripts/t09_reportes.py')
    rep = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rep)

RAIZ = Path('/Users/danielalira/Desktop/Agrocebada/AgroCebada-2026')
if not (RAIZ / 'registro/t09/diseno.json').is_file():
    RAIZ = Path(__file__).resolve().parents[1]
CONFIG = json.loads((RAIZ / 'registro/t09/diseno.json').read_text())


def fixture(escenarios=('A', 'B', 'C'), variantes=True):
    filas = []
    for esc in escenarios:
        for r in ([1] if esc == 'C' else range(1, 6)):
            for i in range(6):
                pid, y = f'P{i}', float(i)
                soporte = esc != 'C' and i != 5 and not (esc == 'B' and i == 4 and r >= 4)
                fuente = 'municipio' if soporte else 'global'
                for proc in rep.PROCEDIMIENTOS:
                    vs = rep.VARIANTES if variantes and proc != 'T' else ('seleccionada',)
                    for v in vs:
                        error = {'T': 2., 'CL': 1., 'TC': .5, 'R': .75}[proc]
                        if v == 'abr_oct':
                            error += .1
                        p = y + error
                        ref = p if proc == 'T' else y + 2
                        filas.append(dict(escenario=esc, procedimiento=proc, variante=v,
                                          id_parcela=pid, repeticion=r, particion=i // 2,
                                          municipio=f'M{i//2}', cultivo_origen='Cebada',
                                          celda_chirps=f'C{i//2}', real=y, prediccion=p,
                                          referencia=ref, correccion=p-ref,
                                          fuente=('global' if proc == 'CL' else fuente),
                                          fuente_referencia=fuente, sin_respaldo=soporte,
                                          ventana='' if proc == 'T' else 'jun_oct' if v == 'seleccionada' else v,
                                          lambda_reg=np.nan if proc == 'T' else .1, n_entrenamiento=10))
    q = pd.DataFrame([dict(id_parcela=f'P{i}', contorno_categoria='B' if i == 0 else 'A',
                           contorno_angosta_o_muy_pequena='si' if i == 1 else 'no',
                           alerta_contorno_t03_bis='si' if i <= 1 else 'no',
                           escalon_etiqueta_municipio=.5 if i < 2 else .01,
                           vecina_etiquetada_menos_20m='si' if i < 3 else 'no') for i in range(6)])
    return pd.DataFrame(filas), q


class TestT09Reportes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.oof, cls.calidad = fixture()
        cls.r = rep.calcular_reportes(cls.oof, cls.calidad, CONFIG)

    def test_metricas_formula_independiente(self):
        m = rep.metricas([1, 2, 4], [2, 1, 6])
        self.assertAlmostEqual(m['MAE'], 4/3)
        self.assertAlmostEqual(m['RMSE'], np.sqrt(2))
        self.assertAlmostEqual(m['sesgo'], 2/3)
        self.assertAlmostEqual(m['R2'], 1-6/(14/3))
        self.assertEqual(m['estado_R2'], 'definido')

    def test_r2_indefinido_no_cero_ficticio(self):
        for y, p, estado in [([], [], 'sin_casos'), ([2], [2], 'n_menor_2'),
                             ([2, 2], [2, 2], 'y_constante'),
                             ([.1]*3, [.11]*3, 'y_constante')]:
            m = rep.metricas(y, p)
            self.assertTrue(np.isnan(m['R2']))
            self.assertEqual(m['estado_R2'], estado)
        self.assertLess(rep.metricas([0, 1], [8, 8])['R2'], 0)

    def test_resumen_repeticiones_no_promedio_folds(self):
        x, q = fixture(('A',), variantes=False)
        mask = x.procedimiento.eq('TC')
        x.loc[mask, 'prediccion'] = x.loc[mask, 'real'] + x.loc[mask, 'repeticion']*.1
        x.loc[mask, 'correccion'] = x.loc[mask, 'prediccion'] - x.loc[mask, 'referencia']
        r = rep.calcular_reportes(x, q, CONFIG)
        z = r['metricas_resumen'].query("procedimiento=='TC' and poblacion=='todas'").iloc[0]
        self.assertAlmostEqual(z.MAE, .3)
        self.assertAlmostEqual(z.MAE_sd_rep, np.std([.1, .2, .3, .4, .5], ddof=0))
        self.assertEqual(z.n_repeticiones, 5)
        self.assertEqual(z.n_parcelas, 6)
        self.assertEqual(z.n_predicciones, 30)

    def test_cl_usa_mascara_comun_aunque_fuente_global(self):
        m = self.r['metricas_por_repeticion']
        a = m.query("escenario=='A' and variante=='seleccionada' and poblacion=='sin_respaldo'")
        self.assertEqual(a.n_predicciones.unique().tolist(), [5])
        self.assertEqual(set(a.procedimiento), set(rep.PROCEDIMIENTOS))

    def test_dmae_por_id_no_media_reps_con_tamanos_distintos(self):
        x, q = fixture(('B',), variantes=False)
        mask = x.procedimiento.eq('TC')
        # P4 sólo es elegible 3 veces y tiene diferencia mucho mayor.
        x.loc[mask, 'prediccion'] = x.loc[mask, 'real'] + np.where(x.loc[mask, 'id_parcela'].eq('P4'), 12., 2.)
        x.loc[mask, 'correccion'] = x.loc[mask, 'prediccion']-x.loc[mask, 'referencia']
        r = rep.calcular_reportes(x, q, CONFIG)
        z = r['comparaciones_emparejadas'].query("candidato=='TC' and frente_a=='T' and poblacion=='sin_respaldo'").iloc[0]
        self.assertAlmostEqual(z.dMAE, 2.) # (0+0+0+0+10)/5
        self.assertAlmostEqual(z.dMAE_media_rep, 1.2) # (2+2+2+0+0)/5
        ds = r['diferencias_por_parcela'].query("candidato=='TC' and frente_a=='T' and poblacion=='sin_respaldo'")
        self.assertEqual(ds.set_index('id_parcela').loc['P4', 'n_repeticiones_elegibles'], 3)

    def test_bootstrap_celda_independiente_determinista(self):
        d = pd.Series([-.7, .2, -.3, 1.1], index=list('abcd'))
        c = pd.Series(['c1', 'c1', 'c1', 'c2'], index=list('abcd'))
        got = rep._bootstrap(d, c, CONFIG['evaluacion']['bootstrap'])
        rng = np.random.RandomState(20261006)
        samples = rng.randint(0, 2, size=(5000, 2))
        expected = np.array([sum([-.8, 1.1][j] for j in row)/sum([3, 1][j] for j in row) for row in samples])
        np.testing.assert_allclose([got['IC95_celdas_inf'], got['IC95_celdas_sup']], np.percentile(expected, [2.5, 97.5]), atol=1e-14)
        self.assertEqual(got, rep._bootstrap(d.sample(frac=1, random_state=1), c, CONFIG['evaluacion']['bootstrap']))

    def test_regla_solo_A_sin_respaldo_selected_frente_T(self):
        c = self.r['comparaciones_emparejadas']
        aplica = c.aplica_regla_promocion
        self.assertEqual(int(aplica.sum()), 3)
        self.assertTrue(c.loc[aplica, 'cumple_regla_promocion'].all())
        self.assertTrue(c.loc[~aplica, 'cumple_regla_promocion'].isna().all())
        self.assertFalse(((c.escenario == 'C') & c.poblacion.eq('sin_respaldo')).any())
        self.assertEqual(set(map(tuple, c[['candidato', 'frente_a']].drop_duplicates().values)), set(rep.PARES))
        fixed = c[c.variante.ne('seleccionada')]
        self.assertEqual(set(map(tuple, fixed[['candidato', 'frente_a']].drop_duplicates().values)), set(rep.PARES_FIJOS))

    def test_sensibilidad_mismas_oof_sin_reentrenar(self):
        s = self.r['sensibilidad_resumen']
        z = s.query("escenario=='A' and procedimiento=='TC' and variante=='seleccionada' and poblacion=='todas'").iloc[0]
        self.assertEqual(z.n_parcelas, 4)
        self.assertEqual(z.n_predicciones, 20)
        self.assertEqual(z.n_alertas_excluidas, 2)
        self.assertFalse(z.reentrenado)
        self.assertAlmostEqual(z.MAE, .5)
        self.assertTrue(self.r['sensibilidad_orden'].mantiene_orden.all())

    def test_desgloses_union_por_id_y_n_pequeno(self):
        d = self.r['desgloses_resumen']
        z = d.query("escenario=='A' and procedimiento=='T' and variante=='seleccionada' and poblacion=='todas' and desglose=='contorno' and categoria=='B/C'").iloc[0]
        self.assertEqual(z.n_parcelas, 1)
        self.assertEqual(z.n_predicciones, 5)
        self.assertTrue(z.poco_informativo)
        self.assertEqual(set(d.desglose), {'municipio', 'cultivo_origen', 'contorno', 'contorno_angosta_o_muy_pequena', 'escalon_etiqueta', 'vecina_etiquetada_menos_20m'})

    def test_resultados_no_cambian_con_orden_de_filas(self):
        rr = rep.calcular_reportes(self.oof.sample(frac=1, random_state=3), self.calidad.sample(frac=1, random_state=4), CONFIG)
        for k, v in self.r.items():
            pd.testing.assert_frame_equal(v, rr[k], check_exact=False, rtol=1e-14, atol=1e-14)

    def test_bloquea_duplicados_y_contextos_no_emparejados(self):
        with self.assertRaisesRegex(ValueError, 'duplicada'):
            rep.calcular_reportes(pd.concat([self.oof, self.oof.iloc[:1]]), self.calidad, CONFIG)
        with self.assertRaisesRegex(ValueError, 'mismas claves'):
            rep.calcular_reportes(self.oof.drop(self.oof.index[1]), self.calidad, CONFIG)

    def test_bloquea_mascara_cl_individual_y_calidad_incompleta(self):
        x = self.oof.copy()
        x.loc[x.procedimiento.eq('CL'), 'sin_respaldo'] = False
        with self.assertRaisesRegex(ValueError, 'máscara común'):
            rep.calcular_reportes(x, self.calidad, CONFIG)
        with self.assertRaisesRegex(ValueError, 'cubre todas'):
            rep.calcular_reportes(self.oof, self.calidad.iloc[1:], CONFIG)

    def test_bloquea_menu_o_bootstrap_modificado(self):
        config = json.loads(json.dumps(CONFIG))
        config['evaluacion']['bootstrap']['replicas'] = 50
        with self.assertRaisesRegex(ValueError, 'Bootstrap'):
            rep.calcular_reportes(self.oof, self.calidad, config)

    def test_numero_entrenamiento_entero_positivo(self):
        for n in (0, -1, .5):
            x = self.oof.copy()
            x['n_entrenamiento'] = n
            with self.assertRaisesRegex(ValueError, 'entero positivo'):
                rep.calcular_reportes(x, self.calidad, CONFIG)

    def test_reproduce_intervalos_T08_aceptados(self):
        # Sólo recalcula reportes de OOF ya publicadas; no ajusta modelos.
        spec = importlib.util.spec_from_file_location('t08_independiente', RAIZ / 'scripts/t08_referencias.py')
        t08 = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(t08)
        antigua = pd.read_csv(RAIZ / 'registro/t03/predicciones_oof_referencias_media_mun__resp_global.csv')
        nueva = pd.read_csv(RAIZ / 'registro/t03/predicciones_oof_referencias_media_mun__resp_grupo.csv')
        part = pd.read_csv(RAIZ / 'registro/t03/particiones.csv')
        celda = part.drop_duplicates('ID_POLIGONO').set_index('ID_POLIGONO').celda_chirps
        anterior = t08.emparejada(pd.concat([antigua, nueva], ignore_index=True), celda)
        frames = []
        for proc in rep.PROCEDIMIENTOS:
            z = (antigua if proc == 'T' else nueva).copy()
            z = z.rename(columns={'ID_POLIGONO': 'id_parcela'})
            z['procedimiento'], z['variante'] = proc, 'seleccionada'
            z['sin_respaldo'] = z.fuente.eq('municipio')
            z['celda_chirps'] = z.id_parcela.map(celda)
            frames.append(z)
        got, _ = rep._comparaciones(pd.concat(frames, ignore_index=True), CONFIG['evaluacion'])
        g = got.query("candidato=='TC' and frente_a=='T'").set_index(['escenario', 'poblacion'])
        a = anterior.query("candidato=='media_mun__resp_grupo'").rename(columns={'subconjunto': 'poblacion'}).set_index(['escenario', 'poblacion'])
        for c in ('dMAE', 'IC95_celdas_inf', 'IC95_celdas_sup', 'IC95_parcelas_inf',
                  'IC95_parcelas_sup', 'dRMSE', 'n_celdas', 'reps_que_mejoran',
                  'n_predicciones', 'parcelas_mejoran', 'parcelas_empeoran'):
            np.testing.assert_allclose(g.loc[a.index, c].round(4), a[c], atol=1e-12, rtol=0, err_msg=c)


if __name__ == '__main__':
    unittest.main()
