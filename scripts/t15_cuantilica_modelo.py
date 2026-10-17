"""Mediana conjunta municipal + S; contrato propio, sin alterar Ridge v3."""
import copy
import warnings
import numpy as np
import pandas as pd
from scipy.optimize import linprog
from scripts.evaluacion_comun_contrato import exigir
from scripts.evaluacion_comun_modelo import validar_X, validar_y, divisiones_internas

VERSION = 'cuantilica-municipal-v1'
CANDIDATO = 'cuantilica_municipal_S_v1'
ALPHAS = (.001, .01, .1, 1.)
S = {w: tuple(f's2_{v}_{w}' for v in ['ndvi_max', 'ndvi_integral',
     'ndvi_dias_sobre_mitad', 'ndwi_en_maximo']) + ('s2_ndvi_al_corte',)
     for w in ['abr_oct', 'jun_oct']}
OPCIONES = [dict(nombre='referencia_sola', columnas=[], alpha=None, ventana='estatica')] + [
    dict(nombre=f'{w}__alpha_{a:g}', columnas=list(S[w]), alpha=a, ventana=w)
    for w in S for a in ALPHAS]
SOLVER_OPTIONS = dict(primal_feasibility_tolerance=1e-9,
                      dual_feasibility_tolerance=1e-9,
                      simplex_dual_edge_weight_strategy='steepest-devex')


def resolver(c, **kwargs):
    with warnings.catch_warnings(record=True) as notices:
        warnings.simplefilter('always')
        res = linprog(c, method='highs-ds', options=SOLVER_OPTIONS, **kwargs)
    exigir(not notices, 'Advertencia del optimizador: ' + ';'.join(str(w.message) for w in notices))
    exigir(res.success and res.status == 0 and np.isfinite(res.x).all(),
           'Programación lineal falló: ' + res.message)
    return res


def resolver_primal(D, y, grupos, alpha):
    """Epígrafos: interceptos libres, beta libre, error absoluto y |beta|."""
    n, p = D.shape
    levels = sorted(set(grupos)); C = np.array([[int(m == g) for g in levels] for m in grupos], float)
    k = len(levels); z = np.zeros((n, p))
    A = np.vstack([np.c_[C, D, -np.eye(n), z], np.c_[-C, -D, -np.eye(n), z],
        np.c_[np.zeros((p, k)), np.eye(p), np.zeros((p, n)), -np.eye(p)],
        np.c_[np.zeros((p, k)), -np.eye(p), np.zeros((p, n)), -np.eye(p)]])
    b = np.r_[y, -y, np.zeros(2*p)]
    c = np.r_[np.zeros(k+p), np.full(n, .5/n), np.full(p, alpha)]
    bounds = [(None, None)]*(k+p) + [(0, None)]*(n+p)
    primary = resolver(c, A_ub=A, b_ub=b, bounds=bounds)
    equal = [c]; values = [float(primary.fun)]; current = primary
    lex = []
    for j in range(p):
        cj = np.zeros(len(c)); cj[k+j] = 1.
        current = resolver(cj, A_ub=A, b_ub=b, bounds=bounds,
                           A_eq=np.asarray(equal), b_eq=np.asarray(values))
        equal.append(cj); values.append(float(current.x[k+j])); lex.append(float(current.fun))
    beta = current.x[k:k+p]
    intercept = {g: float(np.median(y[np.asarray(grupos)==g] - D[np.asarray(grupos)==g]@beta)) for g in levels}
    residual = y - np.array([intercept[g] for g in grupos]) - D@beta
    obj = float(.5*np.mean(np.abs(residual)) + alpha*np.abs(beta).sum())
    exigir(abs(obj-primary.fun) <= 1e-7, 'Canonicalización cambió objetivo primario')
    exigir(float(np.max(A@current.x-b)) <= 1e-7, 'Primal no factible')
    return beta, intercept, dict(objetivo=obj, primario=float(primary.fun),
        lex=lex, n_resoluciones=1+p, max_violacion=float(max(0., np.max(A@current.x-b))))


