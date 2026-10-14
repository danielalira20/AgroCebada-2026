"""Cálculos y fuga: datos reales, referencias independientes y alteraciones sólo en memoria."""
import copy
from dataclasses import replace
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import joblib
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.exceptions import NotFittedError
from sklearn.pipeline import Pipeline

from scripts.t09_entradas import RAIZ, cargar_diseno, cargar_entradas, contexto_externo, validar_particiones
from scripts.t09_estimadores import (CLIMA, OBJETIVO, MediaTerritorial, RidgeClimatico,
                                    columnas_clima, crear_estimador, referencia_loo)
from scripts.t09_seleccion import (ajustar_particion, elegir_configuracion,
                                  mascara_soporte, particiones_internas)


def base_independiente(X, y, te):
    pred, source = [], []
    for m, g in zip(te.municipio, te.cultivo_origen):
        ix = X.municipio.eq(m)
        f = 'municipio'
        if not ix.any():
            ix = X.cultivo_origen.eq(g)
            f = 'grupo'
        if not ix.any():
            ix = pd.Series(True, index=X.index)
            f = 'global'
        pred.append(float(np.mean(y.loc[ix].to_numpy())))
        source.append(f)
    return np.array(pred), np.array(source)


def matriz_independiente(X, y, te, ventana, intensidad, municipal):
    """Matriz completa con interceptos; ecuaciones normales, no centrado municipal/Ridge."""
    cols = columnas_clima(ventana)
    a, b = X[cols].to_numpy(), te[cols].to_numpy()
    mu, sd = a.mean(axis=0), a.std(axis=0, ddof=0)
    sd = np.where(sd == 0, 1., sd)
    z, zt = (a - mu) / sd, (b - mu) / sd
    if municipal:
        municipios = sorted(X.municipio.unique())
        d = np.array([[float(m == k) for k in municipios] for m in X.municipio])
        dt = np.array([[float(m == k) for k in municipios] for m in te.municipio])
        assert te.municipio.isin(municipios).all()
    else:
        d, dt = np.ones((len(X), 1)), np.ones((len(te), 1))
    matrix, test = np.column_stack([d, z]), np.column_stack([dt, zt])
    penalty = np.diag([0.] * d.shape[1] + [len(X) * intensidad] * 3)
    beta = np.linalg.solve(matrix.T @ matrix + penalty, matrix.T @ y.to_numpy())
    return test @ beta, beta[-3:], mu, sd


