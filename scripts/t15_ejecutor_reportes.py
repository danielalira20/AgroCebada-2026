"""Reportes T15 desde OOF completas verificadas; no elige un ganador T16."""
from collections import defaultdict
import csv
import json
from pathlib import Path

import numpy as np

from scripts import evaluacion_comun_contrato as comun
from scripts import evaluacion_comun_reportes as estadistica


def csv_guardar(path, rows, columnas=None):
    rows = list(rows)
    columnas = columnas or list(rows[0])
    with Path(path).open('x', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=columnas, lineterminator='\n')
        w.writeheader()
        for row in rows:
            w.writerow({k: json.dumps(v, ensure_ascii=False, allow_nan=False) if isinstance(v, (dict,list,tuple))
                        else v for k,v in row.items()})


def resumen_grupo(rows):
    """Métricas por repetición y por ID, sin promediar predicciones antes del error."""
    if not rows:
        return dict(n_parcelas=0, n_predicciones=0, n_repeticiones=0, MAE_por_parcela=None,
                    RMSE_igual_peso_parcela=None, sesgo_por_parcela=None, R2_igual_peso_parcela=None,
                    R2_estado='sin_casos', MAE_media_repeticiones=None, RMSE_media_repeticiones=None,
                    R2_media_repeticiones=None, p90_MAE_parcela=None, n_parcelas_MAE_mayor_1=None)
    ids, reps = defaultdict(list), defaultdict(list)
    for row in rows:
        y,p=float(row['real']),float(row['prediccion'])
        comun.exigir(np.isfinite([y,p]).all(), 'Métrica con valor no finito')
        ids[row['ID_POLIGONO']].append((y,p))
        reps[int(row['repeticion'])].append((y,p))
    valores=[]
    for pid, pares in sorted(ids.items()):
        a=np.asarray(pares,float);e=a[:,1]-a[:,0]
        comun.exigir(np.all(a[:,0]==a[0,0]), 'Etiqueta cambia entre repeticiones')
        valores.append((a[0,0],np.mean(abs(e)),np.mean(e**2),np.mean(e)))
    a=np.asarray(valores);mse=float(a[:,2].mean());den=float(np.mean((a[:,0]-a[:,0].mean())**2))
    constante=bool(np.all(a[:,0]==a[0,0]) or den==0)
    ms=[estadistica.metricas(*np.asarray(pares).T) for _,pares in sorted(reps.items())]
    return dict(n_parcelas=len(ids), n_predicciones=len(rows), n_repeticiones=len(reps),
                MAE_por_parcela=float(a[:,1].mean()), RMSE_igual_peso_parcela=float(np.sqrt(mse)),
                sesgo_por_parcela=float(a[:,3].mean()),
                R2_igual_peso_parcela=None if constante else float(1-mse/den),
                R2_estado='objetivo_constante' if constante else 'definido',
                MAE_media_repeticiones=float(np.mean([m['MAE'] for m in ms])),
                RMSE_media_repeticiones=float(np.mean([m['RMSE'] for m in ms])),
                R2_media_repeticiones=None if any(m['R2'] is None for m in ms) else float(np.mean([m['R2'] for m in ms])),
                p90_MAE_parcela=float(np.percentile(a[:,1],90)),
                n_parcelas_MAE_mayor_1=int(np.sum(a[:,1]>1)))


def intervalo_parcelas(rows, contexts, candidato, base, escenario, subconjunto):
    """Sensibilidad con parcelas independientes; no participa en promoción."""
    idx={(r['candidato'],r['escenario'],int(r['repeticion']),r['ID_POLIGONO']):r for r in rows}
    diferencias=defaultdict(list)
    for k,c in sorted(contexts.items()):
        if k[0]!=escenario or (subconjunto=='sin_respaldo' and c['fuente']!='municipio'):continue
        y=c['real']
        diferencias[k[2]].append(abs(float(idx[(candidato,*k)]['prediccion'])-y)-
                                 abs(float(idx[(base,*k)]['prediccion'])-y))
    values=np.array([np.mean(v) for _,v in sorted(diferencias.items())])
    comun.exigir(len(values)>0, 'Intervalo sin pares')
    rng=np.random.RandomState(20261006)
    # Cota pequeña de memoria; conserva la misma secuencia de 5000 remuestras.
    boot=[]
    for start in range(0,5000,100):
        ix=rng.randint(len(values),size=(min(100,5000-start),len(values)))
        boot.extend(values[ix].mean(axis=1))
    return np.percentile(boot,[2.5,97.5]).tolist()


