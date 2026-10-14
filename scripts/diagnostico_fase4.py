"""Fase 4: trazabilidad y granularidad de etiquetas, sin aprender ni corregirlas."""
import argparse
from collections import Counter, defaultdict
import csv
from decimal import Decimal, InvalidOperation, ROUND_HALF_EVEN
import hashlib
import io
import json
import math
from pathlib import Path
import statistics
import struct
import tempfile
import zipfile

ROOT=Path(__file__).resolve().parents[1]
DESIGN='registro/diagnostico/fase4_diseno.json'
DESIGN_SHA='adcdc9e167b6c6121ace5113794418a91be6e58c87f21feac4683b8cd02682ee'
T02='analisis/auditoria_catalogo_y_etiquetas/tablas/'
LEDGER_SHA='199fed965f34033e94716c8c0edaef189ac94e186ec5a28e8325496269fbdea0'
IDS={f'AGC_{i:03d}' for i in range(1,198)}


def check(ok,message):
    if not ok:raise ValueError(message)


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def decimal(text,field='número'):
    check(isinstance(text,str) and bool(text.strip()),'Número vacío: '+field)
    try:d=Decimal(text.strip())
    except InvalidOperation:raise ValueError('Número inválido: '+field) from None
    check(d.is_finite(),'Número no finito: '+field)
    return d


def text(d):
    if d is None:return ''
    return format(d,'f')


def leer(path):
    path=Path(path);check(path.is_file() and not path.is_symlink() and path.stat().st_size<64*1024*1024,'CSV no autorizado/regular/acotado')
    with path.open(encoding='utf-8-sig',newline='') as f:
        reader=csv.DictReader(f);check(reader.fieldnames and len(set(reader.fieldnames))==len(reader.fieldnames),'Cabecera duplicada/vacía')
        rows=list(reader)
    check(rows and all(None not in r and all(v is not None for v in r.values()) for r in rows),'CSV no rectangular')
    return rows


def indexed(rows,key='id_parcela'):
    out={r[key]:r for r in rows};check(len(out)==len(rows) and all(out),'ID vacío/duplicado')
    return out


def csv_write(path,rows):
    check(rows,'Tabla sin esquema')
    with Path(path).open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)


def original_csv(payload):
    r=csv.DictReader(io.StringIO(payload.decode('utf-8-sig')))
    check(r.fieldnames==['ID_POLIGONO','AREA_HA','RENDIMIENTO_T_HA','CONJUNTO',''],'Esquema FIRA distinto')
    rows=list(r);out=[]
    for i,row in enumerate(rows,2):
        check(None not in row and all(v is not None for v in row.values()) and row['']=='','Coma final no vacía/registro irregular')
        check(all(v==v.strip() for v in row.values()),'Espacios originales inesperados; no normalizar en silencio')
        out.append(dict(id_parcela=row['ID_POLIGONO'],area=row['AREA_HA'],y=row['RENDIMIENTO_T_HA'],conjunto=row['CONJUNTO'],linea_original=i))
    out=indexed(out);check(set(out)==IDS,'Universo CSV distinto')
    check(sum(bool(r['y']) for r in out.values())==138,'Etiquetas distintas138')
    for pid,r in out.items():
        check(decimal(r['area'])>0,'Área no positiva')
        check(r['conjunto']==('ENTRENAMIENTO' if r['y'] else 'PREDICCION'),'Etiqueta/partición contradictoria')
        if r['y']:check(decimal(r['y'])>0,'Rendimiento no positivo')
    return out


def original_dbf(payload):
    """Leer atributos DBF conocidos del paquete aprobado, sin código GDAL/PROJ."""
    check(len(payload)>=33,'DBF truncado')
    n,header,length=struct.unpack('<IHH',payload[4:12]);check(n==197 and header==225 and length==425,'Estructura DBF distinta')
    fields=[]
    for pos in range(32,header-1,32):
        name=payload[pos:pos+11].split(b'\0',1)[0].decode('utf-8');kind=chr(payload[pos+11]);width=payload[pos+16]
        check(kind in ('C','N'),'Tipo DBF desconocido');fields.append((name,kind,width))
    check([n for n,_,_ in fields]==['Cultivo','ID_POLIGON','área_ha','Municipio','Estado','CONJUNTO'],'Campos DBF distintos')
    check(payload[header-1]==13 and 1+sum(v for _,_,v in fields)==length,'Cabecera DBF incompatible')
    check(len(payload)>=header+n*length,'Registros DBF truncados')
    rows=[]
    for i in range(n):
        b=payload[header+i*length:header+(i+1)*length];check(b[0]==32,'Fila DBF eliminada/no activa')
        pos=1;r={}
        for name,kind,width in fields:
            value=b[pos:pos+width].decode('utf-8').strip();pos+=width
            if kind=='N':decimal(value,name)
            r[name]=value
        rows.append(r)
    return indexed(rows,'ID_POLIGON')


