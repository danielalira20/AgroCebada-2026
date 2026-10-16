"""Auditor T15 portable: verifica la entrega, sin entrenar ni importar el productor.

Adaptación del auditor local registrado el 16-oct-2026. Sólo cambia E/S:
rutas relativas, gzip, fuentes históricas por Git y salida nueva explícita.
"""
import argparse
import csv, gzip, hashlib, json, math, statistics, subprocess
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--entrega', type=Path, default=ROOT/'registro/t15_resultados')
parser.add_argument('--solo-integridad', action='store_true', help='Huellas y fuentes, sin NumPy ni modelos.')
parser.add_argument('--salida', type=Path, help='JSON nuevo de auditoría; obligatorio para la revisión numérica.')
args = parser.parse_args()
OUT = args.entrega.resolve()
RUN = OUT
if not args.solo_integridad:
    if args.salida is None:
        parser.error('La revisión numérica requiere --salida con un destino nuevo.')
    args.salida = args.salida.resolve()
    if args.salida.exists():
        parser.error('La salida existe; elegir otro nombre.')
    if args.salida.is_relative_to(ROOT) and not args.salida.is_relative_to(ROOT/'reports'):
        parser.error('Dentro del repo la salida sólo se permite en reports/.')

def artifact_path(path):
    path = Path(path)
    return path if path.is_file() else path.with_name(path.name + '.gz')

def artifact_sha(path):
    actual = artifact_path(path)
    opener = gzip.open if actual.suffix == '.gz' else open
    digest = hashlib.sha256()
    with opener(actual, 'rb') as handle:
        for block in iter(lambda: handle.read(1024*1024), b''):
            digest.update(block)
    return digest.hexdigest()

def historical_sha(path, commit):
    result = subprocess.run(['git', '-C', str(ROOT), 'show', f'{commit}:{path}'],
                            check=True, capture_output=True)
    return hashlib.sha256(result.stdout).hexdigest()

def require(condition, message):
    if not condition:
        raise ValueError(message)

publication = json.loads((OUT/'entrega.json').read_text())
manifest_original = json.loads((OUT/'manifest.json').read_text())
frozen = json.loads((OUT/'registro_inicio.json').read_text())
commit = manifest_original['fuente_commit']
require(commit == frozen['commit'] == publication['commit_ejecucion'], 'Commit de ejecución inconsistente')
require(hashlib.sha256(Path(__file__).read_bytes()).hexdigest() == publication['auditor_portable_sha256'], 'Auditor portable distinto del registrado')
for path, expected in publication['artefactos_sha256'].items():
    require(hashlib.sha256((OUT/path).read_bytes()).hexdigest() == expected, 'Paquete alterado: '+path)
for path, expected in manifest_original['archivos_sha256'].items():
    require(artifact_sha(OUT/path) == expected, 'Salida original alterada: '+path)

# Reject changes to every computational input/code read by the original run.
# Documentation/logs may have been appended for publication; their old bytes are
# checked against the frozen Git commit, never passed off as current bytes.
critical = dict(manifest_original['fuentes_sha256'])
critical.update(manifest_original['codigo_sha256'])
critical.update({
    'registro/t15_contrato/contrato_v1.json': manifest_original['contrato_sha256'],
    'registro/t15_contrato/registro_operativo_v1.json': manifest_original['registro_operativo_sha256'],
})
for path, expected in critical.items():
    require(hashlib.sha256((ROOT/path).read_bytes()).hexdigest() == expected, 'Entrada/código actual distinto: '+path)
historical_count = 0
for path, expected in frozen['fuentes_sha256'].items():
    current = ROOT/path
    if current.is_file() and hashlib.sha256(current.read_bytes()).hexdigest() == expected:
        continue
    require(path not in critical, 'Fuente crítica modificada: '+path)
    require(historical_sha(path, commit) == expected, 'Fuente histórica distinta: '+path)
    historical_count += 1
