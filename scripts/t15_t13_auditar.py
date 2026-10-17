"""Auditor independiente de T13 común: ecuaciones normales, pools y métricas escalares."""
import argparse
from collections import defaultdict
import gzip
import hashlib
import json
import math
from pathlib import Path
import numpy as np
from scripts.t15_e1_auditar import Auditor,csvread,sha
from scripts.t15_cuantilica_verificar_tablas import verificar_metricas

REGISTRO='registro/t15_t13/contrato_v1.json'


class AuditorT13(Auditor):
    def __init__(self,root):
        super().__init__(root)
        self.contract=json.loads((self.root/REGISTRO).read_text())
        self.procs={p['candidato']:p for p in self.contract['procedimientos']}
        for row in csvread(self.root/'registro/t15_t13/fuentes/variables_indices_extra.csv'):
            for c in self.contract['variables_nuevas']:self.table[row['id_parcela']][c]=row[c]
        self.external_choice={};self.external={};self.inner=defaultdict(list);self.tracekeys=set();self.nfits=0
        self.partitions={};self.max_H3=0.

    def record(self,t):
        tr,va=t['ids_entrenamiento'],t['ids_validacion'];esc,rep,f=t['escenario'],int(t['repeticion']),int(t['particion'])
        self.check(t['candidato'] in self.procs and t['version']=='comun-centrado-loo-v3','Identidad de candidato/método')
        self.check(t['estado']=='correcto' and not t['advertencias'],'Fit fallido/advertencias')
        self.check(tr==sorted(tr) and len(set(tr))==len(tr) and va==sorted(va) and len(set(va))==len(va),'IDs no únicos/ordenados')
        self.check(not set(tr)&set(va) and set(tr+va)<=self.known,'Fuga ID/59')
        field='particion_principal' if esc=='A' else 'particion_espacial'
        outer={i for i in self.known if int(self.parts[rep,i][field])!=f}
        if t['etapa']=='externa':self.check(set(tr)==outer and set(va)==self.known-outer,'Externa incorrecta')
        else:self.check(set(tr)|set(va)==outer,'Interna incluye externa')
        if esc=='B':self.check(not {self.parts[rep,i]['celda_chirps'] for i in tr}&{self.parts[rep,i]['celda_chirps'] for i in va},'Celda compartida B')
        eligible=[i for i in va if self.table[i]['municipio'] in {self.table[j]['municipio'] for j in tr}]
        self.check(eligible==t['ids_elegibles'],'Elegibles incorrectos')
        cols=t['columnas'];lam=t['lambda_reg'];proc=self.procs[t['candidato']]
        self.check((not cols and lam is None and t['opcion']=='referencia_sola') or
                   (cols==proc['columnas'] and lam in [.01,.1,1.,10.] and t['opcion']==f'abr_oct__lambda_{lam:g}'),'Opción fuera del registro')
        key=(t['candidato'],esc,rep,f,t['etapa'],t['opcion'],t.get('division_interna'))
        self.check(key not in self.tracekeys,'Traza repetida');self.tracekeys.add(key)
        pred,s,beta=self.predict(tr,va,cols,lam,'S');base=np.array([self.ref(tr,i)[0] for i in va])
        state=t['estado_modelo'];digest=hashlib.sha256(json.dumps(state,ensure_ascii=False,sort_keys=True,allow_nan=False,separators=(',',':')).encode()).hexdigest()
        self.check(digest==t['estado_modelo_sha256'],'Estado no vinculado al ajuste')
        self.check(state['ids_entrenamiento']==tr and state['columnas']==cols and state['lambda_reg']==lam and state['n']==len(tr),'Estado de otro entrenamiento')
        self.check(state['version']=='comun-centrado-loo-v3' and state['fit_intercept'] is False and state['intercepto']==0,'Intercepto/versión')
        query=t['consulta'];self.check([r['id_parcela'] for r in query]==va,'Consulta desalineada')
        self.close([r['prediccion'] for r in query],pred,'Predicción desde ecuaciones normales')
        self.close([r['referencia'] for r in query],base,'Referencia independiente')
        self.close([r['correccion'] for r in query],pred-base,'Corrección H3')
        self.check([r['fuente'] for r in query]==[self.ref(tr,i)[1] for i in va],'Fuente respaldo')
        self.close(t['media_abs_correccion'],np.mean(abs(pred-base)),'Corrección media')
        if s is not None:
            self.close(state['alpha'],len(tr)*lam,'Alpha n*lambda');self.close(state['media'],s['mean'],'Media train')
            self.close(state['escala'],s['scale'],'Escala train');self.close(state['coeficientes'],beta,'Coeficientes independientes')
            self.check(state['politica_centro_fit']=='mismo_pool_sin_fila_que_referencia_residual','Política LOO')
            for i in tr:
                source,pool=s['pools'][i]
                self.check(i not in pool and set(pool)<=set(tr),'Fuga pool LOO')
                self.check(state['pools_sin_fila'][i]==dict(fuente=source,n=len(pool),ids=pool),'Pool residual/centro distinto')
                self.close(state['centros_Z_sin_fila'][i],s['z'][[s['positions'][j] for j in pool]].mean(0),'Centro LOO')
            for attr,fieldname in [('centros_Z_municipio','municipio'),('centros_Z_grupo','cultivo_origen')]:
                names={self.table[i][fieldname] for i in tr};self.check(set(state[attr])==names,'Centros aprendidos fuera train')
                for name in names:
                    ix=[n for n,i in enumerate(tr) if self.table[i][fieldname]==name]
                    center=s['z'][ix].mean(0);self.close(state[attr][name],center,'Centro completo train')
                    if fieldname=='municipio':
                        shift=float(abs(((s['z'][ix]-np.asarray(state[attr][name]))@beta).mean()))
                        self.max_H3=max(self.max_H3,shift);self.check(shift<=1e-12,'Corrimiento municipal H3')
            self.close(state['centro_Z_global'],s['z'].mean(0),'Centro global')
            self.check([r['fuente_centrado'] for r in query]==[self.ref(tr,i)[1] for i in va],'Respaldo centro/referencia')
        else:
            self.check(state['alpha'] is None and all(r['fuente_centrado']=='no_aplica' for r in query),'Referencia no pura')
        errors=abs(pred-np.array([float(self.table[i]['rendimiento_t_ha']) for i in va]))
        if t['etapa']=='interna':
            mask=np.array([i in eligible for i in va]);self.close(t['MAE'],errors[mask].mean(),'MAE interna');self.close(t['MAE_todas'],errors.mean(),'MAE todas')
            self.inner[t['candidato'],esc,rep,f,t['opcion']].extend((i,float(e),i in eligible) for i,e in zip(va,errors))
            partkey=(esc,rep,f,t['division_interna']);pair=(tuple(tr),tuple(va))
            if partkey in self.partitions:self.check(self.partitions[partkey]==pair,'Particiones asimétricas por opción/bloque')
            self.partitions[partkey]=pair
        else:
            self.external[t['candidato'],esc,rep,f]=(va,pred)
            self.external_choice[t['candidato'],esc,rep,f]=(t['opcion'],cols,lam)
        self.nfits+=1

    def tables(self,run,rows):
        n=0;maxdiff=0.;quality={r['id_parcela']:r for r in csvread(self.root/'registro/t07/calidad_parcelas.csv')}
        for fname,individual in [('metricas_resumen.csv',False),('metricas_por_repeticion.csv',True),('desgloses_calidad_y_sin24.csv',False)]:
            reports=csvread(run/fname)
            if fname!='desgloses_calidad_y_sin24.csv':self.check(len(reports)==(100 if individual else 20),'Cobertura tablas')
            keys=set()
            for r in reports:
                g=[v for v in rows if v['candidato']==r['candidato'] and v['escenario']==r['escenario'] and (r['subconjunto']=='todas' or v['fuente']=='municipio')]
                if individual:g=[v for v in g if v['repeticion']==r['repeticion']]
                if fname=='desgloses_calidad_y_sin24.csv':
                    kind,val=r['desglose'],r['valor'];k=(r['candidato'],r['escenario'],r['subconjunto'],kind,val)
                    self.check(k not in keys,'Desglose duplicado');keys.add(k)
                    if kind=='sensibilidad_sin24':g=[v for v in g if quality[v['ID_POLIGONO']]['alerta_contorno_t03_bis']!='si']
                    else:
                        field='cultivo_origen' if kind=='grupo_registro' else kind
                        source=self.table if kind in ['municipio','grupo_registro'] else quality
                        g=[v for v in g if (source[v['ID_POLIGONO']][field] or 'no_documentado')==val]
                nn,dd=verificar_metricas(g,r,individual);n+=nn;maxdiff=max(maxdiff,dd)
        contrasts=csvread(run/'contrastes.csv');self.check(len(contrasts)==20,'Contrastes incompletos')
        idx={(r['candidato'],r['escenario'],int(r['repeticion']),r['ID_POLIGONO']):r for r in rows}
        for r in contrasts:
            a,b,esc,sub=r['candidato'],r['frente_a'],r['escenario'],r['subconjunto']
            keys=sorted(k[1:] for k in idx if k[0]==a and k[1]==esc and (sub=='todas' or idx[k]['fuente']=='municipio'))
            perid=defaultdict(list);perrep=defaultdict(list)
            for k in keys:
                aa,bb=idx[a,*k],idx[b,*k];y=float(aa['real']);ea=float(aa['prediccion'])-y;eb=float(bb['prediccion'])-y
                vector=[abs(ea),abs(eb),ea*ea,eb*eb];perid[k[2]].append(vector);perrep[k[1]].append(vector)
            vectors={i:np.array([math.fsum(v[j] for v in values)/len(values) for j in range(4)]) for i,values in perid.items()}
            repvals={k:np.array([math.fsum(v[j] for v in values)/len(values) for j in range(4)]) for k,values in perrep.items()}
            dMAE=math.fsum(v[0]-v[1] for v in vectors.values())/len(vectors)
            diffs=[repvals[k][0]-repvals[k][1] for k in range(1,6)]
            dRMSE=math.fsum(math.sqrt(v[2])-math.sqrt(v[3]) for v in repvals.values())/5
            cells=defaultdict(list)
            for pid,v in vectors.items():cells[self.parts[1,pid]['celda_chirps']].append(v)
            blocks=sorted(cells);sums=np.array([[math.fsum(v[j] for v in cells[k]) for j in range(4)] for k in blocks]);sizes=np.array([len(cells[k]) for k in blocks])
            draws=np.random.RandomState(20261006).randint(len(blocks),size=(5000,len(blocks)))
            values=sums[draws].sum(1)/sizes[draws].sum(1)[:,None]
            ci=np.percentile(values[:,0]-values[:,1],[2.5,97.5]);ric=np.percentile(np.sqrt(values[:,2])-np.sqrt(values[:,3]),[2.5,97.5])
            self.close(r['dMAE'],dMAE,'Delta MAE independiente');self.close(r['dRMSE'],dRMSE,'Delta RMSE');self.close(json.loads(r['IC95_celdas_MAE']),ci,'IC por celdas');self.close(json.loads(r['IC95_celdas_RMSE']),ric,'IC RMSE')
            self.close(json.loads(r['dMAE_por_repeticion']),diffs,'Deltas repetición');self.check(int(r['n_parcelas'])==len(vectors) and int(r['n_predicciones'])==len(keys) and int(r['n_celdas'])==len(cells),'Denominadores de contraste')
            rule=dMAE<=-.01 and ci[1]<0 and sum(d<0 for d in diffs)>=4 and dRMSE<=.01
            self.check((r['cumple_regla_T03']=='True')==rule,'Regla T03')
            self.check((r['elegible_para_promocion_principal']=='True')==(rule and esc=='A' and sub=='sin_respaldo' and a=='t15_t13_S_verdor_v1' and b=='media_mun__resp_grupo'),'Promoción ajena')
        self.close(maxdiff,0,'Diferencia métricas escalares');return n


