"""E2: relieve INEGI por área; sin rendimiento, ajuste ni selección de modelos."""
import argparse
import csv
import gzip
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import sys
import time

os.environ['PROJ_NETWORK'] = 'OFF'
import geopandas as gpd
import numpy as np
import pyproj
import rasterio
from rasterio.enums import Resampling
from rasterio.transform import Affine
from rasterio.vrt import WarpedVRT
from rasterio.windows import Window
from scipy.ndimage import convolve
import shapely
from shapely.affinity import translate
from shapely.ops import transform as transform_geometry

CONTRACT_SHA = 'd7c30ca6572373a78b78348df64e5fda50556f197bbcce03872d92a0735a2d9c'
NODATA = -9999.
ATTR = ['e2_tpi150_media_m', 'e2_exposicion_este_media', 'e2_exposicion_norte_media']
QA = ['cobertura_tpi_fraccion', 'cobertura_exposicion_fraccion',
      'n_celdas_interseccion_positiva', 'area_parcela_utm_m2', 'area_soporte_tpi_m2',
      'area_soporte_exposicion_m2', 'area_fuera_tpi_m2', 'area_fuera_exposicion_m2',
      'fraccion_plano_numerico', 'pendiente_media_grados_QA',
      'norma_resultante_exposicion_QA', 'rango_altitud_QA_m']
INV = pyproj.Transformer.from_crs(32614, 4326, always_xy=True, allow_ballpark=False)
FWD = pyproj.Transformer.from_crs(4326, 32614, always_xy=True, allow_ballpark=False)
PROJ = pyproj.Proj('EPSG:32614')


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for part in iter(lambda: stream.read(1024*1024), b''):
            h.update(part)
    return h.hexdigest()


def dump(path, obj):
    Path(path).write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False)+'\n')


