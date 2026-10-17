"""T15: comparación simétrica acotada de verdor T13 bajo núcleo común inmutable."""
import argparse
import copy
import csv
import gzip
import json
from pathlib import Path
import subprocess
import time
import numpy as np
import pandas as pd
from scripts import evaluacion_comun_centrado_loo as v3
from scripts.t15_comparaciones_contrato import cargar as cargar_base
from scripts.evaluacion_comun_modelo import preparar_contexto,divisiones_internas,clave_opcion
from scripts.t15_comparaciones_traza import ajustar_y_trazar
from scripts.evaluacion_comun_contrato import exigir,sha,leer_csv,validar_oof,RAIZ
from scripts.t15_ejecutar import validar_salida,guardar_json,entorno,OOF
from scripts import t15_ejecutor_reportes as report

REGISTRO='registro/t15_t13/contrato_v1.json'
SHA='620b9e497a4d97df02d23162c9c96f1d1f56f980cd0803c73a4b7e22a3b81156'
CODIGO=['scripts/t15_t13_datos.py','scripts/t15_t13_ejecutar.py','scripts/t15_t13_auditar.py','tests/test_t15_t13.py']
DATA='registro/t15_t13/fuentes/variables_indices_extra.csv'
REF='media_mun__resp_grupo'


def codigos(root):return {p:sha(root/p) for p in CODIGO}


def unir_side(X,side,cols):
    exigir(side.index.is_unique and X.index.is_unique,'IDs repetidos')
    exigir(set(X.index)<=set(side.index),'ID faltante en T13')
    exigir(not set(cols)&set(X),'La familia pisa columnas comunes')
    out=X.join(side[list(cols)],how='left',validate='one_to_one')
    exigir(np.isfinite(out[list(cols)].to_numpy(float)).all(),'Familia con faltantes/infinitos')
    return out


def cargar(root=RAIZ):
    root=Path(root);exigir(sha(root/REGISTRO)==SHA,'Contrato alterado');c=json.loads((root/REGISTRO).read_text())
    _,e=cargar_base(root)
    for p,h in c['fuentes_sha256'].items():exigir(sha(root/p)==h,'Fuente alterada '+p)
    cab,rows=leer_csv(root/DATA);exigir(len(rows)==197 and len({r['id_parcela'] for r in rows})==197,'IDs T13 inválidos')
    side=pd.DataFrame(rows).set_index('id_parcela')[c['variables_nuevas']].astype(float).sort_index()
    exigir(set(side.index)=={k[0] for k in e['tabla']},'Catálogos distintos')
    exigir(np.isfinite(side.to_numpy()).all(),'Familia incompleta/no finita')
    for p in c['procedimientos']:
        exigir(p['columnas']==c['procedimientos'][0]['columnas']+(c['variables_nuevas'] if p['codigo']=='S_V' else []),'Esquema/orden incorrecto')
    old=[r for r in leer_csv(root/'registro/t15_resultados/predicciones_oof.csv')[1] if r['candidato'] in [REF,'comun_centrado_loo_v3_S']]
    old+=leer_csv(root/'registro/t03/predicciones_oof_referencias_mediana_mun__resp_grupo.csv')[1]
    exigir(len(old)==4140,'Comparadores incompletos');validar_oof(old,e['contextos'])
    return c,e,side,old


def opciones(p):
    return [dict(nombre='referencia_sola',columnas=[],lambda_reg=None,ventana='estatica')]+[
        dict(nombre=f'abr_oct__lambda_{l:g}',columnas=p['columnas'],lambda_reg=l,ventana='abr_oct') for l in [.01,.1,1.,10.]]


def ajuste(X,y,q,o,elig):
    try:m,d,t=ajustar_y_trazar(X,y,q,o,elig)
    except Exception as exc:
        raise
    t.update(estado_modelo=m.estado(),consulta=[dict(id_parcela=i,**r.to_dict()) for i,r in d.iterrows()])
    return m,d,t


