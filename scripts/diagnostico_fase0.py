"""Fase 0 del diagnóstico: integridad, reglas y alcance; no ajusta modelos.

Entradas Git fijadas y originales inmutables. El ledger completo queda en una
salida local; PUBLICABLES identifica sólo la evidencia compacta para revisión.
"""
import argparse
from collections import defaultdict
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import re
import tempfile

from scripts.diagnostico_fuentes import exigir,json_estricto,hash_archivo,ruta_segura,preparar

RAIZ=Path(__file__).resolve().parents[1]
DISENO='registro/diagnostico/fase0_diseno.json'
FUENTES='registro/diagnostico/fase0_fuentes.json'
DISENO_SHA='90f2789e1f385967bfa51beb1d7944f6ced2231f48239aa88af6b93dbbca455f'
FUENTES_SHA='f8cf1e2bc8b088d925acdff9693707d1fd513ad535ec32bc8d145995df55132a'
ATOL=1e-9
TABLA='registro/t07/tabla_comun.csv'
PART='registro/t03/particiones.csv'
OOF_BASE='registro/t03/predicciones_oof_referencias_media_mun__resp_grupo.csv'
PUBLICABLES=['inventario_fuentes.csv','compatibilidad_procedimientos.csv','mascaras_contextos.csv',
             'casos_preseleccionados.csv','controles_preseleccionados.csv',
             'preguntas_y_entregables.csv','alcance_temporal.csv','manifest.json']


def csv_completo(path,permitir_vacio=False):
    path=Path(path);exigir(path.is_file() and not path.is_symlink(),'Entrada no regular')
    exigir(path.stat().st_nlink==1 and path.stat().st_size<=64*1024*1024,'Entrada excede contrato de lectura')
    with path.open(encoding='utf-8-sig',newline='') as f:
        reader=csv.DictReader(f);header=reader.fieldnames
        exigir(header and len(header)==len(set(header)) and len(header)<=160,'Cabecera duplicada/inválida')
        rows=[]
        for row in reader:
            exigir(None not in row and all(v is not None for v in row.values()),'CSV no rectangular')
            rows.append(row);exigir(len(rows)<=250000,'CSV excede límite; no validar prefijo parcial')
    exigir(rows or permitir_vacio,'CSV vacío obligatorio');return rows


def numero(text,name):
    try:v=float(text)
    except (ValueError,TypeError):raise ValueError('Número ausente/inválido: '+name)
    exigir(math.isfinite(v),'Número no finito: '+name);return v


def entero(text,name):
    exigir(isinstance(text,str) and re.fullmatch(r'\d+',text),'Entero inválido: '+name);return int(text)


def por_id(rows,col):
    d={}
    for row in rows:
        pid=row[col];exigir(pid and pid==pid.strip() and pid not in d,'ID vacío/duplicado');d[pid]=row
    return d


def configuracion(raiz):
    raiz=Path(raiz)
    exigir(hash_archivo(raiz/DISENO)==DISENO_SHA,'Diseño cambiado: versionar antes de ejecutar')
    exigir(hash_archivo(raiz/FUENTES)==FUENTES_SHA,'Snapshot cambiado: actualizar inventario/versionar')
    return json_estricto(raiz/DISENO),json_estricto(raiz/FUENTES)


def validar_control_inactivo(comparaciones):
    exigir(all(r['candidata_a_promover'] in ['True','False'] for r in comparaciones),'Activación de control no declarada')
    exigir(not any(r['candidata_a_promover']=='True' for r in comparaciones),'Control revuelto vacío pese a candidato que lo activa')


