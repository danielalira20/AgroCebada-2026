"""Controles de integración externos con los datos reales; no evaluación completa."""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

from scripts.t09_entradas import RAIZ, cargar_entradas, contexto_externo
from scripts.t09_estimadores import MediaTerritorial
from scripts.t09_evaluar import (aplicabilidad_reservadas, contextos, evaluar_contexto,
                                preparar_salida, verificar_referencia)


class EvaluacionT09(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.e = cargar_entradas()
        cls.r = evaluar_contexto(cls.e, 'A', 1, 0)

    def test_contextos_externos_conservan_138_y_excluyen_59(self):
        cs = list(contextos(self.e))
        self.assertEqual(len(cs), 59)
        vistas = {}
        for esc, rep, fold in cs:
            tr, _, te, _ = contexto_externo(self.e, esc, rep, fold)
            self.assertFalse(set(tr.index) & set(te.index))
            self.assertEqual(set(tr.index)|set(te.index), set(self.e['X'].index))
            self.assertFalse(set(te.index) & set(self.e['reservadas'].index))
            vistas.setdefault((esc, rep), []).extend(te.index)
            if esc in ('B', 'C'):
                c = 'celda_chirps' if esc == 'B' else 'municipio'
                self.assertFalse(set(tr[c]) & set(te[c]))
        for ids in vistas.values():
            self.assertEqual(len(ids), 138)
            self.assertEqual(set(ids), set(self.e['X'].index))

    def test_ventana_fija_reutiliza_elegida_y_conserva_102_ajustes(self):
        r, o = self.r, self.r['oof']
        self.assertEqual(r['n_ajustes'], 102)
        self.assertEqual(len(r['puntuaciones']), 24)
        self.assertEqual(len(r['selecciones']), 9)
        for proc in ('CL', 'TC', 'R'):
            s = r['selecciones'].query('procedimiento == @proc and variante == "seleccionada"').iloc[0]
            a = o.query('procedimiento == @proc and variante == "seleccionada"').sort_values('id_parcela')
            w = s.ventana
            b = o.query('procedimiento == @proc and variante == @w').sort_values('id_parcela')
            np.testing.assert_array_equal(a.prediccion, b.prediccion)
            self.assertTrue(a.lambda_reg.eq(s.lambda_reg).all())
            self.assertEqual(int(r['puntuaciones'].query('procedimiento == @proc').seleccionada.sum()), 1)
            self.assertEqual(int(r['puntuaciones'].query('procedimiento == @proc').seleccionada_en_ventana.sum()), 2)

    def test_cambiar_etiquetas_externas_no_cambia_modelos_ni_busqueda(self):
        e = deepcopy(self.e)
        ids = self.r['contexto']['evaluacion']
        e['y'].loc[ids] += 10
        cambiado = evaluar_contexto(e, 'A', 1, 0)
        pd.testing.assert_frame_equal(self.r['puntuaciones'], cambiado['puntuaciones'])
        pd.testing.assert_frame_equal(self.r['selecciones'], cambiado['selecciones'])
        pd.testing.assert_frame_equal(self.r['coeficientes'], cambiado['coeficientes'])
        a, b = self.r['oof'], cambiado['oof']
        np.testing.assert_array_equal(a.prediccion, b.prediccion)
        np.testing.assert_allclose(b.real-a.real, 10, rtol=0, atol=1e-14)
        self.assertFalse(a.error.equals(b.error))

    def test_cl_global_no_modifica_poblacion_territorial(self):
        o = self.r['oof']
        t = o.query('procedimiento == "T"').set_index('id_parcela')
        cl = o.query('procedimiento == "CL" and variante == "seleccionada"').set_index('id_parcela')
        self.assertTrue(cl.fuente.eq('global').all())
        np.testing.assert_array_equal(t.sin_respaldo, cl.sin_respaldo)
        np.testing.assert_array_equal(t.fuente, cl.fuente_referencia)

    def test_trazabilidad_interna_no_incluye_ids_externos(self):
        h = self.r['contexto']
        externos = set(h['evaluacion'])
        train = set(h['entrenamiento'])
        vistos = []
        for p in h['internas']:
            a, b = set(p['entrenamiento']), set(p['validacion'])
            self.assertFalse(a & b)
            self.assertFalse((a|b) & externos)
            self.assertEqual(a|b, train)
            self.assertTrue(all(isinstance(x, bool) for x in p['elegibles']))
            vistos.extend(p['validacion'])
        self.assertEqual(len(vistos), len(train))
        self.assertEqual(set(vistos), train)

    def test_aplicabilidad_no_ajusta_modelos_ni_produce_predicciones(self):
        with patch('scripts.t09_evaluar.crear_estimador', side_effect=AssertionError('No ajustar59')):
            a = aplicabilidad_reservadas(self.e)
        self.assertEqual(len(a), 59)
        self.assertEqual(set(a.id_parcela), set(self.e['reservadas'].index))
        self.assertFalse({'real', 'prediccion', 'error'} & set(a.columns))
        self.assertFalse(a.modelo_ajustado.any())
        self.assertTrue(a.fuente_referencia_prevista.eq('municipio').all())
        self.assertTrue(a.n_etiquetas_municipio.gt(0).all())
        self.assertTrue(a.soporte_municipal_escaso.any())

    def test_salida_protege_originales_y_no_sobreescribe(self):
        with tempfile.TemporaryDirectory(dir=RAIZ/'reports') as tmp:
            p = Path(tmp)/'nueva'
            self.assertEqual(preparar_salida(p), p.resolve())
            with self.assertRaises(FileExistsError):
                preparar_salida(p)

    def test_soporte_conjunto_se_comprueba_sin_umbrales_de_confianza(self):
        a = aplicabilidad_reservadas(self.e).set_index('id_parcela')
        for ventana, spec in self.e['configuracion']['ventanas'].items():
            valores = self.e['X'][spec['columnas']].to_numpy(dtype=float)
            sd = valores.std(axis=0, ddof=0)
            sd[sd == 0] = 1
            for pid, r in self.e['reservadas'].iterrows():
                delta = valores-r[spec['columnas']].to_numpy(dtype=float)
                dist = np.sqrt(np.square(delta/sd).sum(axis=1))
                self.assertEqual(a.loc[pid,'perfil_observado_'+ventana], bool(np.equal(delta,0).all(axis=1).any()))
                self.assertAlmostEqual(a.loc[pid,'distancia_clima_estandarizada_min_'+ventana], dist.min(), places=14)
                self.assertEqual(a.loc[pid,'id_perfil_mas_proximo_'+ventana], self.e['X'].index[int(np.argmin(dist))])
        for p in (RAIZ/'registro/t09', RAIZ/'data/raw/no', RAIZ/'reports', Path('/tmp/salida_t09')):
            with self.assertRaises(ValueError):
                preparar_salida(p)

    def test_detector_referencia_rechaza_id_omitido(self):
        with self.assertRaises(ValueError):
            verificar_referencia(self.r['oof'])

    def test_referencia_publicada_restaura_precision_exacta_csv(self):
        filas = []
        for esc, rep, fold in contextos(self.e):
            if esc == 'C':
                continue
            x, y, z, real = contexto_externo(self.e, esc, rep, fold)
            r = MediaTerritorial().fit(x, y).predict_with_details(z).reset_index(drop=True)
            r['ID_POLIGONO'] = r.id_parcela
            r['real'] = real.to_numpy()
            r['escenario'], r['repeticion'], r['particion'], r['procedimiento'] = esc, rep, fold, 'T'
            filas.append(r)
        calculada = pd.concat(filas, ignore_index=True)
        aprobado = verificar_referencia(calculada)
        self.assertEqual(aprobado['diferencia_maxima'], 0)
        self.assertEqual(aprobado['predicciones'], 1380)
        corrupta = calculada.copy()
        corrupta.loc[0, 'prediccion'] += 0.001
        with self.assertRaises(ValueError):
            verificar_referencia(corrupta)


if __name__ == '__main__':
    unittest.main()
