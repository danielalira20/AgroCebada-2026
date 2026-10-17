"""Compara entregas E2 completas sin relajar las tolerancias del contrato."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def require(ok,msg):
    if not ok:raise ValueError(msg)


def read(p,key):
    with p.open() as f:rows=list(csv.DictReader(f))
    out={tuple(r[k] for k in key):r for r in rows}
    require(len(rows)==len(out),'Claves duplicadas')
    return out


def compare(a,b,out):
    require(not out.exists(),'No sobrescribir comparación')
    ma,mb=[json.loads((p/'manifest.json').read_text()) for p in [a,b]]
    for key in ['contrato_sha256','codigo_sha256','fuente_sha256','vectores_sha256','predictores']:
        require(ma[key]==mb[key],'Procedencias distintas: '+key)
    require(ma['estado']==mb['estado']=='completa','Entrega incompleta')
    for p,m in [(a,ma),(b,mb)]:
        for name,h in m['archivos_sha256'].items():require(sha(p/name)==h,'Artefacto alterado: '+name)
    maxima={};checks=0
    for name,key in [('atributos_parcela.csv',['id_parcela']),('calidad.csv',['id_parcela']),
                     ('sensibilidad.csv',['id_parcela','escenario_desplazamiento'])]:
        x,y=[read(p/name,key) for p in [a,b]]
        require(x.keys()==y.keys(),'IDs o escenarios distintos')
        for k,row in x.items():
            require(row.keys()==y[k].keys(),'Esquema distinto')
            for col,v in row.items():
                w=y[k][col]
                if col in key or col=='admisible' or not v or not w:
                    require(v==w,'Estado o clave distinta');checks+=1;continue
                v,w=float(v),float(w);require(math.isfinite(v) and math.isfinite(w),'No finito')
                if col in ['e2_tpi150_media_m','delta_TPI_m','rango_altitud_QA_m']:tol=1e-6
                elif col=='pendiente_media_grados_QA':tol=1e-7
                elif 'area_' in col:tol=max(1e-8,abs(v)*1e-8)
                elif col=='n_celdas_interseccion_positiva':tol=0
                elif col.startswith('delta_'):tol=2e-9
                else:tol=1e-9
                delta=abs(v-w);maxima[col]=max(maxima.get(col,0),delta)
                require(delta<=tol,'Fuera de tolerancia '+str(k)+' '+col+': '+str(delta));checks+=1
    result=dict(schema='E2_reproduccion_plataformas_v1',resultado='aprobado',comprobaciones=checks,
        max_diferencias=maxima,entregas=[{'manifest_sha256':sha(p/'manifest.json'),'versiones':m['versiones']}
                                     for p,m in [(a,ma),(b,mb)]],
        tolerancias='contrato_E2_sin_relajar_OOF_ni_cambiar_modelo',codigo_sha256=sha(__file__))
    out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--a',type=Path,required=True)
    p.add_argument('--b',type=Path,required=True);p.add_argument('--salida',type=Path,required=True)
    a=p.parse_args();print(json.dumps(compare(a.a,a.b,a.salida),indent=2,ensure_ascii=False))
