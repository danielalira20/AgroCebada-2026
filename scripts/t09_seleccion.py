"""Selección interna T09. No ejecuta escenarios externos ni genera la entrega final."""
from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.model_selection import GroupKFold, StratifiedKFold

from scripts.t09_entradas import RAIZ, cargar_diseno
from scripts.t09_estimadores import CLIMA, crear_estimador, validar_X, validar_y


@dataclass(frozen=True)
class ParticionInterna:
    entrenamiento: tuple
    validacion: tuple
    elegibles: tuple


@dataclass
class Seleccion:
    ventana: str
    lambda_reg: float
    puntuaciones: pd.DataFrame
    por_ventana: dict
    n_ajustes: int


def _config(config):
    fija = cargar_diseno(RAIZ / 'registro/t09/diseno.json')
    if config is not None and config != fija:
        raise ValueError('Cambiar búsqueda/política requiere versionar el diseño')
    return fija


def mascara_soporte(Xtr, Xval):
    return Xval.municipio.isin(Xtr.municipio).to_numpy()


def particiones_internas(X, escenario='A', config=None):
    cfg = _config(config)
    if escenario not in ('A', 'B', 'C'):
        raise ValueError('Escenario interno fuera del diseño')
    validar_X(X, CLIMA, territorio=True)
    # Orden por ID: cambiar el orden accidental de lectura no cambia las particiones.
    X = X.sort_index()
    if escenario == 'A':
        n = X.municipio.map(X.municipio.value_counts())
        estrato = X.municipio.where(n.ge(4), 'otros')
        if estrato.value_counts().lt(4).any():
            raise ValueError('Estrato con menos de cuatro casos: revisar política, no silenciar aviso')
        split = StratifiedKFold(4, shuffle=True, random_state=cfg['escenarios']['A']['semilla'])
        divisiones = split.split(X, estrato)
        grupo = None
    else:
        c = 'celda_chirps' if escenario == 'B' else 'municipio'
        if c not in X or not X[c].map(lambda v: isinstance(v, str) and bool(v.strip())).all():
            raise ValueError('Grupo espacial/municipal ausente')
        grupo = X[c]
        if grupo.nunique() < 4:
            raise ValueError('Se requieren cuatro grupos distintos para selección interna')
        divisiones = GroupKFold(4, shuffle=False).split(X, groups=grupo)
    result = []
    vistos = []
    for ia, ib in divisiones:
        a, b = X.iloc[ia], X.iloc[ib]
        if grupo is not None and set(grupo.iloc[ia]) & set(grupo.iloc[ib]):
            raise ValueError('Grupos compartidos entre entrenamiento y validación')
        elegibles = np.ones(len(b), dtype=bool) if escenario == 'C' else mascara_soporte(a, b)
        if not elegibles.any():
            raise ValueError('Validación interna sin casos elegibles; no cambiar de criterio')
        vistos.extend(b.index)
        result.append(ParticionInterna(tuple(a.index), tuple(b.index), tuple(elegibles)))
    if len(vistos) != len(X) or set(vistos) != set(X.index):
        raise ValueError('Validaciones internas incompletas o duplicadas')
    return result


def ajustar_particion(X, y, particion, procedimiento, ventana, lambda_reg):
    """Una opción aprende sólo con entrenamiento; y_validación no se pasa a fit."""
    validar_X(X, CLIMA, territorio=True)
    validar_y(X, y)
    a, b = set(particion.entrenamiento), set(particion.validacion)
    if a & b or a | b != set(X.index) or len(a) != len(particion.entrenamiento) or len(b) != len(particion.validacion):
        raise ValueError('IDs internos no disjuntos/completos')
    if (len(particion.elegibles) != len(b) or not any(particion.elegibles)
            or np.asarray(particion.elegibles).dtype.kind != 'b'):
        raise ValueError('Máscara interna inválida')
    tr, va = X.loc[list(particion.entrenamiento)], X.loc[list(particion.validacion)]
    modelo = crear_estimador(procedimiento, ventana, lambda_reg).fit(tr, y.loc[tr.index])
    return modelo, pd.Series(modelo.predict(va), index=va.index, name='prediccion')


def _clave(fila):
    return round(fila['MAE'], 6), -fila['lambda_reg'], 0 if fila['ventana'] == 'jun_oct' else 1


def elegir_configuracion(X, y, procedimiento='TC', escenario='A', config=None):
    cfg = _config(config)
    if procedimiento not in ('CL', 'TC', 'R'):
        raise ValueError('La referencia exacta no tiene búsqueda climática')
    validar_X(X, CLIMA, territorio=True)
    validar_y(X, y)
    partes = particiones_internas(X, escenario, cfg)
    filas = []
    for ventana in cfg['ventanas']:
        for intensidad in cfg['regularizacion']['lambda']:
            errores, errores_todos = [], []
            for parte in partes:
                _, p = ajustar_particion(X, y, parte, procedimiento, ventana, intensidad)
                e = np.abs(p.to_numpy() - y.loc[p.index].to_numpy())
                errores.append(e[np.asarray(parte.elegibles, dtype=bool)])
                errores_todos.append(e)
            elegido = np.concatenate(errores)
            todos = np.concatenate(errores_todos)
            filas.append({'procedimiento': procedimiento, 'escenario': escenario,
                          'ventana': ventana, 'lambda_reg': float(intensidad),
                          'MAE': float(elegido.mean()), 'MAE_todas': float(todos.mean()),
                          'n_elegibles': len(elegido), 'n_validacion': len(todos), 'n_ajustes': len(partes)})
    if len(filas) != 8 or not np.isfinite([r['MAE'] for r in filas]).all():
        raise ValueError('Búsqueda incompleta o puntuación no finita; no saltar candidatos')
    ganador = min(filas, key=_clave)
    por_ventana = {w: min([r for r in filas if r['ventana'] == w], key=_clave).copy()
                   for w in cfg['ventanas']}
    return Seleccion(ganador['ventana'], ganador['lambda_reg'], pd.DataFrame(filas),
                     por_ventana, sum(r['n_ajustes'] for r in filas))