def cargar(ledger):
    check(sha(ROOT/DESIGN)==DESIGN_SHA,'Diseño fase4 cambió')
    design=json.loads((ROOT/DESIGN).read_text())
    for n,h in design['fuentes'].items():check(sha(ROOT/n)==h,'Fuente fijada distinta: '+n)
    m=json.loads((ROOT/'registro/diagnostico/fase3/manifest.json').read_text())
    for n,h in m['archivos_sha256'].items():check(sha(ROOT/'registro/diagnostico/fase3'/n)==h,'Artefacto F3 distinto')
    check(sha(ledger)==LEDGER_SHA,'Ledger histórico distinto')
    with zipfile.ZipFile(ROOT/'data/raw/DataSet.zip') as z:
        raw=original_csv(z.read('DATASET_RETO_AGRO_2026/ID_area_rendimiento_70_30_Reto_AgroCebada.csv'))
        with zipfile.ZipFile(io.BytesIO(z.read('DATASET_RETO_AGRO_2026/Parcelas_Reto_AGC_CONJUNTO_70_30.zip'))) as zz:
            check(zz.read('Parcelas_Reto_AGC_CONJUNTO.cpg')==b'UTF-8','Codificación DBF distinta')
            shapes=original_dbf(zz.read('Parcelas_Reto_AGC_CONJUNTO.dbf'))
    check(set(shapes)==set(raw),'Identidad geometrías distinta')
    table=indexed(leer(ROOT/'registro/t07/tabla_comun.csv'));cat=indexed(leer(ROOT/T02/'catalogo_parcelas.csv'))
    check(set(table)==set(cat)==set(raw),'Universos integración distintos')
    counts=Counter();series=defaultdict(set)
    # Stream the full ledger; do not infer independent sample size from repeated predictions.
    with Path(ledger).open(newline='') as f:
        reader=csv.DictReader(f)
        for r in reader:
            pid=r['id_parcela'];check(pid in raw and bool(raw[pid]['y']),'OOF con reservada/ID ajeno')
            check(decimal(r['real'])==decimal(raw[pid]['y']),'Etiqueta OOF distinta: '+pid)
            counts[pid]+=1;series[pid].add(tuple(r[k] for k in ('fuente','archivo','candidato','variante','version')))
    check(sum(counts.values())==71208 and all(v==516 for v in counts.values()),'Censo OOF incompleto')
    joins=[]
    for pid,r in sorted(raw.items()):
        a=shapes[pid];t=table[pid];c=cat[pid]
        check(r['y']==t['rendimiento_t_ha']==c['rendimiento_t_ha'],'Etiqueta literal integración distinta '+pid)
        check(decimal(r['area'])==decimal(t['area_ha_origen'])==decimal(c['area_ha_origen']),'Área integración distinta')
        delta=abs(decimal(r['area'])-decimal(a['área_ha']));check(delta<=Decimal('1e-9'),'Área DBF/CSV distinta')
        check(r['conjunto']==a['CONJUNTO']==t['conjunto_origen']==c['conjunto_origen'],'Asignación conjunto distinta')
        check(a['Municipio']==t['municipio']==c['municipio'] and a['Estado']==t['estado']==c['estado'],'Municipio/estado por ID distinto')
        check(a['Cultivo']==t['cultivo_origen']==c['cultivo_origen'],'Grupo de escritura distinto')
        joins.append(dict(id_parcela=pid,linea_original=r['linea_original'],rendimiento_literal=r['y'],area_literal=r['area'],
            y_presente=bool(r['y']),conjunto=r['conjunto'],municipio=t['municipio'],cultivo_origen=t['cultivo_origen'],
            CSV_T02_T07_literal_identico=True,DBF_CSV_area_delta_ha=text(delta),DBF_conjunto_municipio_identico=True,
            n_OOF_comprobados=counts[pid],n_series_OOF=len(series[pid]),fuente_y_individual='no_documentada',
            denominador_y_humedad='no_documentados',estado='conciliado'))
    return raw,table,cat,joins


