"""Pruebas de los controles C2 a C6 de T12 (paso 5) con datos INVENTADOS.

Igual que en el paso 4: la tabla, las particiones y las referencias se fabrican aquí; ninguna prueba lee
rendimientos reales ni calcula errores contra ellos. Lo que se comprueba es el tubo (revuelto, submuestreo,
cortes, reproducción de los modelos finales, parcelas extremas, compuertas y escritura), no los resultados.
"""
import contextlib
import copy
import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd

from scripts import evaluacion_comun_centrado_loo as v3
from scripts import evaluacion_comun_contrato as contrato
from scripts import evaluacion_comun_reportes as comun
from scripts import t12_controles as ctl
from scripts import t12_evaluar as ev
from scripts import t12_heterogeneidad as t12
from tests.test_t12_evaluar import (CTX_SUB, NUMERICAS, entradas_sinteticas, filas_referencia,
                                    procedimientos_reducidos, reducir)

CTX_A = tuple(c for c in CTX_SUB if c[0] == 'A')
REF = ctl.REFERENCIA
_CACHE = {}


def entorno():
    """Entradas inventadas, diseño reducido, referencias y la evaluación principal (una sola vez).

    Cinco parcelas etiquetadas de Oeste pasan a ser la única de su municipio ('Unico1'…'Unico5'; el selector interno
    las junta en un estrato 'otros' como con los municipios chicos reales): cuando les toca estar en la evaluación
    no tienen entrenamiento de su municipio y su respaldo es el grupo. Así `sin_respaldo` y `todas` se distinguen. La corrida es propia (no la memoria de las pruebas del paso 4, que usa otras entradas).
    """
    if not _CACHE:
        base = entradas_sinteticas()
        unicas = sorted(k[0] for k, v in base['tabla'].items()
                        if v['municipio'] == 'Oeste' and k[0] in base['conocidos'])[1:6]
        nombres = {pid: f'Unico{i}' for i, pid in enumerate(unicas, 1)}
        for pid, nombre in nombres.items():
            base['tabla'][(pid,)]['municipio'] = nombre
        for r in base['particiones']:
            if r['ID_POLIGONO'] in nombres:
                r['municipio'] = nombres[r['ID_POLIGONO']]
                r['particion_principal'] = '0'           # juntas: en las otras particiones hay 5 en 'otros'
        base['contextos'] = contrato.contextos(base['tabla'], base['particiones'])
        entradas = reducir(base)
        cfg = procedimientos_reducidos()
        refs = filas_referencia(entradas)
        oof, sel = ev.evaluar_todos(entradas, cfg['procedimientos'], CTX_SUB)
        _CACHE.update(entradas=entradas, cfg=cfg, refs=refs, refs_df=ctl.filas_a_df(refs), oof_lista=oof,
                      sel_lista=sel, principal=pd.DataFrame(oof), seleccion=pd.DataFrame(sel), unicas=unicas)
        c = pd.DataFrame(dict(id_parcela=sorted(k[0] for k in entradas['tabla'])))
        n = len(c)
        c['contorno_categoria'] = ['A' if i % 3 else ('B' if i % 2 else 'C') for i in range(n)]
        c['contorno_angosta_o_muy_pequena'] = ['si' if i % 5 == 0 else 'no' for i in range(n)]
        c['alerta_contorno_t03_bis'] = ['si' if i % 4 == 0 else 'no' for i in range(n)]
        c['escalon_etiqueta_municipio'] = [(0.01, 0.1, 0.5, np.nan)[i % 4] for i in range(n)]
        c['vecina_etiquetada_menos_20m'] = ['si' if i % 2 else 'no' for i in range(n)]
        c['numero_vecinas_etiquetadas_menos_20m'] = 0
        _CACHE['calidad'] = c
        assert len(entradas['conocidos']) == 76
        assert (_CACHE['principal'].fuente != 'municipio').any(), 'debe haber respaldo para distinguir subconjuntos'
    return _CACHE


def dmae_aparte(cand, ref, sub):
    """ΔMAE de T03 §4 calculado con una unión de pandas, sin usar `dmae`."""
    m = cand.merge(ref, on=['repeticion', 'ID_POLIGONO'], suffixes=('', '_b'))
    assert len(m) == len(cand) == len(ref)
    if sub == 'sin_respaldo':
        m = m[m.fuente == 'municipio']
    d = (m.prediccion - m.real).abs() - (m.prediccion_b - m.real_b).abs()
    return float(d.groupby(m.ID_POLIGONO).mean().mean())


def A(df, cand):
    return df[(df.escenario == 'A') & (df.candidato == cand)]


