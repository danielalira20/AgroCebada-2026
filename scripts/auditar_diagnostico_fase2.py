"""Auditor vectorizado desde CSV originales; no importa productores/modelos."""
import argparse
from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path
import numpy as np
import pandas as pd

from scripts.auditar_diagnostico_fase1 import read, check


def run(root,phase0,out):
    spec=Path(__file__).resolve().parents[1]/'registro/diagnostico/fase0_fuentes.json'
    check(hashlib.sha256(spec.read_bytes()).hexdigest()=='f8cf1e2bc8b088d925acdff9693707d1fd513ad535ec32bc8d145995df55132a','Fuentes distintas')
    sources=json.loads(spec.read_text())
    for task,meta in sources['fuentes'].items():
        for f in meta['archivos']:
            p=root/task/f['ruta'];check(p.resolve().is_relative_to(root.resolve()) and not p.is_symlink(),'Ruta fuera root')
            check(p.is_file() and p.stat().st_size==f['bytes'],'Fuente ausente')
            check(hashlib.sha256(p.read_bytes()).hexdigest()==f['sha256'],'Fuente alterada')
    check(hashlib.sha256((phase0/'manifest.json').read_bytes()).hexdigest()=='e5eb9bd692d00f64b0b59fa611723bff7dcaabf00297bc5c3aed27341984f691','Manifiesto fase0 distinto')
    check(hashlib.sha256((phase0/'compatibilidad_procedimientos.csv').read_bytes()).hexdigest()=='869490d52547457441dd43000f09d5fa8c6724c733e2e601159a00e46d32322a','Catálogo previo distinto')
    original_catalog=read(phase0/'compatibilidad_procedimientos.csv')
    cat=read(out/'catalogo_series.csv')
    fields=['fuente','archivo','candidato','variante','version']
    check(len(cat)==51 and set(map(tuple,cat[fields].to_numpy()))==set(map(tuple,original_catalog[fields].to_numpy())),'Catálogo cambia identidad')
    check(cat.serie_id.to_list()==[f'S{i:03d}' for i in range(1,52)],'IDs series')
    tasks={'T08':'base','T09':'t09','T10':'t10','T11':'t11','T13':'t13','T14':'t14'}
    native={};frames=[]
    for m in cat.to_dict('records'):
        path=root/tasks[m['fuente']]/m['archivo']
        if path not in native:native[path]=read(path)
        df=native[path].copy()
        if 'variante' not in df:df['variante']='seleccionada'
        df=df[(df.candidato==m['candidato'])&(df.version==m['version'])&(df.variante==m['variante'])&df.escenario.isin(['A','B'])].copy()
        check(len(df)==1380 and not df.duplicated(['escenario','repeticion','ID_POLIGONO']).any(),'Raw serie incompleta')
        df=df.sort_values(['escenario','ID_POLIGONO','repeticion']).reset_index(drop=True);frames.append(df)
    tab=read(root/'base/registro/t07/tabla_comun.csv');tt=tab[tab.rendimiento_t_ha!=''].set_index('id_parcela')
    ids=sorted(tt.index);check(len(ids)==138,'138 etiquetadas')
    municipalities=tt.municipio.to_dict();registration_groups=tt.cultivo_origen.to_dict()
    labels={i:float(v) for i,v in tt.rendimiento_t_ha.items()}
    lattice=pd.MultiIndex.from_product([['A','B'],ids,range(1,6)],names=['escenario','ID_POLIGONO','repeticion'])
    for df in frames:
        check(pd.MultiIndex.from_frame(df[['escenario','ID_POLIGONO','repeticion']]).equals(lattice),'Malla ID/contexto')
        check(np.array_equal(df.real.to_numpy(),frames[0].real.to_numpy()),'Etiqueta raw distinta')
        check(np.array_equal(df.particion.to_numpy(),frames[0].particion.to_numpy()),'Fold raw distinto')
        check(np.array_equal(df.fuente.to_numpy(),frames[0].fuente.to_numpy()),'Fuente máscara distinta')
    check(np.array_equal(frames[0].real.to_numpy(),np.tile(np.repeat([float(tt.loc[i].rendimiento_t_ha) for i in ids],5),2)),'Raw distinto de T07')
    preds=np.stack([df.prediccion.to_numpy().reshape(2,138,5) for df in frames])
    y=frames[0].real.to_numpy().reshape(2,138,5);err=preds-y[None,:,:,:]
    canon_source=frames[0].fuente.to_numpy().reshape(2,138,5)
    matrix=read(out/'matriz_procedimientos_por_caso.csv');check(len(matrix)==28152,'Matriz incompleta')
    check(not matrix.duplicated(['serie_id','escenario','poblacion','id_parcela']).any(),'Matriz duplicada')
    maxdiff=0.;checks=0;computed={};tops={};cat_records=cat.to_dict('records')
    def compare(actual,expected,col):
        nonlocal maxdiff,checks
        aa=np.array([float(v) if v!='' else np.nan for v in actual],dtype=float)
        check(all(v=='' or math.isfinite(float(v)) for v in actual),'No finito/no vacío '+col)
        bb=np.asarray(expected,dtype=float)
        check(np.array_equal(np.isnan(aa),np.isnan(bb)),'Vacíos '+col)
        if np.any(~np.isnan(aa)):
            diff=np.max(abs(aa[~np.isnan(aa)]-bb[~np.isnan(bb)]));check(diff<=1e-12,'Diferencia '+col);maxdiff=max(maxdiff,float(diff))
        checks+=len(aa)
    def avg(v,mask):
        n=mask.sum(axis=1)
        return np.divide((v*mask).sum(axis=1),n,out=np.full(138,np.nan),where=n>0)
    for si,m in enumerate(cat_records):
        for ei,e in enumerate(['A','B']):
            for pop in ['todas','sin_respaldo']:
                mask=np.ones((138,5),dtype=bool) if pop=='todas' else canon_source[ei]=='municipio'
                n=mask.sum(axis=1);a=abs(err[si,ei]);mae=avg(a,mask);bias=avg(err[si,ei],mask)
                delta=avg(a-abs(err[0,ei]),mask);dist=avg(abs(preds[si,ei]-preds[0,ei]),mask)
                hits=np.zeros(138,dtype=int)
                for rep in range(5):
                    ranked=sorted(np.flatnonzero(mask[:,rep]),key=lambda j:(-a[j,rep],ids[j]))[:10];hits[ranked]+=1
                    tops[si,ei,pop,rep]=set(ranked)
                got=matrix[(matrix.serie_id==m['serie_id'])&(matrix.escenario==e)&(matrix.poblacion==pop)].sort_values('id_parcela')
                check(got.id_parcela.to_list()==ids,'IDs matriz')
                ex={'n_elegibles':n,'mae':mae,'sesgo':bias,'mse':avg(err[si,ei]**2,mask),'delta_mae':delta,'distancia_pred_T08':dist,
                    'fraccion_mismo_signo_T08':avg(np.sign(err[si,ei])==np.sign(err[0,ei]),mask),
                    'sobre':((err[si,ei]>0)&mask).sum(axis=1),'sub':((err[si,ei]<0)&mask).sum(axis=1),'ceros':((err[si,ei]==0)&mask).sum(axis=1),
                    'apariciones_top10':hits,'fraccion_top10':np.divide(hits,n,out=np.full(138,np.nan),where=n>0),
                    'n_municipal':((canon_source[ei]=='municipio')&mask).sum(axis=1),'n_grupo':((canon_source[ei]=='grupo')&mask).sum(axis=1),'n_global':((canon_source[ei]=='global')&mask).sum(axis=1),
                    'rango_error':np.array([np.ptp(err[si,ei,j,mask[j]]) if n[j] else np.nan for j in range(138)])}
                for col,vals in ex.items():compare(got[col],vals,col)
                computed[(si,ei,pop)]=(mae,bias,delta,dist,hits,n)
    sm=read(out/'resumen_comparaciones.csv');rp=read(out/'metricas_por_repeticion.csv')
    check(len(sm)==204 and len(rp)==1020,'Resúmenes incompletos')
    bysid={sid:i for i,sid in enumerate(cat.serie_id)}
    for r in sm.to_dict('records'):
        si=bysid[r['serie_id']];ei=['A','B'].index(r['escenario']);pop=r['poblacion'];mae,bias,delta,dist,hits,n=computed[si,ei,pop]
        mask=np.ones((138,5),dtype=bool) if pop=='todas' else canon_source[ei]=='municipio'
        rm=(abs(err[si,ei])*mask).sum(axis=0)/mask.sum(axis=0)
        repdiff=((abs(err[si,ei])-abs(err[0,ei]))*mask).sum(axis=0)/mask.sum(axis=0)
        values={'mae_parcelas':np.nanmean(mae),'mae_media_repeticiones':rm.mean(),'delta_mae_parcelas':np.nanmean(delta),'distancia_pred_T08':np.nanmean(dist),
                'n_parcelas':(n>0).sum(),'n_registros':n.sum(),'parcelas_mejoran':(delta < -1e-9).sum(),'parcelas_empeoran':(delta>1e-9).sum(),'parcelas_sin_cambio':(abs(delta)<=1e-9).sum()}
        values['overlap_top10_T08']=np.mean([len(tops[si,ei,pop,k]&tops[0,ei,pop,k])/10 for k in range(5)])
        values['repeticiones_mejoran']=(repdiff < -1e-9).sum()
        for col,val in values.items():compare(pd.Series([r[col]]),[val],col)
        for rep in range(5):
            got=rp[(rp.serie_id==r['serie_id'])&(rp.escenario==r['escenario'])&(rp.poblacion==pop)&(rp.repeticion==rep+1)]
            compare(got.mae,[rm[rep]],'MAE repetición')
            diff=((abs(err[si,ei])-abs(err[0,ei]))*mask).sum(axis=0)/mask.sum(axis=0)
            compare(got.delta_mae,[diff[rep]],'delta repetición')
    pairs=read(out/'pares_procedimientos.csv');check(len(pairs)==3960,'Pares incompletos')
    for r in pairs.to_dict('records'):
        si=bysid[r['serie_1']];sj=bysid[r['serie_2']];ei=['A','B'].index(r['escenario']);pop=r['poblacion']
        mask=np.ones((138,5),dtype=bool) if pop=='todas' else canon_source[ei]=='municipio'
        pp=avg(abs(preds[si,ei]-preds[sj,ei]),mask);x=computed[si,ei,pop][1];z=computed[sj,ei,pop][1];valid=~np.isnan(x)
        cv=np.corrcoef(x[valid],z[valid])[0,1] if np.std(x[valid]) and np.std(z[valid]) else np.nan
        compare(pd.Series([r['distancia_pred']]),[np.nanmean(pp)],'distancia par')
        compare(pd.Series([r['correlacion_sesgos_por_parcela']]),[cv],'correlación par')
    co=read(out/'coincidencias_por_frente.csv');check(len(co)==3312,'Frentes incompletos')
    for r in co.to_dict('records'):
        ei=['A','B'].index(r['escenario']);j=ids.index(r['id_parcela']);pop=r['poblacion']
        choices=[i for i,m in enumerate(cat_records) if m['frente']==r['frente'] and str(m['es_referencia'])=='False']
        vals=[computed[i,ei,pop] for i in choices];valid=[z for z in vals if z[5][j]]
        expected={'n_series_configuradas':len(choices),'n_series_elegibles':len(valid),
            'mae_min':min(z[0][j] for z in valid) if valid else np.nan,'mae_max':max(z[0][j] for z in valid) if valid else np.nan,
            'delta_min':min(z[2][j] for z in valid) if valid else np.nan,'delta_max':max(z[2][j] for z in valid) if valid else np.nan,
            'fraccion_top10_min':min(z[4][j]/z[5][j] for z in valid) if valid else np.nan,'fraccion_top10_max':max(z[4][j]/z[5][j] for z in valid) if valid else np.nan}
        for col,val in expected.items():compare(pd.Series([r[col]]),[val],col)
    # Comprobación de soporte por exclusión explícita, distinta de la fórmula cerrada.
    part=read(root/'base/registro/t03/particiones.csv');ss=read(out/'sensibilidad_media_referencia.csv')
    check(len(ss)==1380 and not ss.duplicated(['escenario','repeticion','id_parcela']).any(),'Soporte incompleto/duplicado')
    native_context={(r.escenario,int(r.repeticion),r.ID_POLIGONO):int(r.particion) for r in frames[0].itertuples()}
    check(set(map(tuple,ss[['escenario','repeticion','id_parcela']].to_numpy()))==set(native_context),'Contextos soporte distintos')
    cache={};direct=[];training={}
    for esc,field in [('A','particion_principal'),('B','particion_espacial')]:
        for rep in range(1,6):
            rows=part[part.repeticion==rep]
            for fold in range(5):training[esc,rep,fold]=set(rows[rows[field]!=fold].ID_POLIGONO)
    for r in ss.to_dict('records'):
        check(r['particion']==native_context[r['escenario'],r['repeticion'],r['id_parcela']],'Fold soporte distinto')
        train=training[r['escenario'],r['repeticion'],r['particion']]
        check(r['id_parcela'] not in train,'Eval en entrenamiento')
        check(r['n_entrenamiento']==len(train),'N entrenamiento distinto')
        mun=municipalities[r['id_parcela']];group=registration_groups[r['id_parcela']]
        pool=sorted(i for i in train if municipalities[i]==mun);nmun=len(pool);source='municipio'
        if not pool:pool=sorted(i for i in train if registration_groups[i]==group);source='grupo'
        if not pool:pool=sorted(train);source='global'
        key=tuple(pool)
        if key not in cache:
            yy=np.array([labels[i] for i in pool]);mu=yy.mean()
            dropped=np.array([np.delete(yy,j).mean() for j in range(len(pool))]) if len(pool)>1 else None
            cache[key]=(mu,yy.std(),dropped)
        mu,sd,dropped=cache[key]
        check(source==r['fuente_referencia'] and r['n_municipal']==nmun and r['n_pool']==len(pool),'Fuente/conteos soporte')
        check(r['firma_pool']==hashlib.sha256('|'.join(pool).encode()).hexdigest(),'Pool distinto')
        compare(pd.Series([r['media_pool']]),[mu],'media soporte');compare(pd.Series([r['sd_pool']]),[sd],'SD soporte')
        if dropped is None:
            check(r['influencia_max_abs']=='' and r['media_sin_etiqueta']=='' and r['etiqueta_mas_influyente']=='','Pool n1 inventado')
            maximpact=np.nan
        else:
            maximpact=np.max(abs(dropped-mu));check(r['etiqueta_mas_influyente'] in pool,'Etiqueta fuera training')
            pos=pool.index(r['etiqueta_mas_influyente'])
            compare(pd.Series([r['influencia_max_abs']]),[maximpact],'Influencia explícita')
            compare(pd.Series([r['media_sin_etiqueta']]),[dropped[pos]],'Media sin etiqueta explícita')
            check(abs(abs(dropped[pos]-mu)-maximpact)<=1e-12,'Etiqueta no maximiza influencia')
        direct.append(dict(escenario=r['escenario'],municipio=mun,fuente_referencia=source,id_parcela=r['id_parcela'],n_municipal=nmun,n_pool=len(pool),media_pool=mu,influencia_max_abs=maximpact))
    native_support=pd.DataFrame(direct);ficha=read(out/'ficha_soporte_municipal.csv');check(len(ficha)==54,'Ficha incompleta')
    for r in ficha.to_dict('records'):
        z=native_support[(native_support.escenario==r['escenario'])&(native_support.municipio==r['municipio'])&(native_support.fuente_referencia==r['fuente_referencia'])]
        check(r['n_parcelas']==z.id_parcela.nunique() and r['n_registros']==len(z),'N ficha')
        for col,v in [('n_municipal_min',z.n_municipal.min()),('n_municipal_max',z.n_municipal.max()),('n_pool_min',z.n_pool.min()),('n_pool_max',z.n_pool.max()),('referencia_min',z.media_pool.min()),('referencia_max',z.media_pool.max()),('influencia_max_abs',z.influencia_max_abs.max())]:
            compare(pd.Series([r[col]]),[v],'Ficha/'+col)
    return dict(estado='aprobado',fuentes_sha256_verificadas=154,series=51,registros_raw_AB=70380,filas_matriz=28152,pares=3960,
                soporte_contextos=1380,comparaciones_numericas=checks,diferencia_maxima=maxdiff,tolerancia_abs=1e-12,
                productor_importado=False,modelos_importados=False,reentrenamientos=0,retiro_explicito_entrenamiento=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--fuentes',type=Path,required=True);p.add_argument('--fase0',type=Path,required=True);p.add_argument('--salida',type=Path,required=True);p.add_argument('--evidencia',type=Path,required=True)
    a=p.parse_args();x=run(a.fuentes,a.fase0,a.salida);check(not a.evidencia.exists(),'Evidencia existe: usar destino nuevo');a.evidencia.write_text(json.dumps(x,indent=2)+'\n');print(json.dumps(x))
