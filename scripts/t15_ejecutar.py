"""T15: verificar, comprobar un contexto o ejecutar el contrato principal completo."""
import argparse
import csv
import hashlib
import importlib.metadata
import json
import platform
from pathlib import Path
import subprocess
import time

try:
    import resource
except ImportError:  # Windows local: la evaluación sigue disponible; Docker informa memoria.
    resource=None

from scripts import evaluacion_comun_centrado_loo as v3
from scripts import evaluacion_comun_contrato as comun
from scripts import t15_comparaciones_contrato as contrato
from scripts import t15_comparaciones_traza as traza
from scripts import t15_ejecutor_reportes as reportes
from scripts import t15_registro_operativo as registro
from scripts.evaluacion_comun_modelo import preparar_contexto

REFERENCIA='media_mun__resp_grupo'
OOF=['ID_POLIGONO','repeticion','particion','escenario','real','prediccion','candidato','version','fuente']


def guardar_json(path, value):
    path=Path(path);tmp=path.with_suffix(path.suffix+'.tmp')
    tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    tmp.replace(path)


def entorno():
    return dict(python=platform.python_version(),sistema=platform.system(),arquitectura=platform.machine(),
                librerias={p:importlib.metadata.version(p) for p in ['numpy','pandas','scikit-learn','scipy']})


def validar_salida(path, raiz):
    path,raiz=Path(path).resolve(),Path(raiz).resolve()
    comun.exigir(not path.exists(), 'Destino existente: usar una carpeta nueva')
    comun.exigir(not path.is_relative_to(raiz) or path.is_relative_to(raiz/'reports'),
                 'Dentro del repo sólo se permiten salidas en reports/')
    # No usar una carpeta que contenga al repo como destino.
    comun.exigir(not raiz.is_relative_to(path), 'Destino contiene las fuentes')
    return path


def ejecutar_contexto(entradas,procedimientos,escenario,rep,fold,emitir,*,al_seleccionar=None,al_estado=None):
    """El selector sólo recibe y de entrenamiento; real externo se une al finalizar."""
    X,y,te=preparar_contexto(entradas,escenario,rep,fold)
    elegibles=tuple(bool(v) for v in te.municipio.isin(X.municipio))
    identidad=dict(escenario=escenario,repeticion=rep,particion=fold)
    filas=[];selecciones=[];estados=[]

    def ajustar(opcion,candidato):
        try:
            model,details,t=traza.ajustar_y_trazar(X,y,te,opcion,elegibles)
        except traza.ErrorAjuste as exc:
            emitir({**exc.traza,**identidad,'candidato':candidato,'etapa':'externa'})
            raise
        emitir({**t,**identidad,'candidato':candidato,'etapa':'externa'})
        estado={**identidad,'candidato':candidato,'estado_modelo':model.estado()}
        estados.append(estado)
        if al_estado is not None:al_estado(estado)
        for pid,row in details.iterrows():
            context=entradas['contextos'][escenario,rep,pid]
            comun.exigir(int(context['particion'])==fold and row.fuente==context['fuente'],
                         'Contexto OOF o fuente externa distintos')
            filas.append(dict(ID_POLIGONO=pid,repeticion=rep,particion=fold,escenario=escenario,
                real=context['real'],prediccion=float(row.prediccion),candidato=candidato,
                version=v3.VERSION,fuente=row.fuente))

    ajustar(dict(nombre='referencia_sola',columnas=[],lambda_reg=None,ventana='estatica'),REFERENCIA)
    for p in procedimientos:
        opciones=[dict(o,nombre=f"{o['ventana']}__lambda_{o['lambda_reg']:g}") for o in p['opciones']]
        def interna(t):emitir({**t,**identidad,'candidato':p['candidato'],'etapa':'interna'})
        seleccion=traza.seleccionar_con_traza(X,y,opciones,escenario,al_ajuste=interna)
        opcion=seleccion['elegida']
        elegida={**identidad,'candidato':p['candidato'],'version':v3.VERSION,
            'nombre_opcion':opcion['nombre'],'referencia_sola':not opcion['columnas'],
            'lambda_reg':opcion['lambda_reg'],'ventana':opcion['ventana'],
            'columnas':opcion['columnas'],'puntuaciones':seleccion['puntuaciones'],
            'n_ajustes_internos':seleccion['n_ajustes']}
        selecciones.append(elegida)
        if al_seleccionar is not None:al_seleccionar(elegida)
        ajustar(opcion,p['candidato'])
    return filas,selecciones,estados


