"""Auditor E2 completo: ecuaciones normales, selección, OOF, métricas y guardias independientes."""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import numpy as np
from scripts.t15_e2_auditar_modelo import AuditorModeloE2,MAP
from scripts.t15_e1_auditar import csvread,text_artifact,sha

REF='media_mun__resp_grupo'
PREFIX='comun_centrado_loo_v3_'


def metricas(rows):
    a=np.asarray([(float(r['real']),float(r['prediccion'])) for r in rows])
    e=a[:,1]-a[:,0];den=np.mean((a[:,0]-a[:,0].mean())**2)
    return dict(MAE=float(np.abs(e).mean()),RMSE=float(np.sqrt(np.mean(e**2))),
                R2=None if den==0 else float(1-np.mean(e**2)/den),sesgo=float(e.mean()))


class AuditorEvaluacionE2(AuditorModeloE2):
    def audit_evaluacion(self,run,output):
        run,output=Path(run),Path(output)
        self.check(not output.exists(),'No sobrescribir auditoría')
        m=json.loads((run/'manifest.json').read_text());full=m['evaluacion_completa']
        self.check(m['schema']=='E2_evaluacion_v1' and m['estado']==('completa_verificada' if full else
                   'prueba_funcional_parcial_no_desempeno_global'),'Ejecución incompleta/fallida')
        self.check(m['predicciones_finales59']==0 and m['ganador_T16_congelado'] is False,'Alcance excedido')
        for group in ['codigo_sha256','fuentes_sha256','codigo_modelo_sha256']:
            for name,h in m[group].items():self.check(sha(self.root/name)==h,'Código/fuente distinta '+name)
        for name,h in m['archivos_sha256'].items():self.check(sha(run/name)==h,'Resultado alterado '+name)
        self.check(sha(self.root/'registro/t15_e2_modelo/registro_ejecucion_v1.json')==m['registro_sha256'],'Otro registro')
        self.check(sha(self.root/'registro/t15_e2_evaluacion/autorizacion_v1.json')==m['autorizacion_sha256'],'Otra autorización')
        cfg=json.loads((self.root/'registro/t15_e2_modelo/registro_ejecucion_v1.json').read_text())
        menus={o['nombre']:o for o in cfg['opciones_base']}
        menus['referencia_sola']=dict(columnas=[],lambda_reg=None,ventana='estatica')
        candidates={p['candidato']:p['modo'] for p in cfg['procedimientos']}
        expected_ctx={(s,r,f) for s in ['A','B'] for r in range(1,6) for f in range(5)} if full else {('A',1,0),('B',1,0)}
        traces=0;seen=set();external={};inner=defaultdict(list);divisions={};last=None
        with text_artifact(run/'trazas_ajustes.jsonl') as f:
            for line in f:
                t=json.loads(line);tr,va=t['ids_entrenamiento'],t['ids_validacion'];traces+=1
                candidate=t['candidato'];ctx=(t['escenario'],int(t['repeticion']),int(t['particion']))
                self.check(candidate in candidates and ctx in expected_ctx,'Procedimiento/contexto ajeno')
                if ctx!=last:self.cache.clear();last=ctx
                key=(candidate,*ctx,t['etapa'],t['opcion'],t.get('division_interna'))
                self.check(key not in seen,'Traza duplicada');seen.add(key)
                self.check(t['estado']=='correcto' and not t['advertencias'],'Ajuste fallido/advertencia')
                self.check(tr==sorted(tr) and va==sorted(va) and len(tr)==len(set(tr)) and len(va)==len(set(va)),'IDs inválidos')
                self.check(not set(tr)&set(va) and set(tr+va)<=self.known,'Fuga de validación/59')
                s,r,fold=ctx;field='particion_principal' if s=='A' else 'particion_espacial'
                outer={i for i in self.known if int(self.parts[r,i][field])!=fold}
                if t['etapa']=='externa':self.check(set(tr)==outer and set(va)==self.known-outer,'Partición externa')
                else:
                    self.check(t['etapa']=='interna' and t['division_interna'] in range(4),'División interna ajena')
                    self.check(set(tr)|set(va)==outer,'Interna usa validación externa')
                    divkey=(*ctx,t['division_interna']);pair=(tuple(tr),tuple(va))
                    if divkey in divisions:self.check(divisions[divkey]==pair,'Particiones cambian por opción/candidato')
                    divisions[divkey]=pair
                if s=='B':self.check(not {self.parts[r,i]['celda_chirps'] for i in tr}&
                    {self.parts[r,i]['celda_chirps'] for i in va},'Celda compartida B')
                eligible=[i for i in va if self.table[i]['municipio'] in {self.table[j]['municipio'] for j in tr}]
                self.check(eligible==t['ids_elegibles'],'Elegibilidad distinta')
                option=menus[t['opcion']]
                self.check((t['columnas_base'],t['lambda_reg'],t['ventana'])==
                    (option['columnas'],option['lambda_reg'],option['ventana']),'Menú modificado')
                mode=candidates[candidate] if option['columnas'] else 'referencia'
                self.check(t['modo_E2']==mode and t['procedimiento_solicitado']==candidates[candidate],'Modo/control mezclado')
                pred,state,beta=self.predict(tr,va,t['columnas_base'],t['lambda_reg'],MAP[mode])
                self.close(t['n_entrenamiento'],len(tr),'n train')
                self.close(t['n_validacion'],len(va),'n consulta')
                if state is not None:
                    self.close(t['alpha'],len(tr)*t['lambda_reg'],'Alpha n completo')
                    prep=t['preprocesamiento_E1']
                    self.check(prep['ids_entrenamiento']==tr and prep['ids_admisibles']==state['admitted'],'Preparación fuera de train')
                    self.check(prep['extension_activa']==state['active'],'Activación por consulta')
                    if state['median'] is None:self.check(prep['mediana_E1'] is None,'Mediana ajena')
                    else:self.close(prep['mediana_E1'],state['median'],'Mediana sólo train')
                errors=np.abs(pred-np.asarray([float(self.table[i]['rendimiento_t_ha']) for i in va]))
                if t['etapa']=='interna':
                    mask=np.asarray([i in eligible for i in va]);self.close(t['MAE'],errors[mask].mean(),'MAE interno')
                    self.close(t['MAE_todas'],errors.mean(),'MAE interno todas')
                    inner[candidate,*ctx,t['opcion']].extend((i,float(e),i in eligible) for i,e in zip(va,errors))
                else:external[candidate,*ctx]=(t,pred,tr,va)
        self.check(len(external)==3*len(expected_ctx) and len(inner)==27*len(expected_ctx),'Menú/contextos incompletos')
        for (cand,s,r,fold,opt),pairs in inner.items():
            field='particion_principal' if s=='A' else 'particion_espacial'
            expected={i for i in self.known if int(self.parts[r,i][field])!=fold}
            self.check(len(pairs)==len(expected) and {i for i,_,_ in pairs}==expected,'Cobertura interna')
        choices=set()
        with text_artifact(run/'selecciones.jsonl') as f:
            for line in f:
                row=json.loads(line);key=(row['candidato'],row['escenario'],int(row['repeticion']),int(row['particion']))
                self.check(key in external and key not in choices,'Selección ajena/duplicada');choices.add(key)
                scores=row['puntuaciones'];self.check(len(scores)==9 and {x['nombre'] for x in scores}==set(menus),'Opciones selección incompletas')
                for score in scores:
                    pairs=inner[*key,score['nombre']]
                    self.close(score['MAE'],np.mean([e for _,e,b in pairs if b]),'Puntuación elegible')
                    self.close(score['MAE_todas'],np.mean([e for _,e,_ in pairs]),'Puntuación todas')
                    opt=menus[score['nombre']]
                    self.check(score['referencia_sola']==(not opt['columnas']) and
                               score['lambda_reg']==opt['lambda_reg'] and score['ventana']==opt['ventana'],'Metadatos de desempate alterados')
                    self.close(score['n_elegibles'],sum(b for _,_,b in pairs),'Población puntuación')
                tie=lambda a:(round(a['MAE'],6),0 if a['referencia_sola'] else 1,-(a['lambda_reg'] or 0),0 if a['ventana']=='jun_oct' else 1,a['nombre'])
                winner=min(scores,key=tie)['nombre'];t=external[key][0]
                self.check(row['nombre_opcion']==t['opcion']==winner,'Selección no corresponde a entrenamiento')
                self.check(row['columnas_base']==t['columnas_base'] and row['lambda_reg']==t['lambda_reg'],'Ajuste externo no seleccionado')
        self.check(choices==set(external),'Faltan selecciones')
        states=set()
        with text_artifact(run/'estados_modelos.jsonl') as f:
            for line in f:
                row=json.loads(line);key=(row['candidato'],row['escenario'],int(row['repeticion']),int(row['particion']))
                self.check(key in external and key not in states,'Estado ajeno/duplicado');states.add(key)
                t,pred,tr,va=external[key];state=row['estado_modelo']
                digest=hashlib.sha256(json.dumps(state,sort_keys=True,ensure_ascii=False,allow_nan=False,separators=(',',':')).encode()).hexdigest()
                self.check(digest==t['estado_modelo_sha256'],'Estado no vinculado al ajuste')
                self.verificar(dict(ids_entrenamiento=tr,ids_consulta=va,modo=t['modo_E2'],
                    columnas_base=t['columnas_base'],lambda_reg=t['lambda_reg'],estado_modelo=state,consulta=row['consulta']))
                self.close([x['prediccion'] for x in row['consulta']],pred,'Consulta/traza')
        self.check(states==set(external),'Faltan estados externos')
        oof=csvread(run/('predicciones_oof.csv' if full else 'oof_parcial_prueba.csv'))
        old={(r['candidato'],r['escenario'],int(r['repeticion']),r['ID_POLIGONO']):r
             for r in csvread(self.root/'registro/t15_e1_evaluacion/resultados/predicciones_oof.csv')
             if r['candidato'] in [REF,PREFIX+'S',PREFIX+'E1']}
        oo=set();reused=0
        for row in oof:
            cand,s,rep,pid=row['candidato'],row['escenario'],int(row['repeticion']),row['ID_POLIGONO'];k=(cand,s,rep,pid)
            self.check(k not in oo and pid in self.known,'OOF duplicada/59');oo.add(k)
            fold=int(row['particion']);field='particion_principal' if s=='A' else 'particion_espacial'
            self.check(fold==int(self.parts[rep,pid][field]) and row['version']=='comun-centrado-loo-v3','Partición/versión OOF')
            if k in old:
                self.check(full and row==old[k],'Comparador previo modificado');reused+=1
            else:
                t,pred,tr,va=external[cand,s,rep,fold]
                self.close(row['prediccion'],pred[va.index(pid)],'OOF independiente')
                self.check(row['fuente']==self.ref(tr,pid)[1],'Respaldo OOF')
            self.close(row['real'],self.table[pid]['rendimiento_t_ha'],'Etiqueta original')
        expected_new={(c,s,r,pid) for (c,s,r,f),(t,pred,tr,va) in external.items() for pid in va}
        self.check(oo==expected_new| (set(old) if full else set()),'Cobertura OOF no exacta')
        self.check(traces==111*len(expected_ctx),'Número de trazas incorrecto')
        if full:self.auditar_reportes(run,oof,cfg)
        result=dict(schema='E2_auditoria_evaluacion_v1',resultado='aprobado',comprobaciones=self.n,
            diferencia_maxima=self.max_diff,tolerancia_absoluta=1e-12,trazas=traces,ajustes_externos=len(external),
            selecciones=len(choices),OOF=len(oof),OOF_reutilizadas=reused,evaluacion_completa=full,
            importa_productor_o_sklearn=False,H3_todos_estados_verificados=True,
            codigo_auditor_sha256=sha(__file__),run_manifest_sha256=sha(run/'manifest.json'))
        output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
        return result

    def auditar_reportes(self,run,rows,cfg):
        summary=csvread(run/'metricas_resumen.csv');reps=csvread(run/'metricas_por_repeticion.csv')
        contrasts=csvread(run/'contrastes_E2_con_guardia.csv');raw=csvread(run/'contrastes.csv')
        names={REF,PREFIX+'S',PREFIX+'E1',PREFIX+'E2',PREFIX+'E12',PREFIX+'E2Q'}
        expected={(c,s,u) for c in names for s in ['A','B'] for u in ['todas','sin_respaldo']}
        self.check(len(summary)==24 and {(r['candidato'],r['escenario'],r['subconjunto']) for r in summary}==expected,'Resumen incompleto')
        main={};selections={}
        for row in summary:
            g=[r for r in rows if r['candidato']==row['candidato'] and r['escenario']==row['escenario'] and (row['subconjunto']=='todas' or r['fuente']=='municipio')]
            per_id=defaultdict(list);per_rep=defaultdict(list)
            for r in g:per_id[r['ID_POLIGONO']].append(r);per_rep[int(r['repeticion'])].append(r)
            self.close(row['n_parcelas'],len(per_id),'Denominador ID');self.close(row['n_predicciones'],len(g),'Denominador OOF')
            self.close(row['MAE_por_parcela'],np.mean([metricas(v)['MAE'] for v in per_id.values()]),'MAE por parcela')
            for field in ['RMSE','R2','MAE']:
                val=np.mean([metricas(v)[field] for v in per_rep.values()]);self.close(row[field+'_media_repeticiones'],val,field+' por repetición')
            if row['escenario']=='A' and row['subconjunto']=='sin_respaldo':main[row['candidato']]=row
        self.check(len(reps)==120 and len({(r['candidato'],r['escenario'],r['subconjunto'],r['repeticion']) for r in reps})==120,'Repeticiones incompletas')
        for r in reps:
            g=[a for a in rows if a['candidato']==r['candidato'] and a['escenario']==r['escenario'] and a['repeticion']==r['repeticion'] and (r['subconjunto']=='todas' or a['fuente']=='municipio')]
            for k,v in metricas(g).items():self.close(r[k],v,'Reporte repetición '+k)
        expected_pairs={(PREFIX+p['candidato'],REF if p['frente_a']=='referencia' else PREFIX+p['frente_a'],s,u)
                        for p in cfg['contrastes'] for s in ['A','B'] for u in ['todas','sin_respaldo']}
        self.check(len(raw)==len(contrasts)==28 and {(r['candidato'],r['frente_a'],r['escenario'],r['subconjunto']) for r in contrasts}==expected_pairs,'Contrastes incompletos')
        by={(r['candidato'],r['escenario'],int(r['repeticion']),r['ID_POLIGONO']):r for r in rows};eligible=[]
        for row in contrasts:
            c,b,s,u=row['candidato'],row['frente_a'],row['escenario'],row['subconjunto']
            pairs=defaultdict(list);per_rep=defaultdict(list)
            for pid in sorted(self.known):
                for rep in range(1,6):
                    a,z=by[c,s,rep,pid],by[b,s,rep,pid]
                    if u=='sin_respaldo' and a['fuente']!='municipio':continue
                    ea=float(a['prediccion'])-float(a['real']);eb=float(z['prediccion'])-float(z['real'])
                    v=np.asarray([abs(ea),abs(eb),ea**2,eb**2]);pairs[pid].append(v);per_rep[rep].append(v)
            means={i:np.mean(v,axis=0) for i,v in pairs.items()};rv={i:np.mean(v,axis=0) for i,v in per_rep.items()}
            d=float(np.mean([v[0]-v[1] for v in means.values()]));dr=[rv[i][0]-rv[i][1] for i in range(1,6)]
            rm=float(np.mean([np.sqrt(rv[i][2])-np.sqrt(rv[i][3]) for i in range(1,6)]))
            cells=defaultdict(list)
            for pid,v in means.items():cells[self.parts[1,pid]['celda_chirps']].append(v)
            keys=sorted(cells);sums=np.asarray([np.sum(cells[k],axis=0) for k in keys]);sizes=np.asarray([len(cells[k]) for k in keys])
            ix=np.random.RandomState(20261006).randint(len(keys),size=(5000,len(keys)))
            boot=sums[ix].sum(1)/sizes[ix].sum(1)[:,None]
            ic=np.percentile(boot[:,0]-boot[:,1],[2.5,97.5]);family=np.percentile(boot[:,0]-boot[:,1],[1.25,98.75])
            self.close(row['dMAE'],d,'ΔMAE');self.close(row['dRMSE'],rm,'ΔRMSE')
            self.close(json.loads(row['dMAE_por_repeticion']),dr,'Δ repeticiones')
            self.close(json.loads(row['IC95_celdas_MAE']),ic,'IC95 espacial')
            self.close(json.loads(row['IC97_5_celdas_MAE_familia']),family,'IC97.5 espacial familiar')
            self.close(json.loads(row['IC95_celdas_RMSE']),np.percentile(np.sqrt(boot[:,2])-np.sqrt(boot[:,3]),[2.5,97.5]),'IC95 RMSE')
            rule=bool(d<=-.01 and ic[1]<0 and sum(x<0 for x in dr)>=4 and rm<=.01)
            promotion=row['tipo_contraste']=='promocion' and c in [PREFIX+'E2',PREFIX+'E12'] and b==REF and s=='A' and u=='sin_respaldo'
            self.check((row['cumple_regla_T03']=='True')==rule,'Regla T03')
            self.check((row['cumple_guardia_familia']=='True')==bool(family[1]<0),'Guardia familiar')
            ok=bool(rule and family[1]<0 and promotion)
            self.check((row['elegible_E2_con_guardia']=='True')==ok,'Promoción indebida')
            if ok:eligible.append(c)
        decision=json.loads((run/'decision_E2.json').read_text())
        chosen=min(eligible,key=lambda c:(round(float(main[c]['MAE_por_parcela']),6),0 if c==PREFIX+'E2' else 1)) if eligible else REF
        self.check(decision['alternativas_elegibles']==eligible and decision['procedimiento_recomendado_por_regla']==chosen,'Decisión diferente a reglas')
        self.check(decision['ganador_T16_congelado'] is False and decision['E2Q_promovible'] is False,'Cierre prematuro/control promovido')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--raiz',type=Path,default=Path(__file__).resolve().parents[1])
    p.add_argument('--ejecucion',type=Path,required=True);p.add_argument('--salida',type=Path,required=True)
    a=p.parse_args();print(json.dumps(AuditorEvaluacionE2(a.raiz).audit_evaluacion(a.ejecucion,a.salida),ensure_ascii=False,indent=2))
