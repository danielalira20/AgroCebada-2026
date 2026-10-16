"""Selección v3 con traza por ajuste; no contiene una evaluación completa T15."""
import copy
import hashlib
import json
import warnings

import numpy as np

from scripts import evaluacion_comun_centrado_loo as v3
from scripts.evaluacion_comun_modelo import divisiones_internas, clave_opcion, validar_X, validar_y
from scripts.evaluacion_comun_contrato import exigir


def huella(valor):
    return hashlib.sha256(json.dumps(valor, sort_keys=True, ensure_ascii=False,
                                    allow_nan=False, separators=(',', ':')).encode()).hexdigest()


class ErrorAjuste(ValueError):
    def __init__(self, mensaje, traza):
        super().__init__(mensaje)
        self.traza = copy.deepcopy(traza)


def ajustar_y_trazar(entrenamiento, y_entrenamiento, validacion, opcion, elegibles):
    """No recibe etiquetas de validación; éstas sólo intervienen al puntuar fuera."""
    exigir(not set(entrenamiento.index) & set(validacion.index), 'IDs solapados en ajuste')
    exigir(len(elegibles) == len(validacion) and all(type(v) is bool for v in elegibles),
           'Máscara elegible inválida')
    traza = dict(opcion=opcion['nombre'], estado='iniciado',
                 ids_entrenamiento=sorted(entrenamiento.index),
                 ids_validacion=list(validacion.index),
                 ids_elegibles=[i for i, v in zip(validacion.index, elegibles) if v],
                 n_entrenamiento=len(entrenamiento), n_validacion=len(validacion),
                 n_elegibles=sum(elegibles), lambda_reg=opcion['lambda_reg'],
                 columnas=list(opcion['columnas']), ventana=opcion['ventana'],
                 version=v3.VERSION)
    with warnings.catch_warnings(record=True) as avisos:
        warnings.simplefilter('always')
        try:
            modelo = v3.CorreccionComunCentradaLOO(opcion['columnas'], opcion['lambda_reg'])
            modelo.fit(entrenamiento, y_entrenamiento)
            detalles = modelo.predict_with_details(validacion)
            counts = entrenamiento.municipio.value_counts()
            n_local = [int(counts.get(m, 0)) for m in validacion.municipio]
            exigir(tuple(detalles.index) == tuple(validacion.index), 'Orden de predicción distinto')
            exigir(np.array_equal(detalles.fuente.to_numpy() == 'municipio', np.asarray(elegibles)),
                   'Elegibles distintos de referencia municipal')
            estado = modelo.estado()
            fuentes = detalles.fuente.value_counts()
            pools = estado.get('pools_sin_fila', {})
            traza.update(estado='correcto', alpha=estado['alpha'],
                         referencia_sola=not opcion['columnas'],
                         n_grupos_municipio=int(counts.size),
                         n_grupos_celda=int(entrenamiento.celda_chirps.nunique()),
                         n_singleton_entrenamiento=int((counts == 1).sum()),
                         n_validacion_referencia_una_etiqueta=sum(n == 1 for n in n_local),
                         n_validacion_sin_municipio=sum(n == 0 for n in n_local),
                         fuentes_referencia={k: int(fuentes.get(k, 0)) for k in ['municipio', 'grupo', 'global']},
                         fuentes_centro_LOO={k: sum(p['fuente'] == k for p in pools.values())
                                            for k in ['municipio', 'grupo', 'global']},
                         estado_modelo_sha256=huella(estado),
                         mediana_pendiente=estado.get('mediana_pendiente'),
                         media_abs_correccion=float(detalles.correccion.abs().mean()),
                         max_abs_correccion=float(detalles.correccion.abs().max()),
                         advertencias=[dict(categoria=w.category.__name__, mensaje=str(w.message)) for w in avisos])
            # No silenciar una advertencia y seleccionar como si el ajuste fuera correcto.
            exigir(not avisos, 'Ajuste con advertencias: revisar antes de evaluar')
        except Exception as exc:
            traza.update(estado='fallido', error_tipo=type(exc).__name__, error=str(exc),
                         advertencias=[dict(categoria=w.category.__name__, mensaje=str(w.message)) for w in avisos])
            raise ErrorAjuste('Ajuste detenido; no sustituir por referencia: ' + str(exc), traza) from exc
    return modelo, detalles, traza


def seleccionar_con_traza(X, y, opciones, escenario='A', *, al_ajuste=None):
    """Igual matemática y desempate que v3; añade IDs/conteos/estado por fit."""
    validar_X(X, [])
    validar_y(X, y)
    exigir(escenario in ['A', 'B'], 'Sólo escenarios A/B del contrato')
    exigir(1 <= len(opciones) <= 8, 'Máximo ocho opciones por procedimiento')
    nombres = {o['nombre'] for o in opciones}
    exigir(len(nombres) == len(opciones) and 'referencia_sola' not in nombres, 'Nombre duplicado/reservado')
    divisiones = divisiones_internas(X, escenario)
    alternativas = [dict(nombre='referencia_sola', columnas=[], lambda_reg=None, ventana='estatica'), *opciones]
    puntuaciones, trazas = [], []
    for opcion in alternativas:
        errores, todos = [], []
        for numero, division in enumerate(divisiones):
            tr, va = X.loc[list(division.entrenamiento)], X.loc[list(division.validacion)]
            try:
                _, detalles, traza = ajustar_y_trazar(tr, y.loc[tr.index], va, opcion, division.elegibles)
            except ErrorAjuste as exc:
                exc.traza.update(escenario=escenario, division_interna=numero)
                if al_ajuste is not None:al_ajuste(copy.deepcopy(exc.traza))
                raise
            error = np.abs(detalles.prediccion.to_numpy() - y.loc[va.index].to_numpy())
            mascara = np.asarray(division.elegibles)
            errores.extend(error[mascara])
            todos.extend(error)
            traza.update(escenario=escenario, division_interna=numero,
                         MAE=float(error[mascara].mean()), MAE_todas=float(error.mean()))
            trazas.append(traza)
            if al_ajuste is not None:al_ajuste(copy.deepcopy(traza))
        exigir(errores and np.isfinite(errores).all(), 'Opción no evaluable: no omitir')
        puntuaciones.append(dict(nombre=opcion['nombre'], ventana=opcion['ventana'],
                                  lambda_reg=opcion['lambda_reg'], referencia_sola=not opcion['columnas'],
                                  MAE=float(np.mean(errores)), MAE_todas=float(np.mean(todos)),
                                  n_elegibles=len(errores), n_validacion=len(todos),
                                  n_ajustes=len(divisiones), version=v3.VERSION))
    ganadora = min(puntuaciones, key=clave_opcion)
    return dict(elegida=copy.deepcopy(next(o for o in alternativas if o['nombre'] == ganadora['nombre'])),
                puntuaciones=puntuaciones, n_ajustes=len(trazas), version=v3.VERSION, trazas=trazas)
