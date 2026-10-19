"""Reproduce media/mediana T08 y su contraste con T15; no elige ganador ni exporta 59.

No importa productores/modelos del repo. Reconstruye referencias con Fraction y
evalúa las OOF históricas completas, sin modificar sus predicciones.
"""
import argparse
import csv
import hashlib
import json
import math
import statistics
from collections import defaultdict
from fractions import Fraction
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
BASE = 'media_mun__resp_grupo'
MED = 'mediana_mun__resp_grupo'
TOL = 1e-12


def exigir(ok, mensaje):
    if not ok:
        raise ValueError(mensaje)


def leer_csv(path):
    with Path(path).open(encoding='utf-8-sig', newline='') as handle:
        return list(csv.DictReader(handle))


def referencia(ids, objetivo, tabla, estadistico):
    """Sólo lee rendimientos de los IDs del entrenamiento; objetivo debe estar fuera."""
    exigir(estadistico in ('media', 'mediana'), 'Estadístico ajeno')
    exigir(ids and len(ids) == len(set(ids)), 'Entrenamiento vacío o repetido')
    exigir(objetivo not in ids, 'Objetivo dentro del entrenamiento')
    exigir(all(tabla[i]['rendimiento_t_ha'] != '' for i in ids), 'Reservada en entrenamiento')
    pool_mun = [i for i in ids if tabla[i]['municipio'] == tabla[objetivo]['municipio']]
    pool_grupo = [i for i in ids if tabla[i]['cultivo_origen'] == tabla[objetivo]['cultivo_origen']]
    for fuente, pool in [('municipio', pool_mun), ('grupo', pool_grupo), ('global', ids)]:
        if pool:
            values = [Fraction(tabla[i]['rendimiento_t_ha']) for i in pool]
            result = sum(values, Fraction(0))/len(values) if estadistico == 'media' else statistics.median(values)
            return result, fuente, pool
    raise ValueError('Sin referencia')


def metricas(rows):
    exigir(rows, 'Métricas sin casos')
    real = [float(r['real']) for r in rows]
    errors = [float(r['prediccion'])-y for r, y in zip(rows, real)]
    center = statistics.fmean(real)
    ss = math.fsum((y-center)**2 for y in real)
    return {'MAE': statistics.fmean(abs(e) for e in errors),
            'RMSE': math.sqrt(statistics.fmean(e*e for e in errors)),
            'R2': None if len(set(real)) == 1 else 1-math.fsum(e*e for e in errors)/ss,
            'sesgo': statistics.fmean(errors)}


def resumen(rows):
    ids, reps = defaultdict(list), defaultdict(list)
    for row in rows:
        ids[row['ID_POLIGONO']].append(row)
        reps[int(row['repeticion'])].append(row)
    individual = [metricas(v) for _, v in sorted(ids.items())]
    repeated = [metricas(v) for _, v in sorted(reps.items())]
    return {'n_parcelas': len(ids), 'n_predicciones': len(rows),
            'MAE_por_parcela': statistics.fmean(m['MAE'] for m in individual),
            'RMSE_igual_peso_parcela': math.sqrt(statistics.fmean(m['RMSE']**2 for m in individual)),
            **{key+'_media_repeticiones': None if any(m[key] is None for m in repeated) else statistics.fmean(m[key] for m in repeated) for key in ['MAE', 'RMSE', 'R2', 'sesgo']},
            'p90_MAE_parcela': float(np.percentile([m['MAE'] for m in individual], 90)),
            'n_parcelas_MAE_mayor_1': sum(m['MAE'] > 1 for m in individual)}


def bootstrap_celdas(diferencias, celdas, n_boot=5000):
    groups = defaultdict(list)
    for pid in sorted(diferencias):
        groups[celdas[pid]].append(diferencias[pid])
    blocks = sorted(groups)
    sums = np.array([math.fsum(groups[c]) for c in blocks])
    sizes = np.array([len(groups[c]) for c in blocks])
    rng = np.random.RandomState(20261006)
    draws = rng.randint(len(blocks), size=(n_boot, len(blocks)))
    samples = sums[draws].sum(1)/sizes[draws].sum(1)
    return blocks, samples


