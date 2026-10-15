"""Revisión reproducible de particiones y referencias históricas; cero ajustes de modelos."""
import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import json
import math
from pathlib import Path
import statistics
import warnings

import pandas as pd
import pyproj
from sklearn.model_selection import StratifiedKFold

from scripts.evaluacion_comun_modelo import divisiones_internas, clave_opcion


ROOT = Path(__file__).resolve().parents[1]


def read(path):
    with Path(path).open(encoding='utf-8-sig', newline='') as f: return list(csv.DictReader(f))


def require(value, message):
    if not value: raise ValueError(message)


def inspect(root):
    root = Path(root)
    table = pd.DataFrame(read(root/'registro/t07/tabla_comun.csv')).set_index('id_parcela').sort_index()
    parts = read(root/'registro/t03/particiones.csv')
    known = sorted({r['ID_POLIGONO'] for r in parts})
    require(len(known) == 138, 'Particiones sin 138 IDs')
    table = table.drop(columns=['rendimiento_t_ha'])
    trace = []
    for scenario, field in [('A', 'particion_principal'), ('B', 'particion_espacial')]:
        for rep in range(1, 6):
            pp = [r for r in parts if int(r['repeticion']) == rep]
            for fold in range(5):
                train = sorted(r['ID_POLIGONO'] for r in pp if int(r[field]) != fold)
                x = table.loc[train].copy()
                x['celda_chirps'] = pd.Series({r['ID_POLIGONO']: r['celda_chirps'] for r in pp})
                actual = divisiones_internas(x, scenario)
                methods = [('comun_v3', actual)]
                if scenario == 'B':
                    counts = x.municipio.value_counts()
                    strata = x.municipio.where(x.municipio.map(counts) >= 4, 'otros')
                    with warnings.catch_warnings():
                        warnings.simplefilter('ignore', UserWarning)
                        old = list(StratifiedKFold(4, shuffle=True, random_state=0).split(x, strata))
                    methods.append(('contraste_estratificado', [
                        (tuple(x.iloc[a].index), tuple(x.iloc[b].index)) for a, b in old]))
                for method, splits in methods:
                    seen = []
                    for inner, split in enumerate(splits):
                        a, b = (list(split.entrenamiento), list(split.validacion)) if method == 'comun_v3' else map(list, split)
                        require(not set(a) & set(b) and set(a) | set(b) == set(train), 'Interna no disjunta/completa')
                        seen.extend(b)
                        municipal = Counter(x.loc[a, 'municipio'])
                        nlocal = [municipal[m] for m in x.loc[b, 'municipio']]
                        cell_cross = len(set(x.loc[a, 'celda_chirps']) & set(x.loc[b, 'celda_chirps']))
                        if scenario == 'B' and method == 'comun_v3': require(cell_cross == 0, 'Celda cruzada')
                        trace.append(dict(escenario=scenario, metodo=method, repeticion=rep,
                            particion_externa=fold, particion_interna=inner,
                            n_parcelas_entrenamiento=len(a), n_parcelas_validacion=len(b),
                            n_parcelas_excluidas_respaldo=sum(n == 0 for n in nlocal),
                            n_parcelas_referencia_municipal=sum(n > 0 for n in nlocal),
                            n_parcelas_referencia_unica=sum(n == 1 for n in nlocal),
                            n_celdas_compartidas=cell_cross))
                    require(len(seen) == len(set(seen)) == len(train), 'Validación interna repetida/incompleta')
    summary = []
    for scenario, method in [('A', 'comun_v3'), ('B', 'comun_v3'), ('B', 'contraste_estratificado')]:
        picked = [r for r in trace if r['escenario'] == scenario and r['metodo'] == method]
        summary.append(dict(escenario=scenario, metodo=method, ajustes_internos=len(picked),
            **{k: sum(r[k] for r in picked) for k in ['n_parcelas_validacion', 'n_parcelas_excluidas_respaldo',
                   'n_parcelas_referencia_municipal', 'n_parcelas_referencia_unica']}))
    historical = read(root/'registro/t03/predicciones_oof_referencias_media_mun__resp_grupo.csv')
    singleton = {'A': [], 'B': []}
    levels = {}
    for scenario, field in [('A', 'particion_principal'), ('B', 'particion_espacial')]:
        records = [r for r in historical if r['escenario'] == scenario and r['fuente'] == 'municipio']
        by_id = defaultdict(list)
        for row in records: by_id[row['ID_POLIGONO']].append(abs(float(row['prediccion'])-float(row['real'])))
        levels[scenario] = dict(n_parcelas=len(by_id), n_registros=len(records),
            repeticiones_validas=dict(Counter(len(v) for v in by_id.values())),
            MAE_por_parcela=statistics.fmean(statistics.fmean(v) for v in by_id.values()),
            MAE_por_registro=statistics.fmean(v for values in by_id.values() for v in values))
        for row in records:
            rep, fold = int(row['repeticion']), int(row['particion'])
            tr = [p['ID_POLIGONO'] for p in parts if int(p['repeticion']) == rep and int(p[field]) != fold]
            municipal = Counter(table.loc[tr, 'municipio'])
            if municipal[table.loc[row['ID_POLIGONO'], 'municipio']] == 1:
                singleton[scenario].append(row)
    catalogue = {r['id_parcela']: r for r in read(root/'analisis/auditoria_catalogo_y_etiquetas/tablas/catalogo_parcelas.csv')}
    a, b = catalogue['AGC_120'], catalogue['AGC_048']
    distance = pyproj.Geod(ellps='WGS84').inv(float(a['centroide_lon']), float(a['centroide_lat']),
                                          float(b['centroide_lon']), float(b['centroide_lat']))[2]
    # No se generan predicciones: se consulta la referencia ya publicada de T08.
    reserved = [r for r in read(root/'registro/t03/predicciones_59_referencias.csv')
                if r['ID_POLIGONO'] == 'AGC_120' and r['candidato'] == 'media_mun__resp_grupo']
    require(len(reserved) == 1, 'Referencia reservada ambigua')
    x = table.loc[known].copy();x['celda_chirps'] = pd.Series({r['ID_POLIGONO']: r['celda_chirps'] for r in parts})
    c_splits = divisiones_internas(x, 'C')
    c_disjoint = all(not set(x.loc[list(s.entrenamiento), 'municipio']) &
                     set(x.loc[list(s.validacion), 'municipio']) for s in c_splits)
    reference = dict(MAE=.2, referencia_sola=True, lambda_reg=None, ventana='estatica', nombre='referencia_sola')
    ridge = dict(MAE=.2, referencia_sola=False, lambda_reg=10, ventana='jun_oct', nombre='ridge')
    local120 = next(r for r in read(root/'registro/diagnostico/aplicabilidad59/perfil_59.csv') if r['id_parcela'] == 'AGC_120')
    require(local120['conocida_local_mas_cercana_orilla'] == 'AGC_048', 'Referencia local 120 distinta')
    result = dict(PR=22, commit_revisado='f73f376d81210b7b78e97532759d54b309f7a02f',
        PR21_base='4afabf081a341f3321fcd58a211d18b43ee5a3b4',
        particiones_internas=summary, niveles_referencia_historica=levels,
        n_referencias_unicas_externas={k: len(v) for k, v in singleton.items()},
        MAE_referencia_unica_B=statistics.fmean(abs(float(r['prediccion'])-float(r['real'])) for r in singleton['B']),
        AGC120_referencia_publicada=reserved[0]['prediccion'], AGC120_AGC048_distancia_centros_m=distance,
        AGC120_AGC048_distancia_orillas_m_publicada_C=float(local120['distancia_orillas_municipio_m']),
        C_codigo_agrupa_municipios=c_disjoint, referencia_sola_gana_empate=clave_opcion(reference)<clave_opcion(ridge),
        modelos_ajustados=0, nuevas_predicciones59=0,
        limites='No reproduce nuevos ΔMAE/IC de modelos del repo privado de Migue ni aprueba el PR en GitHub.')
    return result, trace


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--raiz', type=Path, default=ROOT);p.add_argument('--salida', type=Path, required=True)
    a = p.parse_args()
    require(not a.salida.exists(), 'Destino existente')
    result, trace = inspect(a.raiz)
    a.salida.mkdir(parents=True)
    with (a.salida/'particiones_internas.csv').open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=list(trace[0]), lineterminator='\n');writer.writeheader();writer.writerows(trace)
    sources = ['scripts/evaluacion_comun_modelo.py', 'scripts/evaluacion_comun_centrado_loo.py',
               'registro/t03/particiones.csv', 'registro/t03/predicciones_oof_referencias_media_mun__resp_grupo.csv',
               'registro/t03/predicciones_59_referencias.csv', 'registro/t07/tabla_comun.csv',
               'registro/diagnostico/aplicabilidad59/perfil_59.csv']
    result['fuentes_sha256'] = {s: hashlib.sha256((a.raiz/s).read_bytes()).hexdigest() for s in sources}
    (a.salida/'verificacion.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__': main()
