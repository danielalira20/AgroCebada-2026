"""Pruebas sintéticas de T12 (paso 2). No usan rendimientos reales ni las 59."""
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd
from sklearn.base import clone

from scripts import evaluacion_comun_centrado_loo as v3
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


if __name__ == '__main__':
    unittest.main()
