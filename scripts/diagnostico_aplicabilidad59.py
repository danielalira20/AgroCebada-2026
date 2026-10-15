"""C descriptiva: soporte de entradas, geometría y errores T08 históricos. No entrena modelos."""
import argparse
import csv
import hashlib
import io
import json
import math
import os
from pathlib import Path
import platform
import shutil
import tempfile
import zipfile

import geopandas as gpd
import numpy as np
import pyproj
import shapely

from scripts import evaluacion_comun_contrato as contrato

VERSION = 'aplicabilidad-C-v1'
DESIGN = 'registro/diagnostico/aplicabilidad59/diseno.json'
DESIGN_SHA = '9e1d19e196cb0d505e04fd07063b6d21b0c9e062866e8bf697fc3365ee2ac477'
RAIZ = Path(__file__).resolve().parents[1]
PEND = 'pendiente_media_t10_grados'
exigir = contrato.exigir
sha = contrato.sha


def rows(path):
    return contrato.leer_csv(path)[1]


def indexed(path, keys=('id_parcela',)):
    return contrato.indexar(rows(path), list(keys))


def flag(v):
    return str(v).lower() in ('si', 'true', '1')


def dump(path, obj):
    Path(path).write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')


def csv_out(path, records):
    exigir(bool(records), 'No publicar tabla vacía sin definición: ' + Path(path).name)
    with Path(path).open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(records[0]), lineterminator='\n')
        w.writeheader()
        for r in records:
            w.writerow({k: '' if v is None else format(float(v), '.15g') if isinstance(v, (float, np.floating))
                        else 'si' if v is True else 'no' if v is False else v for k, v in r.items()})


def load(root):
    root = Path(root)
    exigir(sha(root / DESIGN) == DESIGN_SHA, 'Diseño C modificado: versionar antes de calcular')
    design = json.loads((root / DESIGN).read_text())
    for name, expected in design['fuentes_sha256'].items():
        exigir(sha(root / name) == expected, 'Fuente C modificada: ' + name)
    e = contrato.cargar_entradas(root)  # Valida cardinalidad, roles, particiones y referencia histórica.
    table = {k[0]: r.copy() for k, r in e['tabla'].items()}
    ids = sorted(table)
    known = sorted(i for i in ids if table[i]['rendimiento_t_ha'] != '')
    reserved = sorted(set(ids) - set(known))
    exigir((len(ids), len(known), len(reserved)) == (197, 138, 59), 'Población C incompatible')
    return design, table, known, reserved, e


def tolerance(c):
    if c.startswith('prec_'): return 1e-6
    if c.startswith(('tmin_', 'tmax_')): return 1e-8
    if c == 'elevacion_media_m': return 1e-6
    if c == PEND: return 1e-8
    if c == 'area_ha_origen': return 1e-10
    if 'dias_' in c or 'dia_inicio' in c: return 0.
    return 1e-8 if 'integral' in c else 1e-9


def matrix(table, ids, columns):
    exigir(bool(ids) and len(ids) == len(set(ids)), 'IDs vacíos/duplicados')
    vals = []
    for pid in ids:
        row = []
        for c in columns:
            value = table[pid][c]
            if value == '':
                exigir(c == PEND, 'Faltante no admitido: ' + c)
                row.append(np.nan)
            else:
                v = contrato.numero(value, c)
                exigir(c != 'area_ha_origen' or v > 0, 'Área no positiva')
                row.append(v)
        vals.append(row)
    return np.asarray(vals, dtype=float)


def fit_space(table, train_ids, columns):
    """Sólo estadísticas de X; no accede al valor del rendimiento."""
    train_ids = tuple(sorted(train_ids))
    raw = matrix(table, train_ids, columns)
    x = raw.copy()
    med = None
    if PEND in columns:
        j = columns.index(PEND)
        exigir(np.isfinite(x[:, j]).any(), 'Pendiente sin dato en entrenamiento')
        med = float(np.nanmedian(x[:, j]))
        missing = np.isnan(x[:, j])
        x[missing, j] = med
        x = np.column_stack((x, missing.astype(float)))
    if 'area_ha_origen' in columns:
        j = columns.index('area_ha_origen')
        x[:, j] = np.log(x[:, j])
    mean = x.mean(axis=0)
    sd = x.std(axis=0, ddof=0)
    constant = sd == 0
    sd[constant] = 1.
    z = (x - mean) / sd
    municipalities = np.array([table[i]['municipio'] for i in train_ids])
    d = np.sqrt(np.mean((z[:, None, :] - z[None, :, :]) ** 2, axis=2))
    np.fill_diagonal(d, np.inf)
    d[municipalities[:, None] != municipalities[None, :]] = np.inf
    baseline = {}
    for mun in sorted(set(municipalities)):
        pick = municipalities == mun
        near = d[pick].min(axis=1)
        baseline[mun] = near[np.isfinite(near)]
    return dict(ids=train_ids, columns=list(columns), raw=raw, mean=mean, sd=sd, z=z,
                median=med, constant=constant, municipalities=municipalities, baseline=baseline)


