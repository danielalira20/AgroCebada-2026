"""Pruebas de la evaluación principal de T12 (paso 4) con datos INVENTADOS.

No leen rendimientos reales: la tabla, las particiones y las referencias se fabrican aquí con la misma
forma que las de T03/T07, para comprobar el tubo completo (contextos, selección, tablas, compuertas)
sin mirar ningún resultado real.
"""
import copy
import json
import multiprocessing
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd

from scripts import evaluacion_comun_centrado_loo as v3
from scripts import evaluacion_comun_contrato as contrato
from scripts import t12_evaluar as ev
from scripts import t12_heterogeneidad as t12

G = ['elevacion_media_m', 'pendiente_media_t10_grados', 'area_ha_origen']
P = [f'pl_{n}_{v}' for v in ('abr_oct', 'jun_oct')
     for n in ('ndvi_max', 'ndvi_integral', 'lai2_max', 'ndvi_dias_sobre_mitad', 'ndvi_dia_inicio')] + ['pl_ndvi_al_corte']
NUMERICAS = G + P
MUNICIPIOS = {'Norte': 30, 'Sur': 20, 'Este': 14, 'Oeste': 12}
N_RESERVADAS = 12


def entradas_sinteticas(semilla=7):
    """76 parcelas etiquetadas y 12 reservadas con la forma de las entradas de T15 (cadenas, como en los CSV)."""
    rng = np.random.default_rng(semilla)
    tabla, part = {}, []
    pend = {'Norte': 0.6, 'Sur': -0.6, 'Este': 0.0, 'Oeste': 0.1}
    k = 0
    ids_conocidos, ids_reservados = [], []
    for m, n in MUNICIPIOS.items():
        for j in range(n + (N_RESERVADAS // 4)):
            pid = f'S{k:04d}'
            reservada = j >= n
            x = {c: float(rng.normal()) for c in NUMERICAS}
            x['area_ha_origen'] = float(np.exp(rng.normal(0.5, 0.4)))
            x['elevacion_media_m'] = 2500 + 100 * x['elevacion_media_m']
            y = 3 + 0.5 * list(MUNICIPIOS).index(m) + pend[m] * x['pl_ndvi_max_abr_oct'] + 0.15 * rng.normal()
            fila = dict(id_parcela=pid, campania='2025', municipio=m, estado='Puebla', cultivo_origen='Cebada',
                        conjunto_origen='parcelas2025', rendimiento_t_ha='' if reservada else repr(round(float(y), 4)),
                        **{c: repr(v) for c, v in x.items()})
            if not reservada and j == 0:
                fila['pendiente_media_t10_grados'] = ''
            tabla[(pid,)] = fila
            (ids_reservados if reservada else ids_conocidos).append((pid, m, j))
            k += 1
    # celdas de 3 parcelas del mismo municipio; folds A estratificados y folds B por celda, 5 repeticiones
    celda = {pid: f'{m}{j // 3}' for pid, m, j in ids_conocidos}
    celdas = sorted(set(celda.values()))
    for rep in range(1, 6):
        r = np.random.default_rng(100 + rep)
        fold_celda = {c: int(f) for c, f in zip(r.permutation(celdas), np.arange(len(celdas)) % 5)}
        for m in MUNICIPIOS:
            propios = [pid for pid, mm, _ in ids_conocidos if mm == m]
            for pid, f in zip(r.permutation(propios), np.arange(len(propios)) % 5):
                part.append(dict(ID_POLIGONO=pid, repeticion=str(rep), semilla=str(20261000 + rep),
                                 particion_principal=str(int(f)), particion_espacial=str(fold_celda[celda[pid]]),
                                 celda_chirps=celda[pid], municipio=m, grupo_registro='Cebada'))
    conocidos = {p for p, _, _ in ids_conocidos}
    reservados = {p for p, _, _ in ids_reservados}
    roles = {'columnas_por_funcion': {'predictor_candidato': ['municipio'] + NUMERICAS, 'calidad': []}}
    return dict(tabla=tabla, particiones=part, conocidos=conocidos, reservados=reservados, roles=roles,
                contextos=contrato.contextos(tabla, part))


def procedimientos_reducidos():
    """Los 8 procedimientos del registro con dos opciones cada uno (primera y última) para que sea rápido."""
    cfg = t12.cargar_diseno()
    for p in cfg['procedimientos']:
        p['opciones'] = [p['opciones'][0], p['opciones'][-1]]
        p['n_opciones_con_variables'] = 2
    return cfg


def reducir(entradas):
    """Repetición 1 completa y la partición 0 de las demás (18 contextos).

    `comparar` busca la celda de cada parcela en la repetición 1, así que esa repetición debe estar entera.
    """
    r = dict(entradas)
    r['contextos'] = {k: v for k, v in entradas['contextos'].items() if k[1] == 1 or v['particion'] == 0}
    return r


CTX_SUB = tuple((e, r, f) for e in ('A', 'B') for r in range(1, 6) for f in range(5) if r == 1 or f == 0)


def filas_referencia(entradas):
    """Lo que T03 guarda para las dos referencias: media y mediana, con su fuente de respaldo."""
    filas = []
    for (esc, rep, pid), c in sorted(entradas['contextos'].items()):
        filas.append(dict(ID_POLIGONO=pid, repeticion=str(rep), particion=str(c['particion']), escenario=esc,
                          real=repr(c['real']), prediccion=repr(c['referencia']), candidato=ev.REFERENCIA,
                          version='T08-v1', fuente=c['fuente']))
    for esc, rep, fold in sorted({(k[0], k[1], c['particion']) for k, c in entradas['contextos'].items()}):
        tr, y, te = v3.preparar_contexto(entradas, esc, rep, fold)
        det = t12._referencia_sola('het', 'mediana').fit(tr, y).predict_with_details(te)
        for pid, pred, fu in zip(te.index, det.prediccion, det.fuente):
            c = entradas['contextos'][(esc, rep, pid)]
            filas.append(dict(ID_POLIGONO=pid, repeticion=str(rep), particion=str(fold), escenario=esc,
                              real=repr(c['real']), prediccion=repr(float(pred)),
                              candidato=ev.REFERENCIA_MEDIANA, version='T08-v1', fuente=str(fu)))
    return filas


_MEMO = {}


def corrida_memorizada(entradas, cfg):
    """evaluar_todos real, una sola vez por sesión de pruebas (50 contextos x 8 procedimientos)."""
    if 'oof' not in _MEMO:
        _MEMO['oof'], _MEMO['sel'] = ev.evaluar_todos(entradas, cfg['procedimientos'], CTX_SUB)
    return _MEMO['oof'], _MEMO['sel']


class Prueba13Evaluacion(unittest.TestCase):
    """El tubo completo con datos inventados: 8 procedimientos x 50 contextos, tablas y manifest."""

    @classmethod
    def setUpClass(cls):
        cls.entradas = reducir(entradas_sinteticas())
        cls.cfg = procedimientos_reducidos()
        cls.refs = filas_referencia(cls.entradas)
        corrida_memorizada(cls.entradas, cls.cfg)
        cls.tmp = Path(tempfile.mkdtemp())
        cls.salida = cls.tmp / 'salida'
        with patch.object(ev, 'compuertas', lambda raiz, c: (cls.cfg, {})), \
                patch.object(ev, 'evaluar_todos', lambda *a, **k: (_MEMO['oof'], _MEMO['sel'])), \
                patch.object(ev, 'preparar_salida', lambda s, r: cls.salida), \
                patch.object(v3, 'cargar_entradas', lambda raiz: cls.entradas), \
                patch.object(ev, 'cargar_referencias', lambda raiz: cls.refs), \
                patch.object(ev, 'N_ETIQUETADAS', 76), patch.object(ev, 'N_RESERVADAS', 12), \
                patch.object(ev, 'CONTEXTOS', CTX_SUB), patch('builtins.print'):
            cls.destino, cls.tablas = ev.ejecutar('x', confirmo_barreras=True)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def leer(self, nombre):
        return pd.read_csv(self.salida / nombre, float_precision='round_trip')

    def test_archivos_y_manifest(self):
        for a in ev.ARCHIVOS:
            self.assertTrue((self.salida / a).exists(), a)
        m = json.loads((self.salida / 'manifest.json').read_text())
        self.assertEqual(m['contextos_externos'], len(CTX_SUB))
        self.assertEqual(len(m['procedimientos']), 8)
        self.assertTrue(m['barreras_confirmadas_por_la_persona'])
        self.assertEqual(m['sha_diseno_t12'], t12.DISENO_SHA)
        for nombre, huella in m['salidas_sha256'].items():
            self.assertEqual(contrato.sha(self.salida / nombre), huella)
        self.assertNotIn('manifest.json', m['salidas_sha256'])

    def test_oof_completa_y_en_formato_t03(self):
        oof = self.leer('predicciones_oof_t12.csv')
        self.assertEqual(list(oof.columns), ev.COLUMNAS_OOF)
        self.assertEqual(len(oof), 8 * len(self.entradas['contextos']))
        self.assertFalse(oof.isna().any().any())
        self.assertFalse(oof.duplicated(['candidato', 'escenario', 'repeticion', 'ID_POLIGONO']).any())
        self.assertEqual(set(oof.candidato), {p['candidato'] for p in self.cfg['procedimientos']})
        self.assertEqual(set(oof.version), {t12.VERSION})
        self.assertFalse(set(oof.ID_POLIGONO) & self.entradas['reservados'])
        filas = self.refs + oof.to_dict('records')
        contrato.validar_oof(filas, self.entradas['contextos'])

    def test_fuente_y_real_vienen_del_contexto(self):
        oof = self.leer('predicciones_oof_t12.csv')
        for r in oof.sample(400, random_state=0).itertuples():
            c = self.entradas['contextos'][(r.escenario, r.repeticion, r.ID_POLIGONO)]
            self.assertEqual((r.real, r.fuente, r.particion), (c['real'], c['fuente'], c['particion']))

    def test_seleccion_interna_guarda_tambien_las_descartadas(self):
        s = self.leer('seleccion_interna_t12.csv')
        g = s.groupby(['candidato', 'escenario', 'repeticion', 'particion'])
        self.assertEqual(len(g), 8 * len(CTX_SUB))
        self.assertTrue((g.size() == 3).all())          # referencia sola + 2 opciones
        self.assertTrue((g.elegida.sum() == 1).all())
        self.assertTrue((g.referencia_sola.sum() == 1).all())
        self.assertTrue(s.MAE_interno.notna().all())
        self.assertEqual(set(s[s.escenario == 'A'].internas), {'estratificada'})
        self.assertEqual(set(s[s.escenario == 'B'].internas), {'celda'})

    def test_metricas(self):
        m = self.leer('metricas_t12.csv')
        self.assertEqual(len(m), 10 * 2 * 2 * 6)        # 8 + 2 referencias, A/B, todas/sin_respaldo, 5 reps + promedio
        p = m[m.repeticion == 'promedio']
        self.assertTrue(np.isfinite(p[['MAE', 'RMSE', 'sesgo', 'R2']].to_numpy()).all())

    def test_comparacion_y_promocion(self):
        c = self.leer('comparacion_emparejada_t12.csv')
        self.assertEqual(len(c), 13 * 4)
        self.assertEqual(set(c.tipo), {'frente_a_referencia', 'C1_ablacion', 'C8_misma_referencia'})
        self.assertEqual(c.aplica_promocion.sum(), 1)
        fila = c[c.aplica_promocion].iloc[0]
        self.assertEqual((fila.candidato, fila.frente_a, fila.escenario, fila.subconjunto),
                         ('t12_het_GP', ev.REFERENCIA, 'A', 'sin_respaldo'))
        self.assertIn(fila.estado_promocion, {'cumple_T03_pendiente_C2_revuelto', 'no_cumple_T03'})
        self.assertEqual(set(c[~c.aplica_promocion].estado_promocion), {'no_aplica'})
        # C1: los cuatro pares registrados
        self.assertEqual(set(zip(c[c.tipo == 'C1_ablacion'].candidato, c[c.tipo == 'C1_ablacion'].frente_a)),
                         {tuple(x) for x in self.cfg['controles']['C1_ablacion']['pares']})
        # el control de mediana se compara con la mediana y también con la media
        med = c[c.candidato == 't12_control_mediana_het_GP']
        self.assertEqual(set(med.frente_a), {ev.REFERENCIA_MEDIANA, ev.REFERENCIA})

    def test_dMAE_recalculado_aparte(self):
        """dMAE (A, todas) = promedio por parcela de la diferencia de error absoluto, calculado con pandas."""
        oof = self.leer('predicciones_oof_t12.csv')
        base = pd.DataFrame([r for r in self.refs if r['candidato'] == ev.REFERENCIA and r['escenario'] == 'A'])
        base['prediccion'] = base.prediccion.astype(float)
        base['real'] = base.real.astype(float)
        base['repeticion'] = base.repeticion.astype(int)
        c = self.leer('comparacion_emparejada_t12.csv')
        for cand in ('t12_het_GP', 't12_control_comun_P', 't12_gb_GP'):
            a = oof[(oof.candidato == cand) & (oof.escenario == 'A')]
            j = a.merge(base, on=['ID_POLIGONO', 'repeticion'], suffixes=('', '_b'))
            self.assertEqual(len(j), len(a))
            j['d'] = (j.prediccion - j.real).abs() - (j.prediccion_b - j.real).abs()
            esperado = j.groupby('ID_POLIGONO').d.mean().mean()
            fila = c[(c.candidato == cand) & (c.frente_a == ev.REFERENCIA) & (c.escenario == 'A') &
                     (c.subconjunto == 'todas')].iloc[0]
            self.assertAlmostEqual(fila.dMAE, esperado, places=12)

    def test_metricas_recalculadas_aparte(self):
        """MAE, RMSE, sesgo y R2 por repetición y su promedio, con pandas, para tres candidatos."""
        oof = self.leer('predicciones_oof_t12.csv')
        m = self.leer('metricas_t12.csv')
        for cand in ('t12_het_GP', 't12_control_comun_G', 't12_control_mediana_het_GP'):
            for esc, sub in (('A', 'todas'), ('B', 'sin_respaldo')):
                g = oof[(oof.candidato == cand) & (oof.escenario == esc)]
                if sub == 'sin_respaldo':
                    g = g[g.fuente == 'municipio']
                filas = []
                for rep in range(1, 6):
                    z = g[g.repeticion == rep]
                    e = z.prediccion - z.real
                    filas.append(dict(n=len(z), MAE=e.abs().mean(), RMSE=np.sqrt((e ** 2).mean()), sesgo=e.mean(),
                                      R2=1 - (e ** 2).sum() / ((z.real - z.real.mean()) ** 2).sum()))
                esperado = pd.DataFrame(filas)
                t = m[(m.candidato == cand) & (m.escenario == esc) & (m.subconjunto == sub)].set_index('repeticion')
                for i in range(5):
                    for col in ('n', 'MAE', 'RMSE', 'sesgo', 'R2'):
                        self.assertAlmostEqual(t.loc[str(i + 1), col], esperado.loc[i, col], places=10)
                for col in ('MAE', 'RMSE', 'sesgo', 'R2'):
                    self.assertAlmostEqual(t.loc['promedio', col], esperado[col].mean(), places=10)

    def test_predicciones_59_exploratorias(self):
        p = self.leer('predicciones_59_t12.csv')
        self.assertEqual(len(p), 8 * N_RESERVADAS)
        self.assertEqual(set(p.ID_POLIGONO), self.entradas['reservados'])
        self.assertTrue(np.isfinite(p[['prediccion', 'referencia', 'correccion']].to_numpy()).all())
        self.assertTrue(p.exploratoria.all())
        np.testing.assert_allclose(p.prediccion, p.referencia + p.correccion, atol=1e-12)
        # La referencia de cada reservada es la media de TODAS las etiquetadas de su municipio (las 76).
        y = pd.Series({k[0]: float(v['rendimiento_t_ha']) for k, v in self.entradas['tabla'].items()
                       if k[0] in self.entradas['conocidos']})
        mun = pd.Series({k[0]: v['municipio'] for k, v in self.entradas['tabla'].items()})
        media = y.groupby(mun.loc[y.index]).mean()
        mediana = y.groupby(mun.loc[y.index]).median()
        es_mediana = p.candidato == 't12_control_mediana_het_GP'
        np.testing.assert_allclose(p.referencia[~es_mediana], p.municipio.map(media)[~es_mediana], atol=1e-12)
        np.testing.assert_allclose(p.referencia[es_mediana], p.municipio.map(mediana)[es_mediana], atol=1e-12)
        self.assertEqual(es_mediana.sum(), N_RESERVADAS)
        self.assertEqual(set(p.fuente), {'municipio'})

    def test_resumen_de_consola_es_solo_A_sin_respaldo_frente_a_la_referencia(self):
        lineas = ev.resumen_consola(self.tablas).split('\n')
        self.assertEqual(len(lineas), 1 + 8)
        self.assertEqual({l.split()[0] for l in lineas[1:]}, {p['candidato'] for p in self.cfg['procedimientos']})


class Prueba13bSinFiltracionNiParciales(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.entradas = entradas_sinteticas()
        cls.reducida = reducir(cls.entradas)
        cls.cfg = procedimientos_reducidos()
        cls.procs = cls.cfg['procedimientos']

    def test_etiquetas_de_evaluacion_no_cambian_las_predicciones(self):
        base = ev.evaluar_contexto(self.entradas, self.procs, 'A', 1, 0)
        _, _, te = v3.preparar_contexto(self.entradas, 'A', 1, 0)
        otra = copy.deepcopy(self.entradas)
        for pid in te.index:
            otra['tabla'][(pid,)]['rendimiento_t_ha'] = '99.0'
        nueva = ev.evaluar_contexto(otra, self.procs, 'A', 1, 0)
        np.testing.assert_array_equal([f['prediccion'] for f in base['oof']], [f['prediccion'] for f in nueva['oof']])
        np.testing.assert_array_equal([f['MAE_interno'] for f in base['seleccion']],
                                      [f['MAE_interno'] for f in nueva['seleccion']])

    def test_etiquetas_basura_de_las_reservadas_no_cambian_las_59(self):
        base = ev.ajustar_59(self.entradas, self.procs)
        otra = copy.deepcopy(self.entradas)
        for pid in otra['reservados']:
            otra['tabla'][(pid,)]['rendimiento_t_ha'] = '77.0'
        nueva = ev.ajustar_59(otra, self.procs)
        self.assertEqual([f['prediccion'] for f in base], [f['prediccion'] for f in nueva])

    def test_el_resultado_no_depende_del_numero_de_procesos(self):
        if multiprocessing.get_start_method() != 'fork':
            self.skipTest('La prueba parchea el cargador y necesita fork')
        ctx = (('A', 1, 0), ('B', 2, 3))
        with patch.object(v3, 'cargar_entradas', lambda raiz: self.entradas):
            uno = ev.evaluar_todos(self.entradas, self.procs, ctx, procesos=1)
            dos = ev.evaluar_todos(self.entradas, self.procs, ctx, procesos=2, raiz='x')
        self.assertEqual(uno, dos)

    def test_dos_corridas_dan_lo_mismo(self):
        ctx = (('A', 3, 1),)
        a = ev.evaluar_todos(self.entradas, self.procs, ctx)
        b = ev.evaluar_todos(self.entradas, self.procs, ctx)
        self.assertEqual(a, b)

    def test_si_un_contexto_falla_no_se_crea_nada(self):
        with tempfile.TemporaryDirectory() as d:
            salida = Path(d) / 'salida'
            llamadas = []
            original = ev.evaluar_contexto

            def falla(*a, **k):
                llamadas.append(1)
                if len(llamadas) == 3:
                    raise ValueError('falla inventada')
                return original(*a, **k)
            with patch.object(ev, 'compuertas', lambda raiz, c: (self.cfg, {})), \
                    patch.object(ev, 'preparar_salida', lambda s, r: salida), \
                    patch.object(v3, 'cargar_entradas', lambda raiz: self.entradas), \
                    patch.object(ev, 'evaluar_contexto', falla), patch.object(ev, 'N_ETIQUETADAS', 76), \
                    patch.object(ev, 'N_RESERVADAS', 12), patch('builtins.print'):
                with self.assertRaises(ValueError):
                    ev.ejecutar('x', confirmo_barreras=True)
            self.assertFalse(salida.exists())

    def test_si_una_entrada_cambia_durante_la_corrida_no_se_crea_nada(self):
        with tempfile.TemporaryDirectory() as d:
            salida = Path(d) / 'salida'
            oof, sel = corrida_memorizada(self.reducida, self.cfg)
            vistas = {}
            original = ev.sha

            def cambiante(ruta):
                n = vistas[str(ruta)] = vistas.get(str(ruta), 0) + 1
                return original(ruta) + ('' if n == 1 else 'x')
            with patch.object(ev, 'compuertas', lambda raiz, c: (self.cfg, {})), \
                    patch.object(ev, 'evaluar_todos', lambda *a, **k: (oof, sel)), \
                    patch.object(ev, 'preparar_salida', lambda s, r: salida), \
                    patch.object(v3, 'cargar_entradas', lambda raiz: self.reducida), \
                    patch.object(ev, 'cargar_referencias', lambda raiz: filas_referencia(self.reducida)), \
                    patch.object(ev, 'sha', cambiante), \
                    patch.object(ev, 'N_ETIQUETADAS', 76), patch.object(ev, 'N_RESERVADAS', 12), \
                    patch.object(ev, 'CONTEXTOS', CTX_SUB), patch('builtins.print'):
                with self.assertRaises(ValueError) as cm:
                    ev.ejecutar('x', confirmo_barreras=True)
            self.assertIn('cambió durante', str(cm.exception))
            self.assertFalse(salida.exists())

    def test_si_las_tablas_no_validan_no_se_crea_nada(self):
        with tempfile.TemporaryDirectory() as d:
            salida = Path(d) / 'salida'
            refs_malas = filas_referencia(self.reducida)
            refs_malas = [dict(r, prediccion=repr(float(r['prediccion']) + 1.0))
                          if r['candidato'] == ev.REFERENCIA else r for r in refs_malas]
            oof, sel = corrida_memorizada(self.reducida, self.cfg)
            with patch.object(ev, 'compuertas', lambda raiz, c: (self.cfg, {})), \
                    patch.object(ev, 'evaluar_todos', lambda *a, **k: (oof, sel)), \
                    patch.object(ev, 'preparar_salida', lambda s, r: salida), \
                    patch.object(v3, 'cargar_entradas', lambda raiz: self.reducida), \
                    patch.object(ev, 'cargar_referencias', lambda raiz: refs_malas), \
                    patch.object(ev, 'N_ETIQUETADAS', 76), patch.object(ev, 'N_RESERVADAS', 12), \
                    patch.object(ev, 'CONTEXTOS', CTX_SUB), patch('builtins.print'):
                with self.assertRaises(ValueError):
                    ev.ejecutar('x', confirmo_barreras=True)
            self.assertFalse(salida.exists())


class Prueba14Compuertas(unittest.TestCase):
    """Con una copia mínima del proyecto: sólo corre si todo lo registrado coincide."""

    @classmethod
    def setUpClass(cls):
        cls.real = Path(t12.RAIZ)
        if not (cls.real / t12.SALIDA_COMPROBACIONES).exists():
            raise unittest.SkipTest('Todavía no existe registro/t12/comprobaciones.json')

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        c = json.loads((self.real / t12.SALIDA_COMPROBACIONES).read_text())
        for f in [t12.DISENO, t12.SALIDA_COMPROBACIONES, *c['codigo_sha256'], *c['fuentes_sha256']]:
            (self.tmp / f).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(self.real / f, self.tmp / f)
        self.c = c

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _editar_comprobaciones(self, **cambios):
        ruta = self.tmp / t12.SALIDA_COMPROBACIONES
        d = json.loads(ruta.read_text())
        d.update(cambios)
        ruta.write_text(json.dumps(d))

    def test_pasa_cuando_todo_coincide(self):
        cfg, c = ev.compuertas(self.tmp, True)
        self.assertEqual(len(cfg['procedimientos']), 8)
        self.assertEqual(c['resultado'], 'aprobado')

    def test_exige_confirmar_las_barreras(self):
        for valor in (False, None, 1, 'si'):
            with self.subTest(valor=valor), self.assertRaises(ValueError):
                ev.compuertas(self.tmp, valor)

    def test_exige_las_comprobaciones(self):
        (self.tmp / t12.SALIDA_COMPROBACIONES).unlink()
        with self.assertRaises(ValueError):
            ev.compuertas(self.tmp, True)

    def test_exige_que_esten_aprobadas(self):
        self._editar_comprobaciones(resultado='fallido')
        with self.assertRaises(ValueError):
            ev.compuertas(self.tmp, True)

    def test_exige_el_mismo_diseno(self):
        self._editar_comprobaciones(sha_diseno_t12='0' * 64)
        with self.assertRaises(ValueError):
            ev.compuertas(self.tmp, True)

    def test_se_detiene_si_cambia_el_codigo_comprobado(self):
        archivo = self.tmp / 'scripts/t12_heterogeneidad.py'
        archivo.write_text(archivo.read_text() + '\n# cambio\n')
        with self.assertRaises(ValueError):
            ev.compuertas(self.tmp, True)

    def test_se_detiene_si_cambia_una_entrada(self):
        archivo = self.tmp / 'registro/t07/tabla_comun.csv'
        archivo.write_text(archivo.read_text() + '\n')
        with self.assertRaises(ValueError):
            ev.compuertas(self.tmp, True)

    def test_se_detiene_si_cambia_el_diseno(self):
        archivo = self.tmp / t12.DISENO
        archivo.write_text(archivo.read_text() + ' ')
        with self.assertRaises(ValueError):
            ev.compuertas(self.tmp, True)

    def test_salida_no_sobrescribe(self):
        (self.tmp / 'registro/t12').mkdir(parents=True, exist_ok=True)
        ev.preparar_salida('registro/t12', self.tmp)                      # la carpeta puede existir
        (self.tmp / 'registro/t12/metricas_t12.csv').write_text('x')
        with self.assertRaises(ValueError):
            ev.preparar_salida('registro/t12', self.tmp)
        ev.preparar_salida('reports/t12_repro', self.tmp)
        for fuera in ('registro/t03', 'scripts', '/tmp/otra', 'registro/t12/../t03'):
            with self.subTest(fuera=fuera), self.assertRaises(ValueError):
                ev.preparar_salida(fuera, self.tmp)

    def test_main_pasa_la_bandera_tal_cual(self):
        llamadas = []

        def falso(salida, raiz, confirmo, procesos):
            llamadas.append((str(salida), confirmo, procesos))
            return Path(salida), None
        with patch.object(ev, 'ejecutar', falso), patch.object(ev, 'resumen_consola', lambda t: ''), \
                patch('builtins.print'):
            ev.main(['--salida', 'registro/t12'])
            ev.main(['--salida', 'registro/t12', '--confirmo-barreras', '--procesos', '3'])
        self.assertEqual(llamadas, [('registro/t12', False, 1), ('registro/t12', True, 3)])


class Prueba15PoblacionesReales(unittest.TestCase):
    """x_poblaciones (sin cifras fijas) es idéntica a entradas_x de los pasos anteriores con los datos reales,
    y `ejecutar` se niega si las poblaciones no son 138 y 59."""

    def test_igual_que_entradas_x(self):
        e = v3.cargar_entradas(t12.RAIZ)
        a, ya, ra = ev.x_poblaciones(e)
        b, yb, rb = t12.entradas_x(e)
        pd.testing.assert_frame_equal(a, b)
        pd.testing.assert_series_equal(ya, yb)
        pd.testing.assert_frame_equal(ra, rb)
        self.assertEqual((len(a), len(ra)), (ev.N_ETIQUETADAS, ev.N_RESERVADAS))

    def test_ejecutar_exige_138_y_59(self):
        e = entradas_sinteticas()
        with patch.object(ev, 'compuertas', lambda raiz, c: (procedimientos_reducidos(), {})), \
                patch.object(ev, 'preparar_salida', lambda s, r: Path('/nunca/se/crea')), \
                patch.object(v3, 'cargar_entradas', lambda raiz: e):
            with self.assertRaises(ValueError) as cm:
                ev.ejecutar('x', confirmo_barreras=True)
        self.assertIn('138', str(cm.exception))
        self.assertFalse(Path('/nunca/se/crea').exists())


if __name__ == '__main__':
    unittest.main()
