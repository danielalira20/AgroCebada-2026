"""E2/E12/E2Q completos: preparación anidada, fuentes fijas y autorización separada."""
import argparse
import csv
import json
from pathlib import Path
import subprocess
import time
from scripts import t15_e2_entradas as entrada
from scripts import t15_e2_modelo as modelo
from scripts import t15_e2_reportes as reportes
from scripts.t15_e2_registrar import verificar_registro
from scripts.evaluacion_comun_contrato import exigir,sha,leer_csv
from scripts.t15_ejecutar import validar_salida,guardar_json,entorno,OOF

ROOT=entrada.ROOT
REGISTRO='registro/t15_e2_modelo/registro_ejecucion_v1.json'
REGISTRO_SHA='fc6a5ef56daa000ec9e89361a23a63f2b0779c9fc62d280d626bb4cba2a55bd9'
AUTORIZACION='registro/t15_e2_evaluacion/autorizacion_v1.json'
CODIGO=['scripts/t15_e2_ejecutar.py','scripts/t15_e2_reportes.py','scripts/t15_e2_auditar_evaluacion.py',
        'tests/test_t15_e2_ejecutar.py']


def cargar(root):
    exigir(sha(root/REGISTRO)==REGISTRO_SHA,'Registro previo alterado')
    verificar_registro(root,root/REGISTRO)
    r=entrada.read_json(root/REGISTRO);a=entrada.read_json(root/AUTORIZACION)
    exigir(a['schema']=='E2_autorizacion_evaluacion_v1' and a['registro_previo_sha256']==REGISTRO_SHA,
           'Autorización no vinculada al registro previo')
    exigir(a['evaluacion_completa_autorizada'] is True and a['predicciones_finales59_autorizadas'] is False,
           'Alcance de autorización incorrecto')
    exigir(a['cambiar_metodo_tras_resultados'] is False,'No permitir ajuste posterior de reglas')
    return r,a,entrada.cargar(root)


def codigo(root):return {p:sha(root/p) for p in CODIGO}


def ejecutar_contexto(datos,registro,esc,rep,fold,emit,seleccion_emit,estado_emit):
    X,y,q=entrada.contexto(datos,esc,rep,fold)
    elig=tuple(bool(v) for v in q.municipio.isin(X.municipio));rows=[]
    identity=dict(escenario=esc,repeticion=rep,particion=fold)
    for proc in registro['procedimientos']:
        mode,candidate=proc['modo'],proc['candidato']
        selection=modelo.seleccionar(X,y,registro['opciones_base'],mode,esc,
            al_ajuste=lambda t:emit({**t,**identity,'candidato':candidate,'etapa':'interna'}))
        option=selection['elegida']
        seleccion_emit({**identity,'candidato':candidate,'version':registro['metodo']['version'],'modo':mode,
            'nombre_opcion':option['nombre'],'referencia_sola':not option['columnas'],
            'lambda_reg':option['lambda_reg'],'ventana':option['ventana'],
            'columnas_base':option['columnas'],'puntuaciones':selection['puntuaciones']})
        try:m,details,t=modelo.ajustar(X,y,q,option,mode,elig)
        except modelo.ErrorAjuste as exc:
            emit({**exc.traza,**identity,'candidato':candidate,'etapa':'externa'});raise
        emit({**t,**identity,'candidato':candidate,'etapa':'externa'})
        estado_emit({**identity,'candidato':candidate,'columnas_base':option['columnas'],
                     'lambda_reg':option['lambda_reg'],'estado_modelo':m.estado(),
                     'consulta':[dict(id_parcela=pid,**row.to_dict()) for pid,row in details.iterrows()]})
        for pid,row in details.iterrows():
            ctx=datos['entradas']['contextos'][esc,rep,pid]
            exigir(ctx['particion']==fold and row.fuente==ctx['fuente'],'Contexto OOF incorrecto')
            rows.append(dict(ID_POLIGONO=pid,repeticion=rep,particion=fold,escenario=esc,
                real=ctx['real'],prediccion=float(row.prediccion),candidato=candidate,
                version=registro['metodo']['version'],fuente=row.fuente))
    return rows


def comprobar_puerta(root,path):
    exigir(path is not None,'Falta puerta de integración comprobada')
    gate=entrada.read_json(path)
    exigir(gate['schema']=='E2_integracion_verificada_v1' and gate['resultado']=='aprobado','Puerta no aprobada')
    exigir(gate['registro_sha256']==sha(root/REGISTRO) and gate['autorizacion_sha256']==sha(root/AUTORIZACION),
           'Puerta de otro registro/autorización')
    exigir(gate['codigo_sha256']==codigo(root),'Código cambió después de comprobar integración')
    exigir(bool(gate.get('evidencia_sha256')),'Puerta sin evidencia vinculada')
    for name,h in gate['evidencia_sha256'].items():exigir(sha(root/name)==h,'Evidencia de integración modificada')
    exigir(gate['auditoria_Mac_aprobada'] is True and gate['auditoria_Linux_aprobada'] is True and
           gate['pruebas_Mac_Linux_aprobadas'] is True and gate['reportes_guardia_comprobados'] is True,
           'Comprobaciones de integración pendientes')
    return gate