def ejecutar(salida):
    salida = Path(salida).resolve()
    exigir(not salida.exists(), 'La salida existe; usar un destino nuevo')
    exigir(not salida.is_relative_to(ROOT) or salida.is_relative_to(ROOT/'reports'), 'Dentro del repo sólo se escribe en reports/')
    design_path = ROOT/'registro/t16_revision_mediana/diseno_revision.json'
    design = json.loads(design_path.read_text())
    for rel, expected in design['fuentes_sha256'].items():
        exigir(hashlib.sha256((ROOT/rel).read_bytes()).hexdigest() == expected, 'Fuente distinta: '+rel)
    table_rows = leer_csv(ROOT/'registro/t07/tabla_comun.csv')
    table = {r['id_parcela']:r for r in table_rows}
    known = {i for i, r in table.items() if r['rendimiento_t_ha'] != ''}
    exigir(len(table_rows) == len(table) == 197 and len(known) == 138, 'Universo distinto')
    parts = leer_csv(ROOT/'registro/t03/particiones.csv')
    quality = {r['id_parcela']:r for r in leer_csv(ROOT/'registro/t07/calidad_parcelas.csv')}
    alerts = {i for i in known if quality[i]['alerta_contorno_t03_bis'] == 'si'}
    exigir(len(alerts) == 24, 'Sensibilidad sin24 distinta')
    cells = {r['ID_POLIGONO']:r['celda_chirps'] for r in parts}
    common_rows = [r for r in leer_csv(ROOT/'registro/t15_resultados/predicciones_oof.csv') if r['candidato'] == BASE]
    common = {(r['escenario'],r['repeticion'],r['ID_POLIGONO']):r for r in common_rows}
    exigir(len(common) == len(common_rows) == 1380, 'Referencia T15 incompleta')
    all_rows, per_fit = {}, []
    reconstructed_max, common_max = 0., 0.
    comparisons = 0
    for candidate, stat in [(BASE, 'media'), (MED, 'mediana')]:
        rows = leer_csv(ROOT/f'registro/t03/predicciones_oof_referencias_{candidate}.csv')
        idx = {(r['escenario'],r['repeticion'],r['ID_POLIGONO']):r for r in rows}
        exigir(len(rows) == len(idx) == 1380, 'OOF incompletas o repetidas')
        exigir(set(idx) == set(common), 'Claves distintas de T15')
        for esc, col in [('A','particion_principal'), ('B','particion_espacial')]:
            for rep in range(1, 6):
                pp = [r for r in parts if int(r['repeticion']) == rep]
                exigir(len(pp) == 138 and {r['ID_POLIGONO'] for r in pp} == known, 'Particiones incompletas')
                for fold in range(5):
                    train = sorted(r['ID_POLIGONO'] for r in pp if int(r[col]) != fold)
                    test = sorted(r['ID_POLIGONO'] for r in pp if int(r[col]) == fold)
                    exigir(set(train).isdisjoint(test) and set(train)|set(test) == known, 'Partición inválida')
                    if esc == 'B':
                        exigir({cells[i] for i in train}.isdisjoint(cells[i] for i in test), 'Solapamiento de celdas B')
                    for pid in test:
                        expected, source, pool = referencia(train, pid, table, stat)
                        row = idx[esc, str(rep), pid]
                        exigir(int(row['particion']) == fold and row['fuente'] == source and row['candidato'] == candidate, 'Máscara/candidato/partición distintos')
                        exigir(abs(float(row['real'])-float(table[pid]['rendimiento_t_ha'])) <= TOL, 'Etiqueta distinta')
                        delta = abs(float(expected)-float(row['prediccion']))
                        reconstructed_max = max(reconstructed_max, delta)
                        exigir(delta <= TOL, 'Referencia no reproduce entrenamiento')
                        exigir(pid not in pool and set(pool) <= set(train), 'Fuga de referencia')
                        if candidate == BASE:
                            other = common[esc, str(rep), pid]
                            exigir(row['fuente'] == other['fuente'] and row['particion'] == other['particion'], 'Máscara T15 distinta')
                            delta = abs(float(row['prediccion'])-float(other['prediccion']))
                            common_max = max(common_max, delta)
                            exigir(delta <= TOL, 'Media T08/T15 distinta')
                        comparisons += 1
                    per_fit.append({'candidato':candidate,'escenario':esc,'repeticion':rep,'particion':fold,'n_entrenamiento':len(train),'n_validacion':len(test),'ids_entrenamiento':';'.join(train),'ids_validacion':';'.join(test),'sin_59':True})
        all_rows[candidate] = rows

    metrics, repeated, contrasts, by_municipio, differences, influence = [], [], [], [], [], []
    for esc in ['A', 'B']:
        for subset in ['todas', 'sin_respaldo']:
            for sensitivity in ['completa', 'sin24']:
                picked = {c:[r for r in all_rows[c] if r['escenario'] == esc and (subset == 'todas' or r['fuente'] == 'municipio') and (sensitivity == 'completa' or r['ID_POLIGONO'] not in alerts)] for c in [BASE, MED]}
                identity = dict(escenario=esc,subconjunto=subset,sensibilidad=sensitivity)
                for c, rows in picked.items():
                    metrics.append({**identity,'candidato':c,**resumen(rows)})
                    for rep in range(1,6):
                        rr = [r for r in rows if int(r['repeticion']) == rep]
                        repeated.append({**identity,'candidato':c,'repeticion':rep,'n_predicciones':len(rr),**metricas(rr)})
                a = {(r['ID_POLIGONO'],r['repeticion']):r for r in picked[BASE]}
                b = {(r['ID_POLIGONO'],r['repeticion']):r for r in picked[MED]}
                exigir(set(a) == set(b), 'Población emparejada distinta')
                per_id, per_rep = defaultdict(list), defaultdict(list)
                for key in sorted(a):
                    y = float(a[key]['real'])
                    d = abs(float(b[key]['prediccion'])-y)-abs(float(a[key]['prediccion'])-y)
                    per_id[key[0]].append(d);per_rep[int(key[1])].append(d)
                diff = {i:statistics.fmean(v) for i,v in sorted(per_id.items())}
                blocks, bs = bootstrap_celdas(diff,cells)
                low, high = np.percentile(bs,[2.5,97.5])
                dmae = statistics.fmean(diff.values())
                drmse = statistics.fmean(metricas([r for r in picked[MED] if int(r['repeticion']) == k])['RMSE']-metricas([r for r in picked[BASE] if int(r['repeticion']) == k])['RMSE'] for k in range(1,6))
                signs = sum(statistics.fmean(per_rep[k]) < 0 for k in range(1,6))
                conditions = {'baja_MAE_001':dmae <= -.01,'IC_celdas_excluye_0':high < 0,'mejora_4_de_5':signs >= 4,'RMSE_no_empeora_mas_001':drmse <= .01}
                contrasts.append({**identity,'n_parcelas':len(diff),'n_predicciones':len(a),'n_celdas':len(blocks),'dMAE_por_parcela':dmae,'dRMSE_media_repeticiones':drmse,'IC95_celdas_inf':float(low),'IC95_celdas_sup':float(high),'repeticiones_mejoran':signs,**conditions,'cumple_regla':all(conditions.values()),'promocion_principal':esc=='A' and subset=='sin_respaldo' and sensitivity=='completa' and all(conditions.values()),'fraccion_remuestras_negativas_no_probabilidad_exito':float((bs < 0).mean())})
                if sensitivity == 'completa':
                    for pid, d in diff.items():
                        differences.append({**identity,'id_parcela':pid,'municipio':table[pid]['municipio'],'celda_chirps':cells[pid],'n_repeticiones':len(per_id[pid]),'dMAE_mediana_menos_media':d,'mejora_con_tolerancia':d < -TOL,'empeora_con_tolerancia':d > TOL})
                    for mun in sorted({table[i]['municipio'] for i in diff}):
                        ids = {i for i in diff if table[i]['municipio'] == mun}
                        rbase = [r for r in picked[BASE] if r['ID_POLIGONO'] in ids]
                        rmed = [r for r in picked[MED] if r['ID_POLIGONO'] in ids]
                        by_municipio.append({**identity,'municipio':mun,'n_parcelas':len(ids),'poco_informativo':len(ids)<5,'dMAE':statistics.fmean(diff[i] for i in ids),'MAE_media':resumen(rbase)['MAE_por_parcela'],'MAE_mediana':resumen(rmed)['MAE_por_parcela'],'sesgo_media':resumen(rbase)['sesgo_media_repeticiones'],'sesgo_mediana':resumen(rmed)['sesgo_media_repeticiones']})
                    if esc == 'A' and subset == 'sin_respaldo':
                        for cell in blocks:
                            remaining = [d for i,d in diff.items() if cells[i] != cell]
                            influence.append({'celda_retirada_solo_del_resumen':cell,'n_parcelas_retiradas':sum(cells[i]==cell for i in diff),'dMAE_restante':statistics.fmean(remaining),'reajuste_modelos':False})

    salida.mkdir(parents=True)
    def save_csv(name, rows):
        with (salida/name).open('w',newline='',encoding='utf-8') as f:
            writer=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');writer.writeheader();writer.writerows(rows)
    for name, rows in [('metricas.csv',metrics),('metricas_por_repeticion.csv',repeated),('contrastes.csv',contrasts),('por_municipio.csv',by_municipio),('diferencias_por_parcela.csv',differences),('influencia_celdas.csv',influence),('contextos_verificados.csv',per_fit)]:save_csv(name,rows)
    manifest={'schema':'agrocebada_revision_mediana_v1','universo':{'total':197,'etiquetadas':138,'reservadas_sin_usar':59},'referencias_reconstruidas':comparisons,'contextos_verificados':len(per_fit),'max_delta_OOF_reconstruccion':reconstructed_max,'max_delta_media_T08_T15':common_max,'tolerancia':TOL,'regla_T03_modificada':False,'T15_modificado':False,'modelo_final_elegido':False,'predicciones_59_generadas':False,'n_boot':5000,'semilla':20261006,'auditor_importa_productor':False,'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'diseno_sha256':hashlib.sha256(design_path.read_bytes()).hexdigest(),'fuentes_sha256':design['fuentes_sha256'],'entorno':{'numpy':np.__version__},'archivos_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(salida.iterdir())}}
    (salida/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    print(json.dumps(manifest,ensure_ascii=False,indent=2))


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--salida',type=Path,required=True)
    ejecutar(parser.parse_args().salida)
