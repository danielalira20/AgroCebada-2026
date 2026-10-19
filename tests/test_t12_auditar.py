"""Pruebas del auditor independiente de T12 (paso 6) con datos INVENTADOS.

Se fabrica un árbol mínimo del proyecto (tabla, particiones, referencias de T03, diseño y las salidas del paso 4 y
del paso 5 hechas con el código de producción) y se comprueba que el auditor, que no importa ese código, lo
reproduce; y que detecta cada alteración de las salidas.
"""
import ast
import io
import csv
import json
import shutil
import tempfile
import unittest
from contextlib import ExitStack, redirect_stdout
from pathlib import Path
from unittest.mock import patch

import numpy as np

from scripts import evaluacion_comun_centrado_loo as v3
from scripts import evaluacion_comun_reportes as comun
from scripts import t12_auditar as aud
from scripts import t12_controles as ctl
from scripts import t12_heterogeneidad as t12
from tests.test_t12_controles import CTX_A, copiar_codigo, entorno, escribir_paso4
from tests.test_t12_evaluar import CTX_SUB

N_CONTEXTOS = len(CTX_SUB)
AUDITAR_REAL = aud.auditar


def escribir_csv(ruta, filas):
    ruta.parent.mkdir(parents=True, exist_ok=True)
    cab = list(filas[0])
    with open(ruta, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=cab, lineterminator='\n')
        w.writeheader()
        w.writerows(filas)


