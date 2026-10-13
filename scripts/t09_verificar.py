"""Auditor independiente: lee OOF; no importa código de producción ni ajusta modelos.

Salidas privadas de comprobación, no resultados adicionales ni modificación del diseño.
"""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
REPO = Path(__file__).resolve().parents[1]
DESIGN_SHA = '1072e4196df68359fa3728e504f23ec28dd94b637715854a6635d36d4478081f'
SEED = 20261006
KEY = ['escenario', 'id_parcela', 'repeticion', 'particion']
MAIN_PAIRS = [('TC', 'T'), ('CL', 'T'), ('TC', 'CL'), ('R', 'T'), ('R', 'TC')]
FIXED_PAIRS = [('TC', 'T'), ('TC', 'CL')]

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def stats(y, p):
    y, p = (np.asarray(y, dtype=float), np.asarray(p, dtype=float))
    if len(y) == 0:
        return {'n_predicciones': 0, 'MAE': np.nan, 'RMSE': np.nan, 'sesgo': np.nan, 'R2': np.nan, 'estado_R2': 'sin_casos'}
    if not (np.isfinite(y).all() and np.isfinite(p).all()):
        raise ValueError('Control independiente no aprobado: np.isfinite(y).all() and np.isfinite(p).all()')
    err = p - y
    ss = float(np.dot(y - y.mean(), y - y.mean()))
    state = 'definido' if len(y) >= 2 and (not np.all(y == y[0])) else 'menos_de_2_o_y_constante'
    return {'n_predicciones': len(y), 'MAE': float(np.abs(err).mean()), 'RMSE': float(np.sqrt(np.dot(err, err) / len(err))), 'sesgo': float(err.mean()), 'R2': float(1 - np.dot(err, err) / ss) if state == 'definido' else np.nan, 'estado_R2': state}

def intervals(delta, cells):
    """Remuestreo independiente de parcelas y de sumas/conteos de celdas."""
    delta = delta.sort_index()
    vals = delta.to_numpy(float)
    parcel_draw = np.random.RandomState(SEED).randint(len(vals), size=(5000, len(vals)))
    parcel_boot = vals[parcel_draw].mean(axis=1)
    members = pd.DataFrame({'d': delta, 'c': cells.reindex(delta.index)})
    if not members.c.notna().all():
        raise ValueError('Control independiente no aprobado: members.c.notna().all()')
    names = sorted(members.c.unique())
    sums = np.array([members.loc[members.c.eq(n), 'd'].sum() for n in names])
    counts = np.array([members.c.eq(n).sum() for n in names])
    draws = np.random.RandomState(SEED).randint(len(names), size=(5000, len(names)))
    block_boot = sums[draws].sum(axis=1) / counts[draws].sum(axis=1)
    return {'IC95_celdas_inf': float(np.percentile(block_boot, 2.5)), 'IC95_celdas_sup': float(np.percentile(block_boot, 97.5)), 'IC95_parcelas_inf': float(np.percentile(parcel_boot, 2.5)), 'IC95_parcelas_sup': float(np.percentile(parcel_boot, 97.5)), 'n_celdas': len(names)}

def paired(candidate, base, cells):
    a = candidate.set_index(['id_parcela', 'repeticion']).sort_index()
    b = base.set_index(['id_parcela', 'repeticion']).sort_index()
    if not a.index.equals(b.index):
        raise ValueError('Control independiente no aprobado: a.index.equals(b.index)')
    if not np.array_equal(a.real, b.real):
        raise ValueError('Control independiente no aprobado: np.array_equal(a.real, b.real)')
    ec, eb = (a.prediccion - a.real, b.prediccion - b.real)
    d = abs(ec) - abs(eb)
    per_id = d.groupby(level='id_parcela').mean()
    per_rep = d.groupby(level='repeticion').mean()
    drmse = np.mean([np.sqrt(np.mean(ec.loc[slice(None), rep].to_numpy() ** 2)) - np.sqrt(np.mean(eb.loc[slice(None), rep].to_numpy() ** 2)) for rep in sorted(per_rep.index)])
    ci = intervals(per_id, cells)
    pass_rule = bool(per_id.mean() <= -0.01 and ci['IC95_celdas_sup'] < 0 and (sum(per_rep < 0) >= 4) and (drmse <= 0.01))
    return {'n_predicciones': len(a), 'n_parcelas': len(per_id), 'dMAE': float(per_id.mean()), 'dMAE_media_repeticiones': float(per_rep.mean()), 'dRMSE': float(drmse), 'reps_que_mejoran': int(sum(per_rep < 0)), 'parcelas_mejoran': int(sum(per_id < 0)), 'parcelas_empeoran': int(sum(per_id > 0)), 'cumple_umbrales_numericos': pass_rule, **ci}

