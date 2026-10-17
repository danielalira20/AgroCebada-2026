"""Auditor numérico E2 independiente del productor/sklearn; no calcula métricas de aporte."""
import argparse
import csv
import gzip
import hashlib
import json
from pathlib import Path
import numpy as np
from scripts.t15_e1_auditar import Auditor, csvread, sha

MAP={'E2':'S','E12':'E1','E2Q':'Q','referencia':'referencia'}
COLUMNS=['e2_tpi150_media_m','e2_exposicion_este_media','e2_exposicion_norte_media']


class AuditorModeloE2(Auditor):
    def __init__(self,root):
        super().__init__(root)
        rows=csvread(self.root/'registro/t15_e2_extraccion/atributos_parcela.csv')
        self.check(len(rows)==197 and len({r['id_parcela'] for r in rows})==197,'IDs E2 inválidos')
        self.check(list(rows[0])==['id_parcela',*COLUMNS],'Columnas E2 ajenas')
        self.check(set(self.table)=={r['id_parcela'] for r in rows},'IDs E2/T07 mezclados')
        for row in rows:
            self.check(not set(COLUMNS)&set(self.table[row['id_parcela']]),'E2 pisa T07')
            self.table[row['id_parcela']].update({c:row[c] for c in COLUMNS})

    def verificar(self,record):
        tr,q=record['ids_entrenamiento'],record['ids_consulta'];mode=record['modo']
        self.check(mode in MAP and tr==sorted(tr) and len(tr)==len(set(tr)),'Procedimiento/IDs train')
        self.check(len(q)==len(set(q)) and not set(tr)&set(q) and set(tr+q)<=self.known,'Fuga/59/IDs')
        state=record['estado_modelo'];columns=record['columnas_base'];lam=record['lambda_reg']
        pred,s,beta=self.predict(tr,q,columns,lam,MAP[mode])
        self.check(state['ids_entrenamiento']==tr and state['n']==len(tr),'Entrenamiento no coincide')
        self.check(state['procedimiento_E2']==mode and state['E2_imputada'] is False,'Otro adaptador/imputación')
        self.check(state['fit_intercept'] is False and state['intercepto']==0,'Intercepto no registrado')
        self.check(state['diagnostico_sin_promocion']==(mode=='E2Q'),'Control promovido')
        raw=record['consulta'];self.check([r['id_parcela'] for r in raw]==q,'Consulta desalineada')
        self.close([r['prediccion'] for r in raw],pred,'Predicción independiente E2')
        base=np.asarray([self.ref(tr,pid)[0] for pid in q])
        self.close([r['referencia'] for r in raw],base,'Referencia territorial')
        self.close([r['correccion'] for r in raw],pred-base,'H3 corrección consulta')
        self.check([r['fuente'] for r in raw]==[self.ref(tr,pid)[1] for pid in q],'Fuentes referencia')
        self.check(state['version']=='comun-centrado-loo-v3','Otro núcleo común')
        if s is None:
            self.check(not columns and state['alpha'] is None,'Referencia no pura')
            self.check(all(r['fuente_centrado']=='no_aplica' for r in raw),'Centrado de referencia')
            return
        expected=list(columns)+(['e1_ndwi_post15_45'] if mode=='E12' else [])+(['e1_no_utilizable'] if mode in ['E12','E2Q'] else [])
        self.check(state['columnas']==expected==state['nombres_transformados'],'Dimensiones/orden incorrectos')
        self.close(state['alpha'],len(tr)*lam,'Alpha n completo')
        self.close(state['media'],s['mean'],'Media sólo train')
        self.close(state['escala'],s['scale'],'Escala sólo train')
        self.close(state['coeficientes'],beta,'Coeficientes ecuaciones normales')
        self.check(state['politica_centro_fit']=='mismo_pool_sin_fila_que_referencia_residual','Centrado LOO distinto')
        for n,pid in enumerate(tr):
            source,pool=s['pools'][pid]
            self.check(pid not in pool and set(pool)<=set(tr),'Pool incluye propia/validación')
            self.check(state['pools_sin_fila'][pid]==dict(fuente=source,n=len(pool),ids=pool),'Pool de centro/residuo')
            self.close(state['centros_Z_sin_fila'][pid],s['z'][[s['positions'][i] for i in pool]].mean(0),'Centro LOO todas columnas')
        for attr,col in [('centros_Z_municipio','municipio'),('centros_Z_grupo','cultivo_origen')]:
            names=sorted({self.table[i][col] for i in tr});self.check(set(state[attr])==set(names),'Grupos aprendidos fuera de train')
            for group in names:
                ix=[n for n,pid in enumerate(tr) if self.table[pid][col]==group]
                self.close(state[attr][group],s['z'][ix].mean(0),'Centro guardado '+col)
        self.close(state['centro_Z_global'],s['z'].mean(0),'Centro global guardado')
        prep=state['preprocesamiento_E1']
        self.check(prep['ids_entrenamiento']==tr and prep['ids_admisibles']==s['admitted'],'Preparación usa otras filas')
        self.check(prep['extension_activa']==s['active'],'Activación con consulta')
        if s['median'] is None:self.check(prep['mediana_E1'] is None,'Mediana no aplicable')
        else:self.close(prep['mediana_E1'],s['median'],'Mediana sólo train')
        self.check([r['fuente_centrado'] for r in raw]==[self.ref(tr,pid)[1] for pid in q],'H3 respaldo consulta')


