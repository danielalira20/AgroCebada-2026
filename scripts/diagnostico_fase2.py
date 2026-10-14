"""Fase2: comparaciones históricas e influencia analítica de la referencia.

No importa estimadores, no aprende parámetros ni construye un predictor mixto.
"""
import argparse
from collections import defaultdict, Counter
import hashlib
import json
import math
from pathlib import Path
import struct
import tempfile

from scripts import diagnostico_fase0 as f0, diagnostico_fase1 as f1
from scripts.diagnostico_fuentes import exigir, hash_archivo, json_estricto, ruta_segura

RAIZ = Path(__file__).resolve().parents[1]
DISENO = 'registro/diagnostico/fase2_diseno.json'
DISENO_SHA = '03cf3cf4cb1eef8e554fad92da3466e1f360179adbbf03f66297e71c443ea93b'
POPS = ('todas', 'sin_respaldo')
EPS = 1e-9


def cambio(v):
    return 'mejora_numerica' if v < -EPS else 'deterioro_numerico' if v > EPS else 'sin_cambio_numerico'


def corr(x, y):
    exigir(len(x) == len(y), 'Pares no alineados')
    if len(x) < 2: return ''
    mx = f1.media(x); my = f1.media(y)
    xx = [v-mx for v in x]; yy = [v-my for v in y]
    ssx = math.fsum(v*v for v in xx); ssy = math.fsum(v*v for v in yy)
    return math.fsum(a*b for a,b in zip(xx,yy))/math.sqrt(ssx*ssy) if ssx and ssy else ''


def metodo(row):
    task, candidate = row['fuente'], row['candidato']
    reference = candidate in ('T','referencia','media_mun__resp_grupo')
    if reference: return 'media_municipio_grupo_global_T08', 'no_aplica', 'no_aplica', True
    if task == 'T09':
        if candidate == 'R_centrado': return 'residuo_LOO_Ridge_nlambda', 'municipal_con_escala_global', 'sin_intercepto', False
        if candidate == 'R': return 'residuo_LOO_Ridge_nlambda', 'sin_centrar_municipio', 'sin_intercepto', False
        if candidate == 'TC': return 'ajuste_conjunto_X_y_territorial_Ridge_nlambda', 'municipal_con_escala_global', 'municipal_no_penalizado', False
    if task == 'T10':
        center = 'municipal_y_escala_intra' if 'config6' in candidate else 'sin_centrar_municipio'
        method = 'residuo_Ridge_puente_seleccion_cuadratica' if candidate.startswith('puente_') else 'residuo_Ridge_T10_seleccion_MAE_ref_sola'
        return method, center, 'aprendido', False
    if task in ('T11','T13'):
        return 'residuo_Ridge_T11_seleccion_cuadratica', 'municipal_y_escala_intra' if task=='T11' and '_c8_' in candidate else 'sin_centrar_municipio', 'aprendido', False
    if task == 'T14': return 'residuo_LOO_Ridge_clima_ponderacion_dias_T14', 'sin_centrar_municipio', 'aprendido', False
    raise ValueError('Método sin clasificar: '+candidate)