def preflight(repo):
    cfg_path = repo / 'registro/t09/diseno.json'
    if not sha(cfg_path) == DESIGN_SHA:
        raise ValueError('Diseño distinto del evaluado')
    cfg = json.loads(cfg_path.read_text())
    for file, digest in cfg['fuentes_sha256'].items():
        if not sha(repo / file) == digest:
            raise ValueError(f'Fuente alterada: {file}')
    t = pd.read_csv(repo / 'registro/t07/tabla_comun.csv').set_index('id_parcela', drop=False)
    known = t[t.conjunto_origen.eq('ENTRENAMIENTO')].sort_index()
    held = t[t.conjunto_origen.eq('PREDICCION')].sort_index()
    if not (t.shape == (197, 60) and len(known) == 138 and (len(held) == 59)):
        raise ValueError('Control independiente no aprobado: t.shape == (197, 60) and len(known) == 138 and (len(held) == 59)')
    if not (known.rendimiento_t_ha.notna().all() and held.rendimiento_t_ha.isna().all()):
        raise ValueError('Control independiente no aprobado: known.rendimiento_t_ha.notna().all() and held.rendimiento_t_ha.isna().all()')
    if not t.index.is_unique:
        raise ValueError('Control independiente no aprobado: t.index.is_unique')
    p = pd.read_csv(repo / 'registro/t03/particiones.csv')
    if not (len(p) == 690 and (not p[['ID_POLIGONO', 'repeticion']].duplicated().any())):
        raise ValueError("Control independiente no aprobado: len(p) == 690 and (not p[['ID_POLIGONO', 'repeticion']].duplicated().any())")
    if not set(p.ID_POLIGONO) == set(known.index):
        raise ValueError('Control independiente no aprobado: set(p.ID_POLIGONO) == set(known.index)')
    cells = p.drop_duplicates('ID_POLIGONO').set_index('ID_POLIGONO').celda_chirps
    return (cfg, t, known, held, p, cells)

def t08_control(repo, cells):
    """Recalcula las 24 comparaciones publicadas, con un algoritmo independiente."""
    tab = pd.read_csv(repo / 'registro/t03/comparacion_emparejada.csv')
    all_oof = pd.concat([pd.read_csv(f) for f in sorted((repo / 'registro/t03').glob('predicciones_oof_referencias_*.csv'))])
    rows, maximum = ([], 0.0)
    check_cols = ['dMAE', 'IC95_celdas_inf', 'IC95_celdas_sup', 'IC95_parcelas_inf', 'IC95_parcelas_sup', 'dRMSE', 'n_celdas', 'n_predicciones', 'reps_que_mejoran', 'parcelas_mejoran', 'parcelas_empeoran']
    for row in tab.to_dict('records'):
        esc = all_oof[all_oof.escenario.eq(row['escenario'])].rename(columns={'ID_POLIGONO': 'id_parcela'})
        base = esc[esc.candidato.eq(row['frente_a'])]
        if row['subconjunto'] == 'sin_respaldo':
            base = base[base.fuente.eq('municipio')]
        keys = set(zip(base.id_parcela, base.repeticion))
        cand = esc[esc.candidato.eq(row['candidato'])]
        cand = cand[[k in keys for k in zip(cand.id_parcela, cand.repeticion)]]
        calc = paired(cand, base, cells)
        for col in check_cols:
            delta = abs(round(calc[col], 4) - row[col])
            maximum = max(maximum, delta)
            if not delta < 1e-12:
                raise ValueError(f"Control T08 distinto: {row['candidato']}/{row['escenario']}/{row['subconjunto']}/{col}")
        if not bool(calc['cumple_umbrales_numericos']) == bool(row['cumple_regla_T03']):
            raise ValueError("Control independiente no aprobado: bool(calc['cumple_umbrales_numericos']) == bool(row['cumple_regla_T03'])")
        rows.append({k: row[k] for k in ['escenario', 'subconjunto', 'candidato']})
    return {'comparaciones': len(rows), 'max_diferencia_publicacion_4_decimales': maximum}

