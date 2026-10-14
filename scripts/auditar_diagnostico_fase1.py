"""Auditor independiente: raw T08 -> NumPy/pandas; no importa productores."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd


def check(ok, msg):
    if not ok: raise ValueError(msg)


def read(p):
    check(p.is_file() and not p.is_symlink() and p.stat().st_nlink==1 and p.stat().st_size<=64*1024*1024,'Entrada no regular o fuera de límites')
    with p.open(encoding='utf-8-sig',newline='') as f:
        rr=csv.DictReader(f);h=rr.fieldnames
        check(h and len(h)==len(set(h)) and len(h)<=160,'Esquema no válido')
        n=0
        for r in rr:
            n+=1;check(n<=250000 and None not in r and all(v is not None for v in r.values()),'CSV incompleto o excede límite')
    return pd.read_csv(p, float_precision='round_trip', keep_default_na=False)
def num(v): return float(v) if v != '' else None
def eq(a, b, name):
    if a is None or b is None:
        check(a is None and b is None, 'Vacío distinto: '+name); return 0.
    diff = abs(a-b); check(diff <= 1e-12, 'Valor distinto: '+name); return diff


def select(df,pop):
    if pop=='todas': return df
    if pop=='sin_respaldo': return df[df.fuente=='municipio']
    if pop=='con_respaldo': return df[df.fuente!='municipio']
    return df[df.fuente==pop]


def stats(df):
    if len(df)==0: return dict(n_elegibles=0, **{k:None for k in ['prediccion_media','sesgo','mae','mse','rmse','mediana_abs','p90_abs','error_min','error_max','rango_error','sd_error','abs_sesgo','fraccion_sobre','fraccion_sub','fraccion_cero']},sobre=0,sub=0,ceros=0)
    e=(df.prediccion-df.real).to_numpy(); a=np.abs(e)
    return dict(n_elegibles=len(df),prediccion_media=df.prediccion.mean(),sesgo=e.mean(),mae=a.mean(),mse=(e*e).mean(),rmse=np.sqrt((e*e).mean()),mediana_abs=np.quantile(a,.5),p90_abs=np.quantile(a,.9),error_min=e.min(),error_max=e.max(),rango_error=np.ptp(e),sd_error=e.std(),abs_sesgo=abs(e.mean()),sobre=(e>0).sum(),sub=(e<0).sum(),ceros=(e==0).sum(),fraccion_sobre=(e>0).mean(),fraccion_sub=(e<0).mean(),fraccion_cero=(e==0).mean())


def run(fuentes,out):
    check(not fuentes.is_symlink() and not out.is_symlink(),'Root no regular')
    anchors={'base/registro/t03/predicciones_oof_referencias_media_mun__resp_grupo.csv':'e767c06ab63898595bf925b98ed90ae0266815528652ed1d44228235f6860569',
             'base/registro/t07/tabla_comun.csv':'f6ffca6b6b4a08be2d921fac180311a2187727d91aac8a25b2356a1ad7720fb5'}
    for rel,sha in anchors.items():
        path=fuentes/rel
        check(path.resolve().is_relative_to(fuentes.resolve()),'Fuente escapa root')
        read(path)
        check(hashlib.sha256(path.read_bytes()).hexdigest()==sha,'Fuente raw diferente')
    raw=read(fuentes/'base/registro/t03/predicciones_oof_referencias_media_mun__resp_grupo.csv')
    tab=read(fuentes/'base/registro/t07/tabla_comun.csv')
    check(raw.version.unique().tolist()==['T08-v1'],'Versión raw')
    check(raw.candidato.unique().tolist()==['media_mun__resp_grupo'],'Candidato raw')
    ids=sorted(tab[tab.rendimiento_t_ha!=''].id_parcela)
    check(len(ids)==138 and len(raw)==1380,'Censo raw')
    keys=['escenario','repeticion','particion','ID_POLIGONO']
    records=read(out/'errores_por_repeticion.csv').rename(columns={'id_parcela':'ID_POLIGONO'})
    check(not records.duplicated(keys).any(),'Duplicación')
    a=raw.sort_values(keys).reset_index(drop=True); b=records.sort_values(keys).reset_index(drop=True)
    check(a[keys].equals(b[keys]),'Claves raw/derivadas')
    check(np.array_equal(a.real.to_numpy(),b.real.to_numpy()) and np.array_equal(a.prediccion.to_numpy(),b.prediccion.to_numpy()),'Predicciones/etiquetas cambiadas')
    ee=a.prediccion.to_numpy()-a.real.to_numpy()
    check(np.array_equal(ee,b.error_firmado.to_numpy()),'Error firmado')
    check(np.array_equal(abs(ee),b.error_absoluto.to_numpy()),'Error abs')
    check(np.array_equal(ee**2,b.error_cuadrado.to_numpy()),'Error cuadrado')
    check(np.array_equal(a.fuente.to_numpy(),b.fuente_referencia.to_numpy()),'Fuente respaldo')
    parcel=read(out/'errores_por_parcela.csv'); maxdiff=0.; counts=0
    check(len(parcel)==1380 and not parcel.duplicated(['escenario','poblacion','id_parcela']).any(),'Tabla completa 1380')
    expected={}
    fixed={'AGC_171','AGC_015','AGC_024','AGC_034','AGC_162','AGC_127','AGC_049','AGC_069','AGC_055','AGC_026'}
    pops=['todas','sin_respaldo','con_respaldo','grupo','global']
    for esc in ['A','B']:
        for pop in pops:
            df=select(raw[raw.escenario==esc],pop)
            tops={rep:set((sub.assign(abs_error=abs(sub.prediccion-sub.real)).sort_values(['abs_error','ID_POLIGONO'],ascending=[False,True])).head(10).ID_POLIGONO)
                  for rep,sub in df.groupby('repeticion')}
            dd={pid:stats(df[df.ID_POLIGONO==pid]) for pid in ids}
            expected[esc,pop]=dd
            totalabs=sum(x['mae'] for x in dd.values() if x['n_elegibles'])
            totalsq=sum(x['mse'] for x in dd.values() if x['n_elegibles'])
            scores={pid:math.fsum(abs(float(r.prediccion)-float(r.real)) for r in df[df.ID_POLIGONO==pid].itertuples())/s['n_elegibles'] for pid,s in dd.items() if s['n_elegibles']}
            ranks={pid:i+1 for i,pid in enumerate(sorted(scores,key=lambda pid:(-scores[pid],pid)))}
            for pid in ids:
                pr=parcel[(parcel.escenario==esc)&(parcel.poblacion==pop)&(parcel.id_parcela==pid)].iloc[0]
                s=dd[pid]; n=s['n_elegibles']
                check(num(pr.rango_mae)==ranks.get(pid),'Ranking por parcela')
                for c,v in s.items(): maxdiff=max(maxdiff,eq(v,num(pr[c]),pid+'/'+c)); counts+=1
                hit=sum(pid in t for t in tops.values())
                for c,v in [('apariciones_top10',hit),('fraccion_top10',hit/n if n else None),('contribucion_abs',s['mae']/totalabs if n and totalabs else None),('contribucion_cuadratica',s['mse']/totalsq if n and totalsq else None)]:
                    maxdiff=max(maxdiff,eq(v,num(pr[c]),c));counts+=1
                check(str(pr.rep_elegibles)=='|'.join(map(str,df[df.ID_POLIGONO==pid].repeticion.to_list())),'Repeticiones elegibles')
    met=read(out/'resumen_metricas.csv')
    for row in met.to_dict('records'):
        dd=[s for s in expected[row['escenario'],row['poblacion']].values() if s['n_elegibles']]
        for col,field in [('mae_parcelas','mae'),('mse_parcelas','mse'),('sesgo_parcelas','sesgo'),('fraccion_sobre_parcelas','fraccion_sobre'),('fraccion_sub_parcelas','fraccion_sub'),('fraccion_cero_parcelas','fraccion_cero')]:
            maxdiff=max(maxdiff,eq(np.mean([d[field] for d in dd]) if dd else None,num(row[col]),col));counts+=1
        for col,p in [('mediana_mae_parcela',.5),('p90_mae_parcela',.9)]:
            maxdiff=max(maxdiff,eq(np.quantile([d['mae'] for d in dd],p) if dd else None,num(row[col]),col));counts+=1
        check(row['n_parcelas']==len(dd),'N parcelas resumen')
        check(row['n_registros']==sum(s['n_elegibles'] for s in dd),'N registros resumen')
        df=select(raw[raw.escenario==row['escenario']],row['poblacion'])
        repmae=[abs(z.prediccion-z.real).mean() for _,z in df.groupby('repeticion')]
        totalabs=sum(z['mae'] for z in dd);totalsq=sum(z['mse'] for z in dd)
        cs=[z for pid,z in expected[row['escenario'],row['poblacion']].items() if pid in fixed and z['n_elegibles']]
        for col,val in [('mae_media_repeticiones',np.mean(repmae) if repmae else None),('rmse_parcelas',np.sqrt(np.mean([z['mse'] for z in dd])) if dd else None),('mae_registros',abs(df.prediccion-df.real).mean() if len(df) else None),('sesgo_registros',(df.prediccion-df.real).mean() if len(df) else None),('contribucion_abs_casos_fijos',sum(z['mae'] for z in cs)/totalabs if totalabs else None),('contribucion_cuadratica_casos_fijos',sum(z['mse'] for z in cs)/totalsq if totalsq else None)]:
            maxdiff=max(maxdiff,eq(val,num(row[col]),col));counts+=1
    reps=read(out/'metricas_por_repeticion.csv')
    for row in reps.to_dict('records'):
        df=select(raw[(raw.escenario==row['escenario'])&(raw.repeticion==row['repeticion'])],row['poblacion'])
        s=stats(df)
        for col,field in [('mae_parcelas','mae'),('mse_parcelas','mse'),('sesgo_parcelas','sesgo'),('rmse_parcelas','rmse')]:
            maxdiff=max(maxdiff,eq(s[field],num(row[col]),col));counts+=1
    pairs=read(out/'contraste_AB_emparejado.csv')
    check(len(pairs)==276,'Pares completo')
    for row in pairs.to_dict('records'):
        ar=select(raw[(raw.escenario=='A')&(raw.ID_POLIGONO==row['id_parcela'])],row['poblacion'])
        br=select(raw[(raw.escenario=='B')&(raw.ID_POLIGONO==row['id_parcela'])],row['poblacion'])
        j=ar.merge(br,on=['repeticion','ID_POLIGONO'],suffixes=('_A','_B'))
        ea=j.prediccion_A-j.real_A;eb=j.prediccion_B-j.real_B
        check(row['n_pares']==len(j),'N pares')
        for col,val in [('mae_A_pares',abs(ea).mean() if len(j) else None),('mae_B_pares',abs(eb).mean() if len(j) else None),('delta_abs_B_menos_A',(abs(eb)-abs(ea)).mean() if len(j) else None),('delta_firmado_B_menos_A',(eb-ea).mean() if len(j) else None),('signos_iguales',int((np.sign(ea)==np.sign(eb)).sum()))]:
            maxdiff=max(maxdiff,eq(val,num(row[col]),col));counts+=1
    # Las dos vistas no son nuevos cálculos: deben ser subconjuntos exactos.
    for file,subset in [('respaldos_separados.csv',parcel[parcel.poblacion.isin(['con_respaldo','grupo','global'])]),('ranking_principal_y_sensibilidad_B.csv',parcel[(parcel.poblacion=='sin_respaldo')&(parcel.orden_caso_fijo!='')])]:
        got=read(out/file);cols=['escenario','poblacion','id_parcela']
        check(got.astype(str).sort_values(cols).reset_index(drop=True).equals(subset.astype(str).sort_values(cols).reset_index(drop=True)),file+' vista distinta')
    dirs=read(out/'direccion_por_grupo.csv')
    municipalities=tab.set_index('id_parcela').municipio.to_dict()
    for row in dirs.to_dict('records'):
        df=select(raw[raw.escenario==row['escenario']],row['poblacion'])
        if row['agrupacion']=='municipio': df=df[df.ID_POLIGONO.map(municipalities)==row['grupo']]
        else:
            bins=df.real.map(lambda y:str(math.floor(y))+'_a_menos_de_'+str(math.floor(y)+1))
            df=df[bins==row['grupo']]
        ss=[stats(z) for _,z in df.groupby('ID_POLIGONO')]
        check(row['n_parcelas']==len(ss) and row['n_registros']==len(df),'Denominador por grupo')
        for col,field in [('mae_parcelas','mae'),('mse_parcelas','mse'),('sesgo_parcelas','sesgo'),('fraccion_sobre_parcelas','fraccion_sobre'),('fraccion_sub_parcelas','fraccion_sub'),('fraccion_cero_parcelas','fraccion_cero')]:
            maxdiff=max(maxdiff,eq(np.mean([z[field] for z in ss]) if ss else None,num(row[col]),'grupo/'+col));counts+=1
    return {'estado':'aprobado','fuente_raw':'T08-v1','anclas_raw_sha256':anchors,'registros_exactos':1380,'parcelas':138,'filas_resumen_parcela':1380,'pares':276,'comparaciones_numericas':counts,'diferencia_maxima':float(maxdiff),'importa_productor':False,'ajustes_modelo':0,'tolerancia_abs':1e-12}


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--fuentes',type=Path,required=True);p.add_argument('--salida',type=Path,required=True);p.add_argument('--evidencia',type=Path,required=True)
    a=p.parse_args();x=run(a.fuentes,a.salida);a.evidencia.write_text(json.dumps(x,indent=2)+'\n');print(json.dumps(x))
