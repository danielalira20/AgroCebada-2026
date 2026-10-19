"""Estadísticos comunes desde OOF validados; no reentrena ni elige ganador T16."""
import numpy as np
from scripts.evaluacion_comun_contrato import validar_oof,exigir


def metricas(y,p):
    y=np.asarray(y,float);p=np.asarray(p,float)
    exigir(len(y)>0 and y.shape==p.shape and np.isfinite(y).all() and np.isfinite(p).all(),'Métricas requieren pares finitos')
    e=p-y;constant=np.all(y==y[0]);den=np.sum((y-y.mean())**2)
    return {'n':len(y),'MAE':float(np.abs(e).mean()),'RMSE':float(np.sqrt(np.mean(e**2))),'sesgo':float(e.mean()),'R2':None if constant else float(1-np.sum(e**2)/den),'R2_estado':'objetivo_constante' if constant else 'definido'}


def resumen(rows,contexts):
    validar_oof(rows,contexts);out=[]
    for cand in sorted({r['candidato'] for r in rows}):
        for esc in ['A','B']:
            for subset in ['todas','sin_respaldo']:
                groups=[]
                for rep in range(1,6):
                    g=[r for r in rows if r['candidato']==cand and r['escenario']==esc and int(r['repeticion'])==rep and (subset=='todas' or r['fuente']=='municipio')]
                    groups.append(metricas([float(r['real']) for r in g],[float(r['prediccion']) for r in g]))
                out.append({'candidato':cand,'escenario':esc,'subconjunto':subset,'n_media':float(np.mean([m['n'] for m in groups])),'metricas_por_repeticion':groups,**{k:float(np.mean([m[k] for m in groups])) for k in ['MAE','RMSE','sesgo']},'R2':None if any(m['R2'] is None for m in groups) else float(np.mean([m['R2'] for m in groups]))})
    return out


def comparar(rows,contexts,candidato,base='media_mun__resp_grupo',escenario='A',subconjunto='sin_respaldo'):
    validar_oof(rows,contexts);exigir(escenario in ['A','B'] and subconjunto in ['todas','sin_respaldo'],'Comparación fuera de protocolo')
    by={r['candidato']:{} for r in rows}
    for r in rows:by[r['candidato']][r['escenario'],int(r['repeticion']),r['ID_POLIGONO']]=r
    exigir(candidato in by and base in by and candidato!=base,'Requiere candidato y base distintos')
    per_id={};per_rep={}
    for k,context in sorted(contexts.items()):
        if k[0]!=escenario or (subconjunto=='sin_respaldo' and context['fuente']!='municipio'):continue
        a,b=by[candidato][k],by[base][k];y=context['real'];ea=float(a['prediccion'])-y;eb=float(b['prediccion'])-y
        values=np.array([abs(ea),abs(eb),ea**2,eb**2])
        per_id.setdefault(k[2],[]).append(values);per_rep.setdefault(k[1],[]).append(values)
    pp={k:np.mean(v,axis=0) for k,v in per_id.items()};rep={k:np.mean(v,axis=0) for k,v in per_rep.items()}
    exigir(set(rep)==set(range(1,6)),'Repeticiones elegibles incompletas')
    d_mae=float(np.mean([v[0]-v[1] for v in pp.values()]));dmae_rep=[v[0]-v[1] for v in rep.values()];drmse_rep=[np.sqrt(v[2])-np.sqrt(v[3]) for v in rep.values()];d_rmse=float(np.mean(drmse_rep))
    cells={}
    for pid,v in pp.items():
        cell=contexts[escenario,1,pid]['celda'];exigir(bool(cell),'Bootstrap requiere celda')
        cells.setdefault(cell,[]).append(v)
    blocks=sorted(cells);sums=np.array([np.sum(cells[k],axis=0) for k in blocks]);sizes=np.array([len(cells[k]) for k in blocks])
    idx=np.random.RandomState(20261006).randint(len(blocks),size=(5000,len(blocks)));n=sizes[idx].sum(axis=1);vals=sums[idx].sum(axis=1)/n[:,None]
    lo,hi=np.percentile(vals[:,0]-vals[:,1],[2.5,97.5]);rlo,rhi=np.percentile(np.sqrt(vals[:,2])-np.sqrt(vals[:,3]),[2.5,97.5])
    improves=int(sum(v<0 for v in dmae_rep));rule=d_mae<=-.01 and hi<0 and improves>=4 and d_rmse<=.01
    return {'candidato':candidato,'frente_a':base,'escenario':escenario,'subconjunto':subconjunto,'n_parcelas':len(pp),'n_predicciones':sum(len(v) for v in per_id.values()),'n_celdas':len(cells),'dMAE':d_mae,'dMAE_por_repeticion':[float(v) for v in dmae_rep],'diferencia_MAE_media_por_repeticion':float(np.mean(dmae_rep)),'dRMSE':d_rmse,'IC95_celdas_MAE':[float(lo),float(hi)],'IC95_celdas_RMSE':[float(rlo),float(rhi)],'repeticiones_mejoran_MAE':improves,'cumple_regla_T03':bool(rule),'elegible_para_promocion_principal':bool(escenario=='A' and subconjunto=='sin_respaldo' and rule),'interpretacion':'contraste del procedimiento declarado; no acredita otra campaña ni aprobación T16'}