def contexts_expected(known, partitions):
    result = {}
    for esc, col in [('A', 'particion_principal'), ('B', 'particion_espacial')]:
        for rep in range(1, 6):
            part = partitions[partitions.repeticion.eq(rep)]
            for fold in range(5):
                test = tuple(sorted(part.loc[part[col].eq(fold), 'ID_POLIGONO']))
                train = tuple(sorted(set(known.index) - set(test)))
                mask = known.loc[list(test), 'municipio'].isin(known.loc[list(train), 'municipio'])
                result[esc, rep, fold] = {'train': train, 'test': test, 'mask': dict(mask)}
    for fold, mun in enumerate(sorted(known.municipio.unique())):
        test = tuple(sorted(known.index[known.municipio.eq(mun)]))
        result['C', 1, fold] = {'train': tuple(sorted(set(known.index) - set(test))), 'test': test, 'mask': {k: False for k in test}}
    if not len(result) == 59:
        raise ValueError('Control independiente no aprobado: len(result) == 59')
    for ctx in result.values():
        train = known.loc[list(ctx['train'])]
        expected_source, expected_reference = ({}, {})
        for pid in ctx['test']:
            r = known.loc[pid]
            municipal = train[train.municipio.eq(r.municipio)].rendimiento_t_ha
            group = train[train.cultivo_origen.eq(r.cultivo_origen)].rendimiento_t_ha
            if len(municipal):
                source, value = ('municipio', float(municipal.mean()))
            elif len(group):
                source, value = ('grupo', float(group.mean()))
            else:
                source, value = ('global', float(train.rendimiento_t_ha.mean()))
            expected_source[pid], expected_reference[pid] = (source, value)
        ctx.update(source=expected_source, reference=expected_reference)
    return result

def audit_oof(oof, expected, known, held, repo, selected):
    if not (len(oof) == 15180 and (not oof[['procedimiento', 'variante', *KEY]].duplicated().any())):
        raise ValueError("Control independiente no aprobado: len(oof) == 15180 and (not oof[['procedimiento', 'variante', *KEY]].duplicated().any())")
    if not not set(oof.id_parcela) & set(held.index):
        raise ValueError('Control independiente no aprobado: not set(oof.id_parcela) & set(held.index)')
    if not set(oof.id_parcela) == set(known.index):
        raise ValueError('Control independiente no aprobado: set(oof.id_parcela) == set(known.index)')
    if not np.array_equal(oof.real.to_numpy(), oof.id_parcela.map(known.rendimiento_t_ha).to_numpy()):
        raise ValueError('Control independiente no aprobado: np.array_equal(oof.real.to_numpy(), oof.id_parcela.map(known.rendimiento_t_ha).to_numpy())')
    if not np.isfinite(oof[['real', 'prediccion', 'referencia', 'correccion']].to_numpy(float)).all():
        raise ValueError("Control independiente no aprobado: np.isfinite(oof[['real', 'prediccion', 'referencia', 'correccion']].to_numpy(float)).all()")
    if not np.max(abs(oof.prediccion - oof.referencia - oof.correccion)) < 1e-12:
        raise ValueError('Control independiente no aprobado: np.max(abs(oof.prediccion - oof.referencia - oof.correccion)) < 1e-12')
    if not oof.sin_respaldo.dtype.kind == 'b':
        raise ValueError("Control independiente no aprobado: oof.sin_respaldo.dtype.kind == 'b'")
    if not set(oof.procedimiento) == {'T', 'CL', 'TC', 'R'}:
        raise ValueError("Control independiente no aprobado: set(oof.procedimiento) == {'T', 'CL', 'TC', 'R'}")
    selected_rows = oof[oof.variante.eq(selected)]
    if not len(selected_rows) == 6072:
        raise ValueError('Control independiente no aprobado: len(selected_rows) == 6072')
    variants = sorted(set(oof.variante) - {selected})
    if not len(variants) == 2:
        raise ValueError('Control independiente no aprobado: len(variants) == 2')
    for (method, variant, esc, rep, fold), d in oof.groupby(['procedimiento', 'variante', 'escenario', 'repeticion', 'particion']):
        if not (esc, rep, fold) in expected:
            raise ValueError('Control independiente no aprobado: (esc, rep, fold) in expected')
        exp = expected[esc, rep, fold]
        if not set(d.id_parcela) == set(exp['test']):
            raise ValueError("Control independiente no aprobado: set(d.id_parcela) == set(exp['test'])")
        if not d.n_entrenamiento.eq(len(exp['train'])).all():
            raise ValueError("Control independiente no aprobado: d.n_entrenamiento.eq(len(exp['train'])).all()")
        if not np.array_equal(d.sin_respaldo.to_numpy(), d.id_parcela.map(exp['mask']).to_numpy()):
            raise ValueError("Control independiente no aprobado: np.array_equal(d.sin_respaldo.to_numpy(), d.id_parcela.map(exp['mask']).to_numpy())")
        if not d.municipio.eq(d.id_parcela.map(known.municipio)).all():
            raise ValueError('Control independiente no aprobado: d.municipio.eq(d.id_parcela.map(known.municipio)).all()')
        if not d.cultivo_origen.eq(d.id_parcela.map(known.cultivo_origen)).all():
            raise ValueError('Control independiente no aprobado: d.cultivo_origen.eq(d.id_parcela.map(known.cultivo_origen)).all()')
        if not not set(exp['test']) & set(exp['train']):
            raise ValueError("Control independiente no aprobado: not set(exp['test']) & set(exp['train'])")
        if not d.fuente_referencia.eq(d.id_parcela.map(exp['source'])).all():
            raise ValueError("Control independiente no aprobado: d.fuente_referencia.eq(d.id_parcela.map(exp['source'])).all()")
        if method == 'CL':
            if not d.fuente.eq('global').all():
                raise ValueError("Control independiente no aprobado: d.fuente.eq('global').all()")
        else:
            if not d.fuente.eq(d.fuente_referencia).all():
                raise ValueError('Control independiente no aprobado: d.fuente.eq(d.fuente_referencia).all()')
            if not max(abs(d.referencia - d.id_parcela.map(exp['reference']))) < 1e-12:
                raise ValueError("Control independiente no aprobado: max(abs(d.referencia - d.id_parcela.map(exp['reference']))) < 1e-12")
        if method == 'T':
            if not (variant == selected and d.correccion.eq(0).all()):
                raise ValueError('Control independiente no aprobado: variant == selected and d.correccion.eq(0).all()')
    for esc, count in [('A', 675), ('B', 659), ('C', 0)]:
        sub = selected_rows[selected_rows.escenario.eq(esc) & selected_rows.procedimiento.eq('CL')]
        if not sub.sin_respaldo.sum() == count:
            raise ValueError('Control independiente no aprobado: sub.sin_respaldo.sum() == count')
    published = pd.read_csv(repo / 'registro/t03/predicciones_oof_referencias_media_mun__resp_grupo.csv',float_precision='round_trip').rename(columns={'ID_POLIGONO': 'id_parcela'})
    baseline = selected_rows[selected_rows.procedimiento.eq('T') & selected_rows.escenario.isin(['A', 'B'])]
    joined = baseline.merge(published, on=KEY, validate='one_to_one', suffixes=('_t09', '_t08'))
    if not len(joined) == 1380:
        raise ValueError('Control independiente no aprobado: len(joined) == 1380')
    for field in ['real', 'prediccion', 'fuente']:
        if not np.array_equal(joined[f'{field}_t09'], joined[f'{field}_t08']):
            raise ValueError(f'T08 {field} distinto')
    return {'filas_oof': len(oof), 'filas_principales': len(selected_rows), 'filas_fijas': len(oof) - len(selected_rows), 'referencias_T08_exactas': len(joined), 'reservadas_en_oof': 0}

