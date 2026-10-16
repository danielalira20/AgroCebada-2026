"""T12: heterogeneidad municipal y contraste no lineal sobre común-centrado-LOO-v3.

Familia `het` (parte 1): pendiente común más desviación municipal contraída.
Familia `gb` (parte 2): boosting con pérdida absoluta sobre las mismas entradas.
Selector (parte 3): elige la opción con las internas de T03/D026 y hereda los municipios
con pendiente propia del entrenamiento externo.
Ambas heredan de v3 la referencia, el residuo sin la fila, las transformaciones,
el escalado y el centro sin la fila; sólo cambia el ajuste final.
No ejecuta evaluaciones ni ajusta las 59.
"""
import copy
import json
from math import sqrt
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.linear_model import Ridge

from scripts import evaluacion_comun_centrado_loo as v3
from scripts.evaluacion_comun_contrato import exigir, sha
from scripts import evaluacion_comun_modelo as base
from scripts.evaluacion_comun_modelo import validar_X, validar_y, aplicar_referencia, divisiones_internas

VERSION = 't12-heterogeneidad-v1'
RAIZ = v3.RAIZ
DISENO = 'registro/t12/procedimiento_t12.json'
DISENO_SHA = 'c0bd784b1bb55dda887294fb597d3e6547485992b5a220a1249ed57c79bf41b9'
N_MIN_PENDIENTE = 12
KAPPA = (1.0, 10.0)
N_ARBOLES = (50, 150)
SEMILLA_GB = 20261015
PARAMETROS_GB = dict(loss='absolute_error', max_depth=2, min_samples_leaf=10, learning_rate=0.05,
                     subsample=0.8, init='zero', random_state=SEMILLA_GB)
# v3 exige un λ de su lista al ajustar. El boosting no lo usa: se fija uno para reutilizar
# el cálculo de residuos y centros sin cambiarlo, y no interviene en ninguna predicción.
LAMBDA_NO_USADO = 1.0
REFERENCIAS = {'media_mun__resp_grupo': 'media', 'mediana_mun__resp_grupo': 'mediana'}
MAX_OPCIONES = 16


def cargar_diseno(raiz=RAIZ):
    """Lee el diseño registrado y se detiene si cambió después del commit."""
    ruta = Path(raiz) / DISENO
    exigir(sha(ruta) == DISENO_SHA, 'Diseño T12 modificado: versionar y registrar antes de correr')
    cfg = json.loads(ruta.read_text(encoding='utf-8'))
    exigir(cfg['schema'] == 'experimento_t12_heterogeneidad_v1', 'Diseño T12 incompatible')
    exigir(cfg['familias']['het']['N_MIN_PENDIENTE'] == N_MIN_PENDIENTE and
           tuple(cfg['familias']['het']['kappa']) == KAPPA, 'Constantes het del código distintas del diseño')
    gb = cfg['familias']['gb']
    exigir(gb['parametros_fijos'] == PARAMETROS_GB and tuple(gb['n_estimators']) == N_ARBOLES,
           'Parámetros gb del código distintos del diseño')
    return cfg


def grupos_con_pendiente(X, n_min=N_MIN_PENDIENTE):
    """Municipios con al menos n_min filas en este entrenamiento, en orden estable."""
    validar_X(X, [])
    n = X.municipio.value_counts()
    return tuple(sorted(str(m) for m in n[n >= n_min].index))


def medianas(X, y):
    """Como T08 `mediana_mun__resp_grupo`: mediana por municipio, por grupo y global."""
    X = X.sort_index()
    y = y.loc[X.index]
    m = {k: float(np.median(y.loc[g.index].to_numpy(float))) for k, g in X.groupby('municipio')}
    g = {k: float(np.median(y.loc[v.index].to_numpy(float))) for k, v in X.groupby('cultivo_origen')}
    return m, g, float(np.median(y.to_numpy(float)))