def paso(valores):
    # Match T02's rule, and keep sample size distinct from number of unique values.
    if len(valores)<3:return ''
    for h in map(Decimal,('0.5','0.1','0.01')):
        if all(v%h==0 for v in valores):return text(h)
    return ''


def granularidad(raw,table):
    by=defaultdict(list);old={r['grupo']:r for r in leer(ROOT/T02/'precision_etiqueta_por_municipio.csv') if r['agrupacion']=='municipio'}
    for pid,r in raw.items():
        if r['y']:by[table[pid]['municipio']].append((pid,r))
    out=[]
    for m,rows in sorted(by.items()):
        ys=[decimal(r['y']) for _,r in rows];counts=Counter(ys);step=paso(ys);distinct=len(counts)
        decimals=[len(r['y'].partition('.')[2]) for _,r in rows]
        compatible=[text(h) for h in map(Decimal,('0.5','0.1','0.01')) if all(v%h==0 for v in ys)]
        check(step==old[m]['paso_comun'],'Paso T02 distinto: '+m)
        check(len(rows)==int(old[m]['parcelas_conocidas']) and distinct==int(old[m]['valores_distintos']),'Conteo T02 distinto')
        check([decimals.count(k) for k in (0,1,2)]==[int(old[m][col]) for col in ('con_0_decimales','con_1_decimal','con_2_decimales')],'Decimales T02 distintos')
        out.append(dict(municipio=m,n_etiquetadas=len(rows),valores_distintos=distinct,
            min=text(min(ys)),max=text(max(ys)),decimales0=decimals.count(0),decimales1=decimals.count(1),decimales2=decimals.count(2),
            paso_compatible_T02=step,pasos_compatibles_incluye_n_pequeno=';'.join(compatible),
            etiqueta_constante=distinct==1,resolucion_medicion_confirmada=False,
            nivel_evidencia='constante_no_identifica_resolucion' if distinct==1 else 'menos3_no_asignar_paso' if len(rows)<3 else 'malla_escrita_observable_no_precision_medicion',
            parcelas_valor_repetido=sum(n for n in counts.values() if n>1),
            ids=';'.join(sorted(pid for pid,_ in rows))))
    return out


def granularidad_entreno(raw,table,contexts):
    known={pid for pid,r in raw.items() if r['y']};parts=defaultdict(dict)
    for r in contexts:
        if r['escenario'] not in ('A','B'):continue
        k=(r['escenario'],int(r['repeticion']));pid=r['id_parcela']
        check(pid in known and pid not in parts[k],'Contexto duplicado/ajeno')
        parts[k][pid]=int(r['particion'])
    check(len(parts)==10 and all(set(v)==known for v in parts.values()),'Particiones incompletas')
    mun=sorted({r['municipio'] for r in table.values()});out=[];lookup={}
    for (esc,rep),mapping in sorted(parts.items()):
        for fold in range(5):
            train={p for p,f in mapping.items() if f!=fold};evaluation=known-train
            check(train.isdisjoint(evaluation) and len(train)+len(evaluation)==138,'Filtración de etiquetas')
            for m in mun:
                ids=sorted(p for p in train if table[p]['municipio']==m);ys=[decimal(raw[p]['y']) for p in ids]
                step=paso(ys);nuniq=len(set(ys))
                row=dict(escenario=esc,repeticion=rep,particion=fold,municipio=m,n_entreno_municipal=len(ids),
                    n_valores_distintos=nuniq,paso_compatible_solo_entreno=step,constante_entreno=bool(ys) and nuniq==1,
                    nivel_evidencia='sin_municipio_entreno' if not ys else 'constante_no_identifica_resolucion' if nuniq==1 else 'menos3_no_asignar_paso' if len(ys)<3 else 'malla_escrita_no_precision',
                    n_evaluacion_municipal=sum(table[p]['municipio']==m for p in evaluation),
                    firma_IDs_entreno=hashlib.sha256('\n'.join(ids).encode()).hexdigest(),etiquetas_evaluacion_usadas=False)
                out.append(row);lookup[(esc,rep,fold,m)]=row
    check(len(out)==450,'Granularidad externa incompleta')
    return out,lookup


