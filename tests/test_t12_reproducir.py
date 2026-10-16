"""Pruebas del comparador de reproducciones de T12 (paso 7) con carpetas sintéticas.

No usan etiquetas reales: construyen una "evidencia oficial" mínima (5 CSV + manifest con huellas) y una copia
que se altera de formas concretas para comprobar que el comparador distingue lo que debe distinguir.
"""
import contextlib
import copy
import csv
import hashlib
import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from scripts import t12_reproducir as rep

HUELLAS = {'a': 'a' * 64, 'b': 'b' * 64}


def sha_bytes(ruta):
    return hashlib.sha256(Path(ruta).read_bytes()).hexdigest()


def escribir_csv(ruta, columnas, filas):
    with Path(ruta).open('w', encoding='utf-8', newline='') as f:
        w = csv.writer(f)
        w.writerow(columnas)
        w.writerows(filas)


def tablas_base():
    oof = (['ID_POLIGONO', 'repeticion', 'particion', 'escenario', 'real', 'prediccion', 'candidato', 'version', 'fuente'],
           [[f'AGC_{i:03d}', r, i % 5, e, 3.5 + i / 10, 3.1 + i / 7, c, 'v1', 'municipio']
            for i in range(1, 7) for r in (1, 2) for e in ('A', 'B') for c in ('t12_het_GP', 't12_het_G')])
    sel = (['candidato', 'escenario', 'repeticion', 'particion', 'opcion', 'internas', 'lambda_reg', 'MAE_interno',
            'elegida'],
           [[c, 'A', 1, f, o, 'estratificada', '' if o == 'referencia_sola' else 0.1, 0.3 + k / 100 + f / 1000, el]
            for c in ('t12_het_GP', 't12_het_G') for f in range(5)
            for k, (o, el) in enumerate((('referencia_sola', False), ('jun_oct_l01_k1', True), ('abr_oct_l1_k1', False)))])
    met = (['candidato', 'escenario', 'subconjunto', 'repeticion', 'n', 'MAE', 'RMSE'],
           [[c, 'A', s, r, 138, 0.31 + 0.001 * i, 0.49]
            for i, c in enumerate(('t12_het_GP', 'media_mun__resp_grupo')) for s in ('todas', 'sin_respaldo')
            for r in ('1', '2', 'promedio')])
    com = (['tipo', 'candidato', 'frente_a', 'escenario', 'subconjunto', 'n_parcelas', 'dMAE', 'cumple_regla_T03'],
           [['frente_a_referencia', 't12_het_GP', 'media_mun__resp_grupo', 'A', 'sin_respaldo', 135, -0.0009, False],
            ['C1_ablacion', 't12_het_GP', 't12_control_comun_GP', 'A', 'sin_respaldo', 135, -0.0006, False]])
    p59 = (['candidato', 'ID_POLIGONO', 'municipio', 'prediccion', 'exploratoria'],
           [['t12_het_GP', 'AGC_003', 'Singuilucan', 3.066128, True], ['t12_het_GP', 'AGC_011', 'Chignahuapan', 4.462064, True]])
    return {'predicciones_oof_t12.csv': oof, 'seleccion_interna_t12.csv': sel, 'metricas_t12.csv': met,
            'comparacion_emparejada_t12.csv': com, 'predicciones_59_t12.csv': p59}


def manifest_base():
    return dict(schema='manifest_t12_evaluacion_v1', version='t12-evaluacion-v1', version_modelos='t12-heterogeneidad-v1',
                sha_diseno_t12='c' * 64, sha_comprobaciones='d' * 64, contextos_externos=50,
                procedimientos=['t12_het_GP', 't12_het_G'], filas_oof=48, ajustes_finales_59=8,
                entradas_sha256=dict(HUELLAS), codigo_sha256=dict(HUELLAS),
                procesos=2, entorno=dict(sistema='Linux', python='3.12.15', numpy='2.2.6', pandas='3.0.6', sklearn='1.9.1'))


