"""Fase 3: calidad, geometrías y curvas originales; nunca ajusta un modelo."""
import argparse
from collections import defaultdict
import csv
import hashlib
import io
import json
import math
from pathlib import Path
import statistics
import tempfile
import zipfile

import geopandas as gpd
import numpy as np
import pandas as pd
from pyproj import Geod, Transformer
from rasterio.io import MemoryFile
from shapely.geometry import box
from shapely.ops import transform
from shapely.geometry.polygon import orient

from scripts.diagnostico_fuentes import exigir, hash_archivo, json_estricto
from scripts import diagnostico_fase0 as f0, diagnostico_fase1 as f1
from scripts import t06_satelite as t06

RAIZ = Path(__file__).resolve().parents[1]
DESIGN = 'registro/diagnostico/fase3_diseno.json'
DESIGN_SHA = '9807621f909e221deda4b2240e4f760877ad6d5c51ae11c4255c0e81079beec7'
T02 = 'analisis/auditoria_catalogo_y_etiquetas/tablas/'
ATLAS = 'analisis/exploracion_parcelas_qgis/capturas_parcelas_atlas/'
START = {'abr_oct':pd.Timestamp('2025-04-01'), 'jun_oct':pd.Timestamp('2025-06-01')}
END = pd.Timestamp('2025-10-31')


def lectura(rel):
    return f0.csv_completo(RAIZ / rel)


def index(rows, key='id_parcela'):
    out = {r[key]:r for r in rows}
    exigir(len(out)==len(rows), 'ID duplicado: '+key)
    return out


def fuentes():
    exigir(hash_archivo(RAIZ/DESIGN)==DESIGN_SHA, 'Diseño fase3 distinto')
    d = json_estricto(RAIZ/DESIGN)
    for rel, sha in d['archivos_fuente'].items():
        p=RAIZ/rel
        exigir(not p.is_symlink() and hash_archivo(p)==sha, 'Fuente fase3 distinta: '+rel)
    for phase in (1,2):
        m=json_estricto(RAIZ/f'registro/diagnostico/fase{phase}/manifest.json')
        for rel,sha in m['codigo_sha256'].items():
            exigir(hash_archivo(RAIZ/rel)==sha, 'Código previo distinto')
    return d


def crudos(outer, ids):
    """Leer sólo miembros conocidos; no extraer un árbol del ZIP ni mezclar sensores."""
    out={}; huellas=[]
    for source, filename in t06.ARCHIVOS.items():
        member='DATASET_RETO_AGRO_2026/'+filename
        payload=outer.read(member)
        huellas.append(dict(miembro=member,sha256=hashlib.sha256(payload).hexdigest(),bytes=len(payload)))
        raw=pd.read_csv(io.BytesIO(payload),encoding='utf-8-sig',dtype={'ID_POLIGONO':str,'fecha_captura':str})
        exigir(set(raw.ID_POLIGONO)==ids, 'Universo satélite incompleto/ajeno')
        allowed={s for s,(f,*_) in t06.SENSORES.items() if f==source}
        exigir(set(raw.sensor)==allowed, 'Sensor inesperado')
        for sensor in sorted(allowed):
            x=raw.loc[raw.sensor==sensor].copy()
            cols=[i+'_'+e for i in t06.SENSORES[sensor][2] for e in t06.ESTADISTICOS]
            other=[c for c in x if c.endswith(tuple('_'+e for e in t06.ESTADISTICOS)) and c not in cols]
            exigir(x[other].isna().all().all(), 'Valores mezclados entre sensores')
            dates=pd.to_datetime(x.fecha_captura,format='%d/%m/%Y',errors='raise')
            exigir(not dates.isna().any() and not x.assign(date=dates).duplicated(['ID_POLIGONO','date']).any(), 'Fechas duplicadas/vacías por sensor e ID')
            cloud=x.porcentaje_nubosidad
            exigir(cloud.dropna().between(0,100).all(), 'Nubosidad fuera de porcentaje')
            exigir(np.isfinite(x[cols].to_numpy(dtype=float)[x[cols].notna()]).all(), 'Índice no finito')
            ref=t06.SENSORES[sensor][3]+'_promedio'
            exigir(not (x[ref].notna() & (cloud.isna() | (cloud==100))).any(), 'Índice presente con nube100/desconocida')
            if sensor!='Landsat':
                exigir(x.ndvi_promedio.dropna().between(-1,1).all(), 'NDVI fuera de rango matemático')
                exigir((x.ndvi_std.dropna()>=0).all(), 'STD negativa')
                present=x.ndvi_promedio.notna()
                exigir(((x.loc[present,'ndvi_min']-1e-6<=x.loc[present,'ndvi_promedio']) &
                        (x.loc[present,'ndvi_promedio']<=x.loc[present,'ndvi_max']+1e-6)).all(), 'NDVI medio fuera de min/max')
            s=pd.DataFrame({'ID_POLIGONO':x.ID_POLIGONO,'fecha_observada':dates.dt.date,
                'fecha_disponible':'no documentada','sensor':sensor,'fuente':filename,
                'porcentaje_nubosidad':cloud,'tiene_dato':x[ref].notna(), 'posterior_al_corte':dates>END})
            for c in cols:s[c]=x[c]
            for old,new in t06.RENOMBRAR.get(sensor,{}).items():
                s=s.rename(columns={old+'_'+e:new+'_'+e for e in t06.ESTADISTICOS})
            out[sensor]=s.sort_values(['ID_POLIGONO','fecha_observada'],kind='stable').reset_index(drop=True)
        del raw
    return out,huellas


