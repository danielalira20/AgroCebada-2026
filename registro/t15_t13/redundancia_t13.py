"""Correlación descriptiva de entradas sin cargar objetivos ni ajustar predictores."""
import argparse,csv,json,math
from pathlib import Path
from collections import defaultdict

def read(path,cols):
    with path.open() as f:return [{k:r[k] for k in cols} for r in csv.DictReader(f)]
def corr(x,y):
    mx=math.fsum(x)/len(x);my=math.fsum(y)/len(y)
    dx=[v-mx for v in x];dy=[v-my for v in y]
    return math.fsum(a*b for a,b in zip(dx,dy))/math.sqrt(math.fsum(a*a for a in dx)*math.fsum(b*b for b in dy))
def calcular(root):
    vcols=[f's2_{c}_en_maximo_abr_oct' for c in ['evi','savi','fapar','mra']];n='s2_ndvi_max_abr_oct'
    base={r['id_parcela']:r for r in read(root/'registro/t07/tabla_comun.csv',['id_parcela','municipio',n])}
    extra={r['id_parcela']:r for r in read(root/'registro/t15_t13/fuentes/variables_indices_extra.csv',['id_parcela',*vcols])}
    if set(base)!=set(extra) or len(base)!=197:raise ValueError('IDs de otro catálogo')
    ids=sorted(base);groups=defaultdict(list)
    for pid in ids:groups[base[pid]['municipio']].append(pid)
    vals={c:{i:float((base if c==n else extra)[i][c]) for i in ids} for c in [n,*vcols]}
    centered={c:{i:vals[c][i]-math.fsum(vals[c][j] for j in groups[base[i]['municipio']])/len(groups[base[i]['municipio']]) for i in ids} for c in vals}
    return dict(schema='T15_T13_redundancia_descriptiva_v1',parcelas=197,usa_rendimientos=False,no_modifica_modelo_o_seleccion=True,
        correlacion_Pearson_con_NDVI_max={c:dict(global_=corr([vals[c][i] for i in ids],[vals[n][i] for i in ids]),dentro_municipio=corr([centered[c][i] for i in ids],[centered[n][i] for i in ids])) for c in vcols})
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('salida',type=Path);a=p.parse_args()
    if a.salida.exists():raise ValueError('No sobrescribir')
    r=calcular(a.root);a.salida.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n');print(json.dumps(r))
