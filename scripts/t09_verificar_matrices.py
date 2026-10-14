"""Reconstrucción matemática independiente T09; no usa scikit-learn ni producción."""
import argparse
import hashlib
import platform
import json
from pathlib import Path
import time

import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits

RAIZ = Path(__file__).resolve().parents[1]
DISENO_SHA256 = '1072e4196df68359fa3728e504f23ec28dd94b637715854a6635d36d4478081f'
TOL_PREDICCION = 1e-9
TOL_COEFICIENTE = 1e-10
TOL_MAE = TOL_PREDICCION


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def preflight(repo, folder):
    design_path = repo/'registro/t09/diseno.json'
    require(sha(design_path) == DISENO_SHA256, 'Diseño cambiado: no adoptar otra búsqueda en silencio')
    design = json.loads(design_path.read_text(encoding='utf-8'))
    for name, digest in design['fuentes_sha256'].items():
        path = (repo/name).resolve()
        require(path.is_relative_to(repo) and path.is_file(), 'Fuente fuera de raíz o ausente: '+name)
        require(sha(path) == digest, 'Fuente original/diseño modificados: '+name)
    manifest = json.loads((folder/'procedencia.json').read_text(encoding='utf-8'))
    mandatory = {'predicciones_oof.csv','contextos.json','seleccion_interna.csv','coeficientes.csv','puntuaciones_internas.csv','aplicabilidad_59.csv','resultado.json'}
    require(mandatory <= set(manifest['salidas_sha256']), 'Manifiesto no protege todos los resultados matemáticos')
    for name, digest in manifest['salidas_sha256'].items():
        path = (folder/name).resolve()
        require(Path(name).name == name and path.is_relative_to(folder) and path.is_file(), 'Resultado fuera de carpeta o ausente: '+name)
        require(sha(path) == digest, 'Resultado distinto del manifiesto: '+name)
    result = json.loads((folder/'resultado.json').read_text(encoding='utf-8'))
    require(result['diseno_sha256'] == DISENO_SHA256, 'OOF pertenece a otro diseño')
    require(result['contextos_externos'] == 59 and result['ajustes_climaticos'] == 6018 and not result['ajuste_final_59'], 'Entrega fuera de evaluación T09 v1')
    return {'sha_diseno': DISENO_SHA256, 'fuentes_protegidas_verificadas': len(design['fuentes_sha256']), 'resultados_manifest_verificados': len(manifest['salidas_sha256'])}


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def territory(municipality, group, y, test_mun, test_group, z):
    mu_m = {m: y[municipality==m].mean() for m in sorted(set(municipality))}
    mu_g = {g: y[group==g].mean() for g in sorted(set(group))}
    z_m = {m: z[municipality==m].mean(axis=0) for m in sorted(set(municipality))}
    z_g = {g: z[group==g].mean(axis=0) for g in sorted(set(group))}
    yg, zg = y.mean(), z.mean(axis=0)
    references, zref, sources = [], [], []
    for m,g in zip(test_mun,test_group):
        if m in mu_m:
            references.append(mu_m[m]); zref.append(z_m[m]); sources.append('municipio')
        elif g in mu_g:
            references.append(mu_g[g]); zref.append(z_g[g]); sources.append('grupo')
        else:
            references.append(yg); zref.append(zg); sources.append('global')
    return np.array(references), np.array(zref), np.array(sources)


def loo_direct(municipality, group, y):
    refs=[]
    for i,(m,g) in enumerate(zip(municipality,group)):
        mask=municipality==m
        mask[i]=False
        if not mask.any():
            mask=group==g
            mask[i]=False
        if not mask.any():
            mask=np.ones(len(y),dtype=bool)
            mask[i]=False
        refs.append(y[mask].mean())
    return np.array(refs)