def fijar_manifest(carpeta, **cambios):
    """Reescribe el manifest con las huellas reales de los CSV de esa carpeta (como lo haría t12_evaluar)."""
    carpeta = Path(carpeta)
    ruta = carpeta / 'manifest.json'
    m = json.loads(ruta.read_text(encoding='utf-8')) if ruta.exists() else manifest_base()
    m.update(cambios)
    m['salidas_sha256'] = {n: sha_bytes(carpeta / n) for n in rep.CLAVES}
    ruta.write_text(json.dumps(m, indent=2) + '\n', encoding='utf-8')


def crear(carpeta, tablas=None, **cambios_manifest):
    carpeta = Path(carpeta)
    carpeta.mkdir(parents=True, exist_ok=True)
    for nombre, (cols, filas) in (tablas or tablas_base()).items():
        escribir_csv(carpeta / nombre, cols, filas)
    fijar_manifest(carpeta, **cambios_manifest)
    return carpeta


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.raiz = Path(self.tmp.name)
        self.of = crear(self.raiz / 'registro' / 't12')
        self.rp = self.raiz / 'reports' / 't12_repro'

    def copia(self, **kw):
        """Reproducción idéntica; luego cada prueba la altera y llama fijar_manifest."""
        shutil.copytree(self.of, self.rp)
        return self.rp

    def tabla(self, nombre, carpeta=None):
        return rep.leer_tabla((carpeta or self.rp) / nombre)

    def reescribir(self, nombre, cols, filas):
        escribir_csv(self.rp / nombre, cols, filas)
        fijar_manifest(self.rp)

    def comparar(self, **kw):
        return rep.comparar(self.rp, self.raiz, **kw)

    def alterar_celda(self, nombre, indice_fila, columna, valor):
        cols, filas = rep.leer_tabla(self.rp / nombre)
        filas[indice_fila][columna] = valor
        escribir_csv(self.rp / nombre, cols, [[f[c] for c in cols] for f in filas])
        fijar_manifest(self.rp)


class Celdas(unittest.TestCase):
    def test_iguales_y_vacios(self):
        self.assertEqual(rep.comparar_celda('x', 'x'), (True, True, 0.0, 0.0))
        self.assertEqual(rep.comparar_celda('', ''), (True, True, 0.0, 0.0))
        self.assertFalse(rep.comparar_celda('', '0.5')[1])
        self.assertFalse(rep.comparar_celda('0.5', '')[1])

    def test_texto_y_banderas_exactos(self):
        self.assertFalse(rep.comparar_celda('True', 'False')[1])
        self.assertFalse(rep.comparar_celda('jun_oct_l1_k1', 'jun_oct_l10_k1')[1])

    def test_tolerancia_absoluta_en_el_borde(self):
        self.assertTrue(rep.comparar_celda('0', '9e-13')[1])
        self.assertFalse(rep.comparar_celda('0', '2e-12')[1])

    def test_tolerancia_relativa_en_el_borde(self):
        base = 1000.0
        self.assertTrue(rep.comparar_celda(repr(base), repr(base * (1 + 0.9e-10)))[1])
        self.assertFalse(rep.comparar_celda(repr(base), repr(base * (1 + 2e-10)))[1])

    def test_nan_e_infinito(self):
        self.assertTrue(rep.comparar_celda('nan', 'NaN')[1])
        self.assertFalse(rep.comparar_celda('nan', '1.0')[1])
        self.assertFalse(rep.comparar_celda('inf', '1.0')[1])

    def test_mismo_numero_escrito_distinto_cuenta_como_texto_distinto_pero_dentro(self):
        igual, dentro, dif, _ = rep.comparar_celda('0.1', '0.10000000000000001')
        self.assertFalse(igual)
        self.assertTrue(dentro)
        self.assertEqual(dif, 0.0)


