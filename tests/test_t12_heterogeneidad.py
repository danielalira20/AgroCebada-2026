"""Pruebas sintéticas de T12 (paso 2). No usan rendimientos reales ni las 59."""
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd
from sklearn.base import clone

from scripts import evaluacion_comun_centrado_loo as v3
from scripts import evaluacion_comun_modelo as base
from scripts import t12_heterogeneidad as t12

COLS = ('x1', 'x2')


def tabla(n_por_municipio, pendientes, semilla=0, ruido=0.05, prefijo='P'):
    """Parcelas inventadas: rendimiento = nivel del municipio + pendiente·x1 + ruido."""
    rng = np.random.default_rng(semilla)
    filas, y, k = [], [], 0
    niveles = {m: 3.0 + 0.5 * i for i, m in enumerate(n_por_municipio)}
    for m, n in n_por_municipio.items():
        for _ in range(n):
            x1, x2 = rng.normal(), rng.normal()
            filas.append(dict(id=f'{prefijo}{k:04d}', municipio=m, cultivo_origen='Cebada', x1=x1, x2=x2))
            y.append(niveles[m] + pendientes.get(m, 0.0) * x1 + ruido * rng.normal())
            k += 1
    X = pd.DataFrame(filas).set_index('id')
    return X, pd.Series(y, index=X.index, name='rendimiento_t_ha')


class Prueba1PendientesOpuestas(unittest.TestCase):
    """Dos municipios con pendientes opuestas: het las recupera y la pendiente común no."""

    @classmethod
    def setUpClass(cls):
        tam = {'Norte': 60, 'Sur': 60}
        pend = {'Norte': 0.5, 'Sur': -0.5}
        cls.X, cls.y = tabla(tam, pend, semilla=1)
        cls.Xn, cls.yn = tabla(tam, pend, semilla=2, prefijo='N')
        cls.het = t12.CorreccionPendienteMunicipal(COLS, 0.01, 1.0).fit(cls.X, cls.y)
        cls.comun = v3.CorreccionComunCentradaLOO(COLS, 0.01).fit(cls.X, cls.y)

    def test_signo_por_municipio(self):
        p = self.het.pendientes()
        # x1 está estandarizada (desviación ≈ 1), así que la pendiente ≈ ±0.5.
        self.assertGreater(p.loc['Norte', 'x1'], 0.3)
        self.assertLess(p.loc['Sur', 'x1'], -0.3)
        self.assertLess(abs(p.loc['Norte', 'x2']), 0.1)

    def test_pendiente_comun_se_anula(self):
        self.assertLess(abs(self.comun.ridge_.coef_[0]), 0.1)

    def test_het_predice_mejor_parcelas_nuevas(self):
        mae_het = np.mean(np.abs(self.het.predict(self.Xn) - self.yn))
        mae_comun = np.mean(np.abs(self.comun.predict(self.Xn) - self.yn))
        self.assertLess(mae_het, 0.6 * mae_comun)

    def test_detalle_marca_pendiente_propia(self):
        d = self.het.predict_with_details(self.Xn)
        self.assertTrue(d.pendiente_propia.all())
        np.testing.assert_allclose(d.prediccion, d.referencia + d.correccion, atol=1e-12)


class Prueba2ReduceAV3(unittest.TestCase):
    """Sin municipios con pendiente propia es v3 exacto; con κ enorme, v3 dentro de 1e-8."""

    @classmethod
    def setUpClass(cls):
        cls.X, cls.y = tabla({'Norte': 40, 'Sur': 30, 'Este': 20}, {'Norte': 0.4, 'Sur': -0.2}, semilla=3)
        cls.Xn, _ = tabla({'Norte': 10, 'Sur': 10, 'Este': 10}, {}, semilla=4, prefijo='N')
        cls.base = v3.CorreccionComunCentradaLOO(COLS, 0.1).fit(cls.X, cls.y)

    def test_sin_grupos_igual_a_v3(self):
        m = t12.CorreccionPendienteMunicipal(COLS, 0.1, 1.0, grupos_pendiente=()).fit(self.X, self.y)
        np.testing.assert_allclose(m.ridge_.coef_, self.base.ridge_.coef_, rtol=0, atol=1e-12)
        np.testing.assert_allclose(m.predict(self.Xn), self.base.predict(self.Xn), rtol=0, atol=1e-12)

    def test_kappa_enorme_igual_a_v3(self):
        with patch.object(t12, 'KAPPA', (1e12,)):
            m = t12.CorreccionPendienteMunicipal(COLS, 0.1, 1e12).fit(self.X, self.y)
            self.assertEqual(m.grupos_pendiente_, ('Este', 'Norte', 'Sur'))
            diff = np.max(np.abs(m.predict(self.Xn) - self.base.predict(self.Xn)))
        self.assertLess(diff, 1e-8)

    def test_kappa_mayor_contrae_mas(self):
        m1 = t12.CorreccionPendienteMunicipal(COLS, 0.1, 1.0).fit(self.X, self.y)
        m10 = t12.CorreccionPendienteMunicipal(COLS, 0.1, 10.0).fit(self.X, self.y)
        norma = lambda m: sum(np.sum(g ** 2) for g in m.gamma_.values())
        self.assertLess(norma(m10), norma(m1))


