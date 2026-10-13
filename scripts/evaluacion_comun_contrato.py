"""Contrato común T15/T16. Valida sin entrenar ni corregir entradas silenciosamente."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
DISENO = 'registro/evaluacion_comun/procedimiento.json'
# Se fija una vez al cerrar el diseño; cambiarlo requiere versión y revisión.
DISENO_SHA = 'da633adf27c7f1cf2d7760dc2f190abe38d9a912f80a976717fc6213c48f76d3'
PART_COLS = ['ID_POLIGONO','repeticion','semilla','particion_principal','particion_espacial','celda_chirps','municipio','grupo_registro']
OOF_COLS = {'ID_POLIGONO','repeticion','particion','escenario','real','prediccion','candidato','version','fuente'}
ATOL, RTOL = 1e-12, 1e-10


def exigir(ok, mensaje):
    if not ok:
        raise ValueError(mensaje)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def leer_csv(path):
    with Path(path).open(encoding='utf-8-sig',newline='') as f:
        reader = csv.DictReader(f)
        cab = reader.fieldnames
        exigir(cab and len(cab)==len(set(cab)) and all(cab), 'Cabecera vacía o duplicada')
        rows = list(reader)
    exigir(all(None not in r and all(v is not None for v in r.values()) for r in rows), 'Ancho de fila incompatible')
    return cab, rows


def numero(x, nombre, vacio=False):
    if x == '' and vacio:
        return None
    try:
        n = float(x)
    except (ValueError,TypeError) as exc:
        raise ValueError('Número inválido: '+nombre) from exc
    exigir(math.isfinite(n), 'Número no finito: '+nombre)
    return n


def entero(x, nombre):
    n = numero(x,nombre)
    exigir(n.is_integer(), 'Entero requerido: '+nombre)
    return int(n)


def indexar(rows, key):
    result = {}
    for row in rows:
        k = tuple(row[c] for c in key)
        exigir(all(v and v.strip()==v for v in k), 'Clave vacía o con espacios: '+str(key))
        exigir(k not in result, 'Clave duplicada: '+str(k))
        result[k] = row
    return result


def cargar_diseno(raiz=RAIZ):
    p = Path(raiz)/DISENO
    exigir(sha(p)==DISENO_SHA, 'Diseño común modificado: versionar y revisar')
    c = json.loads(p.read_text())
    exigir(c['schema']=='agrocebada_comun_v1','Diseño incompatible')
    for name,h in c['fuentes_sha256'].items():
        exigir(sha(Path(raiz)/name)==h, 'Fuente distinta del diseño: '+name)
    return c


def validar_tabla(tabla, catalogo, roles, calidad_relieve):
    t = indexar(tabla, ['id_parcela']);cat=indexar(catalogo,['id_parcela']);q=indexar(calidad_relieve,['id_parcela'])
    exigir(set(t)==set(cat)==set(q) and len(t)==197,'Catálogo/T07/relieve: universo distinto de 197')
    flattened=[c for cols in roles['columnas_por_funcion'].values() for c in cols]
    exigir(len(flattened)==len(set(flattened)) and set(flattened)==set(tabla[0]),'Roles de columnas incompletos o duplicados')
    numeric=[c for c in roles['columnas_por_funcion']['predictor_candidato'] if c!='municipio']+roles['columnas_por_funcion']['calidad']+['area_ha_origen']
    conocidos=[];reservados=[]
    for k,r in t.items():
        exigir(r['campania']=='2025','Campaña distinta del diseño')
        for c in ['id_parcela','conjunto_origen','rendimiento_t_ha','area_ha_origen','municipio','estado','cultivo_origen']:
            exigir(r[c]==cat[k][c], 'T07 distinto de T02: '+k[0]+'/'+c)
        exigir(r['municipio'].strip() and r['cultivo_origen'] in ('Cebada','CEBADA'),'Territorio/grupo desconocido')
        if r['conjunto_origen']=='ENTRENAMIENTO':
            exigir(numero(r['rendimiento_t_ha'],'rendimiento')>0,'Rendimiento no positivo');conocidos.append(k[0])
        else:
            exigir(r['conjunto_origen']=='PREDICCION' and r['rendimiento_t_ha']=='','Las 59 deben tener objetivo vacío');reservados.append(k[0])
        for c in numeric:
            missing=c=='pendiente_media_t10_grados' and numero(q[k]['pendiente_cobertura_valida'],'cobertura')<.5
            v=numero(r[c], k[0]+'/'+c, vacio=missing)
            exigir((v is None)==missing if c=='pendiente_media_t10_grados' else v is not None,'Faltante fuera de regla D020')
            if c=='area_ha_origen':exigir(v>0,'Área no positiva: no admite log')
    exigir(len(conocidos)==138 and len(reservados)==59,'Se requieren 138 etiquetas y 59 objetivos vacíos')
    return t,set(conocidos),set(reservados)


def validar_particiones(cab, part, tabla, conocidos, soporte):
    exigir(cab==PART_COLS and len(part)==690,'Contrato T03: se requieren 690 filas y columnas exactas')
    idx=indexar(part,['ID_POLIGONO','repeticion']);sup=indexar(soporte,['ID_POLIGONO'])
    exigir(set(idx)=={(i,str(r)) for i in conocidos for r in range(1,6)},'IDs/repeticiones incompletos o reservados en particiones')
    for r in part:
        pid=r['ID_POLIGONO'];t=tabla[(pid,)];s=sup[(pid,)]
        exigir(r['municipio']==t['municipio'] and r['grupo_registro']==t['cultivo_origen'],'Municipio/grupo T03 distinto de T07')
        exigir(r['celda_chirps'] and r['celda_chirps']==s['celda_chirps'],'Celda CHIRPS ausente o distinta del soporte T03')
        exigir(entero(r['semilla'],'semilla')==20261000+entero(r['repeticion'],'rep'),'Semilla externa T03 incompatible')
        for c in ['particion_principal','particion_espacial']:exigir(entero(r[c],c) in range(5),'Partición fuera de 0–4')
    for rep in range(1,6):
        rows=[r for r in part if r['repeticion']==str(rep)]
        for col in ['particion_principal','particion_espacial']:
            exigir({r[col] for r in rows}==set(map(str,range(5))),'Falta una partición externa')
        cells={}
        for r in rows:
            cells.setdefault(r['celda_chirps'],set()).add(r['particion_espacial'])
        exigir(all(len(v)==1 for v in cells.values()),'Una celda se divide entre folds B')
    return idx


def referencia(rows, municipio, grupo):
    mun=[numero(r['rendimiento_t_ha'],'y') for r in rows if r['municipio']==municipio]
    grp=[numero(r['rendimiento_t_ha'],'y') for r in rows if r['cultivo_origen']==grupo]
    if mun:return math.fsum(mun)/len(mun),'municipio'
    if grp:return math.fsum(grp)/len(grp),'grupo'
    values=[numero(r['rendimiento_t_ha'],'y') for r in rows]
    exigir(bool(values),'Referencia sin entrenamiento')
    return math.fsum(values)/len(values),'global'


def contextos(tabla,part):
    contexts={}
    for esc,col in [('A','particion_principal'),('B','particion_espacial')]:
        for rep in range(1,6):
            gr=[r for r in part if r['repeticion']==str(rep)]
            for fold in range(5):
                tr=[tabla[(r['ID_POLIGONO'],)] for r in gr if r[col]!=str(fold)]
                te=[r for r in gr if r[col]==str(fold)]
                exigir(not ({r['id_parcela'] for r in tr}&{r['ID_POLIGONO'] for r in te}),'Entrenamiento y evaluación comparten ID')
                for row in te:
                    t=tabla[(row['ID_POLIGONO'],)];ref,source=referencia(tr,t['municipio'],t['cultivo_origen'])
                    contexts[(esc,rep,row['ID_POLIGONO'])]={'particion':fold,'real':numero(t['rendimiento_t_ha'],'y'),'referencia':ref,'fuente':source,'celda':row['celda_chirps']}
    return contexts


def validar_oof(rows,contexts,candidato_esperado=None):
    exigir(bool(rows),'OOF vacío')
    exigir(OOF_COLS<=set(rows[0]),'OOF requiere candidato, versión, fuente y columnas T03')
    keys={};versions={}
    for row in rows:
        c=row['candidato'];v=row['version'];exigir(c.strip()==c and bool(c) and bool(v.strip()),'Candidato/versión vacíos')
        k=(row['escenario'],entero(row['repeticion'],'rep'),row['ID_POLIGONO'])
        exigir(k in contexts,'OOF fuera de A/B o incluye parcela reservada/ajena')
        exigir((c,k) not in keys,'Predicción duplicada');keys[c,k]=row;versions.setdefault(c,set()).add(v)
        expected=contexts[k]
        exigir(entero(row['particion'],'particion')==expected['particion'],'OOF en partición incorrecta')
        exigir(numero(row['real'],'real')==expected['real'],'Etiqueta OOF distinta de T07')
        pred=numero(row['prediccion'],'prediccion')
        exigir(row['fuente']==expected['fuente'],'Respaldo OOF distinto de referencia común')
        if c=='media_mun__resp_grupo':
            exigir(math.isclose(pred,expected['referencia'],abs_tol=ATOL,rel_tol=RTOL),'Referencia no reproduce T08')
    candidates=sorted(versions)
    exigir(candidato_esperado is None or candidates==[candidato_esperado],'Candidato distinto del declarado')
    for c in candidates:
        exigir(len(versions[c])==1,'Se mezclan versiones de un candidato')
        exigir({k for cand,k in keys if cand==c}==set(contexts),'OOF incompleto: cada candidato requiere 1380 claves A/B')
    return {'candidatos':candidates,'predicciones':len(rows),'referencia_verificada':bool('media_mun__resp_grupo' in candidates),'integridad_OOF':True,'metodo_comun_acreditado':False}


def cargar_entradas(raiz=RAIZ):
    raiz=Path(raiz);cfg=cargar_diseno(raiz)
    load=lambda n:leer_csv(raiz/n)[1]
    roles=json.loads((raiz/'registro/t07/contrato_columnas.json').read_text())
    manifest=json.loads((raiz/'registro/t07/manifest.json').read_text())
    for n,h in manifest['archivos_sha256'].items():exigir(sha(raiz/'registro/t07'/n)==h,'Entrega T07 alterada: '+n)
    t,known,reserved=validar_tabla(load('registro/t07/tabla_comun.csv'),load('analisis/auditoria_catalogo_y_etiquetas/tablas/catalogo_parcelas.csv'),roles,load('registro/t07/calidad_relieve.csv'))
    cab,p=leer_csv(raiz/'registro/t03/particiones.csv')
    validar_particiones(cab,p,t,known,load('registro/t03/soporte_parcelas.csv'))
    qc=load('registro/t07/calidad_parcelas.csv');exigir(set(indexar(qc,['id_parcela']))==set(t),'Calidad no cubre 197 IDs')
    contexts=contextos(t,p)
    base=load('registro/t03/predicciones_oof_referencias_media_mun__resp_grupo.csv')
    validar_oof(base,contexts,'media_mun__resp_grupo')
    return {'config':cfg,'tabla':t,'conocidos':known,'reservados':reserved,'particiones':p,'contextos':contexts,'roles':roles}


def validar_experimento(experimento, entradas):
    exigir(experimento.get('schema')=='experimento_comun_v1','Experimento incompatible')
    exigir(experimento.get('sha_procedimiento')==DISENO_SHA,'Experimento usa otro procedimiento')
    exigir(experimento.get('estado')=='registrado_antes_de_ejecutar','Debe registrarse antes de ejecutar')
    exigir(bool(experimento.get('id')) and bool(experimento.get('responsable')) and bool(experimento.get('hipotesis')),'Falta identidad/hipótesis')
    procs=experimento.get('procedimientos',[]);exigir(1<=len(procs)<=8,'Presupuesto: 1–8 procedimientos por experimento')
    exigir(len({p['candidato'] for p in procs})==len(procs),'Candidatos duplicados')
    allow=set(entradas['roles']['columnas_por_funcion']['predictor_candidato'])-{'municipio'}
    quality=set(entradas['roles']['columnas_por_funcion']['calidad'])
    for p in procs:
        name=p['candidato'];exigir(isinstance(name,str) and name.strip()==name and name and name!='media_mun__resp_grupo','Identificador de candidato inválido')
        exigir(all(isinstance(p.get(flag,False),bool) for flag in ['area_explicita','calidad_explicita']), 'Autorización de rol requiere booleano explícito')
        opts=p.get('opciones',[]);exigir(1<=len(opts)<=8,'Máximo ocho opciones con variables por procedimiento')
        seen=set()
        for o in opts:
            cols=o['columnas'];exigir(bool(cols) and len(cols)==len(set(cols)),'Columnas vacías/duplicadas')
            permitted=allow|({'area_ha_origen'} if p.get('area_explicita') else set())|(quality if p.get('calidad_explicita') else set())
            exigir(set(cols)<=permitted,'Rol prohibido o metadato no autorizado como predictor')
            exigir(o['lambda_reg'] in [0.01,.1,1.,10.] and o['ventana'] in ['abr_oct','jun_oct','estatica'],'Opción fuera de búsqueda común')
            key=(tuple(cols),o['ventana'],o['lambda_reg']);exigir(key not in seen,'Opción duplicada');seen.add(key)
        por_ventana={}
        for o in opts:
            exigir(all(c in entradas['tabla'][next(iter(entradas['tabla']))] for c in o['columnas']), 'Columna no existente en T07')
            exigir(not isinstance(o['lambda_reg'], bool), 'λ booleano no permitido')
            temporal={c.rsplit('_',2)[-2]+'_'+c.rsplit('_',2)[-1] for c in o['columnas'] if c.endswith(('abr_oct','jun_oct'))}
            exigir(not temporal or temporal=={o['ventana']}, 'Ventanas mezcladas o mal declaradas')
            por_ventana.setdefault(o['ventana'],[]).append(o)
        for w,ls in por_ventana.items():
            exigir({o['lambda_reg'] for o in ls}=={.01,.1,1.,10.} and len(ls)==4, 'Cada ventana requiere las mismas cuatro λ')
            exigir(len({tuple(o['columnas']) for o in ls})==1, 'Columnas cambian entre valores λ de una ventana')
    return {'procedimientos':len(procs),'opciones_con_variables':sum(len(p['opciones']) for p in procs),'referencia_adicional_sin_busqueda':True}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--raiz',type=Path,default=RAIZ);p.add_argument('--oof',type=Path,action='append',default=[]);p.add_argument('--experimento',type=Path)
    args=p.parse_args()
    try:
        e=cargar_entradas(args.raiz)
        out={'resultado':'verificado','procedimiento_sha256':DISENO_SHA,'etiquetadas':len(e['conocidos']),'reservadas':len(e['reservados']),'contextos_OOF':len(e['contextos']),'modelos_ajustados':0,'estado_procedimiento':e['config']['estado']}
        if args.oof:out['OOF']=[{'archivo':str(f),**validar_oof(leer_csv(f)[1],e['contextos'])} for f in args.oof]
        if args.experimento:out['experimento']=validar_experimento(json.loads(args.experimento.read_text()),e)
    except (ValueError,OSError,KeyError,TypeError,json.JSONDecodeError) as exc:p.exit(1,'Contrato común rechazado: '+str(exc)+'\n')
    print(json.dumps(out,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