def prepare(train,test,window):
    cols=[f'{s}_{window}' for s in ('prec_acumulada_mm','tmin_media_c','tmax_media_c')]
    xx=train[cols].to_numpy(float)
    mean=xx.mean(axis=0)
    scale=xx.std(axis=0,ddof=0)
    scale=np.where(scale==0,1.,scale)
    z=(xx-mean)/scale
    zz=(test[cols].to_numpy(float)-mean)/scale
    y=train.rendimiento_t_ha.to_numpy(float)
    m,g=train.municipio.to_numpy(),train.cultivo_origen.to_numpy()
    target_m,target_g=test.municipio.to_numpy(),test.cultivo_origen.to_numpy()
    ref,zref,source=territory(m,g,y,target_m,target_g,z)
    mu_y={v:y[m==v].mean() for v in sorted(set(m))}
    mu_z={v:z[m==v].mean(axis=0) for v in sorted(set(m))}
    within_z=z-np.array([mu_z[v] for v in m])
    within_y=y-np.array([mu_y[v] for v in m])
    return {'cols':cols,'mean':mean,'scale':scale,'z':z,'z_test':zz,'y':y,
            'reference':ref,'zref':zref,'sources':source,
            'within_z':within_z,'within_y':within_y,'loo_residual':y-loo_direct(m,g,y),
            'municipality':m,'group':g,'test_municipality':target_m,'test_group':target_g}


def matrix_solution(prep,method,penalty):
    z,y=prep['z'],prep['y']
    alpha=len(y)*penalty
    if method=='TC':
        # Alternativa a centrar: columnas indicadoras con interceptos sin penalizar.
        names=sorted(set(prep['municipality']))
        dummies=np.column_stack([prep['municipality']==m for m in names]).astype(float)
        design=np.column_stack([dummies,z])
        regularization=np.column_stack([np.zeros((3,len(names))),np.sqrt(alpha)*np.eye(3)])
        theta=np.linalg.lstsq(np.vstack([design,regularization]),np.concatenate([y,np.zeros(3)]),rcond=None)[0]
        beta=theta[-3:]
        intercepts={m:theta[i] for i,m in enumerate(names)}
        residual_y=y-z@beta
        groups={g:residual_y[prep['group']==g].mean() for g in sorted(set(prep['group']))}
        base=np.array([intercepts[m] if m in intercepts else groups.get(g,residual_y.mean())
                       for m,g in zip(prep['test_municipality'],prep['test_group'])])
        pred=base+prep['z_test']@beta
    elif method=='R':
        design=np.vstack([z,np.sqrt(alpha)*np.eye(3)])
        target=np.concatenate([prep['loo_residual'],np.zeros(3)])
        beta=np.linalg.lstsq(design,target,rcond=None)[0]
        pred=prep['reference']+prep['z_test']@beta
    elif method=='CL':
        design=np.column_stack([np.ones(len(y)),z])
        regularization=np.column_stack([np.zeros(3),np.sqrt(alpha)*np.eye(3)])
        theta=np.linalg.lstsq(np.vstack([design,regularization]),np.concatenate([y,np.zeros(3)]),rcond=None)[0]
        beta=theta[1:]
        pred=theta[0]+prep['z_test']@beta
    else:
        raise ValueError('Método fuera del diseño')
    return beta,pred


def applicable(folder,known,held):
    records=pd.read_csv(folder/'aplicabilidad_59.csv').set_index('id_parcela')
    require(set(records.index)==set(held.index) and len(records)==59,'Aplicabilidad no cubre59IDs')
    cols=[f'{s}_{w}' for w in ('abr_oct','jun_oct') for s in ('prec_acumulada_mm','tmin_media_c','tmax_media_c')]
    outside_global=outside_municipal=scarce=0
    for pid,r in held.iterrows():
        row=records.loc[pid]
        tr=known[known.municipio.eq(r.municipio)]
        g=known[known.cultivo_origen.eq(r.cultivo_origen)]
        expected='municipio' if len(tr) else ('grupo' if len(g) else 'global')
        require(row.fuente_referencia_prevista==expected,'Fuente59distinta de entrenamiento')
        require(row.n_etiquetas_municipio==len(tr),'Conteo de soporte59distinto')
        require(bool(row.soporte_municipal_escaso)==(len(tr)<4),'Bandera escasa59distinta')
        require(bool(row.clima_completo) and not bool(row.modelo_ajustado),'Aplicabilidad confunde ajuste final')
        glob=[c for c in cols if not known[c].min() <= r[c] <= known[c].max()]
        mun=[c for c in cols if len(tr) and not tr[c].min() <= r[c] <= tr[c].max()]
        sglob='' if pd.isna(row.fuera_rango_global) else row.fuera_rango_global
        smun='' if pd.isna(row.fuera_rango_municipio) else row.fuera_rango_municipio
        require(sglob==';'.join(glob) and smun==';'.join(mun),'Rangos59distintos')
        outside_global+=bool(glob); outside_municipal+=bool(mun); scarce+=len(tr)<4
    return {'ids':59,'fuentes_municipales':int(records.fuente_referencia_prevista.eq('municipio').sum()),
            'soporte_escaso':scarce,'fuera_rango_global_al_menos_una_entrada':outside_global,
            'fuera_rango_municipio_al_menos_una_entrada':outside_municipal,'ajustes_finales_59':0}