class Prueba3Umbral(unittest.TestCase):
    """Con menos de 12 filas no hay pendiente propia; una lista heredada se respeta."""

    def test_umbral_doce(self):
        X, y = tabla({'Grande': 30, 'Justo': 12, 'Chico': 11}, {'Grande': 0.3}, semilla=5)
        m = t12.CorreccionPendienteMunicipal(COLS, 0.1, 1.0).fit(X, y)
        self.assertEqual(m.grupos_pendiente_, ('Grande', 'Justo'))
        self.assertNotIn('Chico', m.gamma_)
        d = m.predict_with_details(X)
        self.assertFalse(d.loc[X.municipio == 'Chico', 'pendiente_propia'].any())

    def test_chico_usa_solo_la_comun(self):
        X, y = tabla({'Grande': 30, 'Chico': 11}, {'Grande': 0.3}, semilla=6)
        m = t12.CorreccionPendienteMunicipal(COLS, 0.1, 1.0).fit(X, y)
        p = m.pendientes()
        self.assertEqual(list(p.index), ['comun', 'Grande'])

    def test_lista_heredada(self):
        X, y = tabla({'Grande': 30, 'Mediano': 20}, {}, semilla=7)
        m = t12.CorreccionPendienteMunicipal(COLS, 0.1, 1.0, grupos_pendiente=('Grande',)).fit(X, y)
        self.assertEqual(m.grupos_pendiente_, ('Grande',))
        self.assertTrue(m.estado()['grupos_pendiente_heredados'])

    def test_lista_heredada_con_municipio_ausente(self):
        # Una interna puede no tener filas de un municipio de la lista: su bloque queda en cero.
        X, y = tabla({'Grande': 30}, {}, semilla=8)
        m = t12.CorreccionPendienteMunicipal(COLS, 0.1, 1.0, grupos_pendiente=('Grande', 'Otro')).fit(X, y)
        np.testing.assert_allclose(m.gamma_['Otro'], 0.0, atol=1e-12)

    def test_parametros_invalidos(self):
        X, y = tabla({'Grande': 30}, {}, semilla=9)
        for kwargs in [dict(kappa=5.0), dict(kappa=True), dict(kappa=None),
                       dict(kappa=1.0, grupos_pendiente=('B', 'A')), dict(kappa=1.0, grupos_pendiente=('A', 'A'))]:
            with self.subTest(**{k: str(v) for k, v in kwargs.items()}), self.assertRaises(ValueError):
                t12.CorreccionPendienteMunicipal(COLS, 0.1, **kwargs).fit(X, y)
        with self.assertRaises(ValueError):
            t12.CorreccionPendienteMunicipal((), None, 1.0).fit(X, y)

    def test_cambiar_kappa_exige_reajuste(self):
        X, y = tabla({'Grande': 30}, {}, semilla=10)
        m = t12.CorreccionPendienteMunicipal(COLS, 0.1, 1.0).fit(X, y)
        m.kappa = 10.0
        with self.assertRaisesRegex(ValueError, 'Reajustar'):
            m.predict(X)


class Prueba4SinFiltracion(unittest.TestCase):
    """La predicción de una parcela sólo depende del entrenamiento y de sus propias variables."""

    @classmethod
    def setUpClass(cls):
        cls.X, cls.y = tabla({'Norte': 40, 'Sur': 30}, {'Norte': 0.4}, semilla=11)
        cls.Xn, cls.yn = tabla({'Norte': 15, 'Sur': 15}, {'Norte': 0.4}, semilla=12, prefijo='N')
        cls.m = t12.CorreccionPendienteMunicipal(COLS, 0.1, 1.0).fit(cls.X, cls.y)

    def test_columna_de_rendimiento_en_prueba_no_se_usa(self):
        con = self.Xn.assign(rendimiento_t_ha=999.0)
        np.testing.assert_array_equal(self.m.predict(con), self.m.predict(self.Xn))

    def test_cada_fila_independiente_del_lote(self):
        lote = self.m.predict(self.Xn)
        una = np.array([self.m.predict(self.Xn.iloc[[i]])[0] for i in range(len(self.Xn))])
        np.testing.assert_allclose(lote, una, rtol=0, atol=1e-12)

    def test_etiquetas_ajenas_no_cambian_el_ajuste(self):
        # Reajustar con las mismas filas de entrenamiento: las etiquetas de prueba nunca entran.
        otro = t12.CorreccionPendienteMunicipal(COLS, 0.1, 1.0).fit(self.X, self.y.copy())
        np.testing.assert_array_equal(otro.predict(self.Xn), self.m.predict(self.Xn))

    def test_orden_de_filas_no_importa(self):
        barajado = self.X.sample(frac=1.0, random_state=0)
        otro = t12.CorreccionPendienteMunicipal(COLS, 0.1, 1.0).fit(barajado, self.y.loc[barajado.index])
        np.testing.assert_allclose(otro.predict(self.Xn), self.m.predict(self.Xn), rtol=0, atol=1e-12)

    def test_clon_sklearn(self):
        c = clone(self.m)
        self.assertEqual((c.kappa, c.lambda_reg, c.columnas), (1.0, 0.1, COLS))
        self.assertFalse(hasattr(c, 'ajustado_'))