def audit_contexts(recorded, expected, known, cells):
    if not len(recorded) == 59:
        raise ValueError('Control independiente no aprobado: len(recorded) == 59')
    keys_seen = []
    for ctx in recorded:
        key = (ctx['escenario'], ctx['repeticion'], ctx['particion'])
        if not key in expected:
            raise ValueError('Control independiente no aprobado: key in expected')
        keys_seen.append(key)
        exp = expected[key]
        if not tuple(ctx['entrenamiento']) == exp['train']:
            raise ValueError("Control independiente no aprobado: tuple(ctx['entrenamiento']) == exp['train']")
        if not tuple(ctx['evaluacion']) == exp['test']:
            raise ValueError("Control independiente no aprobado: tuple(ctx['evaluacion']) == exp['test']")
        for field, ids in [('entrenamiento', exp['train']), ('evaluacion', exp['test'])]:
            if not ctx[f'sha_ids_{field}'] == hashlib.sha256('\n'.join(ids).encode()).hexdigest():
                raise ValueError("Control independiente no aprobado: ctx[f'sha_ids_{field}'] == hashlib.sha256('\\n'.join(ids).encode()).hexdigest()")
        if not len(ctx['internas']) == 4:
            raise ValueError("Control independiente no aprobado: len(ctx['internas']) == 4")
        visited = []
        for inner in ctx['internas']:
            tr, val = (inner['entrenamiento'], inner['validacion'])
            if not (len(tr) == len(set(tr)) and len(val) == len(set(val))):
                raise ValueError('Control independiente no aprobado: len(tr) == len(set(tr)) and len(val) == len(set(val))')
            if not not set(tr) & set(val):
                raise ValueError('Control independiente no aprobado: not set(tr) & set(val)')
            if not set(tr) | set(val) == set(exp['train']):
                raise ValueError("Control independiente no aprobado: set(tr) | set(val) == set(exp['train'])")
            mask = inner['elegibles']
            if not (len(mask) == len(val) and all((isinstance(b, bool) for b in mask)) and any(mask)):
                raise ValueError('Control independiente no aprobado: len(mask) == len(val) and all((isinstance(b, bool) for b in mask)) and any(mask)')
            target_mask = [True] * len(val) if key[0] == 'C' else known.loc[val].municipio.isin(known.loc[tr].municipio).tolist()
            if not mask == target_mask:
                raise ValueError('Control independiente no aprobado: mask == target_mask')
            if key[0] == 'B':
                if not not set(cells.loc[tr]) & set(cells.loc[val]):
                    raise ValueError('Control independiente no aprobado: not set(cells.loc[tr]) & set(cells.loc[val])')
                if not not set(cells.loc[list(exp['train'])]) & set(cells.loc[list(exp['test'])]):
                    raise ValueError("Control independiente no aprobado: not set(cells.loc[list(exp['train'])]) & set(cells.loc[list(exp['test'])])")
            if key[0] == 'C':
                if not not set(known.loc[tr].municipio) & set(known.loc[val].municipio):
                    raise ValueError('Control independiente no aprobado: not set(known.loc[tr].municipio) & set(known.loc[val].municipio)')
                if not not set(known.loc[list(exp['train'])].municipio) & set(known.loc[list(exp['test'])].municipio):
                    raise ValueError("Control independiente no aprobado: not set(known.loc[list(exp['train'])].municipio) & set(known.loc[list(exp['test'])].municipio)")
            visited.extend(val)
        if not (len(visited) == len(set(visited)) and set(visited) == set(exp['train'])):
            raise ValueError("Control independiente no aprobado: len(visited) == len(set(visited)) and set(visited) == set(exp['train'])")
    if not len(keys_seen) == len(set(keys_seen)) == 59:
        raise ValueError('Control independiente no aprobado: len(keys_seen) == len(set(keys_seen)) == 59')
    return {'contextos_completos_disjuntos': 59, 'particiones_internas_completas_disjuntas': 236, 'grupos_compartidos_B_C': 0, 'mascaras_independientes_correctas': True}

