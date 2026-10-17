"""QA local del recorte CEM3 fijado: cobertura y soporte, sin atributos/modelos/y."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

import geopandas as gpd
import numpy as np
import rasterio
from rasterio.features import geometry_mask, geometry_window
from shapely.geometry import box
from pyproj import network

DEM_SHA='5f315dd32f7984c0c8f0bdd12f8bc22c014fd097473e2497e30d3be6f648be95'
SHP_SHA='8f8001a4bc4da00c2fcc0797536e94183d1abc88e4a797a7c63bcd2b65f29f29'
SHAPE_SHA={'Parcelas_Reto_AGC_CONJUNTO.prj': 'a02a27b1d1982c8516d83398e85a3c8b1aef1713c13ef4d84d7bde17430c07c4', 'Parcelas_Reto_AGC_CONJUNTO.shx': 'b03e99bc1c619fd9351693091558f549e0b75220f41e1c3b6343dbc41cb7d1f7', 'Parcelas_Reto_AGC_CONJUNTO.cpg': '3ad3031f5503a4404af825262ee8232cc04d4ea6683d42c5dd0a2f2a27ac9824', 'Parcelas_Reto_AGC_CONJUNTO.shp': '8f8001a4bc4da00c2fcc0797536e94183d1abc88e4a797a7c63bcd2b65f29f29', 'Parcelas_Reto_AGC_CONJUNTO.dbf': '9b7d9e06beb70c688c59d4c2e4227ef851596e3382af7d5566b9c669dc35debb'}


def require(ok,message):
    if not ok:raise ValueError(message)


def sha(path):
    digest=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):digest.update(block)
    return digest.hexdigest()


def run(root,raster,output):
    root,raster,output=Path(root).resolve(),Path(raster).resolve(),Path(output).resolve()
    require(raster.suffix.lower() in ['.tif','.tiff'] and raster.is_file(),'Sólo TIFF local ya descargado')
    require(sha(raster)==DEM_SHA,'Otro DEM: registrar una nueva fuente antes de usar')
    require(not output.exists(),'Destino existente: conservarlo')
    require(not output.is_relative_to(root) or output.is_relative_to(root/'reports'),'Dentro del repo sólo reports/')
    shape=root/'data/raw/DATASET_RETO_AGRO_2026/Parcelas_Reto_AGC_CONJUNTO_70_30/Parcelas_Reto_AGC_CONJUNTO.shp'
    for name,expected in SHAPE_SHA.items():
        require(sha(shape.parent/name)==expected,'Original vectorial modificado: '+name)
    network.set_network_enabled(False)
    g=gpd.read_file(shape,columns=['ID_POLIGON'],engine='pyogrio')
    with (root/'registro/t07/catalogo_base.csv').open(encoding='utf-8-sig') as stream:
        ids={r['id_parcela'] for r in csv.DictReader(stream)}
    require(len(g)==g.ID_POLIGON.nunique()==197 and set(g.ID_POLIGON)==ids,'Catálogo/IDs distintos')
    require(g.crs.to_epsg()==4326 and g.geometry.is_valid.all() and not g.geometry.is_empty.any(),'CRS/geometría inválidos; no reparar aquí')
    rows=[]
    with rasterio.Env(GDAL_CACHEMAX=32*1024*1024):
        with rasterio.open(raster,driver='GTiff') as ds:
            require(ds.crs.to_epsg()==4326 and ds.count==1 and ds.shape==(3601,3601),'Esquema del recorte distinto')
            require(ds.dtypes==('int16',) and ds.nodata==-32768,'Tipo/NoData no corresponde a esta fuente')
            arr=ds.read(1,masked=True)
            require(np.isfinite(arr.compressed()).all(),'Elevación no finita')
            regional_valid=int(arr.count());total=int(arr.size)
            minimum,maximum=int(arr.min()),int(arr.max())
            del arr
            region=gpd.GeoSeries([box(*ds.bounds).segmentize(.01)],crs=ds.crs).to_crs(32614).iloc[0]
            meters=g.to_crs(32614)
            distances=meters.geometry.map(lambda z:z.distance(region.boundary))
            covered=sum(region.covers(z) for z in meters.geometry)
            buffered=sum(region.covers(z.buffer(175)) for z in meters.geometry)
            for item in g.sort_values('ID_POLIGON').itertuples():
                window=geometry_window(ds,[item.geometry]);a=ds.read(1,window=window,masked=True)
                mask=geometry_mask([item.geometry],out_shape=a.shape,transform=ds.window_transform(window),
                                   invert=True,all_touched=True)
                values=a[mask].compressed()
                require(len(values)>0,'Parcela sin dato: registrar antes de derivar atributos')
                rows.append(dict(id_parcela=item.ID_POLIGON,uso='QA_soporte_no_predictor',
                    criterio_pixel='all_touched_solo_diagnostico_no_media_fisica',n_celdas_tocadas=int(mask.sum()),
                    n_celdas_validas=len(values),n_elevaciones_enteras_distintas=len(np.unique(values)),
                    rango_valor_elevacion=int(values.max())-int(values.min())))
            metadata=dict(CRS=str(ds.crs),resolucion_angular=list(ds.res),nodata=ds.nodata,
                          unidad_Z_en_TIFF=ds.units[0],bandas=ds.count,tipo=ds.dtypes[0],shape=list(ds.shape))
    output.mkdir(parents=True)
    with (output/'soporte_raster_por_parcela.csv').open('x',newline='',encoding='utf-8') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]),lineterminator='\n');writer.writeheader();writer.writerows(rows)
    report=dict(schema='INEGI_recorte_QA_local_v1',DEM_sha256=DEM_SHA,SHP_sha256=SHP_SHA,
        fuentes_vectoriales_sha256=SHAPE_SHA,n_parcelas=197,IDs_conciliados_T07=True,geometrias_validas_sin_reparar=197,
        parcelas_completas_en_recorte=covered,parcelas_con_margen_175m=buffered,
        distancia_minima_al_borde_m=float(distances.min()),celdas_regionales_validas=regional_valid,
        celdas_regionales_totales=total,minimo_valor=minimum,maximo_valor=maximum,
        celdas_tocadas_min=min(r['n_celdas_tocadas'] for r in rows),
        celdas_tocadas_mediana=float(np.median([r['n_celdas_tocadas'] for r in rows])),
        celdas_tocadas_max=max(r['n_celdas_tocadas'] for r in rows),
        parcelas_con_valor_constante=sum(r['n_elevaciones_enteras_distintas']==1 for r in rows),
        metadatos=metadata,atributos_E2_extraidos=False,rendimientos_utilizados=False,
        no_demuestra_mejora_MAE=True,codigo_sha256=sha(__file__),
        soporte_csv_sha256=sha(output/'soporte_raster_por_parcela.csv'))
    (output/'verificacion_recorte.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--raiz',type=Path,default=Path(__file__).resolve().parents[1])
    parser.add_argument('--raster',type=Path,required=True);parser.add_argument('--salida',type=Path,required=True)
    args=parser.parse_args();print(json.dumps(run(args.raiz,args.raster,args.salida),ensure_ascii=False,indent=2))