class Prueba5PropiaFila(unittest.TestCase):
    """La propia fila nunca entra en su referencia ni en su centro."""

    @classmethod
    def setUpClass(cls):
        cls.X, cls.y = tabla({'Norte': 20, 'Sur': 14, 'Solo': 1}, {'Norte': 0.4}, semilla=13)
        cls.m = t12.CorreccionPendienteMunicipal(COLS, 0.1, 1.0).fit(cls.X, cls.y)

    def test_pools_sin_la_fila(self):
        for pid, (_, ids) in self.m.pools_sin_fila_.items():
            self.assertNotIn(pid, ids)

    def test_residuo_con_media_de_las_demas(self):
        X = self.X.sort_index()
        for i, pid in enumerate(X.index):
            m = X.loc[pid, 'municipio']
            otros = [j for j in X.index if j != pid and X.loc[j, 'municipio'] == m]
            if not otros:  # municipio de una sola fila: respaldo de grupo
                otros = [j for j in X.index if j != pid]
            esperado = self.y[pid] - self.y[otros].mean()
            self.assertAlmostEqual(self.m.residuos_[i], esperado, places=12)

    def test_cambiar_su_etiqueta_no_mueve_su_centro(self):
        y2 = self.y.copy()
        pid = self.X.index[0]
        y2[pid] += 5.0
        m2 = t12.CorreccionPendienteMunicipal(COLS, 0.1, 1.0).fit(self.X, y2)
        np.testing.assert_array_equal(m2.centros_sin_fila_.loc[pid], self.m.centros_sin_fila_.loc[pid])


class Prueba6Desempate(unittest.TestCase):
    """Con el mismo MAE gana la referencia sola; luego λ mayor, κ mayor y jun_oct."""

    def fila(self, nombre, mae, lam=None, kappa=None, ventana='estatica'):
        return dict(nombre=nombre, MAE=mae, referencia_sola=lam is None, lambda_reg=lam, kappa=kappa, ventana=ventana)

    def test_referencia_sola_gana_empate(self):
        filas = [self.fila('abr_oct_l0.01_k1', 0.3000001, 0.01, 1.0, 'abr_oct'),
                 self.fila('referencia_sola', 0.3000004)]
        self.assertEqual(min(filas, key=t12.clave_opcion_het)['nombre'], 'referencia_sola')

    def test_orden_completo(self):
        filas = [self.fila('a', 0.3, 0.1, 10.0, 'jun_oct'),
                 self.fila('b', 0.3, 1.0, 1.0, 'abr_oct'),
                 self.fila('c', 0.3, 1.0, 10.0, 'abr_oct'),
                 self.fila('d', 0.3, 1.0, 10.0, 'jun_oct')]
        self.assertEqual([f['nombre'] for f in sorted(filas, key=t12.clave_opcion_het)], ['d', 'c', 'b', 'a'])

    def test_mae_menor_gana_aunque_sea_mas_complejo(self):
        filas = [self.fila('referencia_sola', 0.31), self.fila('x', 0.30, 0.01, 1.0, 'abr_oct')]
        self.assertEqual(min(filas, key=t12.clave_opcion_het)['nombre'], 'x')


class Diseno(unittest.TestCase):
    def test_huella_y_constantes(self):
        cfg = t12.cargar_diseno()
        self.assertEqual(cfg['regla_promocion']['candidato'], 't12_het_GP')


