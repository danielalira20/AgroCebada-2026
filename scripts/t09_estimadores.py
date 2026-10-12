"""Estimadores T09. Fit aprende sólo X/y recibidos; no lee datos ni ejecuta evaluaciones."""
import numbers

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, RegressorMixin
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.utils.validation import check_is_fitted

OBJETIVO = 'rendimiento_t_ha'
VENTANAS = ('abr_oct', 'jun_oct')
VARIABLES = ('prec_acumulada_mm', 'tmin_media_c', 'tmax_media_c')
CLIMA = tuple(f'{v}_{w}' for w in VENTANAS for v in VARIABLES)
METADATOS = ('id_parcela', 'municipio', 'cultivo_origen')


def columnas_clima(ventana):
    if ventana not in VENTANAS:
        raise ValueError('Ventana fuera del diseño T09')
    return [f'{v}_{ventana}' for v in VARIABLES]


def validar_X(X, columnas=(), territorio=False):
    if not isinstance(X, pd.DataFrame) or X.empty or not X.columns.is_unique:
        raise ValueError('X debe ser una tabla no vacía con columnas únicas')
    if {OBJETIVO, 'real', 'prediccion'} & set(X.columns):
        raise ValueError('Separar etiquetas/predicciones de X antes de ajustar')
    requeridas = ['id_parcela', *columnas]
    if territorio:
        requeridas += ['municipio', 'cultivo_origen']
    if not set(requeridas) <= set(X.columns):
        raise ValueError('Faltan columnas requeridas del estimador')
    ids = X.id_parcela
    if (not ids.map(lambda x: isinstance(x, str) and bool(x.strip())).all()
            or not ids.is_unique or not X.index.is_unique
            or not np.array_equal(X.index.to_numpy(), ids.to_numpy())):
        raise ValueError('IDs únicos y alineados con el índice de X requeridos')
    if territorio:
        for c in ('municipio', 'cultivo_origen'):
            if not X[c].map(lambda x: isinstance(x, str) and bool(x.strip())).all():
                raise ValueError(f'Metadato territorial ausente: {c}')
    for c in columnas:
        if not pd.api.types.is_numeric_dtype(X[c]) or pd.api.types.is_bool_dtype(X[c]):
            raise ValueError(f'Clima numérico requerido: {c}')
        if not np.isfinite(X[c].to_numpy(dtype=float)).all():
            raise ValueError(f'Clima incompleto o no finito: {c}')


def validar_y(X, y):
    if (not isinstance(y, pd.Series) or not y.index.is_unique
            or not np.array_equal(y.index.to_numpy(), X.index.to_numpy())):
        raise ValueError('y debe ser una serie alineada por ID, no por posición')
    if (not pd.api.types.is_numeric_dtype(y) or pd.api.types.is_bool_dtype(y)
            or not np.isfinite(y.to_numpy(dtype=float)).all()):
        raise ValueError('Etiquetas numéricas finitas requeridas')
    if len(y) < 2:
        raise ValueError('Se requieren al menos dos etiquetas de entrenamiento')


def _medias(X, y, clave):
    # Misma agregación de T08: s.mean() por grupo, no un estadístico distinto.
    return pd.DataFrame({'clave': X[clave], 'y': y}).groupby('clave').y.agg(lambda s: s.mean())


def _reiniciar_ajuste(modelo):
    # Un intento fallido no debe permitir seguir usando coeficientes de otro dataset.
    for nombre in list(vars(modelo)):
        if nombre.endswith('_'):
            delattr(modelo, nombre)


