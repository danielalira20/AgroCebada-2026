"""Auditoría adicional de desgloses y frecuencia; no ajusta ni selecciona modelos."""
from collections import defaultdict
import csv,json,math,sys
from pathlib import Path
import numpy as np
root,run,out=map(Path,sys.argv[1:]);n=0;maximum=0.
def read(p):
 with p.open(newline='') as f:return list(csv.DictReader(f))
def check(ok,msg):
 global n
 n+=1
 if not ok:raise ValueError(msg)
def close(x,y,msg):
 global maximum
 if y is None:check(x=='',msg+' indefinido');return
 d=abs(float(x)-float(y));maximum=max(maximum,d);check(math.isfinite(d) and d<=1e-12,msg)
rows=read(run/'predicciones_oof.csv');quality={r['id_parcela']:r for r in read(root/'registro/t07/calidad_parcelas.csv')}
table={r['id_parcela']:r for r in read(root/'registro/t07/tabla_comun.csv')}
des=read(run/'desgloses_calidad_y_sin24.csv')
categories={'municipio':lambda i:table[i]['municipio'],'grupo_registro':lambda i:table[i]['cultivo_origen'],
 'contorno_categoria':lambda i:quality[i]['contorno_categoria'],
 'contorno_angosta_o_muy_pequena':lambda i:quality[i]['contorno_angosta_o_muy_pequena'],
 'escalon_etiqueta_municipio':lambda i:quality[i]['escalon_etiqueta_municipio'] or 'no_documentado',
 'vecina_etiquetada_menos_20m':lambda i:quality[i]['vecina_etiquetada_menos_20m']}
def summary(g):
 if not g:return {'n_parcelas':0,'n_predicciones':0,'n_repeticiones':0}
 ids=defaultdict(list);reps=defaultdict(list)
 for r in g:ids[r['ID_POLIGONO']].append(r);reps[r['repeticion']].append(r)
 def one(v):
  y=np.array([float(r['real']) for r in v]);e=np.array([float(r['prediccion']) for r in v])-y
  den=np.mean((y-y.mean())**2)
  return np.abs(e).mean(),np.mean(e**2),e.mean(),None if np.all(y==y[0]) or den==0 else 1-np.mean(e**2)/den
 a=np.asarray([one(v)[:3] for v in ids.values()]);y=np.array([float(v[0]['real']) for v in ids.values()])
 den=np.mean((y-y.mean())**2);rr=[one(v) for v in reps.values()]
 return dict(n_parcelas=len(ids),n_predicciones=len(g),n_repeticiones=len(reps),MAE_por_parcela=a[:,0].mean(),
  RMSE_igual_peso_parcela=np.sqrt(a[:,1].mean()),sesgo_por_parcela=a[:,2].mean(),
  R2_igual_peso_parcela=None if np.all(y==y[0]) or den==0 else 1-a[:,1].mean()/den,MAE_media_repeticiones=np.mean([v[0] for v in rr]),
  RMSE_media_repeticiones=np.mean([np.sqrt(v[1]) for v in rr]),
  R2_media_repeticiones=None if any(v[3] is None for v in rr) else np.mean([v[3] for v in rr]),
  p90_MAE_parcela=np.percentile(a[:,0],90),n_parcelas_MAE_mayor_1=np.sum(a[:,0]>1))
for row in read(run/'metricas_resumen.csv'):
 g=[r for r in rows if r['candidato']==row['candidato'] and r['escenario']==row['escenario'] and (row['subconjunto']=='todas' or r['fuente']=='municipio')]
 for k,v in summary(g).items():close(row[k],v,'Resumen adicional '+k)
seen=set()
for row in des:
 key=tuple(row[k] for k in ['candidato','escenario','subconjunto','desglose','valor']);check(key not in seen,'Duplicado desglose');seen.add(key)
 c,s,u,d,v=key
 g=[r for r in rows if r['candidato']==c and r['escenario']==s and (u=='todas' or r['fuente']=='municipio')]
 if d=='sensibilidad_sin24':
  check(v=='sin24','Sensibilidad ajena');g=[r for r in g if quality[r['ID_POLIGONO']]['alerta_contorno_t03_bis']!='si']
 else:
  check(d in categories,'Categoría ajena');g=[r for r in g if categories[d](r['ID_POLIGONO'])==v]
 for k,val in summary(g).items():close(row[k],val,'Desglose '+k)
expected=set()
for c in sorted({r['candidato'] for r in rows}):
 for s in ['A','B']:
  for u in ['todas','sin_respaldo']:
   g=[r for r in rows if r['candidato']==c and r['escenario']==s and (u=='todas' or r['fuente']=='municipio')]
   for d,fun in categories.items():expected|={(c,s,u,d,fun(r['ID_POLIGONO'])) for r in g}
   expected.add((c,s,u,'sensibilidad_sin24','sin24'))
check(seen==expected,'Desgloses ausentes/sobrantes')
with (run/'selecciones.jsonl').open() as f:choices=[json.loads(x) for x in f]
freq=read(run/'frecuencia_referencia_sola.csv');check(len(freq)==6,'Frecuencia incompleta')
for r in freq:
 picked=[v for v in choices if v['candidato']==r['candidato'] and v['escenario']==r['escenario']]
 check(len(picked)==25,'Denominador selección')
 # Read exact field names below; counts must be explicit in the source report.
 for key in ['n_contextos','n_selecciones']:
  if key in r:close(r[key],25,'n contextos')
 count=sum(v['referencia_sola'] for v in picked)
 close(r['n_con_correccion'],25-count,'Con corrección');close(r['n_esperados'],25,'Contextos esperados')
 check(r['estado']=='completo' and r['version']=='comun-centrado-loo-v3','Estado/versión frecuencia')
 for k,v in r.items():
  if k in ['referencia_sola','n_referencia_sola']:close(v,count,'Referencias solas')
  if k in ['fraccion_referencia_sola','frecuencia_referencia_sola']:close(v,count/25,'Frecuencia referencia')
result=dict(resultado='aprobado',comprobaciones=n,diferencia_maxima=maximum,tolerancia=1e-12,desgloses=len(des),frecuencias=6,
            modelos_ajustados=0)
check(not out.exists(),'No sobrescribir dictamen');out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result))