if args.solo_integridad:
    print(json.dumps({'resultado':'integridad_verificada', 'commit_ejecucion':commit,
                      'artefactos_publicados':len(publication['artefactos_sha256']),
                      'artefactos_originales':len(manifest_original['archivos_sha256']),
                      'fuentes_fijadas':len(frozen['fuentes_sha256']),
                      'fuentes_actuales_computacionales':len(critical),
                      'fuentes_historicas_consultadas_en_Git':historical_count,
                      'ajustes_nuevos':0}, ensure_ascii=False, indent=2))
    raise SystemExit(0)

import numpy as np
from sklearn.model_selection import StratifiedKFold, GroupKFold

TOL={'referencias_metricas':1e-12,'matrices_coeficientes':1e-10,'prediccion_reconstruida':1e-9}
N=0;MAX=defaultdict(float)

def check(ok,msg):
    global N
    N+=1
    if not ok:raise ValueError(msg)

def close(a,b,contexto,clase='referencias_metricas'):
    if a is None or a=='':check(b is None or b=='',contexto);return
    a,b=float(a),float(b);check(math.isfinite(a) and math.isfinite(b),contexto+' finito')
    delta=abs(a-b);MAX[clase]=max(MAX[clase],delta)
    check(delta<=TOL[clase],f'{contexto}: {a} != {b}, delta={delta}')

def matrix(a,b,contexto):
    a,b=np.asarray(a,float),np.asarray(b,float)
    check(a.shape==b.shape,contexto+' forma')
    delta=float(np.max(abs(a-b))) if a.size else 0.
    MAX['matrices_coeficientes']=max(MAX['matrices_coeficientes'],delta)
    check(delta<=TOL['matrices_coeficientes'],f'{contexto}: delta={delta}')

def csvread(p):
    with Path(p).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))

def jsonlines(p):
    actual=artifact_path(p)
    opener=gzip.open if actual.suffix=='.gz' else open
    with opener(actual,'rt',encoding='utf-8') as f:
        for line in f:yield json.loads(line)

REFCACHE={}
def ref(ids,pid,exclude=None):
    key=(tuple(ids),pid,exclude)
    if key in REFCACHE:return REFCACHE[key]
    pool=[i for i in ids if i!=exclude]
    mun=[i for i in pool if TABLE[i]['municipio']==TABLE[pid]['municipio']]
    grp=[i for i in pool if TABLE[i]['cultivo_origen']==TABLE[pid]['cultivo_origen']]
    for fuente,group in [('municipio',mun),('grupo',grp),('global',pool)]:
        if group:
            value=(statistics.fmean(Y[i] for i in group),fuente,group)
            REFCACHE[key]=value
            return value
    raise ValueError('Sin referencia')

def contexto(esc,rep,fold):
    col='particion_principal' if esc=='A' else 'particion_espacial'
    rows=[r for r in PARTS if int(r['repeticion'])==rep]
    return sorted(r['ID_POLIGONO'] for r in rows if int(r[col])!=fold),sorted(r['ID_POLIGONO'] for r in rows if int(r[col])==fold)

def metricas(rows):
    if not rows:return dict(n=0,MAE=None,RMSE=None,sesgo=None,R2=None)
    ys=[float(r['real']) for r in rows];ps=[float(r['prediccion']) for r in rows]
    errors=[p-y for y,p in zip(ys,ps)];mu=statistics.fmean(ys)
    mse=statistics.fmean(e*e for e in errors);den=math.fsum((y-mu)**2 for y in ys)
    return dict(n=len(rows),MAE=statistics.fmean(abs(e) for e in errors),RMSE=math.sqrt(mse),sesgo=statistics.fmean(errors),R2=None if len(set(ys))==1 else 1-math.fsum(e*e for e in errors)/den)

