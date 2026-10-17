"""Oráculos físicos y guardias E2; superficies matemáticas, nunca rendimientos."""
import ast
import json
import math
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import numpy as np
import rasterio
from rasterio.io import MemoryFile
from rasterio.vrt import WarpedVRT
from rasterio.enums import Resampling
from rasterio.transform import Affine
from shapely.geometry import box
import t15_e2_extraer as e
import t15_e2_auditar as audit


class TestE2(unittest.TestCase):
    def surface(self,p=0,q=0,z0=2000):
        y,x=np.mgrid[-25:26,-25:26]
        return z0+15*x*p-15*y*q

    def test_constant_zero_and_offset(self):
        for z0 in [0,100,2500]:
            a=e.focal(self.surface(z0=z0),np.ones((51,51),bool))
            np.testing.assert_array_equal(a[:4,25,25],0)
            self.assertEqual(a[4,25,25],1)

    def test_ramps_and_cardinal_signs(self):
        for p,q in [(1,0),(-1,0),(0,1),(0,-1),(.1,-.2)]:
            a=e.focal(self.surface(p,q),np.ones((51,51),bool))
            self.assertAlmostEqual(a[0,25,25],0,places=10)
            np.testing.assert_allclose(a[1:3,25,25],[-p/math.sqrt(1+p*p+q*q),-q/math.sqrt(1+p*p+q*q)],atol=1e-12)

    def test_bowl_exact_oracle(self):
        y,x=np.mgrid[-25:26,-25:26];z=225*(x*x+y*y)
        a=e.focal(z,np.ones(z.shape,bool))
        self.assertAlmostEqual(a[0,25,25],-900675/79,places=10)
        self.assertEqual(a[1,25,25],0)

    def test_zoffset_invariance(self):
        z=self.surface(.3,-.7);y,x=np.mgrid[-25:26,-25:26];z+=x*x*.1+y*y*.2
        a=e.focal(z,np.ones(z.shape,bool));b=e.focal(z+10000,np.ones(z.shape,bool))
        np.testing.assert_allclose(a[:4,10:-10,10:-10],b[:4,10:-10,10:-10],atol=5e-11,rtol=0)

    def test_true_north_rotation_scale(self):
        gamma=.02;k=.9997;p,q=math.sin(gamma),-math.cos(gamma)
        a=e.focal(self.surface(p,q),np.ones((51,51),bool),k,gamma)
        np.testing.assert_allclose(a[1:3,25,25],[0,k/math.sqrt(1+k*k)],atol=1e-12)

    def test_no_slope_threshold(self):
        a=e.focal(self.surface(p=1e-10,z0=0),np.ones((51,51),bool))
        self.assertLess(a[1,25,25],0);self.assertEqual(a[4,25,25],0)

    def test_nodata_tpi_propagates_exact_circle(self):
        z=self.surface();valid=np.ones(z.shape,bool);valid[25,35]=False
        a=e.focal(z,valid);self.assertEqual(a[0,25,25],e.NODATA)
        self.assertNotEqual(a[1,25,25],e.NODATA)
        valid[:]=True;valid[35,35]=False
        a=e.focal(z,valid);self.assertEqual(a[0,25,25],0)  # square corner outside disk.

    def test_nodata_horn_and_center(self):
        z=self.surface();valid=np.ones(z.shape,bool);valid[24,24]=False
        a=e.focal(z,valid);np.testing.assert_array_equal(a[:3,25,25],e.NODATA)
        valid[:]=True;valid[25,25]=False
        a=e.focal(z,valid);np.testing.assert_array_equal(a[:,25,25],e.NODATA)

    def test_edges_not_reflected(self):
        a=e.focal(self.surface(),np.ones((51,51),bool))
        self.assertEqual(a[0,9,25],e.NODATA);self.assertEqual(a[0,10,25],0)
        self.assertEqual(a[1,0,25],e.NODATA);self.assertEqual(a[1,1,25],0)

    def test_different_tiles_same_interior(self):
        rng=np.random.default_rng(20261016);z=rng.normal(2000,10,(97,103));valid=np.ones(z.shape,bool)
        full=e.focal(z,valid)
        for tile in [17,32]:
            for r in range(10,87,tile):
                for c in range(10,93,tile):
                    rr,cc=min(r+tile,87),min(c+tile,93)
                    part=e.focal(z[r-10:rr+10,c-10:cc+10],valid[r-10:rr+10,c-10:cc+10])
                    np.testing.assert_array_equal(part[:,10:-10,10:-10],full[:,r:rr,c:cc])

    def test_partial_cell80_20_and_touch_zero(self):
        t=Affine(15,0,0,0,-15,30)
        rr,cc,aa=e.cell_areas(box(3,15,18,30),t,(2,2))
        np.testing.assert_array_equal(rr,[0,0]);np.testing.assert_array_equal(cc,[0,1])
        np.testing.assert_allclose(aa,[180,45],rtol=0,atol=1e-12)
        self.assertEqual(np.dot(aa,[100,200])/aa.sum(),120)
        _,_,area=e.cell_areas(box(0,15,15,30),t,(2,2));self.assertEqual(len(area),1)

    def test_outside_rejected(self):
        with self.assertRaisesRegex(ValueError,'fuera'):
            e.cell_areas(box(-1,0,10,20),Affine(15,0,0,0,-15,30),(2,2))

    def test_strict_warp_mask_and_zero_real(self):
        np.testing.assert_array_equal(e.strict_warp_support(np.array([0.,100.,np.nan,e.NODATA]),
                      np.array([1.,.75,1.,1.])),[0,e.NODATA,e.NODATA,e.NODATA])

    def test_bilinear_nodata_not_renormalized(self):
        profile=dict(driver='GTiff',width=4,height=4,count=1,dtype='float64',transform=Affine(15,0,0,0,-15,60),crs=32614)
        with MemoryFile() as zm, MemoryFile() as mm:
            z=np.full((4,4),100.);z[1,1]=-32768
            with zm.open(**profile,nodata=-32768) as f:f.write(z,1)
            with mm.open(**profile) as f:f.write((z!=-32768).astype(float),1)
            with zm.open() as zs,mm.open() as ms:
                kw=dict(crs=32614,width=4,height=4,transform=Affine(15,0,3.75,0,-15,56.25),resampling=Resampling.bilinear,tolerance=1e-12,dtype='float64')
                with WarpedVRT(zs,nodata=e.NODATA,**kw) as zz,WarpedVRT(ms,src_nodata=None,nodata=0,**kw) as mv:
                    actual,support=zz.read(1),mv.read(1)
                    self.assertGreater(support[0,0],0);self.assertLess(support[0,0],1)
                    self.assertEqual(actual[0,0],100.)
                    self.assertEqual(e.strict_warp_support(actual,support)[0,0],e.NODATA)

    def test_independent_polar_oracle(self):
        z=self.surface(.2,-.1)
        k,g=.9996,.005;a=e.focal(z,np.ones(z.shape,bool),k,g)
        b=audit.independent_values(z,np.array([25]),np.array([25]),[k],[g])
        np.testing.assert_allclose(a[:,25,25],b[0],atol=1e-12,rtol=0)

    def test_norm_and_circular_mean(self):
        for p,q in [(1,2),(0,0),(1e7,-1e7)]:
            a=e.focal(self.surface(p,q),np.ones((51,51),bool))
            self.assertLessEqual(math.hypot(*a[1:3,25,25]),1+1e-12)
        angles=np.radians([359,1]);east=np.mean(np.sin(angles));north=np.mean(np.cos(angles))
        self.assertAlmostEqual(east,0);self.assertGreater(north,.99)

    def test_source_hash_guards(self):
        root=Path(__file__).resolve().parents[1]
        # All 34 common hashes, DEM and five vector files protected; mutations fail before GIS work.
        real=e.sha
        c=json.loads((root/'registro/t15_e2/contrato_tecnico_v1.json').read_text())
        targets=list(c['fuentes_sha256'])+[c['fuente']['ruta_relativa']]+[
            c['vectores']['directorio_relativo']+'/'+name for name in c['vectores']['archivos_sha256']]
        for target in targets:
            with self.subTest(source=target),patch.object(e,'sha',side_effect=lambda p: '0'*64 if Path(p)==root/target else real(p)):
                with self.assertRaises(ValueError):e.validate_inputs(root)

    def test_existing_output_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError,'existente'):e.extract(Path(tmp),Path(tmp))

    def test_real_polygon_z_zero_preserves_xy(self):
        import shapely
        root=Path(__file__).resolve().parents[1]
        c=json.loads((root/'registro/t15_e2/contrato_tecnico_v1.json').read_text())
        result=e.load_plots(root,c)
        self.assertEqual(len(result),197);self.assertFalse(result.has_z.any())
        self.assertTrue(result.is_valid.all());self.assertEqual(result.crs.to_epsg(),32614)
        original=e.gpd.read_file(root/c['vectores']['directorio_relativo']/'Parcelas_Reto_AGC_CONJUNTO.shp',columns=['ID_POLIGON'])
        original=original.sort_values('ID_POLIGON')
        coords=shapely.get_coordinates(original.geometry.force_2d().segmentize(.0001))
        restored=shapely.get_coordinates(result.to_crs(4326).geometry)
        np.testing.assert_allclose(coords,restored,atol=5e-13,rtol=0)

    def test_vector_z_nonzero_blocks(self):
        import shapely
        root=Path(__file__).resolve().parents[1]
        c=json.loads((root/'registro/t15_e2/contrato_tecnico_v1.json').read_text())
        g=e.gpd.read_file(root/c['vectores']['directorio_relativo']/'Parcelas_Reto_AGC_CONJUNTO.shp',columns=['ID_POLIGON'])
        g.loc[0,'geometry']=shapely.force_3d(shapely.force_2d(g.geometry.iloc[0]),z=1.)
        with patch.object(e.gpd,'read_file',return_value=g):
            with self.assertRaisesRegex(ValueError,'Z vectorial'):e.load_plots(root,c)

    def test_duplicate_id_blocks(self):
        root=Path(__file__).resolve().parents[1]
        c=json.loads((root/'registro/t15_e2/contrato_tecnico_v1.json').read_text())
        g=e.gpd.read_file(root/c['vectores']['directorio_relativo']/'Parcelas_Reto_AGC_CONJUNTO.shp',columns=['ID_POLIGON'])
        g.loc[0,'ID_POLIGON']=g.ID_POLIGON.iloc[1]
        with patch.object(e.gpd,'read_file',return_value=g):
            with self.assertRaisesRegex(ValueError,'IDs'):e.load_plots(root,c)

    def test_csv_no_nan_17digits(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'a.csv';e.write_csv(p,['id','v'],[dict(id='A',v=math.nan),dict(id='B',v=1.2345678901234567)])
            self.assertEqual(p.read_bytes(),b'id,v\nA,\nB,1.2345678901234567\n')

    def test_auditor_no_producer_import_or_fitting(self):
        source=Path(audit.__file__).read_text();tree=ast.parse(source)
        imported=[n.module or '' for n in ast.walk(tree) if isinstance(n,ast.ImportFrom)]
        imported += [x.name for n in ast.walk(tree) if isinstance(n,ast.Import) for x in n.names]
        self.assertFalse(any('t15_e2_extraer' in x or 'sklearn' in x for x in imported))
        self.assertNotIn('rendimiento_t_ha',source)


if __name__=='__main__':unittest.main()