class CasosFelices(Base):
    def test_identica_byte_a_byte(self):
        self.copia()
        inf = self.comparar()
        self.assertEqual(inf['resultado'], 'identica_byte_a_byte')
        self.assertTrue(inf['aprobada'])
        self.assertEqual(inf['problemas'], [])
        self.assertEqual(inf['max_dif_abs'], 0.0)
        self.assertTrue(all(t['byte_a_byte'] for t in inf['tablas']))
        self.assertEqual(inf['selecciones']['contextos_con_otra_opcion'], 0)

    def test_ruido_numerico_de_otra_plataforma_pasa(self):
        self.copia()
        self.alterar_celda('predicciones_oof_t12.csv', 3, 'prediccion', repr(float(self.tabla('predicciones_oof_t12.csv')[1][3]['prediccion']) + 3e-15))
        inf = self.comparar()
        self.assertEqual(inf['resultado'], 'reproduce_dentro_de_tolerancia')
        self.assertTrue(inf['aprobada'])
        self.assertGreater(inf['max_dif_abs'], 0)
        self.assertLess(inf['max_dif_abs'], 1e-12)
        t = [x for x in inf['tablas'] if x['archivo'] == 'predicciones_oof_t12.csv'][0]
        self.assertEqual(t['celdas_distintas_en_texto'], 1)
        self.assertEqual(t['celdas_fuera_de_tolerancia'], 0)
        self.assertFalse(t['byte_a_byte'])

    def test_orden_de_filas_distinto_pasa(self):
        self.copia()
        cols, filas = self.tabla('predicciones_oof_t12.csv')
        self.reescribir('predicciones_oof_t12.csv', cols, [[f[c] for c in cols] for f in reversed(filas)])
        inf = self.comparar()
        self.assertTrue(inf['aprobada'])
        self.assertEqual(inf['resultado'], 'reproduce_dentro_de_tolerancia')

    def test_entorno_distinto_solo_informa(self):
        self.copia()
        fijar_manifest(self.rp, entorno=dict(sistema='Darwin', python='3.12.15', numpy='2.2.6', pandas='3.0.6', sklearn='1.9.1'), procesos=1)
        inf = self.comparar(etiqueta='Mac arm64')
        self.assertTrue(inf['aprobada'])
        self.assertEqual(inf['resultado'], 'identica_byte_a_byte')
        self.assertFalse(inf['manifest']['informativos']['entorno']['iguales'])
        self.assertFalse(inf['manifest']['informativos']['procesos']['iguales'])
        self.assertEqual(inf['etiqueta'], 'Mac arm64')
        self.assertIn('entorno distinto', rep.resumen(inf))