def geometrias(outer, ids):
    payload=outer.read('DATASET_RETO_AGRO_2026/Parcelas_Reto_AGC_CONJUNTO_70_30.zip')
    with tempfile.TemporaryDirectory(prefix='diag_f3_geom_') as td:
        with zipfile.ZipFile(io.BytesIO(payload)) as z:
            names={'Parcelas_Reto_AGC_CONJUNTO'+ext for ext in ('.cpg','.dbf','.prj','.shp','.shx')}
            exigir(set(z.namelist())==names, 'Miembros shapefile distintos')
            for name in names:Path(td,name).write_bytes(z.read(name))
        g=gpd.read_file(Path(td,'Parcelas_Reto_AGC_CONJUNTO.shp'),engine='pyogrio')
    exigir(g.crs is not None and g.crs.to_epsg()==4326, 'CRS original inesperado')
    exigir(g.geometry.notna().all() and not g.geometry.is_empty.any() and g.geometry.is_valid.all(), 'Geometría inválida; no reparar automáticamente')
    exigir(g.geom_type.isin(['Polygon','MultiPolygon']).all(), 'Tipo geometría inesperado')
    exigir(not g.ID_POLIGON.duplicated().any() and set(g.ID_POLIGON)==ids, 'Geometrías/IDs incompletos')
    return g.set_index('ID_POLIGON').sort_index(),hashlib.sha256(payload).hexdigest()


def rejilla(outer):
    payload=outer.read('DATASET_RETO_AGRO_2026/Reto_AgroCebada_CHIRPS_Precipitacion_2022_2025.zip')
    with zipfile.ZipFile(io.BytesIO(payload)) as z:
        names=[n for n in z.namelist() if n.endswith('/PREC_2025_07.tif')]
        exigir(len(names)==1, 'Raster climático no único')
        raster=z.read(names[0])
    with MemoryFile(raster) as mem, mem.open() as ds:
        exigir(ds.crs.to_epsg()==4326 and ds.width==65 and ds.height==72 and ds.count==1, 'Rejilla distinta')
        a=ds.transform
        exigir(a.b==a.d==0 and a.a>0 and a.e<0, 'Rejilla rotada')
    return a,{'miembro':names[0],'sha256':hashlib.sha256(raster).hexdigest(),'transform':list(a)[:6]}