# Cargar y fijar fuentes; no se abre la salida de evaluación hasta estas comprobaciones.
TABLE={r['id_parcela']:r for r in csvread(ROOT/'registro/t07/tabla_comun.csv')}
Y={i:float(r['rendimiento_t_ha']) for i,r in TABLE.items() if r['rendimiento_t_ha']!=''}
RESERVED=set(TABLE)-set(Y)
PARTS=csvread(ROOT/'registro/t03/particiones.csv')
CELLS={r['ID_POLIGONO']:r['celda_chirps'] for r in PARTS}
CFG=json.loads((ROOT/'registro/t15_contrato/contrato_v1.json').read_text())
PROCS={p['candidato']:p for p in CFG['principal']['procedimientos']}
BASE='media_mun__resp_grupo'
VERSION=CFG['metodo']['version']
QUALITY={r['id_parcela']:r for r in csvread(ROOT/'registro/t07/calidad_parcelas.csv')}
check((len(TABLE),len(Y),len(RESERVED))==(197,138,59),'Universo 197/138/59')
check(set(r['ID_POLIGONO'] for r in PARTS)==set(Y),'Particiones sólo etiquetadas')
for path,h in json.loads((OUT/'registro_inicio.json').read_text())['fuentes_sha256'].items():
    check((hashlib.sha256((ROOT/path).read_bytes()).hexdigest() if (ROOT/path).is_file() and hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==h else historical_sha(path,commit))==h,'Fuente fijada no verificable: '+path)
manifest=json.loads((RUN/'manifest.json').read_text())
check(manifest['estado']=='completa_verificada' and manifest['evaluacion_completa'] is True,'Entrega incompleta')
check(manifest['fuente_commit']=='cc7d0ae5437490d63408d74b4a3693a7b4494d55','Commit distinto del fijado')
for path,h in manifest['archivos_sha256'].items():check(artifact_sha(RUN/path)==h,'Artefacto modificado '+path)
check(manifest['contadores']['ajustes_internos']==13600 and manifest['contadores']['Ridge_internos']==12000,'Presupuesto interno')
check(manifest['contadores']['ajustes_externos']==450 and manifest['contadores']['Ridge_externos']<=400,'Presupuesto externo')

# Particiones internas reconstruidas con librería pública desde CSV, no desde productor.
INNER={};EXTERNAL={}
for esc in ['A','B']:
    for rep in range(1,6):
        for fold in range(5):
            train,test=contexto(esc,rep,fold);EXTERNAL[esc,rep,fold]=(train,test)
            check(set(train).isdisjoint(test) and set(train)|set(test)==set(Y),'Contexto externo')
            if esc=='A':
                counts=Counter(TABLE[i]['municipio'] for i in train)
                strata=[TABLE[i]['municipio'] if counts[TABLE[i]['municipio']]>=4 else 'otros' for i in train]
                splits=StratifiedKFold(4,shuffle=True,random_state=0).split(train,strata)
            else:splits=GroupKFold(4,shuffle=False).split(train,groups=[CELLS[i] for i in train])
            for k,(a,b) in enumerate(splits):INNER[esc,rep,fold,k]=([train[i] for i in a],[train[i] for i in b])

OOF=csvread(RUN/'predicciones_oof.csv');OIDX={}
for r in OOF:
    esc,rep,fold,pid=r['escenario'],int(r['repeticion']),int(r['particion']),r['ID_POLIGONO']
    key=r['candidato'],esc,rep,pid
    check(key not in OIDX and r['candidato'] in set(PROCS)|{BASE},'OOF duplicada/candidato ajeno')
    OIDX[key]=r;check(pid in Y and pid not in RESERVED and r['version']==VERSION,'OOF universo/versión')
    train,test=EXTERNAL[esc,rep,fold];check(pid in test,'OOF partición')
    close(r['real'],Y[pid],'Etiqueta original')
    value,source,_=ref(train,pid);check(r['fuente']==source,'Fuente de referencia externa')
    check(math.isfinite(float(r['prediccion'])),'Predicción no finita')
    if r['candidato']==BASE:close(r['prediccion'],value,'Referencia original')