def ejecutar(raiz,salida,modo='verificar',*,confirmar_completa=False,codigo='G',escenario='A',rep=1,fold=0):
    comun.exigir(modo in ['verificar','prueba','completa'], 'Modo desconocido')
    comun.exigir(modo!='completa' or confirmar_completa is True,
                 'Evaluación completa requiere modo y confirmación explícitos')
    comun.exigir(modo=='completa' or confirmar_completa is False,
                 'Confirmación completa incompatible con modo de comprobación')
    raiz=Path(raiz).resolve();c,e=contrato.cargar(raiz)
    operativo=registro.cargar(raiz,c)
    verificacion=contrato.preflight(e)
    comun.exigir(escenario in ['A','B'] and type(rep) is int and 1<=rep<=5 and
                 type(fold) is int and 0<=fold<=4, 'Contexto de prueba inválido')
    procedimientos=c['principal']['procedimientos']
    if modo=='prueba':
        procedimientos=[p for p in procedimientos if ''.join(p['bloques'])==codigo]
        comun.exigir(len(procedimientos)==1, 'Procedimiento de prueba no incluido en el principal')
    if modo=='completa':
        # Exigir un registro de código limpio antes de cualquier modelo completo.
        dirty=subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],cwd=raiz,text=True)
        comun.exigir(not dirty, 'Registrar cambios de código antes de evaluación completa')
    salida=validar_salida(salida,raiz);salida.mkdir(parents=True)
    inicio=time.monotonic()
    manifest=dict(schema='agrocebada_T15_ejecutor_v1',modo=modo,estado='en_curso',
        evaluacion_completa=False,version=v3.VERSION,contrato_sha256=contrato.SHA_CONTRATO,
        registro_operativo_sha256=registro.SHA_REGISTRO,
        fuente_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=raiz,text=True).strip(),
        entorno=entorno(),fuentes_sha256=c['fuentes_sha256'],codigo_sha256=operativo['codigo_sha256'],
        control_calidad_sha256=operativo['control_calidad_sha256'],
        modelos_para_59=0,ganador_T16_congelado=False,cierre=operativo['cierre'],
        contadores=dict(ajustes_internos=0,Ridge_internos=0,ajustes_externos=0,Ridge_externos=0))
    guardar_json(salida/'manifest.json',manifest)
    handles=[]
    try:
        guardar_json(salida/'preflight.json',verificacion)
        if modo=='verificar':
            manifest.update(estado='verificado_sin_modelos',contextos_ejecutados=0)
        else:
            logs=(salida/'trazas_ajustes.jsonl').open('x',encoding='utf-8');handles.append(logs)
            choices=(salida/'selecciones.jsonl').open('x',encoding='utf-8');handles.append(choices)
            states=(salida/'estados_modelos.jsonl').open('x',encoding='utf-8');handles.append(states)
            def emitir(t):
                logs.write(json.dumps(t,ensure_ascii=False,allow_nan=False)+'\n');logs.flush()
                if t['estado']=='correcto':
                    clase='internos' if t['etapa']=='interna' else 'externos'
                    manifest['contadores']['ajustes_'+clase]+=1
                    manifest['contadores']['Ridge_'+clase]+=int(t['lambda_reg'] is not None)
            contextos=[(escenario,rep,fold)] if modo=='prueba' else [
                (s,r,f) for s in ['A','B'] for r in range(1,6) for f in range(5)]
            rows=[];todas_selecciones=[]
            nombre_oof='oof_parcial_prueba.csv' if modo=='prueba' else 'predicciones_oof.csv'
            with (salida/nombre_oof).open('x',encoding='utf-8',newline='') as f:
                writer=csv.DictWriter(f,fieldnames=OOF,lineterminator='\n');writer.writeheader()
                for n,(s,r,p) in enumerate(contextos,1):
                    def persistir(stream,value):
                        stream.write(json.dumps(value,ensure_ascii=False,allow_nan=False)+'\n');stream.flush()
                    nuevas,sel,estados=ejecutar_contexto(e,procedimientos,s,r,p,emitir,
                        al_seleccionar=lambda v:persistir(choices,v),al_estado=lambda v:persistir(states,v))
                    writer.writerows(nuevas);f.flush();rows.extend(nuevas);todas_selecciones.extend(sel)
                    manifest.update(contextos_ejecutados=n,filas_OOF=len(rows))
                    guardar_json(salida/'manifest.json',manifest)
                    print(f'T15 {modo}: contexto {n}/{len(contextos)} guardado ({s}, repetición {r}, partición {p}).',flush=True)
            if modo=='prueba':
                manifest.update(estado='comprobacion_funcional_parcial',
                    limites='Un contexto/un candidato: no estima desempeño completo ni selecciona ventanas o modelos finales.')
            else:
                frecuencias=v3.frecuencia_referencia_sola(todas_selecciones)
                comun.exigir(len(frecuencias)==16 and all(r['estado']=='completo' for r in frecuencias),
                             'Selecciones incompletas o duplicadas')
                comun.exigir(len(rows)==12420,'OOF no completa las 12420 claves')
                calidad={r['id_parcela']:r for r in comun.leer_csv(raiz/'registro/t07/calidad_parcelas.csv')[1]}
                tabla={k[0]:v for k,v in e['tabla'].items()}
                manifest['reportes']=reportes.producir(rows,e['contextos'],c,calidad,tabla,salida)
                reportes.csv_guardar(salida/'frecuencia_referencia_sola.csv',frecuencias)
                comun.exigir(manifest['contadores']['Ridge_internos']==12000 and
                             manifest['contadores']['ajustes_internos']==13600 and
                             manifest['contadores']['ajustes_externos']==450 and
                             manifest['contadores']['Ridge_externos']<=400,
                             'Conteo de ajustes incompleto o presupuesto excedido')
                manifest.update(estado='completa_verificada',evaluacion_completa=True)
    except BaseException as exc:
        manifest.update(estado='fallido',evaluacion_completa=False,
                        error=dict(tipo=type(exc).__name__,mensaje=str(exc)))
        raise
    finally:
        for h in handles:h.close()
        manifest['tiempo_segundos']=time.monotonic()-inicio
        # ru_maxrss está en bytes en macOS y KiB en Linux.
        rss=None if resource is None else resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        manifest['memoria_maxima_proceso_MiB']=None if rss is None else rss/(1024**2 if platform.system()=='Darwin' else 1024)
        manifest['memoria_estado']='no_disponible_en_este_sistema' if rss is None else 'medida_ru_maxrss'
        manifest['archivos_sha256']={p.name:hashlib.sha256(p.read_bytes()).hexdigest()
                                     for p in sorted(salida.iterdir()) if p.is_file() and p.name!='manifest.json'}
        guardar_json(salida/'manifest.json',manifest)
    return manifest


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--raiz',type=Path,default=comun.RAIZ)
    p.add_argument('--salida',type=Path,required=True)
    p.add_argument('--modo',choices=['verificar','prueba','completa'],default='verificar')
    p.add_argument('--confirmar-evaluacion-completa',action='store_true')
    p.add_argument('--procedimiento',default='G');p.add_argument('--escenario',choices=['A','B'],default='A')
    p.add_argument('--repeticion',type=int,default=1);p.add_argument('--particion',type=int,default=0)
    a=p.parse_args()
    try:
        r=ejecutar(a.raiz,a.salida,a.modo,confirmar_completa=a.confirmar_evaluacion_completa,
                   codigo=a.procedimiento,escenario=a.escenario,rep=a.repeticion,fold=a.particion)
    except (ValueError,OSError,KeyError,TypeError) as exc:p.exit(1,'T15 detenido: '+str(exc)+'\n')
    print(json.dumps({k:r[k] for k in ['modo','estado','evaluacion_completa','contextos_ejecutados','contadores']},ensure_ascii=False,indent=2))


if __name__=='__main__':main()