def inspect_space(table, pid, state):
    exigir(pid not in state['ids'], 'La parcela evaluada aparece en entrenamiento')
    cols = state['columns']
    raw = matrix(table, [pid], cols)[0]
    x = raw.copy()
    if PEND in cols:
        j = cols.index(PEND); missing = bool(np.isnan(x[j]))
        if missing: x[j] = state['median']
        x = np.r_[x, float(missing)]
    if 'area_ha_origen' in cols:
        j = cols.index('area_ha_origen'); x[j] = np.log(x[j])
    z = (x - state['mean']) / state['sd']
    d = np.sqrt(np.mean((state['z'] - z) ** 2, axis=1))
    local = state['municipalities'] == table[pid]['municipio']
    j = int(np.argmin(d))
    loc = np.flatnonzero(local)
    jl = int(loc[np.argmin(d[loc])]) if len(loc) else None
    b = state['baseline'].get(table[pid]['municipio'], np.array([]))
    dl = float(d[jl]) if jl is not None else None
    q95 = float(np.quantile(b, .95, method='higher')) if len(b) else None
    percentile = float(100 * np.mean(b < dl - 1e-12)) if len(b) else None
    above = bool(dl > q95 + 1e-12) if len(b) else None
    out_global, out_local, absent = [], [], []
    for k, c in enumerate(cols):
        if np.isnan(raw[k]):
            absent.append(c); continue
        for indices, dest in [(np.arange(len(d)), out_global), (loc, out_local)]:
            a = state['raw'][indices, k]; a = a[np.isfinite(a)]
            if len(a) and (raw[k] < a.min() - tolerance(c) or raw[k] > a.max() + tolerance(c)):
                dest.append(c)
    return dict(n_entrenamiento=len(d), n_municipio=int(local.sum()),
        vecino_atributos_global=state['ids'][j], distancia_global=float(d[j]),
        vecino_atributos_municipio=state['ids'][jl] if jl is not None else '',
        distancia_municipio=dl, n_referencia_distancia=len(b),
        percentil_local_estricto=percentile, q95_local=q95, supera_q95_local=above,
        motivo_percentil_ausente='' if len(b) else 'sin_dos_etiquetas_locales',
        fuera_rango_global=';'.join(out_global), fuera_rango_municipio=';'.join(out_local),
        entradas_ausentes=';'.join(absent), constantes_en_entrenamiento=int(state['constant'].sum()))


def geometry(root, ids, design):
    package = Path(root) / 'data/raw/DataSet.zip'
    exigir(sha(package) == design['paquete_zip_sha256'], 'ZIP original diferente')
    with zipfile.ZipFile(package) as outer:
        names = [n for n in outer.namelist() if n.endswith('/Parcelas_Reto_AGC_CONJUNTO_70_30.zip')]
        exigir(len(names) == 1, 'Geometrías ZIP ambiguas')
        data = outer.read(names[0])
    provenance = json.loads((Path(root) / 'registro/t04/procedencia.json').read_text())
    exigir(hashlib.sha256(data).hexdigest() == provenance['geometrias']['sha256_zip'], 'ZIP interior diferente')
    with tempfile.TemporaryDirectory() as tmp, zipfile.ZipFile(io.BytesIO(data)) as inner:
        for suffix in ('.shp', '.shx', '.dbf', '.prj', '.cpg'):
            matches = [n for n in inner.namelist() if Path(n).name == 'Parcelas_Reto_AGC_CONJUNTO' + suffix]
            exigir(len(matches) == 1, 'Falta componente de geometría: ' + suffix)
            (Path(tmp) / Path(matches[0]).name).write_bytes(inner.read(matches[0]))
        g = gpd.read_file(Path(tmp) / 'Parcelas_Reto_AGC_CONJUNTO.shp', encoding='utf-8').set_index('ID_POLIGON')
    exigir(g.index.is_unique and set(g.index) == set(ids), 'IDs geométricos incompatibles')
    exigir(g.crs.to_epsg() == 4326, 'CRS original no identificado')
    g = g.loc[ids]
    exigir(bool(g.geometry.is_valid.all()) and not g.geometry.is_empty.any(), 'Geometría inválida: no reparar en C')
    geoms = g.geometry.to_crs(32614).to_numpy()
    edges = shapely.distance(geoms[:, None], geoms[None, :])
    exigir(np.isfinite(edges).all() and np.all(edges >= 0) and np.array_equal(edges, edges.T), 'Matriz geométrica inválida')
    cat = indexed(Path(root) / 'analisis/auditoria_catalogo_y_etiquetas/tablas/catalogo_parcelas.csv')
    lon = np.array([float(cat[(i,)]['centroide_lon']) for i in ids])
    lat = np.array([float(cat[(i,)]['centroide_lat']) for i in ids])
    n = len(ids)
    _, _, dist = pyproj.Geod(ellps='WGS84').inv(np.repeat(lon, n), np.repeat(lat, n), np.tile(lon, n), np.tile(lat, n))
    return dict(ids=tuple(ids), positions={pid: k for k, pid in enumerate(ids)},
                edges=edges, centers=np.asarray(dist).reshape(n, n))