class CuantilicaMunicipal:
    def __init__(self, columnas=(), alpha=None):
        self.columnas, self.alpha = tuple(columnas), alpha
        self.estado_ = None

    def fit(self, X, y):
        self.estado_ = None
        exigir((not self.columnas and self.alpha is None) or
               (self.columnas in S.values() and type(self.alpha) in [float, int] and self.alpha in ALPHAS),
               'Columnas/alpha ajenos al contrato')
        validar_X(X, self.columnas); validar_y(X, y)
        exigir(y.dtype.kind != 'b', 'Objetivo booleano')
        for col in self.columnas: exigir(X[col].dtype.kind != 'b', 'Predictor booleano')
        X = X.sort_index(); y = y.loc[X.index].to_numpy(float); groups = X.municipio.to_numpy()
        levels = sorted(set(groups))
        groupmed = {g: float(np.median(y[X.cultivo_origen.to_numpy()==g])) for g in sorted(set(X.cultivo_origen))}
        self.parametros_ = (self.columnas, self.alpha)
        if self.columnas:
            V = X[list(self.columnas)].to_numpy(float)
            mu = V.mean(axis=0); scale = V.std(axis=0); scale[scale==0] = 1.
            Z = (V-mu)/scale
            centers = {g: Z[groups==g].mean(axis=0) for g in levels}
            D = Z-np.array([centers[g] for g in groups])
            beta, intercept, solver = resolver_primal(D, y, groups, self.alpha)
            h3 = max(float(np.max(np.abs(D[groups==g].mean(axis=0)))) for g in levels)
            exigir(h3 <= 1e-12, 'Centrado municipal incorrecto')
        else:
            mu = scale = beta = np.array([]); centers = {g: np.array([]) for g in levels}
            intercept = {g: float(np.median(y[groups==g])) for g in levels}; h3 = 0.
            solver = dict(objetivo=float(.5*np.mean(np.abs(y-np.array([intercept[g] for g in groups])))),
                          primario=None, lex=[], n_resoluciones=0, max_violacion=0.)
        self.estado_ = dict(version=VERSION, columnas=list(self.columnas), alpha=self.alpha,
            ids_entrenamiento=list(X.index), media=mu.tolist(), escala=scale.tolist(),
            centros={g: v.tolist() for g, v in centers.items()}, beta=beta.tolist(),
            interceptos=intercept, mediana_grupo=groupmed, mediana_global=float(np.median(y)),
            solver=solver, max_media_D_municipio=h3)
        return self

    def estado(self):
        exigir(self.estado_ is not None and self.parametros_ == (self.columnas, self.alpha),
               'Modelo no ajustado o parámetros cambiados')
        return copy.deepcopy(self.estado_)

    def predict_with_details(self, X):
        return predecir_estado(self.estado(), X)

    def predict(self, X):
        return self.predict_with_details(X).prediccion.to_numpy()


def predecir_estado(s, X):
    exigir(s['version']==VERSION, 'Estado de otra versión')
    validar_X(X, s['columnas']); beta = np.asarray(s['beta'])
    if len(beta): Z = (X[s['columnas']].to_numpy(float)-np.asarray(s['media']))/np.asarray(s['escala'])
    out = []
    for j, (_, row) in enumerate(X.iterrows()):
        g = row.municipio
        if g in s['interceptos']:
            base = s['interceptos'][g]; source = 'municipio'
            correction = float((Z[j]-np.asarray(s['centros'][g]))@beta) if len(beta) else 0.
        elif row.cultivo_origen in s['mediana_grupo']:
            base = s['mediana_grupo'][row.cultivo_origen]; source = 'grupo'; correction = 0.
        else:
            base = s['mediana_global']; source = 'global'; correction = 0.
        out.append(dict(prediccion=float(base+correction), fuente=source,
                        nivel_municipal_o_respaldo=base, correccion_satelital=correction))
    result = pd.DataFrame(out, index=X.index)
    exigir(np.isfinite(result.prediccion).all(), 'Predicción no finita')
    return result


def clave(o):
    return (round(o['MAE'], 6), 0 if o['nombre']=='referencia_sola' else 1,
            -(o['alpha'] or 0.), 0 if o['ventana']=='jun_oct' else 1, o['nombre'])


def ajustar(X, y, q, option):
    exigir(option in OPCIONES, 'Opción no registrada')
    exigir(not set(X.index)&set(q.index), 'Solapamiento de entrenamiento y consulta')
    model = CuantilicaMunicipal(option['columnas'], option['alpha']).fit(X, y)
    d = model.predict_with_details(q)
    exigir(np.array_equal(d.fuente.to_numpy()=='municipio', q.municipio.isin(X.municipio).to_numpy()),
           'Máscara municipal no coincide')
    return model, d


def seleccionar(X, y, escenario, emitir):
    scores = []
    for option in OPCIONES:
        eligible = []; all_errors = []
        for j, split in enumerate(divisiones_internas(X, escenario)):
            tr = X.loc[list(split.entrenamiento)]; va = X.loc[list(split.validacion)]
            model, detail = ajustar(tr, y.loc[tr.index], va, option)
            error = np.abs(detail.prediccion.to_numpy()-y.loc[va.index].to_numpy())
            eligible.extend(error[np.asarray(split.elegibles)]); all_errors.extend(error)
            emitir(dict(etapa='interna', division_interna=j, opcion=option,
                estado_modelo=model.estado(), ids_validacion=list(va.index),
                ids_elegibles=[i for i,b in zip(va.index, split.elegibles) if b],
                consulta=[dict(id_parcela=i, **r.to_dict()) for i,r in detail.iterrows()],
                MAE=float(error[np.asarray(split.elegibles)].mean())))
        exigir(eligible and np.isfinite(eligible).all(), 'Opción no evaluable')
        scores.append(dict(nombre=option['nombre'], alpha=option['alpha'], ventana=option['ventana'],
                           MAE=float(np.mean(eligible)), MAE_todas=float(np.mean(all_errors)),
                           n_elegibles=len(eligible), n_validacion=len(all_errors)))
    win = min(scores, key=clave)
    return copy.deepcopy(next(o for o in OPCIONES if o['nombre']==win['nombre'])), scores
