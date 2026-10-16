"""T12: heterogeneidad municipal y contraste no lineal sobre común-centrado-LOO-v3.

Parte 1 (paso 2): familia `het`, pendiente común más desviación municipal contraída.
Hereda de v3 la referencia, el residuo sin la fila, las transformaciones, el
escalado y el centro sin la fila; sólo cambia el ajuste final de Ridge.
No ejecuta evaluaciones ni ajusta las 59.
"""
import copy
import json
from math import sqrt
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge

from scripts import evaluacion_comun_centrado_loo as v3
from scripts.evaluacion_comun_contrato import exigir, sha
from scripts.evaluacion_comun_modelo import validar_X, aplicar_referencia

VERSION = 't12-heterogeneidad-v1'
RAIZ = v3.RAIZ
DISENO = 'registro/t12/procedimiento_t12.json'
DISENO_SHA = 'c0bd784b1bb55dda887294fb597d3e6547485992b5a220a1249ed57c79bf41b9'
N_MIN_PENDIENTE = 12
KAPPA = (1.0, 10.0)


def cargar_diseno(raiz=RAIZ):
    """Lee el diseño registrado y se detiene si cambió después del commit."""
    ruta = Path(raiz) / DISENO
    exigir(sha(ruta) == DISENO_SHA, 'Diseño T12 modificado: versionar y registrar antes de correr')
    cfg = json.loads(ruta.read_text(encoding='utf-8'))
    exigir(cfg['schema'] == 'experimento_t12_heterogeneidad_v1', 'Diseño T12 incompatible')
    exigir(cfg['familias']['het']['N_MIN_PENDIENTE'] == N_MIN_PENDIENTE and
           tuple(cfg['familias']['het']['kappa']) == KAPPA, 'Constantes del código distintas del diseño')
    return cfg


def grupos_con_pendiente(X, n_min=N_MIN_PENDIENTE):
    """Municipios con al menos n_min filas en este entrenamiento, en orden estable."""
    validar_X(X, [])
    n = X.municipio.value_counts()
    return tuple(sorted(str(m) for m in n[n >= n_min].index))


def _validar_grupos(grupos):
    exigir(isinstance(grupos, tuple) and all(isinstance(g, str) and g.strip() == g and g for g in grupos),
           'Lista de municipios con pendiente propia inválida')
    exigir(len(set(grupos)) == len(grupos) and list(grupos) == sorted(grupos),
           'Municipios con pendiente propia repetidos o fuera de orden')