check(len(OOF)==12420 and len(OIDX)==12420,'OOF completa')
for candidate in set(PROCS)|{BASE}:
    check({(s,k,i) for c,s,k,i in OIDX if c==candidate}=={(s,k,i) for s in ['A','B'] for k in range(1,6) for i in Y},'Cobertura por candidato')

SELECTIONS=list(jsonlines(RUN/'selecciones.jsonl'))
SINDEX={(s['candidato'],s['escenario'],s['repeticion'],s['particion']):s for s in SELECTIONS}
check(len(SELECTIONS)==len(SINDEX)==400,'Selecciones completas únicas')
SCORES=defaultdict(list);TRACE_STATE={};TRACE_PARAMS={};seen=set();counts=Counter()
for t in jsonlines(RUN/'trazas_ajustes.jsonl'):
    candidate,esc,rep,fold=t['candidato'],t['escenario'],t['repeticion'],t['particion']
    exttrain,exttest=EXTERNAL[esc,rep,fold]
    if t['etapa']=='interna':
        train,test=INNER[esc,rep,fold,t['division_interna']]
        key=(candidate,esc,rep,fold,t['opcion'],t['division_interna'])
        SCORES[candidate,esc,rep,fold,t['opcion']].append(t)
    else:
        train,test=exttrain,exttest;key=(candidate,esc,rep,fold,'externa')
        TRACE_STATE[candidate,esc,rep,fold]=t['estado_modelo_sha256']
        TRACE_PARAMS[candidate,esc,rep,fold]={k:t[k] for k in ['columnas','lambda_reg','alpha','version']}
    check(key not in seen,'Ajuste duplicado');seen.add(key)
    counts[t['etapa']]+=1
    check(t['estado']=='correcto' and not t['advertencias'],'Ajuste no correcto/advertencia')
    check(t['ids_entrenamiento']==train and t['ids_validacion']==test,'IDs del ajuste')
    check(not (set(train)|set(test))&RESERVED,'Reservadas dentro de ajuste')
    check(set(train).isdisjoint(test),'Solapamiento de ajuste')
    if t['etapa']=='interna':check(set(train).isdisjoint(exttest) and set(test).isdisjoint(exttest),'Fuga evaluación externa')
    if esc=='B':check({CELLS[i] for i in train}.isdisjoint(CELLS[i] for i in test),'Fuga celda B')
    cm=Counter(TABLE[i]['municipio'] for i in train)
    eligible=[i for i in test if cm[TABLE[i]['municipio']]>0]
    check(t['ids_elegibles']==eligible and t['n_elegibles']==len(eligible),'Máscara interna/externa')
    check(t['n_entrenamiento']==len(train) and t['n_validacion']==len(test),'Tamaños fit')
    check(t['n_singleton_entrenamiento']==sum(n==1 for n in cm.values()),'Singleton entreno')
    check(t['n_validacion_referencia_una_etiqueta']==sum(cm[TABLE[i]['municipio']]==1 for i in test),'Referencia municipal n1')
    src=Counter(ref(train,i)[1] for i in test)
    check(t['fuentes_referencia']=={k:src[k] for k in ['municipio','grupo','global']},'Fuentes validación')
    if t['referencia_sola']:
        check(t['columnas']==[] and t['lambda_reg'] is None and t['alpha'] is None,'Referencia sola parámetros')
        check(all(v==0 for v in t['fuentes_centro_LOO'].values()),'Referencia sin centros LOO')
    else:
        check(t['lambda_reg'] in [.01,.1,1.,10.],'Lambda fuera de registro')
        close(t['alpha'],len(train)*t['lambda_reg'],'Alpha n lambda')
        if t['etapa']=='interna':
            name=t['opcion'];option=next((o for o in PROCS[candidate]['opciones'] if f"{o['ventana']}__lambda_{o['lambda_reg']:g}"==name),None)
        else:
            option=SINDEX[candidate,esc,rep,fold]
        check(option is not None and t['columnas']==option['columnas'] and t['lambda_reg']==option['lambda_reg'],'Columnas/opción registrada')
        src=Counter(ref(train,i,exclude=i)[1] for i in train)
        check(t['fuentes_centro_LOO']=={k:src[k] for k in ['municipio','grupo','global']},'Respaldo LOO')
    if 'pendiente_media_t10_grados' in t['columnas']:
        med=statistics.median(float(TABLE[i]['pendiente_media_t10_grados']) for i in train if TABLE[i]['pendiente_media_t10_grados']!='')
        close(t['mediana_pendiente'],med,'Imputación sólo entrenamiento')