def celdas(g,a):
    """Intersectar en la rejilla original y medir Geod como T02; 6372 sólo escala."""
    tx=Transformer.from_crs(4326,6372,always_xy=True).transform
    pm=g.to_crs(6372); cells={}; rows=[]; geod=Geod(ellps='WGS84')
    for pid,r in g.iterrows():
        geom=r.geometry;poly=pm.loc[pid].geometry
        west,south,east,north=geom.bounds
        cs=range(max(0,math.floor((west-a.c)/a.a)),min(65,math.floor((east-a.c)/a.a)+1))
        rs=range(max(0,math.floor((north-a.f)/a.e)),min(72,math.floor((south-a.f)/a.e)+1))
        overlaps=[]
        for rr in rs:
            for cc in cs:
                key=f'{rr}_{cc}'
                if key not in cells:
                    b=box(a.c+cc*a.a,a.f+(rr+1)*a.e,a.c+(cc+1)*a.a,a.f+rr*a.e)
                    cells[key]=(b,transform(tx,b))
                intersection=geom.intersection(cells[key][0])
                def area_geod(piece):
                    if piece.is_empty:return 0.0
                    if piece.geom_type=='Polygon':return abs(geod.geometry_area_perimeter(orient(piece,1.0))[0])
                    return math.fsum(area_geod(v) for v in piece.geoms) if hasattr(piece,'geoms') else 0.0
                area=area_geod(intersection)
                if area>0:overlaps.append((area,key))
        exigir(overlaps, 'Sin soporte climático')
        area,key=sorted(overlaps,key=lambda k:(-k[0],k[1]))[0]
        rect=poly.minimum_rotated_rectangle;coords=list(rect.exterior.coords)
        lengths=[math.dist(coords[i],coords[i+1]) for i in range(4)]
        rows.append(dict(id_parcela=pid,area_geodesica_ha=abs(geod.geometry_area_perimeter(geom)[0])/10000,
            area_6372_m2=poly.area,ancho_rectangulo_m=min(lengths),largo_rectangulo_m=max(lengths),
            celda_principal=key,celdas_tocadas=len(overlaps),fraccion_celda_principal=area/abs(geod.geometry_area_perimeter(orient(geom,1.0))[0]),
            fraccion_cruce6372_solo_cuatro_vertices=poly.intersection(cells[key][1]).area/poly.area,
            area_celda_principal_m2=cells[key][1].area,fraccion_parcela_sobre_celda=poly.area/cells[key][1].area,
            centroide_lon=geom.centroid.x,centroide_lat=geom.centroid.y,
            centroide_dentro=geom.covers(geom.centroid),
            pixeles_nominales_s2_10m=poly.area/100,pixeles_nominales_s2_20m=poly.area/400,
            pixeles_nominales_pl_3m=poly.area/9))
    return index(rows),pm,cells


def suavizar(v):
    return np.array([statistics.median(v[max(0,i-1):min(len(v),i+2)]) for i in range(len(v))])


def resumen_independiente(p,todas,sensor,ini,fin):
    """Replica aritmética sin llamar curva/variables/resumen de T06."""
    dates=pd.DatetimeIndex(p.f); n=len(p); cloud=todas.porcentaje_nubosidad.dropna().to_list()
    internal=[(b-a).days for a,b in zip(dates,dates[1:])]
    gaps=internal+[(dates[0]-ini).days,(fin-dates[-1]).days] if n else [(fin-ini).days]
    r={'capturas':n,'hueco_max':max(gaps),'nubosidad_media':statistics.mean(cloud) if cloud else np.nan}
    if sensor=='Landsat':
        r['vi6t_mediana']=statistics.median(p.vi6t_promedio.to_list()) if n else np.nan
        return r
    if n<5:return r
    v=suavizar(p.ndvi_promedio.to_list()); k=int(np.argmax(v));base=min(v[:k+1]);amp=v[k]-base
    r.update(ndvi_max=v[k],ndvi_integral=math.fsum(max((dates[i+1]-dates[i]).days,0)*(max(v[i]-base,0)+max(v[i+1]-base,0))/2 for i in range(n-1)))
    near=[i for i,d in enumerate(dates) if abs((d-dates[k]).days)<=15]
    r['ndvi_std_en_maximo']=statistics.median(p.ndvi_std.iloc[near].to_list())
    if sensor=='Planet':r['lai2_max']=max(suavizar(p.lai2_promedio.to_list()))
    else:r['ndwi_en_maximo']=statistics.median(p.ndwi_promedio.iloc[near].to_list())
    if amp>=.1:
        # Integer days and NumPy interpolation conserve exact T06 boundary inclusions.
        xp=(dates-dates[0]).days.to_numpy(); daily=np.arange(xp[-1]+1)
        r['ndvi_dias_sobre_mitad']=int((np.interp(daily,xp,v)>=base+.5*amp).sum())
        if sensor=='Planet':
            fi=None
            for i in range(1,k+1):
                if v[i-1]<base+.2*amp<=v[i]:
                    fi=(dates[i-1]+(dates[i]-dates[i-1])*((base+.2*amp-v[i-1])/(v[i]-v[i-1]))).normalize();break
            r['ndvi_dia_inicio']=fi.dayofyear if fi is not None else np.nan
    return r


def contrastar(expected,actual,tag):
    if expected=='':
        exigir(actual is None or pd.isna(actual), 'Faltante no conservado: '+tag)
        return dict(clave=tag,esperado='',recalculado='',diferencia_abs='',estado='vacio_conservado')
    value=float(expected);exigir(actual is not None and math.isfinite(float(actual)), 'Recalculado ausente: '+tag)
    delta=abs(value-float(actual));exigir(delta<=1e-9, 'Resumen distinto: '+tag+f' delta={delta}')
    return dict(clave=tag,esperado=value,recalculado=float(actual),diferencia_abs=delta,estado='conciliado')


