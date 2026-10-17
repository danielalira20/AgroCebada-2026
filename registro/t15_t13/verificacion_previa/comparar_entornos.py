"""Cotejo Mac/Linux por identidad, selección y todos los valores guardados."""
import argparse,csv,gzip,itertools,json,math
from pathlib import Path

def comparar(a,b):
    stats={'campos':0,'max_diferencia':0.0}
    def check(x,y,where):
        stats['campos']+=1
        if isinstance(x,dict):
            if set(x)!=set(y):raise ValueError('Claves '+where)
            for k in x:
                if k!='estado_modelo_sha256':check(x[k],y[k],where+'/'+k)
        elif isinstance(x,list):
            if len(x)!=len(y):raise ValueError('Largo '+where)
            for n,(v,w) in enumerate(zip(x,y)):check(v,w,where+'/'+str(n))
        elif isinstance(x,(float,int)) and not isinstance(x,bool):
            d=abs(x-y);stats['max_diferencia']=max(stats['max_diferencia'],d)
            if not math.isfinite(d) or d>1e-12:raise ValueError('Número '+where+': '+str(d))
        elif x!=y:
            try:d=abs(float(x)-float(y))
            except (ValueError,TypeError):raise ValueError('Texto '+where)
            stats['max_diferencia']=max(stats['max_diferencia'],d)
            if not math.isfinite(d) or d>1e-12:raise ValueError('Número CSV '+where)
    for name in ['predicciones_incrementales.csv','selecciones.jsonl']:
        if name.endswith('.csv'):
            with (a/name).open() as f:aa=list(csv.DictReader(f))
            with (b/name).open() as f:bb=list(csv.DictReader(f))
        else:
            aa=[json.loads(s) for s in (a/name).read_text().splitlines()];bb=[json.loads(s) for s in (b/name).read_text().splitlines()]
            check([s['elegida']['nombre'] for s in aa],[s['elegida']['nombre'] for s in bb],'selecciones_exactas')
        check(aa,bb,name)
    with gzip.open(a/'trazas_ajustes.jsonl.gz','rt') as fa,gzip.open(b/'trazas_ajustes.jsonl.gz','rt') as fb:
        n=0
        for n,(x,y) in enumerate(itertools.zip_longest(fa,fb),1):
            if x is None or y is None:raise ValueError('Número de trazas')
            check(json.loads(x),json.loads(y),'traza'+str(n))
    return dict(resultado='aprobado',selecciones_iguales=True,trazas=n,**stats)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mac',type=Path);p.add_argument('linux',type=Path);p.add_argument('salida',type=Path);a=p.parse_args()
    if a.salida.exists():raise ValueError('No sobrescribir')
    r=comparar(a.mac,a.linux);a.salida.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