def cargar(fase0, fuentes):
    exigir(hash_archivo(RAIZ/DISENO)==DISENO_SHA, 'Diseño fase2 cambió')
    base, table, known, cases, controls = f1.cargar(fase0, fuentes)
    _, fm = f0.configuracion(RAIZ)
    declared = f0.csv_completo(ruta_segura(fase0, 'compatibilidad_procedimientos.csv'))
    groups = defaultdict(dict); omitted = 0
    for r in f0.csv_completo(ruta_segura(fase0, 'normalizadas_oof.csv')):
        if r['escenario']=='C': omitted += 1; continue
        g = tuple(r[k] for k in ('fuente','archivo','candidato','variante','version'))
        key = (r['escenario'],int(r['repeticion']),r['id_parcela'])
        exigir(key not in groups[g], 'Duplicación de contexto')
        v = {**r, 'repeticion':int(r['repeticion']), 'particion':int(r['particion']),
             'real':f0.numero(r['real'],'y'), 'prediccion':f0.numero(r['prediccion'],'pred')}
        v.update(f1.errores(v)); groups[g][key] = v
    expected = {(r['escenario'],r['repeticion'],r['id_parcela']) for r in base}
    dec = {tuple(r[k] for k in ('fuente','archivo','candidato','variante','version')) for r in declared}
    exigir(set(groups)==dec and len(groups)==51 and omitted==828, 'Series/C distintas del snapshot')
    exigir(sum(len(v) for v in groups.values())==70380, 'Censo A/B incompleto')
    catalog = []; indexed = {}; task_key = {'T08':'base','T09':'t09','T10':'t10','T11':'t11','T13':'t13','T14':'t14'}
    base_by = {(r['escenario'],r['repeticion'],r['id_parcela']):r for r in base}
    for i,(g,rr) in enumerate(sorted(groups.items()),1):
        exigir(set(rr)==expected, 'Contextos por serie incompletos')
        for k,r in rr.items():
            b=base_by[k]
            exigir(r['particion']==b['particion'] and r['real']==b['real'] and r['fuente_referencia']==b['fuente_referencia'], 'Identidad y máscara distintas')
        meta = dict(zip(('fuente','archivo','candidato','variante','version'),g)); sid=f'S{i:03d}'
        method, center, intercept, ref = metodo(meta)
        family = 'T13e' if 't13e.csv' in meta['archivo'] else meta['fuente']
        scope = 'suplementario' if meta['fuente']=='T13' else 'adicional_plan' if meta['fuente']=='T14' else 'principal_plan'
        src=fm['fuentes'][task_key[meta['fuente']]]
        fingerprint=hashlib.sha256(b''.join(struct.pack('>d',rr[k]['prediccion']) for k in sorted(expected))).hexdigest()
        catalog.append(dict(serie_id=sid,**meta,frente=family,ambito=scope,metodo=method,centrado=center,
                            intercepto=intercept,es_referencia=ref,commit_fuente=src['commit'],
                            estado_revision_fuente=src['estado'],filas_AB=1380,firma_pred_AB=fingerprint,
                            metodo_comun_acreditado=False))
        indexed[sid]=rr
    exigir(sum(r['es_referencia'] for r in catalog)==7, 'Referencias duplicadas inesperadas')
    return base_by, table, known, cases, controls, catalog, indexed