def curvas(ser,table):
    rows=[];compare=[];records={}; temporal=[]
    qualities={(r['id_parcela'],r['sensor'],r['ventana']):r for r in lectura('registro/t07/calidad_satelite.csv')}
    traits={(r['ID_POLIGONO'],r['sensor']):r for r in lectura('registro/t06/rasgos_observables.csv')}
    for sensor,s in ser.items():
        dates=pd.to_datetime(s.fecha_observada); prefix=t06.SENSORES[sensor][1]
        ref=t06.SENSORES[sensor][3]+'_promedio'
        temporal.append(dict(sensor=sensor,filas_originales=len(s),parcelas=s.ID_POLIGONO.nunique(),
            primera=str(dates.min().date()),ultima=str(dates.max().date()),duplicados=0,
            posteriores_al_corte=int((dates>END).sum()),filas_2025=int((dates.dt.year==2025).sum()),
            sin_fecha_disponible=len(s),sensor_preservado=True,unidad_ref='sin_unidad' if sensor!='Landsat' else 'unidad_fisica_no_documentada'))
        by={pid:x.assign(f=pd.to_datetime(x.fecha_observada)) for pid,x in s.groupby('ID_POLIGONO',sort=True)}
        for pid,raw in by.items():
            for win,ini in START.items():
                window=raw.loc[(raw.f>=ini)&(raw.f<=END)]
                valid=window.loc[window.tiene_dato & (window.porcentaje_nubosidad<=t06.UMBRAL[sensor])]
                r=resumen_independiente(valid,window,sensor,ini,END)
                for feature in t06.POR_SENSOR[sensor]:
                    col=f'{prefix}_{feature}_{win}'
                    compare.append(contrastar(table[pid][col],r.get(feature),pid+'/'+col))
                if win=='abr_oct' and sensor!='Landsat':
                    sv=suavizar(valid.ndvi_promedio.to_list())
                    last=(valid.f>END-pd.Timedelta(days=15)).to_numpy()
                    al=statistics.median(sv[last]) if last.any() else np.nan
                    compare.append(contrastar(table[pid][f'{prefix}_ndvi_al_corte'],al,pid+'/'+prefix+'_ndvi_al_corte'))
                q=qualities[(pid,sensor,win)]
                for k,v in [('capturas',r['capturas']),('hueco_max_dias',r['hueco_max'])]:
                    compare.append(contrastar(q[k],v,pid+'/'+sensor+'/'+win+'/'+k))
                first=str(valid.f.iloc[0].date()) if len(valid) else ''
                last=str(valid.f.iloc[-1].date()) if len(valid) else ''
                exigir((first,last)==(q['primera'],q['ultima']), 'Fechas calidad distintas')
                internal=valid.f.diff().dt.days.dropna().to_list()
                row=dict(id_parcela=pid,sensor=sensor,ventana=win,umbral=t06.UMBRAL[sensor],
                    capturas_originales=len(window),capturas_validas=len(valid),capturas_excluidas=len(window)-len(valid),
                    capturas_sin_indice=int(window[ref].isna().sum()),capturas_nube_sobre_umbral=int((window.porcentaje_nubosidad>t06.UMBRAL[sensor]).sum()),
                    nubosidad_media=r['nubosidad_media'],hueco_max_dias=r['hueco_max'],
                    hueco_interno_dias=max(internal) if internal else '',primera_valida=first,ultima_valida=last,
                    dias_inicio_sin_captura=(valid.f.iloc[0]-ini).days if len(valid) else (END-ini).days,
                    dias_final_sin_captura=(END-valid.f.iloc[-1]).days if len(valid) else (END-ini).days,
                    capturas_validas_ultimos15=int((valid.f>END-pd.Timedelta(days=15)).sum()),
                    capturas_posteriores_al_corte=int((raw.f>END).sum()),fecha_disponible='no documentada',
                    ndvi_max_suavizado='',ndvi_max_crudo='',fecha_maximo_suavizado='',
                    hueco_previo_maximo_dias='',hueco_posterior_maximo_dias='',
                    inicio_observado='',pico_observado='',final_observado='',fecha_inicio='',fecha_pico='',fecha_final='',
                    posible_ciclo_doble='',meseta_en_pico='',motivo_rasgos='no_aplica_Landsat',
                    valor_al_corte='',ndvi_std_en_maximo='',amplitud='')
                if sensor!='Landsat':
                    sv=suavizar(valid.ndvi_promedio.to_list());k=int(np.argmax(sv));ff=pd.DatetimeIndex(valid.f)
                    trait=t06.rasgos_parcela(valid.f.to_numpy(),valid.ndvi_promedio.to_numpy())
                    if win=='abr_oct':
                        old=traits[(pid,sensor)]
                        for key in ('hay_ciclo','inicio_observado','pico_observado','final_observado','posible_ciclo_doble','meseta_en_pico'):
                            exigir(str(bool(trait[key]))==old[key], 'Rasgo T06 distinto '+pid+'/'+key)
                        for key in ('fecha_inicio','fecha_pico','fecha_final'):
                            actual=str(pd.Timestamp(trait[key]).date()) if pd.notna(trait[key]) else ''
                            exigir(actual==old[key], 'Fecha rasgo distinta '+pid+'/'+key)
                    for key in ('inicio_observado','pico_observado','final_observado','posible_ciclo_doble','meseta_en_pico'):
                        row[key]=bool(trait[key])
                    for key in ('fecha_inicio','fecha_pico','fecha_final'):
                        row[key]=str(pd.Timestamp(trait[key]).date()) if pd.notna(trait[key]) else ''
                    row.update(ndvi_max_suavizado=float(sv[k]),ndvi_max_crudo=float(valid.ndvi_promedio.max()),
                        fecha_maximo_suavizado=str(ff[k].date()),hueco_previo_maximo_dias=(ff[k]-ff[k-1]).days if k else '',
                        hueco_posterior_maximo_dias=(ff[k+1]-ff[k]).days if k<len(ff)-1 else '',
                        motivo_rasgos=trait.get('motivo',''),valor_al_corte=table[pid][prefix+'_ndvi_al_corte'],
                        ndvi_std_en_maximo=r.get('ndvi_std_en_maximo',''),amplitud=float(sv[k]-min(sv[:k+1])))
                rows.append(row);records[(pid,sensor,win)]=(raw,valid,row)
    return rows,compare,records,temporal