def leer(ruta):
    with open(ruta, newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def reescribir(ruta, cambio):
    filas = leer(ruta)
    cambio(filas)
    escribir_csv(ruta, filas)


def construir_arbol(e):
    """Árbol de proyecto inventado con las salidas de los pasos 4 y 5 hechas por el código de producción."""
    raiz = Path(tempfile.mkdtemp()) / 'r'
    raiz.mkdir()
    copiar_codigo(raiz)
    escribir_paso4(raiz, e)
    entradas = e['entradas']
    escribir_csv(raiz / 'registro/t07/tabla_comun.csv', list(entradas['tabla'].values()))
    escribir_csv(raiz / 'registro/t03/particiones.csv', entradas['particiones'])
    for nombre, ruta in aud.REFERENCIAS_T03.items():
        escribir_csv(raiz / ruta, [r for r in e['refs'] if r['candidato'] == nombre])
    (raiz / 'registro/t12/procedimiento_t12.json').write_text(json.dumps(e['cfg']), encoding='utf-8')
    # el manifest del paso 4 se hizo con los archivos reales; aquí apunta a los inventados
    ruta = raiz / 'registro/t12/manifest.json'
    m = json.loads(ruta.read_text())
    m['sha_diseno_t12'] = aud.sha(raiz / 'registro/t12/procedimiento_t12.json')
    m['entradas_sha256'] = {r: aud.sha(raiz / r) for r in ('registro/t07/tabla_comun.csv', 'registro/t03/particiones.csv',
                                                          *aud.REFERENCIAS_T03.values())}
    ruta.write_text(json.dumps(m))
    # paso 5
    with ExitStack() as pila:
        pila.enter_context(patch.object(ctl, 'compuertas', lambda r, solo=ctl.ORDEN: (e['cfg'], {})))
        pila.enter_context(patch.object(v3, 'cargar_entradas', lambda r: entradas))
        pila.enter_context(patch.object(ctl, 'referencias_df', lambda r: e['refs_df']))
        pila.enter_context(patch('builtins.print'))
        ctl.ejecutar('registro/t12', raiz, ctl.ORDEN, 1, CTX_A, 2, (0.5,), (1,))
    return raiz


def auditar(raiz, **kw):
    kw.setdefault('esperados', N_CONTEXTOS)
    kw.setdefault('controles', True)
    return AUDITAR_REAL(raiz, 'registro/t12', **kw)


class PruebaAuditor(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.e = entorno()
        cls.base = construir_arbol(cls.e)
        cls.informe, cls.detalle, _ = auditar(cls.base)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.base.parent, ignore_errors=True)

    def copia(self):
        d = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        shutil.copytree(self.base, d / 'r', ignore=shutil.ignore_patterns(aud.SALIDA))
        return d / 'r'

    # ------------------------------------------------------------ la auditoría limpia
    def test_aprueba_las_salidas_hechas_por_la_produccion(self):
        i = self.informe
        self.assertTrue(i['aprobado'], json.dumps(i, indent=1, default=str)[:3000])
        for parte in ('integridad_oof', 'ajustes_het', 'metricas', 'comparaciones', 'controles'):
            self.assertTrue(i[parte]['aprobado'], parte)

    def test_las_diferencias_son_las_del_orden_de_redondeo(self):
        h = self.informe['ajustes_het']
        self.assertLess(h['dif_max_prediccion'], aud.TOL_PREDICCION)
        self.assertLess(h['dif_max_MAE_interno'], aud.TOL_MAE_INTERNO)
        self.assertLessEqual(self.informe['metricas']['dif_max'], aud.TOL_METRICA)
        self.assertLessEqual(self.informe['comparaciones']['dif_max'], aud.TOL_METRICA)
        self.assertLessEqual(self.informe['controles']['dif_max'], aud.TOL_METRICA)

    def test_cubre_todo_lo_que_dice_cubrir(self):
        h = self.informe['ajustes_het']
        self.assertEqual(h['procedimientos'], ['t12_control_mediana_het_GP', 't12_het_G', 't12_het_GP', 't12_het_P'])
        self.assertEqual(h['contextos'], N_CONTEXTOS)
        self.assertEqual(h['selecciones_reconstruidas'], 4 * N_CONTEXTOS)
        self.assertEqual(len(self.detalle), 4 * N_CONTEXTOS)
        self.assertEqual(h['predicciones_comparadas'], 4 * len(self.e['entradas']['contextos']))
        self.assertEqual(self.informe['comparaciones']['comparaciones'], 13 * 4)
        self.assertEqual(self.informe['metricas']['filas_comparadas'], 10 * 2 * 2 * 6)
        self.assertEqual(self.informe['controles']['C2']['permutaciones'], 2)

    def test_las_elegidas_incluyen_opciones_y_referencia_sola(self):
        elegidas = {f['opcion_elegida'] for f in self.detalle}
        self.assertIn('referencia_sola', elegidas)
        self.assertTrue(len(elegidas) >= 2)

    def test_no_sobrescribe_ni_toca_las_salidas(self):
        antes = {p.name: aud.sha(p) for p in (self.base / 'registro/t12').iterdir() if p.name != aud.SALIDA}
        with self.assertRaises(ValueError):
            auditar(self.base)
        self.assertEqual(antes, {p.name: aud.sha(p) for p in (self.base / 'registro/t12').iterdir()
                                 if p.name != aud.SALIDA})
        guardado = json.loads((self.base / 'registro/t12' / aud.SALIDA).read_text())
        self.assertTrue(guardado['aprobado'])
        self.assertEqual(guardado['salidas_auditadas_sha256'],
                         {n: aud.sha(self.base / 'registro/t12' / n) for n in aud.PRINCIPALES})

    def test_salida_solo_en_registro_t12_o_reports(self):
        for fuera in ('registro/t03', 'scripts', '/tmp/otra'):
            with self.subTest(fuera=fuera), self.assertRaises(ValueError):
                AUDITAR_REAL(self.base, fuera, esperados=N_CONTEXTOS)

    def test_el_auditor_no_importa_el_codigo_de_produccion(self):
        arbol = ast.parse(Path(aud.__file__).read_text(encoding='utf-8'))
        modulos = set()
        for n in ast.walk(arbol):
            if isinstance(n, ast.Import):
                modulos |= {a.name for a in n.names}
            elif isinstance(n, ast.ImportFrom):
                modulos.add(n.module)
        self.assertFalse({m for m in modulos if m.startswith('scripts') or m.startswith('pandas')}, modulos)
        self.assertEqual(sorted(m for m in modulos if m.startswith('sklearn')), ['sklearn', 'sklearn.model_selection'])

    def test_exige_el_numero_de_contextos_esperado(self):
        with self.assertRaises(ValueError):
            AUDITAR_REAL(self.copia(), 'registro/t12', esperados=50)

    # ------------------------------------------------------------ detecta alteraciones
    def alterar(self, archivo, cambio, **kw):
        raiz = self.copia()
        reescribir(raiz / 'registro/t12' / archivo, cambio)
        informe, _, _ = auditar(raiz, verificar_huellas=False, **kw)
        return informe

    def test_detecta_una_prediccion_alterada(self):
        def cambio(filas):
            f = next(r for r in filas if r['candidato'] == 't12_het_GP' and r['escenario'] == 'A')
            f['prediccion'] = repr(float(f['prediccion']) + 1e-6)
        i = self.alterar('predicciones_oof_t12.csv', cambio)
        self.assertFalse(i['ajustes_het']['aprobado'])
        self.assertFalse(i['aprobado'])

    def test_una_prediccion_alterada_de_un_procedimiento_que_no_es_het_no_cae_en_het(self):
        def cambio(filas):
            f = next(r for r in filas if r['candidato'] == 't12_gb_GP' and r['escenario'] == 'A')
            f['prediccion'] = repr(float(f['prediccion']) + 1e-6)
        i = self.alterar('predicciones_oof_t12.csv', cambio)
        self.assertTrue(i['ajustes_het']['aprobado'])
        self.assertFalse(i['metricas']['aprobado'])

    def test_detecta_una_etiqueta_alterada(self):
        def cambio(filas):
            f = next(r for r in filas if r['candidato'] == 't12_het_G')
            f['real'] = repr(float(f['real']) + 0.01)
        i = self.alterar('predicciones_oof_t12.csv', cambio)
        self.assertFalse(i['integridad_oof']['aprobado'])

    def test_detecta_una_metrica_alterada(self):
        def cambio(filas):
            f = next(r for r in filas if r['candidato'] == 't12_het_GP' and r['repeticion'] == '3')
            f['MAE'] = repr(float(f['MAE']) + 1e-9)
        i = self.alterar('metricas_t12.csv', cambio)
        self.assertFalse(i['metricas']['aprobado'])
        self.assertTrue(i['ajustes_het']['aprobado'])

    def test_detecta_una_comparacion_alterada(self):
        for campo in ('IC95_MAE_sup', 'dMAE', 'dRMSE', 'dMAE_rep2', 'IC95_RMSE_inf'):
            with self.subTest(campo=campo):
                def cambio(filas, campo=campo):
                    filas[5][campo] = repr(float(filas[5][campo]) + 1e-9)
                i = self.alterar('comparacion_emparejada_t12.csv', cambio)
                self.assertFalse(i['comparaciones']['aprobado'])

    def test_detecta_promocion_mal_marcada_o_regla_distinta(self):
        def marca(filas):
            for r in filas:
                r['aplica_promocion'] = 'True' if r['candidato'] == 't12_het_G' and r['escenario'] == 'A' and \
                    r['subconjunto'] == 'sin_respaldo' and r['frente_a'] == ctl.REFERENCIA else 'False'
        self.assertFalse(self.alterar('comparacion_emparejada_t12.csv', marca)['comparaciones']['aprobado'])

        def regla(filas):
            filas[0]['cumple_regla_T03'] = 'True' if filas[0]['cumple_regla_T03'] == 'False' else 'False'
        self.assertFalse(self.alterar('comparacion_emparejada_t12.csv', regla)['comparaciones']['aprobado'])

    def test_detecta_una_comparacion_que_falta(self):
        i = self.alterar('comparacion_emparejada_t12.csv', lambda filas: filas.pop())
        self.assertFalse(i['comparaciones']['aprobado'])

    def test_detecta_una_seleccion_alterada(self):
        def intercambio(filas):
            g = [r for r in filas if r['candidato'] == 't12_het_GP' and r['escenario'] == 'A' and
                 r['repeticion'] == '1' and r['particion'] == '0']
            actual = next(r for r in g if r['elegida'] == 'True')
            otro = next(r for r in g if r['elegida'] == 'False')
            actual['elegida'], otro['elegida'] = 'False', 'True'
        i = self.alterar('seleccion_interna_t12.csv', intercambio)
        self.assertFalse(i['ajustes_het']['aprobado'])

    def test_detecta_un_mae_interno_o_una_lista_de_municipios_alterados(self):
        def mae(filas):
            filas[3]['MAE_interno'] = repr(float(filas[3]['MAE_interno']) + 1e-6)
        self.assertFalse(self.alterar('seleccion_interna_t12.csv', mae)['ajustes_het']['aprobado'])

        def grupos(filas):
            f = next(r for r in filas if r['candidato'] == 't12_het_P' and r['municipios_con_pendiente_propia'])
            f['municipios_con_pendiente_propia'] = ''
        self.assertFalse(self.alterar('seleccion_interna_t12.csv', grupos)['ajustes_het']['aprobado'])

        def conteo(filas):
            filas[5]['n_elegibles'] = str(int(filas[5]['n_elegibles']) + 1)
        self.assertFalse(self.alterar('seleccion_interna_t12.csv', conteo)['ajustes_het']['aprobado'])

    def test_detecta_controles_alterados(self):
        casos = {
            'parcelas_extremas_t12.csv': lambda f: f.reverse(),
            'control_revuelto_t12.csv': lambda f: f[0].__setitem__('p', '0.001'),
            'curva_aprendizaje_t12.csv': lambda f: next(
                r for r in f if r['semilla'] == 'completo' and r['procedimiento'] == t12_het).__setitem__('MAE', '9.9'),
            'desglose_error_t12.csv': lambda f: next(
                r for r in f if r['desglose'] == 'municipio').__setitem__('MAE', '9.9'),
            'sensibilidad_sin_alerta_t12.csv': lambda f: f[1].__setitem__('MAE_sin_alerta', '9.9'),
        }
        t12_het = 't12_het_GP'
        for archivo, cambio in casos.items():
            with self.subTest(archivo=archivo):
                raiz = self.copia()
                reescribir(raiz / 'registro/t12' / archivo, cambio)
                m = json.loads((raiz / 'registro/t12' / ctl.MANIFEST).read_text())
                for c in m['controles'].values():                       # que no lo atrape sólo la huella
                    for n in c['archivos_sha256']:
                        c['archivos_sha256'][n] = aud.sha(raiz / 'registro/t12' / n)
                (raiz / 'registro/t12' / ctl.MANIFEST).write_text(json.dumps(m))
                informe, _, _ = auditar(raiz, verificar_huellas=False)
                self.assertFalse(informe['controles']['aprobado'])
                self.assertFalse(informe['aprobado'])

    def test_con_las_huellas_activas_cualquier_cambio_detiene_antes_de_auditar(self):
        for archivo in aud.PRINCIPALES:
            with self.subTest(archivo=archivo):
                raiz = self.copia()
                ruta = raiz / 'registro/t12' / archivo
                ruta.write_text(ruta.read_text() + '\n')
                with self.assertRaises(ValueError):
                    auditar(raiz)
        raiz = self.copia()
        (raiz / 'registro/t07/tabla_comun.csv').write_text(
            (raiz / 'registro/t07/tabla_comun.csv').read_text() + '\n')
        with self.assertRaises(ValueError):
            auditar(raiz)
        raiz = self.copia()
        d = raiz / 'registro/t12/procedimiento_t12.json'
        d.write_text(d.read_text() + ' ')
        with self.assertRaises(ValueError):
            auditar(raiz)

    def test_un_control_modificado_despues_de_generarse_se_detecta(self):
        raiz = self.copia()
        ruta = raiz / 'registro/t12/parcelas_extremas_t12.csv'
        ruta.write_text(ruta.read_text() + '\n')
        informe, _, _ = auditar(raiz)
        self.assertFalse(informe['controles']['aprobado'])

    def test_main_devuelve_cero_si_aprueba_y_uno_si_no(self):
        raiz = self.copia()
        with patch.object(aud, 'N_CONTEXTOS_ESPERADOS', N_CONTEXTOS), \
                patch.object(aud, 'auditar', lambda *a, **k: auditar(raiz, verificar_huellas=False)), \
                redirect_stdout(io.StringIO()):
            self.assertEqual(aud.main(['--raiz', str(raiz), '--controles']), 0)
        raiz2 = self.copia()
        reescribir(raiz2 / 'registro/t12/metricas_t12.csv', lambda f: f[0].__setitem__('MAE', '9'))
        with patch.object(aud, 'auditar', lambda *a, **k: auditar(raiz2, verificar_huellas=False)), \
                redirect_stdout(io.StringIO()):
            self.assertEqual(aud.main(['--raiz', str(raiz2)]), 1)


class PruebaPrimitivas(unittest.TestCase):
    """Piezas del auditor contra casos hechos a mano y contra los estadísticos de T15."""

    def test_pools_sin_fila(self):
        mun = np.array(['a', 'a', 'b', 'c'])
        grp = np.array(['G', 'G', 'G', 'H'])
        p = aud.pools_sin_fila(mun, grp)
        self.assertEqual([list(x) for x in p], [[1], [0], [0, 1], [0, 1, 2]])
        # b es única en su municipio: respaldo del grupo; c es única en municipio y grupo: todas las demás

    def test_crudo_log_area_imputa_con_mediana_y_agrega_indicador_al_final(self):
        class D:
            fila = {'1': {'area_ha_origen': '1', 'pendiente_media_t10_grados': '10'},
                    '2': {'area_ha_origen': str(np.e), 'pendiente_media_t10_grados': ''},
                    '3': {'area_ha_origen': '1', 'pendiente_media_t10_grados': '30'}}
        cols = ['area_ha_origen', 'pendiente_media_t10_grados']
        v, med = aud.crudo(D, ['1', '2', '3'], cols)
        self.assertEqual(med, 20.0)
        np.testing.assert_allclose(v, [[0, 10, 0], [1, 20, 1], [0, 30, 0]])
        v2, _ = aud.crudo(D, ['2'], cols, mediana_pendiente=5.0)
        np.testing.assert_allclose(v2, [[1, 5, 1]])

    def test_desempate_registrado(self):
        base = dict(MAE=0.3, referencia_sola=False, lambda_reg=1.0, kappa=1.0, ventana='abr_oct', nombre='b')
        mejor = lambda **kw: min([base, dict(base, **kw)], key=aud.clave_desempate)
        self.assertEqual(mejor(MAE=0.2999)['MAE'], 0.2999)
        self.assertEqual(mejor(MAE=0.3000004, nombre='a')['nombre'], 'a')    # empate a 6 decimales: decide el nombre
        self.assertEqual(mejor(MAE=0.300002, nombre='a')['nombre'], 'b')     # 6 decimales distintos: decide el MAE
        self.assertTrue(mejor(MAE=0.3000004, referencia_sola=True, lambda_reg=None, kappa=None)['referencia_sola'])
        self.assertEqual(mejor(lambda_reg=10.0)['lambda_reg'], 10.0)
        self.assertEqual(mejor(kappa=10.0)['kappa'], 10.0)
        self.assertEqual(mejor(ventana='jun_oct')['ventana'], 'jun_oct')
        self.assertEqual(mejor(nombre='a')['nombre'], 'a')

    def test_comparar_coincide_con_comparar_de_T15(self):
        e = entorno()
        filas = list(e['refs']) + e['principal'].to_dict('records')
        oof = {}
        for r in filas:
            oof.setdefault(r['candidato'], {})[(r['escenario'], int(r['repeticion']), r['ID_POLIGONO'])] = (
                float(r['real']), float(r['prediccion']), r['fuente'], int(r['particion']))
        celdas = {r['ID_POLIGONO']: r['celda_chirps'] for r in e['entradas']['particiones'] if r['repeticion'] == '1'}
        for cand, base, esc, sub in (('t12_het_GP', ctl.REFERENCIA, 'A', 'sin_respaldo'),
                                     ('t12_gb_GP', ctl.REFERENCIA, 'B', 'todas'),
                                     ('t12_het_GP', 't12_control_comun_GP', 'A', 'todas')):
            mio = aud.comparar(oof, ctl.REFERENCIA, celdas, cand, base, esc, sub)
            t15 = comun.comparar(filas, e['entradas']['contextos'], cand, base, esc, sub)
            for k in ('dMAE', 'dRMSE', 'diferencia_MAE_media_por_repeticion', 'repeticiones_mejoran_MAE',
                      'n_parcelas', 'n_predicciones', 'n_celdas', 'cumple_regla_T03'):
                self.assertEqual(round(float(mio[k]), 12), round(float(t15[k]), 12), k)
            np.testing.assert_allclose([mio['IC95_MAE_inf'], mio['IC95_MAE_sup']], t15['IC95_celdas_MAE'], atol=1e-12)
            np.testing.assert_allclose([mio['IC95_RMSE_inf'], mio['IC95_RMSE_sup']], t15['IC95_celdas_RMSE'],
                                       atol=1e-12)
            np.testing.assert_allclose([mio[f'dMAE_rep{i}'] for i in range(1, 6)], t15['dMAE_por_repeticion'],
                                       atol=1e-12)

    def test_orden_de_desempate_igual_al_de_produccion_cuando_kappa_no_importa(self):
        """Sin municipios con pendiente propia κ no cambia nada: las opciones empatan y decide el desempate."""
        e = entorno()
        raiz = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, raiz, ignore_errors=True)
        escribir_csv(raiz / 'registro/t07/tabla_comun.csv', list(e['entradas']['tabla'].values()))
        escribir_csv(raiz / 'registro/t03/particiones.csv', e['entradas']['particiones'])
        datos = aud.Datos(raiz)
        tr, y, _ = v3.preparar_contexto(e['entradas'], 'A', 1, 2)
        cols = e['cfg']['procedimientos'][0]['opciones'][0]['columnas']
        ops = [dict(nombre=n, columnas=cols, ventana=v, lambda_reg=lam, kappa=k)
               for n, v, lam, k in (('a_k1', 'abr_oct', 1.0, 1.0), ('b_k10', 'abr_oct', 1.0, 10.0),
                                    ('c_jun_k1', 'jun_oct', 1.0, 1.0), ('d_l10', 'abr_oct', 10.0, 1.0))]
        entren, _, celda = datos.contexto('A', 1, 2)
        prod = t12.seleccionar_familia(tr, y, [dict(o) for o in ops], 'A', 'het', 'media', grupos_pendiente=())
        mio = aud.reconstruir_seleccion(datos, entren, 'A', celda, ops, ctl.REFERENCIA, grupos=())
        por_nombre = {p['nombre']: p['MAE'] for p in prod['puntuaciones']}
        self.assertEqual(por_nombre['a_k1'], por_nombre['b_k10'])          # κ no importa sin pendientes propias
        orden_prod = [p['nombre'] for p in sorted(prod['puntuaciones'], key=t12.clave_opcion_het)]
        orden_mio = [p['nombre'] for p in sorted(mio['puntuaciones'], key=aud.clave_desempate)]
        self.assertEqual(orden_prod, orden_mio)
        self.assertEqual(prod['elegida']['nombre'], mio['elegida'])
        for p in prod['puntuaciones']:
            m = next(x for x in mio['puntuaciones'] if x['nombre'] == p['nombre'])
            self.assertAlmostEqual(m['MAE'], p['MAE'], places=10)

    def test_ajuste_numpy_contra_el_de_produccion_con_cada_parametro(self):
        """Mismo contexto, cada λ, κ, referencia y lista de municipios: la ecuación normal coincide con Ridge SVD."""
        e = entorno()
        raiz = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, raiz, ignore_errors=True)
        escribir_csv(raiz / 'registro/t07/tabla_comun.csv', list(e['entradas']['tabla'].values()))
        escribir_csv(raiz / 'registro/t03/particiones.csv', e['entradas']['particiones'])
        datos = aud.Datos(raiz)
        tr, y, te = v3.preparar_contexto(e['entradas'], 'A', 1, 2)
        cols = e['cfg']['procedimientos'][0]['opciones'][0]['columnas']
        entren, evalu, _ = datos.contexto('A', 1, 2)
        self.assertEqual(entren, list(tr.index))
        for referencia, clave in (('media', ctl.REFERENCIA), ('mediana', 'mediana_mun__resp_grupo')):
            for lam in (0.01, 1.0, 10.0):
                for kappa in (1.0, 10.0):
                    grupos = t12.grupos_con_pendiente(tr)
                    prod = t12.CorreccionPendienteMunicipal(cols, lam, kappa, grupos, referencia).fit(tr, y)
                    mio = aud.ajustar(datos, entren, cols, lam, kappa, grupos, clave)
                    pred, fuente = aud.predecir(mio, datos, evalu)
                    d = prod.predict_with_details(te)
                    np.testing.assert_allclose(pred, d.prediccion.to_numpy(), rtol=0, atol=1e-10)
                    self.assertEqual(fuente, list(d.fuente))


if __name__ == '__main__':
    unittest.main()