def comparar(base, known, cases, controls, catalog, indexed):
    matrix=[]; summaries=[]; reps=[]
    fixed={r['id_parcela']:int(r['orden']) for r in cases}; controls_by={r['control']:r['caso'] for r in controls}
    lookup={}; vectors={}; catalog_by={r['serie_id']:r for r in catalog}
    for meta in catalog:
        sid=meta['serie_id']; data=indexed[sid]
        for esc in ('A','B'):
            for pop in POPS:
                by=defaultdict(list); hits=Counter()
                for rep in range(1,6):
                    rr=[r for k,r in data.items() if k[:2]==(esc,rep) and f1.elegible(r,pop)]
                    for r in rr: by[r['id_parcela']].append(r)
                    hits.update(r['id_parcela'] for r in f1.orden(rr,'error_absoluto')[:10])
                    ds=[r['error_absoluto']-base[(esc,rep,r['id_parcela'])]['error_absoluto'] for r in rr]
                    reps.append(dict(serie_id=sid,escenario=esc,poblacion=pop,repeticion=rep,
                                     n_parcelas=len(rr),mae=f1.media([r['error_absoluto'] for r in rr]),
                                     delta_mae=f1.media(ds)))
                local=[]
                for pid in sorted(known):
                    rr=by[pid]; bs=[base[(esc,r['repeticion'],pid)] for r in rr]; s=f1.resumen_parcela(rr); n=len(rr)
                    vectors[(sid,esc,pop,pid)]=tuple(r['prediccion'] for r in rr)
                    row=dict(serie_id=sid,escenario=esc,poblacion=pop,id_parcela=pid,n_elegibles=n,
                        mae=s['mae'],sesgo=s['sesgo'],mse=s['mse'],rango_error=s['rango_error'],
                        sobre=s['sobre'],sub=s['sub'],ceros=s['ceros'],
                        delta_mae=f1.media([r['error_absoluto']-b['error_absoluto'] for r,b in zip(rr,bs)]),
                        distancia_pred_T08=f1.media([abs(r['prediccion']-b['prediccion']) for r,b in zip(rr,bs)]),
                        fraccion_mismo_signo_T08=f1.media([signo(r['error_firmado'])==signo(b['error_firmado']) for r,b in zip(rr,bs)]),
                        apariciones_top10=hits[pid],fraccion_top10=hits[pid]/n if n else '',
                        n_municipal=sum(r['fuente_referencia']=='municipio' for r in rr),
                        n_grupo=sum(r['fuente_referencia']=='grupo' for r in rr),
                        n_global=sum(r['fuente_referencia']=='global' for r in rr),
                        orden_caso_fijo=fixed.get(pid,''),control_de=controls_by.get(pid,''))
                    local.append(row);lookup[(sid,esc,pop,pid)]=row
                matrix.extend(local); eligible=[r for r in local if r['n_elegibles']]
                deltas=[r['delta_mae'] for r in eligible]; ds=f1.media(deltas)
                rep_mae=[r for r in reps if (r['serie_id'],r['escenario'],r['poblacion'])==(sid,esc,pop)]
                summaries.append(dict(serie_id=sid,escenario=esc,poblacion=pop,n_parcelas=len(eligible),
                    n_registros=sum(r['n_elegibles'] for r in local),mae_parcelas=f1.media([r['mae'] for r in eligible]),
                    mae_media_repeticiones=f1.media([r['mae'] for r in rep_mae]),
                    delta_mae_parcelas=ds,direccion=cambio(ds),
                    distancia_pred_T08=f1.media([r['distancia_pred_T08'] for r in eligible]),
                    parcelas_mejoran=sum(cambio(d)=='mejora_numerica' for d in deltas),
                    parcelas_empeoran=sum(cambio(d)=='deterioro_numerico' for d in deltas),
                    parcelas_sin_cambio=sum(cambio(d)=='sin_cambio_numerico' for d in deltas),
                    repeticiones_mejoran=sum(r['delta_mae'] < -EPS for r in rep_mae),
                    overlap_top10_T08=f1.media([len(set(r['id_parcela'] for r in f1.orden([v for k,v in data.items() if k[:2]==(esc,rep) and f1.elegible(v,pop)],'error_absoluto')[:10]) &
                                                     set(r['id_parcela'] for r in f1.orden([v for k,v in base.items() if k[:2]==(esc,rep) and f1.elegible(v,pop)],'error_absoluto')[:10]))/10 for rep in range(1,6)])))
    families=defaultdict(list)
    for meta in catalog:
        if not meta['es_referencia']: families[meta['frente']].append(meta['serie_id'])
    coincidences=[]
    for esc in ('A','B'):
        for pop in POPS:
            for pid in sorted(known):
                for fam,sids in sorted(families.items()):
                    rr=[lookup[(sid,esc,pop,pid)] for sid in sids]; er=[r for r in rr if r['n_elegibles']]
                    coincidences.append(dict(escenario=esc,poblacion=pop,id_parcela=pid,frente=fam,
                        ambito=catalog_by[sids[0]]['ambito'],n_series_configuradas=len(rr),n_series_elegibles=len(er),
                        mae_min=min(r['mae'] for r in er) if er else '',mae_max=max(r['mae'] for r in er) if er else '',
                        delta_min=min(r['delta_mae'] for r in er) if er else '',delta_max=max(r['delta_mae'] for r in er) if er else '',
                        fraccion_top10_min=min(r['fraccion_top10'] for r in er) if er else '',
                        fraccion_top10_max=max(r['fraccion_top10'] for r in er) if er else '',
                        sobre_en_todas_series_y_reps=all(r['sobre']==r['n_elegibles'] for r in er) if er else '',
                        sub_en_todas_series_y_reps=all(r['sub']==r['n_elegibles'] for r in er) if er else '',
                        orden_caso_fijo=fixed.get(pid,'')))
    included=[m['serie_id'] for m in catalog if not m['es_referencia'] or m['fuente']=='T08']
    pairs=[]
    for i,s1 in enumerate(included):
        for s2 in included[i+1:]:
            for esc in ('A','B'):
                for pop in POPS:
                    pp=[];x=[];y=[]
                    for pid in sorted(known):
                        a=lookup[s1,esc,pop,pid];b=lookup[s2,esc,pop,pid]
                        if not a['n_elegibles']: continue
                        exigir(a['n_elegibles']==b['n_elegibles'],'Denominador diferente en pares')
                        x.append(a['sesgo']);y.append(b['sesgo'])
                        v1=vectors[s1,esc,pop,pid];v2=vectors[s2,esc,pop,pid]
                        exigir(len(v1)==len(v2)==a['n_elegibles'],'Vectores de pares no alineados')
                        pp.append(f1.media([abs(a-b) for a,b in zip(v1,v2)]))
                    pairs.append(dict(serie_1=s1,serie_2=s2,escenario=esc,poblacion=pop,n_parcelas=len(pp),
                                      distancia_pred=f1.media(pp),correlacion_sesgos_por_parcela=corr(x,y)))
    return {'matriz_procedimientos_por_caso.csv':matrix,'resumen_comparaciones.csv':summaries,
            'metricas_por_repeticion.csv':reps,'coincidencias_por_frente.csv':coincidences,'pares_procedimientos.csv':pairs}


