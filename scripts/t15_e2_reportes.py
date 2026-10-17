"""Reportes E2: conserva T03 y añade la guardia familiar registrada antes de OOF."""
from collections import defaultdict
import json
from pathlib import Path
import numpy as np
from scripts import t15_ejecutor_reportes as comun
from scripts.evaluacion_comun_contrato import exigir

REF='media_mun__resp_grupo'
NOMBRES={k:'comun_centrado_loo_v3_'+k for k in ['S','E1','E2','E12','E2Q']}
NOMBRES['referencia']=REF


def contrato_reportes(registro):
    procs=[{'candidato':NOMBRES[k]} for k in ['S','E1','E2','E12','E2Q']]
    pairs=[dict(p,candidato=NOMBRES[p['candidato']],frente_a=NOMBRES[p['frente_a']])
           for p in registro['contrastes']]
    return dict(metodo=registro['metodo'],principal=dict(procedimientos=procs,contrastes_planificados=pairs))


def intervalo_familiar(rows,contexts,candidate,base,esc,subset):
    """Mismos 5000 índices espaciales de T03; percentiles extra 1.25/98.75."""
    by={(r['candidato'],r['escenario'],int(r['repeticion']),r['ID_POLIGONO']):r for r in rows}
    per_id=defaultdict(list)
    for k,c in sorted(contexts.items()):
        if k[0]!=esc or (subset=='sin_respaldo' and c['fuente']!='municipio'):continue
        a,b=by[candidate,*k],by[base,*k]
        per_id[k[2]].append(abs(float(a['prediccion'])-c['real'])-abs(float(b['prediccion'])-c['real']))
    cells=defaultdict(list)
    for pid,values in per_id.items():cells[contexts[esc,1,pid]['celda']].append(float(np.mean(values)))
    keys=sorted(cells);exigir(bool(keys),'Intervalo familiar sin pares')
    sums=np.asarray([np.sum(cells[k]) for k in keys]);sizes=np.asarray([len(cells[k]) for k in keys])
    ix=np.random.RandomState(20261006).randint(len(keys),size=(5000,len(keys)))
    delta=sums[ix].sum(1)/sizes[ix].sum(1)
    return np.percentile(delta,[1.25,98.75]).tolist()


def aplicar_guardia(contrastes,rows,contexts):
    out=[]
    for r in contrastes:
        ic=intervalo_familiar(rows,contexts,r['candidato'],r['frente_a'],r['escenario'],r['subconjunto'])
        ic95=json.loads(r['IC95_celdas_MAE']) if isinstance(r['IC95_celdas_MAE'],str) else r['IC95_celdas_MAE']
        exigir(ic[0]<=ic95[0]+1e-12 and ic[1]>=ic95[1]-1e-12,'IC97.5 no contiene IC95')
        t03=r['cumple_regla_T03'] in [True,'True']
        main=r['escenario']=='A' and r['subconjunto']=='sin_respaldo'
        promotable=r['tipo_contraste']=='promocion' and r['candidato'] in [NOMBRES['E2'],NOMBRES['E12']] and r['frente_a']==REF
        out.append({**r,'IC97_5_celdas_MAE_familia':ic,'cumple_guardia_familia':bool(ic[1]<0),
                    'elegible_E2_con_guardia':bool(main and promotable and t03 and ic[1]<0),
                    'E2Q_solo_diagnostico':r['candidato']==NOMBRES['E2Q']})
    return out


def producir(rows,contexts,registro,calidad,tabla,destino):
    destino=Path(destino)
    counts=comun.producir(rows,contexts,contrato_reportes(registro),calidad,tabla,destino)
    exigir(counts['metricas_resumen']==24 and counts['contrastes']==28,'Reportes E2 incompletos')
    from scripts.evaluacion_comun_contrato import leer_csv
    contrasts=aplicar_guardia(leer_csv(destino/'contrastes.csv')[1],rows,contexts)
    comun.csv_guardar(destino/'contrastes_E2_con_guardia.csv',contrasts)
    eligible=[r['candidato'] for r in contrasts if r['elegible_E2_con_guardia']]
    metrics=leer_csv(destino/'metricas_resumen.csv')[1]
    main={r['candidato']:r for r in metrics if r['escenario']=='A' and r['subconjunto']=='sin_respaldo'}
    chosen=min(eligible,key=lambda c:(round(float(main[c]['MAE_por_parcela']),6),0 if c==NOMBRES['E2'] else 1)) if eligible else REF
    decision=dict(schema='E2_decision_registrada_v1',alternativas_elegibles=eligible,
        procedimiento_recomendado_por_regla=chosen,ganador_T16_congelado=False,predicciones_finales59=0,
        T03_intacto=True,E2Q_promovible=False,guardia_familiar='IC97.5_adicional_superior_negativo',
        interpretacion='Evidencia retrospectiva de una campaña; no es validación externa ciega ni garantía futura.')
    (destino/'decision_E2.json').write_text(json.dumps(decision,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    report=destino/'informe.md'
    with report.open('a') as f:
        f.write('\n## Extensión INEGI E2\n\nT03 se conserva y se exige además el IC97.5 registrado para los dos candidatos E2/E12. '
                'E2Q sólo diagnostica disponibilidad. Decisión completa en `contrastes_E2_con_guardia.csv`.\n\n'
                'Procedimiento recomendado por la regla: `'+chosen+'`. T16 sigue sin congelar.\n'
                'Fuentes y arquitectura están fijadas en el manifiesto. Se reutilizan 4140 OOF previas sin alterarlas.\n')
    return {**counts,'contrastes_guardia':len(contrasts),'decision':decision}