def write_csv(path, columns, rows):
    with Path(path).open('w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, columns, lineterminator='\n');w.writeheader()
        for row in rows:
            w.writerow({k: (format(v, '.17g') if isinstance(v, (float, np.floating)) and math.isfinite(v)
                             else '' if isinstance(v, (float, np.floating)) else v) for k, v in row.items()})


def validate_inputs(root):
    path = root/'registro/t15_e2/contrato_tecnico_v1.json'
    require(sha(path) == CONTRACT_SHA, 'Contrato distinto: no extraer')
    c = json.loads(path.read_text())
    for name, digest in c['fuentes_sha256'].items():
        require(sha(root/name) == digest, 'Fuente común alterada: '+name)
    require(sha(root/c['fuente']['ruta_relativa']) == c['fuente']['sha256'], 'DEM no acreditado')
    for name, digest in c['vectores']['archivos_sha256'].items():
        require(sha(root/c['vectores']['directorio_relativo']/name) == digest, 'Vector no acreditado: '+name)
    return c


def load_plots(root, c):
    g = gpd.read_file(root/c['vectores']['directorio_relativo']/'Parcelas_Reto_AGC_CONJUNTO.shp',
                      columns=['ID_POLIGON'])
    require(g.crs is not None and g.crs.to_epsg() == 4326, 'CRS vector distinto')
    require(len(g) == 197 and not g.ID_POLIGON.isna().any() and g.ID_POLIGON.is_unique, 'IDs inválidos')
    with (root/'registro/t07/catalogo_base.csv').open() as f:
        ids = [r['id_parcela'] for r in csv.DictReader(f)]
    require(len(ids) == len(set(ids)) == 197 and set(ids) == set(g.ID_POLIGON), 'No coincide catálogo T07')
    require(g.geometry.notna().all() and (~g.geometry.is_empty).all() and g.is_valid.all(), 'Geometría inválida')
    require(g.geom_type.isin(['Polygon', 'MultiPolygon']).all(), 'Geometría no soportada')
    if g.has_z.any():
        z = shapely.get_coordinates(g.geometry, include_z=True)[:, 2]
        require(np.isfinite(z).all() and np.all(z == 0), 'Z vectorial no nula: requiere revisión')
        g.geometry = g.geometry.force_2d()  # Original Z is a constant zero placeholder, never an elevation.
    g.geometry = g.geometry.segmentize(.0001)
    g.geometry = g.geometry.map(lambda p: transform_geometry(FWD.transform, p))
    g = g.set_crs(32614, allow_override=True)  # Coordinates were transformed explicitly above.
    require(g.is_valid.all() and (g.area > 0).all(), 'Proyección inválida; no reparar')
    return g.sort_values('ID_POLIGON')


def strict_warp_support(z, support):
    valid = (support >= 1-1e-12) & (z != NODATA) & np.isfinite(z)
    return np.where(valid, z, NODATA)


def warp_dem(source, out, c):
    from rasterio.warp import transform_bounds
    grid = Affine(*c['rejilla']['transform_planeada'])
    height, width = c['rejilla']['shape_planeada']
    profile = dict(driver='GTiff', crs='EPSG:32614', transform=grid, width=width,
                   height=height, count=1, dtype='float64', nodata=NODATA,
                   tiled=True, blockxsize=256, blockysize=256, compress='deflate')
    with rasterio.open(source) as src:
        require(src.crs.to_epsg() == 4326 and src.dtypes == ('int16',) and src.count == 1
                and src.nodata == -32768 and src.shape == (3601, 3601), 'Metadatos DEM distintos')
        b = transform_bounds(src.crs, 'EPSG:32614', *src.bounds, densify_pts=21)
        expected = (15, 0, math.floor(b[0]/15)*15, 0, -15, math.ceil(b[3]/15)*15)
        require(tuple(grid)[:6] == expected and (height, width) ==
                (int((expected[5]-math.floor(b[1]/15)*15)/15), int((math.ceil(b[2]/15)*15-expected[2])/15)),
                'Rejilla planeada no reproducida')
        mask_path = out/'soporte_fuente.tif'
        mask_profile = src.profile.copy();mask_profile.update(dtype='float64', nodata=None, compress='deflate')
        valid_n = 0
        with rasterio.open(mask_path, 'w', **mask_profile) as masks:
            for _, w in src.block_windows(1):
                a = src.read(1, window=w);valid = (src.read_masks(1, window=w) > 0) & np.isfinite(a)
                masks.write(valid.astype('float64'), 1, window=w);valid_n += int(valid.sum())
        kwargs = dict(crs='EPSG:32614', transform=grid, height=height, width=width,
                      resampling=Resampling.bilinear, tolerance=1e-12, dtype='float64',
                      warp_mem_limit=32, NUM_THREADS='1')
        # An almost-exact transformer avoids the default 0.125-pixel approximation.
        with rasterio.open(mask_path) as ms, WarpedVRT(src, nodata=NODATA, **kwargs) as vz, \
                WarpedVRT(ms, src_nodata=None, nodata=0., **kwargs) as vm, \
                rasterio.open(out/'dem_utm.tif', 'w', **profile) as dst, \
                rasterio.open(out/'soporte_utm.tif', 'w', **dict(profile, nodata=None)) as support:
            for _, w in dst.block_windows(1):
                z, s = vz.read(1, window=w), vm.read(1, window=w)
                dst.write(strict_warp_support(z, s), 1, window=w);support.write(s, 1, window=w)
        return dict(transform=list(grid)[:6], shape=[height, width], validos_fuente=valid_n,
                    tolerancia_transformacion_pixeles=1e-12, GDAL=rasterio.__gdal_version__)


def focal(z, valid, k=1., gamma=0.):
    """All returned arrays have the original shape; edges without full halo invalid."""
    require(z.shape == valid.shape and z.ndim == 2, 'Máscara incompatible')
    dr, dc = np.mgrid[-10:11, -10:11]
    kernel = ((dr*dr+dc*dc > 0) & (dr*dr+dc*dc <= 100)).astype('float64')
    t_valid = valid & (convolve(valid.astype('int16'), kernel.astype('int16'), mode='constant', cval=0) == 316)
    tpi = z-convolve(np.where(valid, z, 0.), kernel, mode='constant', cval=0)/316
    h_valid = convolve(valid.astype('int16'), np.ones((3, 3), dtype='int16'), mode='constant', cval=0) == 9
    p = np.zeros(z.shape);q = np.zeros(z.shape)
    p[1:-1, 1:-1] = ((z[:-2, 2:]+2*z[1:-1, 2:]+z[2:, 2:])-
                      (z[:-2, :-2]+2*z[1:-1, :-2]+z[2:, :-2]))/120
    q[1:-1, 1:-1] = ((z[:-2, :-2]+2*z[:-2, 1:-1]+z[:-2, 2:])-
                      (z[2:, :-2]+2*z[2:, 1:-1]+z[2:, 2:]))/120
    kp, kq = k*p, k*q
    den = np.sqrt(1+kp*kp+kq*kq)
    east = (-kp*np.cos(gamma)-kq*np.sin(gamma))/den
    north = (kp*np.sin(gamma)-kq*np.cos(gamma))/den
    slope = np.degrees(np.arctan(np.hypot(kp, kq)))
    flat = (np.hypot(kp, kq) <= 1e-12).astype('float64')
    return np.stack([np.where(mask, v, NODATA) for v, mask in
                     [(tpi, t_valid), (east, h_valid), (north, h_valid), (slope, h_valid), (flat, h_valid)]])


def derive(out, tile=256):
    stats = [math.inf, -math.inf, math.inf, -math.inf]
    with rasterio.open(out/'dem_utm.tif') as src:
        profile = src.profile.copy();profile['count'] = 5
        with rasterio.open(out/'derivadas.tif', 'w', **profile) as dst:
            for r in range(0, src.height, tile):
                for col in range(0, src.width, tile):
                    hh, ww = min(tile, src.height-r), min(tile, src.width-col)
                    w = Window(col-10, r-10, ww+20, hh+20)
                    z = src.read(1, window=w, boundless=True, fill_value=NODATA)
                    rows, cols = np.meshgrid(np.arange(r-10, r+hh+10)+.5,
                                             np.arange(col-10, col+ww+10)+.5, indexing='ij')
                    lon, lat = INV.transform(src.transform.c+15*cols, src.transform.f-15*rows)
                    factors = PROJ.get_factors(lon, lat)
                    k = np.asarray(factors.meridional_scale);g = np.radians(factors.meridian_convergence)
                    require(np.isfinite(k).all() and np.max(np.abs(k-1)) <= .001 and
                            np.max(np.abs(k-np.asarray(factors.parallel_scale))) < 1e-8, 'Factores UTM no conformes')
                    result = focal(z, z != NODATA, k, g)[:, 10:-10, 10:-10]
                    dst.write(result, window=Window(col, r, ww, hh))
                    stats = [min(stats[0], float(k.min())), max(stats[1], float(k.max())),
                             min(stats[2], float(np.min(g))), max(stats[3], float(np.max(g)))]
                if r % (tile*4) == 0:
                    print(json.dumps({'etapa':'derivadas', 'fila':r, 'total':src.height}), flush=True)
    return dict(escala_min_max=stats[:2], convergencia_min_max_rad=stats[2:], tile=tile, halo=10)


def cell_areas(geom, transform, shape):
    xmin, ymin, xmax, ymax = geom.bounds
    c0, c1 = math.floor((xmin-transform.c)/15), math.ceil((xmax-transform.c)/15)
    r0, r1 = math.floor((transform.f-ymax)/15), math.ceil((transform.f-ymin)/15)
    require(r0 >= 0 and c0 >= 0 and r1 <= shape[0] and c1 <= shape[1], 'Parcela fuera de rejilla')
    rows, cols = np.meshgrid(np.arange(r0, r1), np.arange(c0, c1), indexing='ij')
    x, y = transform.c+15*cols.ravel(), transform.f-15*rows.ravel()
    cells = shapely.box(x, y-15, x+15, y)
    areas = shapely.area(shapely.intersection(cells, geom))
    keep = areas > 0
    return rows.ravel()[keep], cols.ravel()[keep], areas[keep]


def aggregate(geom, dem, derived):
    rows, cols, areas = cell_areas(geom, dem.transform, dem.shape)
    require(len(areas) > 0, 'Sin intersección positiva')
    require(abs(math.fsum(areas)-geom.area) <= 1e-8*geom.area, 'Las áreas no cierran')
    r0, c0, r1, c1 = rows.min(), cols.min(), rows.max()+1, cols.max()+1
    w = Window(int(c0), int(r0), int(c1-c0), int(r1-r0))
    a = derived.read(window=w)[:, rows-r0, cols-c0]
    z = dem.read(1, window=w)[rows-r0, cols-c0]
    valid_t, valid_h = a[0] != NODATA, (a[1] != NODATA) & (a[2] != NODATA)
    support = [math.fsum(areas[valid_t]), math.fsum(areas[valid_h])]
    cover = np.array(support)/geom.area
    require(np.all(cover <= 1+1e-8), 'Doble conteo de cobertura')
    values = [math.fsum(areas[m]*v[m])/s if s > 0 and cover[j] >= 1-1e-8 else math.nan
              for v, m, s, j in [(a[0], valid_t, support[0], 0), (a[1], valid_h, support[1], 1),
                                 (a[2], valid_h, support[1], 1)]]
    def mean_h(v):
        return math.fsum(areas[valid_h]*v[valid_h])/support[1] if support[1] > 0 else math.nan
    zvalid = z[z != NODATA]
    quality = list(cover)+[len(areas), geom.area]+support+[
        max(0., geom.area-support[0]), max(0., geom.area-support[1]), mean_h(a[4]), mean_h(a[3]),
        math.hypot(*values[1:]), float(np.ptp(zvalid)) if len(zvalid) else math.nan]
    weights = [(int(r), int(c), float(ar), float(ar/support[0]) if vt else 0.,
                float(ar/support[1]) if vh else 0.) for r, c, ar, vt, vh in zip(rows, cols, areas, valid_t, valid_h)]
    return values, quality, weights


def extract(root, out):
    root, out = root.resolve(), out.resolve()
    require(not out.exists(), 'Salida existente: no sobrescribir')
    require(not out.is_relative_to(root) or out.is_relative_to(root/'reports') or
            out.is_relative_to(root/'data/processed/t15_e2'), 'Salida sólo reports o data/processed/t15_e2')
    c = validate_inputs(root);plots = load_plots(root, c)
    out.mkdir(parents=True)
    dump(out/'estado.json', {'estado':'en_proceso', 'entrenamientos':0})
    start = time.monotonic()
    try:
        with rasterio.Env(GDAL_CACHEMAX=32*1024*1024, GDAL_NUM_THREADS='1', PROJ_NETWORK='OFF'):
            warp = warp_dem(root/c['fuente']['ruta_relativa'], out, c)
            deriv = derive(out)
            records, qualities, sensitivity, failures = [], [], [], []
            with rasterio.open(out/'dem_utm.tif') as dem, rasterio.open(out/'derivadas.tif') as der, \
                    gzip.open(out/'pesos.csv.gz', 'wt', encoding='utf-8', newline='') as f:
                writer = csv.writer(f, lineterminator='\n')
                writer.writerow(['id_parcela','fila','columna','area_interseccion_m2','peso_TPI','peso_exposicion'])
                for row in plots.itertuples():
                    pid, geom = row.ID_POLIGON, row.geometry
                    values, quality, weights = aggregate(geom, dem, der)
                    records.append(dict(zip(['id_parcela']+ATTR, [pid]+values)))
                    qualities.append(dict(zip(['id_parcela']+QA, [pid]+quality)))
                    if not all(math.isfinite(v) for v in values):
                        failures.append({'id_parcela':pid,'motivo':'soporte_incompleto'})
                    for ws in weights:
                        writer.writerow([pid]+[format(v,'.17g') if isinstance(v,float) else v for v in ws])
                    for label, dx, dy in [('E15',15,0),('O15',-15,0),('N15',0,15),('S15',0,-15)]:
                        shifted, q, _ = aggregate(translate(geom, dx, dy), dem, der)
                        delta = [a-b for a,b in zip(shifted, values)]
                        sensitivity.append(dict(zip(['id_parcela','escenario_desplazamiento','delta_TPI_m',
                              'delta_E','delta_N','admisible'], [pid,label]+delta+[all(math.isfinite(x) for x in shifted)])))
            write_csv(out/'atributos_parcela.csv', ['id_parcela']+ATTR, records)
            write_csv(out/'calidad.csv', ['id_parcela']+QA, qualities)
            write_csv(out/'sensibilidad.csv',list(sensitivity[0]),sensitivity)
        validate_inputs(root)  # Recheck originals and pinned common artifacts after extraction.
        manifest = dict(schema='E2_extraccion_v1', estado='completa' if not failures else 'no_admisible',
             parcelas=len(records), predictores=ATTR, sin_rendimientos=True, modelos_ajustados=0,
             habilita_entrenamiento=False, pendientes=['auditoria_independiente','reproduccion_Mac_Linux','adaptador_modelo','registro_y_solicitud_evaluacion'],
             contrato_sha256=CONTRACT_SHA, codigo_sha256=sha(__file__),
             fuente_sha256=c['fuente']['sha256'], vectores_sha256=c['vectores']['archivos_sha256'],
             warp=warp, derivadas=deriv, pipeline=FWD.definition, siempre_xy=True, PROJ_red=False,
             geometria='densificar_0.0001_grados_transformar_sin_reparar',
             unidad_z='m_segun_producto',datum_vertical='no_acreditado',disponibilidad_2025='no_acreditada',
             versiones=dict(python=platform.python_version(), sistema=platform.system(), arquitectura=platform.machine(),
                    numpy=np.__version__, geopandas=gpd.__version__, rasterio=rasterio.__version__,
                    GDAL=rasterio.__gdal_version__, PROJ=pyproj.proj_version_str, shapely=shapely.__version__),
             segundos=time.monotonic()-start, problemas=failures,
             archivos_sha256={p.name:sha(p) for p in sorted(out.iterdir()) if p.name != 'estado.json'})
        dump(out/'manifest.json',manifest)
        dump(out/'estado.json',dict(estado=manifest['estado'], entrenamientos=0))
        require(not failures, 'Extraído con soporte incompleto: no evaluar; consultar manifest')
        return manifest
    except Exception as exc:
        dump(out/'estado.json',dict(estado='fallido',error=str(exc),entrenamientos=0))
        raise


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--raiz',type=Path,default=Path(__file__).resolve().parents[1])
    p.add_argument('--salida',type=Path,required=True)
    a = p.parse_args()
    print(json.dumps(extract(a.raiz,a.salida),ensure_ascii=False,indent=2))