def signo(x): return (x>0)-(x<0)


def influencia(pool, table):
    exigir(pool, 'Referencia sin soporte')
    ids=sorted(pool);ys=[f0.numero(table[i]['rendimiento_t_ha'],'y_train') for i in ids]
    n=len(ids);mu=f1.media(ys)
    if n==1: return dict(n_pool=n,media_pool=mu,sd_pool=0.,influencia_max_abs='',etiqueta_mas_influyente='',
                         media_sin_etiqueta='',delta_media_sin_etiqueta='',estado_influencia='pool_unitario_media_sin_etiqueta_indefinida')
    diffs=[((mu-y)/(n-1),pid) for pid,y in zip(ids,ys)]
    delta,pid=sorted(diffs,key=lambda x:(-abs(x[0]),x[1]))[0]
    import statistics
    return dict(n_pool=n,media_pool=mu,sd_pool=statistics.pstdev(ys),influencia_max_abs=abs(delta),
                etiqueta_mas_influyente=pid,media_sin_etiqueta=mu+delta,delta_media_sin_etiqueta=delta,
                estado_influencia='analitica_solo_media_no_elimina_etiqueta')


def pool_referencia(train, target, table):
    municipality=table[target]['municipio'];group=table[target]['cultivo_origen']
    pool={i for i in train if table[i]['municipio']==municipality};source='municipio'
    nmunicipal=len(pool)
    if not pool: pool={i for i in train if table[i]['cultivo_origen']==group};source='grupo'
    if not pool: pool=set(train);source='global'
    return pool,source,nmunicipal


