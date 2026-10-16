"""Valida la propuesta E1 y clasifica soporte; no imputa, ajusta ni predice."""
import argparse
import csv
from datetime import date,timedelta
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import tempfile

ROOT=Path(__file__).resolve().parents[1]
CONFIG='registro/t15_e1/contrato_propuesto_v1.json'
VALUE='e1_ndwi_post15_45'
FLAG='e1_no_utilizable'


def require(ok,message):
    if not ok:raise ValueError(message)


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_json(path):
    def unique(pairs):
        out={}
        for k,v in pairs:
            require(k not in out,'Clave JSON duplicada')
            out[k]=v
        return out
    def invalid(value):raise ValueError('Constante JSON no finita')
    return json.loads(Path(path).read_text(encoding='utf-8'),object_pairs_hook=unique,parse_constant=invalid)


def validate(contract):
    require(contract.get('schema')=='agrocebada_E1_contrato_propuesto_v1','Esquema incompatible')
    require(contract.get('version')=='E1-contrato-v1','Versión incompatible')
    require(contract.get('estado')=='propuesto_para_revision','Estado no autorizado')
    require(contract.get('ejecutable') is False and contract.get('inscripcion_experimental_aceptada') is False,
            'No se puede habilitar ejecución con esta propuesta')
    pop=contract['poblacion']
    require(all(type(pop[k]) is int for k in ['total','etiquetadas','reservadas']),'Conteos enteros requeridos')
    require([pop[k] for k in ['total','etiquetadas','reservadas']]==[197,138,59] and
            pop['eliminar_filas_por_E1'] is False,'No cambiar población')
    rule=contract['observacion']
    require(rule['sensor']=='Sentinel-2' and rule['corte']=='2025-10-31','Sensor/corte incompatible')
    require(rule['ventanas']==['abr_oct','jun_oct'] and rule['intervalo_dias_inclusivos']==[15,45],
            'No cambiar ventana observacional')
    require(rule['min_fechas_distintas_post']==2 and rule['min_capturas_NDVI']==5 and rule['umbral_nubosidad']==5,
            'Soporte distinto de D1')
    require(rule['no_interpolacion'] is True and rule['no_extrapolacion'] is True,'No inventar observaciones')
    require(contract['admisibilidad']['politica_principal']=='solo_calculable_e_intervalo_nominal_no_truncado',
            'Política de calidad diferente')
    require(contract['admisibilidad']['sin_dato']=='vacio_no_cero','Vacío no es cero')
    require(contract['columnas']['candidata']==VALUE and contract['columnas']['indicador_fijo']==FLAG,
            'Nombres de columnas incompatibles')
    prep=contract['preprocesamiento']
    require(prep['implementado'] is False,'La propuesta no implementa un modelo')
    require(prep['aprendizaje']=='solo_entrenamiento_del_fit_interno_o_externo','Fuga en aprendizaje propuesto')
    require(prep['mediana']=='global_de_filas_admisibles_en_entrenamiento_no_197_ni_59',
            'Mediana sólo en entrenamiento')
    require(prep['indicador']=='siempre_una_columna_incluso_sin_faltantes_en_fit','Indicador debe ser fijo')
    require(prep['conteo_alpha']=='todas_filas_entrenamiento_no_solo_admisibles','n debe conservar todas las filas')
    require(contract['comparaciones']['columnas_por_opcion']=={'S':5,'Q':6,'E1':7},'Control o columnas alteradas')
    require(contract['comparaciones']['Q']=='control_diagnostico_no_promocion_automatica','Control no es ganador adicional')
    search=contract['busqueda']
    require(search['ventanas']==['abr_oct','jun_oct'] and search['lambda']==[.01,.1,1,10] and
            search['alpha']=='n_entrenamiento*lambda','Búsqueda incompatible')
    require(search['referencia_sola'] is True,'Falta referencia sola')
    require(search['opciones_con_variables_por_procedimiento']==8 and search['internas_por_contexto']==4
            and search['contextos_externos']==50,'Presupuesto base incorrecto')
    budget=contract['presupuesto']
    require(budget['aceptado'] is False and budget['no_ejecutar_sin_registro_y_revision'] is True,
            'Presupuesto todavía no aceptado')
    require(budget['T15_principal_sin_cambios']=={'procedimientos':8,'opciones':60,'Ridge_internos_max':12000,
                                               'Ridge_externos_max':400},'No ampliar T15 principal')
    require(budget['E1_mas_control_propuesto']=={'procedimientos_nuevos':2,'opciones':16,
                                              'Ridge_internos_max':3200,'Ridge_externos_max':100},
            'Contabilizar Q y E1 por separado')
    require(budget['incremento_solo_Q']=={'opciones':8,'Ridge_internos_max':1600,'Ridge_externos_max':50},
            'Incremento Q incorrecto')
    return {'estado':'propuesta_valida_no_ejecutable','procesamiento_modelo_implementado':False}