def calidad(table,spatial,curve):
    cat=index(lectura(T02+'catalogo_parcelas.csv'));sup=index(lectura(T02+'soporte_por_parcela.csv'))
    qc=index(lectura('registro/t07/calidad_parcelas.csv'));relief=index(lectura('registro/t07/calidad_relieve.csv'))
    review=index(lectura('analisis/exploracion_parcelas_qgis/revision_contornos/revision_contornos.csv'),'ID_POLIGON')
    climate=defaultdict(list)
    for r in lectura('registro/t04/clima_parcela_mes.csv'):
        if r['periodo'].startswith('2025-') and r['periodo']<='2025-10':climate[r['id_parcela']].append(float(r['cobertura_valida']))
    out=[]
    cb={(r['id_parcela'],r['sensor'],r['ventana']):r for r in curve}
    for pid,t in sorted(table.items()):
        s=spatial[pid];c=cat[pid];u=sup[pid];rv=review[pid];rr=relief[pid]
        exigir(s['celda_principal']==u['celda_clima_principal'] and s['celdas_tocadas']==int(u['celdas_clima_tocadas']), 'Soporte celda distinto '+pid)
        exigir(abs(s['fraccion_celda_principal']-float(u['fraccion_en_celda_principal']))<=.000051, 'Fracción T02 fuera de redondeo')
        exigir(abs(s['area_geodesica_ha']-float(c['area_ha_geodesica']))<=.000005, 'Área geodésica distinta')
        exigir(abs(s['centroide_lon']-float(c['centroide_lon']))<=1e-7 and abs(s['centroide_lat']-float(c['centroide_lat']))<=1e-7, 'Centroide distinto')
        exigir(qc[pid]['contorno_categoria']==rv['categoria'], 'Categoría contorno inconsistente')
        row=dict(id_parcela=pid,municipio=t['municipio'],etiquetada=t['rendimiento_t_ha']!='',
            area_ha_origen=float(t['area_ha_origen']),**{k:v for k,v in s.items() if k!='id_parcela'},
            contorno_categoria=rv['categoria'],angosta_o_muy_pequena=rv['angosta_o_muy_pequena'],
            arboles_dentro=rv['arboles_dentro'],divisiones_internas=rv['divisiones_internas'],
            construccion_dentro=rv['construccion_dentro'],imagen_poco_clara=rv['imagen_poco_clara'],
            firmeza_contorno=rv['etapa'],nota_contorno=rv['nota'],confirmar_en_qgis=rv['confirmar_en_qgis'],
            alerta_contorno=qc[pid]['alerta_contorno_t03_bis'],vecina_etiquetada=qc[pid]['vecina_etiquetada_menos_20m'],
            n_vecinas_etiquetadas=int(qc[pid]['numero_vecinas_etiquetadas_menos_20m']),
            elevacion_cobertura=float(rr['elevacion_cobertura_valida']),pendiente_cobertura=float(rr['pendiente_cobertura_valida']),
            elevacion_celdas_validas=int(rr['elevacion_celdas_validas']),pendiente_celdas_validas=int(rr['pendiente_celdas_validas']),
            pendiente_t10_ausente=t['pendiente_media_t10_grados']=='',avisos_relieve=rr['avisos'],
            cobertura_clima_min_2025_ene_oct=min(climate[pid]),
            pixels_validos_satelite='no documentados',regla_pixeles_borde_FIRA='no documentada',fecha_atlas='no documentada')
        exigir(len(climate[pid])==30,'Clima campaña incompleto')
        for sensor in ('Planet','Sentinel-2','Landsat'):
            ab=t06.SENSORES[sensor][1];q=cb[(pid,sensor,'abr_oct')]
            for k in ('capturas_validas','hueco_max_dias','nubosidad_media','capturas_validas_ultimos15',
                      'inicio_observado','pico_observado','final_observado','posible_ciclo_doble','meseta_en_pico','ndvi_std_en_maximo'):
                row[ab+'_'+k]=q[k]
        out.append(row)
    return out


