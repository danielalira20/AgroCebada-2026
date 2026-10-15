"""Casos que distinguen corte, ancla exacta, soporte y ceros de un relleno silencioso."""
import csv
from datetime import date,timedelta
from fractions import Fraction as F
from pathlib import Path
import tempfile
import unittest

from scripts.t15_ndwi_factibilidad import Obs,profile,catalogue,observations,number,run,validate_design
from scripts.auditar_t15_ndwi_factibilidad import exact_profile

BASE=date(2025,7,1)
START=date(2025,4,1)


def series(offsets=None,values=None,waters=None):
    offsets=offsets or [0,5,10,15,20,25,30,40,50,55,60]
    values=values or [.1,.3,.7,.9,.8,.5,.4,.3,.2,.1,.1]
    waters=waters or [.1,.2,.3,.4,.5,.6,.7,.8,.9,1.,.9]
    return [Obs('A',BASE+timedelta(days=d),v,w,0.) for d,v,w in zip(offsets,values,waters)]


class FactibilidadTest(unittest.TestCase):
    def test_ancla_exacta_no_mediana_alrededor(self):
        r=profile(series(waters=[.1,.2,.3,.95,.5,.6,.7,.8,.9,1.,.9]),START)
        self.assertEqual(r['fecha_maximo'],BASE+timedelta(days=15))
        self.assertEqual(r['ndwi_ancla'],.95)
        self.assertNotEqual(r['ndwi_ancla'],r['ndwi_mediana_mas_menos15'])
        self.assertTrue(r['calculable'])
        self.assertAlmostEqual(r['contraste_ndwi'],(.7+.8+.9+1.+.9)/5-.95)

    def test_extremos_15_y45_incluidos(self):
        r=profile(series(),START)
        self.assertEqual(r['primera_post'],BASE+timedelta(days=30))
        self.assertEqual(r['ultima_post'],BASE+timedelta(days=60))
        self.assertEqual(r['n_fechas_post'],5)

    def test_orden_no_cambia(self):
        self.assertEqual(profile(series(),START),profile(list(reversed(series())),START))

    def test_corte_antes_suavizado_y_ancla(self):
        rows=series();fin=BASE+timedelta(days=45)
        ref=profile([o for o in rows if o.fecha<=fin],START,fin)
        changed=[Obs(o.pid,o.fecha,1.,-1.,0.) if o.fecha>fin else o for o in rows]
        self.assertEqual(profile(changed,START,fin),ref)

    def test_nube_excluye_fecha_del_maximo(self):
        rows=series();rows[3]=Obs('A',rows[3].fecha,.99,.4,5.01)
        r=profile(rows,START)
        self.assertEqual(r['n_capturas'],10)
        self.assertNotEqual(r['fecha_maximo'],rows[3].fecha)

    def test_nube_cinco_incluida(self):
        rows=[Obs(o.pid,o.fecha,o.ndvi,o.ndwi,5.) for o in series()]
        self.assertEqual(profile(rows,START),profile(series(),START))

    def test_ndwi_ausente_en_ancla_no_sustituir(self):
        rows=series();o=rows[3];rows[3]=Obs(o.pid,o.fecha,o.ndvi,None,o.nube)
        r=profile(rows,START)
        self.assertFalse(r['calculable']);self.assertIsNone(r['contraste_ndwi'])
        self.assertEqual(r['motivo'],'ndwi_ancla_ausente')

    def test_una_fecha_posterior_no_basta(self):
        rows=[o for o in series() if (o.fecha-BASE).days not in [40,50,55,60]]
        r=profile(rows,START)
        self.assertEqual(r['n_fechas_post'],1)
        self.assertFalse(r['calculable']);self.assertIsNone(r['contraste_ndwi'])

    def test_dos_fechas_distintas_bastan(self):
        rows=[o for o in series() if (o.fecha-BASE).days not in [50,55,60]]
        r=profile(rows,START)
        self.assertEqual(r['n_fechas_post'],2);self.assertTrue(r['calculable'])

    def test_duplicado_no_aumenta_soporte(self):
        with self.assertRaisesRegex(ValueError,'duplicad'):
            profile(series()+[series()[6]],START)

    def test_cero_real_se_conserva(self):
        rows=[Obs(o.pid,o.fecha,o.ndvi,0.,0.) for o in series()]
        r=profile(rows,START)
        self.assertTrue(r['calculable']);self.assertEqual(r['contraste_ndwi'],0.)

    def test_menos_cinco_capturas(self):
        r=profile(series()[:4],START)
        self.assertEqual(r['motivo'],'menos_5_capturas');self.assertIsNone(r['fecha_maximo'])

    def test_meseta_empate_primera_fecha(self):
        rows=series(values=[.1,.3,.7,.9,.9,.9,.4,.3,.2,.1,.1])
        r=profile(rows,START)
        self.assertEqual(r['fecha_maximo'],BASE+timedelta(days=15))
        self.assertEqual(r['n_empates_maximo'],3)

    def test_constante_no_inventa_ciclo(self):
        rows=series(values=[.5]*11)
        r=profile(rows,START)
        self.assertEqual(r['amplitud_ndvi'],0.)
        self.assertEqual(r['fecha_maximo'],BASE)
        self.assertTrue(r['maximo_en_borde'])
        self.assertTrue(r['meseta_45_dias'])

    def test_intervalo_truncado_declarado(self):
        fin=BASE+timedelta(days=45);r=profile(series(),START,fin)
        self.assertTrue(r['intervalo_truncado'])
        self.assertTrue(r['calculable'])
        self.assertLessEqual(r['ultima_post'],fin)

    def test_ndvi_ausente_no_entra_a_curva(self):
        rows=series();o=rows[3];rows[3]=Obs(o.pid,o.fecha,None,o.ndwi,0.)
        self.assertEqual(profile(rows,START)['n_capturas'],10)

    def test_no_ndwi_post_no_es_cero(self):
        rows=[Obs(o.pid,o.fecha,o.ndvi,None if (o.fecha-BASE).days>=30 else o.ndwi,0.) for o in series()]
        r=profile(rows,START)
        self.assertEqual(r['n_fechas_post'],0);self.assertIsNone(r['contraste_ndwi'])

    def test_rendimiento_no_se_consulta(self):
        class Row(dict):
            def __getitem__(self,k):
                if 'rendimiento' in k:raise RuntimeError('No acceder a la etiqueta')
                return super().__getitem__(k)
        row=Row(id_parcela='A',municipio='M',conjunto_origen='PREDICCION',rendimiento_t_ha='inventado')
        self.assertEqual(catalogue([row])['A']['municipio'],'M')

    def test_catalogo_duplicado_rechazado(self):
        r=dict(id_parcela='A',municipio='M',conjunto_origen='PREDICCION')
        with self.assertRaises(ValueError):catalogue([r,r])

    def test_no_sobre_escribir_destino(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);(p/'sentinel').write_text('conservar')
            with self.assertRaises(FileExistsError):run(p,p)
            self.assertEqual((p/'sentinel').read_text(),'conservar')

    def test_no_finito_no_se_acepta(self):
        for s in ['inf','-inf','abc']:
            with self.assertRaises(ValueError):number(s,'NDWI')
        self.assertIsNone(number('NaN','NDWI'))

    def test_auditoria_racional_independiente(self):
        seq=series()
        rational=[(o.fecha,F(str(o.ndvi)),F(str(o.ndwi)),F(str(o.nube))) for o in seq]
        a=exact_profile(rational,START);b=profile(seq,START)
        self.assertEqual(a['fecha_maximo'],b['fecha_maximo'])
        self.assertEqual(a['fechas_post'],b['fechas_post'])
        self.assertAlmostEqual(float(a['contraste_ndwi']),b['contraste_ndwi'],places=14)

    def test_lector_no_acepta_fecha_duplicada(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'a.csv'
            p.write_text('ID_POLIGONO,sensor,fecha_captura,ndvi_promedio,ndwi_promedio,porcentaje_nubosidad\n'
                         'A,Sentinel-2,01/07/2025,0.5,0.2,0\nA,Sentinel-2,01/07/2025,0.6,0.3,0\n')
            with self.assertRaisesRegex(ValueError,'duplicad'):observations(p,['A'])

    def test_parcelas_no_se_mezclan(self):
        o=series()[0]
        with self.assertRaisesRegex(ValueError,'mezclar'):
            profile(series()+[Obs('B',o.fecha,.3,.2,0.)],START)

    def test_diseno_con_otro_intervalo_rechazado(self):
        import json
        p=Path(__file__).resolve().parents[1]/'registro/t15_d1/diseno.json'
        d=json.loads(p.read_text());validate_design(d)
        d['post_dias_inclusivos']=[10,50]
        with self.assertRaisesRegex(ValueError,'Diseño incompatible'):validate_design(d)

    def test_filtro_de_nubes_vacias(self):
        rows=series();o=rows[3];rows[3]=Obs(o.pid,o.fecha,o.ndvi,o.ndwi,None)
        self.assertEqual(profile(rows,START)['n_capturas'],10)

    def test_junio_no_suaviza_con_mayo(self):
        rows=series()
        old=Obs('A',date(2025,5,31),1.,1.,0.)
        self.assertEqual(profile(rows+[old],date(2025,6,1)),profile(rows,date(2025,6,1)))


if __name__=='__main__':unittest.main()
