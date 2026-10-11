"""Contratos de fichas, pérdida de evidencia y protección de salidas.

Sólo metadatos: no se realizan correlaciones ni ajustes con datos reales.
"""
import copy
import csv
import io
import json
from pathlib import Path
import tempfile
import unittest

from scripts.t07_fichas_atributos import (
    RAIZ, CAMPOS, construir, complementar, generar, leer_contrato, verificar,
)


class TestFichasAtributos(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dic, cls.contrato, _ = leer_contrato(RAIZ)
        cls.contenidos = construir()
        cls.fichas = list(csv.DictReader(io.StringIO(cls.contenidos['fichas_atributos.csv'].decode())))
        cls.indice = {r['columna']: r for r in cls.fichas}

    def test_identidad_definiciones_roles_unidades_y_no_valores(self):
        self.assertEqual(len(self.fichas), 60)
        self.assertEqual(len(self.indice), 60)
        for d in self.dic:
            f = self.indice[d['columna']]
            self.assertEqual({k: f[k] for k in d}, d)
        self.assertNotIn('valor', CAMPOS)
        m = json.loads(self.contenidos['manifest.json'])
        self.assertEqual(m['roles'], {'metadato': 5, 'objetivo': 1, 'predictor_candidato': 35,
                                    'referencia_y_evaluacion': 1, 'calidad': 18})
        self.assertFalse(m['selecciona_atributos'])
        self.assertFalse(m['entrena'])

    def test_candidatas_no_certifican_disponibilidad(self):
        for f in self.fichas:
            if f['funcion'] == 'predictor_candidato' or f['columna'] == 'area_ha_origen':
                self.assertEqual(f['disponibilidad_al_corte'], 'no acreditada')
                self.assertEqual(f['fecha_publicacion'], 'no documentada')
                self.assertTrue(f['requisitos_campania_futura'])

    def test_area_grupo_y_calidad_no_promovidos(self):
        self.assertEqual(self.indice['area_ha_origen']['funcion'], 'metadato')
        self.assertEqual(self.indice['area_ha_origen']['frente_de_uso'], 'T10')
        self.assertEqual(self.indice['cultivo_origen']['funcion'], 'referencia_y_evaluacion')
        self.assertIn('T11 ya prevé controles', self.indice['pl_capturas_abr_oct']['condicion_de_uso'])
        self.assertIn('nunca entrada', self.indice['rendimiento_t_ha']['condicion_de_uso'])

    def test_faltantes_pendiente_y_elevacion_distintos(self):
        self.assertIn('D020 no se aplica', self.indice['elevacion_media_m']['aclaracion_faltante'])
        self.assertIn('menor que 0.5', self.indice['pendiente_media_t10_grados']['aclaracion_faltante'])
        self.assertIn('no se imputa', self.indice['rendimiento_t_ha']['significado_vacio'])

    def test_al_corte_conserva_dependencia_de_suavizado(self):
        for c in ('pl_ndvi_al_corte', 's2_ndvi_al_corte'):
            f = self.indice[c]
            self.assertEqual(f['periodo_resumen'], '2025-10-17/2025-10-31')
            self.assertIn('2025-04-01/2025-10-31', f['periodo_insumos_necesarios'])
            self.assertIn('anterior al 17-oct', f['periodo_insumos_necesarios'])
        self.assertEqual(self.indice['prec_acumulada_mm_jun_oct']['periodo_resumen'], '2025-06-01/2025-10-31')

    def test_unidades_pendientes_no_se_inventan(self):
        esperadas = {'pl_lai2_max_abr_oct', 'pl_lai2_max_jun_oct',
                     'ls_vi6t_mediana_abr_oct', 'ls_vi6t_mediana_jun_oct'}
        self.assertEqual({r['columna'] for r in self.fichas if r['unidad_estado'] == 'pendiente'}, esperadas)
        for c in esperadas:
            self.assertIn('P03', self.indice[c]['pendientes'])
            self.assertIn('no documentada', self.indice[c]['unidad'])

    def test_todos_pendientes_tienen_responsable_y_columnas(self):
        filas = list(csv.DictReader(io.StringIO(self.contenidos['pendientes_documentales.csv'].decode())))
        por_id = {r['id']: r for r in filas}
        self.assertEqual(len(filas), 8)
        for r in self.fichas:
            for k in r['pendientes'].split(';'):
                self.assertIn(r['columna'], por_id[k]['columnas'].split(';'))
                self.assertTrue(por_id[k]['responsable'])
                self.assertTrue(por_id[k]['revisa'])

    def test_producto_nuevo_requiere_ficha(self):
        d = dict(self.dic[0], producto='SensorNuevo')
        with self.assertRaisesRegex(ValueError, 'Producto sin ficha'):
            complementar(d, self.contrato)

    def test_nueva_campania_no_reutiliza_calendario(self):
        contrato = copy.deepcopy(self.contrato)
        contrato['ventanas']['abr_oct']['fin'] = '2026-10-31'
        d = next(r for r in self.dic if r['columna'] == 'prec_acumulada_mm_abr_oct')
        with self.assertRaisesRegex(ValueError, 'campaña/corte'):
            complementar(d, contrato)

    def test_reproduccion_exacta_y_verificacion(self):
        with tempfile.TemporaryDirectory() as td:
            a, b = Path(td) / 'a', Path(td) / 'b'
            generar(a); generar(b)
            self.assertEqual(verificar(a)['fichas'], 60)
            self.assertTrue(all((a / n).read_bytes() == (b / n).read_bytes() for n in self.contenidos))

    def test_rechaza_alteracion_en_ficha(self):
        with tempfile.TemporaryDirectory() as td:
            a = Path(td) / 'a'; generar(a)
            p = a / 'fichas_atributos.csv'
            p.write_bytes(p.read_bytes().replace(b'no acreditada', b'acreditada'))
            with self.assertRaisesRegex(ValueError, 'alterada'):
                verificar(a)

    def test_rechaza_faltante_y_extra(self):
        with tempfile.TemporaryDirectory() as td:
            a = Path(td) / 'a'; generar(a)
            (a / 'ajeno.txt').write_text('x')
            with self.assertRaisesRegex(ValueError, 'incompletos o ajenos'):
                verificar(a)
            (a / 'ajeno.txt').unlink()
            (a / 'manifest.json').unlink()
            with self.assertRaisesRegex(ValueError, 'incompletos o ajenos'):
                verificar(a)

    def test_no_sobrescribe_y_no_escribe_en_fuentes(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaisesRegex(ValueError, 'ya existe'):
                generar(td)
        with self.assertRaisesRegex(ValueError, 'protegida'):
            generar(RAIZ / 'registro/t07/fichas')
        with self.assertRaisesRegex(ValueError, 'protegida'):
            generar(RAIZ / 'data/raw/nuevo')


if __name__ == '__main__':
    unittest.main()