check(counts==Counter(interna=13600,externa=450),'Número total trazas')

for s in SELECTIONS:
    alternatives=[]
    for score in s['puntuaciones']:
        ts=SCORES[s['candidato'],s['escenario'],s['repeticion'],s['particion'],score['nombre']]
        check(len(ts)==4,'Cuatro ajustes por opción')
        n=sum(t['n_elegibles'] for t in ts);nt=sum(t['n_validacion'] for t in ts)
        close(score['MAE'],math.fsum(t['MAE']*t['n_elegibles'] for t in ts)/n,'MAE interno ponderado')
        close(score['MAE_todas'],math.fsum(t['MAE_todas']*t['n_validacion'] for t in ts)/nt,'MAE interno todas')
        check(score['n_elegibles']==n and score['n_validacion']==nt,'Denominadores selección')
        alternatives.append(score)
    check(len(alternatives)==1+len(PROCS[s['candidato']]['opciones']),'Menú interno completo')
    key=lambda a:(round(a['MAE'],6),not a['referencia_sola'],-(a['lambda_reg'] or 0),a['ventana']!='jun_oct',a['nombre'])
    best=min(alternatives,key=key)
    check(s['nombre_opcion']==best['nombre'] and s['lambda_reg']==best['lambda_reg'],'Selección reproduce regla interna')