NUMERIC=['area_ha_origen','ancho_rectangulo_m','celdas_tocadas','fraccion_celda_principal','pendiente_cobertura',
    'n_vecinas_etiquetadas']+[s+'_'+k for s in ('pl','s2','ls') for k in ('capturas_validas','hueco_max_dias','nubosidad_media','capturas_validas_ultimos15')]+['pl_ndvi_std_en_maximo','s2_ndvi_std_en_maximo']
CATEGORY=['contorno_categoria','angosta_o_muy_pequena','alerta_contorno','vecina_etiquetada','pendiente_t10_ausente']+[s+'_'+k for s in ('pl','s2') for k in ('final_observado','posible_ciclo_doble','meseta_en_pico')]


def spearman(x,y):
    if len(x)<3 or len(set(x))<2 or len(set(y))<2:return ''
    xx=pd.Series(x).rank(method='average').to_numpy();yy=pd.Series(y).rank(method='average').to_numpy()
    return float(np.corrcoef(xx,yy)[0,1])


def cobertura_analisis(value):
    # Preserve literal source values in quality; remove roundoff-only ranks in analysis.
    return 1.0 if abs(float(value)-1)<=1e-9 else float(value)


def asociaciones(quality,errors):
    q=index(quality);out=[];groups=[]
    for esc in ('A','B'):
        for pop in ('todas','sin_respaldo'):
            er=[r for r in errors if r['escenario']==esc and r['poblacion']==pop and int(r['n_elegibles'])]
            exigir(len(er)==(138 if pop=='todas' else 135),'Censo de errores distinto')
            for col in NUMERIC:
                pairs=[(cobertura_analisis(q[r['id_parcela']][col]) if col=='pendiente_cobertura' else q[r['id_parcela']][col],float(r['mae']),r['municipio']) for r in er if q[r['id_parcela']][col]!='']
                by=defaultdict(list)
                for x,y,m in pairs:by[m].append((float(x),y))
                residual=[(x-statistics.mean(v[0] for v in by[m]),y-statistics.mean(v[1] for v in by[m])) for x,y,m in pairs]
                out.append(dict(escenario=esc,poblacion=pop,variable=col,n_parcelas=len(pairs),
                    rho_global=spearman([float(x) for x,y,m in pairs],[y for x,y,m in pairs]),
                    rho_tras_media_municipal=spearman([x for x,y in residual],[y for x,y in residual]),
                    n_municipios=len(by),normalizacion='cobertura_a1_solo_si_distancia1_menor1e-9' if col=='pendiente_cobertura' else 'literal',interpretacion='exploratorio_sin_causalidad_ni_pvalor_sin_seleccion_atributos'))
            for col in CATEGORY+['municipio']:
                by=defaultdict(list)
                for r in er:by[str(q[r['id_parcela']][col])].append(r)
                for level,rs in sorted(by.items()):
                    groups.append(dict(escenario=esc,poblacion=pop,variable=col,categoria=level,n_parcelas=len(rs),
                        mae=statistics.mean(float(r['mae']) for r in rs),mediana_mae=statistics.median(float(r['mae']) for r in rs),
                        sesgo=statistics.mean(float(r['sesgo']) for r in rs),n_municipios=len({r['municipio'] for r in rs})))
    return out,groups


