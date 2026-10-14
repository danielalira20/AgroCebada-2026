"""R centrado v2: componentes fit/predict, sin ejecutar evaluaciones externas.

Mantiene R-v1 reproducible. Los centros y escala se aprenden sólo en fit;
predict aplica ese estado y no vuelve a calcular estadísticas territoriales.
"""
import numbers

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, RegressorMixin
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.utils.validation import check_is_fitted

from scripts.t09_estimadores import (MediaTerritorial, _reiniciar_ajuste,
                                    columnas_clima, referencia_loo,
                                    validar_X, validar_y)

VERSION = 'T09-R-centrado-v2'


class RidgeResidualCentrado(RegressorMixin, BaseEstimator):
    """Referencia T08 + Ridge LOO sobre Z menos centro municipal del fit.

    Se conserva la escala global. Municipio ausente usa centro de grupo/global,
    aprendido con las mismas filas que la referencia de rendimiento.
    """

    def __init__(self, ventana='jun_oct', lambda_reg=0.1):
        self.ventana = ventana
        self.lambda_reg = lambda_reg

    def fit(self, X, y):
        _reiniciar_ajuste(self)
        try:
            if (not isinstance(self.lambda_reg, numbers.Real)
                    or isinstance(self.lambda_reg, bool)
                    or not np.isfinite(self.lambda_reg) or self.lambda_reg <= 0):
                raise ValueError('Regularización positiva y finita requerida')
            cols = columnas_clima(self.ventana)
            validar_X(X, cols, territorio=True)
            validar_y(X, y)
            X = X.sort_index().copy()
            y = y.loc[X.index].copy()
            self.columnas_ = tuple(cols)
            self.ids_entrenamiento_ = tuple(X.index)
            self.n_entrenamiento_ = len(X)
            self.alpha_ = float(len(X) * self.lambda_reg)
            self.parametros_ajustados_ = (self.ventana, self.lambda_reg)
            self.referencia_ = MediaTerritorial().fit(X, y)
            self.referencia_loo_, self.fuente_loo_ = referencia_loo(X, y)
            self.residuos_ = y - self.referencia_loo_
            self.preprocesado_ = Pipeline([('escala', StandardScaler())])
            z = self.preprocesado_.fit_transform(X[cols])
            if not np.isfinite(z).all():
                raise ValueError('Escala climática no finita')
            zdf = pd.DataFrame(z, index=X.index, columns=cols)
            self.z_municipio_ = zdf.groupby(X.municipio).mean().copy()
            self.z_grupo_ = zdf.groupby(X.cultivo_origen).mean().copy()
            self.z_global_ = zdf.mean().to_numpy().copy()
            self.n_municipio_ = X.municipio.value_counts().sort_index().copy()
            self.n_grupo_ = X.cultivo_origen.value_counts().sort_index().copy()
            self.constantes_ = tuple(c for c, v in zip(
                cols, self.preprocesado_['escala'].var_) if v == 0)
            # Z conserva su escala global. No amplificar las desviaciones pequeñas.
            d = z - self.z_municipio_.loc[X.municipio].to_numpy()
            self.modelo_ = Ridge(alpha=self.alpha_, fit_intercept=False,
                                 solver='svd').fit(d, self.residuos_.to_numpy())
            self.coef_estandarizados_ = self.modelo_.coef_.copy()
            self.coef_fisicos_ = (self.coef_estandarizados_
                                  / self.preprocesado_['escala'].scale_)
            if not np.isfinite(self.coef_estandarizados_).all():
                raise ValueError('Coeficientes no finitos')
            self.ajustado_ = True
        except Exception:
            # Incluso un fallo después de aprender centros invalida el estado parcial.
            _reiniciar_ajuste(self)
            raise
        return self

    def _centros(self, X):
        centers = np.tile(self.z_global_, (len(X), 1))
        source = np.full(len(X), 'global', dtype=object)
        for i, (municipio, grupo) in enumerate(zip(X.municipio, X.cultivo_origen)):
            if municipio in self.z_municipio_.index:
                centers[i] = self.z_municipio_.loc[municipio].to_numpy()
                source[i] = 'municipio'
            elif grupo in self.z_grupo_.index:
                centers[i] = self.z_grupo_.loc[grupo].to_numpy()
                source[i] = 'grupo'
        return centers, source

    def predict_with_details(self, X):
        check_is_fitted(self, 'ajustado_')
        if self.parametros_ajustados_ != (self.ventana, self.lambda_reg):
            raise ValueError('Reajustar después de cambiar parámetros del estimador')
        validar_X(X, self.columnas_, territorio=True)
        z = self.preprocesado_.transform(X[list(self.columnas_)])
        center, source_center = self._centros(X)
        base = self.referencia_.predict_with_details(X)
        if not np.array_equal(source_center, base.fuente.to_numpy()):
            raise ValueError('Centro y referencia usan respaldos distintos')
        correction = self.modelo_.predict(z - center)
        prediction = base.prediccion.to_numpy() + correction
        if not np.isfinite(prediction).all():
            raise ValueError('Predicción no finita; no recortar ni rellenar')
        return pd.DataFrame({'id_parcela': X.id_parcela,
                             'prediccion': prediction,
                             'fuente': base.fuente,
                             'referencia': base.prediccion,
                             'correccion': correction,
                             'fuente_centrado': source_center}, index=X.index)

    def predict(self, X):
        return self.predict_with_details(X).prediccion.to_numpy()

    def estado(self):
        """Estado JSON auditable; devuelve copias, no vistas de los centros aprendidos."""
        check_is_fitted(self, 'ajustado_')
        if self.parametros_ajustados_ != (self.ventana, self.lambda_reg):
            raise ValueError('Reajustar después de cambiar parámetros del estimador')
        def vectors(frame):
            return {str(k): [float(v) for v in row]
                    for k, row in zip(frame.index, frame.to_numpy())}
        return {'version_modelo': VERSION, 'procedimiento': 'R_centrado',
                'ids_entrenamiento': list(self.ids_entrenamiento_),
                'n_entrenamiento': self.n_entrenamiento_, 'ventana': self.ventana,
                'columnas': list(self.columnas_), 'lambda_reg': float(self.lambda_reg),
                'alpha': self.alpha_, 'fit_intercept': False, 'intercepto': 0.0,
                'media_escalado': self.preprocesado_['escala'].mean_.tolist(),
                'escala_global': self.preprocesado_['escala'].scale_.tolist(),
                'coef_estandarizados': self.coef_estandarizados_.tolist(),
                'coef_fisicos': self.coef_fisicos_.tolist(),
                'centros_Z_municipio': vectors(self.z_municipio_),
                'centros_Z_grupo': vectors(self.z_grupo_),
                'centro_Z_global': self.z_global_.tolist(),
                'n_municipio': {str(k): int(v) for k, v in self.n_municipio_.items()},
                'n_grupo': {str(k): int(v) for k, v in self.n_grupo_.items()},
                'referencia_y_municipio': self.referencia_.media_municipio_.to_dict(),
                'referencia_y_grupo': self.referencia_.media_grupo_.to_dict(),
                'referencia_y_global': self.referencia_.media_global_,
                'politica_centro': 'municipio_entrenamiento_luego_grupo_luego_global',
                'reescalar_desviaciones_intramunicipales': False}
