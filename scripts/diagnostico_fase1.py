"""Descriptivos T08 OOF de fase 1. No importa ni ajusta estimadores."""
import argparse
from collections import Counter, defaultdict
import csv
import json
import math
from pathlib import Path
import statistics
import tempfile

from scripts.diagnostico_fuentes import exigir, hash_archivo, json_estricto, ruta_segura
from scripts import diagnostico_fase0 as f0

RAIZ = Path(__file__).resolve().parents[1]
DISENO = 'registro/diagnostico/fase1_diseno.json'
DISENO_SHA = '8fbec800f8d474e551d0a6e20bfe565beb52e7760671d920b7631a53c2cbbb03'
F0_MANIFEST_SHA = 'e5eb9bd692d00f64b0b59fa611723bff7dcaabf00297bc5c3aed27341984f691'
POBLACIONES = ('todas', 'sin_respaldo', 'con_respaldo', 'grupo', 'global')
F0_CODIGO = {'scripts/diagnostico_fase0.py': 'f66fd61dcc7a413675872e03fbdc7a6ec6c48a4cc32ef9fee10817a2718d117b',
             'scripts/diagnostico_fuentes.py': '7281b810a51c767bc63d3469e43b638cc1cb54a521a04fa45e6809e917ee673f'}


def media(xs):
    return math.fsum(xs) / len(xs) if xs else ''


def cuantil(xs, p):
    exigir(0 <= p <= 1, 'Cuantil fuera de rango')
    if not xs:
        return ''
    s = sorted(xs); h = (len(s) - 1) * p; i = math.floor(h)
    return s[i] + (h - i) * (s[min(i + 1, len(s) - 1)] - s[i])


def elegible(row, poblacion):
    exigir(poblacion in POBLACIONES, 'Población desconocida')
    source = row['fuente_referencia']
    return (poblacion == 'todas' or poblacion == 'sin_respaldo' and source == 'municipio'
            or poblacion == 'con_respaldo' and source != 'municipio' or poblacion == source)


def errores(row):
    e = row['prediccion'] - row['real']
    exigir(math.isfinite(e) and math.isfinite(e * e), 'Error no finito')
    return dict(error_firmado=e, error_absoluto=abs(e), error_cuadrado=e * e)


def orden(rows, score):
    return sorted(rows, key=lambda r: (-r[score], r['id_parcela']))


def resumen_parcela(rows):
    es = [r['error_firmado'] for r in rows]
    abses = [r['error_absoluto'] for r in rows]
    sq = [r['error_cuadrado'] for r in rows]
    n = len(rows)
    return dict(n_elegibles=n, prediccion_media=media([r['prediccion'] for r in rows]),
                sesgo=media(es), mae=media(abses), mse=media(sq),
                rmse=math.sqrt(media(sq)) if n else '', mediana_abs=cuantil(abses, .5), p90_abs=cuantil(abses, .9),
                error_min=min(es) if n else '', error_max=max(es) if n else '',
                rango_error=max(es) - min(es) if n else '',
                sd_error=statistics.pstdev(es) if n else '',
                abs_sesgo=abs(media(es)) if n else '',
                sobre=sum(e > 0 for e in es), sub=sum(e < 0 for e in es), ceros=sum(e == 0 for e in es),
                fraccion_sobre=sum(e > 0 for e in es) / n if n else '',
                fraccion_sub=sum(e < 0 for e in es) / n if n else '',
                fraccion_cero=sum(e == 0 for e in es) / n if n else '')


def resumir_conjunto(rows):
    by = defaultdict(list)
    for r in rows:
        by[r['id_parcela']].append(r)
    ps = [resumen_parcela(rs) for _, rs in sorted(by.items())]
    maes = [r['mae'] for r in ps]; mses = [r['mse'] for r in ps]
    return dict(n_parcelas=len(ps), n_registros=len(rows), mae_parcelas=media(maes),
                mse_parcelas=media(mses), rmse_parcelas=math.sqrt(media(mses)) if ps else '',
                mediana_mae_parcela=cuantil(maes, .5), p90_mae_parcela=cuantil(maes, .9),
                sesgo_parcelas=media([r['sesgo'] for r in ps]),
                mae_registros=media([r['error_absoluto'] for r in rows]),
                sesgo_registros=media([r['error_firmado'] for r in rows]),
                fraccion_sobre_parcelas=media([r['fraccion_sobre'] for r in ps]),
                fraccion_sub_parcelas=media([r['fraccion_sub'] for r in ps]),
                fraccion_cero_parcelas=media([r['fraccion_cero'] for r in ps]))