def vecindad(table,errors):
    eb={(r['escenario'],r['poblacion'],r['id_parcela']):r for r in errors}
    parts={(r['escenario'],r['repeticion'],r['id_parcela']):r['particion'] for r in lectura('registro/diagnostico/fase0/mascaras_contextos.csv') if r['escenario'] in ('A','B')}
    sup=index(lectura(T02+'soporte_por_parcela.csv'));out=[]
    for r in lectura(T02+'pares_de_parcelas_cercanas.csv'):
        a,b=r['id_parcela_a'],r['id_parcela_b']; both=bool(table[a]['rendimiento_t_ha'] and table[b]['rendimiento_t_ha'])
        for esc in ('A','B'):
            different=sum(parts[(esc,str(i),a)]!=parts[(esc,str(i),b)] for i in range(1,6)) if both else ''
            qa=eb.get((esc,'todas',a),{});qb=eb.get((esc,'todas',b),{})
            ea=float(qa['sesgo']) if qa else '';ez=float(qb['sesgo']) if qb else ''
            out.append(dict(id_a=a,id_b=b,escenario=esc,distancia_orillas_m=float(r['distancia_orillas_m']),
                ambas_etiquetadas=both,misma_celda_principal=sup[a]['celda_clima_principal']==sup[b]['celda_clima_principal'],
                mismo_rendimiento=r['mismo_rendimiento'],repeticiones_fold_distinto=different,repeticiones_totales=5 if both else '',
                sesgo_a=ea,sesgo_b=ez,mismo_signo_error=(ea*ez>0) if both else '',
                universo='catalogo_completo_solo_descriptivo_no_atributo_predictivo'))
    return out


def pares(quality,errors):
    q=index(quality);er={(r['escenario'],r['poblacion'],r['id_parcela']):r for r in errors};out=[]
    columns=NUMERIC+CATEGORY+['municipio']
    for pair in lectura('registro/diagnostico/fase0/controles_preseleccionados.csv'):
        a,b=pair['caso'],pair['control']
        for col in columns:
            x,y=q[a][col],q[b][col]
            out.append(dict(caso=a,control=b,variable=col,valor_caso=x,valor_control=y,
                diferencia_caso_menos_control=float(x)-float(y) if col in NUMERIC and x!='' and y!='' else '',
                coincide=x==y,diferencias_calidad_seleccion=pair['diferencias_calidad'],
                diferencia_log_area_seleccion=pair['diferencia_log_area'],
                mae_A_caso=er[('A','sin_respaldo',a)]['mae'],mae_A_control=er[('A','sin_respaldo',b)]['mae'],
                criterio_control='fijo_mejor_disponible_no_equivalencia_certificada_no_seleccion_por_error'))
    return out


def pares_curvas(records,table):
    """Sólo fechas válidas comunes; sin interpolar huecos ni elegir nuevos controles."""
    rows=[]
    for pair in lectura('registro/diagnostico/fase0/controles_preseleccionados.csv'):
        a,b=pair['caso'],pair['control']
        for sensor in ('Planet','Sentinel-2'):
            _,va,qa=records[(a,sensor,'abr_oct')];_,vb,qb=records[(b,sensor,'abr_oct')]
            x={str(d.date()):float(v) for d,v in zip(va.f,va.ndvi_promedio)}
            y={str(d.date()):float(v) for d,v in zip(vb.f,vb.ndvi_promedio)}
            common=sorted(set(x)&set(y));n=len(common)
            deltas=[x[d]-y[d] for d in common]
            clim=[c for c in table[a] if c.startswith(('prec_acumulada','tmin_media','tmax_media'))]
            rows.append(dict(caso=a,control=b,sensor=sensor,fechas_validas_comunes=n,
                capturas_validas_caso=len(va),capturas_validas_control=len(vb),
                fraccion_comunes_sobre_menor=n/min(len(va),len(vb)) if min(len(va),len(vb)) else '',
                rmse_ndvi_fechas_comunes=math.sqrt(statistics.mean(v*v for v in deltas)) if n else '',
                diferencia_media_ndvi=statistics.mean(deltas) if n else '',
                diferencia_max_abs_ndvi=max(map(abs,deltas)) if n else '',
                diferencia_rendimiento_caso_menos_control=float(table[a]['rendimiento_t_ha'])-float(table[b]['rendimiento_t_ha']),
                seis_climas_T07_exactamente_iguales=all(table[a][c]==table[b][c] for c in clim),
                final_caso=qa['final_observado'],final_control=qb['final_observado'],
                seleccion='control_fijo_F0_sin_rendimiento',interpretacion='similitud_observacional_no_causa_no_predictor'))
    return rows


