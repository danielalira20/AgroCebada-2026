import io
import unittest
import zipfile
from unittest.mock import patch
import numpy as np
import pandas as pd
from affine import Affine
import geopandas as gpd
from shapely.geometry import box
from scripts import diagnostico_fase3 as f


def valid(values,dates=None):
    dates=dates or pd.date_range('2025-04-01',periods=len(values),freq='7D')
    return pd.DataFrame(dict(f=pd.to_datetime(dates),ndvi_promedio=values,ndvi_std=[.1]*len(values),
        lai2_promedio=[2*v for v in values],ndwi_promedio=[.3]*len(values),
        vi6t_promedio=values,porcentaje_nubosidad=[0.]*len(values)))


class Numerical(unittest.TestCase):
    def test_median_endpoints(self):
        np.testing.assert_array_equal(f.suavizar([0.,1.,0.,1.]),[.5,0.,1.,.5])
    def test_one_point(self):
        np.testing.assert_array_equal(f.suavizar([.3]),[.3])
    def test_constant_curve(self):
        p=valid([.4]*5);r=f.resumen_independiente(p,p,'Planet',f.START['abr_oct'],f.END)
        self.assertEqual(r['ndvi_integral'],0);self.assertNotIn('ndvi_dia_inicio',r)
    def test_integral_physical_days(self):
        p=valid([.1,.2,.4,.8,.2]);r=f.resumen_independiente(p,p,'Planet',f.START['abr_oct'],f.END)
        v=f.suavizar(p.ndvi_promedio.to_list());base=min(v[:np.argmax(v)+1])
        self.assertAlmostEqual(r['ndvi_integral'],np.trapezoid(np.maximum(v-base,0),[0,7,14,21,28]))
    def test_less_than_five_not_cycle(self):
        p=valid([.2]*4);r=f.resumen_independiente(p,p,'Planet',f.START['abr_oct'],f.END)
        self.assertNotIn('ndvi_max',r);self.assertEqual(r['capturas'],4)
    def test_no_observations_not_zero_index(self):
        p=valid([]);r=f.resumen_independiente(p,p,'Landsat',f.START['abr_oct'],f.END)
        self.assertTrue(pd.isna(r['vi6t_mediana']));self.assertEqual(r['hueco_max'],213)
    def test_cloud_mean_includes_excluded(self):
        p=valid([.2]*5);allrows=p.copy();allrows.loc[0,'porcentaje_nubosidad']=100
        r=f.resumen_independiente(p,allrows,'Planet',f.START['abr_oct'],f.END)
        self.assertEqual(r['nubosidad_media'],20)
    def test_gap_has_borders(self):
        p=valid([.2,.3],['2025-05-01','2025-06-01']);r=f.resumen_independiente(p,p,'Landsat',f.START['abr_oct'],f.END)
        self.assertEqual(r['hueco_max'],152)
    def test_blank_preserved(self):
        self.assertEqual(f.contrastar('',np.nan,'x')['estado'],'vacio_conservado')
    def test_blank_not_zero(self):
        with self.assertRaises(ValueError):f.contrastar('',0,'x')
    def test_nonfinite_rejected(self):
        with self.assertRaises(ValueError):f.contrastar('1',np.inf,'x')
    def test_wrong_summary_rejected(self):
        with self.assertRaises(ValueError):f.contrastar('1',1.000001,'x')
    def test_spearman_ties(self):
        self.assertAlmostEqual(f.spearman([1,1,3,4],[4,4,2,1]),-1)
    def test_coverage_roundoff_not_false_variation(self):
        self.assertEqual(f.cobertura_analisis(.999999999998),1.)
        self.assertEqual(f.cobertura_analisis(.8),.8)
    def test_constant_correlation_missing(self):
        self.assertEqual(f.spearman([1,1,1],[2,3,4]),'')
    def test_no_duplicate_ids(self):
        with self.assertRaises(ValueError):f.index([{'id_parcela':'x'},{'id_parcela':'x'}])
    def test_grid_fraction_split_original_not_projected_chord(self):
        g=gpd.GeoDataFrame({'ID_POLIGON':['x']},geometry=[box(-98.401,19.801,-98.399,19.803)],crs=4326).set_index('ID_POLIGON')
        a=Affine(.05,0,-99.95,0,-.05,21.4)
        rows,_,_=f.celdas(g,a)
        self.assertEqual(rows['x']['celdas_tocadas'],2)
        self.assertAlmostEqual(rows['x']['fraccion_celda_principal'],.5,places=4)
    def test_no_reserved_error_forcing(self):
        q=[{'id_parcela':'reserved'}]
        with self.assertRaises(ValueError):f.asociaciones(q,[])


class OriginalGuard(unittest.TestCase):
    def fixture(self,mutation=None):
        basic=[];pro=[]
        for sensor,(source,_,indices,ref) in f.t06.SENSORES.items():
            row={'ID_POLIGONO':'x','fecha_captura':'01/04/2025','sensor':sensor,'porcentaje_nubosidad':0}
            for name in indices:
                for stat in f.t06.ESTADISTICOS:row[name+'_'+stat]=.1 if stat=='std' else .4
            (basic if source=='BASICO' else pro).append(row)
        if mutation:mutation(basic,pro)
        mem=io.BytesIO()
        with zipfile.ZipFile(mem,'w') as z:
            for source,rows in [('BASICO',basic),('PRO',pro)]:
                z.writestr('DATASET_RETO_AGRO_2026/'+f.t06.ARCHIVOS[source],pd.DataFrame(rows).to_csv(index=False))
        mem.seek(0);return zipfile.ZipFile(mem)
    def test_valid_source_separated(self):
        with self.fixture() as z:s,_=f.crudos(z,{'x'})
        self.assertEqual(set(s),{'Planet','Sentinel-2','Landsat'})
    def test_unknown_id(self):
        with self.fixture() as z:
            with self.assertRaises(ValueError):f.crudos(z,{'y'})
    def test_duplicate_dates(self):
        with self.fixture(lambda b,p:p.append(p[0].copy())) as z:
            with self.assertRaises(ValueError):f.crudos(z,{'x'})
    def test_wrong_cloud_unit(self):
        with self.fixture(lambda b,p:p[0].update(porcentaje_nubosidad=101)) as z:
            with self.assertRaises(ValueError):f.crudos(z,{'x'})
    def test_ndvi_wrong_unit(self):
        with self.fixture(lambda b,p:p[0].update(ndvi_promedio=40)) as z:
            with self.assertRaises(ValueError):f.crudos(z,{'x'})
    def test_cloud100_with_data(self):
        with self.fixture(lambda b,p:p[0].update(porcentaje_nubosidad=100)) as z:
            with self.assertRaises(ValueError):f.crudos(z,{'x'})
    def test_mixed_sensor_values(self):
        with self.fixture(lambda b,p:b[1].update(ndvi_promedio=.4)) as z:
            with self.assertRaises(ValueError):f.crudos(z,{'x'})
    def test_after_cut_original_preserved(self):
        with self.fixture(lambda b,p:p[0].update(fecha_captura='01/11/2025')) as z:s,_=f.crudos(z,{'x'})
        self.assertTrue(s['Planet'].posterior_al_corte.iloc[0])


if __name__=='__main__':unittest.main()