def cargar(fase0, fuentes):
    # El manifiesto ya fijado ancla los bytes, no un archivo sin identidad.
    for rel, sha in F0_CODIGO.items():
        exigir(hash_archivo(RAIZ / rel) == sha, 'Productor fase0 cambió')
    exigir(hash_archivo(RAIZ / DISENO) == DISENO_SHA, 'Diseño fase1 cambió')
    mp = ruta_segura(fase0, 'manifest.json')
    exigir(hash_archivo(mp) == F0_MANIFEST_SHA, 'Manifiesto fase0 distinto')
    m = json_estricto(mp)
    for rel, sha in m['archivos_sha256'].items():
        exigir(hash_archivo(ruta_segura(fase0, rel)) == sha, 'Salida fase0 distinta: ' + rel)
    _, fm = f0.configuracion(RAIZ)
    f0.validar_fuentes(fuentes, fm)
    table, known, reserved, _, parts = f0.cargar_base(fuentes)
    cases = f0.csv_completo(ruta_segura(fase0, 'casos_preseleccionados.csv'))
    controls = f0.csv_completo(ruta_segura(fase0, 'controles_preseleccionados.csv'))
    ids = [r['id_parcela'] for r in cases]
    exigir(len(ids) == len(set(ids)) == 10 and set(ids) <= known, 'Casos fijos inválidos')
    exigir([r['caso'] for r in controls] == ids and len({r['control'] for r in controls}) == 10,
           'Controles fijos inválidos')
    expected = {}
    for r in f0.csv_completo(ruta_segura(fase0, 'mascaras_contextos.csv')):
        if r['escenario'] in ('A', 'B'):
            expected[(r['escenario'], int(r['repeticion']), int(r['particion']), r['id_parcela'])] = r
    raw = f0.csv_completo(ruta_segura(fase0, 'normalizadas_oof.csv'))
    rows = []; seen = set()
    for r in raw:
        if r['fuente'] != 'T08':
            continue
        exigir((r['archivo'], r['candidato'], r['variante'], r['version']) ==
               (f0.OOF_BASE, 'media_mun__resp_grupo', 'seleccionada', 'T08-v1'), 'Referencia distinta')
        pid = r['id_parcela']; esc = r['escenario']; rep = f0.entero(r['repeticion'], 'rep')
        fold = f0.entero(r['particion'], 'fold'); key = (esc, rep, fold, pid)
        exigir(key in expected and key not in seen and pid not in reserved, 'Contexto ajeno/duplicado')
        seen.add(key); can = expected[key]
        exigir(r['fuente_referencia'] == can['fuente_referencia'] and r['sin_respaldo'] == can['sin_respaldo'],
               'Máscara fuente distinta')
        exigir(r['unidad'] == 't/ha' and r['metodo_comun_acreditado'] == 'False', 'Unidad/procedimiento cambiado')
        y = f0.numero(r['real'], 'real'); pred = f0.numero(r['prediccion'], 'pred')
        exigir(y == float(table[pid]['rendimiento_t_ha']) and abs(pred - float(r['referencia'])) <= f0.ATOL,
               'Etiqueta/referencia distinta')
        v = {**r, 'repeticion': rep, 'particion': fold, 'real': y, 'prediccion': pred,
             'municipio': table[pid]['municipio'], 'caso_fijo': pid in ids,
             'control_de': next((c['caso'] for c in controls if c['control'] == pid), ''),
             'tramo_real': str(math.floor(y)) + '_a_menos_de_' + str(math.floor(y) + 1)}
        v.update(errores(v)); rows.append(v)
    exigir(seen == set(expected) and len(rows) == 1380, 'Referencia incompleta')
    return sorted(rows, key=lambda r: (r['escenario'], r['repeticion'], r['id_parcela'])), table, known, cases, controls