def summaries(oof):
    rows = []
    xbase = oof[oof.procedimiento.eq('T')]
    expanded = pd.concat([oof, xbase.assign(variante='abr_oct'), xbase.assign(variante='jun_oct')])
    for (esc, method, variant, rep), x in expanded.groupby(['escenario', 'procedimiento', 'variante', 'repeticion']):
        subsets = [('todas', x)] + ([] if esc == 'C' else [('sin_respaldo', x[x.sin_respaldo])])
        for pop, g in subsets:
            rows.append({'escenario': esc, 'procedimiento': method, 'variante': variant, 'repeticion': rep, 'subconjunto': pop, 'n_parcelas': g.id_parcela.nunique(), **stats(g.real, g.prediccion)})
    return pd.DataFrame(rows)

def assert_number(actual, expected, label, tol=1e-12):
    if pd.isna(expected):
        if not pd.isna(actual):
            raise ValueError(f'{label}: debe ser vacío/indefinido')
        return 0.0
    if not not pd.isna(actual):
        raise ValueError(f'{label}: valor faltante')
    error = abs(float(actual) - float(expected))
    if not error <= tol:
        raise ValueError(f'{label}: {actual} != {expected}; diferencia {error}')
    return error

def audit_report_tables(folder, oof, known, selected, cells, repo):
    """Recalcula cada fila de métricas/desgloses desde las OOF, sin llamar reportes."""
    q = pd.read_csv(repo / 'registro/t07/calidad_parcelas.csv').set_index('id_parcela')
    base = oof[oof.procedimiento.eq('T')]
    expanded = pd.concat([oof, base.assign(variante='abr_oct'), base.assign(variante='jun_oct')], ignore_index=True)
    expanded['contorno'] = expanded.id_parcela.map(q.contorno_categoria).map({'A': 'A', 'B': 'B/C', 'C': 'B/C'})
    expanded['contorno_angosta_o_muy_pequena'] = expanded.id_parcela.map(q.contorno_angosta_o_muy_pequena)
    expanded['alerta_contorno_t03_bis'] = expanded.id_parcela.map(q.alerta_contorno_t03_bis)
    expanded['vecina_etiquetada_menos_20m'] = expanded.id_parcela.map(q.vecina_etiquetada_menos_20m)
    expanded['escalon_etiqueta'] = expanded.id_parcela.map(q.escalon_etiqueta_municipio).fillna('no_identificable').map(str)
    if not expanded.loc[expanded.alerta_contorno_t03_bis.eq('si')].id_parcela.nunique() == 24:
        raise ValueError("Control independiente no aprobado: expanded.loc[expanded.alerta_contorno_t03_bis.eq('si')].id_parcela.nunique() == 24")
    max_error, counts = (0.0, {})
    pairs = [('metricas_por_repeticion', 'metricas_resumen'), ('sensibilidad_por_repeticion', 'sensibilidad_resumen'), ('desgloses_por_repeticion', 'desgloses_resumen')]
    for rep_name, summary_name in pairs:
        records = pd.read_csv(folder / f'{rep_name}.csv', float_precision='round_trip')
        table = expanded[expanded.alerta_contorno_t03_bis.eq('no')] if rep_name.startswith('sensibilidad') else expanded
        expected_rows = []
        for r in records.to_dict('records'):
            match = table[table.escenario.eq(r['escenario']) & table.procedimiento.eq(r['procedimiento']) & table.variante.eq(r['variante'])]
            if r['poblacion'] == 'sin_respaldo':
                match = match[match.sin_respaldo]
            elif not r['poblacion'] == 'todas':
                raise ValueError("Control independiente no aprobado: r['poblacion'] == 'todas'")
            if 'desglose' in r:
                if not r['desglose'] in ('municipio', 'cultivo_origen', 'contorno', 'contorno_angosta_o_muy_pequena', 'escalon_etiqueta', 'vecina_etiquetada_menos_20m'):
                    raise ValueError("Control independiente no aprobado: r['desglose'] in ('municipio', 'cultivo_origen', 'contorno', 'contorno_angosta_o_muy_pequena', 'escalon_etiqueta', 'vecina_etiquetada_menos_20m')")
                match = match[match[r['desglose']].map(str).eq(str(r['categoria']))]
            if not len(match) > 0:
                raise ValueError('Control independiente no aprobado: len(match) > 0')
            group = match[match.repeticion.eq(r['repeticion'])]
            calc = stats(group.real, group.prediccion)
            if not (r['n_predicciones'] == len(group) and r['n_parcelas'] == group.id_parcela.nunique()):
                raise ValueError("Control independiente no aprobado: r['n_predicciones'] == len(group) and r['n_parcelas'] == group.id_parcela.nunique()")
            if not r['n_parcelas_union_reps'] == match.id_parcela.nunique():
                raise ValueError("Control independiente no aprobado: r['n_parcelas_union_reps'] == match.id_parcela.nunique()")
            for metric in ('MAE', 'RMSE', 'sesgo', 'R2'):
                max_error = max(max_error, assert_number(r[metric], calc[metric], f'{rep_name}:{metric}'))
            if not (r['estado_R2'] == 'definido') == (calc['estado_R2'] == 'definido'):
                raise ValueError("Control independiente no aprobado: (r['estado_R2'] == 'definido') == (calc['estado_R2'] == 'definido')")
            expected_rows.append({**r, **calc})
        expected = pd.DataFrame(expected_rows)
        summary = pd.read_csv(folder / f'{summary_name}.csv', float_precision='round_trip')
        key = ['escenario', 'procedimiento', 'variante', 'poblacion', 'sensibilidad']
        if 'desglose' in records:
            key += ['desglose', 'categoria']
        if not not records[[*key, 'repeticion']].duplicated().any():
            raise ValueError("Control independiente no aprobado: not records[[*key, 'repeticion']].duplicated().any()")
        if not not summary[key].duplicated().any():
            raise ValueError('Control independiente no aprobado: not summary[key].duplicated().any()')
        if not len(summary) == len(records.groupby(key, dropna=False)):
            raise ValueError('Control independiente no aprobado: len(summary) == len(records.groupby(key, dropna=False))')
        for r in summary.to_dict('records'):
            g = expected
            for c in key:
                g = g[g[c].map(str).eq(str(r[c]))]
            if not (len(g) > 0 and r['n_repeticiones'] == len(g)):
                raise ValueError("Control independiente no aprobado: len(g) > 0 and r['n_repeticiones'] == len(g)")
            if not r['n_predicciones'] == g.n_predicciones.sum():
                raise ValueError("Control independiente no aprobado: r['n_predicciones'] == g.n_predicciones.sum()")
            if not r['n_parcelas'] == g.n_parcelas_union_reps.max():
                raise ValueError("Control independiente no aprobado: r['n_parcelas'] == g.n_parcelas_union_reps.max()")
            if not r['n_parcelas_min_rep'] == g.n_parcelas.min():
                raise ValueError("Control independiente no aprobado: r['n_parcelas_min_rep'] == g.n_parcelas.min()")
            if not r['n_R2_definidas'] == g.estado_R2.eq('definido').sum():
                raise ValueError("Control independiente no aprobado: r['n_R2_definidas'] == g.estado_R2.eq('definido').sum()")
            for metric in ('MAE', 'RMSE', 'sesgo', 'R2'):
                max_error = max(max_error, assert_number(r[metric], g[metric].mean(), f'{summary_name}:{metric}'))
                max_error = max(max_error, assert_number(r[f'{metric}_sd_rep'], g[metric].std(ddof=0), f'{summary_name}:{metric}_sd'))
        counts[rep_name], counts[summary_name] = (len(records), len(summary))
    own = comparisons(oof, cells, selected).rename(columns={'procedimiento': 'candidato', 'subconjunto': 'poblacion', 'dMAE_media_repeticiones': 'dMAE_media_rep'})
    actual = pd.read_csv(folder / 'comparaciones_emparejadas.csv', float_precision='round_trip')
    key = ['escenario', 'variante', 'poblacion', 'candidato', 'frente_a']
    joined = own.merge(actual, on=key, validate='one_to_one', suffixes=('_i', '_p'), how='outer', indicator=True)
    if not (len(joined) == 45 and joined['_merge'].eq('both').all()):
        raise ValueError("Control independiente no aprobado: len(joined) == 45 and joined['_merge'].eq('both').all()")
    for r in joined.to_dict('records'):
        for metric in ('dMAE', 'dMAE_media_rep', 'dRMSE', 'IC95_celdas_inf', 'IC95_celdas_sup', 'IC95_parcelas_inf', 'IC95_parcelas_sup', 'n_predicciones', 'n_parcelas', 'n_celdas', 'reps_que_mejoran', 'parcelas_mejoran', 'parcelas_empeoran'):
            max_error = max(max_error, assert_number(r[f'{metric}_p'], r[f'{metric}_i'], f'contraste:{metric}'))
        applies = r['escenario'] == 'A' and r['variante'] == selected and (r['poblacion'] == 'sin_respaldo') and (r['frente_a'] == 'T')
        if not bool(r['aplica_regla_promocion']) == applies:
            raise ValueError("Control independiente no aprobado: bool(r['aplica_regla_promocion']) == applies")
        if applies:
            got = str(r['cumple_regla_promocion']).lower() == 'true'
            if not got == bool(r['cumple_umbrales_numericos']):
                raise ValueError("Control independiente no aprobado: got == bool(r['cumple_umbrales_numericos'])")
        elif not (pd.isna(r['cumple_regla_promocion']) and r['estado_promocion'] == 'no_aplica'):
            raise ValueError("Control independiente no aprobado: pd.isna(r['cumple_regla_promocion']) and r['estado_promocion'] == 'no_aplica'")
    counts['comparaciones_emparejadas'] = len(actual)
    return {'filas_reportes_recalculadas': counts, 'max_diferencia_reportes': max_error}