# Reconstruir todas las predicciones externas desde estados y resolver beta por álgebra independiente.
state_count=0;ridge_count=0
for saved in jsonlines(RUN/'estados_modelos.jsonl'):
    candidate,esc,rep,fold=saved['candidato'],saved['escenario'],saved['repeticion'],saved['particion']
    state=saved['estado_modelo'];train,test=EXTERNAL[esc,rep,fold];state_count+=1
    digest=hashlib.sha256(json.dumps(state,sort_keys=True,ensure_ascii=False,allow_nan=False,separators=(',',':')).encode()).hexdigest()
    check(digest==TRACE_STATE[candidate,esc,rep,fold],'Huella de estado externo')
    check(state['ids_entrenamiento']==train and state['n']==len(train),'Estado entreno')
    check({k:state[k] for k in ['columnas','lambda_reg','alpha','version']}==TRACE_PARAMS[candidate,esc,rep,fold],'Estado y traza misma configuración')
    check(state['version']==manifest['version'] and state['sha_procedimiento']==CFG['metodo']['sha256'],'Estado versión/metodología registrada')
    check(state['fit_intercept'] is False and state['intercepto']==0. and state['reescalar_intramunicipal'] is False,'Sin intercepto ni escala intramunicipal nueva')
    for mun,mu in state['municipio'].items():close(mu,statistics.fmean(Y[i] for i in train if TABLE[i]['municipio']==mun),'Media municipal entreno')
    for group,mu in state['grupo'].items():close(mu,statistics.fmean(Y[i] for i in train if TABLE[i]['cultivo_origen']==group),'Media de respaldo por grupo')
    close(state['global'],statistics.fmean(Y[i] for i in train),'Media global entreno')
    if not state['columnas']:
        check(state['lambda_reg'] is None,'Estado referencia sola')
        for pid in test:
            value,_,_=ref(train,pid)
            close(OIDX[candidate,esc,rep,pid]['prediccion'],value,'Predicción seleccionada de referencia sola','prediccion_reconstruida')
        continue
    ridge_count+=1;cols=state['columnas']
    close(state['alpha'],len(train)*state['lambda_reg'],'Alpha del estado n lambda')
    def valores(ids):
        arr=np.array([[float(TABLE[i][c]) if TABLE[i][c]!='' else np.nan for c in cols] for i in ids])
        if 'area_ha_origen' in cols:arr[:,cols.index('area_ha_origen')]=np.log(arr[:,cols.index('area_ha_origen')])
        if 'pendiente_media_t10_grados' in cols:
            j=cols.index('pendiente_media_t10_grados');missing=np.isnan(arr[:,j]);arr[missing,j]=state['mediana_pendiente'];arr=np.column_stack([arr,missing.astype(float)])
        return arr
    a,b=valores(train),valores(test);mu=a.mean(0);sd=a.std(0);sd[sd==0]=1
    matrix(state['media'],mu,'Media escalado');matrix(state['escala'],sd,'Escala entreno')
    z,zq=(a-mu)/sd,(b-mu)/sd;positions={i:j for j,i in enumerate(train)}
    residual=[];centers=[]
    for n,pid in enumerate(train):
        value,source,pool=ref(train,pid,exclude=pid)
        check(pid not in pool,'Propia fila en pool LOO')
        check(state['pools_sin_fila'][pid]==dict(fuente=source,n=len(pool),ids=pool),'Pool LOO exacto')
        center=z[[positions[i] for i in pool]].mean(0)
        matrix(state['centros_Z_sin_fila'][pid],center,'Centro LOO sin fila')
        residual.append(Y[pid]-value);centers.append(center)
    D=z-np.asarray(centers);beta=np.linalg.solve(D.T@D+state['alpha']*np.eye(D.shape[1]),D.T@np.asarray(residual))
    matrix(state['coeficientes'],beta,'Beta por ecuaciones normales')
    for n,pid in enumerate(test):
        value,source,pool=ref(train,pid);center=z[[positions[i] for i in pool]].mean(0)
        if source=='municipio':matrix(state['centros_Z_municipio'][TABLE[pid]['municipio']],center,'Centro guardado municipal')
        pred=value+(zq[n]-center)@beta
        close(OIDX[candidate,esc,rep,pid]['prediccion'],pred,'Predicción reconstruida H3','prediccion_reconstruida')
    for mun in {TABLE[i]['municipio'] for i in train}:
        loc=[positions[i] for i in train if TABLE[i]['municipio']==mun]
        corrections=(z[loc]-z[loc].mean(0))@beta
        check(abs(float(corrections.mean()))<=1e-12,'Corrimiento municipal artificial al predecir entrenamiento')
check(state_count==450 and ridge_count==manifest['contadores']['Ridge_externos'],'Estados completos')

# Recalcular métricas sin importar las funciones de reportes del productor.
def resumen_independiente(rows):
    byid,byrep=defaultdict(list),defaultdict(list)
    for row in rows:byid[row['ID_POLIGONO']].append(row);byrep[int(row['repeticion'])].append(row)
    if not rows:return dict(n_parcelas=0,n_predicciones=0,n_repeticiones=0,MAE_por_parcela=None,RMSE_igual_peso_parcela=None,sesgo_por_parcela=None,R2_igual_peso_parcela=None,R2_estado='sin_casos',MAE_media_repeticiones=None,RMSE_media_repeticiones=None,R2_media_repeticiones=None,p90_MAE_parcela=None,n_parcelas_MAE_mayor_1=None)
    ids=[metricas(v) for _,v in sorted(byid.items())];reps=[metricas(v) for _,v in sorted(byrep.items())]
    ys=[float(v[0]['real']) for _,v in sorted(byid.items())]
    mse=statistics.fmean(m['RMSE']**2 for m in ids);den=statistics.fmean((y-statistics.fmean(ys))**2 for y in ys)
    constant=len(set(ys))==1
    return dict(n_parcelas=len(byid),n_predicciones=len(rows),n_repeticiones=len(byrep),
        MAE_por_parcela=statistics.fmean(m['MAE'] for m in ids),RMSE_igual_peso_parcela=math.sqrt(mse),
        sesgo_por_parcela=statistics.fmean(m['sesgo'] for m in ids),R2_igual_peso_parcela=None if constant else 1-mse/den,
        R2_estado='objetivo_constante' if constant else 'definido',MAE_media_repeticiones=statistics.fmean(m['MAE'] for m in reps),
        RMSE_media_repeticiones=statistics.fmean(m['RMSE'] for m in reps),R2_media_repeticiones=None if any(m['R2'] is None for m in reps) else statistics.fmean(m['R2'] for m in reps),
        p90_MAE_parcela=float(np.percentile([m['MAE'] for m in ids],90)),n_parcelas_MAE_mayor_1=sum(m['MAE']>1 for m in ids))