def geo_support(table, pid, train_ids, geo, cell):
    train_ids = sorted(train_ids)
    exigir(bool(train_ids) and pid not in train_ids, 'Vecindad con propia fila o sin entrenamiento')
    i = geo['positions'][pid]; js = [geo['positions'][j] for j in train_ids]
    dist = geo['edges'][i, js]; centers = geo['centers'][i, js]
    local = np.array([table[j]['municipio'] == table[pid]['municipio'] for j in train_ids])
    jc = int(np.argmin(centers)); je = int(np.argmin(dist)); loc = np.flatnonzero(local)
    jl = int(loc[np.argmin(dist[loc])]) if len(loc) else None
    share = np.array([cell[j] == cell[pid] for j in train_ids])
    group = sum(table[j]['cultivo_origen'] == table[pid]['cultivo_origen'] for j in train_ids)
    return dict(n_etiquetas_municipio=int(local.sum()), n_etiquetas_grupo=group,
        fuente_referencia='municipio' if local.any() else 'grupo' if group else 'global',
        soporte_municipal_menos4=int(local.sum()) < 4,
        conocida_mas_cercana_centro=train_ids[jc], distancia_centros_m=float(centers[jc]),
        conocida_mas_cercana_orilla=train_ids[je], distancia_orillas_m=float(dist[je]),
        conocida_local_mas_cercana_orilla=train_ids[jl] if jl is not None else '',
        distancia_orillas_municipio_m=float(dist[jl]) if jl is not None else None,
        n_vecinas20_general=int((dist < 20).sum()), n_vecinas20_municipio=int(((dist < 20) & local).sum()),
        celda_principal=cell[pid], n_etiquetas_celda_principal=int(share.sum()),
        n_etiquetas_celda_y_municipio=int((share & local).sum()))


def breakdown(records, dimensions):
    output = []
    for dimension in dimensions:
        groups = {}
        for r in records:
            value = r[dimension]
            if value is None: value = 'no_definido'
            groups.setdefault((r['escenario'], r.get('representacion', ''), str(value)), []).append(r)
        for (scenario, representation, value), rs in sorted(groups.items()):
            for subset in ('todas', 'sin_respaldo'):
                picked = [r for r in rs if subset == 'todas' or r['fuente_referencia'] == 'municipio']
                if not picked: continue
                errors = [r['error_historico'] for r in picked]
                output.append(dict(escenario=scenario, representacion=representation, subconjunto=subset,
                    dimension=dimension, categoria=value, n_registros_oof=len(picked),
                    n_parcelas=len({r['id_parcela'] for r in picked}),
                    MAE_historico=math.fsum(abs(x) for x in errors) / len(errors),
                    RMSE_historico=math.sqrt(math.fsum(x*x for x in errors) / len(errors)),
                    sesgo_historico=math.fsum(errors) / len(errors)))
    return output