class EntradasReales(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.e = cargar_entradas()
        cls.X, cls.y = cls.e['X'], cls.e['y']
        cls.a, cls.ya, cls.b, cls.yb = contexto_externo(cls.e, 'A')

    def test_preflight_poblacion_roles_y_proteccion(self):
        self.assertEqual((len(self.X), len(self.y), len(self.e['reservadas'])), (138, 138, 59))
        self.assertNotIn(OBJETIVO, self.X.columns)
        self.assertNotIn(OBJETIVO, self.e['reservadas'])
        self.assertTrue(set(self.X.index).isdisjoint(self.e['reservadas'].index))

    def test_diseño_alterado_no_se_adopta(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'diseno.json'
            p.write_bytes((RAIZ / 'registro/t09/diseno.json').read_bytes() + b'\n')
            with self.assertRaisesRegex(ValueError, 'versionar'):
                cargar_diseno(p)

    def test_particiones_rechazan_duplicados_reservadas_y_celdas_divididas(self):
        p = self.e['particiones']
        mods = [p.copy(), p.copy(), p.copy()]
        mods[0].iloc[1] = mods[0].iloc[0]
        mods[1].loc[0, 'ID_POLIGONO'] = self.e['reservadas'].index[0]
        # Una celda con varias parcelas: separar una manteniendo cinco folds.
        ix = p[p.repeticion.eq(1)].celda_chirps.value_counts().index[0]
        j = p.index[p.repeticion.eq(1) & p.celda_chirps.eq(ix)][0]
        mods[2].loc[j, 'particion_espacial'] = (p.loc[j, 'particion_espacial'] + 1) % 5
        for mod in mods:
            with self.subTest():
                with self.assertRaises(ValueError):
                    validar_particiones(mod, self.X)

    def test_etiquetas_desalineadas_no_se_unen_por_posicion(self):
        with self.assertRaisesRegex(ValueError, 'alineada por ID'):
            MediaTerritorial().fit(self.a, self.ya.iloc[::-1])

    def test_etiqueta_en_X_bloquea_fuga_accidental(self):
        a = self.a.assign(rendimiento_t_ha=self.ya)
        with self.assertRaisesRegex(ValueError, 'Separar etiquetas'):
            RidgeClimatico().fit(a, self.ya)

    def test_id_duplicado_o_indice_ajeno_rechazados(self):
        a = self.a.copy(); a.loc[a.index[0], 'id_parcela'] = a.id_parcela.iloc[1]
        with self.assertRaisesRegex(ValueError, 'IDs únicos'):
            MediaTerritorial().fit(a, self.ya)
        with self.assertRaises(ValueError):
            MediaTerritorial().fit(self.a.reset_index(drop=True), self.ya)

    def test_clima_faltante_infinito_texto_y_booleano_rechazados(self):
        col = columnas_clima('jun_oct')[0]
        for valor in [np.nan, np.inf, '20', True]:
            a = self.a.copy()
            a[col] = pd.Series(valor, index=a.index)
            with self.subTest(valor=valor):
                with self.assertRaises(ValueError):
                    RidgeClimatico().fit(a, self.ya)

    def test_etiquetas_no_finitas_o_anonimas_rechazadas(self):
        for y in [self.ya.to_numpy(), self.ya * np.nan, self.ya.astype(str)]:
            with self.assertRaises(ValueError):
                RidgeClimatico().fit(self.a, y)

    def test_parametros_invalidos_y_cambio_despues_fit(self):
        for kwargs in [dict(lambda_reg=0), dict(lambda_reg=-1), dict(lambda_reg=np.inf),
                       dict(lambda_reg=True), dict(ventana='mayo'), dict(procedimiento='PCA')]:
            with self.assertRaises(ValueError):
                RidgeClimatico(**kwargs).fit(self.a, self.ya)
        model = RidgeClimatico().fit(self.a, self.ya)
        model.set_params(ventana='abr_oct')
        with self.assertRaisesRegex(ValueError, 'Reajustar'):
            model.predict(self.b)

    def test_predict_sin_fit_no_inventa_ceros(self):
        for model in [MediaTerritorial(), RidgeClimatico()]:
            with self.assertRaises(NotFittedError):
                model.predict(self.b)

    def test_fit_fallido_no_deja_modelo_anterior_utilizable(self):
        for kind in ['T','CL','TC','R']:
            model = crear_estimador(kind).fit(self.a,self.ya)
            with self.assertRaises(ValueError):
                model.fit(self.a,self.ya*np.nan)
            with self.subTest(procedimiento=kind):
                with self.assertRaises(NotFittedError):
                    model.predict(self.b)

    def test_referencia_reproduce_T08_todos_contextos_y_mascara(self):
        ref = pd.read_csv(RAIZ / 'registro/t03/predicciones_oof_referencias_media_mun__resp_grupo.csv',
                          float_precision='round_trip')
        counts = {'A': 0, 'B': 0}
        for esc in ['A', 'B']:
            for rep in range(1, 6):
                for fold in range(5):
                    a, ya, b, yb = contexto_externo(self.e, esc, rep, fold)
                    got = MediaTerritorial().fit(a, ya).predict_with_details(b)
                    expected = ref[ref.escenario.eq(esc) & ref.repeticion.eq(rep) & ref.particion.eq(fold)]
                    expected = expected.set_index('ID_POLIGONO').loc[b.index]
                    np.testing.assert_allclose(got.prediccion, expected.prediccion, rtol=0, atol=1e-12)
                    np.testing.assert_array_equal(got.fuente, expected.fuente)
                    np.testing.assert_array_equal(yb, expected.real)
                    np.testing.assert_array_equal(mascara_soporte(a, b), got.fuente.eq('municipio'))
                    counts[esc] += int(got.fuente.eq('municipio').sum())
        self.assertEqual(counts, {'A': 675, 'B': 659})

    def test_respaldo_grupo_y_global_se_conservan(self):
        te = self.b.copy(); te['municipio'] = 'municipio no observado'
        te.loc[te.index[0], 'cultivo_origen'] = 'grupo no observado'
        expected, source = base_independiente(self.a, self.ya, te)
        got = MediaTerritorial().fit(self.a, self.ya).predict_with_details(te)
        np.testing.assert_allclose(got.prediccion, expected, atol=1e-12)
        np.testing.assert_array_equal(got.fuente, source)
        self.assertEqual(got.fuente.iloc[0], 'global')

    def test_LOO_vs_exclusion_explicita_y_etiqueta_propia(self):
        got, source = referencia_loo(self.a, self.ya)
        expected, sources = [], []
        for id_ in self.a.index:
            tr = self.a.drop(index=id_)
            p, f = base_independiente(tr, self.ya.loc[tr.index], self.a.loc[[id_]])
            expected.append(p[0]); sources.append(f[0])
        np.testing.assert_allclose(got, expected, rtol=0, atol=1e-10)
        np.testing.assert_array_equal(source, sources)
        id_ = self.a.index[0]
        mod = self.ya.copy(); mod.loc[id_] += 2
        altered, _ = referencia_loo(self.a, mod)
        self.assertAlmostEqual(got.loc[id_], altered.loc[id_], places=12)

    def test_CL_TC_vs_matriz_completa_ambas_ventanas_y_lambdas(self):
        for w in ['abr_oct', 'jun_oct']:
            for intensidad in [0.01, 0.1, 1., 10.]:
                for tipo in ['CL', 'TC']:
                    te = self.b[self.b.municipio.isin(self.a.municipio)]
                    expected, beta, mu, sd = matriz_independiente(self.a, self.ya, te, w, intensidad, tipo == 'TC')
                    model = RidgeClimatico(tipo, w, intensidad).fit(self.a, self.ya)
                    with self.subTest(tipo=tipo, ventana=w, lambda_reg=intensidad):
                        np.testing.assert_allclose(model.predict(te), expected, rtol=0, atol=1e-9)
                        np.testing.assert_allclose(model.coef_estandarizados_, beta, rtol=0, atol=1e-10)
                        np.testing.assert_allclose(model.preprocesado_['escala'].mean_, mu, atol=1e-12)
                        np.testing.assert_allclose(model.preprocesado_['escala'].scale_, sd, atol=1e-12)
                        self.assertEqual(model.alpha_, len(self.a) * intensidad)

    def test_TC_respaldo_residuo_vs_formula_independiente(self):
        model = RidgeClimatico('TC').fit(self.a, self.ya)
        te = self.b.copy(); te['municipio'] = 'municipio no observado'
        te.loc[te.index[0], 'cultivo_origen'] = 'grupo no observado'
        z = model.preprocesado_.transform(self.a[list(model.columnas_)])
        zt = model.preprocesado_.transform(te[list(model.columnas_)])
        residual = self.ya - z @ model.coef_estandarizados_
        intercept, source = base_independiente(self.a, residual, te)
        got = model.predict_with_details(te)
        np.testing.assert_allclose(got.prediccion, intercept + zt @ model.coef_estandarizados_, atol=1e-10)
        np.testing.assert_array_equal(got.fuente, source)

    def test_R_vs_LOO_independiente_y_sistema_lineal_sin_intercepto(self):
        model = RidgeClimatico('R').fit(self.a, self.ya)
        loo = []
        for id_ in self.a.index:
            tr = self.a.drop(index=id_)
            pred, _ = base_independiente(tr, self.ya.loc[tr.index], self.a.loc[[id_]])
            loo.append(pred[0])
        r = self.ya.to_numpy() - loo
        cols = list(model.columnas_)
        x, te = self.a[cols].to_numpy(), self.b[cols].to_numpy()
        mu, sd = x.mean(0), x.std(0)
        z, zt = (x-mu)/sd, (te-mu)/sd
        beta = np.linalg.solve(z.T @ z + model.alpha_ * np.eye(3), z.T @ r)
        base, source = base_independiente(self.a, self.ya, self.b)
        np.testing.assert_allclose(model.predict(self.b), base + zt @ beta, atol=1e-10)
        self.assertEqual(model.modelo_.intercept_, 0.)
        np.testing.assert_allclose(model.residuos_, r, atol=1e-10)

    def test_TC_clima_constante_por_municipio_reproduce_T(self):
        a, b = self.a.copy(), self.b[self.b.municipio.isin(self.a.municipio)].copy()
        for col in CLIMA:
            medias = a.groupby('municipio')[col].mean()
            a[col], b[col] = a.municipio.map(medias), b.municipio.map(medias)
        expected = MediaTerritorial().fit(a, self.ya).predict(b)
        got = RidgeClimatico('TC').fit(a, self.ya).predict(b)
        np.testing.assert_allclose(got, expected, atol=1e-10)

    def test_clima_constante_global_es_finito_y_R_no_desplaza(self):
        a, b = self.a.copy(), self.b.copy()
        a[list(CLIMA)] = 1.; b[list(CLIMA)] = 1.
        base = MediaTerritorial().fit(a, self.ya).predict(b)
        for kind in ['CL', 'TC', 'R']:
            model = RidgeClimatico(kind).fit(a, self.ya)
            self.assertEqual(len(model.constantes_), 3)
            self.assertTrue(np.isfinite(model.predict(b)).all())
            if kind != 'CL': np.testing.assert_allclose(model.predict(b), base, atol=1e-12)

    def test_CL_no_usa_municipio_grupo_celda_o_otras_columnas(self):
        model = RidgeClimatico('CL').fit(self.a, self.ya)
        before = model.predict(self.b)
        te = self.b.copy(); te['municipio'] = 'otro'; te['cultivo_origen'] = 'otro'
        te['celda_chirps'] = 'otro'; te['area_ha_origen'] = 1e9
        np.testing.assert_array_equal(before, model.predict(te))

    def test_datos_de_entrada_no_se_mutan_y_fit_no_retiene_vistas(self):
        for kind in ['CL', 'TC', 'R']:
            a, ya = self.a.copy(), self.ya.copy()
            model = RidgeClimatico(kind).fit(a, ya)
            before = model.predict(self.b)
            pd.testing.assert_frame_equal(a, self.a)
            pd.testing.assert_series_equal(ya, self.ya)
            a.loc[:,list(CLIMA)] *= 100
            ya.loc[:] += 4.
            np.testing.assert_array_equal(before, model.predict(self.b))

    def test_mascara_interna_de_texto_o_entero_bloqueada(self):
        part = particiones_internas(self.a,'A')[0]
        for val in ['false',1]:
            bad = replace(part,elegibles=tuple(val for _ in part.validacion))
            with self.assertRaisesRegex(ValueError,'Máscara'):
                ajustar_particion(self.a,self.ya,bad,'TC','jun_oct',.1)

    def test_clone_pipeline_serializacion_y_reajuste(self):
        for kind in ['CL', 'TC', 'R']:
            estimator = RidgeClimatico(kind, 'abr_oct', 1.)
            pipe = Pipeline([('estimador', clone(estimator))]).fit(self.a, self.ya)
            expected = pipe.predict(self.b)
            with tempfile.TemporaryDirectory() as tmp:
                f = Path(tmp) / 'model.joblib'; joblib.dump(pipe, f)
                np.testing.assert_array_equal(joblib.load(f).predict(self.b), expected)
            unfitted = clone(pipe['estimador'])
            with self.assertRaises(NotFittedError): unfitted.predict(self.b)

    def test_internas_viables_grupos_disjuntos_orden_ID_en_60_contextos(self):
        cases = [(s,r,k) for s in ['A','B'] for r in range(1,6) for k in range(5)]
        cases += [('C',1,k) for k in range(9)]
        cases += [('A',1,'final')]
        for scenario,rep,fold in cases:
            a = self.X if fold == 'final' else contexto_externo(self.e, scenario, rep, fold)[0]
            parts = particiones_internas(a, scenario)
            self.assertEqual(parts, particiones_internas(a.iloc[::-1], scenario))
            self.assertEqual(len(parts), 4)
            seen = []
            for part in parts:
                self.assertTrue(set(part.entrenamiento).isdisjoint(part.validacion))
                seen.extend(part.validacion)
                if scenario != 'A':
                    col = 'celda_chirps' if scenario == 'B' else 'municipio'
                    self.assertTrue(set(a.loc[list(part.entrenamiento),col]).isdisjoint(a.loc[list(part.validacion),col]))
                self.assertTrue(any(part.elegibles))
            self.assertEqual(set(seen), set(a.index)); self.assertEqual(len(seen), len(a))

    def test_fuga_interna_cambiar_y_validacion_no_cambia_ajuste(self):
        part = particiones_internas(self.a, 'A')[0]
        mod = self.ya.copy(); mod.loc[list(part.validacion)] += 3.
        for kind in ['T','CL','TC','R']:
            m, p = ajustar_particion(self.a, self.ya, part, kind, 'jun_oct', .1)
            m2, p2 = ajustar_particion(self.a, mod, part, kind, 'jun_oct', .1)
            np.testing.assert_array_equal(p, p2)
            if kind != 'T':
                np.testing.assert_array_equal(m.preprocesado_['escala'].mean_, m2.preprocesado_['escala'].mean_)
                np.testing.assert_array_equal(m.coef_estandarizados_, m2.coef_estandarizados_)
            if kind == 'R':
                pd.testing.assert_series_equal(m.residuos_, m2.residuos_)

    def test_control_detecta_antigua_fuga_residuos_externos(self):
        part = particiones_internas(self.a, 'A')[0]
        mod = self.ya.copy(); mod.loc[part.validacion[0]] += 1.
        loo, _ = referencia_loo(self.a, self.ya)
        loo2, _ = referencia_loo(self.a, mod)
        old, altered = (self.ya-loo).loc[list(part.entrenamiento)], (mod-loo2).loc[list(part.entrenamiento)]
        self.assertGreater(np.max(np.abs(old-altered)), 0.)

    def test_seleccion_ocho_config_y_MAE_concatenado_no_residuo(self):
        selected = elegir_configuracion(self.a, self.ya, 'R', 'B')
        self.assertEqual((len(selected.puntuaciones), selected.n_ajustes), (8,32))
        parts = particiones_internas(self.a, 'B')
        errors = []
        for part in parts:
            model, pred = ajustar_particion(self.a, self.ya, part, 'R','abr_oct',.01)
            va = self.a.loc[list(part.validacion)]
            # Comprobación manual del rendimiento completo, no un residuo de validación.
            base, _ = base_independiente(self.a.loc[list(part.entrenamiento)],
                                       self.ya.loc[list(part.entrenamiento)],va)
            z = model.preprocesado_.transform(va[list(model.columnas_)])
            full = base + z @ model.coef_estandarizados_
            errors.extend(np.abs(full-self.ya.loc[va.index].to_numpy())[np.array(part.elegibles)])
        row = selected.puntuaciones.query("ventana == 'abr_oct' and lambda_reg == .01").iloc[0]
        self.assertAlmostEqual(row.MAE, np.mean(errors), places=12)
        self.assertEqual(row.n_elegibles, len(errors))
        self.assertEqual(set(selected.por_ventana), {'abr_oct','jun_oct'})

    def test_desempate_predeclarado_con_clima_constante(self):
        a = self.a.copy(); a[list(CLIMA)] = 1.
        s = elegir_configuracion(a, self.ya, 'CL','A')
        self.assertEqual((s.ventana,s.lambda_reg), ('jun_oct',10.))

    def test_C_puntua_todas_sin_fabricar_soporte_municipal(self):
        a,ya,_,_=contexto_externo(self.e,'C',1,0)
        parts=particiones_internas(a,'C')
        for part in parts:
            tr,va=a.loc[list(part.entrenamiento)],a.loc[list(part.validacion)]
            self.assertFalse(mascara_soporte(tr,va).any())
            self.assertTrue(all(part.elegibles))
        selected=elegir_configuracion(a,ya,'TC','C')
        self.assertTrue(selected.puntuaciones.n_elegibles.eq(len(a)).all())

    def test_CL_y_TC_comparten_mascara_con_R_y_referencia(self):
        part=particiones_internas(self.a,'A')[0]
        tr,va=self.a.loc[list(part.entrenamiento)],self.a.loc[list(part.validacion)]
        expected=MediaTerritorial().fit(tr,self.ya.loc[tr.index]).predict_with_details(va).fuente.eq('municipio')
        np.testing.assert_array_equal(part.elegibles,expected)
        self.assertTrue(np.any(part.elegibles))
        model,p=ajustar_particion(self.a,self.ya,part,'CL','jun_oct',.1)
        self.assertTrue(model.predict_with_details(va).fuente.eq('global').all())
        self.assertEqual(len(p),len(va))

    def test_busqueda_expandida_bloqueada_y_T_sin_busqueda(self):
        cfg = copy.deepcopy(self.e['configuracion']); cfg['regularizacion']['lambda'].append(100.)
        with self.assertRaisesRegex(ValueError, 'versionar'):
            elegir_configuracion(self.a, self.ya, config=cfg)
        with self.assertRaisesRegex(ValueError, 'no tiene búsqueda'):
            elegir_configuracion(self.a, self.ya,'T')

    def test_sin_grupos_o_particion_solapada_bloquea(self):
        a = self.a.copy(); a['celda_chirps'] = 'una'
        with self.assertRaisesRegex(ValueError, 'cuatro grupos'):
            particiones_internas(a,'B')
        part = particiones_internas(self.a,'A')[0]
        bad = replace(part,entrenamiento=(*part.entrenamiento,part.validacion[0]))
        with self.assertRaisesRegex(ValueError, 'disjuntos'):
            ajustar_particion(self.a,self.ya,bad,'R','jun_oct',.1)

    def test_etiqueta_externa_no_entra_en_la_seleccion(self):
        # El pool externo alterado sólo en memoria produce el mismo X/y de entrenamiento.
        e2 = dict(self.e); e2['y'] = self.y.copy(); e2['y'].loc[self.b.index] += 4.
        a2,ya2,b2,_ = contexto_externo(e2,'A')
        pd.testing.assert_frame_equal(a2,self.a);pd.testing.assert_series_equal(ya2,self.ya)
        s1 = elegir_configuracion(self.a,self.ya,'TC','A')
        s2 = elegir_configuracion(a2,ya2,'TC','A')
        pd.testing.assert_frame_equal(s1.puntuaciones,s2.puntuaciones)
        m1 = crear_estimador('TC',s1.ventana,s1.lambda_reg).fit(self.a,self.ya)
        m2 = crear_estimador('TC',s2.ventana,s2.lambda_reg).fit(a2,ya2)
        np.testing.assert_array_equal(m1.predict(self.b),m2.predict(b2))


if __name__ == '__main__':
    unittest.main()
