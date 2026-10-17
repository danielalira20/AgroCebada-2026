"""Adaptador E2/E12/E2Q: reutiliza E1 y núcleo LOO v3 sin modificarlos."""
import copy
import warnings
import numpy as np
from scripts.t15_e2_entradas import E2, MODOS
from scripts.t15_e1_modelo import ModeloE1, VALUE, FLAG
from scripts.evaluacion_comun_modelo import validar_X, validar_y, divisiones_internas, clave_opcion
from scripts.evaluacion_comun_contrato import exigir
from scripts.t15_comparaciones_traza import huella, ErrorAjuste

VERSION='E2-adaptador-v1'
MAPA={'E2':'S','E12':'E1','E2Q':'Q','referencia':'referencia'}
S_POR_VENTANA={w:tuple(f's2_{c}_{w}' for c in ['ndvi_max','ndvi_integral','ndvi_dias_sobre_mitad','ndwi_en_maximo'])+
                  ('s2_ndvi_al_corte',) for w in ['abr_oct','jun_oct']}


def validar_columnas(columnas,modo):
    exigir(modo in MAPA, 'Procedimiento E2 desconocido')
    exigir((modo=='referencia')==(not columnas), 'Sólo referencia sin columnas')
    if columnas:
        exigir(tuple(columnas) in [s+E2 for s in S_POR_VENTANA.values()], 'Columnas E2 no registradas o calidad añadida')


def validar_datos(X,columnas,modo):
    validar_columnas(columnas,modo);validar_X(X,columnas)
    if columnas:
        v=X[list(E2)].to_numpy(float)
        exigir(np.isfinite(v).all(), 'E2 no admite imputación')
        exigir((np.abs(v[:,1:])<=1+1e-12).all() and
               (np.linalg.norm(v[:,1:],axis=1)<=1+1e-12).all(), 'Exposición fuera de dominio')


class ModeloE2:
    def __init__(self,columnas=(),lambda_reg=None,modo='E2'):
        self.columnas,self.lambda_reg,self.modo=tuple(columnas),lambda_reg,modo

    def fit(self,X,y):
        self.modelo_=None
        validar_datos(X,self.columnas,self.modo);validar_y(X,y)
        model=ModeloE1(self.columnas,self.lambda_reg,MAPA[self.modo]).fit(X,y)
        self.modelo_=model;self.parametros_=(self.columnas,self.lambda_reg,self.modo)
        return self

    def _comprobar(self,X):
        exigir(getattr(self,'modelo_',None) is not None,'Modelo E2 sin ajustar')
        exigir(self.parametros_==(self.columnas,self.lambda_reg,self.modo),'Reajustar parámetros E2')
        validar_datos(X,self.columnas,self.modo)

    def predict_with_details(self,X):
        self._comprobar(X)
        return self.modelo_.predict_with_details(X)

    def predict(self,X):
        return self.predict_with_details(X).prediccion.to_numpy()

    def estado(self):
        exigir(getattr(self,'modelo_',None) is not None,'Modelo E2 sin ajustar')
        exigir(self.parametros_==(self.columnas,self.lambda_reg,self.modo),'Reajustar parámetros E2')
        state=copy.deepcopy(self.modelo_.estado())
        state.update(adaptador=VERSION,procedimiento_E2=self.modo,
                     columnas_E2=list(E2) if self.columnas else [],E2_imputada=False,
                     diagnostico_sin_promocion=self.modo=='E2Q')
        return state


