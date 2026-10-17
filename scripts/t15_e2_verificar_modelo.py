"""Previa E2: particiones, 16 ajustes algebraicos y H3; sin evaluación de aporte."""
import argparse
import copy
import json
from pathlib import Path
import subprocess
import time
import numpy as np
from scripts import t15_e2_entradas as entradas
from scripts import t15_e2_modelo as modelo
from scripts import t15_e1_modelo as anterior
from scripts.evaluacion_comun_contrato import exigir, sha
from scripts.evaluacion_comun_modelo import divisiones_internas
from scripts.t15_comparaciones_traza import huella

CODIGO=['scripts/t15_e2_entradas.py','scripts/t15_e2_modelo.py',
        'scripts/t15_e2_auditar_modelo.py','scripts/t15_e2_verificar_modelo.py']


def dump(path,obj):
    path.write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+'\n')


def fuentes(root):
    cfg=entradas.read_json(root/entradas.DISENO)
    paths=set(cfg['fuentes_sha256'])|{
        entradas.DISENO,entradas.ENTREGA,'registro/t15_e2_extraccion/atributos_parcela.csv',
        'registro/t15_e2_extraccion/calidad.csv','registro/t15_e2_extraccion/comparacion_plataformas.json',
        'registro/t15_e2_extraccion/auditoria_linux.json','scripts/t15_e1_modelo.py',
        'scripts/t15_e1_ejecutar.py','scripts/t15_e1_contrato.py','scripts/t15_e1_auditar.py',
        'scripts/t15_comparaciones_contrato.py','scripts/t15_comparaciones_traza.py',
        'scripts/t15_ejecutor_reportes.py','registro/t15_contrato/contrato_v1.json',
        'registro/t15_e1/vista_admisibilidad_propuesta.csv','registro/t07/catalogo_base.csv'}
    return {name:sha(root/name) for name in sorted(paths)}


