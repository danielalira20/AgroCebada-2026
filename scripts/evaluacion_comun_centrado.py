"""Procedimiento común centrado v2, para revisión; no ejecuta T15 completo.

Mantiene datos, referencia, búsqueda y presupuesto v1. Cambia la matriz Ridge
a desviaciones municipales de entrenamiento, incluidas columnas transformadas.
"""
import argparse
import copy
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, RegressorMixin
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

from scripts import evaluacion_comun_contrato as contrato_v1
from scripts.evaluacion_comun_contrato import exigir, sha, RAIZ
from scripts.evaluacion_comun_modelo import (CorreccionComun, LAMBDA, NULLABLE,
    validar_X, validar_y, medias, aplicar_referencia, residuos_loo,
    divisiones_internas, clave_opcion, preparar_contexto)

VERSION='comun-centrado-v2'
DISENO='registro/evaluacion_comun/procedimiento_centrado_v2.json'
DISENO_SHA='fb4ba40497b14cc9c9c077a3e993e8d24ca559a2d1cd6ebbce168e12aebd8040'


def cargar_entradas(raiz=RAIZ):
    raiz=Path(raiz)
    exigir(sha(raiz/DISENO)==DISENO_SHA,'Diseño centrado modificado: versionar y revisar')
    cfg=json.loads((raiz/DISENO).read_text())
    exigir(cfg['schema']=='agrocebada_comun_centrado_v2' and cfg['version']==VERSION,'Diseño incompatible')
    e=contrato_v1.cargar_entradas(raiz) # Valida fuentes/roles/particiones, no acredita un modelo.
    exigir(cfg['fuentes_sha256']==e['config']['fuentes_sha256'],'Fuentes v2 distintas del antecedente')
    return {**e,'config':cfg,'sha_procedimiento':DISENO_SHA}


def validar_experimento(experimento,entradas):
    exigir(entradas['config']['version']==VERSION and entradas.get('sha_procedimiento')==DISENO_SHA,
           'Entradas no identificadas para la versión centrada')
    exigir(experimento.get('schema')=='experimento_comun_centrado_v2','Experimento de otra versión')
    exigir(experimento.get('sha_procedimiento')==DISENO_SHA,'Experimento usa otro procedimiento')
    exigir(experimento.get('estado')=='registrado_antes_de_ejecutar','Propuesta pendiente: no ejecutar T15')
    exigir(bool(experimento.get('id')) and bool(experimento.get('responsable')) and bool(experimento.get('hipotesis')),
           'Falta identidad/hipótesis')
    # Sólo se comparte la comprobación estructural de roles, opciones y presupuesto.
    # La identidad v2 anterior nunca se sustituye por una acreditación v1.
    counts=contrato_v1.validar_opciones_y_presupuesto(experimento,entradas)
    return {**counts,'version':VERSION,'sha_procedimiento':DISENO_SHA}


class CorreccionComunCentrada(RegressorMixin,CorreccionComun,BaseEstimator):
    """Referencia T08 + Ridge LOO en Z-centro municipal del entrenamiento."""

    def _limpiar(self):
        for name in list(vars(self)):
            if name.endswith('_'):delattr(self,name)

    def fit(self,X,y):
        self._limpiar()
        try:
            # Validar también cuando los parámetros se modificaron tras construir.
            exigir(len(self.columnas)==len(set(self.columnas)),'Columnas duplicadas')
            exigir(not isinstance(self.lambda_reg,bool) and
                ((not self.columnas and self.lambda_reg is None) or
                 (bool(self.columnas) and self.lambda_reg in LAMBDA)),'Parámetros fuera del procedimiento')
            validar_X(X,self.columnas);validar_y(X,y)
            exigir(pd.api.types.is_numeric_dtype(y) and not pd.api.types.is_bool_dtype(y),'Objetivo numérico requerido')
            X=X.sort_index().copy();y=y.loc[X.index].copy()
            self.ids_entrenamiento_=tuple(X.index)
            self.mun_,self.grupo_,self.global_=medias(X,y)
            self.n_=len(X);self.alpha_=None;self.ridge_=None
            self.nombres_=list(self.columnas)
            if self.columnas:
                self.residuos_=residuos_loo(X,y)
                a=self._valores(X,True) # Log, mediana e indicador: sólo entrenamiento.
                if NULLABLE in self.columnas:self.nombres_.append(NULLABLE+'__faltante')
                self.escalador_=StandardScaler().fit(a)
                z=self.escalador_.transform(a)
                frame=pd.DataFrame(z,index=X.index,columns=self.nombres_)
                self.centros_mun_=frame.groupby(X.municipio).mean().copy()
                self.centros_grupo_=frame.groupby(X.cultivo_origen).mean().copy()
                self.centro_global_=frame.mean().to_numpy().copy()
                self.n_mun_=X.municipio.value_counts().sort_index().copy()
                self.n_grupo_=X.cultivo_origen.value_counts().sort_index().copy()
                d=z-self.centros_mun_.loc[X.municipio].to_numpy()
                self.alpha_=self.n_*float(self.lambda_reg)
                self.ridge_=Ridge(alpha=self.alpha_,fit_intercept=False,solver='svd').fit(d,self.residuos_)
                exigir(np.isfinite(self.ridge_.coef_).all(),'Coeficientes no finitos')
            self.parametros_fit_=(tuple(self.columnas),self.lambda_reg)
            self.ajustado_=True
        except Exception:
            self._limpiar()
            raise
        return self

    def _comprobar(self):
        exigir(getattr(self,'ajustado_',False),'Modelo sin ajustar')
        exigir(self.parametros_fit_==(tuple(self.columnas),self.lambda_reg),
               'Reajustar después de cambiar columnas o lambda')

    def _centros(self,X):
        centers=np.tile(self.centro_global_,(len(X),1));sources=[]
        for i,row in enumerate(X.itertuples()):
            if row.municipio in self.centros_mun_.index:
                centers[i]=self.centros_mun_.loc[row.municipio].to_numpy();sources.append('municipio')
            elif row.cultivo_origen in self.centros_grupo_.index:
                centers[i]=self.centros_grupo_.loc[row.cultivo_origen].to_numpy();sources.append('grupo')
            else:sources.append('global')
        return centers,np.asarray(sources)

    def predict_with_details(self,X):
        self._comprobar();validar_X(X,self.columnas)
        base,source=aplicar_referencia(X,self.mun_,self.grupo_,self.global_)
        correction=np.zeros(len(X));source_center=np.full(len(X),'no_aplica',dtype=object)
        if self.ridge_ is not None:
            z=self.escalador_.transform(self._valores(X))
            center,source_center=self._centros(X)
            exigir(np.array_equal(source_center,source),'Centro y referencia con respaldos diferentes')
            correction=self.ridge_.predict(z-center)
        prediction=base+correction
        exigir(np.isfinite(prediction).all(),'Predicción no finita')
        return pd.DataFrame(dict(prediccion=prediction,referencia=base,correccion=correction,
                                 fuente=source,fuente_centrado=source_center),index=X.index)

    def predict_con_fuente(self,X):
        d=self.predict_with_details(X);return d.prediccion.to_numpy(),d.fuente.to_numpy()

    def predict(self,X):return self.predict_with_details(X).prediccion.to_numpy()

    def estado(self):
        self._comprobar()
        e=copy.deepcopy(super().estado())
        e.update(version=VERSION,familia='referencia_mas_Ridge_residuo_LOO_centrado_municipal',
                 sha_procedimiento=DISENO_SHA,reescalar_intramunicipal=False,
                 politica_centro='municipio_grupo_global_del_entrenamiento')
        if self.ridge_ is not None:
            def vectors(frame):return {str(k):v.tolist() for k,v in zip(frame.index,frame.to_numpy())}
            e.update(centros_Z_municipio=vectors(self.centros_mun_),centros_Z_grupo=vectors(self.centros_grupo_),
                     centro_Z_global=self.centro_global_.tolist(),
                     n_municipio={str(k):int(v) for k,v in self.n_mun_.items()},
                     n_grupo={str(k):int(v) for k,v in self.n_grupo_.items()})
        return e