class MediaTerritorial(RegressorMixin, BaseEstimator):
    """Media municipal → grupo de registro → global, exactamente T08/D019."""

    def fit(self, X, y):
        _reiniciar_ajuste(self)
        validar_X(X, territorio=True)
        validar_y(X, y)
        self.media_municipio_ = _medias(X, y, 'municipio')
        self.media_grupo_ = _medias(X, y, 'cultivo_origen')
        self.media_global_ = float(y.mean())
        if (not np.isfinite(self.media_global_) or not np.isfinite(self.media_municipio_).all()
                or not np.isfinite(self.media_grupo_).all()):
            _reiniciar_ajuste(self)
            raise ValueError('Referencia no finita; no entregar este ajuste')
        self.ids_entrenamiento_ = tuple(X.index)
        self.n_entrenamiento_ = len(X)
        return self

    def predict_with_details(self, X):
        check_is_fitted(self, 'media_municipio_')
        validar_X(X, territorio=True)
        p = X.municipio.map(self.media_municipio_)
        fuente = pd.Series('municipio', index=X.index, dtype=object)
        g = X.cultivo_origen.map(self.media_grupo_)
        fuente.loc[p.isna() & g.notna()] = 'grupo'
        p = p.fillna(g)
        fuente.loc[p.isna()] = 'global'
        p = p.fillna(self.media_global_)
        if not np.isfinite(p).all():
            raise ValueError('Referencia no finita; no rellenar con cero')
        return pd.DataFrame({'id_parcela': X.id_parcela, 'prediccion': p,
                             'fuente': fuente, 'referencia': p, 'correccion': 0.}, index=X.index)

    def predict(self, X):
        return self.predict_with_details(X).prediccion.to_numpy()


def referencia_loo(X, y):
    """LOO de la misma referencia. Nunca admite una etiqueta ausente."""
    validar_X(X, territorio=True)
    validar_y(X, y)
    resultado = pd.Series(np.nan, index=X.index, dtype=float)
    fuente = pd.Series('global', index=X.index, dtype=object)
    for clave, nombre in [('municipio', 'municipio'), ('cultivo_origen', 'grupo')]:
        medias = _medias(X, y, clave)
        n = X[clave].map(X[clave].value_counts()).to_numpy()
        mu = X[clave].map(medias).to_numpy()
        candidato = np.full(len(X), np.nan)
        valido = n > 1
        # Forma centrada: evita restar una etiqueta a una suma grande.
        candidato[valido] = mu[valido] + (mu[valido] - y.to_numpy()[valido]) / (n[valido] - 1)
        usar = resultado.isna().to_numpy() & valido
        resultado.iloc[np.flatnonzero(usar)] = candidato[usar]
        fuente.iloc[np.flatnonzero(usar)] = nombre
    mu = float(y.mean())
    global_ = mu + (mu - y) / (len(y) - 1)
    return resultado.fillna(global_), fuente


