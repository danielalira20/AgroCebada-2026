"""Desglose posterior descriptivo. No ajusta modelos ni altera la selección."""
import csv
import gzip
import json
import math
import sys
from pathlib import Path
import numpy as np


def dump(path,rows):
    with path.open('x',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)


def run(root,out,dest):
    dest.mkdir()
    read=lambda p:list(csv.DictReader(p.open(encoding='utf-8-sig')))
    data={r['id_parcela']:r for r in read(root/'registro/t07/tabla_comun.csv')}
    quality={r['id_parcela']:r for r in read(root/'registro/t07/calidad_parcelas.csv')}
    rows=read(out/'predicciones_oof.csv');idx={(v['candidato'],v['escenario'],int(v['repeticion']),v['ID_POLIGONO']):v for v in rows}
    path=out/'trazas_ajustes.jsonl'
    if path.exists():text=path.read_text()
    else:
        with gzip.open(str(path)+'.gz','rt') as f:text=f.read()
    traces=[json.loads(s) for s in text.splitlines()]
    profiles=[]
    for t in traces:
        if t['etapa']!='externa':continue
        s=t['estado_modelo'];ids=s['ids_entrenamiento'];beta=np.asarray(s['beta']);mu=np.asarray(s['media']);sd=np.asarray(s['escala'])
        med={g:np.median([float(data[i]['rendimiento_t_ha']) for i in ids if data[i]['municipio']==g]) for g in s['interceptos']}
        h3=[]
        for g in s['interceptos']:
            cor=[]
            for pid in ids:
                if data[pid]['municipio']!=g:continue
                z=(np.array([float(data[pid][c]) for c in s['columnas']])-mu)/sd if len(beta) else np.array([])
                cor.append(float((z-np.asarray(s['centros'][g]))@beta))
            h3.append(abs(math.fsum(cor)/len(cor)))
        diffs=[]
        for v in t['consulta']:
            old=idx['mediana_mun__resp_grupo',t['escenario'],t['repeticion'],v['id_parcela']]
            diffs.append(abs(v['prediccion']-float(old['prediccion'])))
            if v['fuente']!='municipio' and v['correccion_satelital']!=0.:raise ValueError('Corrección en respaldo')
        profiles.append(dict(escenario=t['escenario'],repeticion=t['repeticion'],particion=t['particion'],
            opcion=t['opcion']['nombre'],n_entrenamiento=len(ids),n_consulta=len(diffs),
            referencia_sola=not bool(beta.size),n_pendientes_no_cero=int(np.sum(np.abs(beta)>1e-9)),
            norma_L1_beta=float(np.abs(beta).sum()),max_media_correccion_train=max(h3),
            max_cambio_nivel_municipal=float(max(abs(s['interceptos'][g]-med[g]) for g in med)),
            cambio_medio_absoluto_vs_mediana=float(np.mean(diffs)),cambio_maximo_vs_mediana=max(diffs),
            objetivo=s['solver']['objetivo'],brecha_objetivo=None if s['solver']['primario'] is None else abs(s['solver']['objetivo']-s['solver']['primario'])))
    dump(dest/'perfiles_contextos.csv',profiles)
    per=[]
    for esc in ['A','B']:
        for pid in sorted({v['ID_POLIGONO'] for v in rows}):
            r=[v for v in rows if v['ID_POLIGONO']==pid and v['candidato']=='cuantilica_municipal_S_v1' and v['escenario']==esc and v['fuente']=='municipio']
            if not r:continue
            errors={}
            for name in ['cuantilica_municipal_S_v1','media_mun__resp_grupo','mediana_mun__resp_grupo','comun_centrado_loo_v3_S']:
                errors[name]=np.mean([abs(float(idx[name,esc,int(v['repeticion']),pid]['prediccion'])-float(v['real'])) for v in r])
            per.append(dict(escenario=esc,id_parcela=pid,n_repeticiones=len(r),municipio=data[pid]['municipio'],
                alerta_contorno=quality[pid]['alerta_contorno_t03_bis'],
                MAE_cuantilica=float(errors['cuantilica_municipal_S_v1']),MAE_media=float(errors['media_mun__resp_grupo']),
                MAE_mediana=float(errors['mediana_mun__resp_grupo']),MAE_S_Ridge=float(errors['comun_centrado_loo_v3_S']),
                dMAE_vs_media=float(errors['cuantilica_municipal_S_v1']-errors['media_mun__resp_grupo']),
                dMAE_vs_mediana=float(errors['cuantilica_municipal_S_v1']-errors['mediana_mun__resp_grupo'])))
    dump(dest/'comparacion_por_parcela.csv',per)
    detail={}
    for esc in ['A','B']:
        ps=[v for v in profiles if v['escenario']==esc];rs=[v for v in rows if v['candidato']=='cuantilica_municipal_S_v1' and v['escenario']==esc]
        es=[v for v in per if v['escenario']==esc]
        detail[esc]=dict(contextos=len(ps),referencia_sola=sum(v['referencia_sola'] for v in ps),
            contexto_beta_activo=sum(v['n_pendientes_no_cero']>0 for v in ps),
            max_H3_correccion=max(v['max_media_correccion_train'] for v in ps),
            n_parcelas_elegibles=len(es),n_OOF_elegibles=sum(v['n_repeticiones'] for v in es),
            min_prediccion=min(float(v['prediccion']) for v in rs),max_prediccion=max(float(v['prediccion']) for v in rs),
            n_predicciones_negativas=sum(float(v['prediccion'])<0 for v in rs),
            mejoran_vs_mediana=sum(v['dMAE_vs_mediana'] < -1e-12 for v in es),
            empeoran_vs_mediana=sum(v['dMAE_vs_mediana'] > 1e-12 for v in es),
            iguales_vs_mediana=sum(abs(v['dMAE_vs_mediana']) <= 1e-12 for v in es))
    (dest/'resumen_descriptivo.json').write_text(json.dumps(detail,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(detail,ensure_ascii=False,indent=2))


if __name__=='__main__':run(*map(Path,sys.argv[1:]))
