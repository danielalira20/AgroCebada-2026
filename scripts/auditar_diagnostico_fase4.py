"""Auditor aritmético independiente de fase4: Fraction, CSV y originales."""
import argparse
from collections import Counter, defaultdict
import csv
from fractions import Fraction as Q
import hashlib
import io
import json
from pathlib import Path
import statistics
import zipfile

ROOT=Path(__file__).resolve().parents[1]


def read(p):
    with Path(p).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))


def audit(output,ledger):
    output=Path(output);counts=0;maxdiff=0.
    design=json.loads((ROOT/'registro/diagnostico/fase4_diseno.json').read_text())
    for rel,h in design['fuentes'].items():
        if hashlib.sha256((ROOT/rel).read_bytes()).hexdigest()!=h:raise ValueError('Fuente cambió')
    manifest=json.loads((output/'manifest.json').read_text())
    for rel,h in manifest['archivos_sha256'].items():
        if hashlib.sha256((output/rel).read_bytes()).hexdigest()!=h:raise ValueError('Salida cambió')
    if hashlib.sha256(Path(ledger).read_bytes()).hexdigest()!=manifest['ledger_sha256']:raise ValueError('Ledger distinto')
    def equal(a,b):
        nonlocal counts,maxdiff
        counts+=1
        if a=='':
            if b is not None:raise ValueError('Vacío cambiado')
            return
        delta=float(abs(Q(a)-b));maxdiff=max(maxdiff,delta)
        if delta>1e-12:raise ValueError('Discrepancia '+str(delta))
    with zipfile.ZipFile(ROOT/'data/raw/DataSet.zip') as z:
        r=list(csv.DictReader(io.StringIO(z.read('DATASET_RETO_AGRO_2026/ID_area_rendimiento_70_30_Reto_AgroCebada.csv').decode('utf-8-sig'))))
    raw={r['ID_POLIGONO']:r for r in r};table={r['id_parcela']:r for r in read(ROOT/'registro/t07/tabla_comun.csv')};known={p for p,r in raw.items() if r['RENDIMIENTO_T_HA']}
    if len(raw)!=197 or len(known)!=138:raise ValueError('Universo distinto')
    ledger_counts=Counter()
    with Path(ledger).open(newline='') as f:
        for r in csv.DictReader(f):
            p=r['id_parcela']
            if p not in known:raise ValueError('OOF sin etiqueta')
            equal(r['real'],Q(raw[p]['RENDIMIENTO_T_HA']));ledger_counts[p]+=1
    for row in read(output/'conciliacion_etiquetas.csv'):
        pid=row['id_parcela'];r=raw[pid]
        if row['rendimiento_literal']!=r['RENDIMIENTO_T_HA'] or row['area_literal']!=r['AREA_HA']:raise ValueError('Texto original cambiado')
        equal(row['n_OOF_comprobados'],Q(ledger_counts[pid]))
    by=defaultdict(list)
    for p in known:by[table[p]['municipio']].append(p)
    for row in read(output/'etiquetas_contexto.csv'):
        pid=row['id_parcela'];other=[p for p in by[table[pid]['municipio']] if p!=pid]
        average=sum((Q(raw[p]['RENDIMIENTO_T_HA']) for p in other),Q(0))/len(other) if other else None
        equal(row['media_otras_municipio'],average)
        equal(row['desviacion_LOO'],Q(raw[pid]['RENDIMIENTO_T_HA'])-average if average is not None else None)
    for row in read(output/'sensibilidad_area_nominal.csv'):
        pid=row['id_parcela'];a=Q(raw[pid]['AREA_HA']);y=Q(raw[pid]['RENDIMIENTO_T_HA']);da=Q(row['delta_area_ha_hipotetica'])
        if da not in (Q('-0.005'),Q('0.005')) or row['nuevo_rendimiento_evaluado']!='False':raise ValueError('Escenario modificado')
        equal(row['magnitud_variacion_t_ha_hipotetica'],abs(y*da/(a+da)))
    def step(values):
        if len(values)<3:return ''
        return next((s for s in ('0.5','0.1','0.01') if all((v/Q(s)).denominator==1 for v in values)),'')
    for row in read(output/'granularidad_municipal.csv'):
        values=[Q(raw[p]['RENDIMIENTO_T_HA']) for p in by[row['municipio']]]
        counts+=1
        if row['paso_compatible_T02']!=step(values) or (row['etiqueta_constante']=='True')!=(len(set(values))==1):raise ValueError('Paso distinto')
    partitions=defaultdict(dict)
    for r in read(ROOT/'registro/diagnostico/fase0/mascaras_contextos.csv'):
        if r['escenario'] in ('A','B'):partitions[(r['escenario'],r['repeticion'])][r['id_parcela']]=r['particion']
    groups={}
    for row in read(output/'granularidad_entrenamiento.csv'):
        esc,rep,fold,m=(row[c] for c in ('escenario','repeticion','particion','municipio'))
        ids=sorted(p for p,f in partitions[(esc,rep)].items() if f!=fold and table[p]['municipio']==m)
        values=[Q(raw[p]['RENDIMIENTO_T_HA']) for p in ids]
        counts+=1
        if int(row['n_entreno_municipal'])!=len(ids) or row['paso_compatible_solo_entreno']!=step(values) or row['firma_IDs_entreno']!=hashlib.sha256('\n'.join(ids).encode()).hexdigest():raise ValueError('Entrenamiento/granularidad incorrectos')
        groups[(esc,rep,fold,m)]=step(values)
    qual={r['municipio']:r['paso_compatible_T02'] for r in read(output/'granularidad_municipal.csv')};errors=read(ROOT/'registro/diagnostico/fase1/errores_por_repeticion.csv');by_error=defaultdict(lambda:defaultdict(list))
    for r in errors:
        pid=r['id_parcela'];m=table[pid]['municipio'];err=abs(Q(r['prediccion'])-Q(raw[pid]['RENDIMIENTO_T_HA']))
        for pop in ('todas','sin_respaldo'):
            if pop=='sin_respaldo' and r['fuente_referencia']!='municipio':continue
            for basis,gr in [('catalogo_T02_solo_descriptivo',qual[m]),('entrenamiento_fold',groups[(r['escenario'],r['repeticion'],r['particion'],m)])]:
                by_error[(r['escenario'],pop,basis,gr or 'no_identificado')][pid].append(err)
    for row in read(output/'error_por_granularidad.csv'):
        k=tuple(row[c] for c in ('escenario','poblacion','base_granularidad','paso'));by_id=by_error[k];means=[sum(v)/len(v) for v in by_id.values()]
        equal(row['mae_por_ID'],sum(means)/len(means));equal(row['mediana_mae_ID'],statistics.median(means))
        if int(row['n_ID_grupo'])!=len(by_id) or row['MAE_reducido_por_incertidumbre']!='False':raise ValueError('Grupo inválido')
    for row in read(output/'pares_y_etiquetas.csv'):
        a,b=row['id_a'],row['id_b'];both=a in known and b in known
        expected='si' if both and Q(raw[a]['RENDIMIENTO_T_HA'])==Q(raw[b]['RENDIMIENTO_T_HA']) else 'no' if both else ''
        counts+=1
        if expected!=row['misma_etiqueta']:raise ValueError('Pareja cambiada')
    return {'estado':'aprobado','contrastes_exactos_y_aritmeticos':counts,'diferencia_max':maxdiff,'tolerancia':1e-12,
        'productor_importado':False,'aritmetica_independiente':'Fraction, no Decimal del productor',
        'OOF_verificados':sum(ledger_counts.values()),'etiquetas_nuevas':0,'entrenamientos':0}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--salida',type=Path,required=True);p.add_argument('--ledger',type=Path,required=True)
    a=p.parse_args();print(json.dumps(audit(a.salida,a.ledger),ensure_ascii=False,indent=2))