def run(root, destination, detail=None):
    root, destination = Path(root), Path(destination)
    exigir(not destination.exists(), 'Destino existente: conservar evidencia anterior')
    if detail is not None: exigir(not Path(detail).exists(), 'Detalle existente: no reemplazar')
    design, table, known, reserved, e = load(root)
    ids = sorted(table)
    geo = geometry(root, ids, design)
    t02 = indexed(root / 'analisis/auditoria_catalogo_y_etiquetas/tablas/soporte_por_parcela.csv')
    cat = indexed(root / 'analisis/auditoria_catalogo_y_etiquetas/tablas/catalogo_parcelas.csv')
    q = indexed(root / 'registro/t07/calidad_parcelas.csv')
    relief = indexed(root / 'registro/t07/calidad_relieve.csv')
    sat = indexed(root / 'registro/t07/calidad_satelite.csv', ('id_parcela', 'sensor', 'ventana'))
    climate = indexed(root / 'registro/t07/calidad_ventanas.csv', ('id_parcela', 'ventana', 'variable'))
    prior = indexed(root / 'registro/t09/aplicabilidad_59.csv')
    cell = {i: t02[(i,)]['celda_clima_principal'] for i in ids}
    for r in e['particiones']:
        exigir(cell[r['ID_POLIGONO']] == r['celda_chirps'], 'Celda T02/T03 diferente')
    baseline = {(r['escenario'], int(r['repeticion']), r['ID_POLIGONO']): r
                for r in rows(root / 'registro/t03/predicciones_oof_referencias_media_mun__resp_grupo.csv')}
    inputs59, inputsoof, contexts, states = [], [], [], []
    for scenario in ('A', 'B', '59'):
        for repetition in (range(1, 6) if scenario != '59' else [0]):
            for fold in (range(5) if scenario != '59' else [-1]):
                if scenario == '59': train, test = known, reserved
                else:
                    column = 'particion_principal' if scenario == 'A' else 'particion_espacial'
                    part = [r for r in e['particiones'] if int(r['repeticion']) == repetition]
                    train = sorted(r['ID_POLIGONO'] for r in part if int(r[column]) != fold)
                    test = sorted(r['ID_POLIGONO'] for r in part if int(r[column]) == fold)
                exigir(not set(train) & set(test), 'IDs de evaluación en entrenamiento')
                geo_rows = {}
                for pid in test:
                    gs = geo_support(table, pid, train, geo, cell)
                    if scenario != '59':
                        old = baseline[(scenario, repetition, pid)]
                        exigir(gs['fuente_referencia'] == old['fuente'], 'Respaldo histórico distinto')
                        exigir(float(old['real']) == float(table[pid]['rendimiento_t_ha']), 'Etiqueta OOF distinta')
                        gs = dict(id_parcela=pid, municipio=table[pid]['municipio'], escenario=scenario,
                            repeticion=repetition, particion=fold, **gs,
                            alerta_contorno=flag(q[(pid,)]['alerta_contorno_t03_bis']),
                            error_historico=float(old['prediccion']) - float(old['real']))
                        contexts.append(gs)
                    geo_rows[pid] = gs
                for rep in design['representaciones']:
                    state = fit_space(table, train, rep['columnas'])
                    states.append(dict(escenario=scenario, repeticion=repetition, particion=fold,
                        representacion=rep['id'], ids=list(state['ids']), media=state['mean'].tolist(),
                        sd=state['sd'].tolist(), mediana_pendiente=state['median']))
                    for pid in test:
                        result = dict(id_parcela=pid, municipio=table[pid]['municipio'],
                            representacion=rep['id'], **inspect_space(table, pid, state))
                        if scenario == '59': inputs59.append(result)
                        else:
                            old = geo_rows[pid]
                            inputsoof.append(dict(**result, escenario=scenario, repeticion=repetition,
                                particion=fold, fuente_referencia=old['fuente_referencia'],
                                error_historico=old['error_historico']))

    profiles, reconciled = [], []
    for pid in reserved:
        gs = geo_support(table, pid, known, geo, cell)
        r, cr, qr = table[pid], cat[(pid,)], relief[(pid,)]
        selected = [a for a in inputs59 if a['id_parcela'] == pid]
        profile = dict(id_parcela=pid, municipio=r['municipio'], **gs,
            area_ha_origen=float(r['area_ha_origen']), area_ha_geodesica=float(cr['area_ha_geodesica']),
            contorno_categoria=cr['contorno_categoria'], alerta_contorno=flag(q[(pid,)]['alerta_contorno_t03_bis']),
            centroide_dentro_parcela=flag(qr['centroide_dentro_parcela']),
            cobertura_elevacion=float(qr['elevacion_cobertura_valida']),
            cobertura_pendiente=float(qr['pendiente_cobertura_valida']),
            entradas_candidatas_ausentes=';'.join(sorted({c for a in selected for c in a['entradas_ausentes'].split(';') if c})),
            representaciones_fuera_global=';'.join(a['representacion'] for a in selected if a['fuera_rango_global']),
            representaciones_fuera_municipio=';'.join(a['representacion'] for a in selected if a['fuera_rango_municipio']),
            representaciones_supera_q95=';'.join(a['representacion'] for a in selected if a['supera_q95_local']),
            clima_completo=all(climate[(pid, w, v)]['estado'] == 'completa'
                               for w in ('abr_oct', 'jun_oct') for v in ('PREC','Tmin','Tmax')),
            alcance='reconstruccion_retrospectiva_2025_disponibilidad_historica_no_acreditada')
        for sensor, prefix in [('Planet','pl'), ('Sentinel-2','s2')]:
            for window in ('abr_oct','jun_oct'):
                sq = sat[(pid, sensor, window)]
                for dest, source in [('capturas','capturas'), ('hueco_max_dias','hueco_max_dias'),
                                     ('meses_sin_captura','meses_sin_captura')]:
                    profile[f'{prefix}_{dest}_{window}'] = int(float(sq[source]))
            profile[prefix+'_ultima_captura'] = sat[(pid,sensor,'abr_oct')]['ultima']
            profile[prefix+'_ndvi_al_corte_presente'] = r[prefix+'_ndvi_al_corte'] != ''
        reasons = []
        if gs['soporte_municipal_menos4']: reasons.append('pocas_etiquetas_locales')
        if gs['n_etiquetas_celda_principal'] == 0: reasons.append('celda_principal_sin_etiquetas')
        if profile['alerta_contorno']: reasons.append('contorno_requiere_revision_visual')
        if profile['representaciones_fuera_global']: reasons.append('entradas_fuera_rango_global_en_bloques_indicados')
        if profile['representaciones_supera_q95']: reasons.append('combinacion_poco_representada_en_bloques_indicados')
        profile['motivos_revision'] = ';'.join(reasons)
        profile['mensaje_soporte'] = f"Municipio con {gs['n_etiquetas_municipio']} etiquetas; " + (
            f"{gs['n_vecinas20_municipio']} vecinas etiquetadas locales a menos de20m. " if gs['n_vecinas20_municipio'] else
            'Sin vecina etiquetada local a menos de20m. ') + 'El soporte no garantiza el rendimiento.'
        profiles.append(profile)
        previous = prior[(pid,)]
        agree = dict(id_parcela=pid,
            n_municipio_igual_T09=gs['n_etiquetas_municipio'] == int(previous['n_etiquetas_municipio']),
            referencia_igual_T09=gs['fuente_referencia'] == previous['fuente_referencia_prevista'],
            clima_completo_igual_T09=profile['clima_completo'] == flag(previous['clima_completo']),
            delta_distancia_orillas_T02_m=gs['distancia_orillas_m'] - float(t02[(pid,)]['distancia_orillas_m']),
            delta_distancia_centros_T02_m=gs['distancia_centros_m'] - float(t02[(pid,)]['distancia_centros_m']))
        for window in ('abr_oct', 'jun_oct'):
            cs = next(a for a in selected if a['representacion'] == 'C__'+window)
            # Igualdad literal de las tres columnas, misma definición de T09; RMS difiere sólo en sqrt(3).
            cols = next(a['columnas'] for a in design['representaciones'] if a['id'] == 'C__'+window)
            exact = any(all(float(table[j][c]) == float(r[c]) for c in cols) for j in known)
            profile['perfil_clima_exacto_'+window] = exact
            agree['perfil_exacto_igual_T09_'+window] = exact == flag(previous['perfil_observado_'+window])
            agree['delta_distancia_clima_T09_'+window] = cs['distancia_global'] * math.sqrt(3) - float(previous['distancia_clima_estandarizada_min_'+window])
        exigir(all(v for k,v in agree.items() if '_igual_' in k), 'Diferencia de definición T02/T09 no resuelta')
        exigir(abs(agree['delta_distancia_orillas_T02_m']) <= .010001, 'Distancia de orillas no reproduce T02')
        exigir(abs(agree['delta_distancia_centros_T02_m']) <= .100001, 'Distancia entre centros no reproduce T02')
        exigir(all(abs(v) < 1e-9 for k,v in agree.items() if k.startswith('delta_distancia_clima')), 'Clima T09 diferente')
        reconciled.append(agree)

    municipality_rows = []
    for mun in sorted({r['municipio'] for r in table.values()}):
        ps = [p for p in profiles if p['municipio'] == mun]
        municipality_rows.append(dict(municipio=mun, n_etiquetas=sum(table[i]['municipio']==mun for i in known),
            n_reservadas=len(ps), reservadas_vecina20_local=sum(p['n_vecinas20_municipio'] > 0 for p in ps),
            reservadas_celda_nueva=sum(p['n_etiquetas_celda_principal'] == 0 for p in ps),
            reservadas_fuera_global=sum(bool(p['representaciones_fuera_global']) for p in ps),
            reservadas_con_alerta_contorno=sum(p['alerta_contorno'] for p in ps)))
    error_summary = breakdown(contexts, ['soporte_municipal_menos4', 'n_vecinas20_municipio', 'alerta_contorno'])
    error_summary += breakdown(inputsoof, ['supera_q95_local', 'motivo_percentil_ausente'])
    summary = dict(version=VERSION, n_reservadas=len(profiles), n_etiquetadas=len(known),
        n_contextos_externos=50, n_contextos_parcela_oof=len(contexts),
        n_entradas59=len(inputs59), n_entradas_oof=len(inputsoof),
        municipio_representado=sum(p['n_etiquetas_municipio']>0 for p in profiles),
        soporte_municipal_menos4=sum(p['soporte_municipal_menos4'] for p in profiles),
        vecina20_general=sum(p['n_vecinas20_general']>0 for p in profiles),
        vecina20_municipio=sum(p['n_vecinas20_municipio']>0 for p in profiles),
        celda_principal_nueva=sum(p['n_etiquetas_celda_principal']==0 for p in profiles),
        clima_exacto={w:sum(p['perfil_clima_exacto_'+w] for p in profiles) for w in ('abr_oct','jun_oct')},
        fuera_global_algun_bloque=sum(bool(p['representaciones_fuera_global']) for p in profiles),
        supera_q95_algun_bloque=sum(bool(p['representaciones_supera_q95']) for p in profiles),
        alerta_contorno=sum(p['alerta_contorno'] for p in profiles),
        hay_modelo_nuevo=False, hay_predicciones_nuevas=False,
        unidad='parcela_2025_no_repeticion_ni_fila_de_soporte',
        advertencia='Soporte descriptivo; no probabilidad ni intervalo de rendimiento; no validacion temporal.')
    compact = {'perfil_59.csv': profiles, 'entradas_59.csv': inputs59, 'contextos_oof_138.csv': contexts,
        'error_por_soporte.csv': error_summary, 'conciliacion_t02_t09.csv': reconciled, 'resumen_municipio.csv': municipality_rows}
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=destination.name+'.', dir=destination.parent))
    try:
        for name, rs in compact.items(): csv_out(temporary/name, rs)
        csv_out(temporary/'diccionario.csv', dictionary(compact))
        dump(temporary/'resumen.json', summary)
        manifest = dict(version=VERSION, diseno_sha256=DESIGN_SHA, fuentes_sha256=design['fuentes_sha256'],
            paquete_zip_sha256=design['paquete_zip_sha256'],
            archivos_sha256={p.name:sha(p) for p in sorted(temporary.iterdir())},
            software=dict(python=platform.python_version(), numpy=np.__version__, geopandas=gpd.__version__,
                          shapely=shapely.__version__, pyproj=pyproj.__version__, PROJ=pyproj.proj_version_str),
            scripts_sha256={'scripts/diagnostico_aplicabilidad59.py':sha(Path(__file__))},
            estado='tecnicamente_generado_pendiente_revision_independiente',
            T15_ejecutado=False, T18_ejecutado=False)
        dump(temporary/'manifest.json', manifest)
        if detail is not None:
            detail = Path(detail); detail.mkdir(parents=True)
            csv_out(detail/'entradas_oof_138.csv', inputsoof)
            dump(detail/'estados_soporte.json', states)
            np.savez(detail/'distancias_geometricas.npz', ids=np.array(ids), orillas=geo['edges'], centros=geo['centers'])
        os.replace(temporary, destination)
    finally:
        if temporary.exists(): shutil.rmtree(temporary)
    return summary


