"""Componentes comunes verificables. No hay ejecutor de evaluación completa ni ajuste final59."""
from dataclasses import dataclass
import math
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.model_selection import StratifiedKFold,GroupKFold
from sklearn.preprocessing import StandardScaler
from scripts.evaluacion_comun_contrato import exigir

META=['municipio','cultivo_origen']
LAMBDA=(.01,.1,1.,10.)
NULLABLE='pendiente_media_t10_grados'


def validar_X(X, columnas):
    exigir(isinstance(X,pd.DataFrame) and X.index.is_unique and len(X)>0,'X requiere IDs únicos y filas')
    exigir(all(isinstance(i,str) and i and i.strip()==i for i in X.index),'IDs vacíos o inválidos')
    exigir(not set(columnas)&{'rendimiento_t_ha','real','prediccion','id_parcela','campania','estado','conjunto_origen','municipio','cultivo_origen','escalon_etiqueta_municipio','vecina_etiquetada_menos_20m','numero_vecinas_etiquetadas_menos_20m','alerta_contorno_t03_bis','contorno_categoria'},'Rol prohibido como predictor')
    exigir(set(META+list(columnas))<=set(X),'Faltan columnas declaradas')
    exigir(X[META].notna().all().all() and X.municipio.map(lambda x:isinstance(x,str) and bool(x.strip())).all(),'Metadatos inválidos')
    exigir(X.cultivo_origen.isin(['Cebada','CEBADA']).all(),'Grupo desconocido')
    for c in columnas:
        values=X[c].to_numpy(dtype=float)
        exigir(not np.isinf(values).any(),'Predictor infinito')
        exigir(c==NULLABLE or np.isfinite(values).all(),'Faltante no permitido')
        if c=='area_ha_origen':exigir((values>0).all(),'Log requiere área positiva')


def validar_y(X,y):
    exigir(isinstance(y,pd.Series) and y.index.equals(X.index),'y debe estar alineada por ID')
    exigir(np.isfinite(y.to_numpy(float)).all(),'Objetivo no finito')


def medias(X,y):
    # Orden estable antes de sumar, independiente de la lectura o de la arquitectura.
    X=X.sort_index();y=y.loc[X.index]
    m={k:math.fsum(y.loc[g.index])/len(g) for k,g in X.groupby('municipio')}
    g={k:math.fsum(y.loc[v.index])/len(v) for k,v in X.groupby('cultivo_origen')}
    return m,g,math.fsum(y)/len(y)


def aplicar_referencia(X,m,g,global_):
    pred=[];fuente=[]
    for _,r in X.iterrows():
        if r.municipio in m:pred.append(m[r.municipio]);fuente.append('municipio')
        elif r.cultivo_origen in g:pred.append(g[r.cultivo_origen]);fuente.append('grupo')
        else:pred.append(global_);fuente.append('global')
    return np.asarray(pred),np.asarray(fuente)


def residuos_loo(X,y):
    """Cada fila usa la referencia del resto; no comparte su propia etiqueta."""
    validar_X(X,[]);validar_y(X,y);exigir(len(X)>1,'LOO requiere más de una fila')
    # Preagrupar IDs una vez evita repetir groupby por fila y mejora reproducción en ARM/amd64.
    ordered=X.sort_index();values={pid:float(y.loc[pid]) for pid in ordered.index}
    mun={k:tuple(g.index) for k,g in ordered.groupby('municipio')}
    grp={k:tuple(g.index) for k,g in ordered.groupby('cultivo_origen')}
    out=[]
    for pid,row in X.iterrows():
        ids=[i for i in mun[row.municipio] if i!=pid]
        if not ids:ids=[i for i in grp[row.cultivo_origen] if i!=pid]
        if not ids:ids=[i for i in ordered.index if i!=pid]
        ref=math.fsum(values[i] for i in ids)/len(ids)
        out.append(values[pid]-ref)
    return np.asarray(out)