def seleccionar(X,y,p,esc,emit,identity):
    scores=[]
    for o in opciones(p):
        errors=[];all_errors=[]
        for n,split in enumerate(divisiones_internas(X,esc)):
            tr,va=X.loc[list(split.entrenamiento)],X.loc[list(split.validacion)]
            _,d,t=ajuste(tr,y.loc[tr.index],va,o,split.elegibles)
            err=abs(d.prediccion.to_numpy()-y.loc[va.index].to_numpy());errors.extend(err[np.asarray(split.elegibles)]);all_errors.extend(err)
            emit({**t,**identity,'etapa':'interna','division_interna':n,'MAE':float(err[np.asarray(split.elegibles)].mean()),'MAE_todas':float(err.mean())})
        scores.append(dict(nombre=o['nombre'],ventana=o['ventana'],lambda_reg=o['lambda_reg'],referencia_sola=not o['columnas'],
            MAE=float(np.mean(errors)),MAE_todas=float(np.mean(all_errors)),n_elegibles=len(errors),n_validacion=len(all_errors),n_ajustes=4,version=v3.VERSION))
    winner=min(scores,key=clave_opcion)
    return copy.deepcopy(next(o for o in opciones(p) if o['nombre']==winner['nombre'])),scores


def contrato_reportes(c):
    names=c['comparadores_reutilizados'][1:]+[p['candidato'] for p in c['procedimientos']]
    return dict(metodo=c['metodo'],principal=dict(procedimientos=[dict(candidato=n) for n in names],
        contrastes_planificados=[dict(candidato=a,frente_a=b,tipo='promocion' if a=='t15_t13_S_verdor_v1' and b==REF else 'descriptivo') for a,b in c['contrastes']]))


def generar_reportes(rows,e,c,out):
    table={k[0]:v for k,v in e['tabla'].items()};q={r['id_parcela']:r for r in leer_csv(RAIZ/'registro/t07/calidad_parcelas.csv')[1]}
    report.producir(rows,e['contextos'],contrato_reportes(c),q,table,out)
    contrasts=leer_csv(out/'contrastes.csv')[1]
    find=lambda b:next(r for r in contrasts if r['escenario']=='A' and r['subconjunto']=='sin_respaldo' and r['candidato']=='t15_t13_S_verdor_v1' and r['frente_a']==b)
    t03=find(REF);control=find('t15_t13_control_S_abr_v1')
    t=t03['cumple_regla_T03']=='True';aporte=float(control['dMAE'])<0 and json.loads(control['IC95_celdas_MAE'])[1]<0
    d=dict(resultado='evaluado_pendiente_auditoria',cumple_T03=t,cumple_guardia_aporte=aporte,
        elegible_por_contrato=t and aporte,procedimiento_recomendado_por_regla='t15_t13_S_verdor_v1' if t and aporte else REF,
        ganador_T16_congelado=False,predicciones_finales59=0,exposicion_previa=True)
    guardar_json(out/'decision.json',d)
    return d


def comprobar_puerta(root,path):
    exigir(path is not None,'Falta puerta previa');g=json.loads(Path(path).read_text())
    exigir(g['resultado']=='aprobado' and g['contrato_sha256']==SHA and g['codigo_sha256']==codigos(root),'Puerta/código incorrectos')
    exigir(g['tests_Mac']>=12 and g['tests_Linux']>=12 and g['selecciones_iguales'] is True and g['max_diferencia_OOF']<=1e-12,'QA previa insuficiente')
    for p,h in g['evidencias_sha256'].items():exigir(sha(Path(path).parent/p)==h,'Evidencia previa alterada')
    for name in ['auditoria_mac.json','auditoria_linux.json','datos_mac.json','datos_linux.json']:
        exigir(json.loads((Path(path).parent/name).read_text())['resultado']=='aprobado','Auditoría pendiente '+name)
    return g