class Fallos(Base):
    def test_diferencia_real_no_pasa_y_se_localiza(self):
        self.copia()
        self.alterar_celda('predicciones_oof_t12.csv', 5, 'prediccion', '9.5')
        inf = self.comparar()
        self.assertEqual(inf['resultado'], 'no_reproduce')
        self.assertFalse(inf['aprobada'])
        t = [x for x in inf['tablas'] if x['archivo'] == 'predicciones_oof_t12.csv'][0]
        self.assertEqual(t['celdas_fuera_de_tolerancia'], 1)
        self.assertEqual(t['celdas_fuera_por_columna'], {'prediccion': 1})
        ej = t['ejemplos'][0]
        self.assertEqual(ej['columna'], 'prediccion')
        self.assertEqual(ej['reproduccion'], '9.5')
        self.assertEqual(set(ej['clave']), set(rep.CLAVES['predicciones_oof_t12.csv']))

    def test_diferencia_justo_fuera_de_tolerancia(self):
        self.copia()
        v = float(self.tabla('predicciones_oof_t12.csv')[1][0]['prediccion'])
        self.alterar_celda('predicciones_oof_t12.csv', 0, 'prediccion', repr(v + 5e-9))
        self.assertEqual(self.comparar()['resultado'], 'no_reproduce')

    def test_fila_que_falta(self):
        self.copia()
        cols, filas = self.tabla('metricas_t12.csv')
        self.reescribir('metricas_t12.csv', cols, [[f[c] for c in cols] for f in filas[:-1]])
        inf = self.comparar()
        self.assertEqual(inf['resultado'], 'no_reproduce')
        t = [x for x in inf['tablas'] if x['archivo'] == 'metricas_t12.csv'][0]
        self.assertEqual((t['filas_solo_oficial'], t['filas_solo_reproduccion']), (1, 0))

    def test_fila_de_mas(self):
        self.copia()
        cols, filas = self.tabla('predicciones_59_t12.csv')
        extra = dict(filas[0], ID_POLIGONO='AGC_999')
        self.reescribir('predicciones_59_t12.csv', cols, [[f[c] for c in cols] for f in filas + [extra]])
        inf = self.comparar()
        self.assertEqual(inf['resultado'], 'no_reproduce')
        t = [x for x in inf['tablas'] if x['archivo'] == 'predicciones_59_t12.csv'][0]
        self.assertEqual(t['filas_solo_reproduccion'], 1)

    def test_columna_de_mas(self):
        self.copia()
        cols, filas = self.tabla('comparacion_emparejada_t12.csv')
        self.reescribir('comparacion_emparejada_t12.csv', cols + ['nueva'], [[f[c] for c in cols] + ['x'] for f in filas])
        inf = self.comparar()
        self.assertEqual(inf['resultado'], 'no_reproduce')
        t = [x for x in inf['tablas'] if x['archivo'] == 'comparacion_emparejada_t12.csv'][0]
        self.assertFalse(t['columnas_iguales'])

    def test_columna_clave_ausente(self):
        self.copia()
        cols, filas = self.tabla('predicciones_59_t12.csv')
        sin = [c for c in cols if c != 'ID_POLIGONO']
        self.reescribir('predicciones_59_t12.csv', sin, [[f[c] for c in sin] for f in filas])
        inf = self.comparar()
        self.assertEqual(inf['resultado'], 'no_reproduce')
        self.assertTrue(any('faltan columnas clave' in p for p in inf['problemas']))

    def test_clave_repetida_se_reporta_sin_lanzar(self):
        self.copia()
        cols, filas = self.tabla('predicciones_59_t12.csv')
        self.reescribir('predicciones_59_t12.csv', cols, [[f[c] for c in cols] for f in filas + [filas[0]]])
        inf = self.comparar()
        self.assertEqual(inf['resultado'], 'no_reproduce')
        self.assertTrue(any('clave repetida' in p for p in inf['problemas']))

    def test_bandera_distinta(self):
        self.copia()
        self.alterar_celda('comparacion_emparejada_t12.csv', 0, 'cumple_regla_T03', 'True')
        inf = self.comparar()
        self.assertEqual(inf['resultado'], 'no_reproduce')

    def test_numero_contra_vacio(self):
        self.copia()
        self.alterar_celda('seleccion_interna_t12.csv', 0, 'lambda_reg', '0.1')
        self.assertEqual(self.comparar()['resultado'], 'no_reproduce')

    def test_otra_opcion_elegida_se_marca_aparte(self):
        self.copia()
        cols, filas = self.tabla('seleccion_interna_t12.csv')
        # intercambia la opción elegida del primer contexto sin tocar nada más
        ctx = (filas[0]['candidato'], filas[0]['escenario'], filas[0]['repeticion'], filas[0]['particion'])
        for f in filas:
            if (f['candidato'], f['escenario'], f['repeticion'], f['particion']) == ctx:
                f['elegida'] = 'True' if f['opcion'] == 'abr_oct_l1_k1' else 'False'
        self.reescribir('seleccion_interna_t12.csv', cols, [[f[c] for c in cols] for f in filas])
        inf = self.comparar()
        self.assertEqual(inf['resultado'], 'no_reproduce')
        self.assertEqual(inf['selecciones']['contextos_con_otra_opcion'], 1)
        self.assertEqual(inf['selecciones']['ejemplos'][0]['oficial'], 'jun_oct_l01_k1')
        self.assertEqual(inf['selecciones']['ejemplos'][0]['reproduccion'], 'abr_oct_l1_k1')
        self.assertTrue(any('eligieron otra opción' in p for p in inf['problemas']))

    def test_dos_opciones_elegidas_en_un_contexto(self):
        self.copia()
        cols, filas = self.tabla('seleccion_interna_t12.csv')
        filas[0]['elegida'] = 'True'
        self.reescribir('seleccion_interna_t12.csv', cols, [[f[c] for c in cols] for f in filas])
        inf = self.comparar()
        self.assertEqual(inf['resultado'], 'no_reproduce')
        self.assertTrue(any('ilegible' in p for p in inf['problemas']))


    def test_seleccion_malformada_igual_en_ambas_carpetas_no_se_aprueba(self):
        """Aunque las dos coincidan celda a celda, una selección con dos opciones elegidas no es evidencia válida."""
        self.copia()
        for carpeta in (self.of, self.rp):
            cols, filas = rep.leer_tabla(carpeta / 'seleccion_interna_t12.csv')
            filas[0]['elegida'] = 'True'
            escribir_csv(carpeta / 'seleccion_interna_t12.csv', cols, [[f[c] for c in cols] for f in filas])
            fijar_manifest(carpeta)
        inf = self.comparar()
        self.assertTrue(all(t['aprobada'] for t in inf['tablas']))
        self.assertFalse(inf['aprobada'])
        self.assertEqual(inf['resultado'], 'no_reproduce')
        self.assertTrue(any('ilegible' in p for p in inf['problemas']))