def analizar(rows, table, known, cases):
    per_parcel = []; metricas = []; rep_metrics = []; grupos = []
    fixed = {r['id_parcela']: int(r['orden']) for r in cases}
    for esc in ('A', 'B'):
        er = [r for r in rows if r['escenario'] == esc]
        for pop in POBLACIONES:
            selected = [r for r in er if elegible(r, pop)]
            by = defaultdict(list)
            for r in selected:
                by[r['id_parcela']].append(r)
            appearances = Counter(); rep_maes = []
            for rep in range(1, 6):
                rr = [r for r in selected if r['repeticion'] == rep]
                top = orden(rr, 'error_absoluto')[:10]
                appearances.update(r['id_parcela'] for r in top)
                rm = resumir_conjunto(rr)
                rep_metrics.append(dict(escenario=esc, poblacion=pop, repeticion=rep, **rm))
                if rr:
                    rep_maes.append(rm['mae_parcelas'])
            local = []
            for pid in sorted(known):
                rs = by[pid]; stat = resumen_parcela(rs)
                local.append(dict(escenario=esc, poblacion=pop, id_parcela=pid, municipio=table[pid]['municipio'],
                                  real=float(table[pid]['rendimiento_t_ha']), orden_caso_fijo=fixed.get(pid, ''),
                                  control_de=next((r['control_de'] for r in er if r['id_parcela'] == pid), ''),
                                  rep_elegibles='|'.join(str(r['repeticion']) for r in rs), n_repeticiones_previstas=5,
                                  apariciones_top10=appearances[pid],
                                  fraccion_top10=appearances[pid] / len(rs) if rs else '', **stat))
            total_abs = math.fsum(r['mae'] for r in local if r['n_elegibles'])
            total_sq = math.fsum(r['mse'] for r in local if r['n_elegibles'])
            ranks = {r['id_parcela']: i + 1 for i, r in enumerate(orden([r for r in local if r['n_elegibles']], 'mae'))}
            for r in local:
                r.update(rango_mae=ranks.get(r['id_parcela'], ''),
                         contribucion_abs=r['mae'] / total_abs if r['n_elegibles'] and total_abs else '',
                         contribucion_cuadratica=r['mse'] / total_sq if r['n_elegibles'] and total_sq else '')
            per_parcel.extend(local)
            metricas.append(dict(escenario=esc, poblacion=pop, **resumir_conjunto(selected),
                                  mae_media_repeticiones=media(rep_maes),
                                  n_repeticiones_no_vacias=len(rep_maes),
                                  suma_mae_parcelas=total_abs, suma_mse_parcelas=total_sq,
                                  casos_fijos_presentes=sum(r['n_elegibles'] > 0 and r['id_parcela'] in fixed for r in local),
                                  contribucion_abs_casos_fijos=math.fsum(r['contribucion_abs'] for r in local if r['id_parcela'] in fixed and r['contribucion_abs'] != ''),
                                  contribucion_cuadratica_casos_fijos=math.fsum(r['contribucion_cuadratica'] for r in local if r['id_parcela'] in fixed and r['contribucion_cuadratica'] != '')))
            for campo in ('municipio', 'tramo_real'):
                for value in sorted({r[campo] for r in er}):
                    group = [r for r in selected if r[campo] == value]
                    grupos.append(dict(escenario=esc, poblacion=pop, agrupacion=campo, grupo=value,
                                       **resumir_conjunto(group)))
    # A debe recuperar exactamente la selección fijada, no cambiarla tras ver B.
    aa = orden([r for r in per_parcel if r['escenario'] == 'A' and r['poblacion'] == 'sin_respaldo' and r['n_elegibles']], 'mae')[:10]
    exigir([r['id_parcela'] for r in aa] == [r['id_parcela'] for r in cases], 'Ranking A distinto de fase0')
    for r, c in zip(aa, cases):
        exigir(abs(r['mae'] - float(c['criterio_media_error_absoluto'])) <= 1e-12, 'Score A distinto de fase0')
    ranking = sorted([r for r in per_parcel if r['id_parcela'] in fixed and r['poblacion'] == 'sin_respaldo'],
                     key=lambda r: (r['orden_caso_fijo'], r['escenario']))
    respaldos = [r for r in per_parcel if r['poblacion'] in ('con_respaldo', 'grupo', 'global')]
    pairs = []; indexed = {(r['escenario'], r['repeticion'], r['id_parcela']): r for r in rows}
    for pop in ('todas', 'sin_respaldo'):
        for pid in sorted(known):
            a = []; b = []
            for rep in range(1, 6):
                ar = indexed[('A', rep, pid)]; br = indexed[('B', rep, pid)]
                if elegible(ar, pop) and elegible(br, pop):
                    a.append(ar); b.append(br)
            pairs.append(dict(poblacion=pop, id_parcela=pid, municipio=table[pid]['municipio'],
                              n_pares=len(a), rep_pares='|'.join(str(r['repeticion']) for r in a),
                              mae_A_pares=media([r['error_absoluto'] for r in a]),
                              mae_B_pares=media([r['error_absoluto'] for r in b]),
                              delta_abs_B_menos_A=media([br['error_absoluto'] - ar['error_absoluto'] for ar, br in zip(a, b)]),
                              delta_firmado_B_menos_A=media([br['error_firmado'] - ar['error_firmado'] for ar, br in zip(a, b)]),
                              signos_iguales=sum((ar['error_firmado'] > 0) - (ar['error_firmado'] < 0) ==
                                                (br['error_firmado'] > 0) - (br['error_firmado'] < 0) for ar, br in zip(a, b))))
    return {'errores_por_repeticion.csv': rows, 'errores_por_parcela.csv': per_parcel,
            'resumen_metricas.csv': metricas, 'metricas_por_repeticion.csv': rep_metrics,
            'direccion_por_grupo.csv': grupos, 'respaldos_separados.csv': respaldos,
            'ranking_principal_y_sensibilidad_B.csv': ranking, 'contraste_AB_emparejado.csv': pairs}


