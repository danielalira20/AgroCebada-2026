"""Contratos reales, incidencias revisadas y cálculos aislados; sin datos ficticios de entrega."""
import copy, json, tempfile, unittest
from pathlib import Path
import numpy as np, pandas as pd
from scripts import evaluacion_comun_contrato as c
from scripts import evaluacion_comun_modelo as m
from scripts import evaluacion_comun_reportes as r

class ContratosReales(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.e = c.cargar_entradas()
        cls.base = c.leer_csv(c.RAIZ / 'registro/t03/predicciones_oof_referencias_media_mun__resp_grupo.csv')[1]
        cls.cat = c.leer_csv(c.RAIZ / 'analisis/auditoria_catalogo_y_etiquetas/tablas/catalogo_parcelas.csv')[1]
        cls.q = c.leer_csv(c.RAIZ / 'registro/t07/calidad_relieve.csv')[1]
        cls.sup = c.leer_csv(c.RAIZ / 'registro/t03/soporte_parcelas.csv')[1]

    def check_part(self, p):
        c.validar_particiones(c.PART_COLS, p, self.e['tabla'], self.e['conocidos'], self.sup)

    def test_preflight_no_entrena(self):
        self.assertEqual((len(self.e['conocidos']), len(self.e['reservados']), len(self.e['contextos'])), (138, 59, 1380))

    def test_id_duplicado_entre_folds_rechazado(self):
        p = copy.deepcopy(self.e['particiones'])
        p[0]['ID_POLIGONO'] = p[1]['ID_POLIGONO']
        with self.assertRaisesRegex(ValueError, 'duplicada'):
            self.check_part(p)

    def test_id_reservado_no_entra(self):
        p = copy.deepcopy(self.e['particiones'])
        p[0]['ID_POLIGONO'] = sorted(self.e['reservados'])[0]
        with self.assertRaises(ValueError):
            self.check_part(p)

    def test_repeticion_perdida_rechazada(self):
        with self.assertRaises(ValueError):
            self.check_part(self.e['particiones'][:-1])

    def test_metadatos_particiones_incompatibles(self):
        for col, value in [('celda_chirps', ''), ('celda_chirps', '0_0'), ('municipio', 'inventado'), ('grupo_registro', 'cebada'), ('semilla', '0'), ('particion_principal', '7')]:
            p = copy.deepcopy(self.e['particiones'])
            p[0][col] = value
            with self.subTest(columna=col, valor=value), self.assertRaises(ValueError):
                self.check_part(p)

    def test_fold_celda_no_divisible(self):
        p = copy.deepcopy(self.e['particiones'])
        p[0]['particion_espacial'] = str((int(p[0]['particion_espacial']) + 1) % 5)
        with self.assertRaises(ValueError):
            self.check_part(p)

    def test_tabla_no_usa_nan_cualquier_columna(self):
        for col, value in [('pl_ndvi_max_abr_oct', 'NaN'), ('pendiente_media_t10_grados', '')]:
            t = copy.deepcopy(list(self.e['tabla'].values()))
            t[0][col] = value
            with self.subTest(columna=col), self.assertRaises(ValueError):
                c.validar_tabla(t, self.cat, self.e['roles'], self.q)

    def test_etiqueta_reservada_aunque_coincida_catalogo(self):
        t = copy.deepcopy(list(self.e['tabla'].values()))
        cat = copy.deepcopy(self.cat)
        pid = sorted(self.e['reservados'])[0]
        for rows in [t, cat]:
            next((row for row in rows if row['id_parcela'] == pid))['rendimiento_t_ha'] = '4.0'
        with self.assertRaises(ValueError):
            c.validar_tabla(t, cat, self.e['roles'], self.q)

    def test_oof_referencia_reproduce(self):
        self.assertTrue(c.validar_oof(self.base, self.e['contextos'])['referencia_verificada'])

    def test_oof_alterado_rechazado(self):
        for col, value in [('prediccion', '100'), ('prediccion', 'inf'), ('fuente', 'global'), ('real', '100'), ('version', 'otra'), ('candidato', ''), ('ID_POLIGONO', sorted(self.e['reservados'])[0])]:
            rows = copy.deepcopy(self.base)
            rows[0][col] = value
            with self.subTest(columna=col, valor=value), self.assertRaises(ValueError):
                c.validar_oof(rows, self.e['contextos'])

    def test_oof_falta_fila_o_duplicado(self):
        for rows in [self.base[:-1], [*self.base, self.base[0]]]:
            with self.assertRaises(ValueError):
                c.validar_oof(rows, self.e['contextos'])

    def test_cabecera_duplicada_detiene(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'fila.csv'
            p.write_text('ID,ID\n1,1\n')
            with self.assertRaises(ValueError):
                c.leer_csv(p)

    def test_cada_entrenamiento_A_B_admite_internas_comunes(self):
        tab = pd.DataFrame(self.e['tabla'].values()).set_index('id_parcela')
        for esc, col in [('A', 'particion_principal'), ('B', 'particion_espacial')]:
            for rep in range(1, 6):
                p = [x for x in self.e['particiones'] if int(x['repeticion']) == rep]
                for fold in range(5):
                    tr = [x for x in p if int(x[col]) != fold]
                    x = tab.loc[[v['ID_POLIGONO'] for v in tr], ['municipio', 'cultivo_origen']].copy()
                    x['celda_chirps'] = [v['celda_chirps'] for v in tr]
                    with self.subTest(escenario=esc, rep=rep, fold=fold):
                        self.assertEqual(len(m.divisiones_internas(x, esc)), 4)

    def ejemplo_experimento(self):
        return {'schema': 'experimento_comun_v1', 'id': 'SOLO_TEST', 'responsable': 'test', 'hipotesis': 'prueba aislada sin ejecucion', 'estado': 'registrado_antes_de_ejecutar', 'sha_procedimiento': c.DISENO_SHA, 'procedimientos': [{'candidato': 'prueba', 'opciones': [{'columnas': ['prec_acumulada_mm_' + w], 'ventana': w, 'lambda_reg': l} for w in ['abr_oct', 'jun_oct'] for l in m.LAMBDA]}]}

    def test_presupuesto_valido_ocho_y_referencia(self):
        self.assertEqual(c.validar_experimento(self.ejemplo_experimento(), self.e)['opciones_con_variables'], 8)

    def test_busqueda_nueve_o_solo_alfa_favorable_rechazada(self):
        for n in [1, 9]:
            e = self.ejemplo_experimento()
            op = e['procedimientos'][0]['opciones']
            e['procedimientos'][0]['opciones'] = op[:n] if n == 1 else [*op, copy.deepcopy(op[0])]
            with self.subTest(opciones=n), self.assertRaises(ValueError):
                c.validar_experimento(e, self.e)

    def test_columna_derivada_objetivo_prohibida(self):
        for col in ['rendimiento_t_ha', 'cultivo_origen', 'escalon_etiqueta_municipio', 'id_parcela', 'pl_capturas_abr_oct', 'area_ha_origen']:
            e = self.ejemplo_experimento()
            for o in e['procedimientos'][0]['opciones']:
                o['columnas'] = [col]
            with self.subTest(columna=col), self.assertRaises(ValueError):
                c.validar_experimento(e, self.e)

    def test_ventana_mal_declarada_rechazada(self):
        e = self.ejemplo_experimento()
        e['procedimientos'][0]['opciones'][0]['ventana'] = 'jun_oct'
        with self.assertRaises(ValueError):
            c.validar_experimento(e, self.e)

    def test_calidad_area_requieren_declaracion(self):
        e = self.ejemplo_experimento()
        p = e['procedimientos'][0]
        p['calidad_explicita'] = True
        p['area_explicita'] = True
        p['opciones'] = [{'columnas': ['pl_capturas_abr_oct', 'area_ha_origen'], 'ventana': 'abr_oct', 'lambda_reg': l} for l in m.LAMBDA]
        self.assertEqual(c.validar_experimento(e, self.e)['opciones_con_variables'], 4)

    def test_contexto_no_entrega_etiquetas_externas_ni_59(self):
        tr,y,te=m.preparar_contexto(self.e,'A',1,0)
        self.assertFalse(set(tr.index)&set(te.index))
        self.assertFalse(set(tr.index)&self.e['reservados'])
        self.assertFalse(set(te.index)&self.e['reservados'])
        self.assertTrue(y.index.equals(tr.index))
        self.assertNotIn('rendimiento_t_ha',tr)
        self.assertNotIn('rendimiento_t_ha',te)

    def test_autorizacion_area_no_acepta_texto_false(self):
        exp=self.ejemplo_experimento()
        exp['procedimientos'][0]['area_explicita']='false'
        with self.assertRaisesRegex(ValueError,'booleano'):
            c.validar_experimento(exp,self.e)

class CalculosAislados(unittest.TestCase):

    def fixture(self, n=12):
        ids = [f'prueba_{i:02}' for i in range(n)]
        x = pd.DataFrame({'municipio': ['m'] * n, 'cultivo_origen': ['Cebada'] * n, 'prec_acumulada_mm_abr_oct': np.arange(n, dtype=float), 'pendiente_media_t10_grados': np.arange(n, dtype=float), 'celda_chirps': [f'c{i // 3}' for i in range(n)]}, index=ids)
        y = pd.Series(np.sin(np.arange(n)) + 0.2 * np.arange(n), index=ids)
        return (x, y)

    def test_referencia_loo_no_incluye_propia_etiqueta(self):
        x, y = self.fixture(4)
        np.testing.assert_allclose(m.residuos_loo(x, y), [y.iloc[i] - y.drop(index=y.index[i]).mean() for i in range(4)], rtol=0, atol=1e-15)

    def test_respaldos_grupo_global(self):
        x, y = self.fixture(4)
        f = m.CorreccionComun().fit(x, y)
        q = x.iloc[:2].copy()
        q['municipio'] = 'nuevo'
        q.loc[q.index[1], 'cultivo_origen'] = 'CEBADA'
        p, s = f.predict_con_fuente(q)
        self.assertEqual(s.tolist(), ['grupo', 'global'])
        np.testing.assert_allclose(p, y.mean())

    def test_Ridge_con_matrices_independientes(self):
        x, y = self.fixture()
        cols = ['prec_acumulada_mm_abr_oct']
        model = m.CorreccionComun(cols, 0.1).fit(x, y)
        a = (x[cols].to_numpy() - x[cols].mean().to_numpy()) / x[cols].std(ddof=0).to_numpy()
        res = m.residuos_loo(x, y)
        beta = np.linalg.lstsq(np.vstack([a, np.sqrt(len(x) * 0.1) * np.eye(1)]), np.r_[res, 0.0], rcond=None)[0]
        np.testing.assert_allclose(model.predict(x), y.mean() + a @ beta, rtol=0, atol=1e-14)
        self.assertEqual(model.estado()['intercepto'], 0)

    def test_prediccion_no_aprende_media_de_validacion(self):
        x, y = self.fixture()
        model = m.CorreccionComun(['prec_acumulada_mm_abr_oct'], 1).fit(x.iloc[:8], y.iloc[:8])
        before = json.dumps(model.estado(), sort_keys=True)
        q = x.iloc[8:].copy()
        q['prec_acumulada_mm_abr_oct'] += 10000
        model.predict(q)
        self.assertEqual(json.dumps(model.estado(), sort_keys=True), before)

    def test_imputacion_aprende_solo_entrenamiento(self):
        x, y = self.fixture()
        x.loc[x.index[0], 'pendiente_media_t10_grados'] = np.nan
        f = m.CorreccionComun(['pendiente_media_t10_grados'], 1).fit(x.iloc[:8], y.iloc[:8])
        self.assertEqual(f.mediana_pendiente_, 4.0)
        q = x.iloc[8:].copy()
        q['pendiente_media_t10_grados'] = np.nan
        self.assertTrue(np.isfinite(f.predict(q)).all())
        self.assertEqual(f.mediana_pendiente_, 4.0)

    def test_faltante_total_no_se_inventa_cero(self):
        x, y = self.fixture()
        x['pendiente_media_t10_grados'] = np.nan
        with self.assertRaises(ValueError):
            m.CorreccionComun(['pendiente_media_t10_grados'], 1).fit(x, y)

    def test_etiqueta_no_se_vuelve_atributo(self):
        x, y = self.fixture()
        x['rendimiento_t_ha'] = y
        with self.assertRaises(ValueError):
            m.CorreccionComun(['rendimiento_t_ha'], 1).fit(x, y)

    def test_fit_y_desalineada_rechazada(self):
        x, y = self.fixture()
        with self.assertRaises(ValueError):
            m.CorreccionComun().fit(x, y.iloc[::-1])

    def test_fit_ID_duplicado_rechazado(self):
        x, y = self.fixture()
        x.index = [x.index[0]] * len(x)
        y.index = x.index
        with self.assertRaises(ValueError):
            m.CorreccionComun().fit(x, y)

    def test_area_cero_rechazada(self):
        x, y = self.fixture()
        x['area_ha_origen'] = 0
        with self.assertRaises(ValueError):
            m.CorreccionComun(['area_ha_origen'], 1).fit(x, y)

    def test_filas_reordenadas_no_cambian(self):
        x, y = self.fixture()
        q = x.sample(frac=1, random_state=123)
        a = m.CorreccionComun(['prec_acumulada_mm_abr_oct'], 1).fit(x, y)
        b = m.CorreccionComun(['prec_acumulada_mm_abr_oct'], 1).fit(q, y.loc[q.index])
        np.testing.assert_array_equal(a.predict(x), b.predict(x))

    def test_grupos_B_no_se_comparten(self):
        x, _ = self.fixture()
        for s in m.divisiones_internas(x, 'B'):
            self.assertFalse(set(x.loc[list(s.entrenamiento)].celda_chirps) & set(x.loc[list(s.validacion)].celda_chirps))

    def test_etiqueta_validacion_no_modifica_residuo_o_modelo_interno(self):
        x, y = self.fixture()
        s = m.divisiones_internas(x, 'A')[0]
        tr = x.loc[list(s.entrenamiento)]
        a = m.CorreccionComun(['prec_acumulada_mm_abr_oct'], 1).fit(tr, y.loc[tr.index])
        changed = y.copy()
        changed.loc[s.validacion[0]] += 1000
        b = m.CorreccionComun(['prec_acumulada_mm_abr_oct'], 1).fit(tr, changed.loc[tr.index])
        self.assertEqual(a.estado(), b.estado())

    def test_empatados_se_eligen_simple_y_regularizado(self):
        base = {'MAE': 0.3, 'referencia_sola': True, 'lambda_reg': None, 'ventana': 'estatica', 'nombre': 'ref'}
        corr = {'MAE': 0.3000001, 'referencia_sola': False, 'lambda_reg': 10, 'ventana': 'jun_oct', 'nombre': 'corr'}
        self.assertLess(m.clave_opcion(base), m.clave_opcion(corr))
        a = corr.copy()
        a['lambda_reg'] = 0.1
        self.assertLess(m.clave_opcion(corr), m.clave_opcion(a))

    def test_referencia_interna_gana_si_columnas_constantes(self):
        x, y = self.fixture()
        x['prec_acumulada_mm_abr_oct'] = 0.1
        opts = [{'nombre': f'abr_{l}', 'columnas': ['prec_acumulada_mm_abr_oct'], 'lambda_reg': l, 'ventana': 'abr_oct'} for l in m.LAMBDA]
        z = m.seleccionar(x, y, opts)
        self.assertEqual(z['elegida']['nombre'], 'referencia_sola')
        self.assertEqual(z['n_ajustes'], 20)

    def test_R2_constante_no_muestra_menos_infinito(self):
        a = r.metricas([0.1] * 9, [0.2] * 9)
        self.assertIsNone(a['R2'])
        self.assertEqual(a['R2_estado'], 'objetivo_constante')

    def test_metrica_no_acepta_nan(self):
        with self.assertRaises(ValueError):
            r.metricas([1, 2], [1, float('nan')])

class EstadisticosComunes(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        ContratosReales.setUpClass.__func__(cls)

    def test_delta_por_parcela_elegibilidad_desigual(self):
        base = copy.deepcopy(self.base)
        cand = copy.deepcopy(base)
        for row in cand:
            row['candidato'] = 'PRUEBA_ESTADISTICO_SIN_MODELO'
            row['prediccion'] = str(float(row['real']) + 0.03 * int(row['repeticion']))
        rows = base + cand
        out = r.comparar(rows, self.e['contextos'], 'PRUEBA_ESTADISTICO_SIN_MODELO', escenario='B')
        errors = {}
        byrep = {}
        for a, b in zip(cand, base):
            if a['escenario'] != 'B' or a['fuente'] != 'municipio':
                continue
            d = abs(float(a['prediccion']) - float(a['real'])) - abs(float(b['prediccion']) - float(b['real']))
            errors.setdefault(a['ID_POLIGONO'], []).append(d)
            byrep.setdefault(int(a['repeticion']), []).append(d)
        expected = np.mean([np.mean(v) for v in errors.values()])
        other = np.mean([np.mean(v) for v in byrep.values()])
        self.assertAlmostEqual(out['dMAE'], expected, places=14)
        self.assertNotAlmostEqual(expected, other, places=8)
        self.assertEqual(out['n_predicciones'], 659)
        out2 = r.comparar(rows[::-1], self.e['contextos'], 'PRUEBA_ESTADISTICO_SIN_MODELO', escenario='B')
        self.assertEqual(out, out2)

    def test_misma_prediccion_no_se_promueve(self):
        cand = copy.deepcopy(self.base)
        for row in cand:
            row['candidato'] = 'PRUEBA_IDENTICA'
        out = r.comparar(self.base + cand, self.e['contextos'], 'PRUEBA_IDENTICA')
        self.assertEqual(out['dMAE'], 0)
        self.assertEqual(out['dRMSE'], 0)
        self.assertEqual(out['IC95_celdas_MAE'], [0, 0])
        self.assertFalse(out['cumple_regla_T03'])
        json.dumps(out,allow_nan=False)

    def test_referencia_comun_50_contextos_reproduce_T08(self):
        tab = pd.DataFrame(self.e['tabla'].values()).set_index('id_parcela')
        tab['rendimiento_t_ha'] = pd.to_numeric(tab.rendimiento_t_ha)
        errors = []
        for esc, col in [('A', 'particion_principal'), ('B', 'particion_espacial')]:
            for rep in range(1, 6):
                part = [p for p in self.e['particiones'] if int(p['repeticion']) == rep]
                for fold in range(5):
                    tr = tab.loc[[p['ID_POLIGONO'] for p in part if int(p[col]) != fold]]
                    te = tab.loc[[p['ID_POLIGONO'] for p in part if int(p[col]) == fold]]
                    f = m.CorreccionComun().fit(tr, tr.rendimiento_t_ha)
                    pred, src = f.predict_con_fuente(te)
                    for pid, v, source in zip(te.index, pred, src):
                        expected = self.e['contextos'][esc, rep, pid]
                        errors.append(abs(v - expected['referencia']))
                        self.assertEqual(source, expected['fuente'])
        self.assertEqual(len(errors), 1380)
        self.assertLess(max(errors), 1e-12)

    def test_diseno_cambiado_rechazado_sin_aprender(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / c.DISENO
            path.parent.mkdir(parents=True)
            path.write_text('{}')
            with self.assertRaisesRegex(ValueError, 'Diseño'):
                c.cargar_diseno(root)
if __name__ == '__main__':
    unittest.main()
