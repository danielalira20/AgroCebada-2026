"""Auditor C separado: statistics/cdist y distancias escalares; no importa productor ni modelos."""
import argparse
import csv
import hashlib
import io
import json
import math
from pathlib import Path
import statistics
import zipfile

import geopandas as gpd
import numpy as np
from scipy.spatial.distance import cdist
import pyproj
from shapely.ops import transform


def read(p):
    with Path(p).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))


def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def audit(root, output, detail):
    root, output, detail=map(Path,(root,output,detail))
    manifest=json.loads((output/'manifest.json').read_text())
    for name,h in manifest['archivos_sha256'].items():
        if digest(output/name)!=h:raise ValueError('Salida alterada: '+name)
    for name,h in manifest['fuentes_sha256'].items():
        if digest(root/name)!=h:raise ValueError('Fuente alterada: '+name)
    design=json.loads((root/'registro/diagnostico/aplicabilidad59/diseno.json').read_text())
    if digest(root/'registro/diagnostico/aplicabilidad59/diseno.json')!=manifest['diseno_sha256']:
        raise ValueError('Diseño diferente')
    table={r['id_parcela']:r for r in read(root/'registro/t07/tabla_comun.csv')}
    ids=sorted(table);known=sorted(i for i in ids if table[i]['rendimiento_t_ha']);reserved=sorted(set(ids)-set(known))
    if (len(ids),len(known),len(reserved))!=(197,138,59):raise ValueError('Población diferente')
    checks=0;max_delta=0.;max_geometry_delta=0.

    def check(a,b,label,atol=1e-9):
        nonlocal checks,max_delta,max_geometry_delta
        checks+=1
        if b is None:
            if a not in ('',None):raise ValueError(label+': debe estar ausente')
        elif isinstance(b,(bool,np.bool_)):
            if a != ('si' if b else 'no'):raise ValueError(label+': booleano diferente')
        elif isinstance(b,(int,float,np.number)):
            delta=abs(float(a)-float(b))
            if not math.isfinite(delta) or delta>atol:raise ValueError(f'{label}: diferencia{delta}')
            if atol==1e-3:max_geometry_delta=max(max_geometry_delta,delta)
            else:max_delta=max(max_delta,delta)
        elif str(a)!=str(b):raise ValueError(label+': texto diferente')

    # Segundo lector de la geometría original; proyección explícita, operaciones escalares.
    package=root/'data/raw/DataSet.zip'
    if digest(package)!=design['paquete_zip_sha256']:raise ValueError('ZIP diferente')
    with zipfile.ZipFile(package) as z:
        name=[n for n in z.namelist() if n.endswith('/Parcelas_Reto_AGC_CONJUNTO_70_30.zip')]
        if len(name)!=1:raise ValueError('ZIP ambiguo')
        g=gpd.read_file(io.BytesIO(z.read(name[0])),encoding='utf-8').set_index('ID_POLIGON').loc[ids]
    project=pyproj.Transformer.from_crs(4326,32614,always_xy=True)
    geometries=[transform(project.transform,v) for v in g.geometry]
    cache=np.load(detail/'distancias_geometricas.npz',allow_pickle=False)
    if cache['ids'].tolist()!=ids:raise ValueError('Matriz de IDs diferente')
    edges=cache['orillas'];centers=cache['centros']
    for i in range(len(ids)):
        for j in range(i+1):
            check(edges[i,j],geometries[i].distance(geometries[j]),'distancia_orillas',1e-3)
            check(edges[i,j],edges[j,i],'simetria_orillas',1e-3)
    positions={pid:k for k,pid in enumerate(ids)}
    catalogue={r['id_parcela']:r for r in read(root/'analisis/auditoria_catalogo_y_etiquetas/tablas/catalogo_parcelas.csv')}
    geod=pyproj.Geod(ellps='WGS84')
    for i in range(len(ids)):
        a=catalogue[ids[i]]
        for j in range(i+1):
            b=catalogue[ids[j]]
            d=geod.inv(float(a['centroide_lon']),float(a['centroide_lat']),float(b['centroide_lon']),float(b['centroide_lat']))[2]
            check(centers[i,j],d,'distancia_centros',1e-3)
            check(centers[j,i],d,'simetria_centros',1e-3)

    partitions=read(root/'registro/t03/particiones.csv')
    trains={('59',0,-1):known}
    tests={('59',0,-1):reserved}
    for scenario,col in [('A','particion_principal'),('B','particion_espacial')]:
        for rep in range(1,6):
            pp=[r for r in partitions if int(r['repeticion'])==rep]
            for fold in range(5):
                key=(scenario,rep,fold)
                trains[key]=sorted(r['ID_POLIGONO'] for r in pp if int(r[col])!=fold)
                tests[key]=sorted(r['ID_POLIGONO'] for r in pp if int(r[col])==fold)
                if set(trains[key])&set(tests[key]):raise ValueError('ID externo en entrenamiento')
    supports={r['id_parcela']:r for r in read(root/'analisis/auditoria_catalogo_y_etiquetas/tablas/soporte_por_parcela.csv')}
    historical={(r['escenario'],int(r['repeticion']),r['ID_POLIGONO']):r for r in read(root/'registro/t03/predicciones_oof_referencias_media_mun__resp_grupo.csv')}
    cs=read(output/'contextos_oof_138.csv');profiles=read(output/'perfil_59.csv')
    if len(cs)!=1380 or sorted(r['id_parcela'] for r in profiles)!=reserved:raise ValueError('C no cubre población exacta')
    for r in cs+profiles:
        pid=r['id_parcela'];key=(r.get('escenario','59'),int(r.get('repeticion',0)),int(r.get('particion',-1)))
        tr=trains[key]
        if pid not in tests[key] or pid in tr:raise ValueError('Población del contexto diferente')
        i=positions[pid];js=[positions[j] for j in tr]
        local=[j for j in tr if table[j]['municipio']==table[pid]['municipio']]
        group=[j for j in tr if table[j]['cultivo_origen']==table[pid]['cultivo_origen']]
        check(r['n_etiquetas_municipio'],len(local),'n_local')
        check(r['n_etiquetas_grupo'],len(group),'n_grupo')
        check(r['fuente_referencia'],'municipio' if local else 'grupo' if group else 'global','respaldo')
        check(r['n_vecinas20_general'],sum(edges[i,positions[j]]<20 for j in tr),'vecinas20')
        check(r['n_vecinas20_municipio'],sum(edges[i,positions[j]]<20 for j in local),'vecinas20_local')
        check(r['distancia_orillas_m'],min(edges[i,j] for j in js),'min_orillas',1e-3)
        check(r['distancia_centros_m'],min(centers[i,j] for j in js),'min_centros',1e-3)
        check(r['n_etiquetas_celda_principal'],sum(supports[j]['celda_clima_principal']==r['celda_principal'] for j in tr),'n_celda')
        for name in ['conocida_mas_cercana_centro','conocida_mas_cercana_orilla','conocida_local_mas_cercana_orilla']:
            if r[name] and r[name] not in tr:raise ValueError('Vecina ajena al entrenamiento')
        if key[0]!='59':
            previous=historical[(key[0],key[1],pid)]
            check(r['error_historico'],float(previous['prediccion'])-float(previous['real']),'error_historico')

    representations={r['id']:r['columnas'] for r in design['representaciones']}
    diagnostics=read(output/'entradas_59.csv')+read(detail/'entradas_oof_138.csv')
    by_context={}
    for r in diagnostics:
        key=(r.get('escenario','59'),int(r.get('repeticion',0)),int(r.get('particion',-1)),r['representacion'])
        by_context.setdefault(key,[]).append(r)
    saved={(r['escenario'],r['repeticion'],r['particion'],r['representacion']):r for r in json.loads((detail/'estados_soporte.json').read_text())}
    if len(by_context)!=51*15 or len(saved)!=51*15 or len(diagnostics)!=21585:
        raise ValueError('Número de representaciones/contextos diferente')
    pend='pendiente_media_t10_grados'

    def tol(col):
        if col.startswith('prec_'):return 1e-6
        if col.startswith(('tmin_','tmax_')) or col==pend:return 1e-8
        if col=='elevacion_media_m':return 1e-6
        if col=='area_ha_origen':return 1e-10
        if 'dias_' in col or 'dia_inicio' in col:return 0.
        return 1e-8 if 'integral' in col else 1e-9

    for (scenario,rep,fold,representation),rs in sorted(by_context.items()):
        key=(scenario,rep,fold);tr=trains[key];cols=representations[representation]
        if sorted(r['id_parcela'] for r in rs)!=tests[key]:raise ValueError('Cobertura de IDs incompleta')
        if saved[(scenario,rep,fold,representation)]['ids']!=tr:raise ValueError('Estado aprendido con otros IDs')
        raw=[[float(table[i][c]) if table[i][c] else None for c in cols] for i in tr]
        med=statistics.median(row[cols.index(pend)] for row in raw if row[cols.index(pend)] is not None) if pend in cols else None

        def prepare(row):
            out=[]
            for col,v in zip(cols,row):
                if v is None:
                    if col!=pend:raise ValueError('Faltante no admitido')
                    v=med
                out.append(math.log(v) if col=='area_ha_origen' else v)
            if pend in cols:out.append(float(row[cols.index(pend)] is None))
            return out

        x=[prepare(row) for row in raw]
        means=[statistics.fmean(a) for a in zip(*x)]
        sd=[statistics.pstdev(a) for a in zip(*x)];sd=[s if s else 1. for s in sd]
        state=saved[(scenario,rep,fold,representation)]
        for a,b in zip(state['media'],means):check(a,b,'media_solo_entrenamiento')
        for a,b in zip(state['sd'],sd):check(a,b,'sd_solo_entrenamiento')
        z=np.array([[(v-m)/s for v,m,s in zip(row,means,sd)] for row in x])
        raw_q=[[float(table[r['id_parcela']][c]) if table[r['id_parcela']][c] else None for c in cols] for r in rs]
        q=np.array([[(v-m)/s for v,m,s in zip(prepare(row),means,sd)] for row in raw_q])
        distances=cdist(q,z,metric='euclidean')/math.sqrt(len(means))
        train_distances=cdist(z,z,metric='euclidean')/math.sqrt(len(means))
        for i,row in enumerate(rs):
            pid=row['id_parcela'];municipality=table[pid]['municipio']
            local=[j for j in range(len(tr)) if table[tr[j]]['municipio']==municipality]
            check(row['distancia_global'],min(distances[i]),'distancia_atributos_global')
            dl=min(distances[i,j] for j in local) if local else None
            check(row['distancia_municipio'],dl,'distancia_atributos_local')
            if row['vecino_atributos_global'] not in tr:raise ValueError('Vecino de atributos externo')
            if row['vecino_atributos_municipio'] and row['vecino_atributos_municipio'] not in [tr[j] for j in local]:
                raise ValueError('Vecino de atributos local ajeno')
            baseline=[min(train_distances[j,k] for k in local if k!=j) for j in local] if len(local)>=2 else []
            check(row['n_referencia_distancia'],len(baseline),'n_distancias_LOO')
            if baseline:
                ordered=sorted(baseline);p95=ordered[math.ceil(.95*(len(ordered)-1))]
                pct=100*sum(v<dl-1e-12 for v in baseline)/len(baseline)
                check(row['q95_local'],p95,'q95_local')
                check(row['percentil_local_estricto'],pct,'percentil_estricto')
                check(row['supera_q95_local'],dl>p95+1e-12,'supera_q95')
            else:
                for field in ['q95_local','percentil_local_estricto','supera_q95_local']:check(row[field],None,field)
            outside_g=[];outside_l=[];missing=[]
            for j,col in enumerate(cols):
                v=raw_q[i][j]
                if v is None:missing.append(col);continue
                for indices,dest in [(range(len(tr)),outside_g),(local,outside_l)]:
                    values=[raw[k][j] for k in indices if raw[k][j] is not None]
                    if values and (v<min(values)-tol(col) or v>max(values)+tol(col)):dest.append(col)
            check(row['fuera_rango_global'],';'.join(outside_g),'rango_global')
            check(row['fuera_rango_municipio'],';'.join(outside_l),'rango_local')
            check(row['entradas_ausentes'],';'.join(missing),'faltantes_originales')
    # Verifica agregación sin importar funciones del productor.
    feature_rows=diagnostics[885:]
    for group in read(output/'error_por_soporte.csv'):
        dimension=group['dimension']
        source=feature_rows if group['representacion'] else cs
        selected=[r for r in source if r['escenario']==group['escenario'] and
                  r.get('representacion','')==group['representacion'] and
                  (group['subconjunto']=='todas' or r['fuente_referencia']=='municipio')]
        category=group['categoria']
        expected_value={'True':'si','False':'no','no_definido':''}.get(category,category)
        selected=[r for r in selected if r[dimension]==expected_value]
        check(group['n_registros_oof'],len(selected),'n_registros_desglose')
        check(group['n_parcelas'],len({r['id_parcela'] for r in selected}),'n_ids_desglose')
        errors=[float(r['error_historico']) for r in selected]
        check(group['MAE_historico'],statistics.fmean(abs(x) for x in errors),'MAE_historico_desglose')
        check(group['RMSE_historico'],math.sqrt(statistics.fmean(x*x for x in errors)),'RMSE_historico_desglose')
        check(group['sesgo_historico'],statistics.fmean(errors),'sesgo_historico_desglose')
    return dict(resultado='aprobado',comparaciones=checks,max_delta_atributos_estado_y_error=max_delta,
        max_delta_geometria_m=max_geometry_delta,n_contextos=51,n_representaciones=15,
        registros_atributos=21585,geometrias=197,usa_productor=False,ajustes_modelos=0,
        metodo='statistics_pstdev_cdist_y_geometria_escalar_proyeccion_explicita',
        limites='Comprobacion tecnica, no aprobacion humana ni evidencia nueva de mejora predictiva')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--raiz',type=Path,default=Path(__file__).resolve().parents[1])
    p.add_argument('--salida',type=Path,required=True);p.add_argument('--detalle',type=Path,required=True)
    p.add_argument('--evidencia',type=Path)
    a=p.parse_args();result=audit(a.raiz,a.salida,a.detalle)
    if a.evidencia:
        if a.evidencia.exists():raise ValueError('Evidencia existente')
        a.evidencia.parent.mkdir(parents=True,exist_ok=True)
        a.evidencia.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
