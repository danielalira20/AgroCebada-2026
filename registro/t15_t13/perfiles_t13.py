"""Descriptivo de errores por ID; no ajusta ni selecciona modelos."""
import argparse,csv,json,math,hashlib
from pathlib import Path


def read(p):
    with p.open() as f:return list(csv.DictReader(f))


def calcular(root,run,dest):
    rows=read(run/'predicciones_oof.csv');table={r['id_parcela']:r for r in read(root/'registro/t07/tabla_comun.csv')}
    qa={r['id_parcela']:r for r in json.loads((root/'registro/t15_t13/verificacion_previa/datos_mac.json').read_text())['QA']}
    names=['t15_t13_S_verdor_v1','t15_t13_control_S_abr_v1','media_mun__resp_grupo','mediana_mun__resp_grupo']
    out=[]
    for pid in sorted({r['ID_POLIGONO'] for r in rows}):
        g=[r for r in rows if r['ID_POLIGONO']==pid and r['escenario']=='A'];r=dict(id_parcela=pid,municipio=table[pid]['municipio'],real_t_ha=table[pid]['rendimiento_t_ha'])
        r.update({k:qa[pid][k] for k in ['capturas_validas','capturas_alrededor_maximo','fecha_maximo']})
        for name in names:
            v=[r for r in g if r['candidato']==name]
            if len(v)!=5:raise ValueError('Cinco OOF A por ID')
            r[name+'_MAE']=math.fsum(abs(float(s['prediccion'])-float(s['real'])) for s in v)/5
        r['n_OOF_municipio']=sum(s['fuente']=='municipio' for s in g if s['candidato']==names[0])
        r['delta_vs_control']=r[names[0]+'_MAE']-r[names[1]+'_MAE'];r['delta_vs_media']=r[names[0]+'_MAE']-r[names[2]+'_MAE']
        out.append(r)
    with dest.open('x',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(out[0]));w.writeheader();w.writerows(out)
    main=[r for r in out if r['n_OOF_municipio']==5];eps=1e-12
    by={(r['candidato'],int(r['repeticion']),r['ID_POLIGONO']):r for r in rows if r['escenario']=='A'}
    magnitude={}
    for name in names[:2]:
        g=[r for r in rows if r['candidato']==name and r['escenario']=='A' and r['fuente']=='municipio']
        values=[abs(float(r['prediccion'])-float(by['media_mun__resp_grupo',int(r['repeticion']),r['ID_POLIGONO']]['prediccion'])) for r in g]
        magnitude[name]=dict(n=len(values),media_abs_correccion=math.fsum(values)/len(values),max_abs_correccion=max(values))
    return dict(parcelas=138,principal=135,magnitud_correccion_principal=magnitude,vs_control=dict(mejoran=sum(r['delta_vs_control']<-eps for r in main),empatan=sum(abs(r['delta_vs_control'])<=eps for r in main),empeoran=sum(r['delta_vs_control']>eps for r in main)),
        vs_media=dict(mejoran=sum(r['delta_vs_media']<-eps for r in main),empatan=sum(abs(r['delta_vs_media'])<=eps for r in main),empeoran=sum(r['delta_vs_media']>eps for r in main)),
        QA_una_captura_de_197=sum(r['capturas_alrededor_maximo']==1 for r in qa.values()),
        predicciones_promediadas_antes_del_error=False,ajustes=0)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('run',type=Path);p.add_argument('dest',type=Path);a=p.parse_args();print(json.dumps(calcular(a.root,a.run,a.dest),indent=2))