def rows_of(candidate,esc,subset):return [r for r in OOF if r['candidato']==candidate and r['escenario']==esc and (subset=='todas' or r['fuente']=='municipio')]

def comparar_campos(actual,expected,contexto):
    for k,v in expected.items():
        if isinstance(v,str):check(actual[k]==v,contexto+'/'+k)
        else:close(actual[k],v,contexto+'/'+k)

for row in csvread(RUN/'metricas_resumen.csv'):
    picked=rows_of(row['candidato'],row['escenario'],row['subconjunto'])
    comparar_campos(row,resumen_independiente(picked),'Resumen independiente')
for row in csvread(RUN/'metricas_por_repeticion.csv'):
    picked=[r for r in rows_of(row['candidato'],row['escenario'],row['subconjunto']) if r['repeticion']==row['repeticion']]
    m=metricas(picked);m['R2_estado']='objetivo_constante' if len(set(float(r['real']) for r in picked))==1 else 'definido'
    comparar_campos(row,m,'Métricas por repetición')

ALERTS={i for i in Y if QUALITY[i]['alerta_contorno_t03_bis']=='si'}
check(len(ALERTS)==24,'24 parcelas de sensibilidad')
for row in csvread(RUN/'desgloses_calidad_y_sin24.csv'):
    picked=rows_of(row['candidato'],row['escenario'],row['subconjunto'])
    name,val=row['desglose'],row['valor']
    if name=='sensibilidad_sin24':picked=[r for r in picked if r['ID_POLIGONO'] not in ALERTS]
    else:
        def value(pid):
            if name=='municipio':return TABLE[pid]['municipio']
            if name=='grupo_registro':return TABLE[pid]['cultivo_origen']
            return QUALITY[pid][name] or 'no_documentado'
        picked=[r for r in picked if value(r['ID_POLIGONO'])==val]
    comparar_campos(row,resumen_independiente(picked),'Desglose independiente '+name)

