"""Evaluación local de una cuantílica compacta registrada; nunca ajusta las 59."""
import argparse
import csv
import json
from pathlib import Path
import subprocess
import time
from scripts import t15_cuantilica_modelo as modelo
from scripts.evaluacion_comun_contrato import exigir, sha, leer_csv, validar_oof, RAIZ
from scripts.t15_comparaciones_contrato import cargar as cargar_comun, preflight
from scripts.evaluacion_comun_modelo import preparar_contexto
from scripts.t15_ejecutar import validar_salida, guardar_json, entorno, OOF
from scripts.t15_ejecutor_reportes import resumen_grupo, csv_guardar
from scripts.evaluacion_comun_reportes import comparar, metricas

REGISTRO='registro/t15_cuantilica_contrato_v1.json'
CONTRATO_SHA='79ea3ffd0287209f01f89325d92ebcd3fd6c324b935885aa20629642075c1840'
CODIGO=['scripts/t15_cuantilica_modelo.py','scripts/t15_cuantilica_auditar.py',
        'scripts/t15_cuantilica_ejecutar.py','tests/test_t15_cuantilica.py']


def codigos(root):return {p:sha(root/p) for p in CODIGO}


def cargar(root):
    exigir(sha(root/REGISTRO)==CONTRATO_SHA,'Contrato de cuantílica modificado')
    c=json.loads((root/REGISTRO).read_text());_,e=cargar_comun(root)
    for p,h in c['fuentes_sha256'].items():exigir(sha(root/p)==h,'Fuente modificada: '+p)
    exigir(c['version']==modelo.VERSION and c['alpha']==list(modelo.ALPHAS),'Modelo no corresponde al registro')
    exigir(c['variables_por_ventana']=={w:list(cols) for w,cols in modelo.S.items()},'Variables cambiadas')
    rows=leer_csv(root/'registro/t15_resultados/predicciones_oof.csv')[1]
    rows=[r for r in rows if r['candidato'] in ['media_mun__resp_grupo','comun_centrado_loo_v3_S']]
    rows+=leer_csv(root/'registro/t03/predicciones_oof_referencias_mediana_mun__resp_grupo.csv')[1]
    exigir(len(rows)==4140,'Comparadores incompletos');validar_oof(rows,e['contextos'])
    return c,e,rows


def reportes(rows,contexts,c,out,quality,table):
    validar_oof(rows,contexts)
    exigir(len(rows)==5520 and {r['candidato'] for r in rows}=={modelo.CANDIDATO,'media_mun__resp_grupo',
        'mediana_mun__resp_grupo','comun_centrado_loo_v3_S'},'Evaluación incompleta')
    summaries=[];repetitions=[];desgloses=[];contrasts=[]
    alerts={i for i,r in quality.items() if r['alerta_contorno_t03_bis']=='si'}
    exigir(len(alerts & {k[2] for k in contexts})==24,'Sensibilidad sin24 distinta')
    for name in sorted({r['candidato'] for r in rows}):
        for s in ['A','B']:
            for subset in ['todas','sin_respaldo']:
                rs=[r for r in rows if r['candidato']==name and r['escenario']==s and (subset=='todas' or r['fuente']=='municipio')]
                identity=dict(candidato=name,escenario=s,subconjunto=subset)
                summaries.append({**identity,**resumen_grupo(rs)})
                for rep in range(1,6):
                    rr=[r for r in rs if int(r['repeticion'])==rep]
                    repetitions.append({**identity,'repeticion':rep,**metricas([float(r['real']) for r in rr],[float(r['prediccion']) for r in rr])})
                groups={'municipio':lambda i:table[i]['municipio'],
                    'grupo_registro':lambda i:table[i]['cultivo_origen'],
                    'vecina_etiquetada_menos_20m':lambda i:quality[i]['vecina_etiquetada_menos_20m'],
                    'contorno_categoria':lambda i:quality[i]['contorno_categoria']}
                for key,fun in groups.items():
                    for v in sorted({fun(r['ID_POLIGONO']) for r in rs}):
                        desgloses.append({**identity,'desglose':key,'valor':v,
                            **resumen_grupo([r for r in rs if fun(r['ID_POLIGONO'])==v])})
                desgloses.append({**identity,'desglose':'sin24_solo_reporte','valor':'sin_alerta',
                    **resumen_grupo([r for r in rs if r['ID_POLIGONO'] not in alerts])})
    for candidate,base in c['contrastes']:
        for s in ['A','B']:
            for subset in ['todas','sin_respaldo']:
                r=comparar(rows,contexts,candidate,base,s,subset)
                r['elegible_para_promocion_principal'] &= candidate==modelo.CANDIDATO and base=='media_mun__resp_grupo'
                contrasts.append(r)
    csv_guardar(out/'metricas_resumen.csv',summaries);csv_guardar(out/'metricas_repeticiones.csv',repetitions)
    csv_guardar(out/'desgloses.csv',desgloses);guardar_json(out/'contrastes.json',contrasts)
    csv_guardar(out/'contrastes.csv',contrasts)