def producir(rows, contexts, contrato, calidad, tabla, destino):
    """Rechaza una entrega incompleta antes de producir tablas de evaluación."""
    integridad=comun.validar_oof(rows,contexts)
    nombres={p['candidato'] for p in contrato['principal']['procedimientos']}|{'media_mun__resp_grupo'}
    comun.exigir(set(integridad['candidatos'])==nombres, 'Faltan/sobran candidatos del contrato')
    comun.exigir(all(r['version']==contrato['metodo']['version'] for r in rows), 'OOF mezcla versiones')
    comun.exigir(set(calidad)==set(tabla), 'Calidad no cubre el catálogo')
    conocidos={k[2] for k in contexts}
    alertas={i for i in conocidos if calidad[i]['alerta_contorno_t03_bis']=='si'}
    comun.exigir(len(alertas)==24, 'Sensibilidad sin24 no corresponde al catálogo fijado')
    destino=Path(destino)
    por_rep=[];resumen=[];desgloses=[]
    for candidato in sorted(nombres):
        for esc in ['A','B']:
            for subset in ['todas','sin_respaldo']:
                picked=[r for r in rows if r['candidato']==candidato and r['escenario']==esc and
                        (subset=='todas' or r['fuente']=='municipio')]
                identidad=dict(candidato=candidato,escenario=esc,subconjunto=subset)
                resumen.append({**identidad,**resumen_grupo(picked)})
                for rep in range(1,6):
                    g=[r for r in picked if int(r['repeticion'])==rep]
                    m=estadistica.metricas([float(r['real']) for r in g],[float(r['prediccion']) for r in g])
                    por_rep.append({**identidad,'repeticion':rep,**m})
                grupos={
                    'municipio':lambda pid:tabla[pid]['municipio'],
                    'grupo_registro':lambda pid:tabla[pid]['cultivo_origen'],
                    'contorno_categoria':lambda pid:calidad[pid]['contorno_categoria'],
                    'contorno_angosta_o_muy_pequena':lambda pid:calidad[pid]['contorno_angosta_o_muy_pequena'],
                    'escalon_etiqueta_municipio':lambda pid:calidad[pid]['escalon_etiqueta_municipio'] or 'no_documentado',
                    'vecina_etiquetada_menos_20m':lambda pid:calidad[pid]['vecina_etiquetada_menos_20m']}
                for nombre,fun in grupos.items():
                    for valor in sorted({fun(r['ID_POLIGONO']) for r in picked}):
                        g=[r for r in picked if fun(r['ID_POLIGONO'])==valor]
                        desgloses.append({**identidad,'desglose':nombre,'valor':valor,**resumen_grupo(g)})
                g=[r for r in picked if r['ID_POLIGONO'] not in alertas]
                desgloses.append({**identidad,'desglose':'sensibilidad_sin24','valor':'sin24',**resumen_grupo(g)})
    contrastes=[]
    for par in contrato['principal']['contrastes_planificados']:
        for esc in ['A','B']:
            for subset in ['todas','sin_respaldo']:
                r=estadistica.comparar(rows,contexts,par['candidato'],par['frente_a'],esc,subset)
                r['tipo_contraste']=par['tipo']
                # Un par descriptivo no promociona aunque satisfaga umbrales numéricos.
                r['elegible_para_promocion_principal']=bool(r['elegible_para_promocion_principal'] and par['tipo']=='promocion')
                r['IC95_parcelas_MAE_descriptivo']=intervalo_parcelas(rows,contexts,par['candidato'],par['frente_a'],esc,subset)
                r['mejora_simultanea_puntual']=bool(r['dMAE']<0 and r['dRMSE']<=0)
                contrastes.append(r)
    csv_guardar(destino/'metricas_resumen.csv',resumen)
    csv_guardar(destino/'metricas_por_repeticion.csv',por_rep)
    csv_guardar(destino/'desgloses_calidad_y_sin24.csv',desgloses)
    csv_guardar(destino/'contrastes.csv',contrastes)
    texto=['# T15: evaluación del procedimiento común','',
           'Estimación retrospectiva de parcelas 2025. Resultados sobre etiquetas conocidas; no acredita otra campaña ni congela T16.',
           '', '| Candidato | MAE por parcela | RMSE medio por repetición | R² medio por repetición |',
           '|---|---:|---:|---:|']
    for r in resumen:
        if r['escenario']=='A' and r['subconjunto']=='sin_respaldo':
            r2='indefinido' if r['R2_media_repeticiones'] is None else f"{r['R2_media_repeticiones']:.6f}"
            texto.append(f"| {r['candidato']} | {r['MAE_por_parcela']:.6f} | {r['RMSE_media_repeticiones']:.6f} | {r2} |")
    texto+=['','Decisión: A/sin_respaldo según contrato, intervalos por celdas; B y sin24 son sensibilidad. '
             'Los contrastes descriptivos no deciden promoción. Consultar denominadores y poblaciones en los CSV.',
             '', 'MAE y RMSE se expresan en t/ha. R² de objetivo constante queda vacío. '
             'Las repeticiones reutilizan parcelas. Las métricas por ID promedian errores, nunca predicciones antes de medir error. '
             'En B, el número de repeticiones elegibles por parcela puede variar; no confundir sus ponderaciones.',
             '', 'La selección humana conoce resultados anteriores y no constituye una validación externa ciega. '
             'No se atribuye aprobación a los revisores ni se generan predicciones de las 59.']
    (destino/'informe.md').write_text('\n'.join(texto)+'\n',encoding='utf-8')
    return dict(integridad=integridad,metricas_resumen=len(resumen),metricas_por_repeticion=len(por_rep),
                contrastes=len(contrastes),desgloses=len(desgloses),ganador_T16_congelado=False)