def residuos_loo_mediana(X, y):
    """Igual que residuos_loo de v3, con la mediana del mismo grupo de IDs sin la fila."""
    validar_X(X, [])
    validar_y(X, y)
    exigir(len(X) > 1, 'LOO requiere más de una fila')
    pools = v3.pools_sin_fila(X)
    return np.asarray([float(y.loc[pid]) - float(np.median(y.loc[list(pools[pid][1])].to_numpy(float)))
                       for pid in X.index])


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

    def __init__(self, columnas=(), lambda_reg=None, kappa=None, grupos_pendiente=None, referencia='media'):
        super().__init__(columnas, lambda_reg)
        self.kappa = kappa
        self.grupos_pendiente = None if grupos_pendiente is None else tuple(grupos_pendiente)
        self.referencia = referencia

    def _validar_parametros_t12(self):
        exigir(self.referencia in ('media', 'mediana'), 'Referencia fuera del procedimiento')
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
            Xs = X.sort_index()
            exigir(tuple(Xs.index) == self.ids_entrenamiento_, 'Orden de entrenamiento distinto de v3')
            if self.referencia == 'mediana':
                # Control E_T12_008: sólo cambia la referencia y, con ella, el residuo sin la fila.
                self.mun_, self.grupo_, self.global_ = medianas(Xs, y.loc[Xs.index])
                if self.ridge_ is not None:
                    self.residuos_ = residuos_loo_mediana(Xs, y.loc[Xs.index])
            if self.ridge_ is not None:
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
            self.parametros_fit_ = (tuple(self.columnas), self.lambda_reg, self.kappa, self.grupos_pendiente,
                                    self.referencia)
        except Exception:
            self._limpiar()
            raise
        return self

    def _comprobar(self):
        exigir(getattr(self, 'ajustado_', False), 'Modelo sin ajustar')
        exigir(self.parametros_fit_ == (tuple(self.columnas), self.lambda_reg, self.kappa, self.grupos_pendiente,
                                        self.referencia),
               'Reajustar después de cambiar columnas, λ, κ, municipios o referencia')

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
                 kappa=self.kappa, n_min_pendiente=N_MIN_PENDIENTE, referencia=self.referencia,
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


class CorreccionBoostingL1(v3.CorreccionComunCentradaLOO):
    """Referencia T08 + boosting con pérdida absoluta sobre el residuo LOO de v3.

    Entradas: las desviaciones D_i de v3 más un indicador 0/1 por municipio con pendiente propia
    (misma regla de ≥ N_MIN_PENDIENTE filas, o la lista heredada). Objetivo: los r_i de v3.
    init='zero': no hay término constante, la corrección sólo puede venir de las variables.
    Sin columnas es la referencia sola.
    """

    def __init__(self, columnas=(), n_estimators=None, grupos_pendiente=None):
        super().__init__(columnas, LAMBDA_NO_USADO if columnas else None)
        self.n_estimators = n_estimators
        self.grupos_pendiente = None if grupos_pendiente is None else tuple(grupos_pendiente)

    def _validar_parametros_t12(self):
        if self.columnas:
            exigir(not isinstance(self.n_estimators, bool) and self.n_estimators in N_ARBOLES,
                   'n_estimators fuera del procedimiento')
        else:
            exigir(self.n_estimators is None, 'La referencia sola no lleva árboles')
        if self.grupos_pendiente is not None:
            _validar_grupos(self.grupos_pendiente)

    def _entradas(self, d, municipios):
        indicadores = [(municipios == g).astype(float)[:, None] for g in self.grupos_pendiente_]
        return np.hstack([d, *indicadores])

    def fit(self, X, y):
        self._validar_parametros_t12()
        super().fit(X, y)  # v3: residuos_, escalador_, centros_sin_fila_
        try:
            self.grupos_pendiente_ = ()
            self.gb_ = None
            if self.ridge_ is not None:
                Xs = X.sort_index()
                exigir(tuple(Xs.index) == self.ids_entrenamiento_, 'Orden de entrenamiento distinto de v3')
                grupos = grupos_con_pendiente(Xs) if self.grupos_pendiente is None else self.grupos_pendiente
                _validar_grupos(grupos)
                self.grupos_pendiente_ = grupos
                self.ridge_ = None  # el Ridge común de v3 no interviene en esta familia
                z = self.escalador_.transform(self._valores(Xs))
                d = z - self.centros_sin_fila_.loc[Xs.index].to_numpy()
                self.gb_ = GradientBoostingRegressor(n_estimators=self.n_estimators, **PARAMETROS_GB).fit(
                    self._entradas(d, Xs.municipio.to_numpy()), self.residuos_)
                exigir(np.isfinite(self.gb_.predict(self._entradas(d, Xs.municipio.to_numpy()))).all(),
                       'Boosting no finito')
            self.parametros_fit_ = (tuple(self.columnas), self.n_estimators, self.grupos_pendiente)
        except Exception:
            self._limpiar()
            raise
        return self

    def _comprobar(self):
        exigir(getattr(self, 'ajustado_', False), 'Modelo sin ajustar')
        exigir(self.parametros_fit_ == (tuple(self.columnas), self.n_estimators, self.grupos_pendiente),
               'Reajustar después de cambiar columnas, árboles o municipios')

    def predict_with_details(self, X):
        self._comprobar()
        validar_X(X, self.columnas)
        base, source = aplicar_referencia(X, self.mun_, self.grupo_, self.global_)
        correction = np.zeros(len(X))
        source_center = np.full(len(X), 'no_aplica', dtype=object)
        if self.gb_ is not None:
            z = self.escalador_.transform(self._valores(X))
            center, source_center = self._centros(X)
            exigir(np.array_equal(source_center, source), 'Centro y referencia con respaldos diferentes')
            correction = self.gb_.predict(self._entradas(z - center, X.municipio.to_numpy()))
        prediction = base + correction
        exigir(np.isfinite(prediction).all(), 'Predicción no finita')
        return pd.DataFrame(dict(prediccion=prediction, referencia=base, correccion=correction,
                                 fuente=source, fuente_centrado=source_center), index=X.index)

    def importancias(self):
        """Importancia por variable (descriptiva, para C5); los indicadores van al final."""
        self._comprobar()
        exigir(self.gb_ is not None, 'La referencia sola no tiene importancias')
        nombres = list(self.nombres_) + [f'municipio={g}' for g in self.grupos_pendiente_]
        return pd.Series(self.gb_.feature_importances_, index=nombres)

    def estado(self):
        self._comprobar()
        e = {'familia': 'gb_boosting_absoluto_sobre_residuo_LOO_v3', 'version': VERSION,
             'sha_diseno_t12': DISENO_SHA, 'version_base': v3.VERSION,
             'ids_entrenamiento': list(self.ids_entrenamiento_), 'n': self.n_,
             'municipio': self.mun_, 'grupo': self.grupo_, 'global': self.global_,
             'columnas': list(self.columnas), 'n_estimators': self.n_estimators,
             'parametros_gb': dict(PARAMETROS_GB), 'intercepto': 0.0,
             'grupos_pendiente_heredados': self.grupos_pendiente is not None,
             'grupos_pendiente': list(self.grupos_pendiente_)}
        if self.gb_ is not None:
            e.update(nombres_transformados=self.nombres_, media=self.escalador_.mean_.tolist(),
                     escala=self.escalador_.scale_.tolist(),
                     mediana_pendiente=getattr(self, 'mediana_pendiente_', None),
                     importancias=self.importancias().to_dict())
        return e


