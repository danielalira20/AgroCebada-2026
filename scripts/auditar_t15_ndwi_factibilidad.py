"""Auditor D.1 independiente: Fraction sobre CSV original, sin importar productor/modelos."""
from __future__ import annotations
import argparse
import csv
from datetime import date,datetime,timedelta
from fractions import Fraction as F
import hashlib
import json
import math
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def table(path):
    with Path(path).open(encoding="utf-8-sig",newline="") as f:return list(csv.DictReader(f))


def digest(p):
    h=hashlib.sha256()
    with Path(p).open("rb") as f:
        while True:
            b=f.read(1048576)
            if not b:break
            h.update(b)
    return h.hexdigest()


def rational(s):
    return None if str(s).strip().lower() in {"","nan","na","null","none"} else F(str(s))


def mid(values):
    v=sorted(values);n=len(v)
    return v[n//2] if n%2 else (v[n//2-1]+v[n//2])/2


def exact_profile(sequence,start,cutoff=date(2025,10,31)):
    # Tuplas: fecha, NDVI racional, NDWI racional, nubosidad racional.
    seq=sorted(x for x in sequence if start<=x[0]<=cutoff and x[1] is not None
               and x[3] is not None and 0<=x[3]<=5)
    if len({x[0] for x in sequence})!=len(sequence):raise ValueError("Fecha duplicada")
    expected=dict(n_capturas=len(seq),fecha_maximo=None,ndvi_max=None,amplitud_ndvi=None,
                  n_empates_maximo=0,maximo_en_borde=None,meseta_45_dias=None,ndwi_ancla=None,
                  ndwi_mediana_mas_menos15=None,n_fechas_post=0,fechas_post="",primera_post=None,
                  n_fechas_originales_post=None,n_post_descartadas_nube=None,n_post_descartadas_dato=None,
                  ultima_post=None,intervalo_truncado=None,amplitud_temporal_post_dias=None,
                  hueco_max_post_con_bordes_dias=None,ndwi_media_post=None,contraste_ndwi=None,
                  calculable=False,motivo="menos_5_capturas",faltante_ancla=None,faltante_post=None)
    if len(seq)<5:return expected
    sm=[]
    for i in range(len(seq)):
        positions=[j for j in [i-1,i,i+1] if 0<=j<len(seq)]
        sm.append(mid([seq[j][1] for j in positions]))
    mx=max(sm);idx=next(i for i,value in enumerate(sm) if value==mx)
    peak=seq[idx][0];anchor=seq[idx][2];amp=mx-min(sm[:idx+1])
    plateau=[seq[i][0] for i in range(len(seq)) if sm[i]>=mx-amp/F(20)]
    near=[x[2] for x in seq if peak-timedelta(days=15)<=x[0]<=peak+timedelta(days=15)]
    left,right=peak+timedelta(days=15),peak+timedelta(days=45)
    end=min(right,cutoff)
    post=[x for x in seq if left<=x[0]<=end and x[2] is not None]
    originals=[x for x in sequence if start<=x[0]<=cutoff and left<=x[0]<=end]
    bad_cloud=sum(x[3] is None or not 0<=x[3]<=5 for x in originals)
    bad_data=sum(x[3] is not None and 0<=x[3]<=5 and (x[1] is None or x[2] is None) for x in originals)
    avg=sum((x[2] for x in post),F(0))/len(post) if post else None
    gaps=[(post[0][0]-left).days,(end-post[-1][0]).days] if post else []
    for i in range(1,len(post)):gaps.append((post[i][0]-post[i-1][0]).days)
    reasons=[]
    if anchor is None:reasons.append("ndwi_ancla_ausente")
    if len(post)<2:reasons.append("menos_2_fechas_post")
    expected.update(fecha_maximo=peak,ndvi_max=mx,amplitud_ndvi=amp,n_empates_maximo=sm.count(mx),
                    maximo_en_borde=idx==0 or idx==len(seq)-1,
                    meseta_45_dias=(max(plateau)-min(plateau)).days>=45,ndwi_ancla=anchor,
                    ndwi_mediana_mas_menos15=mid(near) if all(v is not None for v in near) else None,
                    n_fechas_post=len(post),fechas_post=";".join(x[0].isoformat() for x in post),
                    n_fechas_originales_post=len(originals),n_post_descartadas_nube=bad_cloud,
                    n_post_descartadas_dato=bad_data,
                    primera_post=post[0][0] if post else None,ultima_post=post[-1][0] if post else None,
                    intervalo_truncado=right>cutoff,
                    amplitud_temporal_post_dias=(post[-1][0]-post[0][0]).days if post else None,
                    hueco_max_post_con_bordes_dias=max(gaps) if gaps else None,
                    ndwi_media_post=avg,contraste_ndwi=avg-anchor if not reasons else None,
                    calculable=not reasons,motivo=";".join(reasons) if reasons else "ok",
                    faltante_ancla=anchor is None,faltante_post=len(post)<2)
    return expected


def audit(output,raw_dir,root=ROOT):
    output=Path(output);root=Path(root)
    contract=json.loads((root/"registro/t15_d1/diseno.json").read_text())
    manifest=json.loads((output/"manifest.json").read_text())
    comparisons=0;max_delta=0.
    def check(actual,expected,location):
        nonlocal comparisons,max_delta
        comparisons+=1
        if expected is None:
            if actual!="":raise ValueError("Vacío distinto: "+location)
        elif isinstance(expected,bool):
            if actual!=str(expected):raise ValueError("Booleano distinto: "+location)
        elif isinstance(expected,(F,float)):
            value=float(actual);delta=abs(value-float(expected))
            if not math.isfinite(value) or delta>1e-12:raise ValueError("Valor distinto: "+location)
            max_delta=max(max_delta,delta)
        elif actual!=str(expected):raise ValueError("Dato distinto: "+location)
    if manifest['diseno_sha256']!=digest(root/"registro/t15_d1/diseno.json"):
        raise ValueError("Diseño distinto")
    for rel,h in contract['fuentes_sha256'].items():
        p=Path(raw_dir)/Path(rel).name if rel.startswith('data/raw/') else root/rel
        if digest(p)!=h:raise ValueError("Fuente distinta: "+rel)
    for rel,h in manifest['archivos_sha256'].items():
        if digest(output/rel)!=h:raise ValueError("Derivado modificado: "+rel)
    for rel,h in manifest['codigo_sha256'].items():
        if digest(root/rel)!=h:raise ValueError("Productor distinto")
    meta={r['id_parcela']:{'id_parcela':r['id_parcela'],'municipio':r['municipio'],
                          'conjunto':r['conjunto_origen']} for r in table(root/'registro/t07/catalogo_base.csv')}
    groups={p:[] for p in meta}
    with (Path(raw_dir)/'Conjunto_datos_BASICO_AgroCebada2026.csv').open(encoding='utf-8-sig',newline='') as f:
        for r in csv.DictReader(f):
            if r['sensor']!='Sentinel-2':continue
            t=datetime.strptime(r['fecha_captura'],'%d/%m/%Y').date()
            groups[r['ID_POLIGONO']].append((t,rational(r['ndvi_promedio']),rational(r['ndwi_promedio']),
                                           rational(r['porcentaje_nubosidad'])))
    expected={}
    for pid,seq in groups.items():
        for window,start in [('abr_oct',date(2025,4,1)),('jun_oct',date(2025,6,1))]:
            expected[pid,window]=dict(**meta[pid],sensor='Sentinel-2',ventana=window,
                                      **exact_profile(seq,start))
    actual=table(output/'perfil_ndwi_postpico.csv')
    if len(actual)!=394 or len(expected)!=394:raise ValueError('Población no completa')
    seen=set()
    for row in actual:
        key=(row['id_parcela'],row['ventana'])
        if key in seen:raise ValueError('Perfil duplicado')
        seen.add(key)
        if set(row)!=set(expected[key]):raise ValueError('Columnas inesperadas')
        for field,value in expected[key].items():check(row[field],value,str(key)+field)
    if seen!=set(expected):raise ValueError('Faltan perfiles')
    for name,dimension in [('resumen_conjunto.csv','conjunto'),('resumen_municipio.csv','municipio')]:
        summary_rows=table(output/name)
        summary_keys={(r['ventana'],r['categoria']) for r in summary_rows}
        expected_keys={(w,c) for w in ['abr_oct','jun_oct'] for c in ['todas',*{v[dimension] for v in expected.values()}]}
        if len(summary_keys)!=len(summary_rows) or summary_keys!=expected_keys:
            raise ValueError('Resumen incompleto o duplicado: '+name)
        for row in summary_rows:
            subset=[v for (pid,w),v in expected.items() if w==row['ventana'] and
                    (row['categoria']=='todas' or v[dimension]==row['categoria'])]
            good=[r for r in subset if r['calculable']]
            fields={'n_parcelas':len(subset),'n_calculables':len(good),'n_ausentes':len(subset)-len(good),
                    'n_ancla_ausente':sum(bool(v['faltante_ancla']) for v in subset),
                    'n_post_insuficiente':sum(bool(v['faltante_post']) for v in subset),
                    'n_intervalo_truncado':sum(bool(v['intervalo_truncado']) for v in subset),
                    'n_maximo_en_borde':sum(bool(v['maximo_en_borde']) for v in subset),
                    'n_meseta_45_dias':sum(bool(v['meseta_45_dias']) for v in subset),
                    'fechas_post_min':min(v['n_fechas_post'] for v in subset),
                    'fechas_post_mediana':mid([F(v['n_fechas_post']) for v in subset]),
                    'contraste_min':min((v['contraste_ndwi'] for v in good),default=None),
                    'contraste_mediana':mid([v['contraste_ndwi'] for v in good]) if good else None,
                    'contraste_max':max((v['contraste_ndwi'] for v in good),default=None)}
            for field,value in fields.items():check(row[field],value,name+field)
    t06={r['ID_POLIGONO']:r for r in table(root/'registro/t06/variables_satelitales.csv')}
    reconciliation=table(output/'conciliacion_t06.csv')
    if len(reconciliation)!=1182 or len({(r['id_parcela'],r['ventana'],r['variable']) for r in reconciliation})!=1182:
        raise ValueError('Conciliación incompleta o duplicada')
    for row in reconciliation:
        pid,w,col=row['id_parcela'],row['ventana'],row['variable']
        key='ndvi_max' if 'ndvi_max' in col else 'n_capturas' if 'capturas' in col else 'ndwi_mediana_mas_menos15'
        e=expected[pid,w][key]
        check(row['calculado'],e,'Conciliación'+col)
        orig=rational(t06[pid][col]);delta=abs(float(e)-float(orig)) if e is not None and orig is not None else None
        check(row['publicado_T06'],orig,'T06'+col)
        check(row['diferencia'],delta,'Delta'+col)
        check(row['coincide'],(e is None and orig is None) or(delta is not None and delta<=1e-9),'Estado'+col)
    variation_rows=table(output/'variacion_sin_y.csv')
    expected_variations={(w,v) for w in ['abr_oct','jun_oct'] for v in
                         ['contraste_ndwi','ndwi_ancla','ndwi_media_post','ndwi_mediana_mas_menos15','ndvi_max']}
    if len(variation_rows)!=10 or {(r['ventana'],r['variable']) for r in variation_rows}!=expected_variations:
        raise ValueError('Variación incompleta o duplicada')
    for row in variation_rows:
        vals=[v for (p,w),v in expected.items() if w==row['ventana'] and v[row['variable']] is not None]
        x=[v[row['variable']] for v in vals];n=len(x);m=sum(x,F(0))/n if n else None
        ss=sum(((v-m)**2 for v in x),F(0)) if n else F(0);within=F(0)
        for mun in {v['municipio'] for v in vals}:
            g=[v[row['variable']] for v in vals if v['municipio']==mun];gm=sum(g,F(0))/len(g)
            within+=sum(((z-gm)**2 for z in g),F(0))
        for field,value in {'n':n,'minimo':min(x) if x else None,'maximo':max(x) if x else None,
                            'desviacion':math.sqrt(float(ss/n)) if n else None,
                            'fraccion_variacion_dentro_municipio':within/ss if ss else None,
                            'uso_rendimiento':False}.items():check(row[field],value,'Variación'+field)
    dictionary=table(output/'diccionario.csv')
    if len(dictionary)!=len(actual[0]) or {d['columna'] for d in dictionary}!=set(actual[0]):
        raise ValueError('Diccionario incompleto o duplicado')
    summary=json.loads((output/'resumen.json').read_text())
    summary_expected={'n_ids':197,'n_perfiles':394,'modelos_ajustados':0,'uso_rendimiento':False,
                      'nuevas_predicciones_59':0,'perfiles_calculables':sum(v['calculable'] for v in expected.values()),
                      'conciliacion_T06_comparaciones':1182,
                      'ambas_ventanas_contraste_exacto':sum(expected[p,'abr_oct']['contraste_ndwi'] is not None
                       and expected[p,'abr_oct']['contraste_ndwi']==expected[p,'jun_oct']['contraste_ndwi'] for p in meta)}
    for key,value in summary_expected.items():
        comparisons+=1
        if summary[key]!=value:raise ValueError('Resumen JSON distinto: '+key)
    return dict(resultado='verificado',comparaciones=comparisons,max_delta=max_delta,IDs=197,perfiles=394,
                usa_productor=False,metodo='Fraction_CSV_original_mediana_racional',modelos_ajustados=0,
                nuevas_predicciones59=0,revision_humana='pendiente',
                codigo_auditor_sha256=digest(Path(__file__)),diseno_sha256=manifest['diseno_sha256'])


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--salida',type=Path,required=True)
    ap.add_argument('--datos',type=Path,default=ROOT/'data/raw/DATASET_RETO_AGRO_2026')
    ap.add_argument('--evidencia',type=Path,required=True)
    a=ap.parse_args();r=audit(a.salida,a.datos)
    a.evidencia.parent.mkdir(parents=True,exist_ok=True)
    with a.evidencia.open('x',encoding='utf-8') as f:f.write(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(r,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
