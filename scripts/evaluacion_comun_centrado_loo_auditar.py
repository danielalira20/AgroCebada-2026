"""Control independiente v3 con lambda fija; no calcula MAE externo ni T15."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import platform

import numpy as np
import pandas as pd
import sklearn

from scripts import evaluacion_comun_centrado_loo as v3
from scripts.evaluacion_comun_modelo import preparar_contexto, NULLABLE


def independiente(x, y, q, cols, lamb=.1):
    x = x.sort_index()
    y = y.loc[x.index]
    a, b = x[cols].to_numpy(float).copy(), q[cols].to_numpy(float).copy()
    if 'area_ha_origen' in cols:
        j = cols.index('area_ha_origen')
        a[:, j], b[:, j] = np.log(a[:, j]), np.log(b[:, j])
    if NULLABLE in cols:
        j = cols.index(NULLABLE)
        ma, mb = np.isnan(a[:, j]), np.isnan(b[:, j])
        v3.exigir((~ma).any(), 'Sin mediana de contraste')
        med = np.median(a[~ma, j])
        a[ma, j], b[mb, j] = med, med
        a, b = np.column_stack([a, ma.astype(float)]), np.column_stack([b, mb.astype(float)])
    mu, sd = a.mean(0), a.std(0)
    sd[sd == 0] = 1
    z, zq = (a-mu)/sd, (b-mu)/sd
    residual, centers, sources, ids = [], [], [], []
    for i, (pid, row) in enumerate(x.iterrows()):
        rest = x.drop(index=pid)
        mask = rest.municipio == row.municipio
        source = 'municipio'
        if not mask.any():
            mask = rest.cultivo_origen == row.cultivo_origen
            source = 'grupo'
        if not mask.any():
            mask = pd.Series(True, index=rest.index)
            source = 'global'
        pool = tuple(rest.loc[mask].index)
        positions = x.index.get_indexer(pool)
        centers.append(z[positions].mean(0))
        residual.append(float(y.loc[pid]) - math.fsum(y.loc[list(pool)])/len(pool))
        sources.append(source)
        ids.append(pool)
    centers, residual = np.stack(centers), np.asarray(residual)
    d = z-centers
    beta = np.linalg.solve(d.T@d + len(x)*lamb*np.eye(d.shape[1]), d.T@residual)
    ref, cq, sourceq = [], [], []
    for row in q.itertuples():
        mask = x.municipio == row.municipio
        source = 'municipio'
        if not mask.any():
            mask = x.cultivo_origen == row.cultivo_origen
            source = 'grupo'
        if not mask.any():
            mask = pd.Series(True, index=x.index)
            source = 'global'
        ref.append(math.fsum(y.loc[mask])/int(mask.sum()))
        cq.append(z[mask.to_numpy()].mean(0))
        sourceq.append(source)
    pred = np.asarray(ref) + (zq-np.stack(cq))@beta
    return dict(pred=pred, source=sourceq, coef=beta, centers=centers, residual=residual,
                ids=ids, sources=sources, d=d, mu=mu, sd=sd)


def auditar(raiz):
    e = v3.cargar_entradas(raiz)
    prop = json.loads((Path(raiz)/'registro/evaluacion_comun/propuesta_t15_centrado_loo_v3.json').read_text())
    blocks = {p['candidato'].removeprefix('comun_centrado_loo_v3_'):
              next(o['columnas'] for o in p['opciones'] if o['ventana'] in ['jun_oct', 'estatica'])
              for p in prop['procedimientos']}
    maximum = dict(prediccion=0., coeficientes=0., centros=0., residuos=0., escala=0.,
                   media_correccion_municipal_predict_train=0.)
    controls, support = [], []
    for esc in ['A', 'B']:
        for rep in range(1, 6):
            for fold in range(5):
                x, y, q = preparar_contexto(e, esc, rep, fold)
                v3.exigir(not set(x.index)&set(q.index) and
                          not (set(x.index)|set(q.index))&e['reservados'], 'IDs fuera de contexto')
                for block in ['C', 'G', 'P', 'S', 'CGP']:
                    cols = blocks[block]
                    model = v3.CorreccionComunCentradaLOO(cols, .1).fit(x, y)
                    a = independiente(x, y, q, cols)
                    pred = model.predict_with_details(q)
                    v3.exigir(pred.fuente.tolist() == a['source'], 'Respaldo externo distinto')
                    for i, pid in enumerate(sorted(x.index)):
                        src, ids = model.pools_sin_fila_[pid]
                        v3.exigir(src == a['sources'][i] and ids == a['ids'][i] and pid not in ids,
                                  'Pool LOO distinto o contiene propia fila')
                    diffs = dict(prediccion=float(np.max(abs(pred.prediccion.to_numpy()-a['pred']))),
                                 coeficientes=float(np.max(abs(model.ridge_.coef_-a['coef']))),
                                 centros=float(np.max(abs(model.centros_sin_fila_.to_numpy()-a['centers']))),
                                 residuos=float(np.max(abs(model.residuos_-a['residual']))),
                                 escala=float(np.max(abs(model.escalador_.scale_-a['sd']))),
                                 media_correccion_municipal_predict_train=float(
                                     model.predict_with_details(x).correccion.groupby(x.municipio).mean().abs().max()))
                    for k, v in diffs.items():
                        maximum[k] = max(maximum[k], v)
                    v3.exigir(diffs['prediccion'] <= 1e-9 and
                              max(diffs['coeficientes'], diffs['centros'], diffs['residuos'], diffs['escala']) <= 1e-10,
                              'No reproduce matriz independiente')
                    v3.exigir(diffs['media_correccion_municipal_predict_train'] <= 1e-12,
                              'Corrimiento municipal inventado en predict')
                    before = json.dumps(model.estado(), sort_keys=True)
                    for pid, row in pred.iterrows():
                        controls.append(dict(escenario=esc, repeticion=rep, particion=fold, bloque=block,
                                             id_parcela=pid, prediccion=float(row.prediccion),
                                             correccion=float(row.correccion), fuente=row.fuente))
                    for source in ['municipio', 'grupo', 'global']:
                        support.append(dict(escenario=esc, repeticion=rep, particion=fold, bloque=block,
                                            fuente_centro_LOO=source,
                                            n_filas=sum(s == source for s, _ in model.pools_sin_fila_.values())))
                    v3.exigir(before == json.dumps(model.estado(), sort_keys=True), 'Predict alteró estado')
    result = dict(resultado='verificado', version=v3.VERSION, sha_procedimiento=v3.DISENO_SHA,
                  alcance='control_matematico_fijo_sin_evaluacion_externa', lambda_fija=.1,
                  contextos=50, bloques=5, ajustes_Ridge_tecnicos=250, predicciones_control=len(controls),
                  maximos=maximum, MAE_externo_calculado=False, seleccion_bloque=False,
                  T15_completo_ejecutado=False, ajustes_finales_59=0, revision_humana_pendiente=True,
                  entorno=dict(sistema=platform.system(), arquitectura=platform.machine(),
                               python=platform.python_version(), numpy=np.__version__, pandas=pd.__version__,
                               sklearn=sklearn.__version__), fuentes_sha256=e['config']['fuentes_sha256'])
    return result, controls, support


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--raiz', type=Path, default=v3.RAIZ)
    p.add_argument('--salida', type=Path, required=True)
    args = p.parse_args()
    v3.exigir(not args.salida.exists(), 'El control requiere destino nuevo')
    result, rows, support = auditar(args.raiz)
    args.salida.mkdir(parents=True)
    pd.DataFrame(rows).to_csv(args.salida/'controles_fijos.csv', index=False, float_format='%.17g')
    pd.DataFrame(support).to_csv(args.salida/'fuentes_centros_LOO.csv', index=False)
    result['control_sha256'] = hashlib.sha256((args.salida/'controles_fijos.csv').read_bytes()).hexdigest()
    (args.salida/'verificacion.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'fuentes_sha256'}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
