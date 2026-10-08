"""Pruebas de alteraciones relevantes en el contrato de la entrega real T06."""
import copy
from pathlib import Path
import unittest

from scripts.t07_fuentes import leer_csv, validar_catalogo
from scripts.t07_satelite import validar, unir

RAIZ = Path(__file__).resolve().parents[1]


class Satelite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.columnas, cls.filas = leer_csv(RAIZ / 'registro/t06/variables_satelitales.csv')
        _, cls.dic = leer_csv(RAIZ / 'registro/t06/variables_satelitales_diccionario.csv')
        _, cls.cov = leer_csv(RAIZ / 'registro/t06/cobertura_ventana.csv')
        _, cat = leer_csv(RAIZ / 'analisis/auditoria_catalogo_y_etiquetas/tablas/catalogo_parcelas.csv')
        cls.cat = validar_catalogo(cat)

    def comprobar(self, filas=None, dic=None, cov=None, columnas=None):
        return validar(columnas or self.columnas, self.filas if filas is None else filas,
                       self.dic if dic is None else dic, self.cov if cov is None else cov, self.cat)

    def test_union_por_id_preserva_8668_valores_y_etiquetas(self):
        s, q, _ = self.comprobar(filas=list(reversed(self.filas)), cov=list(reversed(self.cov)))
        cab, tabla = unir(list(reversed(self.cat)), self.columnas, s)
        self.assertEqual((len(tabla), len(cab), len(q)), (197, 52, 1182))
        for r, original in zip(tabla, self.cat):
            for c, v in original.items(): self.assertEqual(r[c], v)
            for c in self.columnas[1:]: self.assertEqual(r[c], s[r['id_parcela']][c])

    def test_ids_duplicados(self):
        f = copy.deepcopy(self.filas); f[1]['ID_POLIGONO'] = f[0]['ID_POLIGONO']
        with self.assertRaisesRegex(ValueError, 'IDs T06'): self.comprobar(filas=f)

    def test_id_ausente(self):
        with self.assertRaisesRegex(ValueError, 'IDs T06'): self.comprobar(filas=self.filas[:-1])

    def test_id_ajeno(self):
        f = copy.deepcopy(self.filas); f[0]['ID_POLIGONO'] = 'ajeno'
        with self.assertRaisesRegex(ValueError, 'IDs T06'): self.comprobar(filas=f)

    def test_diccionario_duplicado(self):
        d = copy.deepcopy(self.dic); d[-1] = d[0]
        with self.assertRaisesRegex(ValueError, 'Diccionario'): self.comprobar(dic=d)

    def test_ventana_o_sensor_o_umbral_contradictorio(self):
        for c, v in [('ventana', 'jun_oct'), ('sensor', 'Landsat'), ('umbral_nubosidad', '5'), ('tipo', 'calidad')]:
            with self.subTest(c=c):
                d = copy.deepcopy(self.dic); d[0][c] = v
                with self.assertRaisesRegex(ValueError, 'contradictorio'): self.comprobar(dic=d)

    def test_calidad_no_coincide(self):
        f = copy.deepcopy(self.filas); f[0]['pl_capturas_abr_oct'] = '1'
        with self.assertRaisesRegex(ValueError, 'distinta de cobertura'): self.comprobar(filas=f)

    def test_cobertura_duplicada_o_ausente(self):
        for c in [self.cov + [self.cov[0]], self.cov[:-1]]:
            with self.assertRaisesRegex(ValueError, 'Cobertura'): self.comprobar(cov=c)

    def test_fecha_posterior_al_corte(self):
        c = copy.deepcopy(self.cov); c[0]['ultima'] = '2025-11-01'
        with self.assertRaisesRegex(ValueError, 'fuera de ventana'): self.comprobar(cov=c)

    def test_hueco_interno_supera_total(self):
        c = copy.deepcopy(self.cov); c[0]['hueco_max_interno_dias'] = '215'
        with self.assertRaisesRegex(ValueError, 'rango'): self.comprobar(cov=c)

    def test_no_finito_o_nubosidad_invalida(self):
        for col, v in [('pl_ndvi_max_abr_oct', 'nan'), ('s2_nubosidad_media_jun_oct', '101'), ('ls_capturas_abr_oct', '2.5')]:
            with self.subTest(col=col):
                f = copy.deepcopy(self.filas); f[0][col] = v
                with self.assertRaises(ValueError): self.comprobar(filas=f)

    def test_valor_ausente_se_conserva_y_no_se_rellena(self):
        f = copy.deepcopy(self.filas); f[0]['pl_ndvi_integral_jun_oct'] = ''
        s, q, _ = self.comprobar(filas=f)
        _, tabla = unir(self.cat, self.columnas, s)
        self.assertEqual(tabla[0]['pl_ndvi_integral_jun_oct'], '')
        control = next(x for x in q if x['id_parcela'] == tabla[0]['id_parcela'] and x['sensor'] == 'Planet' and x['ventana'] == 'jun_oct')
        self.assertEqual(control['estado'], 'valores_ausentes')
        self.assertIn('pl_ndvi_integral_jun_oct', control['variables_ausentes'])

    def test_clima_no_multiplica_etiquetas(self):
        s, _, _ = self.comprobar()
        with self.assertRaisesRegex(ValueError, 'claves incompatibles'):
            unir(self.cat, self.columnas, s, [{'id_parcela': self.cat[0]['id_parcela']}] * 197)


if __name__ == '__main__': unittest.main()