class Manifests(Base):
    def test_codigo_distinto_no_es_comparable(self):
        self.copia()
        m = json.loads((self.rp / 'manifest.json').read_text())
        cod = dict(m['codigo_sha256'], a='f' * 64)
        fijar_manifest(self.rp, codigo_sha256=cod)
        inf = self.comparar()
        self.assertEqual(inf['resultado'], 'no_comparable')
        self.assertFalse(inf['aprobada'])
        self.assertIn('codigo_sha256', inf['manifest']['campos_distintos'])

    def test_entradas_distintas_no_son_comparables(self):
        self.copia()
        fijar_manifest(self.rp, entradas_sha256=dict(HUELLAS, b='0' * 64))
        self.assertEqual(self.comparar()['resultado'], 'no_comparable')

    def test_cada_campo_obligatorio_del_manifest_bloquea(self):
        valores = dict(schema='otro', version='otra', version_modelos='otra', sha_diseno_t12='0' * 64,
                       sha_comprobaciones='0' * 64, contextos_externos=49, procedimientos=['t12_het_GP'],
                       filas_oof=1, ajustes_finales_59=7)
        for campo, valor in valores.items():
            with self.subTest(campo=campo):
                if self.rp.exists():
                    shutil.rmtree(self.rp)
                self.copia()
                fijar_manifest(self.rp, **{campo: valor})
                inf = self.comparar()
                self.assertEqual(inf['resultado'], 'no_comparable')
                self.assertIn(campo, inf['manifest']['campos_distintos'])

    def test_no_compara_aritmetica_si_no_es_comparable(self):
        self.copia()
        self.alterar_celda('predicciones_oof_t12.csv', 0, 'prediccion', '99')
        fijar_manifest(self.rp, sha_diseno_t12='0' * 64)
        inf = self.comparar()
        self.assertEqual(inf['resultado'], 'no_comparable')
        self.assertNotIn('tablas', inf)

    def test_archivo_editado_a_mano_en_la_reproduccion(self):
        self.copia()
        cols, filas = self.tabla('metricas_t12.csv')
        filas[0]['MAE'] = '0.1'
        escribir_csv(self.rp / 'metricas_t12.csv', cols, [[f[c] for c in cols] for f in filas])  # sin actualizar el manifest
        inf = self.comparar()
        self.assertEqual(inf['resultado'], 'no_reproduce')
        self.assertTrue(any('reproduccion' in p and 'metricas_t12.csv' in p for p in inf['integridad']))

    def test_archivo_oficial_editado_a_mano(self):
        self.copia()
        cols, filas = rep.leer_tabla(self.of / 'metricas_t12.csv')
        filas[0]['MAE'] = '0.1'
        escribir_csv(self.of / 'metricas_t12.csv', cols, [[f[c] for c in cols] for f in filas])
        inf = self.comparar()
        self.assertEqual(inf['resultado'], 'no_reproduce')
        self.assertTrue(any(p.startswith('oficial') for p in inf['integridad']))

    def test_manifest_con_lista_incompleta_de_salidas(self):
        self.copia()
        for c in (self.of, self.rp):
            m = json.loads((c / 'manifest.json').read_text())
            m['salidas_sha256'].pop('metricas_t12.csv')
            (c / 'manifest.json').write_text(json.dumps(m))
        inf = self.comparar()
        self.assertEqual(inf['resultado'], 'no_reproduce')

    def test_falta_un_csv(self):
        self.copia()
        (self.rp / 'metricas_t12.csv').unlink()
        inf = self.comparar()
        self.assertEqual(inf['resultado'], 'no_comparable')
        self.assertIn('metricas_t12.csv', inf['problemas'][0])

    def test_falta_el_manifest(self):
        self.copia()
        (self.rp / 'manifest.json').unlink()
        self.assertEqual(self.comparar()['resultado'], 'no_comparable')