def clave_opcion_gb(row):
    """Desempate registrado: MAE a 6 decimales > referencia sola > menos árboles > jun_oct > nombre."""
    return (round(row['MAE'], 6), 0 if row['referencia_sola'] else 1, row.get('n_estimators') or 0,
            0 if row['ventana'] == 'jun_oct' else 1, row['nombre'])



# ------------------------------------------------------------------ selector (parte 3)
def opciones_registradas(procedimiento):
    """Opciones del JSON con su nombre registrado; no se generan opciones nuevas."""
    familia = procedimiento['familia']
    exigir(familia in ('het', 'gb', 'comun_v3'), 'Familia desconocida')
    exigir(procedimiento['referencia'] in REFERENCIAS, 'Referencia desconocida')
    exigir(familia == 'het' or procedimiento['referencia'] == 'media_mun__resp_grupo',
           'Sólo het admite la referencia mediana')
    opciones = [dict(o) for o in procedimiento['opciones']]
    exigir(len(opciones) == procedimiento['n_opciones_con_variables'], 'Número de opciones distinto del registro')
    return opciones


def _validar_opciones(opciones, familia):
    exigir(1 <= len(opciones) <= MAX_OPCIONES, 'Número de opciones fuera del procedimiento')
    nombres = [o.get('nombre') for o in opciones]
    exigir(all(isinstance(n, str) and n for n in nombres) and len(set(nombres)) == len(nombres) and
           'referencia_sola' not in nombres, 'Nombre de opción vacío, duplicado o reservado')
    claves = {'het': {'nombre', 'columnas', 'ventana', 'lambda_reg', 'kappa'},
              'gb': {'nombre', 'columnas', 'ventana', 'n_estimators'},
              'comun_v3': {'nombre', 'columnas', 'ventana', 'lambda_reg'}}[familia]
    for o in opciones:
        exigir(set(o) == claves and o['columnas'], f'Opción con claves ajenas a la familia {familia}')
        exigir(o['ventana'] in ('abr_oct', 'jun_oct', 'estatica'), 'Ventana desconocida')


def fabrica(familia, opcion, grupos, referencia='media'):
    """Modelo sin ajustar para una opción; la referencia sola usa la misma referencia de la familia."""
    cols = tuple(opcion['columnas'])
    if familia == 'het':
        if not cols:
            return CorreccionPendienteMunicipal((), None, None, grupos, referencia)
        return CorreccionPendienteMunicipal(cols, opcion['lambda_reg'], opcion['kappa'], grupos, referencia)
    exigir(referencia == 'media', 'Sólo het admite la referencia mediana')
    if familia == 'gb':
        return CorreccionBoostingL1(cols, opcion.get('n_estimators') if cols else None, grupos)
    exigir(familia == 'comun_v3', 'Familia desconocida')
    return v3.CorreccionComunCentradaLOO(cols, opcion['lambda_reg'] if cols else None)


