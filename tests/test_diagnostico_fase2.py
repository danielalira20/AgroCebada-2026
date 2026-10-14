"""Controles de comparabilidad, influencia analítica y ausencia de oráculo."""
import math
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import diagnostico_fase2 as d


def table(values, mun=None, group=None):
    return {pid:dict(rendimiento_t_ha=str(y),municipio=(mun or {}).get(pid,'M'),cultivo_origen=(group or {}).get(pid,'G')) for pid,y in values.items()}


class Formulas(unittest.TestCase):
    def test_influencia_equivale_retiro_explicito(self):
        t=table({'A':2.,'B':3.,'C':7.});s=d.influencia(set(t),t)
        means={pid:sum(float(t[i]['rendimiento_t_ha']) for i in t if i!=pid)/2 for pid in t}
        hit=max(abs(v-s['media_pool']) for v in means.values())
        self.assertAlmostEqual(s['influencia_max_abs'],hit)
        self.assertEqual(s['etiqueta_mas_influyente'],'C')
        self.assertAlmostEqual(s['media_sin_etiqueta'],means['C'])

    def test_una_etiqueta_no_divide_entre_cero(self):
        s=d.influencia({'A'},table({'A':3.}))
        self.assertEqual(s['influencia_max_abs'],'');self.assertEqual(s['media_sin_etiqueta'],'')
        self.assertEqual(s['n_pool'],1)

    def test_empate_influencia_por_ID(self):
        s=d.influencia({'B','A'},table({'B':4.,'A':2.}))
        self.assertEqual(s['etiqueta_mas_influyente'],'A')

    def test_etiquetas_iguales_influencia_cero(self):
        s=d.influencia({'B','A'},table({'B':3.,'A':3.}))
        self.assertEqual(s['influencia_max_abs'],0);self.assertEqual(s['sd_pool'],0)

    def test_fuente_grupo_no_municipio_ausente(self):
        t=table({'A':2.,'B':4.,'E':0.},{'A':'X','B':'Y','E':'Z'})
        pool,source,n=d.pool_referencia({'A','B'},'E',t)
        self.assertEqual((pool,source,n),({'A','B'},'grupo',0))

    def test_fuente_global_con_grupo_ausente(self):
        t=table({'A':2.,'E':0.},{'A':'X','E':'Z'},{'A':'U','E':'V'})
        pool,source,n=d.pool_referencia({'A'},'E',t)
        self.assertEqual((pool,source,n),({'A'},'global',0))

    def test_alterar_etiqueta_evaluacion_no_cambia_influencia(self):
        t=table({'A':2.,'B':4.,'E':3.});a=d.influencia(d.pool_referencia({'A','B'},'E',t)[0],t)
        t['E']['rendimiento_t_ha']='999'
        b=d.influencia(d.pool_referencia({'A','B'},'E',t)[0],t)
        self.assertEqual(a,b)

    def test_corr_constante_es_ausencia_no_cero(self):
        self.assertEqual(d.corr([1,1],[2,3]),'')
        self.assertEqual(d.corr([],[]),'')

    def test_corr_pares_y_signo(self):
        self.assertAlmostEqual(d.corr([1,2,3],[3,2,1]),-1)
        with self.assertRaises(ValueError):d.corr([1,2],[1])

    def test_cambio_numerico_no_significacion(self):
        self.assertEqual(d.cambio(-1e-10),'sin_cambio_numerico')
        self.assertEqual(d.cambio(-1e-8),'mejora_numerica')
        self.assertEqual(d.cambio(1e-8),'deterioro_numerico')

    def test_referencias_alias_no_modelos_nuevos(self):
        for task,cand in [('T08','media_mun__resp_grupo'),('T09','T'),('T14','referencia')]:
            self.assertTrue(d.metodo({'fuente':task,'candidato':cand})[3])

    def test_centrados_con_metodos_distintos(self):
        a=d.metodo({'fuente':'T09','candidato':'R_centrado'})
        b=d.metodo({'fuente':'T11','candidato':'t11_c8_planet_abr_oct_centrado'})
        self.assertNotEqual(a[:3],b[:3])

    def test_salida_existente_intacta(self):
        with tempfile.TemporaryDirectory() as td:
            f=Path(td)/'marca';f.write_text('original')
            with self.assertRaises(ValueError):d.ejecutar('no_leer','no_leer',td)
            self.assertEqual(f.read_text(),'original')

    def test_fuente_vacia_y_no_finita_rechazadas(self):
        with self.assertRaises(ValueError):d.influencia(set(),{})
        with self.assertRaises(ValueError):d.influencia({'A'},table({'A':'nan'}))


