"""Protecciones de población, categorías, evidencia y cálculos independientes."""
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import ks_2samp, pearsonr

from scripts.t09_diagnostico_atributos import (
    RAIZ, CLIMA, OBJETIVO, cargar, validar_tabla, pearson, relacion,
    clima_objetivo, ventanas, distancia_ecdf, generar,
)


class TestDiagnostico(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d, cls.dic, cls.contrato = cargar(RAIZ)

    def test_ids_duplicados_rechazados(self):
        d = self.d.copy()
        d.loc[1, 'id_parcela'] = d.loc[0, 'id_parcela']
        with self.assertRaisesRegex(ValueError, 'IDs únicos'):
            validar_tabla(d, self.dic)

    def test_etiqueta_reservada_rechazada(self):
        d = self.d.copy()
        d.loc[d.conjunto_origen.eq('PREDICCION'), OBJETIVO] = 5.
        with self.assertRaisesRegex(ValueError, 'Etiquetas'):
            validar_tabla(d, self.dic)

    def test_nan_climatico_no_es_cero(self):
        d = self.d.copy()
        d.loc[0, CLIMA[0]] = np.nan
        with self.assertRaisesRegex(ValueError, 'Clima incompleto'):
            validar_tabla(d, self.dic)

    def test_infinito_rechazado(self):
        d = self.d.copy()
        d.loc[0, CLIMA[0]] = np.inf
        with self.assertRaisesRegex(ValueError, 'no finito'):
            validar_tabla(d, self.dic)

    def test_texto_numerico_rechazado(self):
        d = self.d.copy()
        d[CLIMA[0]] = d[CLIMA[0]].astype(str)
        with self.assertRaisesRegex(ValueError, 'Texto inesperado'):
            validar_tabla(d, self.dic)

    def test_pearson_constante_o_un_solo_dato_no_definido(self):
        self.assertIsNone(pearson([1,1,1], [1,2,3]))
        self.assertIsNone(pearson([1], [2]))
        self.assertIsNone(pearson([np.nan], [2]))

    def test_pearson_vs_scipy(self):
        e = self.d[self.d.conjunto_origen.eq('ENTRENAMIENTO')]
        for c in CLIMA:
            self.assertAlmostEqual(pearson(e[c], e[OBJETIVO]), pearsonr(e[c], e[OBJETIVO]).statistic, places=13)

    def test_d_ks_empates_vs_scipy(self):
        a, b = [1,1,2,3], [1,2,2,5]
        self.assertAlmostEqual(distancia_ecdf(a,b), ks_2samp(a,b).statistic, places=14)

    def test_ks_muestras_vacias_rechazadas(self):
        with self.assertRaisesRegex(ValueError, 'sin observaciones'):
            distancia_ecdf([], [1])

    def test_centrado_comprobado_con_matriz_de_indicadores(self):
        e = self.d[self.d.conjunto_origen.eq('ENTRENAMIENTO')]
        z = pd.get_dummies(e.municipio, dtype=float).to_numpy()
        for c in CLIMA:
            x, y = e[c].to_numpy(), e[OBJETIVO].to_numpy()
            xr = x - z @ np.linalg.lstsq(z, x, rcond=None)[0]
            yr = y - z @ np.linalg.lstsq(z, y, rcond=None)[0]
            r = relacion(e, c, OBJETIVO)
            self.assertAlmostEqual(r['pearson_dentro_municipio'], pearsonr(xr,yr).statistic, places=12)
            self.assertAlmostEqual(r['fraccion_variacion_x_entre_municipios'],
                                   1 - np.dot(xr,xr)/np.sum((x-x.mean())**2), places=12)

    def test_reservadas_no_cambian_correlaciones_supervisadas(self):
        original = clima_objetivo(self.d)
        copia = self.d.copy()
        mask = copia.conjunto_origen.eq('PREDICCION')
        copia.loc[mask, CLIMA] = 999.
        copia.loc[mask, OBJETIVO] = -999.
        pd.testing.assert_frame_equal(original, clima_objetivo(copia))

    def test_ventanas_siete_pares_seis_candidatos_y_una_calidad(self):
        roles = {r['columna']:r['funcion'] for r in self.dic}
        v = ventanas(self.d, roles)
        iguales = v[v.identicas_197]
        self.assertEqual(iguales.rol.value_counts().to_dict(), {'predictor_candidato':6, 'calidad':1})
        self.assertTrue((iguales.n_pares == 197).all())

    def test_no_sobrescribe_fuentes_o_salidas(self):
        with self.assertRaisesRegex(ValueError, 'reports'):
            generar(RAIZ, RAIZ/'registro/t07')
        with tempfile.TemporaryDirectory(dir=RAIZ/'reports') as td:
            with self.assertRaisesRegex(ValueError, 'ya existe'):
                generar(RAIZ, Path(td))


if __name__ == '__main__':
    unittest.main()