def comparisons(oof, cells, selected):
    rows = []
    for (esc, variant), x in oof.groupby(['escenario', 'variante']):
        pairs = MAIN_PAIRS if variant == selected else FIXED_PAIRS
        for method, reference in pairs:
            a = x[x.procedimiento.eq(method)]
            if reference == 'T' and variant != selected:
                b = oof[oof.procedimiento.eq('T') & oof.variante.eq(selected) & oof.escenario.eq(esc)]
            else:
                b = x[x.procedimiento.eq(reference)]
            if not len(a) == len(b):
                raise ValueError('Control independiente no aprobado: len(a) == len(b)')
            for pop in ['todas'] + ([] if esc == 'C' else ['sin_respaldo']):
                aa, bb = (a, b) if pop == 'todas' else (a[a.sin_respaldo], b[b.sin_respaldo])
                calc = paired(aa, bb, cells)
                rows.append({'escenario': esc, 'variante': variant, 'subconjunto': pop, 'procedimiento': method, 'frente_a': reference, 'habilita_promocion_T09': esc == 'A' and pop == 'sin_respaldo' and (variant == selected) and (reference == 'T'), **calc})
    return pd.DataFrame(rows)

def audit_selection(scores, expected):
    if not len(scores) == 1416:
        raise ValueError('Control independiente no aprobado: len(scores) == 1416')
    keys = ['escenario', 'repeticion', 'particion', 'procedimiento']
    if not not scores[[*keys, 'ventana', 'lambda_reg']].duplicated().any():
        raise ValueError("Control independiente no aprobado: not scores[[*keys, 'ventana', 'lambda_reg']].duplicated().any()")
    winners = []
    for key, g in scores.groupby(keys):
        esc, rep, fold, method = key
        if not (method in ('CL', 'TC', 'R') and (esc, rep, fold) in expected):
            raise ValueError("Control independiente no aprobado: method in ('CL', 'TC', 'R') and (esc, rep, fold) in expected")
        if not len(g) == 8:
            raise ValueError('Control independiente no aprobado: len(g) == 8')
        if not set(zip(g.ventana, g.lambda_reg)) == {(w, z) for w in ('abr_oct', 'jun_oct') for z in (0.01, 0.1, 1.0, 10.0)}:
            raise ValueError("Control independiente no aprobado: set(zip(g.ventana, g.lambda_reg)) == {(w, z) for w in ('abr_oct', 'jun_oct') for z in (0.01, 0.1, 1.0, 10.0)}")
        if not np.isfinite(g.MAE).all():
            raise ValueError('Control independiente no aprobado: np.isfinite(g.MAE).all()')
        records = g.to_dict('records')
        rank = lambda r: (round(r['MAE'], 6), -r['lambda_reg'], 0 if r['ventana'] == 'jun_oct' else 1)
        win = min(records, key=rank)
        for w in ('abr_oct', 'jun_oct'):
            same = min([r for r in records if r['ventana'] == w], key=rank)
            winners.append({**dict(zip(keys, key)), 'variante': w, 'ventana': same['ventana'], 'lambda_reg': same['lambda_reg']})
        winners.append({**dict(zip(keys, key)), 'variante': 'seleccionada', 'ventana': win['ventana'], 'lambda_reg': win['lambda_reg']})
    if not len(winners) == 531:
        raise ValueError('Control independiente no aprobado: len(winners) == 531')
    return pd.DataFrame(winners)

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--raiz', '--repo', dest='repo', type=Path, default=REPO)
    ap.add_argument('--resultados', type=Path)
    ap.add_argument('--salida', type=Path, required=True)
    ap.add_argument('--seleccionada', default='seleccionada')
    args = ap.parse_args()
    args.repo, args.salida = (args.repo.resolve(), args.salida.resolve())
    allowed = [args.repo / 'reports', args.repo / 'data/processed/t09']
    if not any((args.salida.is_relative_to(p) and args.salida != p for p in allowed)):
        raise ValueError('La auditoría sólo escribe en una subcarpeta nueva reports/ o data/processed/t09/')
    if args.salida.exists():
        raise ValueError('Salida debe ser nueva para preservar auditorías anteriores')
    cfg, all_t, known, held, p, cells = preflight(args.repo)
    results = {'auditoria_independiente': True, 'sin_importar_modulos_produccion': True, 'sha_diseno': DESIGN_SHA, 'control_bootstrap_T08': t08_control(args.repo, cells)}
    args.salida.mkdir(parents=True)
    if args.resultados:
        oof = pd.read_csv(args.resultados / 'predicciones_oof.csv', float_precision='round_trip')
        expected = contexts_expected(known, p)
        results.update(audit_oof(oof, expected, known, held, args.repo, args.seleccionada))
        results.update(audit_contexts(json.loads((args.resultados / 'contextos.json').read_text()), expected, known, cells))
        metrics = summaries(oof)
        metrics.to_csv(args.salida / 'metricas_independientes.csv', index=False)
        comp = comparisons(oof, cells, args.seleccionada)
        comp.to_csv(args.salida / 'comparaciones_independientes.csv', index=False)
        score_path = args.resultados / 'puntuaciones_internas.csv'
        winners = audit_selection(pd.read_csv(score_path, float_precision='round_trip'), expected)
        winners.to_csv(args.salida / 'selecciones_recalculadas.csv', index=False)
        actual_selection = pd.read_csv(args.resultados / 'seleccion_interna.csv', float_precision='round_trip')
        win_key = ['escenario', 'repeticion', 'particion', 'procedimiento', 'variante']
        m = winners.merge(actual_selection, on=win_key, validate='one_to_one', suffixes=('_i', '_p'), how='outer', indicator=True)
        if not (len(m) == 531 and m['_merge'].eq('both').all()):
            raise ValueError("Control independiente no aprobado: len(m) == 531 and m['_merge'].eq('both').all()")
        if not (m.ventana_i.eq(m.ventana_p).all() and np.array_equal(m.lambda_reg_i, m.lambda_reg_p)):
            raise ValueError('Control independiente no aprobado: m.ventana_i.eq(m.ventana_p).all() and np.array_equal(m.lambda_reg_i, m.lambda_reg_p)')
        oof_config = oof[oof.procedimiento.ne('T')].drop_duplicates(win_key)
        mm = winners.merge(oof_config, on=win_key, validate='one_to_one', suffixes=('_i', '_o'))
        if not (len(mm) == 531 and mm.ventana_i.eq(mm.ventana_o).all() and np.array_equal(mm.lambda_reg_i, mm.lambda_reg_o)):
            raise ValueError('Control independiente no aprobado: len(mm) == 531 and mm.ventana_i.eq(mm.ventana_o).all() and np.array_equal(mm.lambda_reg_i, mm.lambda_reg_o)')
        results.update(audit_report_tables(args.resultados, oof, known, args.seleccionada, cells, args.repo))
        results.update({'metricas_recalculadas': len(metrics), 'contrastes_recalculados': len(comp), 'selecciones_recalculadas': len(winners)})
    results['evaluacion_T09_verificada'] = args.resultados is not None
    results['estado'] = 'auditoria_T09_aprobada' if args.resultados else 'control_T08_aprobado'
    (args.salida / 'resultado.json').write_text(json.dumps(results, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(results, ensure_ascii=False, indent=2))
if __name__ == '__main__':
    main()
