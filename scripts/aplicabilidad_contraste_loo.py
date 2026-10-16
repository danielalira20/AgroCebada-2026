"""Contextualiza las alertas de C con LOO de entradas; no usa y ni estima modelos."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import tempfile

import numpy as np

from scripts import diagnostico_aplicabilidad59 as anterior

ROOT = Path(__file__).resolve().parents[1]
DESIGN = 'registro/diagnostico/aplicabilidad59/contraste_loo/diseno.json'
DESIGN_SHA = '10565dc17b69e54086cad855f964dbe35ae78f374a95c3484c00d9b694dec801'
require = anterior.exigir


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(root):
    root = Path(root)
    require(sha(root / DESIGN) == DESIGN_SHA, 'Diseño LOO distinto: versionar')
    design = json.loads((root / DESIGN).read_text())
    for p, digest in design['fuentes_sha256'].items():
        require(sha(root / p) == digest, 'Fuente LOO distinta: ' + p)
    original = json.loads((root / 'registro/diagnostico/aplicabilidad59/diseno.json').read_text())
    for p, digest in original['fuentes_sha256'].items():
        require(sha(root / p) == digest, 'Fuente C distinta: ' + p)
    records = anterior.indexed(root / 'registro/t07/tabla_comun.csv')
    catalog = anterior.indexed(root / 'registro/t07/catalogo_base.csv')
    require(set(records) == set(catalog) and len(records) == 197, 'Universo incompleto')
    known = sorted(k[0] for k, r in catalog.items() if r['conjunto_origen'] == 'ENTRENAMIENTO')
    reserved = sorted(k[0] for k, r in catalog.items() if r['conjunto_origen'] == 'PREDICCION')
    require(len(known) == 138 and len(reserved) == 59 and not set(known) & set(reserved), 'Cohortes incompatibles')
    reps = original['representaciones']
    require(len(reps) == len({r['id'] for r in reps}) == 15, 'Representaciones distintas')
    cols = {'municipio'} | {c for r in reps for c in r['columnas']}
    # Sólo este diccionario reducido llega al cálculo; no contiene objetivo ni cohortes.
    table = {k[0]: {c: row[c] for c in cols} for k, row in records.items()}
    return design, original, table, known, reserved


def diagnose(table, pid, train, representation, cohort):
    require(pid not in train and len(train) == len(set(train)), 'Propia fila o referencia duplicada')
    state = anterior.fit_space(table, train, representation['columnas'])
    result = anterior.inspect_space(table, pid, state)
    return dict(cohorte=cohort, id_parcela=pid, municipio=table[pid]['municipio'],
                representacion=representation['id'], **result)


def union_flags(flags):
    require(bool(flags) and all(v is None or type(v) is bool for v in flags), 'Banderas no triestado')
    if any(v is True for v in flags):
        return True
    return None if any(v is None for v in flags) else False


def profiles(detail, representations):
    keys = [(r['cohorte'], r['id_parcela'], r['representacion']) for r in detail]
    require(len(keys) == len(set(keys)), 'Perfiles duplicados')
    grouped = {}
    for r in detail:
        grouped.setdefault((r['cohorte'], r['id_parcela']), []).append(r)
    result = []
    expected = {r['id'] for r in representations}
    for (cohort, pid), rs in sorted(grouped.items()):
        require(len(rs) == len(expected) and {r['representacion'] for r in rs} == expected,
                'Representaciones incompletas')
        require(len({(r['municipio'], r['n_entrenamiento'], r['n_municipio']) for r in rs}) == 1,
                'Metadatos de referencia distintos')
        flags = [r['supera_q95_local'] for r in rs]
        result.append(dict(cohorte=cohort, id_parcela=pid, municipio=rs[0]['municipio'],
            n_parcelas_referencia=rs[0]['n_entrenamiento'],
            n_parcelas_referencia_municipio=rs[0]['n_municipio'],
            n_representaciones=len(rs),
            n_representaciones_q95_evaluables=sum(v is not None for v in flags),
            representaciones_fuera_rango_global=';'.join(r['representacion'] for r in rs if r['fuera_rango_global']),
            representaciones_supera_q95_local=';'.join(r['representacion'] for r in rs if r['supera_q95_local'] is True),
            representaciones_q95_no_definido=';'.join(r['representacion'] for r in rs if r['supera_q95_local'] is None),
            aviso_rango_global=any(bool(r['fuera_rango_global']) for r in rs),
            aviso_q95_local=union_flags(flags)))
    return result


def statistics_flags(values):
    require(all(v is None or type(v) is bool for v in values), 'Estado de aviso inválido')
    total = len(values)
    evaluable = sum(v is not None for v in values)
    flagged = sum(v is True for v in values)
    return dict(n_parcelas_total=total, n_parcelas_evaluables=evaluable,
                n_parcelas_con_aviso=flagged, n_parcelas_sin_diagnostico=total-evaluable,
                proporcion_aviso_observado_sobre_total=flagged/total if total else None,
                proporcion_aviso_sobre_evaluables=flagged/evaluable if evaluable else None)


def comparison(records, key):
    out = {}
    for cohort, prefix in [('etiquetadas_LOO', 'etiquetadas'), ('reservadas', 'reservadas')]:
        stats = statistics_flags([r[key] for r in records if r['cohorte'] == cohort])
        for name, value in stats.items():
            out[prefix + '_' + name] = value
    return out


def summaries(detail, united, representations):
    output = []
    for representation in [r['id'] for r in representations] + ['alguna_de_15']:
        selected = united if representation == 'alguna_de_15' else [
            dict(r, aviso_rango_global=bool(r['fuera_rango_global']), aviso_q95_local=r['supera_q95_local'])
            for r in detail if r['representacion'] == representation]
        for rule, key in [('fuera_rango_global', 'aviso_rango_global'), ('supera_q95_local', 'aviso_q95_local')]:
            output.append(dict(representacion=representation, regla=rule, **comparison(selected, key)))
    municipalities = []
    for mun in sorted({r['municipio'] for r in united}):
        selected = [r for r in united if r['municipio'] == mun]
        for rule, key in [('fuera_rango_global', 'aviso_rango_global'), ('supera_q95_local', 'aviso_q95_local')]:
            municipalities.append(dict(municipio=mun, representacion='alguna_de_15', regla=rule,
                                       **comparison(selected, key)))
    return output, municipalities


def reconcile59(detail, old):
    actual = {(r['id_parcela'], r['representacion']): r for r in detail if r['cohorte'] == 'reservadas'}
    previous = {(r['id_parcela'], r['representacion']): r for r in old}
    require(len(actual) == len(previous) == len(old) == 885 and actual.keys() == previous.keys(), 'IDs C distintos')
    checks, delta = 0, 0.
    for key, row in previous.items():
        for col, value in row.items():
            new = actual[key][col]
            if new is None:
                require(value == '', 'Vacío C distinto: ' + col)
            elif isinstance(new, (bool, np.bool_)):
                require(value == ('si' if new else 'no'), 'Bandera C distinta: ' + col)
            elif isinstance(new, (int, np.integer)):
                require(float(value) == new, 'Conteo C distinto: ' + col)
            elif isinstance(new, (float, np.floating)):
                error = abs(float(value)-float(new));delta = max(delta, error)
                require(math.isfinite(error) and error <= 1e-9, 'Número C distinto: ' + col)
            else:
                require(value == new, 'Texto C distinto: ' + col)
            checks += 1
    return dict(perfiles=885, comparaciones=checks, max_delta_numerico=delta, tolerancia=1e-9,
                estados_y_conteos_exactos=True)


def dictionary(tables):
    descriptions = {
        'cohorte': ('Etiquetada evaluada con las otras 137 o reservada evaluada con las 138; no predictor.', 'categoria', 'no_admitido'),
        'id_parcela': ('ID original único por cohorte en el perfil de unión.', 'ID', 'no_admitido'),
        'municipio': ('Municipio original; desglose descriptivo, no rendimiento.', 'texto', 'no_admitido'),
        'representacion': ('Bloque/ventana de C-v1; alguna_de_15 es la unión de sus avisos, sin duplicar parcelas.', 'categoria', 'no_admitido'),
        'regla': ('Fuera de algún rango global crudo o distancia al vecino local mayor que q95 higher+1e-12.', 'categoria', 'no_admitido'),
        'aviso_rango_global': ('Alguna entrada fuera del rango de sus referencias; no error de predicción ni exclusión.', 'booleano', 'no_admitido'),
        'aviso_q95_local': ('Unión triestado: sí si alguna supera q95; no sólo si todas definidas y no; ausente en otro caso.', 'booleano', 'referencia_local_insuficiente'),
        'n_parcelas_referencia': ('IDs de referencia: 137 para cada etiquetada LOO y 138 para reservadas.', 'parcelas', 'no_admitido'),
        'n_parcelas_referencia_municipio': ('Parcelas de referencia del municipio; la propia fila nunca se incluye.', 'parcelas', 'no_admitido'),
        'n_representaciones': ('Representaciones C inspeccionadas por ID; no observaciones independientes.', 'representaciones', 'no_admitido'),
        'n_representaciones_q95_evaluables': ('Representaciones con al menos dos referencias del municipio.', 'representaciones', 'no_admitido'),
        'representaciones_fuera_rango_global': ('Representaciones con al menos una entrada fuera de rango.', 'lista', 'ningun_aviso'),
        'representaciones_supera_q95_local': ('Representaciones con aviso de distancia local observado.', 'lista', 'ningun_aviso_observado_no_implica_todas_evaluables'),
        'representaciones_q95_no_definido': ('Representaciones sin dos referencias locales; no se cuentan como no aviso.', 'lista', 'todas_evaluables'),
    }
    for cohort in ['etiquetadas', 'reservadas']:
        for suffix, text in [
            ('n_parcelas_total', 'Total de IDs únicos del grupo, incluidos los que no tienen diagnóstico.'),
            ('n_parcelas_evaluables', 'IDs con regla definida.'),
            ('n_parcelas_con_aviso', 'IDs con aviso observado; no número de fallos predictivos.'),
            ('n_parcelas_sin_diagnostico', 'IDs con regla ausente; no se reclasifican como sin aviso.'),
            ('proporcion_aviso_observado_sobre_total', 'Avisos observados / total; no interpreta los indefinidos como negativos.'),
            ('proporcion_aviso_sobre_evaluables', 'Avisos / IDs con diagnóstico definido.')]:
            unit = 'fraccion_0_1' if suffix.startswith('proporcion') else 'parcelas'
            empty = 'denominador_cero' if suffix.startswith('proporcion') else 'no_admitido'
            descriptions[cohort+'_'+suffix] = (cohort+': '+text, unit, empty)
    result = []
    for name, rows in tables.items():
        for col in rows[0]:
            meaning, unit, empty = descriptions[col]
            result.append(dict(archivo=name, columna=col, significado=meaning, unidad=unit, significado_vacio=empty))
    return result


def run(root, output, detail=None):
    root, output = Path(root), Path(output)
    require(not output.exists(), 'Destino existente: conservar evidencia')
    if detail is not None:
        detail = Path(detail);require(not detail.exists(), 'Detalle existente: conservar evidencia')
        require(output.resolve() != detail.resolve() and output.resolve() not in detail.resolve().parents
                and detail.resolve() not in output.resolve().parents, 'Destinos deben ser separados')
    design, original, table, known, reserved = load(root)
    records = []
    for i, pid in enumerate(known):
        train = [p for p in known if p != pid]
        for representation in original['representaciones']:
            records.append(diagnose(table, pid, train, representation, 'etiquetadas_LOO'))
    for representation in original['representaciones']:
        state = anterior.fit_space(table, known, representation['columnas'])
        for pid in reserved:
            records.append(dict(cohorte='reservadas', id_parcela=pid, municipio=table[pid]['municipio'],
                                representacion=representation['id'], **anterior.inspect_space(table, pid, state)))
    require(len(records) == 2955, 'Perfiles incompletos')
    reconciled = reconcile59(records, anterior.rows(root / 'registro/diagnostico/aplicabilidad59/entradas_59.csv'))
    united = profiles(records, original['representaciones'])
    summary, municipalities = summaries(records, united, original['representaciones'])
    tables = {'comparacion_138_59.csv': summary, 'comparacion_por_municipio.csv': municipalities,
              'perfil_union_197.csv': united}
    tables['diccionario.csv'] = dictionary(tables)
    output.parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix='.contraste-LOO-', dir=output.parent))
    try:
        for name, rows in tables.items():
            anterior.csv_out(tmp / name, rows)
        m = dict(version='aplicabilidad-contraste-LOO-v1', diseno_sha256=DESIGN_SHA,
                 fuentes_sha256=design['fuentes_sha256'], codigo_sha256=sha(__file__),
                 archivos_sha256={p.name: sha(p) for p in sorted(tmp.iterdir())},
                 parcelas=197, etiquetadas=138, reservadas=59, representaciones=15, perfiles=2955,
                 espacios_X_ajustados=2085, conciliacion_59=reconciled, modelos_predictivos=0,
                 nuevas_predicciones59=0, reglas_modificadas=False, revision_humana='pendiente')
        if detail is not None:
            detail.mkdir(parents=True, exist_ok=False)
            anterior.csv_out(detail / 'perfiles_2955.csv', records)
            m['detalle_sha256'] = sha(detail / 'perfiles_2955.csv')
        anterior.dump(tmp / 'manifest.json', m)
        require(not output.exists(), 'Destino apareció durante escritura')
        os.rename(tmp, output)
    except BaseException:
        shutil.rmtree(tmp, ignore_errors=True)
        raise
    return m


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--raiz', type=Path, default=ROOT)
    parser.add_argument('--salida', type=Path, required=True)
    parser.add_argument('--detalle', type=Path)
    args = parser.parse_args()
    print(json.dumps(run(args.raiz, args.salida, args.detalle), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