class Prueba7BoostingInitCero(unittest.TestCase):
    """init='zero' y sin variables: el boosting no puede añadir nada que no venga de las variables."""

    @classmethod
    def setUpClass(cls):
        cls.X, cls.y = tabla({'Norte': 45, 'Sur': 35, 'Este': 10}, {'Norte': 0.4}, semilla=21)
        cls.Xn, cls.yn = tabla({'Norte': 15, 'Sur': 15, 'Este': 5}, {'Norte': 0.4}, semilla=22, prefijo='N')

    def test_sin_variables_es_exactamente_la_referencia(self):
        m = t12.CorreccionBoostingL1((), None).fit(self.X, self.y)
        pred = m.predict(self.Xn)
        ref, _ = base.aplicar_referencia(self.Xn, m.mun_, m.grupo_, m.global_)
        np.testing.assert_array_equal(pred, ref)
        solo = v3.CorreccionComunCentradaLOO((), None).fit(self.X, self.y)
        np.testing.assert_array_equal(pred, solo.predict(self.Xn))
        self.assertIsNone(m.gb_)
        self.assertTrue((m.predict_with_details(self.Xn).correccion == 0).all())
        with self.assertRaises(ValueError):
            m.importancias()

    def test_init_zero_en_el_modelo_ajustado(self):
        m = t12.CorreccionBoostingL1(COLS, 50).fit(self.X, self.y)
        self.assertEqual(m.gb_.init, 'zero')
        self.assertEqual(m.gb_.loss, 'absolute_error')
        self.assertEqual((m.gb_.max_depth, m.gb_.min_samples_leaf, m.gb_.learning_rate, m.gb_.subsample),
                         (2, 10, 0.05, 0.8))
        self.assertEqual(m.estado()['intercepto'], 0.0)
        self.assertIsNone(m.ridge_)

    def test_sin_senal_no_hay_correccion(self):
        # Si todos rinden lo mismo, todos los residuos son 0: la corrección tiene que ser 0.
        y = pd.Series(3.7, index=self.X.index)
        m = t12.CorreccionBoostingL1(COLS, 150).fit(self.X, y)
        d = m.predict_with_details(self.Xn)
        self.assertLess(np.max(np.abs(d.correccion)), 1e-12)
        np.testing.assert_allclose(d.prediccion, 3.7, atol=1e-12)

    def test_captura_una_interaccion_que_la_lineal_no_ve(self):
        rng = np.random.default_rng(23)

        def armar(n, prefijo):
            x1, x2 = rng.normal(size=n), rng.normal(size=n)
            X = pd.DataFrame(dict(municipio='Norte', cultivo_origen='Cebada', x1=x1, x2=x2),
                             index=[f'{prefijo}{i:04d}' for i in range(n)])
            return X, pd.Series(3.0 + 1.0 * ((x1 > 0) & (x2 > 0)) + 0.05 * rng.normal(size=n), index=X.index)
        X, y = armar(160, 'T')
        Xn, yn = armar(160, 'V')
        gb = t12.CorreccionBoostingL1(COLS, 150).fit(X, y)
        lin = v3.CorreccionComunCentradaLOO(COLS, 0.1).fit(X, y)
        mae = lambda m: np.mean(np.abs(m.predict(Xn) - yn))
        self.assertLess(mae(gb), 0.8 * mae(lin))

    def test_indicadores_de_municipio_separan_reglas(self):
        X, y = tabla({'Norte': 60, 'Sur': 60}, {'Norte': 0.6, 'Sur': -0.6}, semilla=24)
        Xn, yn = tabla({'Norte': 40, 'Sur': 40}, {'Norte': 0.6, 'Sur': -0.6}, semilla=25, prefijo='N')
        gb = t12.CorreccionBoostingL1(COLS, 150).fit(X, y)
        lin = v3.CorreccionComunCentradaLOO(COLS, 0.1).fit(X, y)
        mae = lambda m: np.mean(np.abs(m.predict(Xn) - yn))
        self.assertLess(mae(gb), 0.8 * mae(lin))
        self.assertIn('municipio=Norte', gb.importancias().index)

    def test_parametros_invalidos(self):
        for kwargs in [dict(columnas=COLS, n_estimators=100), dict(columnas=COLS, n_estimators=True),
                       dict(columnas=COLS, n_estimators=None), dict(columnas=(), n_estimators=50),
                       dict(columnas=COLS, n_estimators=50, grupos_pendiente=('B', 'A'))]:
            with self.subTest(**{k: str(v) for k, v in kwargs.items()}), self.assertRaises(ValueError):
                t12.CorreccionBoostingL1(**kwargs).fit(self.X, self.y)

    def test_lista_heredada_y_umbral(self):
        X, y = tabla({'Grande': 30, 'Justo': 12, 'Chico': 11}, {}, semilla=26)
        m = t12.CorreccionBoostingL1(COLS, 50).fit(X, y)
        self.assertEqual(m.grupos_pendiente_, ('Grande', 'Justo'))
        h = t12.CorreccionBoostingL1(COLS, 50, grupos_pendiente=('Grande',)).fit(X, y)
        self.assertEqual(h.grupos_pendiente_, ('Grande',))
        self.assertTrue(h.estado()['grupos_pendiente_heredados'])

    def test_cambiar_arboles_exige_reajuste_y_clon(self):
        m = t12.CorreccionBoostingL1(COLS, 50).fit(self.X, self.y)
        c = clone(m)
        self.assertEqual((c.n_estimators, c.columnas), (50, COLS))
        self.assertFalse(hasattr(c, 'ajustado_'))
        m.n_estimators = 150
        with self.assertRaisesRegex(ValueError, 'Reajustar'):
            m.predict(self.Xn)

    def test_sin_filtracion_de_etiquetas_de_prueba(self):
        m = t12.CorreccionBoostingL1(COLS, 50).fit(self.X, self.y)
        con = self.Xn.assign(rendimiento_t_ha=999.0)
        np.testing.assert_array_equal(m.predict(con), m.predict(self.Xn))
        una = np.array([m.predict(self.Xn.iloc[[i]])[0] for i in range(len(self.Xn))])
        np.testing.assert_allclose(m.predict(self.Xn), una, rtol=0, atol=1e-12)

    def test_entradas_del_ajuste_usan_el_centro_sin_la_fila(self):
        # Se rehace a mano la matriz de v3 (z menos el centro sin la propia fila, más indicadores)
        # y se comprueba que el boosting aprendió exactamente de ella y no de otra.
        from sklearn.ensemble import GradientBoostingRegressor
        m = t12.CorreccionBoostingL1(COLS, 50).fit(self.X, self.y)
        Xs = self.X.sort_index()
        z = m.escalador_.transform(m._valores(Xs))
        d = z - m.centros_sin_fila_.loc[Xs.index].to_numpy()
        ind = np.column_stack([(Xs.municipio.to_numpy() == g).astype(float) for g in m.grupos_pendiente_])
        a_mano = GradientBoostingRegressor(n_estimators=50, **t12.PARAMETROS_GB).fit(np.hstack([d, ind]), m.residuos_)
        np.testing.assert_array_equal(m.gb_.predict(np.hstack([d, ind])), a_mano.predict(np.hstack([d, ind])))
        # y ese centro no es el municipal completo (que sí incluye la fila).
        completo = z - m.centros_mun_.loc[Xs.municipio].to_numpy()
        self.assertGreater(np.max(np.abs(d - completo)), 1e-3)

    def test_desempate_gb(self):
        def fila(nombre, mae, arboles=None, ventana='estatica'):
            return dict(nombre=nombre, MAE=mae, referencia_sola=arboles is None, n_estimators=arboles, ventana=ventana)
        filas = [fila('x', 0.3, 150, 'jun_oct'), fila('y', 0.3, 50, 'abr_oct'), fila('z', 0.3, 50, 'jun_oct'),
                 fila('referencia_sola', 0.3)]
        self.assertEqual([f['nombre'] for f in sorted(filas, key=t12.clave_opcion_gb)],
                         ['referencia_sola', 'z', 'y', 'x'])
        filas = [fila('referencia_sola', 0.31), fila('y', 0.30, 50, 'abr_oct')]
        self.assertEqual(min(filas, key=t12.clave_opcion_gb)['nombre'], 'y')