def validar_fuentes(root,manifest):
    inventory=[]
    for task,src in manifest['fuentes'].items():
        for f in src['archivos']:
            path=ruta_segura(root,task+'/'+f['ruta'])
            exigir(path.is_file() and path.stat().st_size==f['bytes'] and hash_archivo(path)==f['sha256'],'Fuente distinta de snapshot: '+task+'/'+f['ruta'])
            rows=len(csv_completo(path,permitir_vacio=True)) if path.suffix=='.csv' else ''
            empty_status='sin_filas_actividad_no_acreditada'
            if rows==0 and task=='t10' and f['ruta']=='registro/t10/control_revuelto_t10.csv':
                validar_control_inactivo(csv_completo(Path(root)/'t10/registro/t10/comparacion_emparejada_t10.csv'))
                empty_status='sin_filas_control_no_activado_segun_regla_T10'
            inventory.append(dict(fuente=task,tarea=src['tarea'],responsable=src['responsable'],commit=src['commit'],
                estado_revision=src['estado'],revision_formal_del_commit=src['revision_exacta'],archivo=f['ruta'],sha256=f['sha256'],bytes=f['bytes'],filas_csv=rows,
                uso='soporte_sin_error_real' if '59' in path.name else 'trazabilidad_o_evidencia_historica',
                estado_contenido=empty_status if rows==0 else 'contenido_completo_sin_muestreo',metodo_comun_acreditado=False,url=src['url']))
    # Compatibilidad de los INSUMOS, distinta de equivalencia de los métodos.
    for src in manifest['fuentes']:
        for rel in [TABLA,PART]:exigir(hash_archivo(Path(root)/src/rel)==hash_archivo(Path(root)/'base'/rel),'Tabla/particiones incompatibles entre fuentes')
    t07=json_estricto(Path(root)/'base/registro/t07/manifest.json')
    for rel,h in t07['archivos_sha256'].items():exigir(hash_archivo(Path(root)/'base/registro/t07'/rel)==h,'Entrega T07 alterada')
    return inventory


def cargar_base(root):
    base=Path(root)/'base';table=por_id(csv_completo(base/TABLA),'id_parcela')
    cat=por_id(csv_completo(base/'analisis/auditoria_catalogo_y_etiquetas/tablas/catalogo_parcelas.csv'),'id_parcela')
    exigir(len(table)==197 and set(table)==set(cat),'Universo/catálogo diferente')
    roles=json_estricto(base/'registro/t07/contrato_columnas.json')
    relief=por_id(csv_completo(base/'registro/t07/calidad_relieve.csv'),'id_parcela')
    numeric=[c for c in roles['columnas_por_funcion']['predictor_candidato'] if c!='municipio']+roles['columnas_por_funcion']['calidad']
    missing=[]
    known=set();reserved=set()
    for pid,row in table.items():
        exigir(row['campania']=='2025' and row['municipio'] and row['cultivo_origen'] in ['Cebada','CEBADA'],'Metadatos de unidad inválidos')
        exigir(numero(row['area_ha_origen'],'área')>0 and numero(row['area_ha_origen'],'área')==numero(cat[pid]['area_ha_origen'],'área catálogo'),'Área origen incompatible')
        for col in numeric:
            if col=='pendiente_media_t10_grados' and row[col]=='':
                missing.append(pid);exigir(0<=numero(relief[pid]['pendiente_cobertura_valida'],'cobertura')<.5,'Faltante pendiente no documentado por D020')
            else:numero(row[col],col)
        exigir(row['municipio']==cat[pid]['municipio'] and row['cultivo_origen']==cat[pid]['cultivo_origen'],'Territorio/grupo diferentes')
        if row['conjunto_origen']=='ENTRENAMIENTO':
            known.add(pid);exigir(numero(row['rendimiento_t_ha'],'etiqueta')==numero(cat[pid]['rendimiento_t_ha'],'etiqueta catálogo'),'Etiqueta distinta de catálogo')
        else:
            exigir(row['conjunto_origen']=='PREDICCION' and row['rendimiento_t_ha']==cat[pid]['rendimiento_t_ha']=='','Reservada con objetivo/rol incorrecto');reserved.add(pid)
    exigir(len(known)==138 and len(reserved)==59,'138/59 incorrecto')
    exigir(len(missing)==2,'Faltantes D020 distintos de entrega congelada')
    qc=por_id(csv_completo(base/'registro/t07/calidad_parcelas.csv'),'id_parcela')
    exigir(set(qc)==set(table),'Calidad no cubre 197')
    parts=csv_completo(base/PART);seen=set();by_rep=defaultdict(dict)
    for row in parts:
        pid=row['ID_POLIGONO'];rep=entero(row['repeticion'],'repetición')
        exigir(pid in known and rep in range(1,6) and (rep,pid) not in seen,'ID/repetición duplicado o ajeno');seen.add((rep,pid))
        exigir(row['municipio']==table[pid]['municipio'] and row['grupo_registro']==table[pid]['cultivo_origen'],'Particiones con metadatos diferentes')
        exigir(row['celda_chirps'] and row['semilla'],'Celda/semilla ausente')
        for c in ['particion_principal','particion_espacial']:exigir(entero(row[c],c) in range(5),'Fold fuera de rango')
        by_rep[rep][pid]=row
    exigir(len(parts)==690 and set(by_rep)==set(range(1,6)) and all(set(v)==known for v in by_rep.values()),'Particiones incompletas')
    return table,known,reserved,qc,by_rep