class Uso(Base):
    def test_reproduccion_igual_a_lo_oficial_es_error(self):
        with self.assertRaises(ValueError):
            rep.comparar(self.of, self.raiz)
        with self.assertRaises(ValueError):
            rep.comparar('registro/t12', self.raiz)

    def test_carpetas_inexistentes(self):
        with self.assertRaises(ValueError):
            rep.comparar(self.raiz / 'reports' / 'no_existe', self.raiz)
        self.copia()
        with self.assertRaises(ValueError):
            rep.comparar(self.rp, self.raiz, oficial='registro/otra')

    def test_ruta_relativa_a_la_raiz(self):
        self.copia()
        inf = rep.comparar('reports/t12_repro', self.raiz)
        self.assertTrue(inf['aprobada'])

    def test_comparar_no_modifica_ninguna_carpeta(self):
        self.copia()
        self.alterar_celda('predicciones_oof_t12.csv', 0, 'prediccion', '9')
        antes = {str(p): sha_bytes(p) for c in (self.of, self.rp) for p in c.iterdir()}
        self.comparar()
        despues = {str(p): sha_bytes(p) for c in (self.of, self.rp) for p in c.iterdir()}
        self.assertEqual(antes, despues)

    def test_informe_se_escribe_en_la_reproduccion_y_no_se_sobrescribe(self):
        self.copia()
        inf = self.comparar()
        ruta = rep.escribir_informe(inf, self.rp)
        self.assertEqual(ruta, self.rp / rep.SALIDA)
        guardado = json.loads(ruta.read_text(encoding='utf-8'))
        self.assertEqual(guardado['resultado'], 'identica_byte_a_byte')
        self.assertEqual(guardado['schema'], 'reproduccion_t12_v1')
        antes = sha_bytes(ruta)
        with self.assertRaises(ValueError):
            rep.escribir_informe(inf, self.rp)
        self.assertEqual(sha_bytes(ruta), antes)

    def test_nunca_escribe_en_lo_oficial(self):
        self.copia()
        inf = self.comparar()
        with self.assertRaises(ValueError):
            rep.escribir_informe(inf, self.of)
        self.assertFalse((self.of / rep.SALIDA).exists())

    def test_informe_no_cuenta_como_salida_de_t12(self):
        """Escribir el informe no rompe una segunda comparación (no es un CSV ni el manifest)."""
        self.copia()
        rep.escribir_informe(self.comparar(), self.rp)
        self.assertTrue(self.comparar()['aprobada'])


