"""E1/Q: preparación ajustada por fit en Pipeline; núcleo v3 inmutable."""
import copy
import warnings

import numpy as np
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.pipeline import Pipeline

from scripts import evaluacion_comun_centrado_loo as v3
from scripts.evaluacion_comun_contrato import exigir
from scripts.evaluacion_comun_modelo import validar_X, validar_y, divisiones_internas, clave_opcion
from scripts.t15_e1_contrato import VALUE, FLAG
from scripts.t15_comparaciones_traza import huella, ErrorAjuste

EXTENSION = 'E1-Q-preparacion-v1'


class PreparadorE1(TransformerMixin, BaseEstimator):
    """No conoce y; cada Pipeline aprende únicamente de sus filas de fit."""

    def __init__(self, columnas=(), modo='E1'):
        self.columnas = columnas
        self.modo = modo

    def _validar(self, X):
        exigir(self.modo in ['S', 'Q', 'E1', 'referencia'], 'Modo E1 desconocido')
        exigir(len(self.columnas) == len(set(self.columnas)) and
               not {VALUE, FLAG} & set(self.columnas), 'Columnas base duplicadas o de extensión')
        validar_X(X, self.columnas)
        exigir((self.modo == 'referencia') == (not self.columnas), 'Base vacía sólo para referencia')
        if self.modo in ['Q', 'E1']:
            exigir({VALUE, FLAG} <= set(X), 'Falta tabla adicional E1')
            a, b = X[VALUE].to_numpy(float), X[FLAG].to_numpy(float)
            exigir(not np.isinf(a).any() and np.isin(b, [0., 1.]).all(), 'E1/indicador inválidos')
            exigir(np.array_equal(np.isnan(a), b == 1), 'Valor y ausencia contradictorios')
            exigir(np.all(np.abs(a[np.isfinite(a)]) <= 2), 'Contraste fuera de [-2,2]')

    def fit(self, X, y=None):
        for k in list(vars(self)):
            if k.endswith('_'):
                delattr(self, k)
        self._validar(X)
        self.ids_entrenamiento_ = tuple(sorted(X.index))
        self.parametros_ = (tuple(self.columnas), self.modo)
        self.ids_admisibles_ = tuple(sorted(X.index[X[FLAG].to_numpy(float) == 0])) if self.modo in ['Q', 'E1'] else ()
        self.activo_ = bool(self.ids_admisibles_)
        self.mediana_ = (float(np.median(X.loc[list(self.ids_admisibles_), VALUE].to_numpy(float)))
                         if self.modo == 'E1' and self.activo_ else None)
        self.columnas_salida_ = list(self.columnas)
        if self.modo == 'E1':
            self.columnas_salida_.append(VALUE)
        if self.modo in ['Q', 'E1']:
            self.columnas_salida_.append(FLAG)
        self.ajustado_ = True
        return self

    def transform(self, X):
        exigir(getattr(self, 'ajustado_', False), 'Preparador sin ajustar')
        exigir(self.parametros_ == (tuple(self.columnas), self.modo), 'Reajustar parámetros del preparador')
        self._validar(X)
        columns = ['municipio', 'cultivo_origen', *self.columnas]
        if 'celda_chirps' in X:
            columns.append('celda_chirps')
        out = X[columns].copy()
        if self.modo in ['Q', 'E1']:
            if self.modo == 'E1':
                # El apagado es un estado del fit: no reactivar con la validación.
                out[VALUE] = X[VALUE].fillna(self.mediana_).astype(float) if self.activo_ else 0.
            out[FLAG] = X[FLAG].astype(float) if self.activo_ else 1.
        return out

    def estado(self):
        exigir(getattr(self, 'ajustado_', False), 'Preparador sin ajustar')
        return dict(version=EXTENSION, modo=self.modo, columnas_base=list(self.columnas),
                    columnas_salida=self.columnas_salida_.copy(),
                    ids_entrenamiento=list(self.ids_entrenamiento_),
                    ids_admisibles=list(self.ids_admisibles_), n_admisibles=len(self.ids_admisibles_),
                    extension_activa=self.activo_, mediana_E1=self.mediana_,
                    sin_admisibles='ambas_columnas_desactivadas_en_fit_y_predict',
                    imputacion_es_observacion=False)


class ModeloE1:
    def __init__(self, columnas=(), lambda_reg=None, modo='E1'):
        self.columnas, self.lambda_reg, self.modo = tuple(columnas), lambda_reg, modo

    def fit(self, X, y):
        self.pipeline_ = None
        validar_y(X, y)
        p = PreparadorE1(self.columnas, self.modo)
        columns = list(self.columnas)
        if self.modo == 'E1': columns.append(VALUE)
        if self.modo in ['Q', 'E1']: columns.append(FLAG)
        pipeline = Pipeline([('E1', p), ('v3', v3.CorreccionComunCentradaLOO(columns, self.lambda_reg))])
        pipeline.fit(X, y)
        self.pipeline_ = pipeline
        self.parametros_ = (self.columnas, self.lambda_reg, self.modo)
        return self

    def _comprobar(self):
        exigir(getattr(self, 'pipeline_', None) is not None, 'Modelo E1 sin ajustar')
        exigir(self.parametros_ == (self.columnas, self.lambda_reg, self.modo), 'Reajustar parámetros E1')

    def predict_with_details(self, X):
        self._comprobar()
        prepared = self.pipeline_['E1'].transform(X)
        return self.pipeline_['v3'].predict_with_details(prepared)

    def predict(self, X):
        self._comprobar()
        return self.pipeline_.predict(X)

    def estado(self):
        self._comprobar()
        e = copy.deepcopy(self.pipeline_['v3'].estado())
        e['extension'] = EXTENSION
        e['preprocesamiento_E1'] = self.pipeline_['E1'].estado()
        return e