CLAVES = {'het': lambda r: clave_opcion_het(r), 'gb': lambda r: clave_opcion_gb(r),
          'comun_v3': lambda r: base.clave_opcion(r)}


def seleccionar_familia(X, y, opciones, escenario, familia, referencia='media', grupos_pendiente=None):
    """Selección interna T03 §5 / §5 bis con la referencia sola compitiendo.

    - Internas: A estratificadas por municipio (semilla 0); B por celda CHIRPS (D026).
    - MAE interno: sólo filas cuyo municipio está en el ajuste interno (población sin_respaldo).
    - La lista de municipios con pendiente propia sale del entrenamiento que recibe esta función
      (el externo) y la heredan todos los ajustes internos.
    Sólo usa X e y del entrenamiento; nunca recibe filas de evaluación externa ni las 59.
    """
    validar_X(X, [])
    validar_y(X, y)
    exigir(escenario in ('A', 'B'), 'Escenario fuera de T12')
    exigir(familia in CLAVES, 'Familia desconocida')
    exigir(referencia in ('media', 'mediana'), 'Referencia desconocida')
    _validar_opciones(opciones, familia)
    X = X.sort_index()
    y = y.loc[X.index]
    grupos = grupos_con_pendiente(X) if grupos_pendiente is None else tuple(grupos_pendiente)
    _validar_grupos(grupos)
    divisiones = divisiones_internas(X, escenario)
    alternativas = [dict(nombre='referencia_sola', columnas=[], ventana='estatica'), *opciones]
    puntuaciones = []
    n_una_etiqueta = 0
    for k, op in enumerate(alternativas):
        errores, todos = [], []
        for split in divisiones:
            tr, va = X.loc[list(split.entrenamiento)], X.loc[list(split.validacion)]
            exigir(not set(tr.index) & set(va.index), 'Interna no disjunta')
            modelo = fabrica(familia, op, grupos, referencia).fit(tr, y.loc[tr.index])
            err = np.abs(modelo.predict(va) - y.loc[va.index].to_numpy())
            errores.extend(err[np.asarray(split.elegibles)])
            todos.extend(err)
            if k == 0:
                n_mun = tr.municipio.value_counts()
                n_una_etiqueta += int(va.municipio.map(n_mun).eq(1).sum())
        exigir(errores and np.isfinite(errores).all(), 'Opción no evaluable; no saltarla')
        puntuaciones.append(dict(nombre=op['nombre'], ventana=op['ventana'], lambda_reg=op.get('lambda_reg'),
                                 kappa=op.get('kappa'), n_estimators=op.get('n_estimators'),
                                 referencia_sola=not op['columnas'], MAE=float(np.mean(errores)),
                                 MAE_todas=float(np.mean(todos)), n_elegibles=len(errores),
                                 n_validacion=len(todos), n_ajustes=len(divisiones)))
    ganadora = min(puntuaciones, key=CLAVES[familia])
    elegida = next(o for o in alternativas if o['nombre'] == ganadora['nombre'])
    return dict(elegida=dict(elegida), puntuaciones=puntuaciones, grupos_pendiente=grupos,
                internas='estratificada' if escenario == 'A' else 'celda',
                n_excluidas_respaldo=puntuaciones[0]['n_validacion'] - puntuaciones[0]['n_elegibles'],
                n_validacion_referencia_una_etiqueta=n_una_etiqueta,
                n_ajustes=len(alternativas) * len(divisiones), familia=familia, referencia=referencia,
                version=VERSION)


def ajustar_y_predecir(X, y, X_eval, procedimiento, escenario):
    """Selecciona dentro de X, ajusta con todo X y predice X_eval (evaluación externa o las 59).

    X_eval nunca entra en la selección ni en el ajuste.
    """
    familia = procedimiento['familia']
    referencia = REFERENCIAS[procedimiento['referencia']]
    exigir(not set(X.index) & set(X_eval.index), 'Evaluación externa dentro del entrenamiento')
    sel = seleccionar_familia(X, y, opciones_registradas(procedimiento), escenario, familia, referencia)
    modelo = fabrica(familia, sel['elegida'], sel['grupos_pendiente'], referencia).fit(X, y)
    detalle = modelo.predict_with_details(X_eval)
    return dict(seleccion=sel, modelo=modelo, detalle=detalle, candidato=procedimiento['candidato'],
                version=VERSION, sha_diseno_t12=DISENO_SHA)
