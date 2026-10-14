"""Regresiones sobre cancelación, pesos, máscaras y trazabilidad de fase1."""
import math
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import diagnostico_fase1 as d


def fila(pid='P', y=3., pred=4., source='municipio', rep=1):
    r = dict(id_parcela=pid, real=y, prediccion=pred, fuente_referencia=source,
             repeticion=rep, escenario='A')
    return {**r, **d.errores(r)}


class Formulas(unittest.TestCase):
    def test_error_antes_de_promediar_no_cancela(self):
        s = d.resumen_parcela([fila(pred=2), fila(pred=4, rep=2)])
        self.assertEqual(s['sesgo'], 0); self.assertEqual(s['mae'], 1)
        self.assertEqual(s['mse'], 1); self.assertEqual(s['abs_sesgo'], 0)

    def test_signos_y_cero_exacto(self):
        s = d.resumen_parcela([fila(pred=2), fila(pred=3), fila(pred=4)])
        self.assertEqual((s['sobre'], s['sub'], s['ceros']), (1, 1, 1))
        self.assertEqual(s['fraccion_sub'], 1/3)

    def test_ausencia_no_es_error_cero(self):
        s = d.resumen_parcela([])
        self.assertEqual(s['n_elegibles'], 0)
        for col in ('mae', 'sesgo', 'sd_error', 'rmse', 'error_min', 'fraccion_sub'):
            self.assertEqual(s[col], '')

    def test_pesos_parcela_frente_a_registro(self):
        s = d.resumir_conjunto([fila('A', pred=5)] + [fila('B', pred=3, rep=k) for k in range(1,6)])
        self.assertEqual(s['mae_parcelas'], 1)
        self.assertAlmostEqual(s['mae_registros'], 1/3)
        self.assertEqual(s['n_parcelas'], 2); self.assertEqual(s['n_registros'], 6)

    def test_rmse_no_es_promedio_de_raices(self):
        s = d.resumir_conjunto([fila('A', pred=5), fila('B', pred=3)])
        self.assertAlmostEqual(s['rmse_parcelas'], math.sqrt(2))

    def test_cuantiles_r7_y_unico(self):
        self.assertEqual(d.cuantil([0,10], .9), 9)
        self.assertEqual(d.cuantil([3], .5), 3)
        self.assertEqual(d.cuantil([], .5), '')

    def test_rango_no_intervalo(self):
        s = d.resumen_parcela([fila(pred=2), fila(pred=4)])
        self.assertEqual(s['rango_error'], 2); self.assertEqual(s['sd_error'], 1)

    def test_empate_por_id(self):
        self.assertEqual([r['id_parcela'] for r in d.orden([{'id_parcela':'B','mae':1}, {'id_parcela':'A','mae':1}], 'mae')], ['A','B'])

    def test_no_finito(self):
        for val in (float('inf'), float('nan'), 1e308):
            with self.assertRaises(ValueError):
                fila(pred=val)

    def test_mascaras_fuentes(self):
        for source in ('municipio','grupo','global'):
            r = fila(source=source)
            self.assertTrue(d.elegible(r, 'todas'))
            self.assertEqual(d.elegible(r, 'sin_respaldo'), source=='municipio')
            self.assertEqual(d.elegible(r, 'con_respaldo'), source!='municipio')
            self.assertEqual(d.elegible(r, 'grupo'), source=='grupo')
        with self.assertRaises(ValueError): d.elegible(fila(), 'inexistente')

    def test_salida_existente_no_sobreescrita(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)/'marca'; p.write_text('conservar')
            with self.assertRaisesRegex(ValueError, 'ya existe'):
                d.ejecutar('no_leer', 'no_leer', td)
            self.assertEqual(p.read_text(), 'conservar')

    def test_fallo_no_publica_tablas_parciales(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td)/'out'
            with patch.object(d, 'cargar', return_value=([], {}, set(), [], [])), \
                 patch.object(d, 'analizar', return_value={'x.csv':[{'n':1}]}), \
                 patch.object(d, 'csv_escribir', side_effect=ValueError('fallo controlado')):
                with self.assertRaises(ValueError): d.ejecutar('x','y',out,False)
            self.assertFalse(out.exists()); self.assertEqual(list(Path(td).iterdir()), [])