class Prueba16Medidas(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.e = entorno()

    def test_dmae_coincide_con_comparar_de_T15(self):
        filas = list(self.e['refs']) + self.e['principal'].to_dict('records')
        ref_a = A(self.e['refs_df'], REF)
        for cand in ('t12_het_GP', 't12_gb_GP', 't12_control_comun_P'):
            for sub in ('sin_respaldo', 'todas'):
                esperado = comun.comparar(filas, self.e['entradas']['contextos'], cand, REF, 'A', sub)['dMAE']
                mio = ctl.dmae(A(self.e['principal'], cand), ref_a, sub)
                self.assertAlmostEqual(mio, esperado, places=12, msg=(cand, sub))

    def test_dmae_coincide_con_el_calculo_aparte(self):
        ref_a = A(self.e['refs_df'], REF)
        for cand in ('t12_het_GP', 't12_het_G', 't12_control_comun_GP'):
            for sub in ('sin_respaldo', 'todas'):
                self.assertAlmostEqual(ctl.dmae(A(self.e['principal'], cand), ref_a, sub),
                                       dmae_aparte(A(self.e['principal'], cand), ref_a, sub), places=12)

    def test_dmae_de_la_referencia_consigo_misma_es_cero(self):
        ref_a = A(self.e['refs_df'], REF)
        self.assertEqual(ctl.dmae(ref_a, ref_a, 'todas'), 0.0)

    def test_dmae_exige_comparacion_emparejada(self):
        ref_a = A(self.e['refs_df'], REF)
        cand = A(self.e['principal'], 't12_het_GP')
        with self.assertRaises(ValueError):
            ctl.dmae(cand.iloc[:-1], ref_a, 'todas')

    def test_dmae_promedia_por_parcela_no_por_fila(self):
        """Con repeticiones desiguales por parcela, el promedio por fila y el por parcela difieren."""
        ref = pd.DataFrame(dict(repeticion=[1, 2, 3, 1], ID_POLIGONO=['a', 'a', 'a', 'b'], real=[1.0] * 4,
                                prediccion=[2.0, 2.0, 2.0, 2.0], fuente=['municipio'] * 4))
        cand = ref.assign(prediccion=[1.5, 1.5, 1.5, 1.0])         # a mejora 0.5 (3 veces); b mejora 1.0
        self.assertAlmostEqual(ctl.dmae(cand, ref, 'todas'), (-0.5 + -1.0) / 2)

    def test_metricas_por_repeticion(self):
        x = A(self.e['principal'], 't12_het_GP')
        m = ctl.metricas_por_repeticion(x)
        maes, rmses, sesgos = [], [], []
        for _, g in x.groupby('repeticion'):
            e = g.prediccion.to_numpy() - g.real.to_numpy()
            maes.append(np.mean(np.abs(e)))
            rmses.append(np.sqrt(np.mean(e ** 2)))
            sesgos.append(np.mean(e))
        self.assertAlmostEqual(m['MAE'], np.mean(maes), places=12)
        self.assertAlmostEqual(m['RMSE'], np.mean(rmses), places=12)
        self.assertAlmostEqual(m['sesgo'], np.mean(sesgos), places=12)


class Prueba17Revuelto(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.e = entorno()
        cls.cols = ctl.columnas_gp(cls.e['cfg'])
        cls.ref_a = A(cls.e['refs_df'], REF)

    def test_las_columnas_revueltas_son_todas_las_G_y_P_del_diseno_completo(self):
        completo = ctl.columnas_gp(t12.cargar_diseno())
        self.assertEqual(set(completo), set(NUMERICAS))
        self.assertEqual(len(completo), len(set(completo)))
        self.assertEqual(set(self.cols), set(NUMERICAS))

    def test_baraja_solo_dentro_del_municipio_y_filas_completas(self):
        ent = self.e['entradas']
        antes = copy.deepcopy(ent['tabla'])
        b = ctl.barajar(ent, self.cols, 99)
        self.assertEqual(ent['tabla'], antes)                       # el original no se toca
        self.assertEqual(set(b['tabla']), set(ent['tabla']))
        movidas = 0
        for municipio in {v['municipio'] for v in antes.values()}:
            ids = sorted(k[0] for k, v in antes.items() if v['municipio'] == municipio and k[0] in ent['conocidos'])
            orig = [tuple(antes[(i,)][c] for c in self.cols) for i in ids]
            nuevo = [tuple(b['tabla'][(i,)][c] for c in self.cols) for i in ids]
            self.assertEqual(sorted(orig), sorted(nuevo))            # mismas filas, sólo cambian de dueña
            movidas += sum(o != n for o, n in zip(orig, nuevo))
        self.assertGreater(movidas, 40)                              # sí se movió casi todo (no es la identidad)

    def test_no_toca_reservadas_etiquetas_ni_otras_columnas(self):
        ent = self.e['entradas']
        b = ctl.barajar(ent, self.cols, 5)
        for k, v in ent['tabla'].items():
            nuevo = b['tabla'][k]
            if k[0] in ent['reservados']:
                self.assertEqual(nuevo, v)
            for c in v:
                if c not in self.cols:
                    self.assertEqual(nuevo[c], v[c], c)

    def test_determinista_y_cada_semilla_baraja_distinto(self):
        ent = self.e['entradas']
        a, a2 = ctl.barajar(ent, self.cols, 7), ctl.barajar(ent, self.cols, 7)
        c = ctl.barajar(ent, self.cols, 8)
        self.assertEqual(a['tabla'], a2['tabla'])
        self.assertNotEqual(a['tabla'], c['tabla'])

    def test_la_valoracion_con_la_identidad_reproduce_el_observado(self):
        """Si no se baraja nada, repetir todo el procedimiento da el mismo ΔMAE que la evaluación principal."""
        observado = ctl.dmae(A(self.e['principal'], ctl.HET_GP), self.ref_a)
        with patch.object(ctl, 'barajar', lambda ent, cols, semilla: ent):
            r = ctl.revuelto_una(self.e['entradas'], self.e['cfg'], self.ref_a, 1, CTX_A)
        self.assertAlmostEqual(r['dMAE_revuelto'], observado, places=12)

    def test_revolver_empeora_y_cada_permutacion_usa_su_semilla(self):
        observado = ctl.dmae(A(self.e['principal'], ctl.HET_GP), self.ref_a)
        self.assertLess(observado, 0, 'la señal inventada debe existir para que la prueba tenga poder')
        filas = [ctl.revuelto_una(self.e['entradas'], self.e['cfg'], self.ref_a, k, CTX_A) for k in (1, 2, 3)]
        self.assertEqual([f['semilla'] for f in filas], [ctl.SEMILLA_REVUELTO + k for k in (1, 2, 3)])
        for f in filas:
            self.assertGreater(f['dMAE_revuelto'], observado)
        self.assertEqual(len({f['dMAE_revuelto'] for f in filas}), 3)
        otra = ctl.revuelto_una(self.e['entradas'], self.e['cfg'], self.ref_a, 2, CTX_A)
        self.assertEqual(otra, filas[1])                             # repetible, no depende del orden

    def test_las_reservadas_y_las_etiquetas_de_evaluacion_no_cambian_el_revuelto(self):
        ent = self.e['entradas']
        base = ctl.revuelto_una(ent, self.e['cfg'], self.ref_a, 1, CTX_A[:2])
        otra = copy.deepcopy(ent)
        for pid in otra['reservados']:
            otra['tabla'][(pid,)]['rendimiento_t_ha'] = '55.0'
            otra['tabla'][(pid,)]['elevacion_media_m'] = '1.0'
        self.assertEqual(ctl.revuelto_una(otra, self.e['cfg'], self.ref_a, 1, CTX_A[:2]), base)

    def test_p_valor_cuenta_empates_y_suma_uno(self):
        valores = [-0.02, -0.01, 0.0, 0.01, -0.005]

        def falso(entradas, cfg, ref_a, k, contextos):
            return dict(permutacion=k, semilla=ctl.SEMILLA_REVUELTO + k, dMAE_revuelto=valores[k - 1])

        with patch.object(ctl, 'revuelto_una', falso):
            t = ctl.control_revuelto(None, None, None, observado=-0.01, n=5)['control_revuelto_t12.csv']
        self.assertEqual(list(t.permutacion), [1, 2, 3, 4, 5])
        self.assertEqual(list(t.igual_o_mejor_que_el_observado), [True, True, False, False, False])
        self.assertTrue((t.b == 2).all())
        self.assertTrue(np.allclose(t.p, 3 / 6))
        self.assertTrue((t.n_permutaciones == 5).all())
        self.assertTrue((t.dMAE_observado == -0.01).all())

    def test_ninguna_permutacion_mejor_da_p_minimo_de_20_permutaciones(self):
        with patch.object(ctl, 'revuelto_una', lambda e, c, r, k, x: dict(permutacion=k, semilla=0, dMAE_revuelto=0.1)):
            t = ctl.control_revuelto(None, None, None, observado=-0.01)['control_revuelto_t12.csv']
        self.assertEqual(len(t), 20)
        self.assertAlmostEqual(float(t.p.iloc[0]), 1 / 21)

    def test_varios_procesos_solo_con_la_corrida_real(self):
        with self.assertRaises(ValueError):
            ctl.control_revuelto(None, None, None, -0.01, n=2, contextos=CTX_A, procesos=2, raiz='x')


class Prueba18Curva(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.e = entorno()
        cls.ref_a = A(cls.e['refs_df'], REF)

    def contexto(self, rep=1, fold=0):
        return v3.preparar_contexto(self.e['entradas'], 'A', rep, fold)

    def test_submuestreo_tamanos_y_municipios_pequenos(self):
        tr, y, te = self.contexto()
        n = tr.municipio.value_counts()
        self.assertTrue((n < ctl.N_MIN_SUBMUESTREO).any() and (n >= ctl.N_MIN_SUBMUESTREO).any(),
                        'el ejemplo debe tener municipios grandes y pequeños')
        for f in (0.5, 0.75):
            sub = ctl.submuestrear(tr, f, np.random.RandomState(3))
            self.assertTrue(set(sub.index) <= set(tr.index))
            self.assertFalse(set(sub.index) & set(te.index))
            m = sub.municipio.value_counts()
            for mun, total in n.items():
                esperado = int(np.floor(f * total + 0.5)) if total >= ctl.N_MIN_SUBMUESTREO else total
                self.assertEqual(m[mun], esperado, (f, mun))
            self.assertTrue(sub.index.is_monotonic_increasing)

    def test_submuestreo_con_todo_devuelve_todo_y_es_repetible(self):
        tr, _, _ = self.contexto()
        self.assertEqual(list(ctl.submuestrear(tr, 1.0, np.random.RandomState(1)).index), list(tr.index))
        a = ctl.submuestrear(tr, 0.5, np.random.RandomState(4))
        b = ctl.submuestrear(tr, 0.5, np.random.RandomState(4))
        c = ctl.submuestrear(tr, 0.5, np.random.RandomState(5))
        self.assertEqual(list(a.index), list(b.index))
        self.assertNotEqual(list(a.index), list(c.index))

    def test_con_la_fraccion_completa_se_reproduce_la_evaluacion_principal(self):
        ctxs = (('A', 1, 0), ('A', 1, 3))
        filas = pd.DataFrame(ctl.curva_una(self.e['entradas'], self.e['cfg'], 1.0, 20261015, ctxs))
        for cand, ref in ((REF, self.ref_a), (ctl.CONTROL_GP, A(self.e['principal'], ctl.CONTROL_GP)),
                          (ctl.HET_GP, A(self.e['principal'], ctl.HET_GP))):
            x = filas[filas.procedimiento == cand].set_index('ID_POLIGONO')
            r = ref.set_index(['repeticion', 'ID_POLIGONO'])
            esperado = r.loc[[(1, i) for i in x.index]]
            np.testing.assert_allclose(x.prediccion.to_numpy(), esperado.prediccion.to_numpy(), rtol=0, atol=1e-12,
                                       err_msg=cand)
            self.assertEqual(list(x.fuente), list(esperado.fuente))

    def test_con_la_mitad_la_referencia_se_recalcula_y_la_evaluacion_no_cambia(self):
        rep, fold, semilla = 2, 0, 20261016
        tr, y, te = self.contexto(rep, fold)
        filas = pd.DataFrame(ctl.curva_una(self.e['entradas'], self.e['cfg'], 0.5, semilla, (('A', rep, fold),)))
        sub = ctl.submuestrear(tr, 0.5, np.random.RandomState([semilla, rep, fold]))
        self.assertLess(len(sub), len(tr))
        for cand in (REF, ctl.CONTROL_GP, ctl.HET_GP):
            x = filas[filas.procedimiento == cand]
            self.assertEqual(sorted(x.ID_POLIGONO), sorted(te.index))             # se evalúa lo mismo
            self.assertTrue((x.n_entrenamiento == len(sub)).all())
        # referencia: promedio de los rendimientos que SÍ quedaron en el submuestreo, por municipio
        medias = y.loc[sub.index].groupby(sub.municipio).mean()
        x = filas[filas.procedimiento == REF].set_index('ID_POLIGONO')
        for pid in te.index:
            if x.loc[pid, 'fuente'] == 'municipio':
                esperado = medias[te.loc[pid, 'municipio']]
            else:
                esperado = y.loc[sub.index][sub.cultivo_origen == te.loc[pid, 'cultivo_origen']].mean()
            self.assertAlmostEqual(x.loc[pid, 'prediccion'], esperado, places=12)
        # y es distinta de la referencia con todo el entrenamiento
        completa = A(self.e['refs_df'], REF).query('repeticion == @rep').set_index('ID_POLIGONO').prediccion
        self.assertFalse(np.allclose(x.prediccion.sort_index(), completa.loc[x.index].sort_index()))

    def test_tabla_de_la_curva(self):
        ctxs = tuple(c for c in CTX_A if c[1] == 1)
        t = ctl.control_curva(self.e['entradas'], self.e['cfg'], self.e['principal'], self.ref_a, (0.5,), (1, 2),
                              ctxs)['curva_aprendizaje_t12.csv']
        self.assertEqual(set(t.fraccion), {0.5, 1.0})
        self.assertEqual(set(t.procedimiento), {REF, ctl.CONTROL_GP, ctl.HET_GP})
        self.assertEqual(set(t.subconjunto), {'todas', 'sin_respaldo'})
        self.assertEqual(set(t[t.fraccion == 0.5].semilla.astype(str)), {'1', '2', 'promedio'})
        self.assertEqual(set(t[t.fraccion == 1.0].semilla.astype(str)), {'completo'})
        self.assertTrue((t[t.procedimiento == REF].dMAE_vs_referencia == 0).all())
        # 1.0 = evaluación principal restringida a esos contextos
        pr = self.e['principal']
        pr = pr[(pr.escenario == 'A') & (pr.repeticion == 1)]
        for cand in (ctl.CONTROL_GP, ctl.HET_GP):
            esperado = ctl.metricas_por_repeticion(pr[pr.candidato == cand])
            fila = t[(t.fraccion == 1.0) & (t.procedimiento == cand) & (t.subconjunto == 'todas')].iloc[0]
            self.assertAlmostEqual(fila.MAE, esperado['MAE'], places=12)
            self.assertAlmostEqual(fila.RMSE, esperado['RMSE'], places=12)
        ref1 = A(self.e['refs_df'], REF)
        ref1 = ref1[ref1.repeticion == 1]
        for cand in (ctl.CONTROL_GP, ctl.HET_GP):
            for sub in ('todas', 'sin_respaldo'):
                fila = t[(t.fraccion == 1.0) & (t.procedimiento == cand) & (t.subconjunto == sub)].iloc[0]
                self.assertAlmostEqual(fila.dMAE_vs_referencia, dmae_aparte(pr[pr.candidato == cand], ref1, sub),
                                       places=12)
        # el promedio es el promedio de las semillas
        for (cand, sub), g in t[t.fraccion == 0.5].groupby(['procedimiento', 'subconjunto']):
            semillas = g[g.semilla.astype(str).isin(['1', '2'])]
            prom = g[g.semilla.astype(str) == 'promedio'].iloc[0]
            self.assertAlmostEqual(prom.MAE, semillas.MAE.mean(), places=12)
            self.assertAlmostEqual(prom.dMAE_vs_referencia, semillas.dMAE_vs_referencia.mean(), places=12)
        # menos entrenamiento: más error de la referencia no está garantizado, pero el n sí baja
        h = t[(t.procedimiento == ctl.HET_GP) & (t.subconjunto == 'todas')]
        n = h.set_index(h.semilla.astype(str)).n_entrenamiento_promedio
        self.assertLess(n['1'], n['completo'])

    def test_el_respaldo_no_cambia_con_el_submuestreo(self):
        rep, fold = 1, 1
        filas = pd.DataFrame(ctl.curva_una(self.e['entradas'], self.e['cfg'], 0.5, 20261017, (('A', rep, fold),)))
        for pid, fu in zip(filas.ID_POLIGONO, filas.fuente):
            self.assertEqual(fu, self.e['entradas']['contextos'][('A', rep, pid)]['fuente'])


class Prueba19Desgloses(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.e = entorno()
        cls.tmp = Path(tempfile.mkdtemp())
        cls.ruta = cls.tmp / 'calidad.csv'
        cls.e['calidad'].to_csv(cls.ruta, index=False)
        cls.part = pd.DataFrame(cls.e['entradas']['particiones'])
        cls.attr = ctl.atributos(cls.ruta, cls.part)
        cls.oof = pd.concat([cls.e['principal'], cls.e['refs_df'][cls.e['refs_df'].candidato == REF]],
                            ignore_index=True)
        cls.t = ctl.desgloses(cls.oof, cls.attr)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_atributos(self):
        a, c = self.attr, self.e['calidad'].set_index('id_parcela')
        self.assertEqual(set(a.index), self.e['entradas']['conocidos'])
        for pid in list(a.index)[:30]:
            self.assertEqual(a.loc[pid, 'contorno'], 'A' if c.loc[pid, 'contorno_categoria'] == 'A' else 'B o C')
            self.assertEqual(a.loc[pid, 'angosta_o_muy_pequena'], c.loc[pid, 'contorno_angosta_o_muy_pequena'])
            self.assertEqual(a.loc[pid, 'alerta_contorno_t03_bis'], c.loc[pid, 'alerta_contorno_t03_bis'])
            self.assertEqual(a.loc[pid, 'municipio'], self.e['entradas']['tabla'][(pid,)]['municipio'])
        self.assertEqual(set(a.escalon_etiqueta), {'0.01', '0.1', '0.5', 'sin escalón'})

    def test_un_corte_cubre_a_todas_las_parcelas_una_vez(self):
        for corte in ctl.CORTES:
            g = self.t[(self.t.subconjunto == 'todas') & (self.t.escenario == 'A') & (self.t.candidato == REF) &
                       (self.t.desglose == corte)]
            self.assertEqual(g.n_parcelas.sum(), 76, corte)

    def test_metricas_de_un_corte_recalculadas_aparte(self):
        for sub in ('todas', 'sin_respaldo'):
            for cand in ('t12_het_GP', 't12_gb_GP'):
                filas = self.oof[(self.oof.escenario == 'A') & (self.oof.candidato == cand) &
                                 self.oof.ID_POLIGONO.map(self.attr.municipio).eq('Norte')]
                base = self.oof[(self.oof.escenario == 'A') & (self.oof.candidato == REF) &
                                self.oof.ID_POLIGONO.map(self.attr.municipio).eq('Norte')]
                if sub == 'sin_respaldo':
                    filas, base = filas[filas.fuente == 'municipio'], base[base.fuente == 'municipio']
                fila = self.t[(self.t.subconjunto == sub) & (self.t.escenario == 'A') & (self.t.candidato == cand) &
                              (self.t.desglose == 'municipio') & (self.t.categoria == 'Norte')].iloc[0]
                maes = [np.abs(g.prediccion - g.real).mean() for _, g in filas.groupby('repeticion')]
                self.assertAlmostEqual(fila.MAE, np.mean(maes), places=12)
                self.assertEqual(fila.n_parcelas, filas.ID_POLIGONO.nunique())
                self.assertEqual(fila.n_predicciones, len(filas))
                self.assertAlmostEqual(fila.dMAE_vs_referencia, dmae_aparte(filas, base, 'todas'), places=12)

    def test_la_referencia_tiene_dmae_cero_y_se_marca_lo_poco_informativo(self):
        self.assertTrue((self.t[self.t.candidato == REF].dMAE_vs_referencia == 0).all())
        self.assertTrue((self.t.poco_informativo == (self.t.n_parcelas < 5)).all())
        self.assertTrue((~self.t.poco_informativo).any())

    def test_una_categoria_con_pocas_parcelas_queda_marcada(self):
        raras = list(self.attr.index[:3])
        attr = self.attr.copy()
        attr['escalon_etiqueta'] = attr.escalon_etiqueta.astype(object)
        attr.loc[raras, 'escalon_etiqueta'] = 'rara'
        t = ctl.desgloses(self.oof[self.oof.escenario == 'A'], attr)
        f = t[(t.desglose == 'escalon_etiqueta') & (t.categoria == 'rara')]
        self.assertTrue(len(f) and (f.n_parcelas == 3).all() and f.poco_informativo.all())
        self.assertFalse(t[(t.desglose == 'municipio') & (t.categoria == 'Norte')].poco_informativo.any())

    def test_cuartiles_del_error_de_la_referencia(self):
        for esc in ('A', 'B'):
            r = self.oof[(self.oof.escenario == esc) & (self.oof.candidato == REF)]
            e = (r.prediccion - r.real).abs().groupby(r.ID_POLIGONO).mean()
            g = self.t[(self.t.subconjunto == 'todas') & (self.t.escenario == esc) & (self.t.candidato == REF) &
                       (self.t.desglose == 'cuartil_error_referencia')].set_index('categoria')
            self.assertEqual(set(g.index), {'Q1_menor_error', 'Q2', 'Q3', 'Q4_mayor_error'})
            self.assertTrue(g.n_parcelas.between(18, 20).all())
            self.assertLess(g.loc['Q1_menor_error', 'MAE'], g.loc['Q2', 'MAE'])
            self.assertLess(g.loc['Q3', 'MAE'], g.loc['Q4_mayor_error', 'MAE'])
            # los de Q4 son las parcelas de mayor error de la referencia
            q4 = e.sort_values().index[-int(g.loc['Q4_mayor_error', 'n_parcelas']):]
            esperado = np.mean([np.abs(x.prediccion - x.real).mean() for _, x in r[r.ID_POLIGONO.isin(q4)].groupby('repeticion')])
            self.assertAlmostEqual(g.loc['Q4_mayor_error', 'MAE'], esperado, places=12)

    def test_sensibilidad_sin_alerta(self):
        s = ctl.sensibilidad_sin_alerta(self.oof, self.attr)
        alerta = set(self.attr.index[self.attr.alerta_contorno_t03_bis == 'si'])
        self.assertTrue(alerta)
        for cand in ('t12_het_GP', REF):
            f = s[(s.subconjunto == 'todas') & (s.escenario == 'A') & (s.candidato == cand)].iloc[0]
            self.assertEqual(f.n_parcelas, 76)
            self.assertEqual(f.n_parcelas_sin_alerta, 76 - len(alerta))
            x = self.oof[(self.oof.escenario == 'A') & (self.oof.candidato == cand) &
                         ~self.oof.ID_POLIGONO.isin(alerta)]
            self.assertAlmostEqual(f.MAE_sin_alerta, np.mean([np.abs(g.prediccion - g.real).mean()
                                                              for _, g in x.groupby('repeticion')]), places=12)
        het = s[(s.subconjunto == 'sin_respaldo') & (s.escenario == 'A') & (s.candidato == 't12_het_GP')].iloc[0]
        ref = self.oof[(self.oof.escenario == 'A') & (self.oof.candidato == REF)]
        cand = self.oof[(self.oof.escenario == 'A') & (self.oof.candidato == 't12_het_GP')]
        keep = lambda d: d[(d.fuente == 'municipio') & ~d.ID_POLIGONO.isin(alerta)]
        self.assertAlmostEqual(het.dMAE_sin_alerta, dmae_aparte(keep(cand), keep(ref), 'todas'), places=12)
        self.assertTrue((s[s.candidato == REF][['dMAE', 'dMAE_sin_alerta']] == 0).all().all())

    def test_sin_alertas_la_sensibilidad_es_igual_a_la_principal(self):
        attr = self.attr.assign(alerta_contorno_t03_bis='no')
        s = ctl.sensibilidad_sin_alerta(self.oof, attr)
        for c in ('n_parcelas', 'MAE', 'RMSE', 'sesgo', 'dMAE'):
            np.testing.assert_allclose(s[c], s[c + '_sin_alerta'], rtol=0, atol=1e-12)


class Prueba20QueAprendio(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.e = entorno()
        cls.cands = (ctl.HET_GP, ctl.HET_G, ctl.GB_GP)
        cls.modelos = ctl.reproducir_finales(cls.e['entradas'], cls.e['cfg'], cls.e['principal'],
                                             cls.e['seleccion'], cls.cands, CTX_A)

    def test_reproduce_las_predicciones_guardadas_incluso_tras_pasar_por_csv(self):
        self.assertEqual(len(self.modelos), 3 * len(CTX_A))
        with tempfile.TemporaryDirectory() as d:
            ruta = Path(d) / 's.csv'
            self.e['seleccion'].to_csv(ruta, index=False, float_format='%.17g')
            sel = pd.read_csv(ruta)
            principal = pd.DataFrame(self.e['principal']).to_csv(Path(d) / 'p.csv', index=False, float_format='%.17g')
            principal = pd.read_csv(Path(d) / 'p.csv', float_precision='round_trip')
            otra = ctl.reproducir_finales(self.e['entradas'], self.e['cfg'], principal, sel, self.cands, CTX_A)
        self.assertEqual(set(otra), set(self.modelos))

    def test_se_detiene_si_la_seleccion_guardada_no_reproduce_la_prediccion(self):
        sel = self.e['seleccion'].copy()
        g = sel[(sel.candidato == ctl.HET_GP) & (sel.escenario == 'A') & (sel.repeticion == 1) & (sel.particion == 0)]
        elegida = g[g.elegida].index[0]
        otra = g[~g.elegida & (g.referencia_sola != g.loc[elegida, 'referencia_sola'])].index[0]
        sel.loc[[elegida, otra], 'elegida'] = [False, True]
        with self.assertRaises(ValueError):
            ctl.reproducir_finales(self.e['entradas'], self.e['cfg'], self.e['principal'], sel, (ctl.HET_GP,), CTX_A)

    def test_se_detiene_si_cambian_los_municipios_con_pendiente_propia(self):
        sel = self.e['seleccion'].copy()
        mascara = (sel.candidato == ctl.HET_GP) & (sel.escenario == 'A') & sel.elegida & ~sel.referencia_sola
        self.assertTrue(mascara.any())
        sel.loc[mascara, 'municipios_con_pendiente_propia'] = ''
        with self.assertRaises(ValueError):
            ctl.reproducir_finales(self.e['entradas'], self.e['cfg'], self.e['principal'], sel, (ctl.HET_GP,), CTX_A)

    def test_pendientes_resumen_recalculado_aparte(self):
        t = ctl.resumen_pendientes(self.modelos, ctl.HET_GP)
        n_total = len(CTX_A)
        n_sola = sum(1 for (c, _, _), (_, s, _) in self.modelos.items() if c == ctl.HET_GP and s)
        comun = t[t.fila == 'pendiente_comun']
        self.assertTrue((comun.n_contextos_total == n_total).all())
        self.assertTrue((comun.n_contextos_con_coeficiente + n_sola == n_total).all())
        self.assertTrue((comun.n_contextos_referencia_sola == n_sola).all())
        betas = {}
        for (c, rep, fold), (m, sola, _) in self.modelos.items():
            if c != ctl.HET_GP or sola:
                continue
            est = m.estado()
            for nombre, b in zip(m.nombres_, est['beta']):
                betas.setdefault(nombre, []).append(b)
        for r in comun.itertuples():
            v = np.array(betas[r.variable])
            self.assertAlmostEqual(r.coef_estandarizado_medio, v.mean(), places=12)
            self.assertAlmostEqual(r.coef_estandarizado_sd, v.std(), places=12)
            self.assertAlmostEqual(r.fraccion_positiva, (v > 0).mean(), places=12)
            self.assertEqual(r.n_contextos_con_coeficiente, len(v))
        self.assertTrue(((t.fraccion_mismo_signo >= 0.5) & (t.fraccion_mismo_signo <= 1)).all())

    def test_pendiente_municipal_es_beta_mas_gamma(self):
        t = ctl.resumen_pendientes(self.modelos, ctl.HET_GP)
        municipales = t[t.fila != 'pendiente_comun']
        self.assertTrue(len(municipales))
        valores = {}
        for (c, rep, fold), (m, sola, _) in self.modelos.items():
            if c != ctl.HET_GP or sola:
                continue
            est = m.estado()
            for g, gam in est['gamma'].items():
                for nombre, b, d in zip(m.nombres_, est['beta'], gam):
                    valores.setdefault((g, nombre), []).append(b + d)
        for r in municipales.itertuples():
            self.assertAlmostEqual(r.coef_estandarizado_medio, np.mean(valores[(r.fila, r.variable)]), places=12)
            self.assertEqual(r.n_contextos_con_coeficiente, len(valores[(r.fila, r.variable)]))

    def test_importancia_gb(self):
        t = ctl.resumen_importancia(self.modelos, ctl.GB_GP)
        n_total = len(CTX_A)
        n_sola = sum(1 for (c, _, _), (_, s, _) in self.modelos.items() if c == ctl.GB_GP and s)
        self.assertTrue((t.n_contextos_total == n_total).all())
        # en cada contexto con corrección las importancias suman 1: la suma por contextos da la fracción con corrección
        self.assertAlmostEqual(t.importancia_media_todos_los_contextos.sum(), (n_total - n_sola) / n_total, places=9)
        self.assertTrue((t.importancia_media_todos_los_contextos <= t.importancia_media_donde_existe + 1e-15).all())
        self.assertTrue(t.importancia_media_todos_los_contextos.is_monotonic_decreasing)
        self.assertTrue((t.n_contextos_con_la_variable <= n_total - n_sola).all())
        acumulado = {}
        for (c, rep, fold), (m, sola, _) in self.modelos.items():
            if c == ctl.GB_GP and not sola:
                for nombre, v in m.importancias().items():
                    acumulado.setdefault(nombre, []).append(float(v))
        for r in t.itertuples():
            v = acumulado[r.variable]
            self.assertEqual(r.n_contextos_con_la_variable, len(v))
            self.assertAlmostEqual(r.importancia_media_donde_existe, np.mean(v), places=12)
            self.assertAlmostEqual(r.importancia_media_todos_los_contextos, sum(v) / n_total, places=12)
        self.assertTrue((t.n_contextos_con_la_variable < n_total - n_sola).any(),
                        'el ejemplo debe tener variables que no están en todos los contextos')


class Prueba21Parcelas(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.e = entorno()
        cls.tmp = Path(tempfile.mkdtemp())
        cls.e['calidad'].to_csv(cls.tmp / 'c.csv', index=False)
        cls.attr = ctl.atributos(cls.tmp / 'c.csv', pd.DataFrame(cls.e['entradas']['particiones']))
        cls.t = ctl.control_parcelas(cls.e['principal'], cls.e['refs_df'], cls.attr, n=6)['parcelas_extremas_t12.csv']

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_recalculado_aparte(self):
        a = A(self.e['principal'], ctl.HET_GP)
        r = A(self.e['refs_df'], REF)
        m = a.merge(r, on=['repeticion', 'ID_POLIGONO'], suffixes=('', '_r'))
        g = m.groupby('ID_POLIGONO').agg(real=('real', 'mean'), p=('prediccion', 'mean'), r=('prediccion_r', 'mean'))
        g['d'] = (g.p - g.real).abs() - (g.r - g.real).abs()
        mejora = g.sort_values('d').head(6)
        empeora = g.sort_values('d', ascending=False).head(6)
        t = self.t
        self.assertEqual(list(t[t.grupo == 'mejora'].ID_POLIGONO), list(mejora.index))
        self.assertEqual(list(t[t.grupo == 'empeora'].ID_POLIGONO), list(empeora.index))
        for fila in t.itertuples():
            esperado = g.loc[fila.ID_POLIGONO]
            self.assertAlmostEqual(fila.d_error_abs, esperado.d, places=12)
            self.assertAlmostEqual(fila.prediccion_media, esperado.p, places=12)
            self.assertAlmostEqual(fila.referencia_media, esperado.r, places=12)
            self.assertAlmostEqual(fila.real, esperado.real, places=12)
            self.assertEqual(fila.n_repeticiones, int((m.ID_POLIGONO == fila.ID_POLIGONO).sum()))
            self.assertEqual(fila.municipio, self.attr.loc[fila.ID_POLIGONO, 'municipio'])

    def test_orden_y_rangos(self):
        t = self.t
        self.assertEqual(len(t), 12)
        self.assertEqual(len(set(t.ID_POLIGONO)), 12)
        self.assertTrue(t[t.grupo == 'mejora'].d_error_abs.is_monotonic_increasing)
        self.assertTrue(t[t.grupo == 'empeora'].d_error_abs.is_monotonic_decreasing)
        self.assertEqual(list(t[t.grupo == 'mejora'].rango), [1, 2, 3, 4, 5, 6])
        self.assertLess(t[t.grupo == 'mejora'].d_error_abs.max(), t[t.grupo == 'empeora'].d_error_abs.min())
        self.assertTrue(t.n_repeticiones.between(1, 5).all())

    def test_con_pocas_parcelas_no_se_repite_ninguna(self):
        pocas = ctl.control_parcelas(self.e['principal'], self.e['refs_df'], self.attr, n=500)['parcelas_extremas_t12.csv']
        self.assertEqual(len(pocas), 76)
        self.assertEqual(len(set(pocas.ID_POLIGONO)), 76)


def copiar_codigo(destino):
    for f in ev.CODIGO + ('scripts/t12_controles.py',):
        (destino / f).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(Path(t12.RAIZ) / f, destino / f)


def escribir_paso4(raiz, e):
    """Corre el paso 4 con los datos inventados y deja sus archivos en raiz/registro/t12."""
    salida = raiz / 'registro/t12'
    with patch.object(ev, 'compuertas', lambda r, c: (e['cfg'], {})), \
            patch.object(ev, 'evaluar_todos', lambda *a, **k: (e['oof_lista'], e['sel_lista'])), \
            patch.object(ev, 'preparar_salida', lambda s, r: salida), \
            patch.object(v3, 'cargar_entradas', lambda r: e['entradas']), \
            patch.object(ev, 'cargar_referencias', lambda r: e['refs']), \
            patch.object(ev, 'N_ETIQUETADAS', 76), patch.object(ev, 'N_RESERVADAS', 12), \
            patch.object(ev, 'CONTEXTOS', CTX_SUB), patch('builtins.print'):
        ev.ejecutar('x', confirmo_barreras=True)
    (raiz / 'registro/t07').mkdir(parents=True, exist_ok=True)
    e['calidad'].to_csv(raiz / ctl.CALIDAD, index=False)


class Prueba22Compuertas(unittest.TestCase):
    """Los controles sólo corren sobre la evaluación principal íntegra y con el código comprobado."""

    @classmethod
    def setUpClass(cls):
        cls.real = Path(t12.RAIZ)
        if not (cls.real / t12.SALIDA_COMPROBACIONES).exists():
            raise unittest.SkipTest('Todavía no existe registro/t12/comprobaciones.json')
        cls.e = entorno()
        cls.base = Path(tempfile.mkdtemp())
        escribir_paso4(cls.base, cls.e)
        c = json.loads((cls.real / t12.SALIDA_COMPROBACIONES).read_text())
        m = json.loads((cls.base / 'registro/t12/manifest.json').read_text())
        for f in [t12.DISENO, t12.SALIDA_COMPROBACIONES, *c['codigo_sha256'], *c['fuentes_sha256'],
                  *m['codigo_sha256'], *m['entradas_sha256']]:
            (cls.base / f).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(cls.real / f, cls.base / f)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(getattr(cls, 'base', '/nonexistent'), ignore_errors=True)

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        shutil.copytree(self.base, self.tmp / 'r', dirs_exist_ok=True)
        self.r = self.tmp / 'r'

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def agregar(self, ruta, texto=' '):
        p = self.r / ruta
        p.write_text(p.read_text() + texto)

    def test_pasa_cuando_todo_coincide(self):
        cfg, m = ctl.compuertas(self.r)
        self.assertEqual(len(cfg['procedimientos']), 8)
        self.assertTrue(m['barreras_confirmadas_por_la_persona'])

    def test_se_detiene_si_se_modifica_cualquier_salida_principal(self):
        for nombre in ctl.PRINCIPALES:
            with self.subTest(nombre=nombre):
                shutil.copytree(self.base, self.tmp / 'x', dirs_exist_ok=True)
                p = self.tmp / 'x/registro/t12' / nombre
                p.write_text(p.read_text() + '\n')
                with self.assertRaises(ValueError):
                    ctl.compuertas(self.tmp / 'x')
                shutil.rmtree(self.tmp / 'x')

    def test_se_detiene_sin_manifest_o_con_manifest_ajeno(self):
        (self.r / 'registro/t12/manifest.json').unlink()
        with self.assertRaises(ValueError):
            ctl.compuertas(self.r)

    def test_se_detiene_si_el_manifest_no_tiene_las_barreras_confirmadas(self):
        for campo, valor in (('barreras_confirmadas_por_la_persona', False), ('schema', 'otro'),
                             ('sha_diseno_t12', '0' * 64), ('sha_comprobaciones', '0' * 64)):
            with self.subTest(campo=campo):
                shutil.copytree(self.base, self.tmp / 'x', dirs_exist_ok=True)
                p = self.tmp / 'x/registro/t12/manifest.json'
                d = json.loads(p.read_text())
                d[campo] = valor
                p.write_text(json.dumps(d))
                with self.assertRaises(ValueError):
                    ctl.compuertas(self.tmp / 'x')
                shutil.rmtree(self.tmp / 'x')

    def test_se_detiene_si_cambia_el_codigo_o_una_entrada_despues_de_la_evaluacion(self):
        for archivo in ('scripts/t12_heterogeneidad.py', 'scripts/t12_evaluar.py',
                        'scripts/evaluacion_comun_reportes.py'):
            with self.subTest(archivo=archivo):
                shutil.copytree(self.base, self.tmp / 'x', dirs_exist_ok=True)
                p = self.tmp / 'x' / archivo
                p.write_text(p.read_text() + '\n# cambio\n')
                with self.assertRaises(ValueError):
                    ctl.compuertas(self.tmp / 'x')
                shutil.rmtree(self.tmp / 'x')

    def test_el_codigo_que_solo_conoce_el_manifest_tambien_se_vigila(self):
        """t12_evaluar.py y reportes no están en las comprobaciones del paso 3: sólo este control los vigila."""
        c = json.loads((self.r / t12.SALIDA_COMPROBACIONES).read_text())
        self.assertNotIn('scripts/t12_evaluar.py', c['codigo_sha256'])
        self.agregar('scripts/t12_evaluar.py', '\n# cambio\n')
        ev.compuertas(self.r, True)                                  # las comprobaciones no lo notan
        with self.assertRaises(ValueError):
            ctl.compuertas(self.r)

    def test_se_detiene_si_cambia_una_entrada(self):
        self.agregar('registro/t07/tabla_comun.csv', '\n')
        with self.assertRaises(ValueError):
            ctl.compuertas(self.r)

    def test_control_desconocido(self):
        with self.assertRaises(ValueError):
            ctl.compuertas(self.r, ('C9',))

    def test_salida_solo_en_registro_t12_o_reports_y_sin_sobrescribir(self):
        ctl.preparar_salida('registro/t12', self.r, ctl.ORDEN)
        ctl.preparar_salida('reports/t12_repro', self.r, ctl.ORDEN)
        for fuera in ('registro/t03', 'scripts', '/tmp/otra', 'registro/t12/../t03'):
            with self.subTest(fuera=fuera), self.assertRaises(ValueError):
                ctl.preparar_salida(fuera, self.r, ctl.ORDEN)
        (self.r / 'registro/t12/desglose_error_t12.csv').write_text('x')
        with self.assertRaises(ValueError):
            ctl.preparar_salida('registro/t12', self.r, ('C4',))
        ctl.preparar_salida('registro/t12', self.r, ('C6',))         # otro control: no choca
        (self.r / 'registro/t12' / ctl.MANIFEST).write_text(json.dumps({'controles': {'C6': {}}}))
        with self.assertRaises(ValueError):
            ctl.preparar_salida('registro/t12', self.r, ('C6',))


class Prueba23Ejecucion(unittest.TestCase):
    """Las tuberías completas con datos inventados: archivos, manifest, sin sobrescribir ni dejar parciales."""

    @classmethod
    def setUpClass(cls):
        cls.e = entorno()
        cls.paso4 = Path(tempfile.mkdtemp())
        escribir_paso4(cls.paso4, cls.e)
        copiar_codigo(cls.paso4)
        cls.completo = cls.nuevo()
        with cls.parches(), patch('builtins.print'):
            ctl.ejecutar('registro/t12', cls.completo, ctl.ORDEN, 1, CTX_A, 2, (0.5,), (1,))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.paso4, ignore_errors=True)
        shutil.rmtree(cls.completo.parent, ignore_errors=True)

    @classmethod
    def nuevo(cls):
        d = Path(tempfile.mkdtemp())
        shutil.copytree(cls.paso4, d / 'r')
        return d / 'r'

    @classmethod
    def parches(cls):
        from contextlib import ExitStack
        pila = ExitStack()
        pila.enter_context(patch.object(ctl, 'compuertas', lambda raiz, solo=ctl.ORDEN: (cls.e['cfg'], {})))
        pila.enter_context(patch.object(v3, 'cargar_entradas', lambda raiz: cls.e['entradas']))
        pila.enter_context(patch.object(ctl, 'referencias_df', lambda raiz: cls.e['refs_df']))
        return pila

    def test_todos_los_archivos_y_el_manifest(self):
        carpeta = self.completo / 'registro/t12'
        m = json.loads((carpeta / ctl.MANIFEST).read_text())
        self.assertEqual(set(m['controles']), set(ctl.ARCHIVOS))
        for c, info in m['controles'].items():
            self.assertEqual(set(info['archivos_sha256']), set(ctl.ARCHIVOS[c]))
            for nombre, huella in info['archivos_sha256'].items():
                self.assertEqual(ctl.sha(carpeta / nombre), huella)
            self.assertIn('scripts/t12_controles.py', info['codigo_sha256'])
        # el paso 4 sigue intacto
        p = json.loads((carpeta / 'manifest.json').read_text())
        for n, h in p['salidas_sha256'].items():
            self.assertEqual(ctl.sha(carpeta / n), h)

    def test_el_p_del_revuelto_usa_el_observado_de_la_tabla_principal(self):
        t = pd.read_csv(self.completo / 'registro/t12/control_revuelto_t12.csv')
        c = pd.read_csv(self.completo / 'registro/t12/comparacion_emparejada_t12.csv')
        obs = float(c[c.aplica_promocion].iloc[0].dMAE)
        self.assertTrue(np.allclose(t.dMAE_observado, obs, rtol=0, atol=1e-12))
        self.assertEqual(len(t), 2)
        self.assertTrue(((t.p * (t.n_permutaciones + 1)).round() == t.b + 1).all())

    def test_las_otras_tablas_tienen_lo_esperado(self):
        carpeta = self.completo / 'registro/t12'
        self.assertEqual(set(pd.read_csv(carpeta / 'curva_aprendizaje_t12.csv').fraccion), {0.5, 1.0})
        self.assertEqual(len(pd.read_csv(carpeta / 'parcelas_extremas_t12.csv')), 2 * ctl.N_EXTREMAS)
        self.assertEqual(set(pd.read_csv(carpeta / 'pendientes_por_municipio_t12.csv').candidato),
                         {ctl.HET_GP, ctl.HET_G})
        self.assertEqual(set(pd.read_csv(carpeta / 'desglose_error_t12.csv').desglose), set(ctl.CORTES))

    def test_no_se_sobrescribe_nada(self):
        carpeta = self.completo / 'registro/t12'
        antes = {p.name: ctl.sha(p) for p in carpeta.iterdir()}
        with self.parches(), patch('builtins.print'), self.assertRaises(ValueError):
            ctl.ejecutar('registro/t12', self.completo, ('C6',), 1, CTX_A)
        self.assertEqual(antes, {p.name: ctl.sha(p) for p in carpeta.iterdir()})

    def test_si_un_control_falla_se_conservan_los_terminados_y_no_queda_nada_a_medias(self):
        raiz = self.nuevo()
        carpeta = raiz / 'registro/t12'
        with self.parches(), patch('builtins.print'), \
                patch.object(ctl, 'control_parcelas', side_effect=RuntimeError('falla')), \
                self.assertRaises(RuntimeError):
            ctl.ejecutar('registro/t12', raiz, ('C4', 'C6'), 1, CTX_A)
        m = json.loads((carpeta / ctl.MANIFEST).read_text())
        self.assertEqual(set(m['controles']), {'C4'})                # C4 va primero y terminó
        self.assertTrue((carpeta / 'desglose_error_t12.csv').exists())
        self.assertFalse((carpeta / 'parcelas_extremas_t12.csv').exists())
        # se repite sólo el que falló
        with self.parches(), patch('builtins.print'):
            ctl.ejecutar('registro/t12', raiz, ('C6',), 1, CTX_A)
        m = json.loads((carpeta / ctl.MANIFEST).read_text())
        self.assertEqual(set(m['controles']), {'C4', 'C6'})

    def test_si_una_tabla_ya_existe_no_se_calcula_nada(self):
        raiz = self.nuevo()
        (raiz / 'registro/t12/parcelas_extremas_t12.csv').write_text('previo')
        with self.parches(), patch('builtins.print'), patch.object(ctl, 'control_desgloses') as c4, \
                self.assertRaises(ValueError):
            ctl.ejecutar('registro/t12', raiz, ('C4', 'C6'), 1, CTX_A)
        c4.assert_not_called()

    def test_orden_rapido_primero(self):
        self.assertEqual(ctl.ORDEN, ('C4', 'C6', 'C5', 'C3', 'C2'))
        self.assertEqual(set(ctl.ORDEN), set(ctl.ARCHIVOS))

    def test_main_exige_controles_y_pasa_los_argumentos(self):
        llamadas = []
        with patch.object(ctl, 'ejecutar', lambda *a: llamadas.append(a) or Path('x')), patch('builtins.print'):
            with self.assertRaises(ValueError):
                ctl.main([])
            ctl.main(['--controles', '--solo', 'C4', 'C6', '--procesos', '3'])
        self.assertEqual(llamadas[0][2:], (['C4', 'C6'], 3))
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            ctl.main(['--controles', '--solo', 'C9'])


if __name__ == '__main__':
    unittest.main()