def ajustar(X,y,q,opcion,modo,elegibles):
    exigir(modo in MODOS,'Sólo E2/E12/E2Q')
    exigir(not set(X.index)&set(q.index),'IDs de entrenamiento/consulta solapados')
    exigir(len(elegibles)==len(q) and all(type(v) is bool for v in elegibles),'Máscara no booleana/alineada')
    mode=modo if opcion['columnas'] else 'referencia'
    t=dict(opcion=opcion['nombre'],columnas_base=list(opcion['columnas']),lambda_reg=opcion['lambda_reg'],
           ventana=opcion['ventana'],modo_E2=mode,procedimiento_solicitado=modo,adaptador=VERSION,
           ids_entrenamiento=sorted(X.index),ids_validacion=list(q.index),
           ids_elegibles=[i for i,b in zip(q.index,elegibles) if b],estado='iniciado')
    with warnings.catch_warnings(record=True) as notices:
        warnings.simplefilter('always')
        try:
            m=ModeloE2(opcion['columnas'],opcion['lambda_reg'],mode).fit(X,y)
            d=m.predict_with_details(q);s=m.estado()
            exigir(np.array_equal(d.fuente.to_numpy()=='municipio',elegibles),'Máscara municipal distinta')
            t.update(estado='correcto',columnas=s['columnas'],alpha=s['alpha'],
                     referencia_sola=mode=='referencia',estado_modelo_sha256=huella(s),
                     n_entrenamiento=len(X),n_validacion=len(q),n_elegibles=sum(elegibles),
                     preprocesamiento_E1=s['preprocesamiento_E1'],version=s['version'],
                     advertencias=[dict(categoria=w.category.__name__,mensaje=str(w.message)) for w in notices])
            exigir(not notices,'Advertencias durante ajuste: detener')
        except Exception as exc:
            t.update(estado='fallido',error_tipo=type(exc).__name__,error=str(exc))
            raise ErrorAjuste('Ajuste E2 detenido: '+str(exc),t) from exc
    return m,d,t


def validar_menu(opciones):
    exigir(len(opciones)==8 and len({o['nombre'] for o in opciones})==8,'Ocho opciones únicas requeridas')
    pairs=set()
    for o in opciones:
        exigir(o['ventana'] in S_POR_VENTANA and o['columnas']==list(S_POR_VENTANA[o['ventana']]+E2),
               'Columnas/ventana no coinciden')
        exigir(type(o['lambda_reg']) in [int,float] and o['lambda_reg'] in [.01,.1,1.,10.], 'Lambda no registrada')
        exigir(o['nombre']==f"{o['ventana']}__lambda_{o['lambda_reg']:g}", 'Nombre no canónico')
        pairs.add((o['ventana'],o['lambda_reg']))
    exigir(len(pairs)==8,'Menú incompleto o duplicado')


def seleccionar(X,y,opciones,modo,escenario,al_ajuste=None):
    exigir(modo in MODOS and escenario in ['A','B'],'Procedimiento/escenario no registrado')
    validar_menu(opciones);validar_y(X,y)
    alternatives=[dict(nombre='referencia_sola',columnas=[],lambda_reg=None,ventana='estatica'),*opciones]
    scores=[];count=0
    for option in alternatives:
        errors=[];all_errors=[]
        for n,split in enumerate(divisiones_internas(X,escenario)):
            tr,va=X.loc[list(split.entrenamiento)],X.loc[list(split.validacion)]
            try:
                _,d,t=ajustar(tr,y.loc[tr.index],va,option,modo,split.elegibles)
            except ErrorAjuste as exc:
                exc.traza.update(division_interna=n,escenario=escenario)
                if al_ajuste:al_ajuste(copy.deepcopy(exc.traza))
                raise
            err=np.abs(d.prediccion.to_numpy()-y.loc[va.index].to_numpy())
            errors.extend(err[np.asarray(split.elegibles)]);all_errors.extend(err);count+=1
            t.update(division_interna=n,escenario=escenario,MAE=float(err[np.asarray(split.elegibles)].mean()),
                     MAE_todas=float(err.mean()))
            if al_ajuste:al_ajuste(copy.deepcopy(t))
        exigir(errors and np.isfinite(errors).all(),'Opción no evaluable; no saltar')
        scores.append(dict(nombre=option['nombre'],ventana=option['ventana'],lambda_reg=option['lambda_reg'],
                           referencia_sola=not option['columnas'],MAE=float(np.mean(errors)),
                           MAE_todas=float(np.mean(all_errors)),n_elegibles=len(errors),
                           n_validacion=len(all_errors),n_ajustes=4,version='comun-centrado-loo-v3'))
    winner=min(scores,key=clave_opcion)
    return dict(elegida=copy.deepcopy(next(o for o in alternatives if o['nombre']==winner['nombre'])),
                puntuaciones=scores,n_ajustes=count,adaptador=VERSION)