def ejecutar(root,out,modo='prueba',puerta=None):
    root=Path(root).resolve();exigir(root==RAIZ.resolve(),'Ejecutar desde el repo identificado')
    exigir(modo in ['prueba','completa'],'Modo no admitido');out=validar_salida(out,root);c,e,side,old=cargar(root);codes=codigos(root)
    if modo=='completa':
        comprobar_puerta(root,puerta)
        exigir(not subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],cwd=root,text=True),'Guardar código antes de evaluar')
    out.mkdir(parents=True);start=time.monotonic()
    manifest=dict(schema='T15_T13_evaluacion_v1',modo=modo,estado='en_curso',evaluacion_completa=False,
        contrato_sha256=SHA,codigo_sha256=codes,fuentes_sha256=c['fuentes_sha256'],fuente_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),
        entorno=entorno(),contextos=0,ajustes=0,OOF_nuevas=0,predicciones_finales59=0,ganador_T16_congelado=False,puerta_sha256=sha(puerta) if puerta else None)
    guardar_json(out/'manifest.json',manifest)
    try:
        contexts=[(s,1,0) for s in ['A','B']] if modo=='prueba' else [(s,r,f) for s in ['A','B'] for r in range(1,6) for f in range(5)]
        all_rows=[];all_sel=[]
        with gzip.open(out/'trazas_ajustes.jsonl.gz','wt',encoding='utf-8') as traza,(out/'selecciones.jsonl').open('x') as sels,\
             (out/'predicciones_incrementales.csv').open('x',newline='') as incremental:
            writer=csv.DictWriter(incremental,fieldnames=OOF,lineterminator='\n');writer.writeheader()
            def emit(t):
                traza.write(json.dumps(t,ensure_ascii=False,allow_nan=False)+'\n');traza.flush();manifest['ajustes']+=1
            for n,(s,r,f) in enumerate(contexts,1):
                X,y,q=preparar_contexto(e,s,r,f);X=unir_side(X,side,c['variables_nuevas']);q=unir_side(q,side,c['variables_nuevas'])
                for p in c['procedimientos']:
                    identity=dict(escenario=s,repeticion=r,particion=f,candidato=p['candidato'])
                    o,scores=seleccionar(X,y,p,s,emit,identity)
                    selection={**identity,'nombre_opcion':o['nombre'],'referencia_sola':not o['columnas'],'lambda_reg':o['lambda_reg'],'ventana':o['ventana'],'elegida':o,'puntuaciones':scores,'version':v3.VERSION}
                    sels.write(json.dumps(selection,ensure_ascii=False,allow_nan=False)+'\n');sels.flush();all_sel.append(selection)
                    elig=tuple(bool(v) for v in q.municipio.isin(X.municipio))
                    _,details,t=ajuste(X,y,q,o,elig)
                    emit({**t,**identity,'etapa':'externa'})
                    new=[]
                    for pid,v in details.iterrows():
                        context=e['contextos'][s,r,pid];exigir(context['particion']==f and context['fuente']==v.fuente,'Contexto OOF incorrecto')
                        new.append(dict(ID_POLIGONO=pid,repeticion=r,particion=f,escenario=s,real=context['real'],prediccion=float(v.prediccion),candidato=p['candidato'],version=v3.VERSION,fuente=v.fuente))
                    writer.writerows(new);incremental.flush();all_rows.extend(new)
                manifest.update(contextos=n,OOF_nuevas=len(all_rows));guardar_json(out/'manifest.json',manifest)
                print(f'T13 común: {n}/{len(contexts)} contextos ({s},{r},{f}).',flush=True)
        if modo=='completa':
            exigir(manifest['ajustes']==2100 and len(all_rows)==2760 and len(all_sel)==100,'Presupuesto/cobertura incorrectos')
            all_rows=old+all_rows;validar_oof(all_rows,e['contextos']);generar_reportes(all_rows,e,c,out)
            manifest.update(estado='completa_pendiente_auditoria',evaluacion_completa=True,OOF_reutilizadas=4140)
            report.csv_guardar(out/'frecuencia_referencia_sola.csv',v3.frecuencia_referencia_sola(all_sel))
        else:manifest['estado']='piloto_funcional_no_desempeno_global'
        report.csv_guardar(out/('predicciones_oof.csv' if modo=='completa' else 'oof_parcial_prueba.csv'),all_rows,OOF)
        exigir(codigos(root)==codes,'Código cambió durante evaluación')
        for p,h in c['fuentes_sha256'].items():exigir(sha(root/p)==h,'Fuente cambió durante evaluación')
    except BaseException as exc:
        manifest.update(estado='fallido',evaluacion_completa=False,error=dict(tipo=type(exc).__name__,mensaje=str(exc)));raise
    finally:
        manifest['tiempo_segundos']=time.monotonic()-start;manifest['archivos_sha256']={p.name:sha(p) for p in out.iterdir() if p.name!='manifest.json' and p.is_file()}
        guardar_json(out/'manifest.json',manifest)
    return manifest


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--raiz',type=Path,default=RAIZ);p.add_argument('--salida',type=Path,required=True);p.add_argument('--modo',choices=['prueba','completa'],default='prueba');p.add_argument('--puerta',type=Path)
    a=p.parse_args();r=ejecutar(a.raiz,a.salida,a.modo,a.puerta);print(json.dumps({k:v for k,v in r.items() if k not in ['fuentes_sha256','codigo_sha256']},ensure_ascii=False,indent=2))