@unittest.skipUnless(os.getenv('AGRO_DIAG_FASE0') and os.getenv('AGRO_DIAG_FUENTES'),'Requiere snapshots fijados')
class Reales(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base,cls.table,cls.known,cls.cases,cls.controls,cls.catalog,cls.index=d.cargar(Path(os.environ['AGRO_DIAG_FASE0']),Path(os.environ['AGRO_DIAG_FUENTES']))
        cls.t=d.comparar(cls.base,cls.known,cls.cases,cls.controls,cls.catalog,cls.index)
        _,_,_,_,parts=d.f0.cargar_base(Path(os.environ['AGRO_DIAG_FUENTES']))
        cls.support=d.soporte(cls.base,cls.table,cls.known,parts)

    def test_51_series_y_matriz_sin_59(self):
        self.assertEqual(len(self.catalog),51);self.assertEqual(len(self.t['matriz_procedimientos_por_caso.csv']),28152)
        self.assertEqual({r['id_parcela'] for r in self.t['matriz_procedimientos_por_caso.csv']},self.known)
        self.assertEqual(sum(len(v) for v in self.index.values()),70380)

    def test_pares_excluyen_alias_ref(self):
        self.assertEqual(sum(r['es_referencia'] for r in self.catalog),7)
        self.assertEqual(len(self.t['pares_procedimientos.csv']),3960)
        ids={r['serie_id'] for r in self.catalog if not r['es_referencia'] or r['fuente']=='T08'}
        self.assertTrue(all(r['serie_1'] in ids and r['serie_2'] in ids for r in self.t['pares_procedimientos.csv']))

    def test_denominadores_constantes_entre_series(self):
        for r in self.t['resumen_comparaciones.csv']:
            self.assertEqual(r['n_registros'],690 if r['poblacion']=='todas' else 675 if r['escenario']=='A' else 659)

    def test_filas_sin_elegibles_no_inventan_mae(self):
        for r in self.t['matriz_procedimientos_por_caso.csv']:
            if not r['n_elegibles']:
                self.assertEqual(r['mae'],'');self.assertEqual(r['delta_mae'],'')

    def test_t08_delta_cero_y_casos_fijos(self):
        rr=[r for r in self.t['matriz_procedimientos_por_caso.csv'] if r['serie_id']=='S001']
        self.assertTrue(all(r['delta_mae']==0 for r in rr if r['n_elegibles']))
        self.assertEqual({r['id_parcela'] for r in rr if r['orden_caso_fijo']},{r['id_parcela'] for r in self.cases})

    def test_influencia_no_toca_evaluacion(self):
        for r in self.support['sensibilidad_media_referencia.csv']:
            self.assertNotEqual(r['id_parcela'],r['etiqueta_mas_influyente'])
        self.assertEqual(len(self.support['sensibilidad_media_referencia.csv']),1380)
        self.assertEqual(len(self.support['ficha_soporte_municipal.csv']),54)

    def test_familias_no_cuentan_baseline_alias(self):
        self.assertEqual(len(self.t['coincidencias_por_frente.csv']),3312)
        self.assertEqual({r['frente'] for r in self.t['coincidencias_por_frente.csv']},{'T09','T10','T11','T13','T13e','T14'})

    def test_ninguna_salida_prediccion_mixta(self):
        for rows in self.t.values():
            self.assertNotIn('ganador_por_parcela',rows[0])
            self.assertNotIn('prediccion_oraculo',rows[0])


if __name__=='__main__':unittest.main()
