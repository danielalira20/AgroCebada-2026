"""Verificación escalar adicional de repeticiones, desgloses y frecuencias."""
import argparse
import csv
import gzip
import json
import math
from pathlib import Path


def require(ok,msg):
    if not ok:raise ValueError(msg)


def read(p):
    with p.open() as f:return list(csv.DictReader(f))


def verificar_metricas(rows,report,individual=False):
    require(bool(rows),'Grupo vacío')
    error=lambda r:float(r['prediccion'])-float(r['real'])
    if individual:
        y=[float(r['real']) for r in rows];n=len(y);sse=math.fsum(error(r)**2 for r in rows);mean=math.fsum(y)/n
        den=math.fsum((v-mean)**2 for v in y)
        expected=dict(n=n,MAE=math.fsum(abs(error(r)) for r in rows)/n,RMSE=math.sqrt(sse/n),
            sesgo=math.fsum(error(r) for r in rows)/n,R2=None if den==0 or all(v==y[0] for v in y) else 1-sse/den)
    else:
        ids=sorted({r['ID_POLIGONO'] for r in rows});ae=[];se=[];bias=[];ys=[]
        for pid in ids:
            g=[r for r in rows if r['ID_POLIGONO']==pid];n=len(g)
            ae.append(math.fsum(abs(error(r)) for r in g)/n);se.append(math.fsum(error(r)**2 for r in g)/n)
            bias.append(math.fsum(error(r) for r in g)/n);ys.append(float(g[0]['real']))
        mse=math.fsum(se)/len(ids);mean=math.fsum(ys)/len(ids);den=math.fsum((v-mean)**2 for v in ys)/len(ids)
        reps=[]
        for rep in sorted({int(r['repeticion']) for r in rows}):
            g=[r for r in rows if int(r['repeticion'])==rep];y=[float(r['real']) for r in g];n=len(g)
            ss=math.fsum(error(r)**2 for r in g);ym=math.fsum(y)/n;dd=math.fsum((v-ym)**2 for v in y)
            reps.append((math.fsum(abs(error(r)) for r in g)/n,math.sqrt(ss/n),None if dd==0 or all(v==y[0] for v in y) else 1-ss/dd))
        # Percentil lineal como definición, implementado sin numpy.
        aa=sorted(ae);rank=.9*(len(aa)-1);a=int(rank);p90=aa[a]+(rank-a)*(aa[min(a+1,len(aa)-1)]-aa[a])
        expected=dict(n_parcelas=len(ids),n_predicciones=len(rows),n_repeticiones=len(reps),MAE_por_parcela=math.fsum(ae)/len(ids),
            RMSE_igual_peso_parcela=math.sqrt(mse),sesgo_por_parcela=math.fsum(bias)/len(ids),
            R2_igual_peso_parcela=None if den==0 or all(v==ys[0] for v in ys) else 1-mse/den,MAE_media_repeticiones=math.fsum(v[0] for v in reps)/len(reps),
            RMSE_media_repeticiones=math.fsum(v[1] for v in reps)/len(reps),
            R2_media_repeticiones=None if any(v[2] is None for v in reps) else math.fsum(v[2] for v in reps)/len(reps),
            p90_MAE_parcela=p90,n_parcelas_MAE_mayor_1=sum(v>1 for v in ae))
    maximum=0.
    for key,value in expected.items():
        if value is None:require(report[key]=='','R2 constante requiere vacío')
        else:
            d=abs(value-float(report[key]));maximum=max(maximum,d);require(d<=1e-12,'Métrica alterada: '+key)
    return len(expected),maximum


def verificar(root,out):
    rows=read(out/'predicciones_oof.csv');table={r['id_parcela']:r for r in read(root/'registro/t07/tabla_comun.csv')}
    quality={r['id_parcela']:r for r in read(root/'registro/t07/calidad_parcelas.csv')}
    count=0;maximum=0.;expectedkeys=set();keys=set()
    names={r['candidato'] for r in rows}
    for name in names:
        for esc in ['A','B']:
            for sub in ['todas','sin_respaldo']:
                g=[v for v in rows if v['candidato']==name and v['escenario']==esc and (sub=='todas' or v['fuente']=='municipio')]
                groupdefs={'municipio':lambda i:table[i]['municipio'],'grupo_registro':lambda i:table[i]['cultivo_origen'],
                    'vecina_etiquetada_menos_20m':lambda i:quality[i]['vecina_etiquetada_menos_20m'],
                    'contorno_categoria':lambda i:quality[i]['contorno_categoria']}
                for kind,fun in groupdefs.items():
                    for val in {fun(v['ID_POLIGONO']) for v in g}:expectedkeys.add((name,esc,sub,kind,val))
                expectedkeys.add((name,esc,sub,'sin24_solo_reporte','sin_alerta'))
    for fname,individual in [('metricas_resumen.csv',False),('metricas_repeticiones.csv',True),('desgloses.csv',False)]:
        reports=read(out/fname)
        require(fname=='desgloses.csv' or len(reports)==(80 if individual else 16),'Cobertura de métricas')
        for r in reports:
            g=[v for v in rows if v['candidato']==r['candidato'] and v['escenario']==r['escenario'] and (r['subconjunto']=='todas' or v['fuente']=='municipio')]
            if individual:g=[v for v in g if v['repeticion']==r['repeticion']]
            if fname=='desgloses.csv':
                kind,val=r['desglose'],r['valor'];key=(r['candidato'],r['escenario'],r['subconjunto'],kind,val)
                require(key not in keys,'Desglose duplicado');keys.add(key)
                if kind=='sin24_solo_reporte':g=[v for v in g if quality[v['ID_POLIGONO']]['alerta_contorno_t03_bis']!='si']
                else:
                    field='cultivo_origen' if kind=='grupo_registro' else kind
                    source=table if kind in ['municipio','grupo_registro'] else quality
                    g=[v for v in g if source[v['ID_POLIGONO']][field]==val]
            n,d=verificar_metricas(g,r,individual);count+=n;maximum=max(maximum,d)
    require(keys==expectedkeys,'Falta/sobra desglose')
    with (out/'selecciones.jsonl').open() as f:sels=[json.loads(s) for s in f]
    freq=read(out/'frecuencia_opciones.csv');require(len(freq)==18,'Frecuencias incompletas')
    for r in freq:require(int(r['n_contextos'])==sum(s['escenario']==r['escenario'] and s['elegida']['nombre']==r['opcion'] for s in sels),'Frecuencia incorrecta')
    incremental=read(out/'predicciones_incrementales.csv')
    require(incremental==[r for r in rows if r['candidato']=='cuantilica_municipal_S_v1'],'OOF incremental distinta')
    return dict(resultado='aprobado',comprobaciones_metricas=count,max_diferencia=maximum,desgloses=len(keys),frecuencias=18,OOF_incrementales=len(incremental))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--raiz',type=Path,required=True);p.add_argument('--entrada',type=Path,required=True);p.add_argument('--salida',type=Path,required=True)
    a=p.parse_args();require(not a.salida.exists(),'No sobrescribir salida');res=verificar(a.raiz,a.entrada)
    a.salida.write_text(json.dumps(res,indent=2)+'\n');print(json.dumps(res))