class RidgeClimatico(RegressorMixin, BaseEstimator):
    """CL, TC o R; escalado encapsulado en fit y sólo clima penalizado.

    X es DataFrame por ID, y es Series por el mismo ID. Admite clone/Pipeline,
    no la interfaz genérica de matrices anónimas sin identidad parcelaria.
    """
    def __init__(self, procedimiento='TC', ventana='jun_oct', lambda_reg=0.1):
        self.procedimiento = procedimiento
        self.ventana = ventana
        self.lambda_reg = lambda_reg

    def fit(self, X, y):
        _reiniciar_ajuste(self)
        if self.procedimiento not in ('CL', 'TC', 'R'):
            raise ValueError('Procedimiento fuera del diseño T09')
        if (not isinstance(self.lambda_reg, numbers.Real) or isinstance(self.lambda_reg, bool)
                or not np.isfinite(self.lambda_reg) or self.lambda_reg <= 0):
            raise ValueError('Regularización positiva y finita requerida')
        cols = columnas_clima(self.ventana)
        validar_X(X, cols, territorio=self.procedimiento != 'CL')
        validar_y(X, y)
        self.columnas_ = tuple(cols)
        self.ids_entrenamiento_ = tuple(X.index)
        self.n_entrenamiento_ = len(X)
        self.alpha_ = float(len(X) * self.lambda_reg)
        self.parametros_ajustados_ = (self.procedimiento, self.ventana, self.lambda_reg)
        # El pipeline se crea y reajusta dentro de cada fit, nunca sobre todo el dataset.
        self.preprocesado_ = Pipeline([('escala', StandardScaler())])
        z = self.preprocesado_.fit_transform(X[cols])
        self.constantes_ = tuple(c for c, v in zip(cols, self.preprocesado_['escala'].var_) if v == 0)
        fit_z, fit_y = z, y.to_numpy(dtype=float)
        self.modelo_ = Ridge(alpha=self.alpha_, fit_intercept=self.procedimiento == 'CL', solver='svd')
        if self.procedimiento != 'CL':
            self.referencia_ = MediaTerritorial().fit(X, y)
        if self.procedimiento == 'TC':
            zdf = pd.DataFrame(z, index=X.index, columns=cols)
            self.z_municipio_ = zdf.groupby(X.municipio).mean()
            self.z_grupo_ = zdf.groupby(X.cultivo_origen).mean()
            self.z_global_ = zdf.mean().to_numpy()
            fit_z = z - self.z_municipio_.loc[X.municipio].to_numpy()
            fit_y = y.to_numpy() - X.municipio.map(self.referencia_.media_municipio_).to_numpy()
        elif self.procedimiento == 'R':
            self.referencia_loo_, self.fuente_loo_ = referencia_loo(X, y)
            self.residuos_ = y.copy() - self.referencia_loo_
            fit_y = self.residuos_.to_numpy()
        self.modelo_.fit(fit_z, fit_y)
        self.coef_estandarizados_ = self.modelo_.coef_.copy()
        self.coef_fisicos_ = self.coef_estandarizados_ / self.preprocesado_['escala'].scale_
        if not np.isfinite(self.coef_estandarizados_).all():
            _reiniciar_ajuste(self)
            raise ValueError('Coeficientes no finitos; no entregar este ajuste')
        return self

    def predict_with_details(self, X):
        check_is_fitted(self, 'coef_estandarizados_')
        if self.parametros_ajustados_ != (self.procedimiento, self.ventana, self.lambda_reg):
            raise ValueError('Reajustar después de cambiar parámetros del estimador')
        validar_X(X, self.columnas_, territorio=self.procedimiento != 'CL')
        z = self.preprocesado_.transform(X[list(self.columnas_)])
        if self.procedimiento == 'CL':
            base = np.full(len(X), float(self.modelo_.intercept_))
            correccion = z @ self.coef_estandarizados_
            fuente = np.full(len(X), 'global', dtype=object)
        else:
            detalle = self.referencia_.predict_with_details(X)
            base, fuente = detalle.prediccion.to_numpy(), detalle.fuente.to_numpy()
            if self.procedimiento == 'TC':
                zr = np.tile(self.z_global_, (len(X), 1))
                for i, (m, g, f) in enumerate(zip(X.municipio, X.cultivo_origen, fuente)):
                    if f == 'municipio':
                        zr[i] = self.z_municipio_.loc[m].to_numpy()
                    elif f == 'grupo':
                        zr[i] = self.z_grupo_.loc[g].to_numpy()
                correccion = (z - zr) @ self.coef_estandarizados_
            else:
                correccion = self.modelo_.predict(z)
        p = base + correccion
        if not np.isfinite(p).all():
            raise ValueError('Predicción no finita; no recortar ni rellenar')
        return pd.DataFrame({'id_parcela': X.id_parcela, 'prediccion': p, 'fuente': fuente,
                             'referencia': base, 'correccion': correccion}, index=X.index)

    def predict(self, X):
        return self.predict_with_details(X).prediccion.to_numpy()


def crear_estimador(procedimiento, ventana='jun_oct', lambda_reg=0.1):
    if procedimiento == 'T':
        return MediaTerritorial()
    return RidgeClimatico(procedimiento, ventana, lambda_reg)