def _entradas_reales_sin_rendimiento():
    """X real de las 138 y de las 59. El rendimiento sólo sirve para saber cuáles no tienen etiqueta."""
    d = pd.read_csv(t12.RAIZ / 'registro/t07/tabla_comun.csv').set_index('id_parcela')
    sin_etiqueta = d.rendimiento_t_ha.isna().to_numpy()
    d = d.drop(columns=['rendimiento_t_ha'])
    g = ['elevacion_media_m', base.NULLABLE, 'area_ha_origen']

    def p(v):
        return [f'pl_ndvi_max_{v}', f'pl_ndvi_integral_{v}', f'pl_lai2_max_{v}',
                f'pl_ndvi_dias_sobre_mitad_{v}', f'pl_ndvi_dia_inicio_{v}', 'pl_ndvi_al_corte']
    columnas = {'abr_oct': g + p('abr_oct'), 'jun_oct': g + p('jun_oct')}
    for c in set(columnas['abr_oct']) | set(columnas['jun_oct']):
        d[c] = pd.to_numeric(d[c], errors='raise')
    return d[~sin_etiqueta].copy(), d[sin_etiqueta].copy(), columnas


class Prueba8ReproduciblesYFinitas(unittest.TestCase):
    """Misma semilla, mismo resultado; y predicciones finitas para las 59.

    Las etiquetas del entrenamiento aquí son INVENTADAS (una función de las propias variables más
    ruido con semilla fija). Sólo se comprueba que el código corre y que nada sale infinito o NaN.
    """

    @classmethod
    def setUpClass(cls):
        cls.X138, cls.X59, cls.columnas = _entradas_reales_sin_rendimiento()
        rng = np.random.default_rng(31)
        z = (cls.X138.elevacion_media_m - cls.X138.elevacion_media_m.mean()) / cls.X138.elevacion_media_m.std()
        cls.y_falsa = pd.Series(3.5 + 0.3 * z + 0.2 * rng.normal(size=len(cls.X138)), index=cls.X138.index)

    def test_poblaciones(self):
        self.assertEqual((len(self.X138), len(self.X59)), (138, 59))
        self.assertFalse(self.X138.index.intersection(self.X59.index).size)

    def test_dos_corridas_dan_lo_mismo(self):
        for fabrica in (lambda c: t12.CorreccionBoostingL1(c, 150),
                        lambda c: t12.CorreccionPendienteMunicipal(c, 0.1, 10.0)):
            cols = self.columnas['abr_oct']
            a = fabrica(cols).fit(self.X138, self.y_falsa)
            b = fabrica(cols).fit(self.X138, self.y_falsa)
            np.testing.assert_array_equal(a.predict(self.X59), b.predict(self.X59))
            barajado = self.X138.sample(frac=1.0, random_state=1)
            c = fabrica(cols).fit(barajado, self.y_falsa.loc[barajado.index])
            np.testing.assert_allclose(a.predict(self.X59), c.predict(self.X59), rtol=0, atol=1e-10)

    def test_las_59_finitas_en_todas_las_opciones(self):
        for ventana, cols in self.columnas.items():
            for bloque, c in [('GP', cols), ('G', cols[:3]), ('P', cols[3:])]:
                modelos = [t12.CorreccionBoostingL1(c, n) for n in t12.N_ARBOLES] + \
                          [t12.CorreccionPendienteMunicipal(c, lam, k) for lam in base.LAMBDA for k in t12.KAPPA]
                for m in modelos:
                    with self.subTest(ventana=ventana, bloque=bloque, modelo=type(m).__name__):
                        d = m.fit(self.X138, self.y_falsa).predict_with_details(self.X59)
                        self.assertEqual(len(d), 59)
                        self.assertTrue(np.isfinite(d.prediccion).all())
                        self.assertTrue(np.isfinite(d.correccion).all())
                        self.assertEqual(list(d.index), list(self.X59.index))

    def test_valores_extremos_siguen_finitos(self):
        cols = self.columnas['abr_oct']
        extremo = self.X59.copy()
        extremo[cols[0]] = extremo[cols[0]] * 100
        extremo.iloc[0, extremo.columns.get_loc(base.NULLABLE)] = np.nan
        for m in (t12.CorreccionBoostingL1(cols, 150), t12.CorreccionPendienteMunicipal(cols, 0.01, 1.0)):
            d = m.fit(self.X138, self.y_falsa).predict_with_details(extremo)
            self.assertTrue(np.isfinite(d.prediccion).all(), type(m).__name__)