def errores_por_grano(table,quality,lookup):
    q={r['municipio']:r for r in quality};groups=defaultdict(lambda:defaultdict(list))
    for r in leer(ROOT/'registro/diagnostico/fase1/errores_por_repeticion.csv'):
        esc=r['escenario'];rep=int(r['repeticion']);fold=int(r['particion']);pid=r['id_parcela'];m=table[pid]['municipio']
        check(decimal(r['real'])==decimal(table[pid]['rendimiento_t_ha']),'Error unido a otra etiqueta')
        pred=decimal(r['prediccion']);error=abs(pred-decimal(r['real']))
        for pop in ('todas','sin_respaldo'):
            if pop=='sin_respaldo' and r['fuente_referencia']!='municipio':continue
            for basis,step in [('catalogo_T02_solo_descriptivo',q[m]['paso_compatible_T02']),('entrenamiento_fold',lookup[(esc,rep,fold,m)]['paso_compatible_solo_entreno'])]:
                groups[(esc,pop,basis,step or 'no_identificado')][pid].append(error)
    out=[]
    for (esc,pop,basis,step),by in sorted(groups.items()):
        maes=[sum(v)/len(v) for v in by.values()]
        out.append(dict(escenario=esc,poblacion=pop,base_granularidad=basis,paso=step,n_ID_grupo=len(by),
            n_registros=sum(len(v) for v in by.values()),mae_por_ID=text(sum(maes)/len(maes)),mediana_mae_ID=text(statistics.median(maes)),
            parcelas_con_mismo_peso=True,IDs_pueden_estar_en_mas_de_un_grupo_entreno=basis=='entrenamiento_fold',
            MAE_reducido_por_incertidumbre=False,lectura='descriptivo_no_comparacion_de_modelos_ni_pesos_por_precision'))
    return out


def locales(raw,table,cat):
    known={pid for pid,r in raw.items() if r['y']};by=defaultdict(list)
    for p in known:by[table[p]['municipio']].append(p)
    old=indexed(leer(ROOT/T02/'desviacion_municipal_por_parcela.csv'))
    cases={r['id_parcela']:r['orden'] for r in leer(ROOT/'registro/diagnostico/fase0/casos_preseleccionados.csv')}
    controls={r['control']:r['caso'] for r in leer(ROOT/'registro/diagnostico/fase0/controles_preseleccionados.csv')}
    errors={r['id_parcela']:r for r in leer(ROOT/'registro/diagnostico/fase1/errores_por_parcela.csv') if r['escenario']=='A' and r['poblacion']=='sin_respaldo'}
    rows=[];area=[]
    for pid in sorted(known):
        r=raw[pid];t=table[pid];c=cat[pid];y=decimal(r['y']);a=decimal(r['area']);other=sorted(set(by[t['municipio']])-{pid})
        avg=sum(decimal(raw[p]['y']) for p in other)/len(other) if other else None;delta=y-avg if avg is not None else None
        if avg is not None:
            check(abs(avg-decimal(old[pid]['promedio_demas_municipio']))<=Decimal('.00051'),'Media LOO T02 distinta')
            check(abs(delta-decimal(old[pid]['desviacion_municipal']))<=Decimal('.00051'),'Desviación T02 distinta')
        extreme='no_identificable' if delta is None else 'alta' if delta>1 else 'baja' if delta< -1 else 'no'
        check((extreme==old[pid]['extrema']) if avg is not None else old[pid]['extrema']=='','Extremo T02 distinto: '+pid)
        rows.append(dict(id_parcela=pid,municipio=t['municipio'],y_literal=r['y'],area_literal=r['area'],
            n_otras_etiquetas_municipio=len(other),media_otras_municipio=text(avg),desviacion_LOO=text(delta),
            extrema_regla_historica_T02=extreme,distancia_abs_al_umbral1=text(abs(abs(delta)-1)) if delta is not None else '',
            contorno=c['contorno_categoria'],angosta=c['contorno_angosta_o_muy_pequena'],
            orden_caso_fijo=cases.get(pid,''),control_de=controls.get(pid,''),mae_A_municipal=errors[pid]['mae'],
            fuente_individual='no_documentada',variedad_individual='no_documentada',sin_correccion=True))
        check(a>Decimal('.005'),'Área no admite escenario nominal')
        for da in (Decimal('-.005'),Decimal('.005')):
            # Algebraic sensitivity only; no new target value or evaluation with an adjusted target.
            magnitude=abs(y*da/(a+da))
            area.append(dict(id_parcela=pid,area_ha_literal=r['area'],y_t_ha_literal=r['y'],
                delta_area_ha_hipotetica=text(da),variacion_relativa_rendimiento_hipotetica=text(abs(da/(a+da))),
                magnitud_variacion_t_ha_hipotetica=text(magnitude),
                supuesto='si_area_fue_redondeada_centésima_y_masa_no_cambia;no_error_area_demostrado',
                area_geodesica_T02_ha=c['area_ha_geodesica'],diferencia_area_declarada_geodesica_ha=text(abs(a-decimal(c['area_ha_geodesica']))),
                nuevo_rendimiento_evaluado=False))
    return rows,area


