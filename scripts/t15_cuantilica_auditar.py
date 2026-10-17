"""Auditor independiente: otra formulación primal, dual, estados, selección y OOF."""
import argparse
import csv
import gzip
import hashlib
import json
import math
from pathlib import Path
import warnings
import numpy as np
from scipy.optimize import linprog
from scripts.evaluacion_comun_contrato import exigir, sha, leer_csv, validar_oof
from scripts.t15_comparaciones_contrato import cargar
from scripts.evaluacion_comun_modelo import preparar_contexto, divisiones_internas


def solve(c, **kw):
    with warnings.catch_warnings(record=True) as notices:
        warnings.simplefilter('always')
        r = linprog(c, method='highs-ds', options=dict(primal_feasibility_tolerance=1e-9,
            dual_feasibility_tolerance=1e-9, simplex_dual_edge_weight_strategy='steepest-devex'), **kw)
    exigir(not notices and r.success, 'Auditor LP: ' + r.message)
    return r


def primal_independiente(D, y, groups, alpha):
    n,p = D.shape; levels = sorted(set(groups)); k = len(levels)
    C = np.asarray([[float(m==g) for g in levels] for m in groups])
    # Variables no negativas a+,a-,b+,b-,r+,r-; sólo igualdades.
    E = np.c_[C,-C,D,-D,np.eye(n),-np.eye(n)]
    c = np.r_[np.zeros(2*k),np.full(2*p,alpha),np.full(2*n,.5/n)]
    pri = solve(c,A_eq=E,b_eq=y,bounds=(0,None))
    equal = [*E, c]; rhs = [*y, float(pri.fun)]; cur = pri
    for j in range(p):
        cj = np.zeros(len(c)); cj[2*k+j]=1.; cj[2*k+p+j]=-1.
        cur=solve(cj,A_eq=np.asarray(equal),b_eq=np.asarray(rhs),bounds=(0,None))
        value=float(cur.fun);value=0. if abs(value)<=1e-9 else value
        equal.append(cj);rhs.append(value)
    beta=np.array(rhs[-p:])
    # Certificado dual distinto del primal: suma por municipio=0 y |D.T s|<=alpha.
    dual=solve(-y,A_ub=np.r_[D.T,-D.T],b_ub=np.full(2*p,alpha),
               A_eq=C.T,b_eq=np.zeros(k),bounds=[(-.5/n,.5/n)]*n)
    exigir(abs(pri.fun+dual.fun)<=1e-7,'Brecha primal-dual')
    return beta,float(pri.fun),float(-dual.fun)


def preparar_independiente(X, columns):
    v=np.array([[float(row[c]) for c in columns] for _,row in X.iterrows()])
    n=len(v); mu=np.array([math.fsum(v[:,j])/n for j in range(v.shape[1])])
    sd=np.array([math.sqrt(math.fsum((float(x)-mu[j])**2 for x in v[:,j])/n) for j in range(v.shape[1])])
    sd[sd==0]=1.;z=(v-mu)/sd; groups=X.municipio.to_numpy()
    centers={g:np.array([math.fsum(z[groups==g,j])/int(sum(groups==g)) for j in range(v.shape[1])])
             for g in sorted(set(groups))}
    d=np.array([row-centers[g] for row,g in zip(z,groups)])
    return mu,sd,centers,d


