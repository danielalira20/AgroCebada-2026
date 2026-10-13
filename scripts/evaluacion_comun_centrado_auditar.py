"""Control técnico H3 en 50 contextos reales; no mide MAE ni ejecuta T15.

Usa una λ fija y bloques predefinidos. Reconstruye transformación, referencia
LOO y Ridge con NumPy, sin usar Ridge/StandardScaler para el contraste.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import platform
import sys

import numpy as np
import pandas as pd
import scipy
import sklearn

from scripts.evaluacion_comun_contrato import exigir
from scripts.evaluacion_comun_modelo import preparar_contexto, NULLABLE
from scripts import evaluacion_comun_centrado as v2


def independiente(x,y,q,cols,lamb=.1):
    x=x.sort_index();y=y.loc[x.index]
    a=x[cols].to_numpy(float).copy();b=q[cols].to_numpy(float).copy()
    if 'area_ha_origen' in cols:
        j=cols.index('area_ha_origen');a[:,j]=np.log(a[:,j]);b[:,j]=np.log(b[:,j])
    if NULLABLE in cols:
        j=cols.index(NULLABLE);ma=np.isnan(a[:,j]);mb=np.isnan(b[:,j]);exigir((~ma).any(),'Sin mediana')
        med=np.median(a[~ma,j]);a[ma,j]=med;b[mb,j]=med
        a=np.column_stack([a,ma.astype(float)]);b=np.column_stack([b,mb.astype(float)])
    mu=a.mean(0);sd=a.std(0);sd[sd==0]=1;z=(a-mu)/sd;zq=(b-mu)/sd
    muni=x.municipio.to_numpy();grp=x.cultivo_origen.to_numpy()
    centers={m:z[muni==m].mean(0) for m in set(muni)}
    groups={g:z[grp==g].mean(0) for g in set(grp)}
    pm={m:math.fsum(y[muni==m])/sum(muni==m) for m in set(muni)}
    pg={g:math.fsum(y[grp==g])/sum(grp==g) for g in set(grp)};pglobal=math.fsum(y)/len(y)
    residual=[]
    for i in range(len(x)):
        mask=muni==muni[i];mask[i]=False
        if not mask.any():mask=grp==grp[i];mask[i]=False
        if not mask.any():mask=np.arange(len(x))!=i
        residual.append(y.iloc[i]-math.fsum(y.iloc[np.flatnonzero(mask)])/sum(mask))
    d=z-np.stack([centers[m] for m in muni]);alpha=len(x)*lamb
    beta=np.linalg.lstsq(np.vstack([d,np.sqrt(alpha)*np.eye(d.shape[1])]),np.r_[residual,np.zeros(d.shape[1])],rcond=None)[0]
    cq=[];ref=[];source=[]
    for r in q.itertuples():
        if r.municipio in centers:cq.append(centers[r.municipio]);ref.append(pm[r.municipio]);source.append('municipio')
        elif r.cultivo_origen in groups:cq.append(groups[r.cultivo_origen]);ref.append(pg[r.cultivo_origen]);source.append('grupo')
        else:cq.append(z.mean(0));ref.append(pglobal);source.append('global')
    pred=np.asarray(ref)+(zq-np.stack(cq))@beta
    return dict(pred=pred,source=source,coef=beta,centers=centers,mu=mu,sd=sd,d=d)


def auditar(raiz):
    e=v2.cargar_entradas(raiz)
    prop=json.loads((Path(raiz)/'registro/evaluacion_comun/propuesta_t15_centrado_v2.json').read_text())
    blocks={p['candidato'].removeprefix('comun_centrado_v2_'):next(o['columnas'] for o in p['opciones'] if o['ventana'] in ['jun_oct','estatica']) for p in prop['procedimientos']}
    controls=[];maximum=dict(prediccion=0.,coeficientes=0.,centros=0.,media=0.,escala=0.,correccion_media_municipal_train=0.)
    for esc in ['A','B']:
        for rep in range(1,6):
            for fold in range(5):
                x,y,q=preparar_contexto(e,esc,rep,fold)
                exigir(not set(x.index)&set(q.index) and not (set(x.index)|set(q.index))&e['reservados'],'IDs fuera de contexto')
                for block in ['C','G','P','S','CGP']:
                    cols=blocks[block];model=v2.CorreccionComunCentrada(cols,.1).fit(x,y)
                    audit=independiente(x,y,q,cols)
                    pred=model.predict_with_details(q)
                    exigir(pred.fuente.tolist()==audit['source'],'Respaldo independiente distinto')
                    diffs=dict(prediccion=float(np.max(abs(pred.prediccion.to_numpy()-audit['pred']))),
                               coeficientes=float(np.max(abs(model.ridge_.coef_-audit['coef']))),
                               centros=max(float(np.max(abs(model.centros_mun_.loc[m]-v))) for m,v in audit['centers'].items()),
                               media=float(np.max(abs(model.escalador_.mean_-audit['mu']))),
                               escala=float(np.max(abs(model.escalador_.scale_-audit['sd']))),
                               correccion_media_municipal_train=float(model.predict_with_details(x).correccion.groupby(x.municipio).mean().abs().max()))
                    for name,value in diffs.items():maximum[name]=max(maximum[name],value)
                    exigir(diffs['prediccion']<=1e-9,'Predicción no reproduce matriz')
                    exigir(diffs['coeficientes']<=1e-10 and diffs['centros']<=1e-10,'Estado no reproduce matriz')
                    exigir(diffs['correccion_media_municipal_train']<=1e-12,'H3 en entrenamiento')
                    before=json.dumps(model.estado(),sort_keys=True)
                    for pid,row in pred.iterrows():controls.append(dict(escenario=esc,repeticion=rep,particion=fold,bloque=block,id_parcela=pid,prediccion=float(row.prediccion),correccion=float(row.correccion),fuente=row.fuente))
                    exigir(before==json.dumps(model.estado(),sort_keys=True),'Predict modificó el estado')
    return dict(resultado='verificado',version=v2.VERSION,sha_procedimiento=v2.DISENO_SHA,
                alcance='control_matematico_fijo_sin_evaluacion_externa',lambda_fija=.1,
                contextos=50,bloques=5,ajustes_Ridge_tecnicos=250,predicciones_control=len(controls),
                maximos=maximum,seleccion_de_bloque=False,MAE_externo_calculado=False,
                T15_completo_ejecutado=False,ajustes_finales_59=0,revision_humana_pendiente=True,
                entorno=dict(sistema=platform.system(),arquitectura=platform.machine(),python=platform.python_version(),
                    numpy=np.__version__,pandas=pd.__version__,scipy=scipy.__version__,sklearn=sklearn.__version__),
                fuentes_sha256=e['config']['fuentes_sha256']),controls


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--raiz',type=Path,default=v2.RAIZ);parser.add_argument('--salida',type=Path,required=True)
    a=parser.parse_args();exigir(not a.salida.exists(),'El control requiere destino nuevo; no sobreescribir')
    result,rows=auditar(a.raiz);a.salida.mkdir(parents=True)
    pd.DataFrame(rows).to_csv(a.salida/'controles_fijos.csv',index=False,float_format='%.17g')
    result['control_sha256']=hashlib.sha256((a.salida/'controles_fijos.csv').read_bytes()).hexdigest()
    (a.salida/'verificacion.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='fuentes_sha256'},ensure_ascii=False,indent=2))


if __name__=='__main__':main()
