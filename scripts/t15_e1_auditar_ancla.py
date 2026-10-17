"""Auditor portable del ancla desde raw: no importa el productor ni lee rendimientos."""
import argparse,csv,hashlib,json,math
from collections import defaultdict
from datetime import datetime,date,timedelta
from pathlib import Path

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--raiz',type=Path,default=Path(__file__).resolve().parents[1])
parser.add_argument('--qa',type=Path,required=True)
parser.add_argument('--salida',type=Path,required=True)
args=parser.parse_args()
ROOT=args.raiz.resolve();OUT=args.qa.resolve()
def require(ok,message='QA del ancla no coincide'):
    if not ok:raise ValueError(message)
require(not args.salida.exists(),'Elegir una salida nueva')
raw=ROOT/'data/raw/DATASET_RETO_AGRO_2026/Conjunto_datos_BASICO_AgroCebada2026.csv'
require(hashlib.sha256(raw.read_bytes()).hexdigest()=='96d68040d954d0903d761fd8ceed0dcd4a08e3842915a3ca44517d60e8bee4ef','Fuente raw distinta')
groups=defaultdict(list)
def number(s):return None if s.strip().lower() in {'','nan','na','null','none'} else float(s)
with (ROOT/'data/raw/DATASET_RETO_AGRO_2026/Conjunto_datos_BASICO_AgroCebada2026.csv').open(encoding='utf-8-sig',newline='') as f:
    for r in csv.DictReader(f):
        if r['sensor']=='Sentinel-2':
            groups[r['ID_POLIGONO']].append((datetime.strptime(r['fecha_captura'],'%d/%m/%Y').date(),
                number(r['ndvi_promedio']),number(r['ndwi_promedio']),number(r['porcentaje_nubosidad'])))
cut=date(2025,10,31)
def profile(obs,start,remove=None):
    valid=sorted((o for o in obs if start<=o[0]<=cut and o[0]!=remove and o[1] is not None and
                  o[3] is not None and 0<=o[3]<=5),key=lambda o:o[0])
    if len(valid)<5:return None,None,False,valid
    smooth=[]
    for i in range(len(valid)):
        v=sorted(o[1] for o in valid[max(0,i-1):i+2]);smooth.append(v[len(v)//2] if len(v)%2 else (v[0]+v[1])/2)
    peak=valid[smooth.index(max(smooth))];post=[o[2] for o in valid if peak[0]+timedelta(days=15)<=o[0]<=min(cut,peak[0]+timedelta(days=45)) and o[2] is not None]
    contrast=math.fsum(post)/len(post)-peak[2] if len(post)>=2 and peak[2] is not None else None
    admitted=contrast is not None and peak[0]+timedelta(days=45)<=cut
    return peak[0],contrast,admitted,valid
n=0;maximum=0.;base_cache={}
with (OUT/'perturbaciones.csv').open() as f:
    rows=list(csv.DictReader(f))
for r in rows:
    pid,w=r['id_parcela'],r['ventana'];start=date(2025,4 if w=='abr_oct' else 6,1)
    key=(pid,w)
    if key not in base_cache:base_cache[key]=profile(groups[pid],start)
    base=base_cache[key];remove=date.fromisoformat(r['fecha_retirada'])
    alt=profile(groups[pid],start,remove)
    require(str(base[0])==r['maximo_original']);n+=1
    require((alt[0].isoformat() if alt[0] else '')==r['maximo_alternativo']);n+=1
    require((r['admisible_original']=='True')==base[2] and (r['admisible_alternativo']=='True')==alt[2]);n+=2
    base_index=next(i for i,o in enumerate(base[3]) if o[0]==base[0])
    removed_index=next(i for i,o in enumerate(base[3]) if o[0]==remove)
    require(int(r['posicion_relativa'])==removed_index-base_index and abs(removed_index-base_index)<=1);n+=1
    for observed,expected in [('contraste_original',base[1]),('contraste_alternativo',alt[1]),('diferencia_E1_si_ambos_admisibles',alt[1]-base[1] if base[2] and alt[2] else None)]:
        value=None if r[observed]=='' else float(r[observed])
        require((value is None)==(expected is None));n+=1
        if value is not None:
            difference=abs(value-expected);maximum=max(maximum,difference);require(difference<=1e-12);n+=1
require(len(rows)==1180 and len(base_cache)==394,'Entrega incompleta')
result={'resultado':'aprobado','perfiles':394,'perturbaciones':len(rows),'comprobaciones':n,'diferencia_maxima':maximum,'tolerancia_absoluta':1e-12,'sin_importar_productor':True,'sin_rendimientos':True,'alcance':'fechas_soporte_valores_y_retiros_reconstruidos_desde_raw'}
args.salida.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(result,ensure_ascii=False,indent=2))