def auditar(root,run,out):
    root,run,out=Path(root),Path(run),Path(out)
    if out.exists():raise ValueError('No sobrescribir auditoría')
    a=AuditorT13(root);manifest=json.loads((run/'manifest.json').read_text())
    a.check(manifest['estado'] in ['piloto_funcional_no_desempeno_global','completa_pendiente_auditoria'],'Ejecución no completa/correcta')
    a.check(sha(root/REGISTRO)==manifest['contrato_sha256'],'Contrato de otra corrida')
    for p,h in {**manifest['fuentes_sha256'],**manifest['codigo_sha256']}.items():a.check(sha(root/p)==h,'Fuente/código alterado '+p)
    for p,h in manifest['archivos_sha256'].items():a.check(sha(run/p)==h,'Resultado alterado '+p)
    with gzip.open(run/'trazas_ajustes.jsonl.gz','rt') as f:
        for line in f:a.record(json.loads(line))
    seen=set();choices={}
    with (run/'selecciones.jsonl').open() as f:
        for line in f:
            s=json.loads(line);key=(s['candidato'],s['escenario'],s['repeticion'],s['particion']);a.check(key not in seen,'Selección duplicada');seen.add(key)
            a.check(len(s['puntuaciones'])==5,'Menú no completo')
            for score in s['puntuaciones']:
                values=a.inner[*key,score['nombre']];ids=[v[0] for v in values]
                outer={i for i in a.known if int(a.parts[key[2],i]['particion_principal' if key[1]=='A' else 'particion_espacial'])!=key[3]}
                a.check(set(ids)==outer and len(ids)==len(outer),'Validaciones internas incompletas/repetidas')
                a.close(score['MAE'],np.mean([v for _,v,b in values if b]),'Puntuación interna');a.close(score['MAE_todas'],np.mean([v for _,v,_ in values]),'Puntuación todas')
            tie=lambda r:(round(r['MAE'],6),0 if r['referencia_sola'] else 1,-(r['lambda_reg'] or 0),0 if r['ventana']=='jun_oct' else 1,r['nombre'])
            winner=min(s['puntuaciones'],key=tie);a.check(winner['nombre']==s['nombre_opcion']==s['elegida']['nombre'],'Desempate/selección incorrecta')
            a.check((s['elegida']['columnas']==[])==winner['referencia_sola'],'Referencia falsa')
            a.check(a.external_choice[key]==(s['elegida']['nombre'],s['elegida']['columnas'],s['elegida']['lambda_reg']),'Ajuste externo distinto del seleccionado');choices[key]=s
    full=manifest['evaluacion_completa'];rows=csvread(run/('predicciones_oof.csv' if full else 'oof_parcial_prueba.csv'))
    newseen=set();old=[]
    for p in ['registro/t15_resultados/predicciones_oof.csv','registro/t03/predicciones_oof_referencias_mediana_mun__resp_grupo.csv']:
        old.extend(r for r in csvread(root/p) if r['candidato'] in a.contract['comparadores_reutilizados'])
    oldidx={(r['candidato'],r['escenario'],int(r['repeticion']),r['ID_POLIGONO']):r for r in old}
    for r in rows:
        cand,esc,rep,pid=r['candidato'],r['escenario'],int(r['repeticion']),r['ID_POLIGONO'];key=(cand,esc,rep,pid)
        a.check(key not in newseen and pid in a.known,'OOF repetida/59');newseen.add(key)
        a.close(r['real'],a.table[pid]['rendimiento_t_ha'],'Etiqueta OOF');fold=int(r['particion'])
        a.check(int(a.parts[rep,pid]['particion_principal' if esc=='A' else 'particion_espacial'])==fold,'OOF en fold ajeno')
        if cand in a.procs:
            va,pred=a.external[cand,esc,rep,fold];a.close(r['prediccion'],pred[va.index(pid)],'OOF distinta de ajuste')
            train=[i for i in a.known if int(a.parts[rep,i]['particion_principal' if esc=='A' else 'particion_espacial'])!=fold]
            a.check(r['fuente']==a.ref(train,pid)[1],'Fuente OOF')
        else:a.check(key in oldidx and r==oldidx[key],'Comparador previo alterado')
    a.check(a.nfits==(2100 if full else 84) and len(seen)==(100 if full else 4),'Presupuesto/contextos incompletos')
    newrows=[r for r in rows if r['candidato'] in a.procs]
    a.check(csvread(run/'predicciones_incrementales.csv')==newrows,'OOF incremental desalineada')
    scalar=0
    if full:
        a.check(len(rows)==6900 and len(newrows)==2760,'Cobertura final OOF')
        expected={(c,s,r,pid) for c in set(a.procs)|set(a.contract['comparadores_reutilizados']) for s in ['A','B'] for r in range(1,6) for pid in a.known}
        a.check(newseen==expected,'Claves OOF incompletas');scalar=a.tables(run,rows)
        freq=csvread(run/'frecuencia_referencia_sola.csv');a.check(len(freq)==4,'Frecuencia incompleta')
        for row in freq:
            sels=[v for k,v in choices.items() if k[:2]==(row['candidato'],row['escenario'])]
            a.check(int(row['n_contextos'])==len(sels)==25 and int(row['n_referencia_sola'])==sum(v['referencia_sola'] for v in sels),'Frecuencia incorrecta')
        contrasts=csvread(run/'contrastes.csv');pick=lambda b:next(r for r in contrasts if r['candidato']=='t15_t13_S_verdor_v1' and r['frente_a']==b and r['escenario']=='A' and r['subconjunto']=='sin_respaldo')
        x,y=pick('media_mun__resp_grupo'),pick('t15_t13_control_S_abr_v1');d=json.loads((run/'decision.json').read_text())
        t03=x['cumple_regla_T03']=='True';aporte=float(y['dMAE'])<0 and json.loads(y['IC95_celdas_MAE'])[1]<0
        a.check(d['cumple_T03']==t03 and d['cumple_guardia_aporte']==aporte and d['elegible_por_contrato']==(t03 and aporte),'Decisión no corresponde al contrato')
    result=dict(resultado='aprobado',ajustes=a.nfits,selecciones=len(seen),OOF=len(rows),comprobaciones=a.n,comprobaciones_metricas_escalares=scalar,
        diferencia_maxima=a.max_diff,max_corrimiento_H3=a.max_H3,tolerancia=1e-12,importa_productor_sklearn=False,
        reconstruye_ecuaciones_normales=True,manifest_sha256=sha(run/'manifest.json'),auditor_sha256=sha(__file__))
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--raiz',type=Path,required=True);p.add_argument('--entrada',type=Path,required=True);p.add_argument('--salida',type=Path,required=True);a=p.parse_args()
    print(json.dumps(auditar(a.raiz,a.entrada,a.salida),ensure_ascii=False,indent=2))
