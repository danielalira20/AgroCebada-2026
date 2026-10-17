import gzip,json,sys
from pathlib import Path
from collections import defaultdict
import numpy as np
root,run,out=map(Path,sys.argv[1:]);sys.path.insert(0,str(root))
from scripts.t15_e2_auditar_modelo import AuditorModeloE2,MAP
a=AuditorModeloE2(root);maximum=0.;counts=defaultdict(int);query=defaultdict(list);states=0;corrected=0
plain=run/'estados_modelos.jsonl'
f=plain.open() if plain.exists() else gzip.open(str(plain)+'.gz','rt')
with f:
 for line in f:
  row=json.loads(line);state=row['estado_modelo'];states+=1;mode=state['procedimiento_E2'];tr=state['ids_entrenamiento']
  counts[row['candidato'],row['escenario'],mode=='referencia']+=1
  query[row['candidato'],row['escenario']].extend(abs(r['correccion']) for r in row['consulta'])
  if mode=='referencia':continue
  corrected+=1;a.cache.clear();s=a.prepare(tr,row['columnas_base'],MAP[mode]);beta=np.array(state['coeficientes'])
  groups=defaultdict(list)
  for n,pid in enumerate(tr):groups[a.table[pid]['municipio']].append(n)
  for mun,ix in groups.items():
   d=(s['z'][ix]-np.array(state['centros_Z_municipio'][mun]))@beta
   maximum=max(maximum,abs(float(np.mean(d))))
if maximum>1e-12 or states!=150:raise ValueError('H3/completitud')
result=dict(resultado='aprobado',estados_externos=states,estados_con_correccion=corrected,
 max_media_correccion_train_por_municipio=maximum,tolerancia=1e-12,
 medias_cero_exigidas_en_validacion=False,
 ajustes=[dict(candidato=k[0],escenario=k[1],referencia_sola=k[2],cantidad=v) for k,v in sorted(counts.items())],
 correcciones_consulta=[dict(candidato=k[0],escenario=k[1],media_abs=float(np.mean(v)),max_abs=float(np.max(v))) for k,v in sorted(query.items())])
if out.exists():raise ValueError('No sobrescribir')
out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result))