def dictionary(tables):
    definitions = {
        'municipio':('Municipio original conciliado con T02; agrupación territorial, no etiqueta de rendimiento.','nombre','no_admitido'),
        'representacion':('Bloques y ventana cuyas entradas se inspeccionan; no es un modelo nuevo evaluado.','ID_representacion','no_aplica_en_desgloses_geograficos'),
        'escenario':('A municipal conocido o B separación por celda, evaluación histórica T03.','categoria_A_B','no_admitido'),
        'repeticion':('Repetición T03 de1 a5; reutiliza las mismas parcelas.','entero1_5','no_admitido'),
        'particion':('Partición externa T03 de0 a4.','entero0_4','no_admitido'),
        'n_entrenamiento':('IDs del entrenamiento usado para aprender escala/mediana de X.','parcelas','no_admitido'),
        'n_municipio':('IDs del mismo municipio disponibles en ese entrenamiento.','parcelas','no_admitido'),
        'n_etiquetas_municipio':('Etiquetas locales disponibles:138 para reservadas; sólo entrenamiento externo para OOF.','parcelas','no_admitido'),
        'n_etiquetas_grupo':('IDs del mismo grupo de registro Cebada/CEBADA disponibles en entrenamiento; no interpretación agronómica.','parcelas','no_admitido'),
        'fuente_referencia':('Nivel municipal, grupo o global aplicable según disponibilidad de IDs; coincide con T08.','categoria','no_admitido'),
        'n_vecinas20_general':('Parcelas etiquetadas del entrenamiento con distancia entre orillas <20m, cualquier municipio.','parcelas','no_admitido'),
        'n_vecinas20_municipio':('Vecinas <20m del mismo municipio y entrenamiento; no bandera global T07.','parcelas','no_admitido'),
        'n_etiquetas_celda_principal':('Etiquetas del entrenamiento cuya celda principal T02 coincide; no todas las intersecciones.','parcelas','no_admitido'),
        'n_etiquetas_celda_y_municipio':('Etiquetas de entrenamiento con igual municipio y celda principal.','parcelas','no_admitido'),
        'distancia_orillas_m':('Distancia mínima al polígono etiquetado del entrenamiento en EPSG32614.','m','no_admitido'),
        'distancia_orillas_municipio_m':('Distancia mínima entre orillas hacia una etiqueta local del entrenamiento.','m','sin_etiquetas_locales'),
        'distancia_centros_m':('Mínima distancia geodésica WGS84 entre centroides T02 hacia entrenamiento.','m','no_admitido'),
        'alerta_contorno':('Bandera T03bis/T07 de contorno para inspección; no daño confirmado ni regla de exclusión.','booleano','no_admitido'),
        'contorno_categoria':('Categoría visual de T02, atlas sin fecha acreditada de2025.','categoria_A_B_C','no_admitido'),
        'centroide_dentro_parcela':('El centroide utilizado para la comparación de relieve cae dentro de la parcela.','booleano','no_admitido'),
        'cobertura_elevacion':('Fracción con elevación válida de T05/T07; conservar literal, incluso redondeo próximo a1.','fraccion','no_admitido'),
        'cobertura_pendiente':('Fracción con pendiente válida de T05/T07; no mide incertidumbre del rendimiento.','fraccion','no_admitido'),
        'area_ha_origen':('Área declarada original; denominador del rendimiento aún no confirmado.','ha','no_admitido'),
        'area_ha_geodesica':('Área geodésica de T02, conservada con su redondeo publicado.','ha','no_admitido'),
        'entradas_candidatas_ausentes':('Unión de faltantes originales de las representaciones indicadas, antes de imputar para distancia.','lista_columnas','ninguna'),
        'representaciones_fuera_global':('Representaciones con alguna entrada fuera del rango global de entrenamiento, con tolerancias por unidad.','lista','ninguna'),
        'representaciones_fuera_municipio':('Representaciones con entrada fuera del rango local; n local pequeño limita interpretación.','lista','ninguna'),
        'clima_completo':('Las seis combinaciones variable/ventana de T07 tienen estado completa.','booleano','no_admitido'),
        'alcance':('Reconstrucción2025 con disponibilidad histórica de publicación no acreditada; no validación futura.','texto','no_admitido'),
        'mensaje_soporte':('Mensaje descriptivo propuesto para la app; no predicción ni garantía.','texto','no_admitido'),
        'motivo_percentil_ausente':('Explica por qué no existe referencia LOO local, incluido municipio con una etiqueta.','texto','percentil_disponible'),
        'constantes_en_entrenamiento':('Columnas transformadas, incluido indicador D020, con desviación exactamente cero; escala fijada a1.','columnas','no_admitido'),
        'dimension':('Condición usada para agrupar errores históricos; puede variar por repetición/entrenamiento.','columna','no_admitido'),
        'categoria':('Valor de la dimensión del grupo; True/False indican sí/no y no_definido ausencia de referencia.','texto','categoria_vacia_legitima'),
        'subconjunto':('Todas las evaluadas o sin_respaldo: municipio presente en el entrenamiento correspondiente.','categoria','no_admitido'),
        'n_etiquetas':('Total de parcelas etiquetadas del municipio en el catálogo de138.','parcelas','no_admitido'),
        'n_reservadas':('Reservadas del municipio; puede ser cero.','parcelas','no_admitido'),
        'reservadas_vecina20_local':('Reservadas del municipio con al menos una etiquetada local <20m.','parcelas','no_admitido'),
        'reservadas_celda_nueva':('Reservadas cuya celda principal no aparece entre las138.','parcelas','no_admitido'),
        'reservadas_fuera_global':('Reservadas con alguna entrada candidata fuera del rango global, no número de modelos fallidos.','parcelas','no_admitido'),
        'reservadas_con_alerta_contorno':('Reservadas con bandera de revisión de contorno T03bis/T07.','parcelas','no_admitido'),
        'id_parcela':('Identificador original; nunca predictor automático.','ID','no_admitido'),
        'distancia_global':('Distancia RMS estandarizada al vecino de atributos global.','adimensional','no_admitido'),
        'distancia_municipio':('Distancia RMS al vecino de atributos del mismo municipio.','adimensional','sin_etiquetas_locales'),
        'percentil_local_estricto':('Porcentaje de distancias LOO locales estrictamente menores, con tolerancia1e-12. No probabilidad.','porcentaje','sin_dos_etiquetas_locales'),
        'q95_local':('Cuantil95 higher de distancias LOO del entrenamiento local.','adimensional','sin_dos_etiquetas_locales'),
        'supera_q95_local':('Distancia local mayor que q95+1e-12; diagnóstico no regla de rechazo.','booleano','sin_dos_etiquetas_locales'),
        'fuera_rango_global':('Columnas originales fuera de rango del entrenamiento global.','lista_columnas','ninguna'),
        'fuera_rango_municipio':('Columnas originales fuera de rango local; interpretar junto a n_municipio.','lista_columnas','ninguna_o_sin_etiquetas_locales'),
        'entradas_ausentes':('Columnas ausentes antes de imputar en la copia para distancia.','lista_columnas','ninguna'),
        'n_referencia_distancia':('Filas locales de entrenamiento con otra fila local para distancia LOO.','filas','no_admitido'),
        'error_historico':('Predicción T08 existente menos etiqueta original; no nueva evaluación.','t/ha','no_admitido'),
        'MAE_historico':('Media de pérdidas absolutas de los registros históricos del grupo.','t/ha','sin_registros'),
        'RMSE_historico':('Raíz de media cuadrática de errores históricos del grupo.','t/ha','sin_registros'),
        'sesgo_historico':('Media de predicción menos real de registros históricos del grupo.','t/ha','sin_registros'),
        'n_registros_oof':('Registros parcela/repetición del grupo; dependientes.','registros','no_admitido'),
        'n_parcelas':('IDs distintos del grupo, que pueden aparecer en otros grupos entre repeticiones.','parcelas','no_admitido'),
        'celda_principal':('Celda de lluvia principal de T02; no conjunto completo de celdas tocadas.','ID_celda','no_admitido'),
        'motivos_revision':('Razones descriptivas de revisión; no suma de riesgo calibrada.','lista','sin_motivo_especifico'),
        'representaciones_supera_q95':('Representaciones que superan su referencia local de distancia, no modelos fallidos.','lista','ninguna_o_percentil_no_definido'),
        'soporte_municipal_menos4':('Menos de cuatro etiquetas del municipio en el entrenamiento pertinente.','booleano','no_admitido'),
    }
    output = []
    for name, rs in tables.items():
        for c in rs[0]:
            meaning, unit, empty = definitions.get(c, (c.replace('_',' '), 'texto', 'no_admitido'))
            if c.startswith(('vecino_atributos_','conocida_')):
                meaning='ID del vecino de entrenamiento que minimiza la distancia indicada; no se usa como predictor.'
                unit='ID';empty='sin_etiquetas_locales' if ('local' in c or 'municipio' in c) else 'no_admitido'
            if c.startswith(('pl_','s2_')):
                meaning='Calidad/observación T06/T07 del sensor '+('Planet' if c.startswith('pl_') else 'Sentinel2')+' en la ventana indicada; no rendimiento.'
                if 'hueco_max' in c:unit='dias'
                elif 'meses_sin' in c:unit='meses'
                elif 'capturas' in c:unit='capturas'
                elif 'ultima' in c:unit='fecha_ISO';empty='sin_captura_valida'
                else:unit='booleano'
            if c.startswith('perfil_clima_exacto'):
                meaning='Las tres entradas climáticas de la ventana coinciden literalmente con alguna etiquetada; no igualdad de rendimiento.';unit='booleano'
            if '_igual_T09' in c:
                meaning='La definición indicada coincide con el diagnóstico T09 publicado.';unit='booleano'
            if c.startswith('delta_distancia_'):
                meaning='Valor C menos valor publicado T02/T09; distinguir el redondeo geométrico de la equivalencia sqrt3 del clima.'
            if 'distancia_' in c and c.endswith('_m'): unit = 'm'
            if c.startswith('delta_distancia_clima'): unit = 'adimensional_norma_Euclidea_T09'
            if c.startswith('area_ha'): unit = 'ha'
            if 'cobertura' in c: unit = 'fraccion_0_1'
            if c.startswith('n_'): unit = 'conteo'
            if 'captura' in c and 'ultima' in c: unit = 'fecha_ISO'
            output.append(dict(archivo=name, columna=c, significado=meaning, unidad=unit, significado_vacio=empty))
    return output


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--raiz', type=Path, default=RAIZ)
    ap.add_argument('--salida', type=Path, required=True)
    ap.add_argument('--detalle', type=Path)
    args = ap.parse_args()
    print(json.dumps(run(args.raiz, args.salida, args.detalle), ensure_ascii=False, indent=2))


if __name__ == '__main__': main()
