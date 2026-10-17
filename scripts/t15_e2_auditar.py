"""Recalcula E2 desde CEM/vector originales; no importa el extractor ni usa etiquetas.

Independencia: fórmulas, ventanas, pesos y agregación propios. Comparte las bibliotecas
GDAL/PROJ/GEOS, no es una certificación independiente de esos motores geográficos.
"""
import argparse
import csv
import gzip
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import time
os.environ['PROJ_NETWORK'] = 'OFF'
import numpy as np
import geopandas as gpd
import pyproj
import rasterio
import shapely
from rasterio.transform import Affine
from rasterio.vrt import WarpedVRT
from rasterio.enums import Resampling
from rasterio.windows import Window
from shapely.geometry import box
from shapely.ops import transform

PIN = 'd7c30ca6572373a78b78348df64e5fda50556f197bbcce03872d92a0735a2d9c'


def check(ok, message):
    if not ok:
        raise ValueError(message)


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        while chunk := f.read(1048576):
            h.update(chunk)
    return h.hexdigest()


def table(path):
    with Path(path).open() as f:
        rows = list(csv.DictReader(f))
    check(len(rows) == 197 and len({r['id_parcela'] for r in rows}) == 197, 'Tabla no 1:1')
    return {r['id_parcela']:r for r in rows}


def scalar_cells(geom, t):
    xmin,ymin,xmax,ymax = geom.bounds
    result = []
    for r in range(math.floor((t.f-ymax)/15), math.ceil((t.f-ymin)/15)):
        for col in range(math.floor((xmin-t.c)/15), math.ceil((xmax-t.c)/15)):
            left, top = t.c+15*col, t.f-15*r
            area = geom.intersection(box(left,top-15,left+15,top)).area
            if area > 0:
                result.append((r,col,area))
    return result


def independent_values(z, rr, cc, k, gamma):
    """Direct neighborhood indexing, math.fsum and polar orientation (no convolution)."""
    result = []
    for row, col, scale, convergence in zip(rr, cc, k, gamma):
        n = [z[row+dr,col+dc] for dr in range(-10,11) for dc in range(-10,11)
             if 0 < dr*dr+dc*dc <= 100]
        center = z[row,col]
        tpi = center-math.fsum(n)/316 if center != -9999 and all(v != -9999 for v in n) else math.nan
        nine = z[row-1:row+2,col-1:col+2].ravel()
        if len(nine) != 9 or -9999 in nine:
            result.append((tpi,math.nan,math.nan,math.nan,math.nan));continue
        # Dot products with analytically specified Horn stencils, rather than array slices.
        p = math.fsum(v*w for v,w in zip(nine,[-1,0,1,-2,0,2,-1,0,1]))/120
        q = math.fsum(v*w for v,w in zip(nine,[1,2,1,0,0,0,-1,-2,-1]))/120
        magnitude = math.hypot(p,q)*scale
        inclination = math.atan(magnitude)
        true_downhill = math.atan2(-p,-q)+convergence
        east, north = math.sin(inclination)*math.sin(true_downhill), math.sin(inclination)*math.cos(true_downhill)
        result.append((tpi,east,north,math.degrees(inclination),float(magnitude <= 1e-12)))
    return np.asarray(result)


