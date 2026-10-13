"""Recalcula R centrado y sus informes sin importar los estimadores/evaluador.

NumPy resuelve una matriz aumentada; scikit-learn se usa sólo para las mismas
particiones registradas, nunca para escalar, Ridge o métricas.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import GroupKFold, StratifiedKFold
from threadpoolctl import threadpool_limits

from scripts.t09_verificar_matrices import prepare, require, sha

RAIZ=Path(__file__).resolve().parents[1]
DISENO='ac28ebdd6b2b5c67650f55a6c33ddfc1f24742a0358e9e0f8b819f2cc93fc429'
REGISTRO='bac0ca3ba04c99cb7269392c7b15464c7745fca0fca2976b4d821c9b23c1922b'
TOL=1e-9
TOL_COEF=1e-10


def matriz(p,intensidad):
    d=p['within_z'];alpha=len(d)*intensidad
    a=np.vstack([d,np.sqrt(alpha)*np.eye(3)])
    beta=np.linalg.lstsq(a,np.r_[p['loo_residual'],np.zeros(3)],rcond=None)[0]
    return beta,p['reference']+(p['z_test']-p['zref'])@beta


def preflight(repo,folder):
    require(sha(repo/'registro/t09/diseno_R_centrado_v2.json')==DISENO,'Diseño v2 cambiado')
    require(sha(repo/'registro/t09/registro_R_centrado_v2.json')==REGISTRO,'Registro v2 cambiado')
    cfg=json.loads((repo/'registro/t09/diseno_R_centrado_v2.json').read_text())
    reg=json.loads((repo/'registro/t09/registro_R_centrado_v2.json').read_text())
    for name,digest in {**cfg['fuentes_sha256'],**reg['historicos_sha256']}.items():
        require(sha(repo/name)==digest,'Fuente/histórico cambiado: '+name)
    man=json.loads((folder/'procedencia.json').read_text())
    required={'resultado.json','predicciones_oof.csv','puntuaciones_internas.csv','seleccion_interna.csv',
              'coeficientes.csv','estados.json','contextos.json','metricas_por_repeticion.csv','metricas_resumen.csv',
              'comparaciones_emparejadas.csv','diferencias_por_parcela.csv'}
    require(set(man['salidas_sha256'])==required,'Salidas completas requeridas')
    require(man['diseno_sha256']==DISENO and man['registro_sha256']==REGISTRO,'Manifiesto de otro diseño')
    require(man['fuentes_sha256']==cfg['fuentes_sha256'] and man['historicos_sha256']==reg['historicos_sha256'],
            'Manifiesto no protege fuentes/históricos')
    for name,digest in man['salidas_sha256'].items():
        require(Path(name).name==name and sha(folder/name)==digest,'Resultado cambiado: '+name)
    expected_code={'scripts/t09_centrado_evaluar.py','scripts/t09_residual_centrado.py','scripts/t09_estimadores.py',
                   'scripts/t09_entradas.py','scripts/t09_evaluar.py','scripts/t09_seleccion.py',
                   'scripts/t09_reportes.py','scripts/t09_diagnostico_atributos.py','scripts/t07_fichas_atributos.py'}
    require(set(man['codigo_sha256'])==expected_code,'Código ejecutado no identificado por completo')
    for name,digest in man['codigo_sha256'].items():require(sha(repo/name)==digest,'Código diferente al ejecutado: '+name)
    result=json.loads((folder/'resultado.json').read_text())
    require(result['fits_ridge_totales']==2006 and result['contextos_externos']==59 and
            result['ajuste_final_59'] is False and result['es_confirmacion_independiente'] is False,
            'Presupuesto/alcance incorrectos')
    return cfg,reg


def internas(train,esc):
    if esc=='A':
        n=train.municipio.map(train.municipio.value_counts())
        estrato=train.municipio.where(n.ge(4),'otros')
        split=StratifiedKFold(4,shuffle=True,random_state=0).split(train,estrato)
    else:
        col='celda_chirps' if esc=='B' else 'municipio'
        split=GroupKFold(4,shuffle=False).split(train,groups=train[col])
    partes=[]
    for ia,ib in split:
        a,b=train.iloc[ia],train.iloc[ib]
        elig=[True]*len(b) if esc=='C' else [bool(x) for x in b.municipio.isin(a.municipio)]
        partes.append(dict(entrenamiento=list(a.index),validacion=list(b.index),elegibles=elig))
    return partes


def clave(r):return round(r['MAE'],6),-r['lambda_reg'],0 if r['ventana']=='jun_oct' else 1


def auditar_matrices(repo,folder):
    tab=pd.read_csv(repo/'registro/t07/tabla_comun.csv').set_index('id_parcela',drop=False).sort_index()
    known=tab[tab.conjunto_origen.eq('ENTRENAMIENTO')]
    held=tab[tab.conjunto_origen.eq('PREDICCION')]
    require(len(known)==138 and len(held)==59 and held.rendimiento_t_ha.isna().all(),'Poblaciones 138/59 cambiadas')
    parts=pd.read_csv(repo/'registro/t03/particiones.csv')
    contexts=json.loads((folder/'contextos.json').read_text())
    states=json.loads((folder/'estados.json').read_text())
    read=lambda name:pd.read_csv(folder/(name+'.csv'),float_precision='round_trip')
    oof,scores,sel,coef=[read(n) for n in ['predicciones_oof','puntuaciones_internas','seleccion_interna','coeficientes']]
    expected=[(s,r,k) for s in ['A','B'] for r in range(1,6) for k in range(5)]+[('C',1,k) for k in range(9)]
    require([(c['escenario'],c['repeticion'],c['particion']) for c in contexts]==expected,'Contextos alterados/duplicados')
    require(len(states)==118 and len(scores)==472 and len(sel)==177 and len(coef)==531 and len(oof)==9108,'Conteos incompletos')
    require(not oof.duplicated(['escenario','repeticion','id_parcela','procedimiento','variante']).any(),'OOF duplicada')
    require(not (set(oof.id_parcela)&set(held.index)),'Reservadas en evaluación')
    require(set(oof.procedimiento)=={'T','R','TC','R_centrado'},'Procedimientos extra/incompletos')
    for col in ['real','municipio','cultivo_origen','celda_chirps']:
        original='rendimiento_t_ha' if col=='real' else col
        require(np.array_equal(oof[col].to_numpy(),known[original].reindex(oof.id_parcela).to_numpy()),
                'Metadato/etiqueta OOF diferente de T07: '+col)
    maximum=dict(prediccion=0.,coeficiente=0.,centro_escala=0.,MAE_interno=0.,media_municipal_train=0.)
    ninner=nouter=npred=0
    def close(a,b,key,tol=TOL):
        difference=float(np.max(np.abs(np.asarray(a,float)-np.asarray(b,float))))
        require(difference<=tol,'Discrepancia independiente: '+key)
        maximum[key]=max(maximum[key],difference)
    for ctx in contexts:
        esc,rep,fold=(ctx[x] for x in ['escenario','repeticion','particion'])
        if esc=='C':ids=sorted(known.index[known.municipio.eq(sorted(known.municipio.unique())[fold])])
        else:
            col='particion_principal' if esc=='A' else 'particion_espacial'
            ids=sorted(parts.loc[parts.repeticion.eq(rep)&parts[col].eq(fold),'ID_POLIGONO'])
        train=known.loc[~known.index.isin(ids)];test=known.loc[ids]
        require(ctx['entrenamiento']==list(train.index) and ctx['evaluacion']==ids,'IDs externos distintos de T03')
        require(ctx['internas']==internas(train,esc),'Particiones internas distintas del registro')
        match=lambda df:df[df.escenario.eq(esc)&df.repeticion.eq(rep)&df.particion.eq(fold)]
        sc=match(scores);choice=match(sel);out=match(oof);co=match(coef)
        require(len(sc)==8 and len(choice)==3,'Selección incompleta en contexto')
        recalculated=[]
        for w in ['abr_oct','jun_oct']:
            preps=[prepare(known.loc[c['entrenamiento']],known.loc[c['validacion']],w) for c in ctx['internas']]
            for intensity in [.01,.1,1,10]:
                eligible,allloss=[],[]
                for c,p in zip(ctx['internas'],preps):
                    _,prediction=matriz(p,intensity)
                    loss=abs(prediction-known.loc[c['validacion']].rendimiento_t_ha.to_numpy())
                    allloss.extend(loss);eligible.extend(loss[np.array(c['elegibles'],bool)]);ninner+=1
                actual=sc[sc.ventana.eq(w)&sc.lambda_reg.eq(intensity)]
                require(len(actual)==1,'Opción interna duplicada/ausente')
                r=actual.iloc[0]
                require(r.n_elegibles==len(eligible) and r.n_validacion==len(allloss) and r.n_ajustes==4,'Denominadores internos')
                close([np.mean(eligible),np.mean(allloss)],[r.MAE,r.MAE_todas],'MAE_interno')
                recalculated.append(dict(ventana=w,lambda_reg=intensity,MAE=float(np.mean(eligible))))
        best=min(recalculated,key=clave)
        selected=choice[choice.variante.eq('seleccionada')]
        require(len(selected)==1 and (selected.iloc[0].ventana,selected.iloc[0].lambda_reg)==(best['ventana'],best['lambda_reg']),
                'Ganador interno distinto de reconstrucción')
        require(sc.seleccionada.sum()==1 and sc[sc.seleccionada].iloc[0].ventana==best['ventana'] and
                sc[sc.seleccionada].iloc[0].lambda_reg==best['lambda_reg'],'Bandera de opción ganadora distinta')
        for w in ['abr_oct','jun_oct']:
            q=min([r for r in recalculated if r['ventana']==w],key=clave)
            c=choice[choice.variante.eq(w)]
            require(len(c)==1 and c.iloc[0].lambda_reg==q['lambda_reg'],'Lambda de ventana fija distinto')
            require(c.iloc[0].alpha==len(train)*q['lambda_reg'],'Alpha de selección distinto')
            close([q['MAE']],[c.iloc[0].MAE_interno],'MAE_interno')
            p=prepare(train,test,w);beta,pred=matriz(p,q['lambda_reg']);nouter+=1
            st=[s['estado'] for s in states if s['escenario']==esc and s['repeticion']==rep and s['particion']==fold and s['estado']['ventana']==w]
            require(len(st)==1,'Estado externo duplicado/ausente');st=st[0]
            require(st['ids_entrenamiento']==list(train.index) and st['n_entrenamiento']==len(train) and
                    st['alpha']==len(train)*q['lambda_reg'] and st['lambda_reg']==q['lambda_reg'] and
                    st['fit_intercept'] is False and st['intercepto']==0 and st['reescalar_desviaciones_intramunicipales'] is False,
                    'Estado fuera del diseño/entrenamiento')
            close(beta,st['coef_estandarizados'],'coeficiente',TOL_COEF)
            close(beta/p['scale'],st['coef_fisicos'],'coeficiente',TOL_COEF)
            require(st['version_modelo']=='T09-R-centrado-v2' and st['columnas']==p['cols'],
                    'Estado con versión/columnas distintas')
            close(p['mean'],st['media_escalado'],'centro_escala',TOL_COEF)
            close(p['scale'],st['escala_global'],'centro_escala',TOL_COEF)
            close(p['z'].mean(0),st['centro_Z_global'],'centro_escala',TOL_COEF)
            for kind,col in [('municipio','municipality'),('grupo','group')]:
                cats=p[col]
                require(set(st['centros_Z_'+kind])==set(cats),'Categorías de centro')
                for cat in sorted(set(cats)):
                    mask=cats==cat
                    require(st['n_'+kind][cat]==int(mask.sum()),'N de centro almacenado distinto')
                    close(p['z'][mask].mean(0),st['centros_Z_'+kind][cat],'centro_escala',TOL_COEF)
                    close([p['y'][mask].mean()],[st['referencia_y_'+kind][cat]],'centro_escala',TOL_COEF)
            close([p['y'].mean()],[st['referencia_y_global']],'centro_escala',TOL_COEF)
            corr=p['within_z']@beta
            maximum['media_municipal_train']=max(maximum['media_municipal_train'],
                max(abs(corr[p['municipality']==m].mean()) for m in set(p['municipality'])))
            wanted=out[out.procedimiento.eq('R_centrado')&out.ventana.eq(w)]
            for variante,g in wanted.groupby('variante'):
                require(set(g.id_parcela)==set(ids) and len(g)==len(ids),'OOF faltante/extra')
                g=g.set_index('id_parcela').loc[ids]
                require(g.version.eq('T09-evaluacion-R-centrado-v2').all(),'OOF nueva con versión histórica')
                require(g.fuente_centrado.eq(p['sources']).all() and g.fuente.eq(p['sources']).all() and
                        g.sin_respaldo.eq(p['sources']=='municipio').all(),'Respaldo/máscara diferentes de entrenamiento')
                close(pred,g.prediccion,'prediccion');close(p['reference'],g.referencia,'prediccion')
                close(pred-p['reference'],g.correccion,'prediccion')
                require(np.array_equal(g.real.to_numpy(),test.rendimiento_t_ha.to_numpy()),'y externa incorrecta')
                cc=co[co.variante.eq(variante)].set_index('columna').loc[p['cols']]
                require(len(cc)==3 and cc.alpha.eq(len(train)*q['lambda_reg']).all(),'Coeficientes/alpha faltantes')
                close(beta,cc.coef_estandarizado,'coeficiente',TOL_COEF);close(beta/p['scale'],cc.coef_fisico,'coeficiente',TOL_COEF)
                close(p['mean'],cc.media_escalado,'centro_escala',TOL_COEF);close(p['scale'],cc.escala,'centro_escala',TOL_COEF)
                npred+=len(g)
            base=out[out.procedimiento.eq('T')].set_index('id_parcela').loc[ids]
            close(p['reference'],base.prediccion,'prediccion')
        npred+=len(test)
    require(ninner==1888 and nouter==118 and npred==6072 and maximum['media_municipal_train']<=1e-12,'Cobertura de reconstrucción incompleta')
    # Filas históricas deben conservar valores y versión v1, incluso tras serializar.
    old=pd.read_csv(repo/'registro/t09/predicciones_oof.csv',float_precision='round_trip')
    keys=['escenario','repeticion','id_parcela','procedimiento','variante']
    actual=oof[oof.procedimiento.isin(['R','TC'])].set_index(keys).sort_index()
    old=old[old.procedimiento.isin(['R','TC'])].set_index(keys).sort_index()
    for col in old:
        pd.testing.assert_series_equal(actual[col],old[col],check_names=False)
    return dict(estado='aprobado',soluciones_internas=ninner,reajustes_externos=nouter,
                predicciones_recalculadas=npred,historicas_preservadas=len(old),max_diferencias=maximum,
                importaciones_estimadores_produccion=0,uso_sklearn='solo_particiones',tolerancia_pred_MAE=TOL,tolerancia_coef_centros=TOL_COEF)


def metrics(g):
    y=g.real.to_numpy();p=g.prediccion.to_numpy();err=p-y
    require(np.isfinite(y).all() and np.isfinite(p).all(),'Reporte no finito')
    r2=np.nan if len(y)<2 or np.all(y==y[0]) else 1-np.dot(err,err)/np.square(y-y.mean()).sum()
    return dict(MAE=float(abs(err).mean()),RMSE=float(np.sqrt(np.dot(err,err)/len(err))),sesgo=float(err.mean()),R2=float(r2))


def bootstrap(dp,cells):
    dp=dp.sort_index();v=dp.to_numpy()
    rng=np.random.RandomState(20261006);parcelas=v[rng.randint(len(v),size=(5000,len(v)))].mean(1)
    totals=pd.DataFrame({'d':dp,'celda':cells.reindex(dp.index)}).groupby('celda').d.agg(['sum','size'])
    require(totals['size'].sum()==len(v),'Bootstrap omitió parcelas')
    rng=np.random.RandomState(20261006);draw=rng.randint(len(totals),size=(5000,len(totals)))
    bloques=totals['sum'].to_numpy()[draw].sum(1)/totals['size'].to_numpy()[draw].sum(1)
    lo,hi=np.percentile(bloques,[2.5,97.5]);lp,hp=np.percentile(parcelas,[2.5,97.5])
    return dict(IC95_celdas_inf=lo,IC95_celdas_sup=hi,IC95_parcelas_inf=lp,IC95_parcelas_sup=hp,n_celdas=len(totals))


def auditar_reportes(folder):
    read=lambda n:pd.read_csv(folder/(n+'.csv'),float_precision='round_trip')
    oof=read('predicciones_oof');ref=oof[oof.procedimiento.eq('T')]
    x=pd.concat([oof,ref.assign(variante='abr_oct'),ref.assign(variante='jun_oct')],ignore_index=True)
    summary,rep,comparisons,diffs=[read(n) for n in ['metricas_resumen','metricas_por_repeticion','comparaciones_emparejadas','diferencias_por_parcela']]
    maximum=0.;nr=nc=nd=0
    def verify(a,b):
        nonlocal maximum
        if np.isnan(a):require(pd.isna(b),'R2 indefinido rellenado');return
        d=float(abs(a-b));require(d<=TOL,'Reporte distinto de reconstrucción');maximum=max(maximum,d)
    for esc,g in x.groupby('escenario'):
        for pob,s in [('todas',g)]+([] if esc=='C' else [('sin_respaldo',g[g.sin_respaldo])]):
            for (variante,proc),h in s.groupby(['variante','procedimiento']):
                vals=[]
                for r,z in h.groupby('repeticion'):
                    mm=metrics(z);vals.append(mm)
                    actual=rep[rep.escenario.eq(esc)&rep.poblacion.eq(pob)&rep.variante.eq(variante)&rep.procedimiento.eq(proc)&rep.repeticion.eq(r)]
                    require(len(actual)==1 and actual.iloc[0].n_predicciones==len(z),'Métrica por repetición ausente')
                    for k,v in mm.items():verify(v,actual.iloc[0][k])
                    nr+=1
                actual=summary[summary.escenario.eq(esc)&summary.poblacion.eq(pob)&summary.variante.eq(variante)&summary.procedimiento.eq(proc)]
                require(len(actual)==1 and actual.iloc[0].n_parcelas==h.id_parcela.nunique(),'Resumen ausente')
                for k in vals[0]:
                    v=np.array([m[k] for m in vals]);verify(np.nanmean(v),actual.iloc[0][k]);verify(np.nanstd(v),actual.iloc[0][k+'_sd_rep'])
            for variante,z in s.groupby('variante'):
                a=z[z.procedimiento.eq('R_centrado')].set_index(['id_parcela','repeticion']).sort_index()
                for proc in (['T','R','TC'] if variante=='seleccionada' else ['T']):
                    b=z[z.procedimiento.eq(proc)].set_index(['id_parcela','repeticion']).sort_index()
                    require(a.index.equals(b.index),'Comparación desalineada')
                    delta=abs(a.prediccion-a.real)-abs(b.prediccion-b.real)
                    dp=delta.groupby(level=0).mean();dr=delta.groupby(level=1).mean()
                    cells=a.reset_index().drop_duplicates('id_parcela').set_index('id_parcela').celda_chirps
                    rmse=np.mean([metrics(a.xs(r,level=1))['RMSE']-metrics(b.xs(r,level=1))['RMSE'] for r in dr.index])
                    actual=comparisons[comparisons.escenario.eq(esc)&comparisons.poblacion.eq(pob)&comparisons.variante.eq(variante)&comparisons.frente_a.eq(proc)]
                    require(len(actual)==1,'Comparación ausente/duplicada');actual=actual.iloc[0]
                    expected=dict(dMAE=dp.mean(),dMAE_media_rep=dr.mean(),dRMSE=rmse,reps_que_mejoran=int((dr<0).sum()),**bootstrap(dp,cells))
                    for k,v in expected.items():verify(v,actual[k])
                    condiciones=[dp.mean()<=-.01,expected['IC95_celdas_sup']<0,(dr<0).sum()>=4,rmse<=.01]
                    aplica=esc=='A' and pob=='sin_respaldo' and variante=='seleccionada' and proc=='T'
                    require(actual.aplica_regla_promocion==aplica and actual.estado_promocion==
                            (('cumple' if all(condiciones) else 'no_cumple') if aplica else 'no_aplica'),'Regla de promoción diferente')
                    d=diffs[diffs.escenario.eq(esc)&diffs.poblacion.eq(pob)&diffs.variante.eq(variante)&diffs.frente_a.eq(proc)].set_index('id_parcela').sort_index()
                    require(d.index.equals(dp.index),'Diferencias por parcela incompletas')
                    for pid,v in dp.items():verify(v,d.loc[pid,'d_error_absoluto'])
                    nc+=1;nd+=len(d)
    require(nr==len(rep) and nc==len(comparisons)==25 and nd==len(diffs),'Cobertura de informes incompleta')
    return dict(estado='aprobado',metricas_por_repeticion=nr,metricas_resumen=len(summary),contrastes=nc,
                diferencias_por_parcela=nd,max_diferencia=maximum)


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--resultados',required=True,type=Path)
    ap.add_argument('--salida',required=True,type=Path);args=ap.parse_args()
    folder=args.resultados.resolve();out=args.salida.resolve()
    require(not out.exists() and out.suffix=='.json' and out.parent.is_relative_to(RAIZ/'reports')
            and out.parent!=RAIZ/'reports','Escribir nueva evidencia sólo en subcarpeta reports/')
    preflight(RAIZ,folder)
    with threadpool_limits(limits=1):result=dict(matrices=auditar_matrices(RAIZ,folder),reportes=auditar_reportes(folder))
    result['verificador_sha256']=sha(Path(__file__))
    result['auxiliar_numpy_sha256']=sha(RAIZ/'scripts/t09_verificar_matrices.py')
    out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
