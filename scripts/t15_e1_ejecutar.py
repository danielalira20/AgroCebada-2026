"""Comparación separada E1/Q; reutiliza S/referencia publicados con fuentes exactas."""
import argparse
import csv
import json
from pathlib import Path
import subprocess
import time

import numpy as np
import pandas as pd

from scripts import t15_comparaciones_contrato as comun
from scripts import t15_e1_contrato as vista
from scripts import t15_e1_modelo as modelo
from scripts import t15_ejecutor_reportes as reportes
from scripts.evaluacion_comun_modelo import preparar_contexto
from scripts.evaluacion_comun_contrato import exigir, sha, leer_csv, validar_oof
from scripts.t15_ejecutar import guardar_json, validar_salida, entorno, OOF

ROOT=Path(__file__).resolve().parents[1]
REGISTRO='registro/t15_e1_evaluacion/registro_v1.json'
REGISTRO_SHA='4c05485aa33017fa15ad0fa7b5edde638fdc75c33bd1174e9932046a26520c89'
REFERENCIA='media_mun__resp_grupo'
S='comun_centrado_loo_v3_S'
CODIGO=['scripts/t15_e1_modelo.py','scripts/t15_e1_ejecutar.py','scripts/t15_e1_estabilidad.py']


def cargar(root=ROOT):
    root=Path(root)
    c,e=comun.cargar(root)
    exigir(sha(root/REGISTRO)==REGISTRO_SHA, 'Registro modificado: versionar antes de ejecutar')
    cfg=vista.read_json(root/REGISTRO)
    exigir(cfg['schema']=='agrocebada_E1_ejecucion_v1' and
           cfg['estado']=='registrado_antes_de_nuevas_OOF','Falta registro E1')
    exigir(cfg['decision']==c['decision'] and cfg['metodo']==c['metodo'], 'Criterios comunes modificados')
    s=next(p for p in c['principal']['procedimientos'] if p['bloques']==['S'])
    exigir(cfg['S_comparador']==s, 'Comparador S diferente')
    exigir([(p['modo'],p['promocion']) for p in cfg['procedimientos']]==[('Q',False),('E1',True)],
           'Menú/control E1 distinto')
    exigir([p['candidato'] for p in cfg['procedimientos']]==['comun_centrado_loo_v3_Q','comun_centrado_loo_v3_E1'],
           'Identidades E1 distintas')
    exigir(cfg['presupuesto']==dict(Ridge_internos=3200,Ridge_externos_max=100,
        referencias_internas_sin_cache=400,referencias_externas=50,contextos=50,
        opciones_por_procedimiento=8,S_y_referencia_publicados_reutilizados=True),'Presupuesto E1 modificado')
    for p,h in cfg['fuentes_sha256'].items():
        exigir(sha(root/p)==h,'Fuente E1/T15 modificada: '+p)
    vista.validate(vista.read_json(root/vista.CONFIG))
    original=vista.read_csv(root/'registro/t15_d1/perfil_ndwi_postpico.csv');vista.population(original)
    classified=[vista.classify(r) for r in original]
    rows=vista.read_csv(root/'registro/t15_e1/vista_admisibilidad_propuesta.csv')
    exigir([{k:str(v) for k,v in r.items()} for r in classified]==rows, 'Vista E1 no reproduce D1')
    by_window={w:{r['id_parcela']:r for r in rows if r['ventana']==w} for w in ['abr_oct','jun_oct']}
    catalog={k[0]:r for k,r in e['tabla'].items()}
    exigir(all(set(v)==set(catalog) for v in by_window.values()), 'IDs E1/T07 distintos')
    side=[]
    for pid in sorted(catalog):
        a,b=by_window['abr_oct'][pid],by_window['jun_oct'][pid]
        exigir(all(a[k]==b[k] for k in [vista.VALUE,vista.FLAG,'estado_E1','municipio','conjunto']),
               'E1 difiere entre ventanas: registrar política antes de usar')
        exigir(a['municipio']==catalog[pid]['municipio'] and a['conjunto']==catalog[pid]['conjunto_origen'],
               'Metadatos E1 distintos de T07')
        side.append(dict(id_parcela=pid,**{vista.VALUE:np.nan if a[vista.VALUE]=='' else float(a[vista.VALUE]),
                                        vista.FLAG:int(a[vista.FLAG])}))
    side=pd.DataFrame(side).set_index('id_parcela')
    exigir(len(side)==197 and int((side[vista.FLAG]==0).sum())==151, 'Soporte E1 alterado')
    published=leer_csv(root/'registro/t15_resultados/predicciones_oof.csv')[1]
    baseline=[r for r in published if r['candidato'] in [S,REFERENCIA]]
    validar_oof(baseline,e['contextos'])
    exigir({r['version'] for r in baseline}=={modelo.v3.VERSION}, 'S publicado de otra versión')
    return cfg,e,side,baseline