class Consola(Base):
    def correr(self, *args):
        salida = io.StringIO()
        with contextlib.redirect_stdout(salida):
            codigo = rep.main(['--raiz', str(self.raiz), *args])
        return codigo, salida.getvalue()

    def test_aprobada_devuelve_cero_y_guarda(self):
        self.copia()
        codigo, texto = self.correr('--reproduccion', 'reports/t12_repro', '--etiqueta', 'Windows amd64')
        self.assertEqual(codigo, 0)
        self.assertIn('REPRODUCCIÓN IDÉNTICA BYTE A BYTE', texto)
        self.assertIn('Windows amd64', texto)
        self.assertTrue((self.rp / rep.SALIDA).exists())

    def test_dentro_de_tolerancia_devuelve_cero(self):
        self.copia()
        v = float(self.tabla('predicciones_oof_t12.csv')[1][2]['prediccion'])
        self.alterar_celda('predicciones_oof_t12.csv', 2, 'prediccion', repr(v + 1e-14))
        codigo, texto = self.correr('--reproduccion', 'reports/t12_repro')
        self.assertEqual(codigo, 0)
        self.assertIn('APROBADA', texto)
        self.assertIn('OK dentro de tolerancia', texto)

    def test_fallo_devuelve_uno_e_imprime_el_problema(self):
        self.copia()
        self.alterar_celda('predicciones_oof_t12.csv', 2, 'prediccion', '8')
        codigo, texto = self.correr('--reproduccion', 'reports/t12_repro')
        self.assertEqual(codigo, 1)
        self.assertIn('LA REPRODUCCIÓN NO COINCIDE', texto)
        self.assertIn('PROBLEMA', texto)
        self.assertIn('DIFERENTE', texto)

    def test_no_comparable_devuelve_uno(self):
        self.copia()
        fijar_manifest(self.rp, sha_diseno_t12='0' * 64)
        codigo, texto = self.correr('--reproduccion', 'reports/t12_repro', '--sin-informe')
        self.assertEqual(codigo, 1)
        self.assertIn('NO SE PUEDE COMPARAR', texto)

    def test_sin_informe_no_escribe(self):
        self.copia()
        codigo, _ = self.correr('--reproduccion', 'reports/t12_repro', '--sin-informe')
        self.assertEqual(codigo, 0)
        self.assertFalse((self.rp / rep.SALIDA).exists())

    def test_segunda_corrida_con_informe_existente_falla_sin_perder_el_primero(self):
        self.copia()
        self.correr('--reproduccion', 'reports/t12_repro')
        antes = sha_bytes(self.rp / rep.SALIDA)
        with self.assertRaises(ValueError):
            self.correr('--reproduccion', 'reports/t12_repro')
        self.assertEqual(sha_bytes(self.rp / rep.SALIDA), antes)


class Constantes(unittest.TestCase):
    def test_criterio_es_el_de_t15(self):
        self.assertEqual((rep.ATOL, rep.RTOL), (1e-12, 1e-10))

    def test_claves_cubren_los_cinco_csv_de_t12_evaluar(self):
        from scripts import t12_evaluar
        self.assertEqual(set(rep.CLAVES) | {'manifest.json'}, set(t12_evaluar.ARCHIVOS))

    def test_cada_clave_existe_en_las_columnas_de_producción(self):
        base = tablas_base()
        for nombre, claves in rep.CLAVES.items():
            self.assertTrue(set(claves) <= set(base[nombre][0]), nombre)


if __name__ == '__main__':
    unittest.main()