def referencia(table,ids,pid):
    row=table[pid];chosen=[i for i in ids if table[i]['municipio']==row['municipio']];source='municipio'
    if not chosen:chosen=[i for i in ids if table[i]['cultivo_origen']==row['cultivo_origen']];source='grupo'
    if not chosen:chosen=list(ids);source='global'
    exigir(chosen,'Referencia sin entrenamiento');return math.fsum(numero(table[i]['rendimiento_t_ha'],'y') for i in sorted(chosen))/len(chosen),source


def contextos(table,known,parts,root):
    contexts={}
    for esc,field in [('A','particion_principal'),('B','particion_espacial')]:
        for rep,rows in parts.items():
            for fold in range(5):
                tr={pid for pid,r in rows.items() if int(r[field])!=fold};te=known-tr
                exigir(tr and te and not tr&te,'Fold vacío/solapado')
                if esc=='B':exigir(not {rows[i]['celda_chirps'] for i in tr}&{rows[i]['celda_chirps'] for i in te},'Celda compartida entre entrenamiento/evaluación B')
                for pid in te:
                    ref,source=referencia(table,tr,pid)
                    contexts[(esc,rep,fold,pid)]={'referencia':ref,'fuente':source,'celda':rows[pid]['celda_chirps'],'n_train':len(tr)}
    exigir(len(contexts)==1380,'1380 claves A/B requeridas')
    stored=json_estricto(Path(root)/'t09/registro/t09/centrado_v2/contextos.json');seen=set()
    for r in stored:
        key=(r['escenario'],r['repeticion'],r['particion']);exigir(key not in seen,'Contexto T09 duplicado');seen.add(key)
        tr=set(r['entrenamiento']);te=set(r['evaluacion'])
        exigir(len(tr)==len(r['entrenamiento']) and len(te)==len(r['evaluacion']) and not tr&te and tr|te==known,'Contexto T09 inválido')
        if r['escenario']=='C':
            exigir(r['repeticion']==1 and r['particion'] in range(9),'Contexto C inválido')
            exigir(len({table[i]['municipio'] for i in te})==1 and not {table[i]['municipio'] for i in tr}&{table[i]['municipio'] for i in te},'C no excluye municipio')
            for pid in te:
                ref,source=referencia(table,tr,pid);contexts[(*key,pid)]={'referencia':ref,'fuente':source,'celda':parts[1][pid]['celda_chirps'],'n_train':len(tr)}
        else:
            expected={k[3] for k in contexts if k[:3]==key};exigir(expected==te,'Contexto T09 A/B distinto de T03')
        for split in r['internas']:
            a=set(split['entrenamiento']);b=set(split['validacion'])
            exigir(len(a)==len(split['entrenamiento']) and len(b)==len(split['validacion']),'IDs internos duplicados')
            exigir(len(split['elegibles'])==len(b) and all(isinstance(x,bool) for x in split['elegibles']),'Máscara interna inválida')
            exigir(not a&b and a|b==tr and not (a|b)&te,'Entrenamiento interno mezcla evaluación externa')
    exigir(len(seen)==59 and sum(k[0]=='C' for k in contexts)==138,'Contextos T09 incompletos')
    return contexts


def archivos_oof(manifest):
    for task,src in manifest['fuentes'].items():
        for f in src['archivos']:
            rel=f['ruta']
            if task=='base' and rel==OOF_BASE:yield 'T08',task,rel
            elif task=='t09' and rel=='registro/t09/centrado_v2/predicciones_oof.csv':yield 'T09',task,rel
            elif task in ['t10','t11','t13'] and '/predicciones_oof_' in rel:yield task.upper(),task,rel
            elif task=='t14' and '/predicciones_oof_t14_' in rel:yield 'T14',task,rel