def auditar(root,run,output):
    root,run,output=Path(root),Path(run),Path(output)
    if output.exists():raise ValueError('No sobrescribir auditoría')
    m=json.loads((run/'manifest.json').read_text())
    if m['schema']!='E2_previa_modelo_v1' or m['estado']!='verificacion_tecnica_completa' or m['evaluacion_aporte_completa']:
        raise ValueError('No es comprobación previa completa')
    a=AuditorModeloE2(root)
    for name,h in m['codigo_sha256'].items():a.check(sha(root/name)==h,'Código distinto '+name)
    for name,h in m['fuentes_sha256'].items():a.check(sha(root/name)==h,'Entrada distinta '+name)
    for name,h in m['archivos_sha256'].items():a.check(sha(run/name)==h,'Resultado alterado '+name)
    records=[]
    with (run/'ajustes_verificacion.jsonl').open() as f:
        for line in f:
            rec=json.loads(line);a.verificar(rec);records.append(rec)
    expected={(esc,w,mode) for esc in ['A','B'] for w in ['abr_oct','jun_oct'] for mode in MAP}
    a.check(len(records)==16 and {(r['escenario'],r['ventana'],r['modo']) for r in records}==expected,'Pruebas reales incompletas')
    for rec in records:
        field='particion_principal' if rec['escenario']=='A' else 'particion_espacial'
        expected_train={i for i in a.known if int(a.parts[1,i][field])!=0}
        a.check(set(rec['ids_entrenamiento'])==expected_train and set(rec['ids_consulta'])==a.known-expected_train,'Contexto de otra partición')
    # Deliberately remove centering, then repair the total prediction to keep it consistent:
    # the numerical audit must reject H3 even if no file/hash mismatch is involved.
    import copy
    bad=copy.deepcopy(next(r for r in records if r['modo']=='E12'))
    tr,q=bad['ids_entrenamiento'],bad['ids_consulta']
    s=a.prepare(tr,bad['columnas_base'],'E1');beta=np.asarray(bad['estado_modelo']['coeficientes'])
    uncentered=((s['raw'](q)-s['mean'])/s['scale'])@beta
    for row,correction in zip(bad['consulta'],uncentered):
        row['correccion']=float(correction);row['prediccion']=row['referencia']+float(correction)
    negative=AuditorModeloE2(root)
    try:negative.verificar(bad)
    except ValueError:rejected=True
    else:raise ValueError('El auditor aceptó quitar H3')
    result=dict(schema='E2_auditoria_modelo_v1',resultado='aprobado',ajustes_recalculados=16,
                comprobaciones=a.n,diferencia_maxima=a.max_diff,tolerancia_absoluta=1e-12,
                importa_productor_o_sklearn=False,reutiliza_auditor_independiente_E1=True,
                H3_sin_centrado_rechazado=rejected,evaluacion_aporte_completa=False,
                codigo_auditor_sha256=sha(__file__),manifest_sha256=sha(run/'manifest.json'))
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--raiz',type=Path,default=Path(__file__).resolve().parents[1])
    p.add_argument('--entrega',type=Path,required=True);p.add_argument('--salida',type=Path,required=True)
    a=p.parse_args();print(json.dumps(auditar(a.raiz,a.entrega,a.salida),ensure_ascii=False,indent=2))