# Contrastes, remuestreo por celda y sensibilidad por parcela.
for row in csvread(RUN/'contrastes.csv'):
    ca,cb,esc,subset=row['candidato'],row['frente_a'],row['escenario'],row['subconjunto']
    pairs=defaultdict(list);byrep=defaultdict(list)
    for (candidate,s,rep,pid),r in sorted(OIDX.items()):
        if candidate!=ca or s!=esc or (subset=='sin_respaldo' and r['fuente']!='municipio'):continue
        b=OIDX[cb,s,rep,pid];y=float(r['real']);ea=float(r['prediccion'])-y;eb=float(b['prediccion'])-y
        values=np.array([abs(ea),abs(eb),ea*ea,eb*eb]);pairs[pid].append(values);byrep[rep].append(values)
    ids=sorted(pairs);a={i:np.mean(pairs[i],axis=0) for i in ids}
    delta=statistics.fmean(float(a[i][0]-a[i][1]) for i in ids)
    rep_means={r:np.mean(values,axis=0) for r,values in byrep.items()}
    dreps=[float(rep_means[r][0]-rep_means[r][1]) for r in range(1,6)]
    drmse=statistics.fmean(math.sqrt(rep_means[r][2])-math.sqrt(rep_means[r][3]) for r in range(1,6))
    close(row['dMAE'],delta,'ΔMAE por parcela');close(row['dRMSE'],drmse,'ΔRMSE medio repetición')
    matrix(json.loads(row['dMAE_por_repeticion']),dreps,'ΔMAE repeticiones')
    groups=defaultdict(list)
    for pid in ids:groups[CELLS[pid]].append(a[pid])
    blocks=sorted(groups);sums=np.array([np.sum(groups[k],axis=0) for k in blocks]);sizes=np.array([len(groups[k]) for k in blocks])
    rng=np.random.RandomState(20261006);ix=rng.randint(len(blocks),size=(5000,len(blocks)))
    sample_n=sizes[ix].sum(1);sample=sums[ix].sum(1)/sample_n[:,None]
    lo,hi=np.percentile(sample[:,0]-sample[:,1],[2.5,97.5])
    clo,chi=json.loads(row['IC95_celdas_MAE']);close(clo,lo,'IC celda inferior');close(chi,hi,'IC celda superior')
    rm=np.percentile(np.sqrt(sample[:,2])-np.sqrt(sample[:,3]),[2.5,97.5])
    matrix(json.loads(row['IC95_celdas_RMSE']),rm,'IC RMSE por celda')
    dvalues=np.array([a[i][0]-a[i][1] for i in ids]);rng=np.random.RandomState(20261006)
    vals=[]
    for start in range(0,5000,100):vals.extend(dvalues[rng.randint(len(ids),size=(100,len(ids)))].mean(1))
    matrix(json.loads(row['IC95_parcelas_MAE_descriptivo']),np.percentile(vals,[2.5,97.5]),'IC parcelas descriptivo')
    improves=sum(v<0 for v in dreps);rule=delta<=-.01 and hi<0 and improves>=4 and drmse<=.01
    check(int(row['repeticiones_mejoran_MAE'])==improves,'Signos por repetición')
    check(row['cumple_regla_T03']==str(bool(rule)),'Regla T03')
    eligible=rule and esc=='A' and subset=='sin_respaldo' and row['tipo_contraste']=='promocion'
    check(row['elegible_para_promocion_principal']==str(bool(eligible)),'Promoción de contraste descriptivo')
    check(int(row['n_parcelas'])==len(ids) and int(row['n_predicciones'])==sum(len(v) for v in pairs.values()),'Denominadores contraste')

for row in csvread(RUN/'frecuencia_referencia_sola.csv'):
    ss=[s for s in SELECTIONS if s['candidato']==row['candidato'] and s['escenario']==row['escenario']]
    check(len(ss)==int(row['n_contextos'])==25 and row['estado']=='completo','Frecuencia completa')
    n=sum(s['referencia_sola'] for s in ss)
    check(n==int(row['n_referencia_sola']) and 25-n==int(row['n_con_correccion']),'Recuento referencias')
    close(row['fraccion_referencia_sola'],n/25,'Proporción referencia')

summary={'resultado':'verificado','auditor_importa_productor':False,'tolerancias_fijadas_antes_de_ver_resultados':TOL,'comprobaciones':N,'maximos_observados':dict(MAX),'OOF_verificadas':len(OOF),'selecciones_verificadas':len(SELECTIONS),'trazas_verificadas':dict(counts),'estados_externos':state_count,'Ridge_externos_reconstruidos':ridge_count,'fuentes_ejecucion_fijada_verificadas':True,'entradas_actuales_computacionales_intactas':True,'fuentes_historicas_consultadas_en_Git':historical_count,'fugas_por_ID_grupo_reservadas_detectadas':0,'columnas_y_parametros_fuera_registro':0,'limite':'Verifica datos, trazas, álgebra y reportes; la selección humana previa no es validación externa ciega. No garantiza exactitud de medición en campo ni otra campaña.','script_auditor_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
summary['adaptacion_portable_del_auditor_sha256']=publication['auditor_original_sha256']
args.salida.parent.mkdir(parents=True,exist_ok=True)
with args.salida.open('x',encoding='utf-8') as handle:
    handle.write(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(summary,ensure_ascii=False,indent=2))