class CorreccionComun:
    """Referencia + Ridge sin intercepto; aprende imputación y escala sólo con fit."""
    def __init__(self,columnas=(),lambda_reg=None):
        self.columnas=tuple(columnas);self.lambda_reg=lambda_reg
        exigir(not isinstance(lambda_reg,bool),'λ booleano no permitido')
        exigir(len(self.columnas)==len(set(self.columnas)),'Columnas duplicadas')
        exigir((not self.columnas and lambda_reg is None) or (bool(self.columnas) and lambda_reg in LAMBDA),'Referencia sola o λ común obligatorio')

    def _valores(self,X,ajustar=False):
        v=X[list(self.columnas)].to_numpy(float).copy()
        if 'area_ha_origen' in self.columnas:
            j=self.columnas.index('area_ha_origen');v[:,j]=np.log(v[:,j])
        extra=[]
        for j,c in enumerate(self.columnas):
            miss=np.isnan(v[:,j])
            if c==NULLABLE:
                extra.append(miss.astype(float))
                if ajustar:
                    exigir((~miss).any(),'No se puede imputar pendiente totalmente ausente en entrenamiento')
                    self.mediana_pendiente_=float(np.median(v[~miss,j]))
                v[miss,j]=self.mediana_pendiente_
        if extra:v=np.column_stack([v,*extra])
        return v

    def fit(self,X,y):
        validar_X(X,self.columnas);validar_y(X,y)
        X=X.sort_index();y=y.loc[X.index]
        self.ids_entrenamiento_=tuple(X.index);self.mun_,self.grupo_,self.global_=medias(X,y)
        self.n_=len(X);self.alpha_=None;self.ridge_=None
        self.nombres_=list(self.columnas)
        if self.columnas:
            self.residuos_=residuos_loo(X,y)
            a=self._valores(X,True)
            if NULLABLE in self.columnas:self.nombres_.append(NULLABLE+'__faltante')
            self.escalador_=StandardScaler().fit(a)
            self.alpha_=self.n_*float(self.lambda_reg)
            self.ridge_=Ridge(alpha=self.alpha_,fit_intercept=False,solver='svd').fit(self.escalador_.transform(a),self.residuos_)
        self.ajustado_=True
        return self

    def predict_con_fuente(self,X):
        exigir(getattr(self,'ajustado_',False),'Modelo sin ajustar')
        validar_X(X,self.columnas)
        p,s=aplicar_referencia(X,self.mun_,self.grupo_,self.global_)
        if self.ridge_ is not None:p=p+self.ridge_.predict(self.escalador_.transform(self._valores(X)))
        exigir(np.isfinite(p).all(),'Predicción no finita')
        return p,s

    def predict(self,X):return self.predict_con_fuente(X)[0]

    def estado(self):
        exigir(getattr(self,'ajustado_',False),'Modelo sin ajustar')
        e={'familia':'referencia_mas_Ridge_residuo_LOO','ids_entrenamiento':list(self.ids_entrenamiento_),'n':self.n_,'municipio':self.mun_,'grupo':self.grupo_,'global':self.global_,'columnas':list(self.columnas),'lambda_reg':self.lambda_reg,'alpha':self.alpha_,'fit_intercept':False,'intercepto':0.0}
        if self.ridge_ is not None:e.update(nombres_transformados=self.nombres_,media=self.escalador_.mean_.tolist(),escala=self.escalador_.scale_.tolist(),coeficientes=self.ridge_.coef_.tolist(),mediana_pendiente=getattr(self,'mediana_pendiente_',None))
        return e


@dataclass(frozen=True)
class Division:
    entrenamiento:tuple
    validacion:tuple
    elegibles:tuple


def divisiones_internas(X,escenario):
    validar_X(X,[]);X=X.sort_index()
    exigir(escenario in ['A','B','C'],'Escenario desconocido')
    if escenario=='A':
        counts=X.municipio.value_counts();strata=X.municipio.where(X.municipio.map(counts)>=4,'otros')
        exigir(strata.value_counts().min()>=4,'Estrato A insuficiente para cuatro internas')
        splits=StratifiedKFold(4,shuffle=True,random_state=0).split(X,strata);group=None
    else:
        col='celda_chirps' if escenario=='B' else 'municipio'
        exigir(col in X and X[col].map(lambda v:isinstance(v,str) and bool(v.strip())).all(),'Grupo espacial/municipal ausente')
        group=X[col];exigir(group.nunique()>=4,'Cuatro grupos requeridos')
        splits=GroupKFold(4,shuffle=False).split(X,groups=group)
    out=[];seen=[]
    for ia,ib in splits:
        a,b=X.iloc[ia],X.iloc[ib]
        if group is not None:exigir(not set(group.iloc[ia])&set(group.iloc[ib]),'Grupo en entrenamiento y validación')
        eligible=np.ones(len(b),bool) if escenario=='C' else b.municipio.isin(a.municipio).to_numpy()
        exigir(eligible.any(),'División interna sin casos elegibles')
        seen.extend(b.index);out.append(Division(tuple(a.index),tuple(b.index),tuple(bool(v) for v in eligible)))
    exigir(len(seen)==len(set(seen))==len(X) and set(seen)==set(X.index),'Validación interna incompleta')
    return out