def auditar_estado(state,X,y,q,consulta,refit=True):
    X=X.sort_index();y=y.loc[X.index].to_numpy(float);cols=state['columnas'];groups=X.municipio.to_numpy()
    exigir(state['ids_entrenamiento']==list(X.index),'IDs train distintos')
    maximum=0.; checks=0
    def near(a,b,tol=1e-12):
        nonlocal maximum,checks
        a=np.asarray(a,float);b=np.asarray(b,float)
        exigir(a.shape==b.shape and np.isfinite(a).all() and np.isfinite(b).all(),'Forma/finito auditor')
        delta=float(np.max(np.abs(a-b))) if a.size else 0.;maximum=max(maximum,delta);checks+=1
        exigir(delta<=tol, f'Auditor diferencia {delta} > {tol}')
    if cols:
        mu,sd,centers,D=preparar_independiente(X,cols)
        near(state['media'],mu,1e-10);near(state['escala'],sd,1e-10)
        for g in centers:near(state['centros'][g],centers[g],1e-12)
        # Auditor usa matriz guardada para el certificado de sus coeficientes;
        # la preparación independiente anterior verifica que esa matriz es correcta.
        Z=(X[cols].to_numpy(float)-state['media'])/state['escala']
        D=Z-np.array([state['centros'][g] for g in groups])
        beta=np.asarray(state['beta'])
        if refit:
            bi,obj,dual=primal_independiente(D,y,groups,state['alpha'])
            near(beta,bi,1e-6)
            near(state['solver']['objetivo'],obj,1e-7)
            near(state['solver']['objetivo'],dual,1e-7)
        for g in set(groups):near(D[groups==g].mean(axis=0),np.zeros(len(cols)),1e-12)
    else:D=np.empty((len(X),0));beta=np.array([])
    for g in sorted(set(groups)):
        near(state['interceptos'][g],np.median(y[groups==g]-D[groups==g]@beta),1e-12)
        if cols:near(float(np.mean(D[groups==g]@beta)),0.,1e-12)
    for g in sorted(set(X.cultivo_origen)):
        near(state['mediana_grupo'][g],np.median(y[X.cultivo_origen.to_numpy()==g]))
    near(state['mediana_global'],np.median(y))
    exigir([r['id_parcela'] for r in consulta]==list(q.index),'Orden consulta distinto')
    for row,(_,qr) in zip(consulta,q.iterrows()):
        g=qr.municipio;correction=0.
        if g in state['interceptos']:
            base=state['interceptos'][g];source='municipio'
            if cols:
                zz=[(float(qr[c])-state['media'][j])/state['escala'][j]-state['centros'][g][j] for j,c in enumerate(cols)]
                correction=math.fsum(a*b for a,b in zip(zz,beta))
        elif qr.cultivo_origen in state['mediana_grupo']:
            base=state['mediana_grupo'][qr.cultivo_origen];source='grupo'
        else:base=state['mediana_global'];source='global'
        exigir(row['fuente']==source,'Fuente distinta')
        near(row['correccion_satelital'],correction);near(row['nivel_municipal_o_respaldo'],base)
        near(row['prediccion'],base+correction)
    return dict(comprobaciones=checks,max_diferencia=maximum)


def jsonl(path):
    if path.exists():return [json.loads(s) for s in path.read_text().splitlines()]
    with gzip.open(str(path)+'.gz','rt') as f:return [json.loads(s) for s in f]