def audit(repo,folder,internal=True):
    table=pd.read_csv(repo/'registro/t07/tabla_comun.csv').set_index('id_parcela',drop=False).sort_index()
    known=table[table.conjunto_origen.eq('ENTRENAMIENTO')]
    held=table[table.conjunto_origen.eq('PREDICCION')]
    contexts=json.loads((folder/'contextos.json').read_text())
    oof=pd.read_csv(folder/'predicciones_oof.csv',float_precision='round_trip')
    selected=pd.read_csv(folder/'seleccion_interna.csv',float_precision='round_trip')
    coef=pd.read_csv(folder/'coeficientes.csv',float_precision='round_trip')
    scores=pd.read_csv(folder/'puntuaciones_internas.csv',float_precision='round_trip')
    maximum_coef=maximum_pred=maximum_scale=maximum_score=maximum_score_all=0.
    outer_checks=inner_solutions=score_checks=pred_checks=coefficient_outputs=0
    for ctx in contexts:
        esc,rep,fold=ctx['escenario'],ctx['repeticion'],ctx['particion']
        train,test=known.loc[ctx['entrenamiento']],known.loc[ctx['evaluacion']]
        mask_sel=selected.escenario.eq(esc)&selected.repeticion.eq(rep)&selected.particion.eq(fold)
        choices=selected[mask_sel & selected.variante.isin(['abr_oct','jun_oct'])]
        require(len(choices)==6,'Configuraciones externas únicas incompletas')
        prepared={w:prepare(train,test,w) for w in ('abr_oct','jun_oct')}
        ref_rows=oof[oof.escenario.eq(esc)&oof.repeticion.eq(rep)&oof.particion.eq(fold)&oof.procedimiento.eq('T')].set_index('id_parcela').loc[test.index]
        ref_diff=float(np.max(abs(prepared['abr_oct']['reference']-ref_rows.prediccion.to_numpy())))
        require(ref_diff<=TOL_PREDICCION,'Referencia territorial distinta de solución independiente')
        maximum_pred=max(maximum_pred,ref_diff); pred_checks+=len(ref_rows)
        for r in choices.itertuples():
            prep=prepared[r.ventana]
            beta,pred=matrix_solution(prep,r.procedimiento,r.lambda_reg)
            coefficients=coef[coef.escenario.eq(esc)&coef.repeticion.eq(rep)&coef.particion.eq(fold)
                              &coef.procedimiento.eq(r.procedimiento)&coef.ventana.eq(r.ventana)]
            for variant,wanted in coefficients.groupby('variante'):
                wanted=wanted.set_index('columna').loc[prep['cols']]
                require(len(wanted)==3 and wanted.alpha.eq(len(train)*r.lambda_reg).all(),'Coeficientes/alpha incompatibles')
                dc=float(max(np.max(abs(beta-wanted.coef_estandarizado.to_numpy())),
                             np.max(abs(beta/prep['scale']-wanted.coef_fisico.to_numpy()))))
                ds=float(max(np.max(abs(prep['mean']-wanted.media_escalado.to_numpy())),
                             np.max(abs(prep['scale']-wanted.escala.to_numpy()))))
                require(dc<=TOL_COEFICIENTE and ds<=TOL_COEFICIENTE,'Coeficientes/escalado difieren de matriz independiente')
                maximum_coef=max(maximum_coef,dc); maximum_scale=max(maximum_scale,ds); coefficient_outputs+=1
            actual=oof[oof.escenario.eq(esc)&oof.repeticion.eq(rep)&oof.particion.eq(fold)
                       &oof.procedimiento.eq(r.procedimiento)&oof.ventana.eq(r.ventana)]
            for variant,g in actual.groupby('variante'):
                g=g.set_index('id_parcela').loc[test.index]
                dp=float(np.max(abs(pred-g.prediccion.to_numpy())))
                require(dp<=TOL_PREDICCION,'Predicciones externas distintas de solución independiente')
                maximum_pred=max(maximum_pred,dp); pred_checks+=len(pred)
            outer_checks+=1
        if internal:
            internal_prep={}
            for w in ('abr_oct','jun_oct'):
                for k,inner in enumerate(ctx['internas']):
                    internal_prep[(w,k)]=prepare(known.loc[inner['entrenamiento']],known.loc[inner['validacion']],w)
            ctx_scores=scores[scores.escenario.eq(esc)&scores.repeticion.eq(rep)&scores.particion.eq(fold)]
            require(len(ctx_scores)==24,'Scores internos incompletos')
            for r in ctx_scores.itertuples():
                losses,losses_all=[],[]
                for k,inner in enumerate(ctx['internas']):
                    prep=internal_prep[(r.ventana,k)]
                    _,prediction=matrix_solution(prep,r.procedimiento,r.lambda_reg)
                    truth=known.loc[inner['validacion']].rendimiento_t_ha.to_numpy()
                    loss=abs(prediction-truth)
                    losses_all.extend(loss); losses.extend(loss[np.array(inner['elegibles'],dtype=bool)])
                    inner_solutions+=1
                ds=abs(np.mean(losses)-r.MAE); da=abs(np.mean(losses_all)-r.MAE_todas)
                require(ds<=TOL_MAE and da<=TOL_MAE,'Puntuación interna distinta de matrices independientes')
                require(len(losses)==r.n_elegibles and len(losses_all)==r.n_validacion,'Denominadores internos incompatibles')
                maximum_score=max(maximum_score,float(ds)); maximum_score_all=max(maximum_score_all,float(da)); score_checks+=1
    require(outer_checks==354 and pred_checks==15180 and coefficient_outputs==531
            and (not internal or (inner_solutions==5664 and score_checks==1416)), 'Cobertura matemática incompleta')
    return {'estado':'aprobado','modulos_produccion_importados':0,'sklearn_usado':False,
            'ecuacion':'lstsq(A_aug,y_aug); TC=municipal_dummies_unpenalized; CL=global_intercept_unpenalized; R=no_intercept',
            'reajustes_externos_unicos':outer_checks,'salidas_coeficientes_con_reutilizacion':coefficient_outputs,
            'predicciones_externas_recalculadas':pred_checks,
            'soluciones_internas_recalculadas':inner_solutions,'puntuaciones_internas_recalculadas':score_checks,
            'max_diferencia_coeficientes':maximum_coef,'max_diferencia_predicciones':maximum_pred,
            'max_diferencia_media_escala':maximum_scale,'max_diferencia_MAE_interno':maximum_score,
            'max_diferencia_MAE_todas_interno':maximum_score_all,'aplicabilidad59':applicable(folder,known,held)}


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--raiz', '--repo', dest='repo',type=Path,default=RAIZ)
    ap.add_argument('--resultados',type=Path,required=True)
    ap.add_argument('--salida',type=Path,required=True)
    args=ap.parse_args()
    args.repo, args.resultados, args.salida = args.repo.resolve(), args.resultados.resolve(), args.salida.resolve()
    allowed = [args.repo/'reports', args.repo/'data/processed/t09']
    require(any(args.salida.parent.is_relative_to(base) and args.salida.parent != base for base in allowed) and args.salida.suffix == '.json', 'La auditoría sólo escribe un nuevo JSON en subcarpeta reports/ o data/processed/t09/')
    require(not args.salida.exists(),'La evidencia anterior se conserva; elegir nuevo archivo')
    provenance = preflight(args.repo, args.resultados)
    start=time.monotonic()
    with threadpool_limits(limits=1):
        result=audit(args.repo,args.resultados,True)
    result.update(provenance)
    result['tolerancias'] = {'prediccion':TOL_PREDICCION,'coeficientes_y_escala':TOL_COEFICIENTE,'MAE':TOL_MAE}
    result['MAE_tolerancia_derivada'] = 'abs(MAE_ind-MAE_prod) no excede la media de abs(pred_ind-pred_prod); mismo límite de predicción'
    result['entorno'] = {'sistema':platform.system(),'arquitectura':platform.machine(),'numpy':np.__version__,'pandas':pd.__version__}
    result['verificacion_matematica_completa'] = True
    args.salida.parent.mkdir(parents=True,exist_ok=True)
    args.salida.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False,indent=2))
    print('Duración de comprobación: '+str(round(time.monotonic()-start,2))+' segundos')


if __name__=='__main__':
    main()
