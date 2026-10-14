"""Preflight T09; valida insumos reales sin ajustar ni evaluar estimadores."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from scripts.t07_fichas_atributos import leer_contrato, verificar
from scripts.t09_diagnostico_atributos import validar_tabla
from scripts.t09_estimadores import CLIMA, METADATOS, OBJETIVO, validar_X, validar_y

RAIZ = Path(__file__).resolve().parents[1]
DISENO_SHA256 = '1072e4196df68359fa3728e504f23ec28dd94b637715854a6635d36d4478081f'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def cargar_diseno(path):
    if sha(path) != DISENO_SHA256:
        raise ValueError('Diseño T09 cambiado: versionar y revisar antes de ejecutar')
    return json.loads(Path(path).read_text(encoding='utf-8'))


def validar_particiones(p, X):
    columnas = ['ID_POLIGONO', 'repeticion', 'semilla', 'particion_principal',
                'particion_espacial', 'celda_chirps', 'municipio', 'grupo_registro']
    if list(p.columns) != columnas or len(p) != 690 or p.isna().any().any():
        raise ValueError('Contrato de particiones T03 incompleto')
    if p[['ID_POLIGONO', 'repeticion']].duplicated().any():
        raise ValueError('Particiones duplicadas por ID/repetición')
    if set(p.repeticion) != {1, 2, 3, 4, 5} or set(p.ID_POLIGONO) != set(X.index):
        raise ValueError('IDs o repeticiones T03 incompatibles; nunca incluir reservadas')
    for _, g in p.groupby('ID_POLIGONO'):
        if g[['celda_chirps', 'municipio', 'grupo_registro']].nunique().ne(1).any():
            raise ValueError('Metadatos cambian entre repeticiones T03')
    if not p.municipio.eq(p.ID_POLIGONO.map(X.municipio)).all():
        raise ValueError('Municipio T03 distinto de T07')
    if not p.grupo_registro.eq(p.ID_POLIGONO.map(X.cultivo_origen)).all():
        raise ValueError('Grupo T03 distinto de T07')
    for _, g in p.groupby('repeticion'):
        for c in ['particion_principal', 'particion_espacial']:
            if set(g[c]) != {0, 1, 2, 3, 4}:
                raise ValueError('Se requieren cinco particiones externas T03')
        if g.groupby('celda_chirps').particion_espacial.nunique().ne(1).any():
            raise ValueError('Celda dividida en particiones externas espaciales')


def cargar_entradas(raiz=RAIZ):
    raiz = Path(raiz)
    config = cargar_diseno(raiz / 'registro/t09/diseno.json')
    # Identidad de insumos y procedencia congelada; una modificación no se adopta en silencio.
    for n, h in config['fuentes_sha256'].items():
        path = raiz / n
        if not path.is_file() or sha(path) != h:
            raise ValueError(f'Insumo/procedencia T09 distinto del diseño: {n}')
    dic, roles, _ = leer_contrato(raiz)
    verificar(raiz / 'registro/t07_fichas', raiz)
    tabla = pd.read_csv(raiz / 'registro/t07/tabla_comun.csv')
    validar_tabla(tabla, dic)
    por_col = {r['columna']: r for r in dic}
    for c in CLIMA:
        unidad = 'mm' if c.startswith('prec_') else 'grados Celsius'
        if (por_col[c]['unidad'] != unidad or por_col[c]['funcion'] != 'predictor_candidato'):
            raise ValueError(f'Unidad/rol climático incompatibles: {c}')
    if roles['ventanas'] != {w: {k: v for k, v in spec.items() if k != 'columnas'}
                             for w, spec in config['ventanas'].items()}:
        raise ValueError('Calendario T07 distinto del diseño T09')
    tabla = tabla.set_index('id_parcela', drop=False).sort_index()
    conocidas = tabla.conjunto_origen.eq('ENTRENAMIENTO')
    cols = [*METADATOS, *CLIMA]
    X, y = tabla.loc[conocidas, cols].copy(), tabla.loc[conocidas, OBJETIVO].copy()
    reservadas = tabla.loc[~conocidas, cols].copy()
    p = pd.read_csv(raiz / 'registro/t03/particiones.csv')
    validar_particiones(p, X)
    celdas = p.drop_duplicates('ID_POLIGONO').set_index('ID_POLIGONO').celda_chirps
    X['celda_chirps'] = X.index.map(celdas)
    validar_X(X, CLIMA, territorio=True)
    validar_y(X, y)
    validar_X(reservadas, CLIMA, territorio=True)
    return {'X': X, 'y': y, 'reservadas': reservadas, 'particiones': p,
            'configuracion': config, 'sha_diseno': DISENO_SHA256}


def contexto_externo(entradas, escenario, repeticion=1, particion=0):
    """Sólo separa por IDs congelados; no ajusta modelos ni calcula métricas."""
    X, y, p = entradas['X'], entradas['y'], entradas['particiones']
    if escenario in ('A', 'B'):
        col = 'particion_principal' if escenario == 'A' else 'particion_espacial'
        fila = p[p.repeticion.eq(repeticion)]
        if repeticion not in range(1, 6) or particion not in range(5):
            raise ValueError('Contexto externo fuera de T03')
        ids = sorted(fila.loc[fila[col].eq(particion), 'ID_POLIGONO'])
    elif escenario == 'C':
        municipios = sorted(X.municipio.unique())
        if repeticion != 1 or particion not in range(len(municipios)):
            raise ValueError('Municipio excluido fuera de T09')
        ids = sorted(X.index[X.municipio.eq(municipios[particion])])
    else:
        raise ValueError('Escenario fuera del diseño')
    te = X.loc[ids].copy()
    tr = X.loc[~X.index.isin(ids)].copy()
    return tr, y.loc[tr.index].copy(), te, y.loc[te.index].copy()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--raiz', type=Path, default=RAIZ)
    args = parser.parse_args()
    e = cargar_entradas(args.raiz)
    print(json.dumps({'resultado': 'aprobado', 'etiquetadas': len(e['X']),
                      'reservadas': len(e['reservadas']), 'particiones': len(e['particiones']),
                      'sha_diseno': e['sha_diseno'], 'modelos_ajustados': 0}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