class CorreccionPendienteMunicipal(v3.CorreccionComunCentradaLOO):
    """Referencia T08 + Ridge LOO v3 con pendiente común y desviación municipal contraída.

    r_i ≈ D_i·β + D_i·γ_m(i), penalización n·λ·(‖β‖² + κ·Σ‖γ_m‖²), sin intercepto.
    Se implementa escalando cada bloque municipal por 1/√κ en un solo Ridge.

    grupos_pendiente=None: se calcula con este entrenamiento (≥ N_MIN_PENDIENTE filas).
    Una tupla: se usa tal cual (las internas heredan la lista del entrenamiento externo).
    """

    def __init__(self, columnas=(), lambda_reg=None, kappa=None, grupos_pendiente=None):
        super().__init__(columnas, lambda_reg)
        self.kappa = kappa
        self.grupos_pendiente = None if grupos_pendiente is None else tuple(grupos_pendiente)

    def _validar_parametros_t12(self):
        if self.columnas:
            exigir(not isinstance(self.kappa, bool) and self.kappa in KAPPA, 'κ fuera del procedimiento')
        else:
            exigir(self.kappa is None, 'La referencia sola no lleva κ')
        if self.grupos_pendiente is not None:
            _validar_grupos(self.grupos_pendiente)

    def _aumentar(self, d, municipios):
        bloques = [d]
        for g in self.grupos_pendiente_:
            bloques.append(d * (municipios == g)[:, None] / sqrt(self.kappa))
        return np.hstack(bloques)

    def fit(self, X, y):
        self._validar_parametros_t12()
        super().fit(X, y)  # v3: residuos_, escalador_, centros_sin_fila_, alpha_; deja un Ridge común
        try:
            self.grupos_pendiente_ = ()
            if self.ridge_ is not None:
                Xs = X.sort_index()
                exigir(tuple(Xs.index) == self.ids_entrenamiento_, 'Orden de entrenamiento distinto de v3')
                grupos = grupos_con_pendiente(Xs) if self.grupos_pendiente is None else self.grupos_pendiente
                _validar_grupos(grupos)
                self.grupos_pendiente_ = grupos
                self.n_por_grupo_ = {g: int((Xs.municipio == g).sum()) for g in grupos}
                # Mismas transformaciones que v3, sin reaprender mediana ni escala.
                z = self.escalador_.transform(self._valores(Xs))
                d = z - self.centros_sin_fila_.loc[Xs.index].to_numpy()
                self.ridge_ = Ridge(alpha=self.alpha_, fit_intercept=False, solver='svd').fit(
                    self._aumentar(d, Xs.municipio.to_numpy()), self.residuos_)
                exigir(np.isfinite(self.ridge_.coef_).all(), 'Coeficientes no finitos')
                p, c = d.shape[1], self.ridge_.coef_
                self.beta_ = c[:p].copy()
                self.gamma_ = {g: c[p * (k + 1):p * (k + 2)] / sqrt(self.kappa) for k, g in enumerate(grupos)}
            self.parametros_fit_ = (tuple(self.columnas), self.lambda_reg, self.kappa, self.grupos_pendiente)
        except Exception:
            self._limpiar()
            raise
        return self

    def _comprobar(self):
        exigir(getattr(self, 'ajustado_', False), 'Modelo sin ajustar')
        exigir(self.parametros_fit_ == (tuple(self.columnas), self.lambda_reg, self.kappa, self.grupos_pendiente),
               'Reajustar después de cambiar columnas, λ, κ o municipios')

    def predict_with_details(self, X):
        self._comprobar()
        validar_X(X, self.columnas)
        base, source = aplicar_referencia(X, self.mun_, self.grupo_, self.global_)
        correction = np.zeros(len(X))
        source_center = np.full(len(X), 'no_aplica', dtype=object)
        propia = np.zeros(len(X), bool)
        if self.ridge_ is not None:
            z = self.escalador_.transform(self._valores(X))
            center, source_center = self._centros(X)
            exigir(np.array_equal(source_center, source), 'Centro y referencia con respaldos diferentes')
            municipios = X.municipio.to_numpy()
            correction = self.ridge_.predict(self._aumentar(z - center, municipios))
            propia = np.isin(municipios, self.grupos_pendiente_)
        prediction = base + correction
        exigir(np.isfinite(prediction).all(), 'Predicción no finita')
        return pd.DataFrame(dict(prediccion=prediction, referencia=base, correccion=correction,
                                 fuente=source, fuente_centrado=source_center,
                                 pendiente_propia=propia), index=X.index)

    def pendientes(self):
        """β + γ_m por municipio con pendiente propia, y β como 'comun' (para C5)."""
        self._comprobar()
        exigir(self.ridge_ is not None, 'La referencia sola no tiene pendientes')
        filas = {'comun': self.beta_}
        filas.update({g: self.beta_ + self.gamma_[g] for g in self.grupos_pendiente_})
        return pd.DataFrame(filas, index=self.nombres_).T

    def estado(self):
        e = copy.deepcopy(super().estado())
        e.update(version=VERSION, sha_diseno_t12=DISENO_SHA, version_base=v3.VERSION,
                 familia='het_pendiente_comun_mas_desviacion_municipal_contraida',
                 kappa=self.kappa, n_min_pendiente=N_MIN_PENDIENTE,
                 grupos_pendiente_heredados=self.grupos_pendiente is not None,
                 grupos_pendiente=list(self.grupos_pendiente_))
        if self.ridge_ is not None:
            e.update(beta=self.beta_.tolist(), gamma={g: v.tolist() for g, v in self.gamma_.items()},
                     n_por_grupo=dict(self.n_por_grupo_))
        return e


def clave_opcion_het(row):
    """Desempate registrado: MAE a 6 decimales > referencia sola > λ mayor > κ mayor > jun_oct > nombre."""
    return (round(row['MAE'], 6), 0 if row['referencia_sola'] else 1, -(row.get('lambda_reg') or 0),
            -(row.get('kappa') or 0), 0 if row['ventana'] == 'jun_oct' else 1, row['nombre'])
