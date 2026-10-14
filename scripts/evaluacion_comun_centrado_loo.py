"""v3: residuo y centro usan el mismo pool sin fila. No ejecuta T15 completo."""
import argparse
import copy
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

from scripts import evaluacion_comun_centrado as v2
from scripts import evaluacion_comun_contrato as contrato
from scripts.evaluacion_comun_modelo import (
    LAMBDA, NULLABLE, validar_X, validar_y, medias, residuos_loo,
    divisiones_internas, clave_opcion, preparar_contexto,
)

VERSION = 'comun-centrado-loo-v3'
DISENO = 'registro/evaluacion_comun/procedimiento_centrado_loo_v3.json'
DISENO_SHA = '95ee8be41a60f05f797b8466c741713efcb261efb4bcdbf28af66f7895dcf7a2'
RAIZ = contrato.RAIZ
exigir = contrato.exigir


def cargar_entradas(raiz=RAIZ):
    raiz = Path(raiz)
    exigir(contrato.sha(raiz / DISENO) == DISENO_SHA, 'Diseño LOO modificado: versionar y revisar')
    cfg = json.loads((raiz / DISENO).read_text())
    exigir(cfg['schema'] == 'agrocebada_comun_centrado_loo_v3' and cfg['version'] == VERSION,
           'Diseño LOO incompatible')
    e = v2.cargar_entradas(raiz)
    exigir(cfg['fuentes_sha256'] == e['config']['fuentes_sha256'], 'Fuentes v3 distintas del antecedente')
    return {**e, 'config': cfg, 'sha_procedimiento': DISENO_SHA}


def validar_experimento(exp, entradas):
    exigir(entradas['config']['version'] == VERSION and entradas.get('sha_procedimiento') == DISENO_SHA,
           'Entradas no identificadas para v3')
    exigir(exp.get('schema') == 'experimento_comun_centrado_loo_v3' and
           exp.get('sha_procedimiento') == DISENO_SHA, 'Experimento de otra versión')
    exigir(exp.get('estado') == 'registrado_antes_de_ejecutar', 'Propuesta pendiente: no ejecutar T15')
    exigir(all(exp.get(k) for k in ['id', 'responsable', 'hipotesis']), 'Falta identidad/hipótesis')
    names = {p['candidato'] for p in exp['procedimientos']} | {'media_mun__resp_grupo'}
    for comparison in exp.get('contrastes_planificados', []):
        exigir(comparison.get('candidato') in names and comparison.get('frente_a') in names and
               comparison['candidato'] != comparison['frente_a'], 'Contraste de candidato ajeno o versión anterior')
    return {**contrato.validar_opciones_y_presupuesto(exp, entradas),
            'version': VERSION, 'sha_procedimiento': DISENO_SHA}


def pools_sin_fila(X):
    """IDs del municipio, grupo o global restantes; nunca una resta de sumas."""
    validar_X(X, [])
    exigir(len(X) >= 2, 'Centro LOO requiere al menos dos filas')
    ordered = X.sort_index()
    municipal = {k: tuple(g.index) for k, g in ordered.groupby('municipio')}
    groups = {k: tuple(g.index) for k, g in ordered.groupby('cultivo_origen')}
    all_ids = tuple(ordered.index)
    result = {}
    for pid, row in X.iterrows():
        for source, ids in [('municipio', municipal[row.municipio]),
                            ('grupo', groups[row.cultivo_origen]), ('global', all_ids)]:
            remaining = tuple(i for i in ids if i != pid)
            if remaining:
                result[pid] = (source, remaining)
                break
    exigir(len(result) == len(X), 'Centro LOO sin respaldo')
    return result


