"""Registra E2 antes de evaluación de aporte; no ejecuta ni autoriza la corrida completa."""
import argparse
import copy
import json
from pathlib import Path
from scripts import t15_e2_entradas as entradas
from scripts import t15_e2_verificar_modelo as previa
from scripts.evaluacion_comun_contrato import exigir, sha


def validar(r):
    exigir(r['schema']=='agrocebada_E2_ejecucion_v1','Otro registro')
    exigir(r['evaluacion_completa_autorizada'] is False and r['predicciones_finales59_autorizadas'] is False,
           'No convertir registro técnico en autorización de evaluación')
    exigir(r['metodo']['version']=='comun-centrado-loo-v3' and r['metodo']['lambda']==[.01,.1,1.,10.]
           and r['metodo']['ventanas']==['abr_oct','jun_oct'] and r['metodo']['alpha']=='n_entrenamiento*lambda', 'Método cambiado')
    exigir([(p['modo'],p['dimension'],p['promocion']) for p in r['procedimientos']]==
           [('E2',8,True),('E12',10,True),('E2Q',9,False)],'Cartera o promoción control cambiadas')
    exigir(len(r['opciones_base'])==8 and all(len(o['columnas'])==8 for o in r['opciones_base']), 'Menú no acotado')
    from scripts.t15_e2_modelo import validar_menu
    validar_menu(r['opciones_base'])
    exigir(r['presupuesto']['trazas_sin_cache']==5550 and r['presupuesto']['OOF_total']==8280 and
           r['presupuesto']['Ridge_internos']==4800 and r['presupuesto']['ajustes_externos']==150 and
           r['presupuesto']['OOF_nuevas']==4140 and r['presupuesto']['OOF_reutilizadas']==4140,'Presupuesto incoherente')
    exigir(r['decision']['T03']['promocion']==dict(dMAE_max=-.01,IC95_superior_max_exclusivo=0,
           repeticiones_mejoran_min=4,dRMSE_max=.01),'Regla T03 alterada')
    family=r['decision']['guardia_familia_E2']
    exigir(family['candidatos']==['E2','E12'] and family['percentiles']==[1.25,98.75], 'Protección familiar alterada')
    exigir(r['poblacion']==dict(total=197,etiquetadas=138,reservadas=59,excluir_por_error=False,
                              corte='2025-10-31'),'Población alterada')
    exigir(r['referencia_sola_compite'] is True and r['tolerancia_OOF_mismo_CSV']==1e-12,'Referencia/tolerancia cambiada')
    exigir(len(r['contrastes'])==7 and r['aprendizaje_solo_train'] is True and r['H3_centrar_todas_columnas'] is True,
           'Protección H3/filtración ausente')
    return True