def seleccionar(X,y,opciones,escenario='A'):
    """Misma búsqueda v1; todos los fits utilizan el centrado v2, también internos."""
    validar_X(X,[]);validar_y(X,y)
    exigir(1<=len(opciones)<=8,'Máximo ocho opciones con variables')
    names={o['nombre'] for o in opciones}
    exigir(len(names)==len(opciones) and 'referencia_sola' not in names,'Nombre duplicado/reservado')
    divisions=divisiones_internas(X,escenario);scores=[]
    alternatives=[dict(nombre='referencia_sola',columnas=[],lambda_reg=None,ventana='estatica'),*opciones]
    for option in alternatives:
        errors,all_errors=[],[]
        for split in divisions:
            tr,va=X.loc[list(split.entrenamiento)],X.loc[list(split.validacion)]
            model=CorreccionComunCentrada(option['columnas'],option['lambda_reg']).fit(tr,y.loc[tr.index])
            e=abs(model.predict(va)-y.loc[va.index].to_numpy())
            errors.extend(e[np.asarray(split.elegibles)]);all_errors.extend(e)
        exigir(errors and np.isfinite(errors).all(),'Opción no evaluable; no saltarla')
        scores.append(dict(nombre=option['nombre'],ventana=option['ventana'],lambda_reg=option['lambda_reg'],
                           referencia_sola=not option['columnas'],MAE=float(np.mean(errors)),MAE_todas=float(np.mean(all_errors)),
                           n_elegibles=len(errors),n_validacion=len(all_errors),n_ajustes=4,version=VERSION))
    winner=min(scores,key=clave_opcion)
    selected=next(o for o in alternatives if o['nombre']==winner['nombre'])
    return dict(elegida=selected.copy(),puntuaciones=scores,n_ajustes=len(alternatives)*4,version=VERSION)


def seleccionar_registrado(entradas,experimento,candidato,escenario,repeticion,particion):
    validar_experimento(experimento,entradas)
    procs=[p for p in experimento['procedimientos'] if p['candidato']==candidato]
    exigir(len(procs)==1,'Candidato no registrado')
    options=[dict(o,nombre=f"{o['ventana']}__lambda_{o['lambda_reg']:g}") for o in procs[0]['opciones']]
    tr,y,te=preparar_contexto(entradas,escenario,repeticion,particion)
    choice=seleccionar(tr,y,options,escenario)
    selected=choice['elegida'];model=CorreccionComunCentrada(selected['columnas'],selected['lambda_reg']).fit(tr,y)
    prediction,source=model.predict_con_fuente(te)
    return dict(seleccion=choice,modelo=model,ids_evaluacion=tuple(te.index),prediccion=prediction,fuente=source,
                ids_entrenamiento=tuple(tr.index),version=VERSION,sha_procedimiento=DISENO_SHA)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--raiz',type=Path,default=RAIZ);ap.add_argument('--experimento',type=Path)
    args=ap.parse_args();e=cargar_entradas(args.raiz)
    result=dict(version=VERSION,sha_procedimiento=DISENO_SHA,etiquetadas=len(e['conocidos']),
                reservadas=len(e['reservados']),modelos_ajustados=0,evaluacion_T15_completa=False)
    if args.experimento:result['experimento']=validar_experimento(json.loads(args.experimento.read_text()),e)
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
