"""Complemento C: distingue ponderación por parcela, registro y repetición. Sin nuevos ajustes."""
import argparse
import collections
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import tempfile


def read(path):
    with Path(path).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def aggregate(records):
    if not records:raise ValueError('No calcular un grupo vacío como cero')
    seen=set();by_id=collections.defaultdict(list);by_rep=collections.defaultdict(list)
    for r in records:
        key=(r['id_parcela'],r['repeticion'])
        if key in seen:raise ValueError('Registro parcela/repetición duplicado en grupo')
        seen.add(key)
        error=float(r['error_historico'])
        if not math.isfinite(error):raise ValueError('Error histórico no finito')
        by_id[r['id_parcela']].append(error);by_rep[r['repeticion']].append(error)
    mean=lambda a:math.fsum(a)/len(a)
    all_errors=[e for values in by_id.values() for e in values]
    return dict(n_registros=len(records), n_parcelas=len(by_id),
        n_repeticiones_por_parcela_min=min(map(len,by_id.values())),
        n_repeticiones_por_parcela_max=max(map(len,by_id.values())),
        MAE_por_parcela_t_ha=mean([mean([abs(e) for e in values]) for values in by_id.values()]),
        RMSE_por_parcela_t_ha=math.sqrt(mean([mean([e*e for e in values]) for values in by_id.values()])),
        sesgo_por_parcela_t_ha=mean([mean(values) for values in by_id.values()]),
        MAE_por_registro_t_ha=mean([abs(e) for e in all_errors]),
        RMSE_por_registro_t_ha=math.sqrt(mean([e*e for e in all_errors])),
        MAE_media_repeticiones_t_ha=mean([mean([abs(e) for e in values]) for values in by_rep.values()]))


def run(compact,detail,destination):
    compact,detail,destination=map(Path,(compact,detail,destination))
    if destination.exists():raise ValueError('Destino existente')
    source=compact/'contextos_oof_138.csv';feature=detail/'entradas_oof_138.csv';groups=compact/'error_por_soporte.csv'
    manifest=json.loads((compact/'manifest.json').read_text())
    for n in [source.name,groups.name]:
        if sha(compact/n)!=manifest['archivos_sha256'][n]:raise ValueError('Fuente compacta alterada')
    geo=read(source);features=read(feature);definitions=read(groups)
    result=[];checks=0;maximum=0.
    for scenario in ['A','B']:
        for subset in ['todas','sin_respaldo']:
            rs=[r for r in geo if r['escenario']==scenario and (subset=='todas' or r['fuente_referencia']=='municipio')]
            result.append(dict(escenario=scenario,representacion='',subconjunto=subset,dimension='global',categoria='todas',**aggregate(rs)))
    for group in definitions:
        pool=features if group['representacion'] else geo
        cat={'True':'si','False':'no','no_definido':''}.get(group['categoria'],group['categoria'])
        rs=[r for r in pool if r['escenario']==group['escenario'] and r.get('representacion','')==group['representacion']
            and (group['subconjunto']=='todas' or r['fuente_referencia']=='municipio') and r[group['dimension']]==cat]
        metrics=aggregate(rs)
        if metrics['n_registros']!=int(group['n_registros_oof']) or metrics['n_parcelas']!=int(group['n_parcelas']):
            raise ValueError('Desglose no conserva la población histórica')
        for a,b in [('MAE_por_registro_t_ha','MAE_historico'),('RMSE_por_registro_t_ha','RMSE_historico')]:
            delta=abs(metrics[a]-float(group[b]));checks+=1;maximum=max(maximum,delta)
            if delta>1e-12:raise ValueError('No reproduce el agregado por registro original')
        result.append({k:group[k] for k in ['escenario','representacion','subconjunto','dimension','categoria']}|metrics)
    destination.parent.mkdir(parents=True,exist_ok=True)
    temp=Path(tempfile.mkdtemp(prefix=destination.name+'.',dir=destination.parent))
    p=temp/'error_por_soporte_unidad_parcela.csv'
    with p.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(result[0]),lineterminator='\n');w.writeheader()
        for r in result:w.writerow({k:format(v,'.15g') if isinstance(v,float) else v for k,v in r.items()})
    evidence=dict(version='C-complemento-unidad-parcela-v1',fuentes_sha256={
        'contextos_oof_138.csv':sha(source),'entradas_oof_138.csv_detalle_local':sha(feature),
        'error_por_soporte.csv':sha(groups),'manifest_C':sha(compact/'manifest.json')},
        archivos_sha256={p.name:sha(p)},codigo_sha256=sha(Path(__file__)),
        comparaciones_agregado_por_registro=checks,max_delta=maximum,
        unidades=dict(parcela='Media entre IDs de pérdida media por ID en sus repeticiones elegibles; RMSE usa errores cuadrados, no predicciones promediadas.',
            registro='Cada fila OOF recibe igual peso; difiere si varían las repeticiones elegibles por ID.',
            repeticion='Media de los MAE de cada repetición; no equivale necesariamente a los otros dos.'),
        advertencias=['Un ID puede pertenecer a categorías distintas entre repeticiones: grupos no aditivos.',
                      'Desglose exploratorio de referencia T08 histórica, no nueva mejora ni incertidumbre individual.'],
        modelos_ajustados=0)
    (temp/'manifest.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2)+'\n')
    os.replace(temp,destination)
    return {'grupos':len(result),'comparaciones':checks,'max_delta':maximum,
        'globales':[r for r in result if r['dimension']=='global']}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--compactos',type=Path,required=True);p.add_argument('--detalle',type=Path,required=True)
    p.add_argument('--salida',type=Path,required=True)
    a=p.parse_args();print(json.dumps(run(a.compactos,a.detalle,a.salida),ensure_ascii=False,indent=2))


if __name__=='__main__':main()