# ------------------------------------------------------------------ parte 3: selector
def tabla_celdas(n_por_municipio, pendientes, semilla, prefijo='S', n_celdas=6):
    X, y = tabla(n_por_municipio, pendientes, semilla=semilla, prefijo=prefijo)
    X['celda_chirps'] = [f'c{i % n_celdas}' for i in range(len(X))]
    return X, y


def opciones_sinteticas(familia):
    if familia == 'het':
        return [dict(nombre=f'{v}_l{l:g}_k{k:g}', columnas=list(COLS), ventana=v, lambda_reg=l, kappa=k)
                for v in ('abr_oct', 'jun_oct') for l in base.LAMBDA for k in t12.KAPPA]
    if familia == 'gb':
        return [dict(nombre=f'{v}_n{n}', columnas=list(COLS), ventana=v, n_estimators=n)
                for v in ('abr_oct', 'jun_oct') for n in t12.N_ARBOLES]
    return [dict(nombre=f'abr_oct_l{l:g}', columnas=list(COLS), ventana='abr_oct', lambda_reg=l) for l in base.LAMBDA]


class Prueba9Selector(unittest.TestCase):
    """Selección interna: internas de T03/D026, lista heredada, empates y sin filtración."""

    @classmethod
    def setUpClass(cls):
        cls.X, cls.y = tabla_celdas({'Norte': 50, 'Sur': 40, 'Medio': 13, 'Uno': 1, 'Dos': 1, 'Tres': 3},
                                    {'Norte': 0.6, 'Sur': -0.6}, semilla=41)

    def test_comun_v3_reproduce_el_selector_de_dani(self):
        ops = opciones_sinteticas('comun_v3')
        for esc in ('A', 'B'):
            nuestro = t12.seleccionar_familia(self.X, self.y, ops, esc, 'comun_v3')
            dani = v3.seleccionar(self.X, self.y, ops, esc)
            with self.subTest(escenario=esc):
                self.assertEqual(nuestro['elegida']['nombre'], dani['elegida']['nombre'])
                np.testing.assert_allclose([r['MAE'] for r in nuestro['puntuaciones']],
                                           [r['MAE'] for r in dani['puntuaciones']], rtol=0, atol=1e-12)

    def test_internas_heredan_la_lista_externa(self):
        vistos = []
        original = t12.CorreccionPendienteMunicipal.fit

        def espia(modelo, X, y):
            vistos.append((modelo.grupos_pendiente, X.municipio.value_counts().get('Medio', 0)))
            return original(modelo, X, y)
        with patch.object(t12.CorreccionPendienteMunicipal, 'fit', espia):
            sel = t12.seleccionar_familia(self.X, self.y, opciones_sinteticas('het'), 'A', 'het')
        self.assertEqual(sel['grupos_pendiente'], ('Medio', 'Norte', 'Sur'))
        self.assertEqual(len(vistos), 17 * 4)
        self.assertTrue(all(g == ('Medio', 'Norte', 'Sur') for g, _ in vistos))
        # En las internas Medio tiene menos de 12 filas: si se recalculara, perdería su pendiente.
        self.assertTrue(all(n < t12.N_MIN_PENDIENTE for _, n in vistos))

    def test_elige_correccion_cuando_hay_senal(self):
        sel = t12.seleccionar_familia(self.X, self.y, opciones_sinteticas('het'), 'A', 'het')
        self.assertFalse(sel['elegida']['nombre'] == 'referencia_sola')
        self.assertEqual(sel['n_ajustes'], 17 * 4)
        ref = next(r for r in sel['puntuaciones'] if r['referencia_sola'])
        mejor = min(r['MAE'] for r in sel['puntuaciones'])
        self.assertLess(mejor, ref['MAE'])

    def test_referencia_sola_gana_si_todo_empata(self):
        y = pd.Series(4.0, index=self.X.index)
        for familia in ('het', 'gb', 'comun_v3'):
            with self.subTest(familia=familia):
                sel = t12.seleccionar_familia(self.X, y, opciones_sinteticas(familia), 'A', familia)
                self.assertEqual(sel['elegida']['nombre'], 'referencia_sola')

    def test_escenario_B_agrupa_por_celda(self):
        sel = t12.seleccionar_familia(self.X, self.y, opciones_sinteticas('gb'), 'B', 'gb')
        self.assertEqual(sel['internas'], 'celda')
        pocas = self.X.assign(celda_chirps=['c0', 'c1', 'c2'] * (len(self.X) // 3) + ['c0'] * (len(self.X) % 3))
        with self.assertRaises(ValueError):
            t12.seleccionar_familia(pocas, self.y, opciones_sinteticas('gb'), 'B', 'gb')

    def test_mae_interno_excluye_respaldos(self):
        sel = t12.seleccionar_familia(self.X, self.y, opciones_sinteticas('comun_v3'), 'A', 'comun_v3')
        # 'Uno' y 'Dos' nunca tienen otra fila de su municipio en el ajuste interno.
        self.assertGreaterEqual(sel['n_excluidas_respaldo'], 2)
        self.assertEqual(len({(r['n_elegibles'], r['n_validacion']) for r in sel['puntuaciones']}), 1)

    def test_opciones_invalidas(self):
        het = opciones_sinteticas('het')
        malas = [het + [dict(het[0], nombre='extra')],  # 17 opciones
                 [het[0], dict(het[1], nombre=het[0]['nombre'])],
                 [dict(het[0], nombre='referencia_sola')],
                 [dict(het[0], n_estimators=50)]]
        for ops in malas:
            with self.assertRaises(ValueError):
                t12.seleccionar_familia(self.X, self.y, ops, 'A', 'het')
        with self.assertRaises(ValueError):
            t12.seleccionar_familia(self.X, self.y, opciones_sinteticas('gb'), 'A', 'gb', referencia='mediana')

    def test_evaluacion_externa_nunca_entra(self):
        Xe, _ = tabla_celdas({'Norte': 10, 'Sur': 10}, {}, semilla=42, prefijo='E')
        proc = dict(candidato='prueba', familia='het', referencia='media_mun__resp_grupo',
                    opciones=opciones_sinteticas('het'), n_opciones_con_variables=16)
        vistos = set()
        original = t12.CorreccionPendienteMunicipal.fit

        def espia(modelo, X, y):
            vistos.update(X.index)
            return original(modelo, X, y)
        with patch.object(t12.CorreccionPendienteMunicipal, 'fit', espia):
            r = t12.ajustar_y_predecir(self.X, self.y, Xe, proc, 'A')
        self.assertFalse(vistos & set(Xe.index))
        con = t12.ajustar_y_predecir(self.X, self.y, Xe.assign(rendimiento_t_ha=999.0), proc, 'A')
        np.testing.assert_array_equal(r['detalle'].prediccion, con['detalle'].prediccion)
        with self.assertRaises(ValueError):
            t12.ajustar_y_predecir(self.X, self.y, self.X.iloc[:3], proc, 'A')

    def test_modelo_final_conserva_la_lista_y_la_opcion(self):
        Xe, _ = tabla_celdas({'Norte': 10, 'Sur': 10}, {}, semilla=43, prefijo='E')
        for familia in ('het', 'gb'):
            ops = opciones_sinteticas(familia)
            proc = dict(candidato='prueba', familia=familia, referencia='media_mun__resp_grupo',
                        opciones=ops, n_opciones_con_variables=len(ops))
            r = t12.ajustar_y_predecir(self.X, self.y, Xe, proc, 'A')
            with self.subTest(familia=familia):
                self.assertNotEqual(r['seleccion']['elegida']['nombre'], 'referencia_sola')
                self.assertEqual(r['modelo'].grupos_pendiente_, r['seleccion']['grupos_pendiente'])
                self.assertEqual(r['modelo'].grupos_pendiente_, ('Medio', 'Norte', 'Sur'))
                self.assertEqual(r['modelo'].columnas, tuple(r['seleccion']['elegida']['columnas']))

    def test_desempate_kappa_dentro_del_selector(self):
        # Sin municipios con ≥ 12 filas, κ no cambia nada: k1 y k10 empatan exacto y debe ganar κ = 10.
        X, y = tabla_celdas({'A1': 11, 'A2': 11, 'A3': 11, 'A4': 11}, {m: 0.6 for m in ('A1', 'A2', 'A3', 'A4')},
                            semilla=44)
        sel = t12.seleccionar_familia(X, y, opciones_sinteticas('het'), 'A', 'het')
        self.assertEqual(sel['grupos_pendiente'], ())
        self.assertNotEqual(sel['elegida']['nombre'], 'referencia_sola')
        self.assertEqual(sel['elegida']['kappa'], 10.0)
        pares = {}
        for r in sel['puntuaciones']:
            if not r['referencia_sola']:
                pares.setdefault((r['ventana'], r['lambda_reg']), set()).add(round(r['MAE'], 12))
        self.assertTrue(all(len(v) == 1 for v in pares.values()))


class Prueba10ReferenciaMediana(unittest.TestCase):
    """Control E_T12_008: sólo cambia la referencia (y el residuo) a la mediana."""

    @classmethod
    def setUpClass(cls):
        cls.X, cls.y = tabla({'Norte': 21, 'Sur': 14, 'Uno': 1}, {'Norte': 0.4}, semilla=51)
        cls.y.iloc[0] += 3.0  # un valor extremo para que media y mediana difieran

    def test_referencia_sola_mediana(self):
        m = t12.CorreccionPendienteMunicipal((), None, None, referencia='mediana').fit(self.X, self.y)
        Xn = self.X.iloc[:5]
        esperado = [float(np.median(self.y[self.X.municipio == mu])) for mu in Xn.municipio]
        np.testing.assert_allclose(m.predict(Xn), esperado, rtol=0, atol=1e-12)
        self.assertNotAlmostEqual(m.mun_['Norte'], float(self.y[self.X.municipio == 'Norte'].mean()))

    def test_residuo_con_mediana_de_las_demas(self):
        m = t12.CorreccionPendienteMunicipal(COLS, 0.1, 1.0, referencia='mediana').fit(self.X, self.y)
        X = self.X.sort_index()
        for i, pid in enumerate(X.index):
            otros = [j for j in X.index if j != pid and X.loc[j, 'municipio'] == X.loc[pid, 'municipio']]
            if not otros:
                otros = [j for j in X.index if j != pid]
            self.assertAlmostEqual(m.residuos_[i], self.y[pid] - float(np.median(self.y[otros])), places=12)

    def test_selector_propaga_la_mediana(self):
        X, y = tabla_celdas({'Norte': 30, 'Sur': 20, 'Este': 8}, {'Norte': 0.5}, semilla=52)
        y.iloc[0] += 3.0
        refs = []
        original = t12.CorreccionPendienteMunicipal.fit

        def espia(modelo, X, y):
            refs.append(modelo.referencia)
            return original(modelo, X, y)
        proc = dict(candidato='t12_control_mediana_het_GP', familia='het', referencia='mediana_mun__resp_grupo',
                    opciones=opciones_sinteticas('het'), n_opciones_con_variables=16)
        Xe, _ = tabla_celdas({'Norte': 5, 'Sur': 5}, {}, semilla=53, prefijo='E')
        with patch.object(t12.CorreccionPendienteMunicipal, 'fit', espia):
            r = t12.ajustar_y_predecir(X, y, Xe, proc, 'A')
        self.assertEqual(set(refs), {'mediana'})
        self.assertEqual(len(refs), 17 * 4 + 1)
        self.assertEqual(r['modelo'].mun_['Norte'], float(np.median(y[X.municipio == 'Norte'])))

    def test_media_por_defecto_igual_que_antes(self):
        a = t12.CorreccionPendienteMunicipal(COLS, 0.1, 1.0).fit(self.X, self.y)
        b = t12.CorreccionPendienteMunicipal(COLS, 0.1, 1.0, referencia='media').fit(self.X, self.y)
        np.testing.assert_array_equal(a.predict(self.X), b.predict(self.X))
        c = t12.CorreccionPendienteMunicipal(COLS, 0.1, 1.0, referencia='mediana').fit(self.X, self.y)
        self.assertGreater(np.max(np.abs(a.predict(self.X) - c.predict(self.X))), 1e-3)
        with self.assertRaises(ValueError):
            t12.CorreccionPendienteMunicipal(COLS, 0.1, 1.0, referencia='moda').fit(self.X, self.y)


class Prueba11ProcedimientosRegistrados(unittest.TestCase):
    """Los 8 procedimientos del JSON corren con las entradas reales y etiquetas INVENTADAS."""

    @classmethod
    def setUpClass(cls):
        cls.cfg = t12.cargar_diseno()
        cls.X138, cls.X59, _ = _entradas_reales_sin_rendimiento()
        rng = np.random.default_rng(61)
        z = (cls.X138.elevacion_media_m - cls.X138.elevacion_media_m.mean()) / cls.X138.elevacion_media_m.std()
        cls.y_falsa = pd.Series(3.5 + 0.3 * z + 0.2 * rng.normal(size=len(cls.X138)), index=cls.X138.index)

    def test_ocho_procedimientos(self):
        procs = self.cfg['procedimientos']
        self.assertEqual(len(procs), 8)
        self.assertEqual(sum(p['promovible'] for p in procs), 1)
        for p in procs:
            with self.subTest(candidato=p['candidato']):
                r = t12.ajustar_y_predecir(self.X138, self.y_falsa, self.X59, p, 'A')
                self.assertEqual(len(r['detalle']), 59)
                self.assertTrue(np.isfinite(r['detalle'].prediccion).all())
                self.assertEqual(len(r['seleccion']['puntuaciones']), p['n_opciones_con_variables'] + 1)
                if p['familia'] != 'comun_v3':
                    # Depende sólo de cuántas parcelas hay por municipio, no de rendimientos.
                    self.assertEqual(r['seleccion']['grupos_pendiente'], ('Calpulalpan', 'Chignahuapan', 'Singuilucan'))


if __name__ == '__main__':
    unittest.main()