def contexto(e,side,esc,rep,fold):
    X,y,q=preparar_contexto(e,esc,rep,fold)
    exigir(not set(side)&set(X), 'Tabla adicional pisa columnas T07')
    return X.join(side,validate='one_to_one'),y,q.join(side,validate='one_to_one')


def ejecutar(root,output,modo='verificar',*,confirmar_completa=False,verificacion=None):
    exigir(modo in ['verificar','prueba','completa'], 'Modo desconocido')
    exigir(confirmar_completa is (modo=='completa'), 'Completa requiere confirmación explícita')
    root=Path(root).resolve();output=validar_salida(output,root)
    cfg,e,side,baseline=cargar(root)
    if modo=='completa':
        exigir(verificacion is not None, 'Falta verificación previa de esta versión')
        gate=vista.read_json(verificacion)
        exigir(gate['schema']=='E1_previa_verificada' and gate['resultado']=='aprobado', 'Pruebas previas incompletas')
        exigir(gate['registro_sha256']==sha(root/REGISTRO), 'Otro registro en las pruebas')
        exigir(gate['codigo_sha256']=={p:sha(root/p) for p in CODIGO}, 'Código cambió después de pruebas')
        dirty=subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],cwd=root,text=True)
        exigir(not dirty, 'Registrar código antes de la evaluación completa')
    output.mkdir(parents=True);start=time.monotonic()
    manifest=dict(schema='E1_Q_evaluacion_v1',modo=modo,estado='en_curso',evaluacion_completa=False,
        version=modelo.v3.VERSION,extension=modelo.EXTENSION,registro_sha256=sha(root/REGISTRO),
        fuente_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),
        codigo_sha256={p:sha(root/p) for p in CODIGO},fuentes_sha256=cfg['fuentes_sha256'],entorno=entorno(),
        contadores=dict(ajustes_internos=0,Ridge_internos=0,ajustes_externos=0,Ridge_externos=0),
        OOF_reutilizadas=2760 if modo=='completa' else 0,predicciones_finales59=0,
        ganador_T16_congelado=False)
    guardar_json(output/'manifest.json',manifest)
    try:
        if modo=='verificar':
            manifest.update(estado='verificado_sin_modelos',contextos_ejecutados=0)
        else:
            contexts=[('A',1,0)] if modo=='prueba' else [(s,r,f) for s in ['A','B'] for r in range(1,6) for f in range(5)]
            choices=[];rows=[]
            with (output/'trazas_ajustes.jsonl').open('x') as log, (output/'selecciones.jsonl').open('x') as selections, (output/'estados_modelos.jsonl').open('x') as states, (output/'predicciones_nuevas_incrementales.csv').open('x',newline='') as incremental:
                writer=csv.DictWriter(incremental,fieldnames=OOF,lineterminator='\n');writer.writeheader()
                def persist(stream,value):
                    stream.write(json.dumps(value,ensure_ascii=False,allow_nan=False)+'\n');stream.flush()
                def emit(t):
                    persist(log,t)
                    if t['estado']=='correcto':
                        cl='internos' if t['etapa']=='interna' else 'externos'
                        manifest['contadores']['ajustes_'+cl]+=1
                        manifest['contadores']['Ridge_'+cl]+=int(t['lambda_reg'] is not None)
                for n,(esc,rep,fold) in enumerate(contexts,1):
                    before=len(rows)
                    X,y,q=contexto(e,side,esc,rep,fold)
                    elig=tuple(bool(v) for v in q.municipio.isin(X.municipio))
                    identity=dict(escenario=esc,repeticion=rep,particion=fold)
                    for procedure in cfg['procedimientos']:
                        mode,candidate=procedure['modo'],procedure['candidato']
                        options=[dict(o,nombre=f"{o['ventana']}__lambda_{o['lambda_reg']:g}") for o in cfg['S_comparador']['opciones']]
                        selection=modelo.seleccionar(X,y,options,mode,esc,
                            al_ajuste=lambda t:emit({**t,**identity,'candidato':candidate,'etapa':'interna'}))
                        option=selection['elegida']
                        chosen={**identity,'candidato':candidate,'version':modelo.v3.VERSION,'modo':mode,
                                'nombre_opcion':option['nombre'],'referencia_sola':not option['columnas'],
                                'lambda_reg':option['lambda_reg'],'ventana':option['ventana'],
                                'columnas_base':option['columnas'],'puntuaciones':selection['puntuaciones']}
                        choices.append(chosen);persist(selections,chosen)
                        try: model,d,t=modelo.ajustar(X,y,q,option,mode,elig)
                        except modelo.ErrorAjuste as exc:
                            emit({**exc.traza,**identity,'candidato':candidate,'etapa':'externa'});raise
                        emit({**t,**identity,'candidato':candidate,'etapa':'externa'})
                        persist(states,{**identity,'candidato':candidate,'estado_modelo':model.estado()})
                        for pid,row in d.iterrows():
                            ctx=e['contextos'][esc,rep,pid]
                            exigir(ctx['particion']==fold and row.fuente==ctx['fuente'], 'Contexto OOF incorrecto')
                            rows.append(dict(ID_POLIGONO=pid,repeticion=rep,particion=fold,escenario=esc,
                                real=ctx['real'],prediccion=float(row.prediccion),candidato=candidate,
                                version=modelo.v3.VERSION,fuente=row.fuente))
                    writer.writerows(rows[before:]);incremental.flush()
                    manifest.update(contextos_ejecutados=n,OOF_nuevas=len(rows))
                    guardar_json(output/'manifest.json',manifest)
                    print(f'E1/Q: {n}/{len(contexts)} contextos guardados ({esc}, {rep}, {fold}).',flush=True)
            if modo=='completa':
                rows=baseline+rows
                exigir(len(rows)==5520 and len(choices)==100, 'Evaluación E1 incompleta')
                exigir(manifest['contadores']['ajustes_internos']==3600 and
                       manifest['contadores']['Ridge_internos']==3200 and
                       manifest['contadores']['ajustes_externos']==100 and
                       manifest['contadores']['Ridge_externos']<=100,'Presupuesto E1 incompleto/excedido')
                report_contract=dict(metodo=cfg['metodo'],principal=dict(procedimientos=[cfg['S_comparador'],*cfg['procedimientos']],
                    contrastes_planificados=cfg['contrastes']))
                quality={r['id_parcela']:r for r in leer_csv(root/'registro/t07/calidad_parcelas.csv')[1]}
                table={k[0]:r for k,r in e['tabla'].items()}
                manifest['reportes']=reportes.producir(rows,e['contextos'],report_contract,quality,table,output)
                reportes.csv_guardar(output/'frecuencia_referencia_sola.csv',modelo.v3.frecuencia_referencia_sola(choices))
                manifest.update(estado='completa_verificada',evaluacion_completa=True)
            else:manifest.update(estado='prueba_funcional_parcial_no_desempeno_global')
            reportes.csv_guardar(output/('predicciones_oof.csv' if modo=='completa' else 'oof_parcial_prueba.csv'),rows,OOF)
    except BaseException as exc:
        manifest.update(estado='fallido',evaluacion_completa=False,error=dict(tipo=type(exc).__name__,mensaje=str(exc)))
        raise
    finally:
        manifest['tiempo_segundos']=time.monotonic()-start
        manifest['archivos_sha256']={p.name:sha(p) for p in output.iterdir() if p.name!='manifest.json' and p.is_file()}
        guardar_json(output/'manifest.json',manifest)
    return manifest


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--raiz',type=Path,default=ROOT);ap.add_argument('--salida',type=Path,required=True)
    ap.add_argument('--modo',choices=['verificar','prueba','completa'],default='verificar')
    ap.add_argument('--confirmar-completa',action='store_true');ap.add_argument('--verificacion',type=Path)
    args=ap.parse_args()
    print(json.dumps(ejecutar(args.raiz,args.salida,args.modo,confirmar_completa=args.confirmar_completa,
                             verificacion=args.verificacion),ensure_ascii=False,indent=2))