def require_execution(contract):
    validate(contract)
    raise RuntimeError('Contrato propuesto: no ejecutar modelos ni selección')


def read_csv(path):
    with Path(path).open(encoding='utf-8-sig',newline='') as f:
        r=csv.DictReader(f);fields=r.fieldnames or []
        require(fields and len(fields)==len(set(fields)),'Cabecera vacía o duplicada')
        rows=list(r)
    require(all(None not in r and all(v is not None for v in r.values()) for r in rows),'CSV no rectangular')
    return rows


def boolean(value,nullable=False):
    if nullable and value=='':return None
    require(value in {'True','False'},'Booleano CSV inválido')
    return value=='True'


def finite(value):
    if value=='':return None
    try:n=float(value)
    except (ValueError,TypeError) as exc:raise ValueError('Índice no numérico') from exc
    require(math.isfinite(n),'Índice no finito')
    return n


def classify(row):
    require(row['ventana'] in {'abr_oct','jun_oct'},'Ventana desconocida')
    require(row['id_parcela'] and row['municipio'],'Identidad vacía')
    require(row['conjunto'] in {'ENTRENAMIENTO','PREDICCION'},'Conjunto desconocido')
    calc=boolean(row['calculable']);trunc=boolean(row['intervalo_truncado'],nullable=True)
    try:npost=int(row['n_fechas_post']);ncap=int(row['n_capturas'])
    except (ValueError,TypeError) as exc:raise ValueError('Conteo no entero') from exc
    require(npost>=0 and ncap>=0,'Conteo negativo')
    value=finite(row['contraste_ndwi']);anchor=finite(row['ndwi_ancla']);postmean=finite(row['ndwi_media_post'])
    peak=date.fromisoformat(row['fecha_maximo']) if row['fecha_maximo'] else None
    cutoff=date(2025,10,31);start=date(2025,4 if row['ventana']=='abr_oct' else 6,1)
    if peak:
        require(start<=peak<=cutoff,'Máximo fuera de ventana/corte')
        require(trunc is not None and trunc==(peak+timedelta(days=45)>cutoff),'Truncamiento contradictorio')
    else:require(ncap<5 and not calc,'Falta máximo con soporte suficiente')
    dates=[date.fromisoformat(d) for d in row['fechas_post'].split(';') if d]
    require(len(dates)==npost and len(dates)==len(set(dates)),'Fechas posteriores duplicadas o conteo distinto')
    require(not dates or peak is not None,'Fechas sin ancla temporal')
    if peak:
        require(all(peak+timedelta(days=15)<=d<=min(peak+timedelta(days=45),cutoff) for d in dates),
                'Observación posterior fuera de intervalo/corte')
    require(calc==(ncap>=5 and npost>=2 and anchor is not None),'Calculabilidad contradictoria')
    if calc:
        require(value is not None and postmean is not None and peak is not None,'Cálculo marcado válido sin valor')
        require(-2<=value<=2 and abs(value-(postmean-anchor))<=1e-12,'Contraste no reproduce media menos ancla')
    else:require(value is None,'No calculable no puede tener un valor')
    admitted=calc and trunc is False
    state='admisible_completo' if admitted else 'calculable_truncado_no_admitido' if calc else 'no_calculable'
    return {'id_parcela':row['id_parcela'],'municipio':row['municipio'],'conjunto':row['conjunto'],
            'ventana':row['ventana'],'estado_E1':state,'valor_observado_D1':row['contraste_ndwi'],
            VALUE:row['contraste_ndwi'] if admitted else '',FLAG:0 if admitted else 1,
            'intervalo_truncado':row['intervalo_truncado'],'n_fechas_post':npost,
            'fecha_maximo':row['fecha_maximo'],'motivo_D1':row['motivo'],'conservar_fila':True}


