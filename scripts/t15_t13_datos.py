"""Auditor directo del resumen T13 desde ZIP original; sin modelos ni etiquetas."""
import argparse
import csv
from datetime import datetime
import io
import json
import math
from pathlib import Path
from statistics import median
import zipfile
from scripts.evaluacion_comun_contrato import exigir, sha, leer_csv, RAIZ
from scripts.t15_ejecutar import guardar_json

CONTRATO='registro/t15_t13/contrato_v1.json'
SHA='620b9e497a4d97df02d23162c9c96f1d1f56f980cd0803c73a4b7e22a3b81156'
TABLA='registro/t15_t13/fuentes/variables_indices_extra.csv'
INDICES=['evi','savi','fapar','mra']


def resumir(rows):
    groups={};seen=set()
    for r in rows:
        if r['sensor']!='Sentinel-2':continue
        pid=r['ID_POLIGONO'];date=datetime.strptime(r['fecha_captura'],'%d/%m/%Y').date()
        exigir((pid,date) not in seen,'ID/fecha repetida');seen.add((pid,date))
        if not ('2025-04-01'<=date.isoformat()<='2025-10-31'):continue
        if not r['ndvi_promedio'] or not r['porcentaje_nubosidad']:continue
        v=float(r['ndvi_promedio']);cloud=float(r['porcentaje_nubosidad'])
        exigir(math.isfinite(v) and math.isfinite(cloud) and 0<=cloud<=100,'Dato original inválido')
        if cloud>5:continue
        values=[float(r[k+'_promedio']) for k in [*INDICES,'ndwi']]
        exigir(all(math.isfinite(x) for x in values),'Índice original faltante/no finito')
        groups.setdefault(pid,[]).append((date,v,values))
    out=[]
    for pid,g in sorted(groups.items()):
        g.sort();exigir(len(g)>=5,'Menos de cinco capturas válidas')
        smooth=[median([r[1] for r in g[max(0,j-1):min(len(g),j+2)]]) for j in range(len(g))]
        k=smooth.index(max(smooth));near=[r for r in g if abs((r[0]-g[k][0]).days)<=15]
        r=dict(id_parcela=pid,s2_ndvi_max_abr_oct=smooth[k])
        r.update({f's2_{index}_en_maximo_abr_oct':median([n[2][j] for n in near]) for j,index in enumerate([*INDICES,'ndwi'])})
        out.append((r,dict(id_parcela=pid,capturas_validas=len(g),capturas_alrededor_maximo=len(near),fecha_maximo=g[k][0].isoformat(),primera=g[0][0].isoformat(),ultima=g[-1][0].isoformat())))
    return out


def auditar(root=RAIZ):
    root=Path(root);exigir(sha(root/CONTRATO)==SHA,'Contrato alterado')
    c=json.loads((root/CONTRATO).read_text())
    for p,h in c['fuentes_sha256'].items():exigir(sha(root/p)==h,'Fuente alterada: '+p)
    original=root/'data/raw/DataSet.zip'
    with zipfile.ZipFile(original) as z:
        files=[p for p in z.namelist() if p.endswith('/Conjunto_datos_BASICO_AgroCebada2026.csv') or p=='Conjunto_datos_BASICO_AgroCebada2026.csv']
        exigir(len(files)==1,'Básico ambiguo/ausente');raw=z.read(files[0])
    import hashlib
    rows=list(csv.DictReader(io.StringIO(raw.decode('utf-8-sig'))));summary=resumir(rows)
    t={r['id_parcela']:r for r in leer_csv(root/TABLA)[1]}
    common={r['id_parcela']:r for r in leer_csv(root/'registro/t07/tabla_comun.csv')[1]}
    exigir(len(t)==len(summary)==197 and set(t)==set(common)=={r['id_parcela'] for r,_ in summary},'197 IDs requeridos')
    maximum=0.;n=0
    for row,_ in summary:
        for col,v in row.items():
            if col=='id_parcela':continue
            d=abs(v-float(t[row['id_parcela']][col]));maximum=max(maximum,d);n+=1
            exigir(d<=1e-9,'Resumen T13 difiere del ZIP: '+row['id_parcela']+'/'+col)
        for source,target in [('s2_ndvi_max_abr_oct','s2_ndvi_max_abr_oct'),('s2_ndwi_en_maximo_abr_oct','s2_ndwi_en_maximo_abr_oct')]:
            d=abs(row[source]-float(common[row['id_parcela']][target]));maximum=max(maximum,d);n+=1
            exigir(d<=1e-9,'Ancla T07 distinta')
    return dict(resultado='aprobado',parcelas=197,comparaciones=n,diferencia_maxima=maximum,
        contrato_sha256=SHA,ZIP_sha256=sha(original),miembro_ZIP=files[0],CSV_original_sha256=hashlib.sha256(raw).hexdigest(),
        resumen_sha256=sha(root/TABLA),lee_rendimientos=False,importa_T06_T13=False,modelos_ajustados=0,
        QA=[q for _,q in summary])


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--raiz',type=Path,default=RAIZ);p.add_argument('--salida',type=Path,required=True);a=p.parse_args()
    exigir(not a.salida.exists(),'No sobrescribir auditoría');r=auditar(a.raiz);guardar_json(a.salida,r)
    print(json.dumps({k:v for k,v in r.items() if k!='QA'},ensure_ascii=False,indent=2))
