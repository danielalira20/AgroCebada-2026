"""Auditor aparte: originales→T06 aceptado, sin importar productor/figuras fase3."""
import argparse
import csv
import io
import json
import math
from pathlib import Path
import tempfile
import zipfile
import hashlib
import pandas as pd
from scripts import t06_satelite as t

ROOT=Path(__file__).resolve().parents[1]


def read(p):
    with Path(p).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))


def audit(output):
    output=Path(output);count=0;maximum=0
    d=json.loads((ROOT/'registro/diagnostico/fase3_diseno.json').read_text())
    for n,sha in d['archivos_fuente'].items():
        if hashlib.sha256((ROOT/n).read_bytes()).hexdigest()!=sha:raise ValueError('Fuente distinta '+n)
    m=json.loads((output/'manifest.json').read_text())
    for n,sha in m['archivos_sha256'].items():
        if hashlib.sha256((output/n).read_bytes()).hexdigest()!=sha:raise ValueError('Salida distinta '+n)
    def compare(a,b):
        nonlocal count,maximum
        count+=1
        if a=='' or pd.isna(b):
            if not (a=='' and pd.isna(b)):raise ValueError('Vacío distinto')
        else:
            delta=abs(float(a)-float(b));maximum=max(maximum,delta)
            if not math.isfinite(delta) or delta>1e-9:raise ValueError('Valor distinto '+str(delta))
    with tempfile.TemporaryDirectory(prefix='auditor_f3_') as td:
        with zipfile.ZipFile(ROOT/'data/raw/DataSet.zip') as z:
            for name in [*t.ARCHIVOS.values(),'ID_area_rendimiento_70_30_Reto_AgroCebada.csv']:
                Path(td,name).write_bytes(z.read('DATASET_RETO_AGRO_2026/'+name))
        ser=t.series(Path(td))
        ids=pd.read_csv(Path(td,'ID_area_rendimiento_70_30_Reto_AgroCebada.csv'),encoding='utf-8-sig',usecols=['ID_POLIGONO','CONJUNTO']).sort_values('ID_POLIGONO')
        variables=t.variables(ser,ids).set_index('ID_POLIGONO')
        table={r['id_parcela']:r for r in read(ROOT/'registro/t07/tabla_comun.csv')}
        for pid,r in variables.iterrows():
            for col,b in r.items():compare(table[pid][col],b)
        qualities=read(output/'curvas_calidad.csv');keys=set()
        for r in qualities:
            pid,sensor,win=r['id_parcela'],r['sensor'],r['ventana'];key=(pid,sensor,win)
            if key in keys:raise ValueError('Clave duplicada curva')
            keys.add(key);s=ser[sensor];dates=pd.to_datetime(s.fecha_observada)
            raw=s.loc[(s.ID_POLIGONO==pid)&(dates>=t.VENTANAS[win])&(dates<=t.CORTE)]
            p=t.validas(s.loc[s.ID_POLIGONO==pid],sensor,t.VENTANAS[win])
            inner,gap=t.huecos(p.f,t.VENTANAS[win],t.CORTE)
            compare(r['capturas_originales'],len(raw));compare(r['capturas_validas'],len(p))
            compare(r['hueco_max_dias'],gap);compare(r['hueco_interno_dias'],inner)
            compare(r['capturas_validas_ultimos15'],sum(p.f>t.CORTE-pd.Timedelta(days=15)))
            if sensor!='Landsat':
                trait=t.rasgos_parcela(p.f.to_numpy(),p.ndvi_promedio.to_numpy())
                for k in ['inicio_observado','pico_observado','final_observado','posible_ciclo_doble','meseta_en_pico']:
                    count+=1
                    if r[k]!=str(bool(trait[k])):raise ValueError('Rasgo distinto '+pid+'/'+k)
        if len(keys)!=1182:raise ValueError('Curvas incompletas')
        # Changing only post-cut values cannot change any accepted compact summary.
        mutated={sensor:s.copy() for sensor,s in ser.items()}
        for s in mutated.values():
            post=pd.to_datetime(s.fecha_observada)>t.CORTE
            for c in s:
                if c.endswith('_promedio'):s.loc[post,c]=.987
        again=t.variables(mutated,ids).set_index('ID_POLIGONO')
        for pid,r in variables.iterrows():
            for c,b in r.items():compare('' if pd.isna(b) else str(b),again.loc[pid,c])
    q=read(output/'calidad_por_parcela.csv')
    if len(q)!=197 or len({r['id_parcela'] for r in q})!=197:raise ValueError('Calidad incompleta')
    result={'estado':'aprobado','contrastes':count,'diferencia_max':maximum,'tolerancia':1e-9,
        'modelo_entrenado':False,'auditor_importa_productor_fase3':False,
        'post_corte_metamorfico':'no_cambia_8668_valores_T06','calidad_197_curvas_1182':'completas'}
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--salida',type=Path,required=True)
    a=p.parse_args();print(json.dumps(audit(a.salida),ensure_ascii=False,indent=2))