@unittest.skipUnless(os.getenv('AGRO_DIAG_FASE0') and os.getenv('AGRO_DIAG_FUENTES'), 'Requiere snapshots reales fijados')
class DatosReales(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows, cls.table, cls.known, cls.cases, _ = d.cargar(Path(os.environ['AGRO_DIAG_FASE0']), Path(os.environ['AGRO_DIAG_FUENTES']))
        cls.t = d.analizar(cls.rows, cls.table, cls.known, cls.cases)

    def test_censo_y_sin_reservadas(self):
        self.assertEqual(len(self.rows), 1380); self.assertEqual(len(self.known), 138)
        self.assertEqual({r['id_parcela'] for r in self.rows}, self.known)
        self.assertTrue(all(self.table[r['id_parcela']]['conjunto_origen']=='ENTRENAMIENTO' for r in self.rows))

    def test_denominadores_por_registro(self):
        m = {(r['escenario'],r['poblacion']):r for r in self.t['resumen_metricas.csv']}
        self.assertEqual(m['A','sin_respaldo']['n_registros'],675)
        self.assertEqual(m['B','sin_respaldo']['n_registros'],659)
        self.assertEqual(m['B','con_respaldo']['n_registros'],31)

    def test_contribuciones_suman_uno(self):
        for esc in ('A','B'):
            for pop in d.POBLACIONES:
                rr = [r for r in self.t['errores_por_parcela.csv'] if r['escenario']==esc and r['poblacion']==pop and r['n_elegibles']]
                if rr:
                    self.assertAlmostEqual(math.fsum(r['contribucion_abs'] for r in rr),1)
                    self.assertAlmostEqual(math.fsum(r['contribucion_cuadratica'] for r in rr),1)

    def test_138_filas_incluye_ausencias_por_mascara(self):
        for esc in ('A','B'):
            for pop in d.POBLACIONES:
                rr = [r for r in self.t['errores_por_parcela.csv'] if r['escenario']==esc and r['poblacion']==pop]
                self.assertEqual({r['id_parcela'] for r in rr},self.known)
                self.assertTrue(all(r['mae']=='' for r in rr if not r['n_elegibles']))

    def test_comparticion_sin_denominador_no_es_cero(self):
        for r in self.t['resumen_metricas.csv']:
            if not r['n_parcelas']:
                self.assertEqual(r['contribucion_abs_casos_fijos'], '')
                self.assertEqual(r['contribucion_cuadratica_casos_fijos'], '')

    def test_casos_y_controles_conservados(self):
        rr = self.t['ranking_principal_y_sensibilidad_B.csv']
        self.assertEqual(len(rr),20)
        self.assertEqual([r['id_parcela'] for r in rr if r['escenario']=='A'],[r['id_parcela'] for r in self.cases])
        self.assertEqual(len({r['id_parcela'] for r in self.rows if r['control_de']}),10)

    def test_pares_mascara_en_ambos_escenarios(self):
        pp = [r for r in self.t['contraste_AB_emparejado.csv'] if r['poblacion']=='sin_respaldo']
        ix = {(r['escenario'],r['repeticion'],r['id_parcela']):r for r in self.rows}
        for r in pp:
            reps = [int(x) for x in r['rep_pares'].split('|')] if r['rep_pares'] else []
            self.assertEqual(r['n_pares'],len(reps))
            for k in reps:
                self.assertTrue(all(ix[e,k,r['id_parcela']]['fuente_referencia']=='municipio' for e in ('A','B')))


if __name__ == '__main__': unittest.main()