def pares_etiquetas(raw,table):
    rows=[]
    for r in leer(ROOT/T02/'pares_de_parcelas_cercanas.csv'):
        a,b=r['id_parcela_a'],r['id_parcela_b'];ya,yb=raw[a]['y'],raw[b]['y'];both=bool(ya and yb)
        same='si' if both and decimal(ya)==decimal(yb) else 'no' if both else ''
        check(same==r['mismo_rendimiento'],'Igualdad de vecino distinta')
        rows.append(dict(id_a=a,id_b=b,municipio_a=table[a]['municipio'],municipio_b=table[b]['municipio'],
            distancia_orillas_m=r['distancia_orillas_m'],ambas_etiquetadas=both,y_a=ya,y_b=yb,
            misma_etiqueta=same,diferencia_abs_etiquetas=text(abs(decimal(ya)-decimal(yb))) if both else '',
            escritura_a=table[a]['cultivo_origen'],escritura_b=table[b]['cultivo_origen'],
            productor_o_medicion_compartida_confirmada=False,duplicado_tecnico_confirmado=False,
            lectura='igualdad_no_prueba_misma_medicion_nunca_deduplicar_por_y'))
    return rows


def ejecutar(ledger,salida):
    salida=Path(salida);check(not salida.exists(),'No sobrescribir salidas')
    raw,table,cat,joins=cargar(ledger);quality=granularidad(raw,table)
    train,lookup=granularidad_entreno(raw,table,leer(ROOT/'registro/diagnostico/fase0/mascaras_contextos.csv'))
    local,area=locales(raw,table,cat)
    tables={'conciliacion_etiquetas.csv':joins,'granularidad_municipal.csv':quality,
        'granularidad_entrenamiento.csv':train,'error_por_granularidad.csv':errores_por_grano(table,quality,lookup),
        'sensibilidad_area_nominal.csv':area,'etiquetas_contexto.csv':local,'pares_y_etiquetas.csv':pares_etiquetas(raw,table)}
    salida.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.diag_f4_',dir=salida.parent) as td:
        tmp=Path(td)
        for name,rows in tables.items():csv_write(tmp/name,rows)
        m=dict(schema='agrocebada_diagnostico_fase4_entrega_v1',estado='tecnico_para_revision',diseno_sha256=DESIGN_SHA,
            codigo_sha256={'scripts/diagnostico_fase4.py':sha(ROOT/'scripts/diagnostico_fase4.py')},
            ledger_sha256=LEDGER_SHA,OOF_etiquetas_comprobadas=71208,parcelas=197,etiquetadas=138,reservadas=59,
            modelos_nuevos=0,etiquetas_editadas=0,predicciones_editadas=0,revision_humana='pendiente',
            n_filas_tablas={n:len(v) for n,v in tables.items()},archivos_sha256={p.name:sha(p) for p in sorted(tmp.iterdir())})
        (tmp/'manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n');tmp.rename(salida)
    return m


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--ledger',type=Path,required=True);p.add_argument('--salida',type=Path,required=True)
    a=p.parse_args();print(json.dumps(ejecutar(a.ledger,a.salida),ensure_ascii=False,indent=2))