def registrar(root,run,audit,output):
    root,run,audit,output=map(Path,[root,run,audit,output])
    exigir(not output.exists(),'No sobrescribir registro de ejecución')
    d=entradas.cargar(root);m=entradas.read_json(run/'manifest.json');a=entradas.read_json(audit)
    exigir(m['estado']=='verificacion_tecnica_completa' and not m['evaluacion_aporte_completa'],'Falta previa')
    exigir(a['resultado']=='aprobado' and a['ajustes_recalculados']==16 and
           a['manifest_sha256']==sha(run/'manifest.json'),'Auditoría no vinculada')
    exigir(a['codigo_auditor_sha256']==sha(root/'scripts/t15_e2_auditar_modelo.py'),'Auditoría de otro código')
    for name,h in m['codigo_sha256'].items():exigir(sha(root/name)==h,'Código cambió tras previa')
    for name,h in m['fuentes_sha256'].items():exigir(sha(root/name)==h,'Fuente cambió tras previa')
    for name,h in m['archivos_sha256'].items():exigir(sha(run/name)==h,'Prueba alterada')
    c=d['diseno']
    r=dict(schema='agrocebada_E2_ejecucion_v1',fecha='2026-10-16',responsable='Dani',
        estado='registrado_antes_de_evaluacion_aporte',
        alcance_autorizado='Dani solicita adaptación, comprobación H3 y registro; sin evaluación completa',
        evaluacion_completa_autorizada=False,predicciones_finales59_autorizadas=False,
        contrato_historico_inmutable=entradas.DISENO_SHA,entrega_E2_sha256=entradas.ENTREGA_SHA,
        poblacion=dict(total=197,etiquetadas=138,reservadas=59,excluir_por_error=False,corte='2025-10-31'),
        metodo=copy.deepcopy(d['antecedente']['metodo']),
        procedimientos=[dict(modo=p['id'],candidato='comun_centrado_loo_v3_'+p['id'],
                              dimension=c['modelo']['dimensiones'][p['id']],promocion=p['promocion'],formula=p['formula'])
                         for p in c['procedimientos']],opciones_base=entradas.opciones(d),
        contrastes=copy.deepcopy(c['contrastes']),presupuesto=copy.deepcopy(c['presupuesto']),
        decision=copy.deepcopy(c['decision']),referencia_sola_compite=True,aprendizaje_solo_train=True,
        H3_centrar_todas_columnas=True,tolerancia_OOF_mismo_CSV=1e-12,
        preparacion_E2=dict(columnas=list(entradas.E2),imputacion=False,union='1_a_1_por_ID',
                           calidad_como_predictor=False,geometria_original=True,estatico_no_multiplica_filas=True),
        preparacion_E1='idéntica a E1-Q-preparacion-v1; mediana sólo train, indicador fijo y apagado si no hay admisibles',
        comparadores_reutilizados=['comun_centrado_loo_v3_S','comun_centrado_loo_v3_E1','media_mun__resp_grupo'],
        fuentes_sha256=m['fuentes_sha256'],codigo_sha256={**m['codigo_sha256'],
            'scripts/t15_e2_registrar.py':sha(__file__),'tests/test_t15_e2_modelo.py':sha(root/'tests/test_t15_e2_modelo.py')},
        previa_sha256=sha(run/'manifest.json'),auditoria_previa_sha256=sha(audit),
        exposicion_previa=[*c['exposicion_previa'],
            '16 registros técnicos en A/B repetición1 partición0,lambda0.1,dosventanas;32ajustes incluyendo puente;sin MAE externo ni selección por aporte',
            'Prueba de selección interna A/E2 contra selector v3: mismo resultado; no se usó validación externa para cambiar menú'],
        limitaciones=['una_campania','disponibilidad_bytes_2025_no_acreditada','datum_vertical_no_acreditado',
                      'sin_garantia_baja_MAE','no_revision_humana_externa_atribuida'],
        siguientes_puertas=['pruebas_y_auditoria_Mac_Linux_mismo_registro',
             'ejecutor_y_reportes_E2_con_guardia_familia_verificados','solicitud_explicita_evaluacion_completa'])
    validar(r)
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(r,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    return r


def verificar_registro(root,path):
    root=Path(root);r=entradas.read_json(path);validar(r)
    d=entradas.cargar(root);c=d['diseno']
    for name,expected in [('decision',c['decision']),('presupuesto',c['presupuesto']),
                          ('contrastes',c['contrastes']),('opciones_base',entradas.opciones(d)),
                          ('metodo',d['antecedente']['metodo'])]:
        exigir(r[name]==expected,'Registro no coincide con diseño: '+name)
    exigir(r['entrega_E2_sha256']==entradas.ENTREGA_SHA and r['contrato_historico_inmutable']==entradas.DISENO_SHA,
           'Registro vinculado a otros datos')
    exigir(r['fuentes_sha256']==previa.fuentes(root),'Inventario de fuentes diferente')
    paths=previa.CODIGO+['scripts/t15_e2_registrar.py','tests/test_t15_e2_modelo.py']
    exigir(r['codigo_sha256']=={p:sha(root/p) for p in paths},'Código cambiado tras registro')
    return dict(resultado='aprobado',registro_sha256=sha(path),
                fuentes=len(r['fuentes_sha256']),codigo=len(paths),evaluacion_autorizada=False)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--raiz',type=Path,default=entradas.ROOT)
    p.add_argument('--previa',type=Path,required=True);p.add_argument('--auditoria',type=Path,required=True)
    p.add_argument('--salida',type=Path,required=True);a=p.parse_args()
    print(json.dumps(registrar(a.raiz,a.previa,a.auditoria,a.salida),ensure_ascii=False,indent=2))