def ejecutar(root,output,modo='verificar',*,confirmar_completa=False,verificacion=None):
    exigir(modo in ['verificar','prueba','completa'],'Modo no registrado')
    exigir(confirmar_completa is (modo=='completa'),'Completa requiere confirmación explícita')
    root=Path(root).resolve();output=validar_salida(output,root)
    registro,auth,datos=cargar(root);codes=codigo(root)
    if modo=='completa':
        comprobar_puerta(root,verificacion)
        exigir(not subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],cwd=root,text=True),
               'Guardar código antes de evaluación completa')
    output.mkdir(parents=True);start=time.monotonic()
    manifest=dict(schema='E2_evaluacion_v1',modo=modo,estado='en_curso',evaluacion_completa=False,
        registro_sha256=sha(root/REGISTRO),autorizacion_sha256=sha(root/AUTORIZACION),
        codigo_sha256=codes,fuentes_sha256=registro['fuentes_sha256'],codigo_modelo_sha256=registro['codigo_sha256'],
        fuente_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),
        entorno=entorno(),puerta_sha256=sha(verificacion) if verificacion else None,
        predicciones_finales59=0,ganador_T16_congelado=False,contextos_ejecutados=0,
        contadores=dict(ajustes_internos=0,Ridge_internos=0,ajustes_externos=0,Ridge_externos=0),
        OOF_nuevas=0,OOF_reutilizadas=0)
    guardar_json(output/'manifest.json',manifest)
    try:
        if modo=='verificar':manifest.update(estado='verificado_sin_modelos')
        else:
            contexts=[(s,1,0) for s in ['A','B']] if modo=='prueba' else [(s,r,f) for s in ['A','B'] for r in range(1,6) for f in range(5)]
            rows=[];choices=[]
            with (output/'trazas_ajustes.jsonl').open('x') as log,(output/'selecciones.jsonl').open('x') as sels,\
                 (output/'estados_modelos.jsonl').open('x') as states,\
                 (output/'predicciones_nuevas_incrementales.csv').open('x',newline='') as incremental:
                writer=csv.DictWriter(incremental,fieldnames=OOF,lineterminator='\n');writer.writeheader()
                def persist(f,v):f.write(json.dumps(v,ensure_ascii=False,allow_nan=False)+'\n');f.flush()
                def emit(t):
                    persist(log,t)
                    if t['estado']=='correcto':
                        k='internos' if t['etapa']=='interna' else 'externos'
                        manifest['contadores']['ajustes_'+k]+=1
                        manifest['contadores']['Ridge_'+k]+=int(t['lambda_reg'] is not None)
                def selected(v):choices.append(v);persist(sels,v)
                for n,(s,r,f) in enumerate(contexts,1):
                    new=ejecutar_contexto(datos,registro,s,r,f,emit,selected,lambda v:persist(states,v))
                    rows.extend(new);writer.writerows(new);incremental.flush()
                    manifest.update(contextos_ejecutados=n,OOF_nuevas=len(rows));guardar_json(output/'manifest.json',manifest)
                    print(f'E2: {n}/{len(contexts)} contextos guardados ({s}, {r}, {f}).',flush=True)
            if modo=='completa':
                c=manifest['contadores']
                exigir(c['ajustes_internos']==5400 and c['Ridge_internos']==4800 and c['ajustes_externos']==150 and
                       c['Ridge_externos']<=150 and len(rows)==4140 and len(choices)==150,'Presupuesto/cobertura incorrectos')
                rows=datos['fuentes_reutilizadas']+rows;exigir(len(rows)==8280,'Reutilización incompleta')
                table={k[0]:r for k,r in datos['entradas']['tabla'].items()}
                quality={r['id_parcela']:r for r in leer_csv(root/'registro/t07/calidad_parcelas.csv')[1]}
                manifest['reportes']=reportes.producir(rows,datos['entradas']['contextos'],registro,quality,table,output)
                from scripts.evaluacion_comun_centrado_loo import frecuencia_referencia_sola
                reportes.comun.csv_guardar(output/'frecuencia_referencia_sola.csv',frecuencia_referencia_sola(choices))
                manifest.update(estado='completa_verificada',evaluacion_completa=True,OOF_reutilizadas=4140)
            else:manifest.update(estado='prueba_funcional_parcial_no_desempeno_global')
            reportes.comun.csv_guardar(output/('predicciones_oof.csv' if modo=='completa' else 'oof_parcial_prueba.csv'),rows,OOF)
        exigir(codes==codigo(root),'Código cambió durante evaluación')
        exigir(sha(root/REGISTRO)==manifest['registro_sha256'] and sha(root/AUTORIZACION)==manifest['autorizacion_sha256'],
               'Registro/autorización cambió durante evaluación')
        for p,h in registro['fuentes_sha256'].items():exigir(sha(root/p)==h,'Fuente cambió durante evaluación')
        for p,h in registro['codigo_sha256'].items():exigir(sha(root/p)==h,'Modelo cambió durante evaluación')
    except BaseException as exc:
        manifest.update(estado='fallido',evaluacion_completa=False,error=dict(tipo=type(exc).__name__,mensaje=str(exc)));raise
    finally:
        manifest['tiempo_segundos']=time.monotonic()-start
        manifest['archivos_sha256']={p.name:sha(p) for p in output.iterdir() if p.name!='manifest.json' and p.is_file()}
        guardar_json(output/'manifest.json',manifest)
    return manifest


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--raiz',type=Path,default=ROOT)
    p.add_argument('--salida',type=Path,required=True);p.add_argument('--modo',choices=['verificar','prueba','completa'],default='verificar')
    p.add_argument('--confirmar-completa',action='store_true');p.add_argument('--verificacion',type=Path)
    a=p.parse_args();print(json.dumps(ejecutar(a.raiz,a.salida,a.modo,confirmar_completa=a.confirmar_completa,verificacion=a.verificacion),ensure_ascii=False,indent=2))