def normalizar(rows,label,task,rel,table,contexts):
    out=[];seen=set();groups=defaultdict(set);versions=defaultdict(set)
    for row in rows:
        pid=row['ID_POLIGONO'];exigir('id_parcela' not in row or row['id_parcela']==pid,'Alias ID incompatible')
        esc=row['escenario'];rep=entero(row['repeticion'],'rep');fold=entero(row['particion'],'fold');key=(esc,rep,fold,pid)
        exigir(key in contexts and (esc!='C' or task=='t09'),'OOF ajeno, reservada o contexto inválido')
        e=contexts[key];candidate=row['candidato'];version=row['version'];variant=row.get('variante','seleccionada')
        exigir(candidate and candidate.strip()==candidate and version and version.strip()==version,'Candidato/versión vacíos')
        group=(label,rel,candidate,variant);ident=(group,key)
        exigir(ident not in seen,'OOF duplicado');seen.add(ident);groups[group].add(key);versions[group].add(version)
        real=numero(row['real'],'real');pred=numero(row['prediccion'],'predicción')
        exigir(real==numero(table[pid]['rendimiento_t_ha'],'y catálogo'),'OOF cambia etiqueta')
        exigir(row['fuente']==e['fuente'],'OOF usa respaldo distinto de referencia común')
        if 'referencia' in row:exigir(abs(numero(row['referencia'],'referencia')-e['referencia'])<=ATOL,'Referencia OOF no reproduce T08')
        if candidate in ['media_mun__resp_grupo','referencia','T']:exigir(abs(pred-e['referencia'])<=ATOL,'Predicción de referencia alterada')
        for col,expected in [('municipio',table[pid]['municipio']),('cultivo_origen',table[pid]['cultivo_origen']),('celda_chirps',e['celda'])]:
            if col in row:exigir(row[col]==expected,'Metadato OOF diferente de fuente canónica')
        if 'sin_respaldo' in row:exigir(row['sin_respaldo']==str(e['fuente']=='municipio'),'Máscara OOF incompatible')
        out.append(dict(fuente=label,archivo=rel,candidato=candidate,variante=variant,version=version,
            escenario=esc,repeticion=rep,particion=fold,id_parcela=pid,real=real,prediccion=pred,
            referencia=e['referencia'],fuente_referencia=e['fuente'],sin_respaldo=e['fuente']=='municipio',
            celda_chirps=e['celda'],unidad='t/ha',metodo_comun_acreditado=False))
    summaries=[]
    expected={k for k in contexts if k[0]!='C'}
    for g,keys in sorted(groups.items()):
        exigir(len(versions[g])==1,'Versiones mezcladas dentro del mismo procedimiento')
        exigir({k for k in keys if k[0]!='C'}==expected,'OOF A/B incompleto; no rellenar ni eliminar filas')
        if task=='t09':exigir({k for k in keys if k[0]=='C'}=={k for k in contexts if k[0]=='C'},'OOF C incompleto')
        summaries.append(dict(fuente=g[0],archivo=g[1],candidato=g[2],variante=g[3],version=next(iter(versions[g])),
            filas=len(keys),A=sum(k[0]=='A' for k in keys),B=sum(k[0]=='B' for k in keys),C=sum(k[0]=='C' for k in keys),
            etiqueta_clave_referencia_mascara_verificadas=True,compatibilidad_de_datos=True,metodos_equivalentes=False,modelo_nuevo_acreditado=False))
    return out,summaries


def seleccionar_casos(base,table,qc):
    eligible=defaultdict(list)
    for r in base:
        if r['escenario']=='A' and r['sin_respaldo']:eligible[r['id_parcela']].append(abs(r['prediccion']-r['real']))
    ordered=sorted(((math.fsum(e)/len(e),pid,len(e)) for pid,e in eligible.items()),key=lambda x:(-x[0],x[1]))
    exigir(len(ordered)>=10,'Insuficientes casos principales');cases=[]
    for rank,(score,pid,n) in enumerate(ordered[:10],1):cases.append(dict(orden=rank,id_parcela=pid,fuente='T08',escenario='A',poblacion='sin_respaldo',n_repeticiones_elegibles=n,criterio_media_error_absoluto=score,municipio=table[pid]['municipio']))
    return cases,seleccionar_controles(cases,base,table,qc)