def clave_opcion(row):
    return (round(row['MAE'],6),0 if row['referencia_sola'] else 1,-(row.get('lambda_reg') or 0),0 if row['ventana']=='jun_oct' else 1,row['nombre'])


def seleccionar(X,y,opciones,escenario='A'):
    """Opciones registradas: referencia sola + cuatro λ por ventana; no usa y externa ni59."""
    validar_X(X,[]);validar_y(X,y)
    exigir(1<=len(opciones)<=8,'Máximo ocho opciones con variables')
    ids={o['nombre'] for o in opciones};exigir(len(ids)==len(opciones) and 'referencia_sola' not in ids,'Nombre de opción duplicado/reservado')
    div=divisiones_internas(X,escenario);scores=[]
    alternatives=[{'nombre':'referencia_sola','columnas':[],'lambda_reg':None,'ventana':'estatica'},*opciones]
    # En cada división se conserva el mismo soporte para todas las alternativas.
    for o in alternatives:
        errors=[];all_errors=[]
        for split in div:
            tr=X.loc[list(split.entrenamiento)];va=X.loc[list(split.validacion)]
            model=CorreccionComun(o['columnas'],o['lambda_reg']).fit(tr,y.loc[tr.index])
            err=np.abs(model.predict(va)-y.loc[va.index].to_numpy())
            errors.extend(err[np.asarray(split.elegibles)]);all_errors.extend(err)
        exigir(errors and np.isfinite(errors).all(),'Opción no evaluable; no saltarla')
        scores.append({'nombre':o['nombre'],'ventana':o['ventana'],'lambda_reg':o['lambda_reg'],'referencia_sola':not o['columnas'],'MAE':float(np.mean(errors)),'MAE_todas':float(np.mean(all_errors)),'n_elegibles':len(errors),'n_validacion':len(all_errors),'n_ajustes':4})
    winner=min(scores,key=clave_opcion)
    selected=next(o for o in alternatives if o['nombre']==winner['nombre'])
    return {'elegida':selected.copy(),'puntuaciones':scores,'n_ajustes':len(alternatives)*4}


def preparar_contexto(entradas,escenario,repeticion,particion):
    """Separa el contexto real congelado; las 59 nunca forman parte de y ni de internas."""
    exigir(escenario in ['A','B'] and repeticion in range(1,6) and particion in range(5),'Contexto fuera de A/B T03')
    field='particion_principal' if escenario=='A' else 'particion_espacial'
    records=[v for v in entradas['particiones'] if int(v['repeticion'])==repeticion]
    ids_train=sorted(v['ID_POLIGONO'] for v in records if int(v[field])!=particion)
    ids_test=sorted(v['ID_POLIGONO'] for v in records if int(v[field])==particion)
    exigir(not set(ids_train)&set(ids_test) and set(ids_train)|set(ids_test)==entradas['conocidos'],'Contexto no disjunto/completo')
    table=pd.DataFrame(entradas['tabla'].values()).set_index('id_parcela')
    y=pd.to_numeric(table.loc[ids_train,'rendimiento_t_ha'])
    table=table.drop(columns=['rendimiento_t_ha'])
    numeric=[col for col in entradas['roles']['columnas_por_funcion']['predictor_candidato'] if col!='municipio']+entradas['roles']['columnas_por_funcion']['calidad']+['area_ha_origen']
    for col in numeric:table[col]=pd.to_numeric(table[col],errors='raise')
    table['celda_chirps']=table.index.map({v['ID_POLIGONO']:v['celda_chirps'] for v in records})
    return table.loc[ids_train].copy(),y,table.loc[ids_test].copy()


def seleccionar_registrado(entradas,experimento,candidato,escenario,repeticion,particion):
    """Entrada pública para T15: registro validado y ajuste sólo dentro del contexto externo."""
    from scripts.evaluacion_comun_contrato import validar_experimento
    validar_experimento(experimento,entradas)
    procs=[p for p in experimento['procedimientos'] if p['candidato']==candidato]
    exigir(len(procs)==1,'Candidato no registrado')
    options=[dict(o,nombre=f"{o['ventana']}__lambda_{o['lambda_reg']:g}") for o in procs[0]['opciones']]
    tr,y,te=preparar_contexto(entradas,escenario,repeticion,particion)
    choice=seleccionar(tr,y,options,escenario)
    selected=choice['elegida'];model=CorreccionComun(selected['columnas'],selected['lambda_reg']).fit(tr,y)
    prediction,source=model.predict_con_fuente(te)
    return {'seleccion':choice,'modelo':model,'ids_evaluacion':tuple(te.index),'prediccion':prediction,'fuente':source,'ids_entrenamiento':tuple(tr.index)}