def auditar(root,out,refit=True):
    root=Path(root);out=Path(out);contract=json.loads((root/'registro/t15_cuantilica_contrato_v1.json').read_text())
    manifest=json.loads((out/'manifest.json').read_text())
    exigir(manifest['contrato_sha256']==sha(root/'registro/t15_cuantilica_contrato_v1.json'),'Contrato no coincide')
    for p,h in contract['fuentes_sha256'].items():exigir(sha(root/p)==h,'Fuente alterada: '+p)
    for p,h in manifest['codigo_sha256'].items():exigir(sha(root/p)==h,'Código alterado: '+p)
    for p,h in manifest['archivos_sha256'].items():
        file=out/p
        raw=file.read_bytes() if file.exists() else gzip.decompress(Path(str(file)+'.gz').read_bytes())
        exigir(hashlib.sha256(raw).hexdigest()==h,'Artefacto alterado: '+p)
    _,e=cargar(root);traces=jsonl(out/'trazas_ajustes.jsonl');sels=jsonl(out/'selecciones.jsonl')
    count=0;maximum=0.;expected_oof={}; n_q=0;selected_names=[]
    options=[dict(nombre='referencia_sola',columnas=[],alpha=None,ventana='estatica')]+[
        dict(nombre=f'{w}__alpha_{a:g}',columnas=cols,alpha=a,ventana=w)
        for w,cols in contract['variables_por_ventana'].items() for a in contract['alpha']]
    expected_options={o['nombre']:o for o in options};seen_contexts=set()
    for sel in sels:
        s,r,f=sel['escenario'],sel['repeticion'],sel['particion'];X,y,q=preparar_contexto(e,s,r,f)
        exigir((s,r,f) not in seen_contexts,'Contexto duplicado');seen_contexts.add((s,r,f))
        exigir(len(sel['puntuaciones'])==9 and {o['nombre'] for o in sel['puntuaciones']}==set(expected_options),'Menú alterado')
        internal=divisiones_internas(X,s); ts=[t for t in traces if (t['escenario'],t['repeticion'],t['particion'])==(s,r,f)]
        exigir(len(ts)==37,'Se requieren 36 internos y un externo')
        totals={o['nombre']:[] for o in sel['puntuaciones']}
        seen=set();ext=None
        for t in ts:
            exigir(t['estado']=='correcto','Ajuste no completado')
            exigir(t['opcion']==expected_options[t['opcion']['nombre']],'Opción fuera de contrato')
            exigir(t['estado_modelo']['columnas']==t['opcion']['columnas'] and t['estado_modelo']['alpha']==t['opcion']['alpha'],'Estado de otra opción')
            if t['etapa']=='interna':
                j=t['division_interna'];sp=internal[j];a=X.loc[list(sp.entrenamiento)];b=X.loc[list(sp.validacion)]
                exigir(t['ids_elegibles']==[pid for pid,yes in zip(b.index,sp.elegibles) if yes],'Máscara distinta')
                key=(t['opcion']['nombre'],j);exigir(key not in seen,'Ajuste duplicado');seen.add(key)
                if s=='B':exigir(not set(a.celda_chirps)&set(b.celda_chirps),'Fuga espacial interna')
            else:a=X;b=q;ext=t
            exigir(t['ids_validacion']==list(b.index),'IDs consulta alterados')
            exigir(not(set(a.index)|set(b.index))&e['reservados'],'Reservadas usadas')
            exigir(not set(a.index)&set(b.index),'Fuga por ID')
            if s=='B':exigir(not set(X.celda_chirps)&set(q.celda_chirps),'Fuga espacial externa')
            result=auditar_estado(t['estado_modelo'],a,y.loc[a.index],b,t['consulta'],refit=refit)
            count+=result['comprobaciones'];maximum=max(maximum,result['max_diferencia'])
            n_q+=int(bool(t['estado_modelo']['columnas']))
            if t['etapa']=='interna':
                errors=[abs(v['prediccion']-float(y.loc[v['id_parcela']])) for v in t['consulta'] if v['id_parcela'] in t['ids_elegibles']]
                exigir(abs(float(np.mean(errors))-t['MAE'])<=1e-12,'MAE interna incorrecta')
                totals[t['opcion']['nombre']].extend(errors)
        for score in sel['puntuaciones']:
            exigir(abs(np.mean(totals[score['nombre']])-score['MAE'])<=1e-12,'Selección usa otro error')
        key=lambda o:(round(o['MAE'],6),0 if o['nombre']=='referencia_sola' else 1,-(o['alpha'] or 0.),0 if o['ventana']=='jun_oct' else 1,o['nombre'])
        win=min(sel['puntuaciones'],key=key)['nombre'];selected_names.append(win)
        exigir(sel['elegida']['nombre']==win and ext['opcion']==sel['elegida'],'Selección incorrecta')
        for row in ext['consulta']:expected_oof[s,r,row['id_parcela']]=row['prediccion']
    partial=manifest['modo']=='prueba'
    rows=leer_csv(out/('oof_parcial_prueba.csv' if partial else 'predicciones_oof.csv'))[1]
    new=[v for v in rows if v['candidato']==contract['candidato']]
    exigir(len(new)==len(expected_oof),'OOF incompletas')
    for row in new:
        key=(row['escenario'],int(row['repeticion']),row['ID_POLIGONO']);ctx=e['contextos'][key]
        exigir(abs(float(row['prediccion'])-expected_oof[key])<=1e-12,'OOF distinta del estado')
        exigir(float(row['real'])==ctx['real'] and int(row['particion'])==ctx['particion'] and row['fuente']==ctx['fuente'],'OOF identidad incorrecta')
    if not partial:
        exigir(len(traces)==1850 and len(sels)==50 and len(rows)==5520,'Presupuesto completo distinto')
        validar_oof(rows,e['contextos']);auditar_reportes(rows,e['contextos'],out,contract)
        old=leer_csv(root/'registro/t15_resultados/predicciones_oof.csv')[1]
        old=[v for v in old if v['candidato'] in ['media_mun__resp_grupo','comun_centrado_loo_v3_S']]
        old+=leer_csv(root/'registro/t03/predicciones_oof_referencias_mediana_mun__resp_grupo.csv')[1]
        key=lambda v:(v['candidato'],v['escenario'],int(v['repeticion']),v['ID_POLIGONO'])
        historical={key(v):v for v in old};reused=[v for v in rows if v['candidato']!=contract['candidato']]
        exigir(len(reused)==4140,'Comparadores incompletos')
        for row in reused:exigir(row==historical[key(row)],'Comparador histórico modificado o reetiquetado')
    for t in new:exigir(t['version']==contract['version'],'Versión nueva incorrecta')
    return dict(resultado='aprobado',ajustes=len(traces),ajustes_cuantilicos=n_q,
                contextos=len(sels),OOF_nuevas=len(new),comprobaciones=count,max_diferencia=maximum,
                recalculo_primal_dual_independiente=refit,selecciones=selected_names)