def seleccionar_controles(cases,base,table,qc):
    """Distancia de metadatos; no consume errores ni rendimientos del control."""
    excluded={r['id_parcela'] for r in cases};used=set();controls=[]
    def mismatch(a,b):
        return sum(qc[a][c]!=qc[b][c] for c in ['contorno_categoria','contorno_angosta_o_muy_pequena'])+int((table[a]['pendiente_media_t10_grados']=='')!=(table[b]['pendiente_media_t10_grados']==''))
    def distance(a,b):
        return (mismatch(a,b),abs(math.log(numero(table[a]['area_ha_origen'],'área'))-math.log(numero(table[b]['area_ha_origen'],'área'))),
                abs(numero(table[a]['pl_capturas_abr_oct'],'capturas')-numero(table[b]['pl_capturas_abr_oct'],'capturas')),b)
    known={r['id_parcela'] for r in base}
    for c in cases:
        pid=c['id_parcela'];pool=[i for i in known-excluded-used if table[i]['municipio']==table[pid]['municipio']]
        if not pool:controls.append(dict(caso=pid,control='',estado='sin_control_comparable_en_municipio',diferencias_calidad='',diferencia_log_area='',diferencia_capturas='',seleccion_por_error=False));continue
        pick=min(pool,key=lambda i:distance(pid,i));used.add(pick);d=distance(pid,pick)
        controls.append(dict(caso=pid,control=pick,estado='mejor_disponible_segun_regla_no_equivalencia_certificada',diferencias_calidad=d[0],diferencia_log_area=d[1],diferencia_capturas=d[2],seleccion_por_error=False))
    return controls


def temporal(root,table):
    src=Path(root)/'base/registro/t07';roles=json_estricto(src/'contrato_columnas.json');inventory=json_estricto(src/'inventario_fuentes.json')
    exigir(inventory['corte_observacional']=='2025-10-31','Corte diferente: no mover en diagnóstico')
    dictionary=csv_completo(src/'diccionario_columnas.csv');d={}
    for r in dictionary:
        if r['archivo']=='tabla_comun.csv':exigir(r['columna'] not in d,'Diccionario duplicado');d[r['columna']]=r
    columns=list(next(iter(table.values())));exigir(set(columns)==set(d),'Diccionario no cubre tabla completa')
    out=[]
    for col in columns:
        r=d[col];period=r['periodo'];last=''
        if period=='abr_oct' or col.endswith('_abr_oct'):last='2025-10-31'
        elif period=='jun_oct' or col.endswith('_jun_oct'):last='2025-10-31'
        elif '/' in period and re.fullmatch(r'\d{4}-\d{2}-\d{2}/\d{4}-\d{2}-\d{2}',period):last=period.split('/')[1]
        exigir(not last or last<='2025-10-31','Observación posterior al corte')
        out.append(dict(columna=col,funcion=r['funcion'],producto=r['producto'],unidad_declarada=r['unidad'],
            unidad_fisica_pendiente=col in roles['unidades_fisicas_pendientes'],periodo=period,fin_observado_explicito=last,
            corte_observacional='2025-10-31',fecha_publicacion_historica='no_documentada',
            disponible_al_corte='no_acreditado',uso_actual='reconstruccion_retrospectiva_2025',
            uso_operacional='requiere_evidencia_de_publicacion_y_regla_de_uso',campania_futura='requiere_validacion_temporal',
            ausencia_no_equivale_a_cero=True,significado_vacio=r['significado_vacio']))
    return out


def validar(root,manifest):
    inv=validar_fuentes(root,manifest);table,known,reserved,qc,parts=cargar_base(root);contexts=contextos(table,known,parts,root)
    ledger=[];series=[];baseline=[]
    for label,task,rel in archivos_oof(manifest):
        out,sums=normalizar(csv_completo(Path(root)/task/rel),label,task,rel,table,contexts);ledger.extend(out);series.extend(sums)
        if label=='T08':baseline=out
    exigir(len(baseline)==1380 and len(series)==51,'Inventario de procedimientos inesperado')
    cases,controls=seleccionar_casos(baseline,table,qc)
    masks=[dict(escenario=k[0],repeticion=k[1],particion=k[2],id_parcela=k[3],fuente_referencia=v['fuente'],
                todas=True,sin_respaldo=v['fuente']=='municipio',celda_chirps=v['celda'],n_entrenamiento=v['n_train']) for k,v in sorted(contexts.items())]
    return {'inventario_fuentes.csv':inv,'compatibilidad_procedimientos.csv':series,'mascaras_contextos.csv':masks,
        'casos_preseleccionados.csv':cases,'controles_preseleccionados.csv':controls,
        'alcance_temporal.csv':temporal(root,table),'normalizadas_oof.csv':sorted(ledger,key=lambda r:(r['fuente'],r['archivo'],r['candidato'],r['variante'],r['escenario'],r['repeticion'],r['particion'],r['id_parcela']))}