def soporte(base, table, known, parts):
    cache={}; out=[]
    for k,r in sorted(base.items()):
        esc,rep,pid=k;fold=r['particion'];field='particion_principal' if esc=='A' else 'particion_espacial'
        train={i for i in known if int(parts[rep][i][field])!=fold}
        test=known-train;exigir(pid in test and not train&test,'Referencia incluye evaluación')
        pool,source,nmun=pool_referencia(train,pid,table)
        exigir(not pool&test and source==r['fuente_referencia'],'Pool/fuente incompatible')
        ck=(esc,rep,fold,source,tuple(sorted(pool)))
        if ck not in cache: cache[ck]=influencia(pool,table)
        s=cache[ck];exigir(abs(s['media_pool']-r['prediccion'])<=f0.ATOL,'Referencia reconstruida distinta')
        out.append(dict(escenario=esc,repeticion=rep,particion=fold,id_parcela=pid,
            municipio=table[pid]['municipio'],fuente_referencia=source,n_entrenamiento=len(train),n_municipal=nmun,
            firma_pool=hashlib.sha256('|'.join(sorted(pool)).encode()).hexdigest(),**s))
    grouped=[]
    for esc in ('A','B'):
        for municipality in sorted({table[i]['municipio'] for i in known}):
            for source in ('municipio','grupo','global'):
                rr=[r for r in out if r['escenario']==esc and r['municipio']==municipality and r['fuente_referencia']==source]
                vals=[r['influencia_max_abs'] for r in rr if r['influencia_max_abs']!='']
                grouped.append(dict(escenario=esc,municipio=municipality,fuente_referencia=source,
                    etiquetas_municipio_total=sum(table[i]['municipio']==municipality for i in known),
                    n_parcelas=len({r['id_parcela'] for r in rr}),n_registros=len(rr),
                    n_municipal_min=min(r['n_municipal'] for r in rr) if rr else '',
                    n_municipal_max=max(r['n_municipal'] for r in rr) if rr else '',
                    n_pool_min=min(r['n_pool'] for r in rr) if rr else '',n_pool_max=max(r['n_pool'] for r in rr) if rr else '',
                    referencia_min=min(r['media_pool'] for r in rr) if rr else '',referencia_max=max(r['media_pool'] for r in rr) if rr else '',
                    influencia_max_abs=max(vals) if vals else '',
                    pools_unitarios=sum(r['n_pool']==1 for r in rr)))
    return {'sensibilidad_media_referencia.csv':out,'ficha_soporte_municipal.csv':grouped}


def ejecutar(fase0, fuentes, salida, figuras=True):
    salida=Path(salida);exigir(not salida.exists(),'Salida existente: usar destino nuevo')
    salida.parent.mkdir(parents=True,exist_ok=True)
    base,table,known,cases,controls,catalog,indexed=cargar(fase0,fuentes)
    tables=comparar(base,known,cases,controls,catalog,indexed)
    _,_,_,_,parts=f0.cargar_base(fuentes)
    tables.update(soporte(base,table,known,parts));tables['catalogo_series.csv']=catalog
    with tempfile.TemporaryDirectory(prefix='.diag_f2_',dir=salida.parent) as td:
        tmp=Path(td)
        for name,rows in tables.items(): f1.csv_escribir(tmp/name,rows)
        if figuras:
            from scripts.diagnostico_fase2_figuras import crear
            crear(tables,cases,tmp)
        manifest=dict(schema='agrocebada_diagnostico_fase2_entrega_v1',estado='tecnico_para_revision',diseno_sha256=DISENO_SHA,
            fase0_manifest_sha256=f1.F0_MANIFEST_SHA,series=51,referencias_alias=7,candidatos_no_referencia=44,
            registros_AB_verificados=70380,C_registros_fuera_contraste=828,parcelas=138,reservadas_evaluadas=0,
            reentrenamientos=0,mezcla_oraculo=False,revision_humana='pendiente',figuras_generadas=figuras,
            codigo_sha256={rel:hash_archivo(RAIZ/rel) for rel in ('scripts/diagnostico_fase2.py','scripts/diagnostico_fase2_figuras.py')},
            n_filas_tablas={name:len(rows) for name,rows in tables.items()},
            archivos_sha256={p.name:hash_archivo(p) for p in sorted(tmp.iterdir())})
        (tmp/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        tmp.rename(salida)
    return manifest


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--fase0',type=Path,required=True);p.add_argument('--fuentes',type=Path,required=True)
    p.add_argument('--salida',type=Path,required=True);p.add_argument('--sin-figuras',action='store_true');a=p.parse_args()
    m=ejecutar(a.fase0,a.fuentes,a.salida,not a.sin_figuras)
    print(json.dumps({k:m[k] for k in ('estado','series','registros_AB_verificados','reentrenamientos')},ensure_ascii=False))


if __name__=='__main__': main()