def population(rows):
    keys=[(r['id_parcela'],r['ventana']) for r in rows]
    require(len(keys)==len(set(keys))==394,'Perfiles incompletos o duplicados')
    for window in ['abr_oct','jun_oct']:
        sub=[r for r in rows if r['ventana']==window]
        require(len(sub)==197 and sum(r['conjunto']=='ENTRENAMIENTO' for r in sub)==138 and
                sum(r['conjunto']=='PREDICCION' for r in sub)==59,'Población 197/138/59 requerida')
    a={r['id_parcela']:(r['municipio'],r['conjunto']) for r in rows if r['ventana']=='abr_oct'}
    b={r['id_parcela']:(r['municipio'],r['conjunto']) for r in rows if r['ventana']=='jun_oct'}
    require(a==b,'IDs/metadatos distintos entre ventanas')


def write_csv(path,rows):
    with Path(path).open('w',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');writer.writeheader();writer.writerows(rows)


def run(output,root=ROOT):
    output=Path(output);root=Path(root)
    require(not output.exists(),'Destino existente: usar uno nuevo')
    c=read_json(root/CONFIG);validate(c)
    for key in ['perfil','diseno','manifest']:
        require(sha(root/c['fuente'][key])==c['fuente'][key+'_sha256'],'Fuente D1 distinta: '+key)
    original=read_csv(root/c['fuente']['perfil']);population(original)
    view=[classify(row) for row in original]
    summary=[]
    for window in ['abr_oct','jun_oct']:
        for group in ['todas','ENTRENAMIENTO','PREDICCION']:
            sub=[r for r in view if r['ventana']==window and(group=='todas' or r['conjunto']==group)]
            summary.append({'ventana':window,'conjunto':group,'n_parcelas':len(sub),
                            'admisibles_completos':sum(r['estado_E1']=='admisible_completo' for r in sub),
                            'calculables_truncados_no_admitidos':sum(r['estado_E1']=='calculable_truncado_no_admitido' for r in sub),
                            'no_calculables_D1':sum(r['estado_E1']=='no_calculable' for r in sub),
                            'no_utilizables_como_E1_observado':sum(r[FLAG] for r in sub),'filas_eliminadas':0})
    output.parent.mkdir(parents=True,exist_ok=True)
    temp=Path(tempfile.mkdtemp(prefix='.E1-contrato-',dir=output.parent))
    try:
        write_csv(temp/'vista_admisibilidad_propuesta.csv',view)
        write_csv(temp/'resumen_admisibilidad.csv',summary)
        m={'estado':'propuesta_validada_sin_ejecucion','contrato_sha256':sha(root/CONFIG),
           'perfil_D1_sha256':c['fuente']['perfil_sha256'],'codigo_sha256':sha(Path(__file__)),
           'archivos_sha256':{p.name:sha(p) for p in temp.iterdir()},'valores_imputados':0,
           'transformadores_ajustados':0,'modelos_ajustados':0,'nuevas_predicciones59':0,
           'integracion_T07':False,'revision_humana':'pendiente'}
        (temp/'manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        require(not output.exists(),'El destino apareció durante la escritura')
        os.rename(temp,output)
    except BaseException:
        shutil.rmtree(temp,ignore_errors=True);raise
    return m


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--salida',type=Path,required=True)
    args=ap.parse_args();print(json.dumps(run(args.salida),ensure_ascii=False,indent=2))


if __name__=='__main__':main()