class CorreccionComunCentradaLOO(v2.CorreccionComunCentrada):
    """Mantiene predict v2; alinea la matriz del fit con la referencia LOO."""

    def fit(self, X, y):
        self._limpiar()
        try:
            exigir(len(self.columnas) == len(set(self.columnas)), 'Columnas duplicadas')
            exigir(not isinstance(self.lambda_reg, bool) and
                   ((not self.columnas and self.lambda_reg is None) or
                    (bool(self.columnas) and self.lambda_reg in LAMBDA)), 'Parámetros fuera del procedimiento')
            validar_X(X, self.columnas)
            validar_y(X, y)
            exigir(pd.api.types.is_numeric_dtype(y) and not pd.api.types.is_bool_dtype(y),
                   'Objetivo numérico requerido')
            X = X.sort_index().copy()
            y = y.loc[X.index].copy()
            self.ids_entrenamiento_ = tuple(X.index)
            self.mun_, self.grupo_, self.global_ = medias(X, y)
            self.n_, self.alpha_, self.ridge_ = len(X), None, None
            self.nombres_ = list(self.columnas)
            if self.columnas:
                pools = pools_sin_fila(X)
                self.residuos_ = residuos_loo(X, y)
                a = self._valores(X, True)
                if NULLABLE in self.columnas:
                    self.nombres_.append(NULLABLE + '__faltante')
                self.escalador_ = StandardScaler().fit(a)
                z = self.escalador_.transform(a)
                frame = pd.DataFrame(z, index=X.index, columns=self.nombres_)
                self.centros_mun_ = frame.groupby(X.municipio).mean().copy()
                self.centros_grupo_ = frame.groupby(X.cultivo_origen).mean().copy()
                self.centro_global_ = frame.mean().to_numpy().copy()
                self.n_mun_ = X.municipio.value_counts().sort_index().copy()
                self.n_grupo_ = X.cultivo_origen.value_counts().sort_index().copy()
                self.pools_sin_fila_ = copy.deepcopy(pools)
                positions = {pid: i for i, pid in enumerate(X.index)}
                self.centros_sin_fila_ = pd.DataFrame(
                    [z[[positions[j] for j in pools[pid][1]]].mean(0) for pid in X.index],
                    index=X.index, columns=self.nombres_,
                )
                d = z - self.centros_sin_fila_.to_numpy()
                self.alpha_ = self.n_ * float(self.lambda_reg)
                self.ridge_ = Ridge(alpha=self.alpha_, fit_intercept=False, solver='svd').fit(d, self.residuos_)
                exigir(np.isfinite(self.ridge_.coef_).all(), 'Coeficientes no finitos')
            self.parametros_fit_ = (tuple(self.columnas), self.lambda_reg)
            self.ajustado_ = True
        except Exception:
            self._limpiar()
            raise
        return self

    def estado(self):
        e = copy.deepcopy(super().estado())
        e.update(version=VERSION, sha_procedimiento=DISENO_SHA,
                 familia='referencia_mas_Ridge_residuo_LOO_centro_LOO_coherente',
                 politica_centro_fit='mismo_pool_sin_fila_que_referencia_residual',
                 politica_centro_predict='municipio_grupo_global_entrenamiento_completo')
        if self.ridge_ is not None:
            e['centros_Z_sin_fila'] = {pid: row.tolist() for pid, row in
                                      zip(self.centros_sin_fila_.index, self.centros_sin_fila_.to_numpy())}
            e['pools_sin_fila'] = {pid: {'fuente': source, 'n': len(ids), 'ids': list(ids)}
                                  for pid, (source, ids) in self.pools_sin_fila_.items()}
        return e


def seleccionar(X, y, opciones, escenario='A'):
    validar_X(X, [])
    validar_y(X, y)
    exigir(1 <= len(opciones) <= 8, 'Máximo ocho opciones con variables')
    names = {o['nombre'] for o in opciones}
    exigir(len(names) == len(opciones) and 'referencia_sola' not in names, 'Nombre duplicado/reservado')
    divisions = divisiones_internas(X, escenario)
    alternatives = [dict(nombre='referencia_sola', columnas=[], lambda_reg=None, ventana='estatica'), *opciones]
    scores = []
    for option in alternatives:
        errors, all_errors = [], []
        for split in divisions:
            tr, va = X.loc[list(split.entrenamiento)], X.loc[list(split.validacion)]
            model = CorreccionComunCentradaLOO(option['columnas'], option['lambda_reg']).fit(tr, y.loc[tr.index])
            err = np.abs(model.predict(va) - y.loc[va.index].to_numpy())
            errors.extend(err[np.asarray(split.elegibles)])
            all_errors.extend(err)
        exigir(errors and np.isfinite(errors).all(), 'Opción no evaluable; no saltarla')
        scores.append(dict(nombre=option['nombre'], ventana=option['ventana'], lambda_reg=option['lambda_reg'],
                           referencia_sola=not option['columnas'], MAE=float(np.mean(errors)),
                           MAE_todas=float(np.mean(all_errors)), n_elegibles=len(errors),
                           n_validacion=len(all_errors), n_ajustes=len(divisions), version=VERSION))
    winner = min(scores, key=clave_opcion)
    selected = next(o for o in alternatives if o['nombre'] == winner['nombre'])
    return dict(elegida=selected.copy(), puntuaciones=scores,
                n_ajustes=len(alternatives) * len(divisions), version=VERSION)