def ajustar(X, y, validacion, opcion, modo, elegibles):
    exigir(not set(X.index) & set(validacion.index), 'IDs solapados en ajuste E1')
    exigir(len(elegibles) == len(validacion) and all(type(v) is bool for v in elegibles), 'Máscara inválida')
    mode = modo if opcion['columnas'] else 'referencia'
    t = dict(opcion=opcion['nombre'], estado='iniciado', ids_entrenamiento=sorted(X.index),
             ids_validacion=list(validacion.index), ids_elegibles=[i for i, b in zip(validacion.index, elegibles) if b],
             n_entrenamiento=len(X), n_validacion=len(validacion), n_elegibles=sum(elegibles),
             lambda_reg=opcion['lambda_reg'], columnas_base=list(opcion['columnas']),
             ventana=opcion['ventana'], version=v3.VERSION, extension=EXTENSION, modo=mode)
    with warnings.catch_warnings(record=True) as notices:
        warnings.simplefilter('always')
        try:
            model = ModeloE1(opcion['columnas'], opcion['lambda_reg'], mode).fit(X, y)
            details = model.predict_with_details(validacion)
            exigir(np.array_equal(details.fuente.to_numpy() == 'municipio', elegibles), 'Máscara municipal distinta')
            state = model.estado()
            counts = X.municipio.value_counts()
            pools = state.get('pools_sin_fila', {})
            t.update(estado='correcto', alpha=state['alpha'], referencia_sola=mode == 'referencia',
                     columnas=state['columnas'], n_grupos_municipio=int(counts.size),
                     n_grupos_celda=int(X.celda_chirps.nunique()),
                     n_singleton_entrenamiento=int((counts == 1).sum()),
                     n_validacion_referencia_una_etiqueta=int(sum(counts.get(m, 0) == 1 for m in validacion.municipio)),
                     n_validacion_sin_municipio=int(sum(counts.get(m, 0) == 0 for m in validacion.municipio)),
                     fuentes_referencia={k:int((details.fuente == k).sum()) for k in ['municipio', 'grupo', 'global']},
                     fuentes_centro_LOO={k:sum(p['fuente'] == k for p in pools.values()) for k in ['municipio', 'grupo', 'global']},
                     preprocesamiento_E1=state['preprocesamiento_E1'], estado_modelo_sha256=huella(state),
                     media_abs_correccion=float(details.correccion.abs().mean()),
                     max_abs_correccion=float(details.correccion.abs().max()),
                     advertencias=[dict(categoria=w.category.__name__, mensaje=str(w.message)) for w in notices])
            exigir(not notices, 'Ajuste con advertencias: detener y revisar')
        except Exception as exc:
            t.update(estado='fallido', error_tipo=type(exc).__name__, error=str(exc))
            raise ErrorAjuste('Ajuste E1 detenido: '+str(exc), t) from exc
    return model, details, t


def seleccionar(X, y, opciones, modo, escenario, al_ajuste=None):
    validar_X(X, []); validar_y(X, y)
    exigir(modo in ['Q', 'E1'] and len(opciones) == 8, 'Menú E1/Q requiere ocho opciones')
    exigir(len({o['nombre'] for o in opciones}) == 8 and
           'referencia_sola' not in {o['nombre'] for o in opciones}, 'Opciones duplicadas/reservadas')
    alternatives = [dict(nombre='referencia_sola', columnas=[], lambda_reg=None, ventana='estatica'), *opciones]
    scores, traces = [], []
    for o in alternatives:
        errors, all_errors = [], []
        for n, split in enumerate(divisiones_internas(X, escenario)):
            tr, va = X.loc[list(split.entrenamiento)], X.loc[list(split.validacion)]
            try:
                _, d, t = ajustar(tr, y.loc[tr.index], va, o, modo, split.elegibles)
            except ErrorAjuste as exc:
                exc.traza.update(escenario=escenario, division_interna=n)
                if al_ajuste is not None: al_ajuste(copy.deepcopy(exc.traza))
                raise
            e = np.abs(d.prediccion.to_numpy() - y.loc[va.index].to_numpy())
            errors.extend(e[np.asarray(split.elegibles)]); all_errors.extend(e)
            t.update(escenario=escenario, division_interna=n, MAE=float(e[np.asarray(split.elegibles)].mean()),
                     MAE_todas=float(e.mean()))
            traces.append(t)
            if al_ajuste is not None: al_ajuste(copy.deepcopy(t))
        exigir(errors and np.isfinite(errors).all(), 'Opción no evaluable: no omitir')
        scores.append(dict(nombre=o['nombre'], ventana=o['ventana'], lambda_reg=o['lambda_reg'],
                           referencia_sola=not o['columnas'], MAE=float(np.mean(errors)),
                           MAE_todas=float(np.mean(all_errors)), n_elegibles=len(errors),
                           n_validacion=len(all_errors), n_ajustes=4, version=v3.VERSION))
    winner = min(scores, key=clave_opcion)
    return dict(elegida=copy.deepcopy(next(o for o in alternatives if o['nombre'] == winner['nombre'])),
                puntuaciones=scores, n_ajustes=len(traces), version=v3.VERSION)