def verificar(root,output):
    root,output=Path(root).resolve(),Path(output).resolve()
    exigir(not output.exists(),'Destino existente: no sobrescribir evidencia')
    exigir(not output.is_relative_to(root) or output.is_relative_to(root/'reports'),'Dentro repo sólo reports')
    datos=entradas.cargar(root);opts=entradas.opciones(datos);modelo.validar_menu(opts)
    pins=fuentes(root);codes={p:sha(root/p) for p in CODIGO}
    output.mkdir(parents=True)
    manifest=dict(schema='E2_previa_modelo_v1',estado='en_proceso',evaluacion_aporte_completa=False,
        ajustes_prueba=0,metricas_aporte_calculadas=0,predicciones_finales59=0,OOF_para_decidir=0,
        codigo_sha256=codes,fuentes_sha256=pins,base_commit=subprocess.check_output(
            ['git','rev-parse','HEAD'],cwd=root,text=True).strip())
    dump(output/'manifest.json',manifest);start=time.monotonic()
    try:
        contexts=[]
        for esc in ['A','B']:
            for rep in range(1,6):
                for fold in range(5):
                    X,y,q=entradas.contexto(datos,esc,rep,fold)
                    divisions=divisiones_internas(X,esc);seen=[]
                    for split in divisions:
                        a,b=set(split.entrenamiento),set(split.validacion)
                        exigir(not a&b and a|b==set(X.index),'Interna fuera de contexto')
                        exigir(not (a|b)&set(q.index),'Validación externa en interna')
                        if esc=='B':exigir(not set(X.loc[list(a),'celda_chirps'])&set(X.loc[list(b),'celda_chirps']),'Celda compartida en B')
                        seen.extend(split.validacion)
                    exigir(len(seen)==len(set(seen))==len(X) and set(seen)==set(X.index),'Cobertura interna')
                    contexts.append(dict(escenario=esc,repeticion=rep,particion=fold,
                        n_train=len(X),n_consulta=len(q),n_internas=len(divisions),
                        ids_train_sha256=huella(sorted(X.index)),ids_consulta_sha256=huella(list(q.index))))
        dump(output/'particiones_verificadas.json',contexts)
        records=[];H3_max=0.;bridge_max=0.;frozen_checks=0
        for esc in ['A','B']:
            X,y,q=entradas.contexto(datos,esc,1,0)
            for window in ['abr_oct','jun_oct']:
                option=next(o for o in opts if o['ventana']==window and o['lambda_reg']==.1)
                for mode in [*entradas.MODOS,'referencia']:
                    columns=option['columnas'] if mode!='referencia' else []
                    lam=.1 if columns else None
                    m=modelo.ModeloE2(columns,lam,mode).fit(X,y);state=m.estado();d=m.predict_with_details(q)
                    expected=anterior.ModeloE1(columns,lam,modelo.MAPA[mode]).fit(X,y)
                    delta=float(np.max(np.abs(d.prediccion.to_numpy()-expected.predict(q))))
                    exigir(delta<=1e-12,'Puente con núcleo existente no coincide');bridge_max=max(bridge_max,delta)
                    # Freeze state: queries cannot update scale, centers, medians or fitted pools.
                    initial=huella(state)
                    m.predict_with_details(q.iloc[::-1]);exigir(huella(m.estado())==initial,'Aprendizaje durante predict')
                    frozen_checks+=1
                    if columns:
                        # Only numerical identity, not a performance score on training.
                        corrections=m.predict_with_details(X).correccion
                        means=corrections.groupby(X.municipio).mean().to_numpy()
                        delta=float(np.max(np.abs(means)));H3_max=max(H3_max,delta)
                        exigir(delta<=1e-12,'H3: media de corrección municipal no nula')
                        exigir(state['columnas']==columns+(['e1_ndwi_post15_45'] if mode=='E12' else [])+
                               (['e1_no_utilizable'] if mode in ['E12','E2Q'] else []),'Indicador omitido o sin centrar')
                    records.append(dict(escenario=esc,repeticion=1,particion=0,ventana=window,modo=mode,
                        columnas_base=columns,lambda_reg=lam,ids_entrenamiento=list(sorted(X.index)),
                        ids_consulta=list(q.index),estado_modelo=state,
                        consulta=[dict(id_parcela=pid,**row.to_dict()) for pid,row in d.iterrows()]))
        with (output/'ajustes_verificacion.jsonl').open('x') as f:
            for r in records:f.write(json.dumps(r,ensure_ascii=False,allow_nan=False)+'\n')
        summary=dict(resultado='aprobado',contextos_verificados=50,internas_verificadas=200,
            opciones_por_procedimiento=8,dimensiones={'E2':8,'E12':10,'E2Q':9},
            registros_ajustes=16,ajustes_adaptador_Ridge=12,ajustes_adaptador_referencia=4,
            ajustes_puente_antecedente_Ridge=12,ajustes_puente_antecedente_referencia=4,
            H3_max_media_correccion_municipal=H3_max,puente_max_diferencia=bridge_max,
            predict_sin_cambiar_estado=frozen_checks,evalua_rendimiento=False,
            consulta_y_no_usada_para_elegir=True,predicciones_finales59=0,
            presupuesto_evaluacion_futura=datos['diseno']['presupuesto'])
        dump(output/'resumen.json',summary)
        exigir(pins==fuentes(root) and codes=={p:sha(root/p) for p in CODIGO},'Código o datos cambiaron durante comprobación')
        manifest.update(estado='verificacion_tecnica_completa',ajustes_prueba=32,
            segundos=time.monotonic()-start,archivos_sha256={p.name:sha(p) for p in output.iterdir() if p.name!='manifest.json'})
        dump(output/'manifest.json',manifest)
        return manifest
    except Exception as exc:
        manifest.update(estado='fallido',error=str(exc),segundos=time.monotonic()-start)
        dump(output/'manifest.json',manifest);raise


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--raiz',type=Path,default=entradas.ROOT)
    p.add_argument('--salida',type=Path,required=True);a=p.parse_args()
    print(json.dumps(verificar(a.raiz,a.salida),ensure_ascii=False,indent=2))
