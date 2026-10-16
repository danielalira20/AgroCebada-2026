"""Auditor independiente E1/Q: CSV, pools explícitos y ecuaciones normales, sin sklearn."""
import argparse
import csv
from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path
import statistics

import numpy as np

VALUE='e1_ndwi_post15_45'
FLAG='e1_no_utilizable'


def csvread(path):
    with Path(path).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class Auditor:
    def __init__(self,root):
        self.root=Path(root);self.n=0;self.max_diff=0.
        self.table={r['id_parcela']:r for r in csvread(self.root/'registro/t07/tabla_comun.csv')}
        self.side={r['id_parcela']:r for r in csvread(self.root/'registro/t15_e1/vista_admisibilidad_propuesta.csv') if r['ventana']=='abr_oct'}
        self.parts={(int(r['repeticion']),r['ID_POLIGONO']):r for r in csvread(self.root/'registro/t03/particiones.csv')}
        self.known={i for i,r in self.table.items() if r['rendimiento_t_ha']!=''}
        self.cache={}

    def check(self,ok,msg):
        self.n+=1
        if not ok:raise ValueError(msg)

    def close(self,a,b,msg):
        a,b=np.asarray(a,float),np.asarray(b,float)
        self.check(a.shape==b.shape and np.isfinite(a).all() and np.isfinite(b).all(),msg+' forma/finito')
        delta=float(np.max(np.abs(a-b))) if a.size else 0.
        self.max_diff=max(self.max_diff,delta)
        self.check(delta<=1e-12,msg+f' diferencia={delta}')

    def pool(self,ids,pid,exclude=None):
        ids=[i for i in ids if i!=exclude];q=self.table[pid]
        for name,col in [('municipio','municipio'),('grupo','cultivo_origen')]:
            group=[i for i in ids if self.table[i][col]==q[col]]
            if group:return name,group
        return 'global',ids

    def ref(self,ids,pid,exclude=None):
        source,pool=self.pool(ids,pid,exclude)
        return math.fsum(float(self.table[i]['rendimiento_t_ha']) for i in pool)/len(pool),source,pool

    def prepare(self,train,columns,mode):
        key=(tuple(train),tuple(columns),mode)
        if key in self.cache:return self.cache[key]
        admitted=[i for i in train if self.side[i][FLAG]=='0'] if mode in ['Q','E1'] else []
        active=bool(admitted)
        med=statistics.median(float(self.side[i][VALUE]) for i in admitted) if mode=='E1' and active else None
        def raw(ids):
            rows=[]
            for pid in ids:
                row=[float(self.table[pid][c]) for c in columns]
                if mode=='E1':row.append((float(self.side[pid][VALUE]) if self.side[pid][VALUE]!='' else med) if active else 0.)
                if mode in ['Q','E1']:row.append(float(self.side[pid][FLAG]) if active else 1.)
                rows.append(row)
            return np.asarray(rows,float)
        a=raw(train);mean=a.mean(0);scale=a.std(0);scale[scale==0]=1.
        z=(a-mean)/scale;pos={pid:i for i,pid in enumerate(train)}
        pools={pid:self.pool(train,pid,pid) for pid in train}
        centers=np.asarray([z[[pos[i] for i in pools[pid][1]]].mean(0) for pid in train])
        residual=np.asarray([float(self.table[pid]['rendimiento_t_ha'])-self.ref(train,pid,pid)[0] for pid in train])
        D=z-centers
        result=dict(train=train,mean=mean,scale=scale,z=z,positions=pos,pools=pools,D=D,residual=residual,
                    raw=raw,admitted=admitted,active=active,median=med)
        self.cache[key]=result
        return result

    def predict(self,train,query,columns,lam,mode):
        base=np.asarray([self.ref(train,pid)[0] for pid in query])
        if not columns:return base,None,None
        s=self.prepare(train,columns,mode);D=s['D']
        beta=np.linalg.solve(D.T@D+len(train)*lam*np.eye(D.shape[1]),D.T@s['residual'])
        zq=(s['raw'](query)-s['mean'])/s['scale']
        centers=np.asarray([s['z'][[s['positions'][i] for i in self.pool(train,pid)[1]]].mean(0) for pid in query])
        return base+(zq-centers)@beta,s,beta

    def audit(self,run,output):
        run=Path(run);m=json.loads((run/'manifest.json').read_text())
        self.check(m['estado'] in ['completa_verificada','prueba_funcional_parcial_no_desempeno_global'],'Evaluación no terminada')
        self.check(not Path(output).exists(),'Destino auditor existente')
        for path,h in m['codigo_sha256'].items():self.check(sha(self.root/path)==h,'Código distinto '+path)
        for path,h in m['fuentes_sha256'].items():self.check(sha(self.root/path)==h,'Fuente distinta '+path)
        self.check(sha(self.root/'registro/t15_e1_evaluacion/registro_v1.json')==m['registro_sha256'],'Registro distinto')
        for name,h in m['archivos_sha256'].items():self.check(sha(run/name)==h,'Resultado alterado '+name)
        external={};external_hash={};inner=defaultdict(list);seen=set();context_sets={}; traces=0
        with (run/'trazas_ajustes.jsonl').open() as f:
            for line in f:
                t=json.loads(line);tr=t['ids_entrenamiento'];va=t['ids_validacion'];traces+=1
                self.check(t['estado']=='correcto' and not t['advertencias'],'Fit incompleto/advertencia')
                self.check(tr==sorted(tr) and len(tr)==len(set(tr)) and len(va)==len(set(va)),'IDs repetidos/desorden')
                self.check(not set(tr)&set(va) and set(tr+va)<=self.known,'Fuga IDs/59')
                esc,rep,fold=t['escenario'],int(t['repeticion']),int(t['particion'])
                field='particion_principal' if esc=='A' else 'particion_espacial'
                outer_train={i for i in self.known if int(self.parts[rep,i][field])!=fold}
                outer_test=self.known-outer_train
                if t['etapa']=='externa':self.check(set(tr)==outer_train and set(va)==outer_test,'Partición externa distinta')
                else:self.check(set(tr)|set(va)==outer_train,'Partición interna fuera de entrenamiento externo')
                if esc=='B':
                    self.check(not {self.parts[rep,i]['celda_chirps'] for i in tr}&{self.parts[rep,i]['celda_chirps'] for i in va},'Celda compartida en B')
                eligible=[i for i in va if self.table[i]['municipio'] in {self.table[j]['municipio'] for j in tr}]
                self.check(eligible==t['ids_elegibles'],'Elegibles distintos')
                key=(t['candidato'],esc,rep,fold,t['etapa'],t['opcion'],t.get('division_interna'))
                self.check(key not in seen,'Traza duplicada');seen.add(key)
                pred,state,beta=self.predict(tr,va,t['columnas_base'],t['lambda_reg'],t['modo'])
                prep=t['preprocesamiento_E1']
                if state is not None:
                    self.check(prep['ids_admisibles']==state['admitted'] and prep['extension_activa']==state['active'],'Estado de admisibilidad aprendido fuera')
                    if state['median'] is None:self.check(prep['mediana_E1'] is None,'Mediana no aplicable')
                    else:self.close(prep['mediana_E1'],state['median'],'Mediana de entrenamiento')
                    self.close(t['alpha'],len(tr)*t['lambda_reg'],'Alpha n completo')
                y=np.asarray([float(self.table[i]['rendimiento_t_ha']) for i in va])
                err=np.abs(pred-y);mask=np.asarray([i in eligible for i in va])
                base=np.asarray([self.ref(tr,i)[0] for i in va])
                self.close(t['media_abs_correccion'],np.mean(abs(pred-base)),'Magnitud corrección')
                if t['etapa']=='interna':
                    self.close(t['MAE'],err[mask].mean(),'MAE interno independiente')
                    self.close(t['MAE_todas'],err.mean(),'MAE interno todas')
                    group=(t['candidato'],esc,rep,fold,t['opcion'])
                    inner[group].extend((i,float(e),i in eligible) for i,e in zip(va,err))
                    context_sets[group]=outer_train
                else:
                    external[t['candidato'],esc,rep,fold]=(pred,state,beta,tr,va)
                    external_hash[t['candidato'],esc,rep,fold]=t['estado_modelo_sha256']
        for key,pairs in inner.items():self.check({i for i,_,_ in pairs}==context_sets[key] and len(pairs)==len(context_sets[key]),'Validación interna no cubre cada ID una vez')
        with (run/'selecciones.jsonl').open() as f:
            for line in f:
                r=json.loads(line)
                for score in r['puntuaciones']:
                    pairs=inner[r['candidato'],r['escenario'],r['repeticion'],r['particion'],score['nombre']]
                    self.close(score['MAE'],np.mean([e for _,e,b in pairs if b]),'Puntuación completa')
                    self.close(score['MAE_todas'],np.mean([e for _,e,_ in pairs]),'Puntuación todas')
                tie=lambda s:(round(s['MAE'],6),0 if s['referencia_sola'] else 1,-(s['lambda_reg'] or 0),0 if s['ventana']=='jun_oct' else 1,s['nombre'])
                self.check(r['nombre_opcion']==min(r['puntuaciones'],key=tie)['nombre'],'Selección/desempate distinto')
        with (run/'estados_modelos.jsonl').open() as f:
            for line in f:
                r=json.loads(line);state=r['estado_modelo']
                _,s,beta,tr,va=external[r['candidato'],r['escenario'],r['repeticion'],r['particion']]
                digest=hashlib.sha256(json.dumps(state,sort_keys=True,ensure_ascii=False,allow_nan=False,separators=(',',':')).encode()).hexdigest()
                # Vincular cada estado a la huella emitida se revisa abajo sobre las trazas externas.
                if s is not None:
                    self.close(state['media'],s['mean'],'Media escalador')
                    self.close(state['escala'],s['scale'],'Escala entrenamiento')
                    self.close(state['coeficientes'],beta,'Coeficientes ecuaciones normales')
                    for pid in tr:
                        source,pool=s['pools'][pid]
                        self.check(state['pools_sin_fila'][pid]==dict(fuente=source,n=len(pool),ids=pool),'Pool LOO/residuo')
                        self.close(state['centros_Z_sin_fila'][pid],s['z'][[s['positions'][i] for i in pool]].mean(0),'Centro LOO')
                self.check(external_hash[r['candidato'],r['escenario'],r['repeticion'],r['particion']]==digest,
                           'Estado no vinculado a traza')
        full=m['evaluacion_completa'];oof=csvread(run/('predicciones_oof.csv' if full else 'oof_parcial_prueba.csv'))
        old={(r['candidato'],r['escenario'],int(r['repeticion']),r['ID_POLIGONO']):r for r in csvread(self.root/'registro/t15_resultados/predicciones_oof.csv')}
        oof_seen=set()
        for r in oof:
            key=(r['candidato'],r['escenario'],int(r['repeticion']),r['ID_POLIGONO'])
            self.check(key not in oof_seen,'OOF duplicada');oof_seen.add(key)
            self.check(r['ID_POLIGONO'] in self.known,'59 en OOF')
            if key in old:self.close(r['prediccion'],old[key]['prediccion'],'OOF S/referencia inmutable')
            else:
                pred,_,_,tr,va=external[r['candidato'],r['escenario'],int(r['repeticion']),int(r['particion'])]
                self.close(r['prediccion'],pred[va.index(r['ID_POLIGONO'])],'OOF independiente')
            self.close(r['real'],self.table[r['ID_POLIGONO']]['rendimiento_t_ha'],'Etiqueta OOF original')
        self.check(len(oof)==(5520 if full else 2*len(next(iter(external.values()))[-1])),'Número OOF incorrecto')
        if full:
            self.check(traces==3700 and len(external)==100 and len(inner)==900,'Conteo completo/menú')
            for row in csvread(run/'metricas_resumen.csv'):
                selected=[r for r in oof if r['candidato']==row['candidato'] and r['escenario']==row['escenario'] and (row['subconjunto']=='todas' or r['fuente']=='municipio')]
                ids=defaultdict(list);reps=defaultdict(list)
                for r in selected:
                    y,p=float(r['real']),float(r['prediccion']);ids[r['ID_POLIGONO']].append(abs(p-y));reps[int(r['repeticion'])].append((y,p))
                self.close(row['MAE_por_parcela'],np.mean([np.mean(v) for v in ids.values()]),'MAE reporte')
                rms=[];r2=[]
                for pairs in reps.values():
                    a=np.asarray(pairs);mse=np.mean((a[:,1]-a[:,0])**2)
                    rms.append(np.sqrt(mse));r2.append(1-mse/np.mean((a[:,0]-a[:,0].mean())**2))
                self.close(row['RMSE_media_repeticiones'],np.mean(rms),'RMSE reporte')
                self.close(row['R2_media_repeticiones'],np.mean(r2),'R2 reporte')
        result=dict(schema='E1_auditoria_independiente_v1',resultado='aprobado',comprobaciones=self.n,
            tolerancia_absoluta=1e-12,diferencia_maxima=self.max_diff,trazas=traces,OOF=len(oof),
            evaluacion_completa=full,importa_productor_o_sklearn=False,
            codigo_auditor_sha256=sha(__file__),run_manifest_sha256=sha(run/'manifest.json'))
        Path(output).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
        return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--raiz',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--ejecucion',type=Path,required=True);p.add_argument('--salida',type=Path,required=True)
    a=p.parse_args();print(json.dumps(Auditor(a.raiz).audit(a.ejecucion,a.salida),ensure_ascii=False,indent=2))