def ejecutar(salida,series_salida,figuras=True):
    fuentes();salida=Path(salida);series_salida=Path(series_salida)
    exigir(not salida.exists() and not series_salida.exists(),'Usar destinos nuevos, nunca sobrescribir')
    salida.parent.mkdir(parents=True,exist_ok=True);series_salida.parent.mkdir(parents=True,exist_ok=True)
    table=index(lectura('registro/t07/tabla_comun.csv'));ids=set(table)
    exigir(len(ids)==197 and sum(bool(r['rendimiento_t_ha']) for r in table.values())==138,'Universo distinto')
    with zipfile.ZipFile(RAIZ/'data/raw/DataSet.zip') as z:
        ser,hashes=crudos(z,ids);g,geom_sha=geometrias(z,ids);grid,grid_meta=rejilla(z)
    spatial,pm,cells=celdas(g,grid)
    curve,compare,records,temporal=curvas(ser,table)
    quality=calidad(table,spatial,curve)
    errors=lectura('registro/diagnostico/fase1/errores_por_parcela.csv')
    assoc,groups=asociaciones(quality,errors)
    tables={'calidad_por_parcela.csv':quality,'curvas_calidad.csv':curve,'conciliacion_resumenes.csv':compare,
        'asociaciones_calidad_error.csv':assoc,'desgloses_calidad_error.csv':groups,
        'vecindad_contextos.csv':vecindad(table,errors),'pares_casos_controles.csv':pares(quality,errors),
        'inventario_temporal.csv':temporal,'comparacion_curvas_pares.csv':pares_curvas(records,table)}
    with tempfile.TemporaryDirectory(prefix='.diag_f3_',dir=salida.parent) as td:
        tmp=Path(td)
        for n,rs in tables.items():f1.csv_escribir(tmp/n,rs)
        if figuras:
            from scripts.diagnostico_fase3_figuras import crear
            crear(tmp,g,pm,cells,records,quality,errors,table)
        manifest=dict(schema='agrocebada_diagnostico_fase3_entrega_v1',estado='tecnico_para_revision',
            diseno_sha256=DESIGN_SHA,parcelas_calidad=197,parcelas_etiquetadas=138,reservadas_evaluadas=0,
            reentrenamientos=0,cambios_originales=0,revision_humana='pendiente',figuras_generadas=figuras,
            miembros_originales=hashes,geometria_miembro_sha256=geom_sha,rejilla=grid_meta,
            max_diferencia_resumen=max(r['diferencia_abs'] for r in compare if r['diferencia_abs']!=''),
            n_filas_tablas={n:len(rs) for n,rs in tables.items()},
            codigo_sha256={n:hash_archivo(RAIZ/n) for n in ('scripts/diagnostico_fase3.py','scripts/diagnostico_fase3_figuras.py')},
            archivos_sha256={p.name:hash_archivo(p) for p in sorted(tmp.iterdir())})
        (tmp/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
        # Series in a separate temporary directory; preserve all dates, index names and sensors.
        with tempfile.TemporaryDirectory(prefix='.diag_f3_series_',dir=series_salida.parent) as sd:
            st=Path(sd)
            for sensor,s in ser.items():s.to_csv(st/('serie_'+t06.SENSORES[sensor][1]+'.csv'),index=False,lineterminator='\n')
            (st/'proveniencia.json').write_text(json.dumps({'miembros':hashes,'zip_sha256':hash_archivo(RAIZ/'data/raw/DataSet.zip'),
                'filtrado':False,'solo_modelable_hasta':'2025-10-31','disponibilidad':'no documentada'},ensure_ascii=False,indent=2)+'\n')
            st.rename(series_salida)
        tmp.rename(salida)
    return manifest


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--salida',type=Path,required=True)
    p.add_argument('--series',type=Path,required=True);p.add_argument('--sin-figuras',action='store_true')
    args=p.parse_args();print(json.dumps(ejecutar(args.salida,args.series,not args.sin_figuras),ensure_ascii=False,indent=2))
