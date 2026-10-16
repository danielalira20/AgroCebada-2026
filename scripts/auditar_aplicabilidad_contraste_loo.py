"""Auditor separado con statistics/cdist; no importa el productor ni modelos."""
import argparse
from collections import defaultdict
import csv
import hashlib
import json
import math
from pathlib import Path
import statistics

import numpy as np
from scipy.spatial.distance import cdist


def read(path):
    with Path(path).open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def digest(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def tolerance(col):
    if col.startswith('prec_'): return 1e-6
    if col.startswith(('tmin_', 'tmax_')): return 1e-8
    if col == 'elevacion_media_m': return 1e-6
    if col == 'pendiente_media_t10_grados': return 1e-8
    if col == 'area_ha_origen': return 1e-10
    if 'dias_' in col or 'dia_inicio' in col: return 0.
    return 1e-8 if 'integral' in col else 1e-9


def audit(root, output, detail):
    root, output, detail = map(Path, (root, output, detail))
    manifest = json.loads((output/'manifest.json').read_text())
    for name, value in manifest['archivos_sha256'].items():
        if digest(output/name) != value: raise ValueError('Salida distinta: '+name)
    for name, value in manifest['fuentes_sha256'].items():
        if digest(root/name) != value: raise ValueError('Fuente distinta: '+name)
    if digest(detail/'perfiles_2955.csv') != manifest['detalle_sha256']:
        raise ValueError('Detalle distinto')
    design = json.loads((root/'registro/diagnostico/aplicabilidad59/diseno.json').read_text())
    reps = {r['id']: r['columnas'] for r in design['representaciones']}
    table = {r['id_parcela']: r for r in read(root/'registro/t07/tabla_comun.csv')}
    cat = read(root/'registro/t07/catalogo_base.csv')
    known = sorted(r['id_parcela'] for r in cat if r['conjunto_origen'] == 'ENTRENAMIENTO')
    reserved = sorted(r['id_parcela'] for r in cat if r['conjunto_origen'] == 'PREDICCION')
    if (len(table), len(known), len(reserved)) != (197, 138, 59): raise ValueError('Población distinta')
    details = read(detail/'perfiles_2955.csv')
    expected_keys = {(cohort, pid, rep) for cohort, ids in [('etiquetadas_LOO', known), ('reservadas', reserved)]
                     for pid in ids for rep in reps}
    actual_keys = {(r['cohorte'], r['id_parcela'], r['representacion']) for r in details}
    if expected_keys != actual_keys or len(details) != len(actual_keys): raise ValueError('Perfiles incompletos')
    groups = defaultdict(list)
    for row in details:
        excluded = row['id_parcela'] if row['cohorte'] == 'etiquetadas_LOO' else ''
        groups[(excluded, row['representacion'])].append(row)
    checks, maximum = 0, 0.

    def check(actual, expected, name):
        nonlocal checks, maximum
        checks += 1
        if expected is None:
            if actual != '': raise ValueError('Debe faltar '+name)
        elif type(expected) is bool:
            if actual != ('si' if expected else 'no'): raise ValueError('Bandera distinta '+name)
        elif isinstance(expected, (float, int, np.number)):
            error = abs(float(actual)-float(expected));maximum = max(maximum, error)
            if not math.isfinite(error) or error > 1e-9: raise ValueError('Número distinto '+name)
        elif actual != expected: raise ValueError('Texto distinto '+name)

    calculated = {}
    pend = 'pendiente_media_t10_grados'
    for (excluded, rep), rows in groups.items():
        tr = [p for p in known if p != excluded]
        cols = reps[rep]
        raw = [[float(table[p][c]) if table[p][c] != '' else None for c in cols] for p in tr]
        if any(value is None and col != pend for row in raw for col, value in zip(cols, row)):
            raise ValueError('Faltante nuevo')
        median = statistics.median(r[cols.index(pend)] for r in raw if r[cols.index(pend)] is not None) if pend in cols else None

        def prepare(row):
            values = [median if v is None else v for v in row]
            if 'area_ha_origen' in cols:
                j = cols.index('area_ha_origen');values[j] = math.log(values[j])
            if pend in cols: values.append(float(row[cols.index(pend)] is None))
            return values

        x = [prepare(r) for r in raw]
        mean = [statistics.fmean(c) for c in zip(*x)]
        scale = [statistics.pstdev(c) or 1. for c in zip(*x)]
        z = np.array([[(v-m)/s for v, m, s in zip(r, mean, scale)] for r in x])
        distances = cdist(z, z)/math.sqrt(len(mean))
        for row in rows:
            pid = row['id_parcela']
            if pid in tr: raise ValueError('Evaluada en referencia')
            rawq = [float(table[pid][c]) if table[pid][c] != '' else None for c in cols]
            q = np.array([[(v-m)/s for v, m, s in zip(prepare(rawq), mean, scale)]])
            query = cdist(q, z)[0]/math.sqrt(len(mean))
            local = [j for j, p in enumerate(tr) if table[p]['municipio'] == table[pid]['municipio']]
            dl = min(query[j] for j in local) if local else None
            reference = [min(distances[j, k] for k in local if k != j) for j in local] if len(local) >= 2 else []
            q95 = sorted(reference)[math.ceil(.95*(len(reference)-1))] if reference else None
            exceeds = bool(dl > q95+1e-12) if reference else None
            check(row['n_entrenamiento'], len(tr), 'n_entrenamiento')
            check(row['n_municipio'], len(local), 'n_local')
            check(row['n_referencia_distancia'], len(reference), 'n_referencia')
            check(row['distancia_global'], min(query), 'distancia_global')
            check(row['distancia_municipio'], dl, 'distancia_local')
            check(row['q95_local'], q95, 'q95')
            check(row['supera_q95_local'], exceeds, 'supera_q95')
            check(row['percentil_local_estricto'], 100*sum(v < dl-1e-12 for v in reference)/len(reference) if reference else None, 'percentil')
            outside, outside_local, missing = [], [], []
            for j, col in enumerate(cols):
                value = rawq[j]
                if value is None: missing.append(col);continue
                for indices, dest in [(range(len(tr)), outside), (local, outside_local)]:
                    values = [raw[k][j] for k in indices if raw[k][j] is not None]
                    if values and (value < min(values)-tolerance(col) or value > max(values)+tolerance(col)):
                        dest.append(col)
            check(row['fuera_rango_global'], ';'.join(outside), 'rango_global')
            check(row['fuera_rango_municipio'], ';'.join(outside_local), 'rango_local')
            check(row['entradas_ausentes'], ';'.join(missing), 'faltantes')
            check(row['motivo_percentil_ausente'], '' if reference else 'sin_dos_etiquetas_locales', 'motivo')
            for col, pool, minimum in [('vecino_atributos_global', list(range(len(tr))), min(query)),
                                       ('vecino_atributos_municipio', local, dl)]:
                if not pool:
                    check(row[col], '', col)
                else:
                    if row[col] not in [tr[j] for j in pool]: raise ValueError('Vecino ajeno a referencia')
                    check(query[tr.index(row[col])], minimum, 'distancia_vecino_elegido')
            calculated[(row['cohorte'], pid, rep)] = (bool(outside), exceeds)

    united = {}
    for cohort, ids in [('etiquetadas_LOO', known), ('reservadas', reserved)]:
        for pid in ids:
            values = [calculated[(cohort, pid, r)] for r in reps]
            flags = [v[1] for v in values]
            qflag = True if True in flags else None if None in flags else False
            united[(cohort, pid)] = (any(v[0] for v in values), qflag)
    profile = read(output/'perfil_union_197.csv')
    if len(profile) != 197 or len({r['id_parcela'] for r in profile}) != 197: raise ValueError('Unión incompleta')
    for row in profile:
        values = united[(row['cohorte'], row['id_parcela'])]
        check(row['aviso_rango_global'], values[0], 'union_rango')
        check(row['aviso_q95_local'], values[1], 'union_q95')
    for filename in ['comparacion_138_59.csv', 'comparacion_por_municipio.csv']:
        for row in read(output/filename):
            index = 0 if row['regla'] == 'fuera_rango_global' else 1
            for cohort, ids, prefix in [('etiquetadas_LOO', known, 'etiquetadas'), ('reservadas', reserved, 'reservadas')]:
                pick = [pid for pid in ids if 'municipio' not in row or table[pid]['municipio'] == row['municipio']]
                values = [united[(cohort, pid)][index] if row['representacion'] == 'alguna_de_15' else
                          calculated[(cohort, pid, row['representacion'])][index] for pid in pick]
                n = len(values);valid = sum(v is not None for v in values);flagged = sum(v is True for v in values)
                for key, value in [('n_parcelas_total', n), ('n_parcelas_evaluables', valid),
                                   ('n_parcelas_con_aviso', flagged), ('n_parcelas_sin_diagnostico', n-valid),
                                   ('proporcion_aviso_observado_sobre_total', flagged/n if n else None),
                                   ('proporcion_aviso_sobre_evaluables', flagged/valid if valid else None)]:
                    check(row[prefix+'_'+key], value, 'conteos_y_denominadores')
    return dict(estado='aprobado', comparaciones=checks, max_delta=maximum, tolerancia=1e-9,
                perfiles=2955, parcelas=197, espacios_reconstruidos=len(groups),
                metodo='statistics_fmean_pstdev_median_cdist_cuantil_ordenado',
                importa_productor=False, modelos_predictivos=0)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--raiz', type=Path, default=Path(__file__).resolve().parents[1])
    p.add_argument('--salida', type=Path, required=True);p.add_argument('--detalle', type=Path, required=True)
    p.add_argument('--evidencia', type=Path, required=True)
    a = p.parse_args()
    if a.evidencia.exists(): raise ValueError('Evidencia existente')
    result = audit(a.raiz, a.salida, a.detalle)
    a.evidencia.parent.mkdir(parents=True, exist_ok=True)
    a.evidencia.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__': main()