def auditar_reportes(rows,contexts,out,contract):
    # Fórmulas escalares/agrupación y bootstrap propios; no importa productor de informes.
    summary=leer_csv(out/'metricas_resumen.csv')[1]
    exigir(len(summary)==16 and len({(r['candidato'],r['escenario'],r['subconjunto']) for r in summary})==16,'Métricas incompletas')
    for r in summary:
        group=[v for v in rows if v['candidato']==r['candidato'] and v['escenario']==r['escenario'] and
               (r['subconjunto']=='todas' or v['fuente']=='municipio')]
        ids=sorted({v['ID_POLIGONO'] for v in group})
        ae=[math.fsum(abs(float(v['prediccion'])-float(v['real'])) for v in group if v['ID_POLIGONO']==i)/sum(v['ID_POLIGONO']==i for v in group) for i in ids]
        rm=[];rs=[]
        for rep in range(1,6):
            g=[v for v in group if int(v['repeticion'])==rep];ys=[float(v['real']) for v in g];n=len(g)
            sse=math.fsum((float(v['prediccion'])-float(v['real']))**2 for v in g)
            rm.append(math.sqrt(sse/n));mean=math.fsum(ys)/n;rs.append(1-sse/math.fsum((y-mean)**2 for y in ys))
        for k,v in [('MAE_por_parcela',math.fsum(ae)/len(ae)),('RMSE_media_repeticiones',math.fsum(rm)/5),('R2_media_repeticiones',math.fsum(rs)/5)]:
            exigir(abs(float(r[k])-v)<=1e-12,'Métrica distinta: '+k)
    contrasts=json.loads((out/'contrastes.json').read_text())
    exigir(len(contrasts)==16 and {(c['candidato'],c['frente_a'],c['escenario'],c['subconjunto']) for c in contrasts}=={
        (a,b,s,subset) for a,b in contract['contrastes'] for s in ['A','B'] for subset in ['todas','sin_respaldo']},'Contrastes incompletos')
    for c in contrasts:
        esc,subset=c['escenario'],c['subconjunto'];pair={}
        for name in [c['candidato'],c['frente_a']]:
            pair[name]={(v['ID_POLIGONO'],int(v['repeticion'])):float(v['prediccion']) for v in rows if v['candidato']==name and v['escenario']==esc and (subset=='todas' or v['fuente']=='municipio')}
        pp={};reps={}
        for (pid,rep),p in pair[c['candidato']].items():
            y=contexts[esc,rep,pid]['real'];b=pair[c['frente_a']][pid,rep]
            vals=[abs(p-y),abs(b-y),(p-y)**2,(b-y)**2]
            pp.setdefault(pid,[]).append(vals);reps.setdefault(rep,[]).append(vals)
        per={i:np.mean(v,axis=0) for i,v in pp.items()};cells={}
        for pid,v in per.items():cells.setdefault(contexts[esc,1,pid]['celda'],[]).append(v)
        cellnames=sorted(cells);sizes=np.array([len(cells[i]) for i in cellnames]);sums=np.array([np.sum(cells[i],axis=0) for i in cellnames])
        ix=np.random.RandomState(20261006).randint(len(cells),size=(5000,len(cells)))
        draw=sums[ix].sum(axis=1)/sizes[ix].sum(axis=1)[:,None];lo,hi=np.percentile(draw[:,0]-draw[:,1],[2.5,97.5])
        dmae=float(np.mean([v[0]-v[1] for v in per.values()]));dr=float(np.mean([np.sqrt(np.mean(v,axis=0)[2])-np.sqrt(np.mean(v,axis=0)[3]) for v in reps.values()]))
        improves=sum(np.mean(v,axis=0)[0]<np.mean(v,axis=0)[1] for v in reps.values())
        for a,b in [(dmae,c['dMAE']),(dr,c['dRMSE']),(lo,c['IC95_celdas_MAE'][0]),(hi,c['IC95_celdas_MAE'][1])]:exigir(abs(a-b)<=1e-12,'Contraste incorrecto')
        rule=bool(dmae<=-.01 and hi<0 and improves>=4 and dr<=.01)
        exigir(rule==c['cumple_regla_T03'],'Regla T03 incorrecta')
        eligible=c['candidato']==contract['candidato'] and c['frente_a']=='media_mun__resp_grupo' and esc=='A' and subset=='sin_respaldo' and rule
        exigir(c['elegible_para_promocion_principal']==eligible,'Promoción de contraste no registrado')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--raiz',type=Path,required=True);p.add_argument('--entrada',type=Path,required=True);p.add_argument('--salida',type=Path,required=True)
    args=p.parse_args();exigir(not args.salida.exists(),'No sobrescribir auditoría')
    result=auditar(args.raiz,args.entrada);args.salida.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False))
