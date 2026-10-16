"""QA sin rendimientos: quitar cada vecina inmediata del ancla y recalcular."""
import argparse
from datetime import timedelta
import json
from pathlib import Path
import statistics

from scripts import t15_ndwi_factibilidad as d1
from scripts.t15_e1_contrato import require
from scripts.t15_ejecutor_reportes import csv_guardar
from scripts.t15_ejecutar import guardar_json, validar_salida


def admisible(p):
    return bool(p['calculable'] and p['intervalo_truncado'] is False)


def perturbar(observaciones, inicio):
    base = d1.profile(observaciones, inicio)
    valid = [o for o in observaciones if inicio <= o.fecha <= d1.CORTE and o.ndvi is not None
             and o.nube is not None and 0 <= o.nube <= 5]
    valid.sort(key=lambda o:o.fecha)
    if base['fecha_maximo'] is None: return base, []
    anchor = next(i for i, o in enumerate(valid) if o.fecha == base['fecha_maximo'])
    tests = []
    for i in range(max(0, anchor-1), min(len(valid), anchor+2)):
        removed = valid[i]
        alt = d1.profile([o for o in observaciones if o.fecha != removed.fecha], inicio)
        shift = (alt['fecha_maximo']-base['fecha_maximo']).days if alt['fecha_maximo'] else None
        diff = alt['contraste_ndwi']-base['contraste_ndwi'] if admisible(base) and admisible(alt) else None
        tests.append(dict(fecha_retirada=removed.fecha.isoformat(), posicion_relativa=i-anchor,
                          maximo_original=base['fecha_maximo'].isoformat(),
                          maximo_alternativo=alt['fecha_maximo'].isoformat() if alt['fecha_maximo'] else '',
                          desplazamiento_dias=shift, contraste_original=base['contraste_ndwi'],
                          contraste_alternativo=alt['contraste_ndwi'], admisible_original=admisible(base),
                          admisible_alternativo=admisible(alt), diferencia_E1_si_ambos_admisibles=diff))
    return base, tests


def run(root, output):
    root, output = Path(root), Path(output)
    output = validar_salida(output, root)
    design = json.loads((root/'registro/t15_d1/diseno.json').read_text())
    raw = root/next(k for k in design['fuentes_sha256'] if k.endswith(d1.RAW))
    require(d1.sha(raw) == design['fuentes_sha256'][str(raw.relative_to(root))], 'Raw modificado')
    cats = d1.catalogue(d1.read_csv(root/'registro/t07/catalogo_base.csv'))
    observations, _ = d1.observations(raw, cats)
    original = {(r['id_parcela'],r['ventana']):r for r in d1.read_csv(root/'registro/t15_d1/perfil_ndwi_postpico.csv')}
    rows = []
    for pid in sorted(cats):
        for window, start in d1.VENTANAS.items():
            base, perturbations = perturbar(observations[pid], start)
            require(str(base['fecha_maximo']) == original[pid,window]['fecha_maximo'], 'Ancla difiere de D1')
            require(str(base['calculable']) == original[pid,window]['calculable'], 'Soporte difiere de D1')
            for row in perturbations:
                rows.append(dict(**cats[pid], ventana=window, **row))
    summary = []
    for window in d1.VENTANAS:
        sub = [r for r in rows if r['ventana'] == window]
        for group in ['todas','ENTRENAMIENTO','PREDICCION']:
            part = [r for r in sub if group == 'todas' or r['conjunto'] == group]
            ids = sorted({r['id_parcela'] for r in part})
            deltas = [abs(r['diferencia_E1_si_ambos_admisibles']) for r in part
                      if r['diferencia_E1_si_ambos_admisibles'] is not None]
            summary.append(dict(ventana=window, conjunto=group, n_parcelas=len(ids), n_perturbaciones=len(part),
                parcelas_con_cambio_fecha=sum(any(r['desplazamiento_dias'] != 0 for r in part if r['id_parcela']==pid) for pid in ids),
                parcelas_con_cambio_admisibilidad=sum(any(r['admisible_original'] != r['admisible_alternativo'] for r in part if r['id_parcela']==pid) for pid in ids),
                n_pares_admisibles=len(deltas), mediana_cambio_absoluto_E1=statistics.median(deltas) if deltas else None,
                maximo_cambio_absoluto_E1=max(deltas) if deltas else None,
                maximo_desplazamiento_dias=max(abs(r['desplazamiento_dias']) for r in part if r['desplazamiento_dias'] is not None)))
    output.mkdir(parents=True)
    csv_guardar(output/'perturbaciones.csv', rows)
    csv_guardar(output/'resumen.csv', summary)
    by_type=[]
    for window in d1.VENTANAS:
        for kind in ['ancla','vecinas_inmediatas']:
            for group in ['todas','ENTRENAMIENTO','PREDICCION']:
                sub=[r for r in rows if r['ventana']==window and
                     ((r['posicion_relativa']==0)==(kind=='ancla')) and
                     (group=='todas' or r['conjunto']==group)]
                by_type.append(dict(ventana=window,retiro=kind,conjunto=group,n_pruebas=len(sub),
                    ids_con_cambio_ancla=len({r['id_parcela'] for r in sub if r['desplazamiento_dias']!=0}),
                    ids_pierden_admisibilidad=len({r['id_parcela'] for r in sub if r['admisible_original'] and not r['admisible_alternativo']}),
                    ids_ganan_admisibilidad=len({r['id_parcela'] for r in sub if not r['admisible_original'] and r['admisible_alternativo']})))
    csv_guardar(output/'resumen_tipo_retiro.csv',by_type)
    manifest = dict(schema='E1_QA_ancla_v1', codigo_sha256=d1.sha(Path(__file__)),
        raw_sha256=d1.sha(raw), n_perturbaciones=len(rows), n_perfiles=394,
        usa_rendimientos=False, modifica_admisibilidad=False,
        tratamiento='sensibilidad_descriptiva_sin_filtrar_por_error',
        archivos_sha256={p.name:d1.sha(p) for p in output.iterdir()})
    guardar_json(output/'manifest.json', manifest)
    return manifest


if __name__ == '__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--raiz', type=Path, default=d1.ROOT)
    ap.add_argument('--salida', type=Path, required=True)
    args=ap.parse_args()
    print(json.dumps(run(args.raiz,args.salida),ensure_ascii=False,indent=2))