def escribir_csv(path,rows):
    exigir(rows,'Tabla derivada vacía')
    with path.open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)


def ejecutar(root,diseno,manifest,salida):
    salida=Path(salida);exigir(not salida.exists(),'Salida nueva obligatoria; no sobreescribir')
    artifacts=validar(root,manifest)
    artifacts['preguntas_y_entregables.csv']=[dict(id=r['id'],pregunta=r['pregunta'],evidencia=r['evidencia'],fase_respuesta=r['fase_respuesta'],limite=r.get('limite','Descriptivo, no causal'),estado='pregunta_registrada_sin_respuesta_en_fase0') for r in diseno['preguntas']]
    # Sólo escribir después de completar todas las verificaciones; un fallo no publica un prefijo.
    salida.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.fase0_',dir=salida.parent) as temp:
        stage=Path(temp)/'entrega';stage.mkdir()
        for name,rows in artifacts.items():escribir_csv(stage/name,rows)
        masks=artifacts['mascaras_contextos.csv'];counts={s:{'todas':sum(r['escenario']==s for r in masks),'sin_respaldo':sum(r['escenario']==s and r['sin_respaldo'] for r in masks)} for s in ['A','B','C']}
        result=dict(schema='agrocebada_diagnostico_fase0_entrega_v1',fase='0',subfases=['0.1','0.2','0.3'],estado='verificada_tecnicamente_para_revision',
            diseno_sha256=DISENO_SHA,fuentes_sha256=FUENTES_SHA,base_dev=manifest['base_dev'],
            codigo_sha256={n:hash_archivo(RAIZ/n) for n in ['scripts/diagnostico_fase0.py','scripts/diagnostico_fuentes.py']},
            parcelas_etiquetadas=138,parcelas_reservadas_sin_objetivo=59,series_historicas=51,
            registros_oof_verificados=len(artifacts['normalizadas_oof.csv']),archivos_fuente_verificados=len(artifacts['inventario_fuentes.csv']),
            mascaras=counts,casos_principales=10,controles_disponibles=sum(bool(r['control']) for r in artifacts['controles_preseleccionados.csv']),
            reentrenamientos=0,modelos_finales_59=0,fase1_interpretacion_ejecutada=False,metodo_comun_acreditado=False,
            revision_humana_fase0='pendiente',cronologia='Etiquetas/resultados explorados previamente; reglas fijadas antes de ejecutar esta fase, no análisis ciego',
            disponibilidad_historica_fira='no_documentada',garantia_campania_futura=False,
            publicables=PUBLICABLES,archivo_local_no_publicable='normalizadas_oof.csv',
            fuentes_errores=[],archivos_sha256={n:hash_archivo(stage/n) for n in sorted(artifacts)})
        (stage/'manifest.json').write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
        os.rename(stage,salida)
    return result


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--raiz',type=Path,default=RAIZ);ap.add_argument('--fuentes',type=Path,required=True);ap.add_argument('--salida',type=Path);ap.add_argument('--preparar-fuentes',action='store_true')
    args=ap.parse_args()
    try:
        design,sources=configuracion(args.raiz)
        if args.preparar_fuentes:
            preparar(args.raiz,sources,args.fuentes);print(json.dumps({'resultado':'fuentes_materializadas','reentrenamientos':0}));return
        exigir(args.salida is not None,'Falta destino de salida')
        result=ejecutar(args.fuentes,design,sources,args.salida)
    except (ValueError,OSError,KeyError,TypeError,json.JSONDecodeError) as e:ap.exit(1,'Fase 0 rechazada: '+str(e)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ['archivos_sha256','publicables']},ensure_ascii=False,indent=2))


if __name__=='__main__':main()