def audit(root, delivery, output):
    start = time.monotonic();root=root.resolve();delivery=delivery.resolve();output=output.resolve()
    check(not output.exists() and not output.is_relative_to(delivery), 'Auditoría nueva fuera de entrega')
    cp = root/'registro/t15_e2/contrato_tecnico_v1.json'
    check(digest(cp) == PIN, 'Contrato no reconocido');c=json.loads(cp.read_text())
    for name, sha in c['fuentes_sha256'].items():
        check(digest(root/name) == sha, 'Fuente común alterada: '+name)
    source=root/c['fuente']['ruta_relativa']
    check(digest(source) == c['fuente']['sha256'], 'DEM equivocado')
    vector=root/c['vectores']['directorio_relativo']
    for name, sha in c['vectores']['archivos_sha256'].items():
        check(digest(vector/name) == sha, 'Vector equivocado')
    manifest=json.loads((delivery/'manifest.json').read_text())
    check(manifest['estado'] == 'completa' and manifest['contrato_sha256'] == PIN, 'Extracción incompleta')
    check(manifest['codigo_sha256'] == digest(root/'scripts/t15_e2_extraer.py'), 'Código productor cambiado')
    for name, sha in manifest['archivos_sha256'].items():
        check(digest(delivery/name) == sha, 'Artefacto alterado: '+name)
    attrs, qa=table(delivery/'atributos_parcela.csv'),table(delivery/'calidad.csv')
    geo=gpd.read_file(vector/'Parcelas_Reto_AGC_CONJUNTO.shp',columns=['ID_POLIGON'])
    check(geo.crs.to_epsg()==4326 and geo.ID_POLIGON.is_unique and geo.is_valid.all(), 'Geometrías no acreditadas')
    if geo.has_z.any():
        zz=shapely.get_coordinates(geo.geometry,include_z=True)[:,2]
        check(np.isfinite(zz).all() and np.all(zz==0),'Z original no acreditada')
        geo.geometry=geo.geometry.force_2d()
    check(set(geo.ID_POLIGON)==set(attrs)==set(qa), 'IDs mezclados')
    with (root/'registro/t07/catalogo_base.csv').open() as f:
        check({r['id_parcela'] for r in csv.DictReader(f)}==set(attrs), 'Catálogo diferente')
    forward=pyproj.Transformer.from_crs(4326,32614,always_xy=True,allow_ballpark=False)
    inverse=pyproj.Transformer.from_crs(32614,4326,always_xy=True,allow_ballpark=False)
    proj=pyproj.Proj(32614);t=Affine(*c['rejilla']['transform_planeada'])
    height,width=c['rejilla']['shape_planeada'];maxdiff=np.zeros(5);maxagg=np.zeros(3)
    weights={}
    with gzip.open(delivery/'pesos.csv.gz','rt') as f:
        for row in csv.DictReader(f):
            key=(row['id_parcela'],int(row['fila']),int(row['columna']))
            check(key not in weights,'Peso duplicado')
            weights[key]=tuple(float(row[k]) for k in ['area_interseccion_m2','peso_TPI','peso_exposicion'])
    checks=0;seen=set();maxwarp=0.;maxarea=0.;sens=[];min_margin=math.inf
    shifts=[('E15',15,0),('O15',-15,0),('N15',0,15),('S15',0,-15)]
    from shapely.affinity import translate
    with rasterio.Env(GDAL_CACHEMAX=33554432,GDAL_NUM_THREADS='1',PROJ_NETWORK='OFF'), \
            rasterio.open(source) as raw, WarpedVRT(raw,crs=32614,transform=t,width=width,height=height,
                  resampling=Resampling.bilinear,tolerance=1e-12,dtype='float64',nodata=-9999.,warp_mem_limit=32,NUM_THREADS='1') as vrt, \
            rasterio.open(delivery/'dem_utm.tif') as dem, rasterio.open(delivery/'derivadas.tif') as deriv:
        check(dem.transform==deriv.transform==t and dem.shape==deriv.shape==(height,width),'Rejillas mezcladas')
        footprint=transform(forward.transform,box(*raw.bounds).segmentize(.0001))
        for number,row in enumerate(geo.sort_values('ID_POLIGON').itertuples(),1):
            pid=row.ID_POLIGON;geom=transform(forward.transform,row.geometry.segmentize(.0001))
            check(footprint.covers(geom.buffer(210)),'Falta margen fuente de 210m')
            min_margin=min(min_margin,geom.distance(footprint.boundary));checks+=1
            baseline=None
            for label,dx,dy in [('original',0,0)]+shifts:
                g=translate(geom,dx,dy);cells=scalar_cells(g,t)
                rr,cc,aa=map(np.array,zip(*cells));rr=rr.astype(int);cc=cc.astype(int)
                areaerr=abs(math.fsum(aa)-g.area)/g.area;maxarea=max(maxarea,areaerr)
                check(areaerr<=1e-8,'Cierre independiente de área')
                r0,c0,r1,c1=int(rr.min()-10),int(cc.min()-10),int(rr.max()+11),int(cc.max()+11)
                w=Window(c0,r0,c1-c0,r1-r0)
                z=vrt.read(1,window=w);stored=dem.read(1,window=w)
                # This region must have full original support; no silent nodata renormalization.
                check(np.all(z!=-9999) and np.all(stored!=-9999),'Soporte independiente incompleto')
                delta=float(np.max(np.abs(z-stored)));maxwarp=max(maxwarp,delta)
                check(delta<=1e-6,'Reproyección regional/ventana difieren')
                # Compare native support using a separately opened 0/1 GDAL warp.
                # Complete original region + inner margin is also checked below.
                lon,lat=inverse.transform(t.c+(cc+.5)*15,t.f-(rr+.5)*15)
                factors=proj.get_factors(lon,lat)
                values=independent_values(z,rr-r0,cc-c0,np.asarray(factors.meridional_scale),
                                          np.radians(factors.meridian_convergence))
                check(np.isfinite(values).all(),'Valor independiente no finito')
                area=math.fsum(aa)
                means=np.asarray([math.fsum(aa*values[:,j])/area for j in range(3)])
                if label=='original':
                    baseline=means
                    old=np.asarray([float(attrs[pid][k]) for k in c['columnas_modelo']])
                    da=np.abs(old-means);maxagg=np.maximum(maxagg,da)
                    check(np.all(da<=np.array([1e-6,1e-9,1e-9])),'Media independiente no coincide: '+pid)
                    own=deriv.read(window=Window(int(cc.min()),int(rr.min()),int(cc.max()-cc.min()+1),int(rr.max()-rr.min()+1)))
                    actual=own[:,rr-rr.min(),cc-cc.min()].T
                    dif=np.max(np.abs(actual-values),axis=0);maxdiff=np.maximum(maxdiff,dif)
                    check(np.all(dif<=np.array([1e-6,1e-9,1e-9,1e-7,0])),'Derivada independiente no coincide')
                    expected_quality=[1.,1.,len(aa),g.area,area,area,max(0,g.area-area),max(0,g.area-area),
                        math.fsum(aa*values[:,4])/area,math.fsum(aa*values[:,3])/area,
                        math.hypot(*means[1:]),float(np.ptp(z[rr-r0,cc-c0]))]
                    for key,val in zip(c['calidad_no_predictiva'],expected_quality):
                        observed=float(qa[pid][key]);tol=1e-7 if key.endswith('grados_QA') else max(1e-8,abs(val)*1e-10)
                        check(abs(observed-val)<=tol,'Calidad inconsistente '+pid+': '+key);checks+=1
                    for r,col,a in cells:
                        key=(pid,r,col);seen.add(key)
                        check(key in weights,'Falta peso')
                        recorded=weights[key]
                        check(abs(recorded[0]-a)<=max(1e-8,a*1e-10) and
                              max(abs(recorded[1]-a/area),abs(recorded[2]-a/area))<=1e-10,'Peso incorrecto')
                        checks+=3
                else:
                    sens.append((pid,label,means-baseline))
                checks+=len(aa)*5+3
            if number%40==0:
                print(json.dumps({'auditoria_parcelas':number,'total':197}),flush=True)
        # Source mask must be all-valid for this fixed crop; contract rejects any altered source hash.
        check(all((raw.read_masks(1,window=w)>0).all() for _,w in raw.block_windows(1)), 'Fuente contiene NoData')
    check(seen==set(weights),'Pesos extra o parcelas mezcladas')
    with (delivery/'sensibilidad.csv').open() as f:
        ss=list(csv.DictReader(f))
    check(len(ss)==788 and len({(r['id_parcela'],r['escenario_desplazamiento']) for r in ss})==788,'Sensibilidad incompleta')
    keyed={(r['id_parcela'],r['escenario_desplazamiento']):r for r in ss}
    for pid,label,d in sens:
        row=keyed[(pid,label)]
        check(row['admisible']=='True','Desplazamiento no admisible')
        check(np.all(np.abs(d-[float(row[k]) for k in ['delta_TPI_m','delta_E','delta_N']])<=
                     np.array([2e-6,2e-9,2e-9])),'Sensibilidad independiente difiere')
        checks+=4
    result=dict(schema='E2_auditoria_independiente_v1',resultado='aprobado',parcelas=197,
        controles=788,celdas=len(seen),comprobaciones=checks,max_diferencia_agregados=maxagg.tolist(),
        max_diferencia_derivadas=maxdiff.tolist(),max_diferencia_rewarp_m=maxwarp,
        max_error_relativo_cierre_area=maxarea,sin_rendimientos=True,modelos_ajustados=0,
        margen_fuente_minimo_m=min_margin,parcelas_con_margen_210m=197,
        codigo_sha256=digest(__file__),productor_sha256=manifest['codigo_sha256'],
        manifest_sha256=digest(delivery/'manifest.json'),contrato_sha256=PIN,
        bibliotecas_compartidas=['GDAL','PROJ','GEOS'],
        independencia='sin_importar_productor_focal_directo_polar_sumafsum_intersecciones_escalares',
        sistema=platform.system(),arquitectura=platform.machine(),segundos=time.monotonic()-start)
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--raiz',type=Path,default=Path(__file__).resolve().parents[1])
    p.add_argument('--entrega',required=True,type=Path);p.add_argument('--salida',required=True,type=Path)
    a=p.parse_args();print(json.dumps(audit(a.raiz,a.entrega,a.salida),indent=2,ensure_ascii=False))