def seleccionar_registrado(entradas, experimento, candidato, escenario, repeticion, particion):
    validar_experimento(experimento, entradas)
    procedures = [p for p in experimento['procedimientos'] if p['candidato'] == candidato]
    exigir(len(procedures) == 1, 'Candidato no registrado')
    options = [dict(o, nombre=f"{o['ventana']}__lambda_{o['lambda_reg']:g}") for o in procedures[0]['opciones']]
    tr, y, te = preparar_contexto(entradas, escenario, repeticion, particion)
    choice = seleccionar(tr, y, options, escenario)
    selected = choice['elegida']
    model = CorreccionComunCentradaLOO(selected['columnas'], selected['lambda_reg']).fit(tr, y)
    prediction, source = model.predict_con_fuente(te)
    return dict(seleccion=choice, modelo=model, ids_evaluacion=tuple(te.index),
                prediccion=prediction, fuente=source, ids_entrenamiento=tuple(tr.index),
                version=VERSION, sha_procedimiento=DISENO_SHA)


def frecuencia_referencia_sola(filas, contextos_esperados_por_escenario=25):
    """Resumen de selecciones reales; prohíbe contar varias veces el mismo fit."""
    exigir(isinstance(contextos_esperados_por_escenario, int) and
           not isinstance(contextos_esperados_por_escenario, bool) and
           1 <= contextos_esperados_por_escenario <= 25, 'Denominador esperado inválido')
    exigir(bool(filas), 'No hay selecciones: no informar frecuencia cero')
    seen, groups = set(), {}
    for r in filas:
        exigir(r.get('version') == VERSION, 'Selección de otra versión')
        exigir(isinstance(r.get('candidato'), str) and r['candidato'].strip(), 'Candidato vacío')
        exigir(r.get('escenario') in ['A', 'B'], 'Escenario no admitido')
        rep, fold = r.get('repeticion'), r.get('particion')
        exigir(type(rep) is int and 1 <= rep <= 5 and type(fold) is int and 0 <= fold <= 4,
               'Contexto de selección inválido')
        option = r.get('nombre_opcion')
        exigir(isinstance(option, str) and option, 'Opción no documentada')
        only = r.get('referencia_sola')
        exigir(type(only) is bool and only == (option == 'referencia_sola'), 'Bandera de referencia incoherente')
        exigir((only and r.get('lambda_reg') is None) or
               (not only and type(r.get('lambda_reg')) in [int, float] and r['lambda_reg'] in LAMBDA),
               'Regularización incoherente con la selección')
        key = (r['candidato'], r['escenario'], rep, fold)
        exigir(key not in seen, 'Contexto de selección duplicado')
        seen.add(key)
        groups.setdefault(key[:2], []).append(only)
    out = []
    for (candidate, scenario), values in sorted(groups.items()):
        n = len(values)
        exigir(n <= contextos_esperados_por_escenario, 'Más selecciones que contextos esperados')
        out.append(dict(candidato=candidate, escenario=scenario, version=VERSION,
                        n_contextos=n, n_esperados=contextos_esperados_por_escenario,
                        n_referencia_sola=sum(values), n_con_correccion=n-sum(values),
                        fraccion_referencia_sola=sum(values)/n,
                        estado='completo' if n == contextos_esperados_por_escenario else 'parcial'))
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--raiz', type=Path, default=RAIZ)
    p.add_argument('--experimento', type=Path)
    args = p.parse_args()
    e = cargar_entradas(args.raiz)
    result = dict(version=VERSION, sha_procedimiento=DISENO_SHA,
                  etiquetadas=len(e['conocidos']), reservadas=len(e['reservados']),
                  modelos_ajustados=0, evaluacion_T15_completa=False)
    if args.experimento:
        result['experimento'] = validar_experimento(json.loads(args.experimento.read_text()), e)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