def csv_escribir(path, rows):
    exigir(rows, 'Tabla sin esquema')
    with Path(path).open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, list(rows[0]), lineterminator='\n'); writer.writeheader(); writer.writerows(rows)


def ejecutar(fase0, fuentes, salida, figuras=True):
    salida = Path(salida)
    exigir(not salida.exists(), 'Salida ya existe: usar destino nuevo')
    salida.parent.mkdir(parents=True, exist_ok=True)
    rows, table, known, cases, controls = cargar(fase0, fuentes)
    tables = analizar(rows, table, known, cases)
    with tempfile.TemporaryDirectory(prefix='.diag_f1_', dir=salida.parent) as td:
        tmp = Path(td)
        for name, vals in tables.items():
            csv_escribir(tmp / name, vals)
        if figuras:
            from scripts.diagnostico_fase1_figuras import crear
            crear(tables, cases, tmp)
        manifest = dict(schema='agrocebada_diagnostico_fase1_entrega_v1', estado='tecnico_para_revision',
                        diseno_sha256=DISENO_SHA, fase0_manifest_sha256=F0_MANIFEST_SHA,
                        fuente='T08', candidato='media_mun__resp_grupo', version='T08-v1',
                        registros_oof=1380, parcelas=138, reservadas_evaluadas=0,
                        reentrenamientos=0, nuevos_hiperparametros=0, figuras_generadas=figuras,
                        revision_humana='pendiente', top10_ids=[r['id_parcela'] for r in cases],
                        controles_ids=[r['control'] for r in controls],
                        codigo_sha256={rel: hash_archivo(RAIZ / rel) for rel in ('scripts/diagnostico_fase1.py', 'scripts/diagnostico_fase1_figuras.py')},
                        n_filas_tablas={name: len(vals) for name, vals in tables.items()},
                        archivos_sha256={p.name: hash_archivo(p) for p in sorted(tmp.iterdir())})
        (tmp / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        tmp.rename(salida)
    return manifest


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--fase0', type=Path, required=True); p.add_argument('--fuentes', type=Path, required=True)
    p.add_argument('--salida', type=Path, required=True); p.add_argument('--sin-figuras', action='store_true')
    a = p.parse_args()
    m = ejecutar(a.fase0, a.fuentes, a.salida, not a.sin_figuras)
    print(json.dumps({k: m[k] for k in ('estado', 'registros_oof', 'parcelas', 'reentrenamientos')}, ensure_ascii=False))


if __name__ == '__main__':
    main()