def comprobar_puerta(root,path):
    exigir(path is not None,'Falta comprobación piloto previa')
    g=json.loads(Path(path).read_text())
    exigir(g['codigo_sha256']==codigos(root) and g['contrato_sha256']==CONTRATO_SHA,'Puerta de otro código/contrato')
    exigir(g['resultado']=='aprobado' and g['selecciones_iguales'] is True,'Pilotos no conciliados')
    for p,h in g['evidencia_sha256'].items():exigir(sha(Path(path).parent/p)==h,'Evidencia piloto alterada')
    for key in ['auditoria_mac.json','auditoria_linux.json']:
        a=json.loads((Path(path).parent/key).read_text())
        exigir(a['resultado']=='aprobado' and a['recalculo_primal_dual_independiente'] is True and a['ajustes']==74,
               'Auditoría piloto insuficiente')
    exigir(g['max_diferencia_predicciones']<=1e-6,'Diferencia piloto fuera de contrato')
    exigir(g['tests_mac']>=13 and g['tests_linux']>=13,'Pruebas previas incompletas')
    return g


def ejecutar(root,out,modo='verificar',confirmar=False,puerta=None):
    exigir(modo in ['verificar','prueba','completa'],'Modo inválido')
    exigir(confirmar is (modo=='completa'),'Completa requiere confirmación explícita')
    root=Path(root).resolve();out=validar_salida(out,root);c,e,old=cargar(root);codes=codigos(root)
    if modo=='completa':
        comprobar_puerta(root,puerta)
        exigir(not subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],cwd=root,text=True),
               'Guardar cambios de código antes de evaluar')
    out.mkdir(parents=True);start=time.monotonic()
    manifest=dict(schema='T15_cuantilica_ejecucion_v1',modo=modo,estado='iniciado',evaluacion_completa=False,
        contrato_sha256=CONTRATO_SHA,codigo_sha256=codes,fuentes_sha256=c['fuentes_sha256'],
        fuente_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),entorno=entorno(),
        predicciones_finales59=0,ganador_T16_congelado=False,ajustes=0,contextos=0,OOF_nuevas=0,
        puerta_sha256=sha(puerta) if puerta else None)
    guardar_json(out/'manifest.json',manifest)
    try:
        preflight(e)
        if modo=='verificar':manifest['estado']='verificado_sin_modelos'
        else:
            contexts=[(s,1,0) for s in ['A','B']] if modo=='prueba' else [(s,r,f) for s in ['A','B'] for r in range(1,6) for f in range(5)]
            rows=[];selections=[]
            with (out/'trazas_ajustes.jsonl').open('x') as traces,(out/'selecciones.jsonl').open('x') as sels,\
                 (out/'predicciones_incrementales.csv').open('x',newline='') as incremental:
                writer=csv.DictWriter(incremental,fieldnames=OOF,lineterminator='\n');writer.writeheader()
                def save(f,v):f.write(json.dumps(v,ensure_ascii=False,allow_nan=False)+'\n');f.flush()
                for n,(s,r,f) in enumerate(contexts,1):
                    identity=dict(escenario=s,repeticion=r,particion=f,candidato=modelo.CANDIDATO)
                    X,y,q=preparar_contexto(e,s,r,f)
                    def emit(t):save(traces,{**t,**identity,'estado':'correcto'});manifest['ajustes']+=1
                    option,scores=modelo.seleccionar(X,y,s,emit)
                    selection={**identity,'elegida':option,'puntuaciones':scores};selections.append(selection);save(sels,selection)
                    m,d=modelo.ajustar(X,y,q,option)
                    emit(dict(etapa='externa',opcion=option,estado_modelo=m.estado(),ids_validacion=list(q.index),
                        consulta=[dict(id_parcela=i,**v.to_dict()) for i,v in d.iterrows()]))
                    new=[]
                    for pid,row in d.iterrows():
                        ctx=e['contextos'][s,r,pid]
                        exigir(ctx['particion']==f and ctx['fuente']==row.fuente,'Contexto incorrecto')
                        new.append(dict(ID_POLIGONO=pid,repeticion=r,particion=f,escenario=s,real=ctx['real'],
                            prediccion=float(row.prediccion),candidato=modelo.CANDIDATO,version=modelo.VERSION,fuente=row.fuente))
                    rows+=new;writer.writerows(new);incremental.flush()
                    manifest.update(contextos=n,OOF_nuevas=len(rows));guardar_json(out/'manifest.json',manifest)
                    print(f'Cuantílica: {n}/{len(contexts)} contextos guardados ({s},{r},{f}).',flush=True)
            if modo=='completa':
                exigir(len(rows)==1380 and len(selections)==50 and manifest['ajustes']==1850,'Presupuesto incumplido')
                rows=old+rows
                quality={r['id_parcela']:r for r in leer_csv(root/'registro/t07/calidad_parcelas.csv')[1]}
                table={k[0]:v for k,v in e['tabla'].items()}
                reportes(rows,e['contextos'],c,out,quality,table)
                freq=[]
                for s in ['A','B']:
                    for option in modelo.OPCIONES:
                        freq.append(dict(escenario=s,opcion=option['nombre'],n_contextos=sum(v['escenario']==s and v['elegida']==option for v in selections)))
                csv_guardar(out/'frecuencia_opciones.csv',freq)
                manifest.update(estado='completa_pendiente_auditoria',evaluacion_completa=True,OOF_reutilizadas=4140)
            else:manifest['estado']='piloto_funcional_no_resultado_global'
            csv_guardar(out/('predicciones_oof.csv' if modo=='completa' else 'oof_parcial_prueba.csv'),rows,OOF)
        exigir(codes==codigos(root),'Código cambió durante ejecución')
        for p,h in c['fuentes_sha256'].items():exigir(sha(root/p)==h,'Fuente cambió durante ejecución: '+p)
    except BaseException as exc:
        manifest.update(estado='fallido',evaluacion_completa=False,error=dict(tipo=type(exc).__name__,mensaje=str(exc)));raise
    finally:
        manifest['tiempo_segundos']=time.monotonic()-start
        manifest['archivos_sha256']={p.name:sha(p) for p in out.iterdir() if p.name!='manifest.json' and p.is_file()}
        guardar_json(out/'manifest.json',manifest)
    return manifest


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--raiz',type=Path,default=RAIZ);p.add_argument('--salida',type=Path,required=True)
    p.add_argument('--modo',choices=['verificar','prueba','completa'],default='verificar');p.add_argument('--confirmar-completa',action='store_true');p.add_argument('--puerta',type=Path)
    a=p.parse_args();print(json.dumps(ejecutar(a.raiz,a.salida,a.modo,a.confirmar_completa,a.puerta),ensure_ascii=False,indent=2))
