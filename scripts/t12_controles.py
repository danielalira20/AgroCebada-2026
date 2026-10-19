"""T12 paso 5: controles C2 a C6 del registro (C1 ya está en comparacion_emparejada_t12.csv).

C2 revuelto · C3 curva de aprendizaje · C4 desgloses y sensibilidad sin alerta · C5 qué aprendió ·
C6 parcelas que más mejoran y empeoran. Se corre sobre la evaluación principal ya guardada en
`registro/t12/` y no cambia ningún criterio: sólo mide.

Cada control escribe sus archivos nuevos cuando termina y los anota en `manifest_controles.json`;
si uno falla, los que ya terminaron se conservan y se puede repetir sólo el que falló con --solo.
No se sobrescribe ningún archivo.
"""
import argparse
import json
import platform
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits

from scripts import evaluacion_comun_centrado_loo as v3
from scripts import t12_evaluar as ev
from scripts import t12_heterogeneidad as t12
from scripts.evaluacion_comun_contrato import exigir, sha

VERSION = 't12-controles-v1'
RAIZ = t12.RAIZ
REFERENCIA = ev.REFERENCIA
HET_GP, HET_G, GB_GP = 't12_het_GP', 't12_het_G', 't12_gb_GP'
CONTROL_GP = 't12_control_comun_GP'
N_PERMUTACIONES = 20
SEMILLA_REVUELTO = 20261015                 # la semilla de la permutación k es SEMILLA_REVUELTO + k, k = 1..20
FRACCIONES = (0.5, 0.75)                    # 1.0 sale de la evaluación principal
SEMILLAS_CURVA = (20261015, 20261016, 20261017)
N_MIN_SUBMUESTREO = 10
N_EXTREMAS = 20
MANIFEST = 'manifest_controles.json'
ARCHIVOS = {'C2': ('control_revuelto_t12.csv',),
            'C3': ('curva_aprendizaje_t12.csv',),
            'C4': ('desglose_error_t12.csv', 'sensibilidad_sin_alerta_t12.csv'),
            'C5': ('pendientes_por_municipio_t12.csv', 'importancia_gb_t12.csv'),
            'C6': ('parcelas_extremas_t12.csv',)}
ORDEN = ('C4', 'C6', 'C5', 'C3', 'C2')      # primero lo rápido; lo lento al final
CONTEXTOS_A = tuple(c for c in t12.CONTEXTOS if c[0] == 'A')
PRINCIPALES = ('predicciones_oof_t12.csv', 'seleccion_interna_t12.csv', 'comparacion_emparejada_t12.csv',
               'metricas_t12.csv', 'predicciones_59_t12.csv')
CALIDAD = 'registro/t07/calidad_parcelas.csv'


# ------------------------------------------------------------------ compuertas y entradas
def compuertas(raiz, solo=ORDEN):
    """Los controles sólo corren sobre la evaluación principal íntegra y con el código comprobado."""
    raiz = Path(raiz)
    cfg, comprobaciones = ev.compuertas(raiz, True)   # las barreras se confirmaron al correr el paso 4
    carpeta = raiz / 'registro/t12'
    ruta = carpeta / 'manifest.json'
    exigir(ruta.exists(), 'Falta la evaluación principal (registro/t12/manifest.json)')
    m = json.loads(ruta.read_text(encoding='utf-8'))
    exigir(m.get('schema') == 'manifest_t12_evaluacion_v1' and m.get('sha_diseno_t12') == t12.DISENO_SHA and
           m.get('barreras_confirmadas_por_la_persona') is True, 'Manifest de la evaluación principal inválido')
    exigir(m['sha_comprobaciones'] == sha(carpeta / 'comprobaciones.json'), 'Comprobaciones distintas de las usadas')
    for nombre in PRINCIPALES:
        exigir(sha(carpeta / nombre) == m['salidas_sha256'][nombre], f'Salida principal modificada: {nombre}')
    for archivo, huella in m['codigo_sha256'].items():
        exigir(sha(raiz / archivo) == huella, f'El código cambió después de la evaluación principal: {archivo}')
    for archivo, huella in m['entradas_sha256'].items():
        exigir(sha(raiz / archivo) == huella, f'Una entrada cambió después de la evaluación principal: {archivo}')
    exigir(set(solo) <= set(ARCHIVOS), 'Control desconocido')
    return cfg, m


def preparar_salida(salida, raiz, solo):
    raiz = Path(raiz).resolve()
    salida = Path(salida)
    salida = (salida if salida.is_absolute() else raiz / salida).resolve()
    permitidas = [raiz / 'registro/t12', raiz / 'reports']
    exigir(any(salida == p or p in salida.parents for p in permitidas),
           'La salida debe estar en registro/t12 o en una subcarpeta de reports/')
    ocupados = [a for c in solo for a in ARCHIVOS[c] if (salida / a).exists()]
    exigir(not ocupados, f'Conservar evidencia: ya existen {ocupados}')
    exigir(not (salida / MANIFEST).exists() or all(
        c not in json.loads((salida / MANIFEST).read_text())['controles'] for c in solo),
        'Alguno de esos controles ya está en el manifest de controles')
    return salida


def cargar_principal(carpeta):
    """OOF de los 8 procedimientos y de las dos referencias de T03, como DataFrame con columna `candidato`."""
    carpeta = Path(carpeta)
    oof = pd.read_csv(carpeta / 'predicciones_oof_t12.csv', float_precision='round_trip')
    return oof


def filas_a_df(filas):
    d = pd.DataFrame(filas)
    for c in ('real', 'prediccion'):
        d[c] = d[c].astype(float)
    d['repeticion'] = d.repeticion.astype(int)
    if 'particion' in d:
        d['particion'] = d.particion.astype(int)
    return d


def referencias_df(raiz):
    return filas_a_df(ev.cargar_referencias(raiz))


# ------------------------------------------------------------------ medidas
def dmae(cand, base, subconjunto='sin_respaldo'):
    """ΔMAE de T03 §4: promedio por parcela de la diferencia de error absoluto en sus repeticiones elegibles.

    `cand` y `base` son DataFrames con repeticion, ID_POLIGONO, real, prediccion y fuente. Es la misma
    cuenta que `comparar` de T15 (se prueba que coinciden), sin el bootstrap.
    """
    a = cand.set_index(['repeticion', 'ID_POLIGONO']).sort_index()
    b = base.set_index(['repeticion', 'ID_POLIGONO']).sort_index()
    exigir(a.index.is_unique and a.index.equals(b.index), 'Comparación no emparejada')
    d = (a.prediccion - a.real).abs() - (b.prediccion - b.real).abs()
    if subconjunto == 'sin_respaldo':
        d = d[(a.fuente == 'municipio').to_numpy()]
    exigir(len(d) > 0, 'Sin parcelas elegibles')
    return float(d.groupby(level='ID_POLIGONO').mean().mean())


def metricas_por_repeticion(g):
    """Métricas por repetición y su promedio (T03 §4: no se juntan las repeticiones antes de promediar)."""
    filas = []
    for _, x in g.groupby('repeticion'):
        e = x.prediccion - x.real
        total = ((x.real - x.real.mean()) ** 2).sum()
        filas.append(dict(n=len(x), MAE=e.abs().mean(), RMSE=np.sqrt((e ** 2).mean()), sesgo=e.mean(),
                          R2=1 - (e ** 2).sum() / total if total > 0 else np.nan))   # una sola parcela: sin R2
    return pd.DataFrame(filas).mean().to_dict()


# ------------------------------------------------------------------ C2 revuelto
def columnas_gp(cfg):
    """Todas las columnas G y P que usa alguna opción de t12_het_GP (ambas ventanas), en orden estable."""
    proc = next(p for p in cfg['procedimientos'] if p['candidato'] == HET_GP)
    cols = []
    for o in t12.opciones_registradas(proc):
        cols += [c for c in o['columnas'] if c not in cols]
    exigir(cols, 'Sin columnas G y P')
    return cols


def barajar(entradas, columnas, semilla):
    """Baraja las filas completas de `columnas` entre las etiquetadas del mismo municipio. Las reservadas no se tocan."""
    tabla = {k: dict(v) for k, v in entradas['tabla'].items()}
    por_municipio = {}
    for pid in sorted(entradas['conocidos']):
        por_municipio.setdefault(tabla[(pid,)]['municipio'], []).append(pid)
    rng = np.random.RandomState(semilla)
    for m in sorted(por_municipio):
        ids = por_municipio[m]
        perm = rng.permutation(len(ids))
        originales = [{c: tabla[(i,)][c] for c in columnas} for i in ids]
        for j, i in enumerate(ids):
            tabla[(i,)].update(originales[perm[j]])
    return {**entradas, 'tabla': tabla}


def emparejar(ref, oof):
    """La referencia sólo en las parcelas y repeticiones que se evaluaron (todas, en la corrida real)."""
    r = ref.merge(oof[['repeticion', 'ID_POLIGONO']].drop_duplicates(), on=['repeticion', 'ID_POLIGONO'])
    exigir(len(r) == len(oof), 'La referencia no cubre todas las predicciones evaluadas')
    return r


def revuelto_una(entradas, cfg, ref_a, k, contextos=CONTEXTOS_A):
    """Repite todo el procedimiento de t12_het_GP con el bloque GP revuelto (permutación k)."""
    semilla = SEMILLA_REVUELTO + k
    barajada = barajar(entradas, columnas_gp(cfg), semilla)
    proc = next(p for p in cfg['procedimientos'] if p['candidato'] == HET_GP)
    oof, _ = ev.evaluar_todos(barajada, [proc], contextos, procesos=1)
    oof = filas_a_df(oof)
    return dict(permutacion=k, semilla=semilla, dMAE_revuelto=dmae(oof, emparejar(ref_a, oof)))


def control_revuelto(entradas, cfg, ref_a, observado, n=N_PERMUTACIONES, contextos=CONTEXTOS_A, procesos=1, raiz=None):
    if procesos == 1:
        filas = [revuelto_una(entradas, cfg, ref_a, k, contextos) for k in range(1, n + 1)]
    else:
        exigir(raiz is not None and tuple(contextos) == CONTEXTOS_A, 'Varios procesos sólo con la corrida real')
        with ProcessPoolExecutor(max_workers=procesos, initializer=_iniciar, initargs=(str(raiz),)) as pool:
            filas = list(pool.map(_tarea_revuelto, range(1, n + 1)))
    t = pd.DataFrame(filas)
    t['dMAE_observado'] = observado
    t['igual_o_mejor_que_el_observado'] = t.dMAE_revuelto <= observado
    b = int(t.igual_o_mejor_que_el_observado.sum())
    t['b'], t['n_permutaciones'], t['p'] = b, n, (b + 1) / (n + 1)
    return {'control_revuelto_t12.csv': t}


# ------------------------------------------------------------------ C3 curva de aprendizaje
def submuestrear(tr, fraccion, rng):
    """Submuestrea sólo los municipios con al menos N_MIN_SUBMUESTREO filas; los pequeños quedan completos."""
    n = tr.municipio.value_counts()
    conservar = []
    for m in sorted(n.index):
        ids = sorted(tr.index[tr.municipio == m])
        if n[m] >= N_MIN_SUBMUESTREO:
            k = int(np.floor(fraccion * n[m] + 0.5))
            ids = sorted(str(i) for i in rng.choice(ids, size=k, replace=False))
        conservar += ids
    return tr.loc[sorted(conservar)]


def curva_una(entradas, cfg, fraccion, semilla, contextos=CONTEXTOS_A):
    """Referencia, control común GP y het_GP con el entrenamiento submuestreado; la evaluación no cambia."""
    procs = {p['candidato']: p for p in cfg['procedimientos']}
    filas = []
    with threadpool_limits(limits=1):
        for esc, rep, fold in contextos:
            tr, y, te = v3.preparar_contexto(entradas, esc, rep, fold)
            rng = np.random.RandomState([semilla, rep, fold])
            sub = submuestrear(tr, fraccion, rng)
            ys = y.loc[sub.index]
            detalles = {REFERENCIA: t12._referencia_sola('comun_v3', 'media').fit(sub, ys).predict_with_details(te)}
            for c in (CONTROL_GP, HET_GP):
                detalles[c] = t12.ajustar_y_predecir(sub, ys, te, procs[c], esc)['detalle']
            for c, det in detalles.items():
                for pid, pred, fu in zip(te.index, det.prediccion.to_numpy(), det.fuente.to_numpy()):
                    real = entradas['contextos'][(esc, rep, pid)]['real']
                    exigir(fu == entradas['contextos'][(esc, rep, pid)]['fuente'], 'El submuestreo cambió el respaldo')
                    filas.append(dict(procedimiento=c, fraccion=fraccion, semilla=semilla, repeticion=rep,
                                      ID_POLIGONO=pid, real=real, prediccion=float(pred), fuente=str(fu),
                                      n_entrenamiento=len(sub)))
    return filas


def resumen_curva(filas, fraccion, semilla):
    d = pd.DataFrame(filas)
    salida = []
    ref = d[d.procedimiento == REFERENCIA]
    for c, g in d.groupby('procedimiento', sort=False):
        for sub in ('sin_respaldo', 'todas'):
            z = g if sub == 'todas' else g[g.fuente == 'municipio']
            m = metricas_por_repeticion(z)
            salida.append(dict(procedimiento=c, fraccion=fraccion, semilla=semilla, subconjunto=sub,
                               n_entrenamiento_promedio=float(g.n_entrenamiento.mean()),
                               MAE=m['MAE'], RMSE=m['RMSE'], R2=m['R2'],
                               dMAE_vs_referencia=0.0 if c == REFERENCIA else dmae(g, ref, sub)))
    return salida


def control_curva(entradas, cfg, principal, ref_a, fracciones=FRACCIONES, semillas=SEMILLAS_CURVA,
                  contextos=CONTEXTOS_A, procesos=1, raiz=None):
    tareas = [(f, s) for f in fracciones for s in semillas]
    if procesos == 1:
        corridas = [curva_una(entradas, cfg, f, s, contextos) for f, s in tareas]
    else:
        exigir(raiz is not None and tuple(contextos) == CONTEXTOS_A, 'Varios procesos sólo con la corrida real')
        with ProcessPoolExecutor(max_workers=procesos, initializer=_iniciar, initargs=(str(raiz),)) as pool:
            corridas = list(pool.map(_tarea_curva, tareas))
    filas = []
    for (f, s), c in zip(tareas, corridas):
        filas += resumen_curva(c, f, s)
    # fracción 1.0: la evaluación principal, con la referencia de T03
    en_contextos = {(e, r, f) for e, r, f in contextos}
    dentro = lambda d: np.array([('A', r, f) in en_contextos for r, f in zip(d.repeticion, d.particion)], dtype=bool)
    a = principal[(principal.escenario == 'A').to_numpy() & dentro(principal)]
    ref_a = ref_a[dentro(ref_a)]
    completo = []
    n_tr = float(np.mean([len(v3.preparar_contexto(entradas, e, r, f)[0]) for e, r, f in contextos]))
    for c in (REFERENCIA, CONTROL_GP, HET_GP):
        z = (ref_a if c == REFERENCIA else a[a.candidato == c]).assign(procedimiento=c, n_entrenamiento=n_tr)
        completo += z.to_dict('records')
    filas += resumen_curva(completo, 1.0, 'completo')
    t = pd.DataFrame(filas)
    prom = (t[t.semilla != 'completo'].groupby(['procedimiento', 'fraccion', 'subconjunto'], sort=False)
            [['n_entrenamiento_promedio', 'MAE', 'RMSE', 'R2', 'dMAE_vs_referencia']].mean().reset_index())
    prom['semilla'] = 'promedio'
    t = pd.concat([t, prom], ignore_index=True).sort_values(['subconjunto', 'procedimiento', 'fraccion', 'semilla'],
                                                            key=lambda s: s.astype(str)).reset_index(drop=True)
    return {'curva_aprendizaje_t12.csv': t}


# ------------------------------------------------------------------ C4 desgloses
def atributos(raiz_o_ruta, particiones):
    """Cortes de T03 §4 bis por parcela, más municipio y grupo de registro."""
    cal = pd.read_csv(raiz_o_ruta, dtype={'escalon_etiqueta_municipio': str}).set_index('id_parcela')
    p = particiones.drop_duplicates('ID_POLIGONO').set_index('ID_POLIGONO')
    a = pd.DataFrame(index=p.index)
    a['municipio'] = p.municipio
    a['grupo_registro'] = p.grupo_registro
    a['contorno'] = np.where(cal.contorno_categoria.reindex(a.index) == 'A', 'A', 'B o C')
    a['angosta_o_muy_pequena'] = cal.contorno_angosta_o_muy_pequena.reindex(a.index)
    a['escalon_etiqueta'] = cal.escalon_etiqueta_municipio.reindex(a.index).fillna('sin escalón')
    a['vecina_etiquetada_menos_20m'] = cal.vecina_etiquetada_menos_20m.reindex(a.index)
    a['alerta_contorno_t03_bis'] = cal.alerta_contorno_t03_bis.reindex(a.index)
    return a


CORTES = ('municipio', 'grupo_registro', 'contorno', 'angosta_o_muy_pequena', 'escalon_etiqueta',
          'vecina_etiquetada_menos_20m', 'cuartil_error_referencia')


def cuartiles_referencia(oof_ref):
    """Cuartil del error absoluto de la referencia por parcela (promedio de sus repeticiones), por escenario."""
    salida = {}
    for esc, g in oof_ref.groupby('escenario'):
        e = (g.prediccion - g.real).abs().groupby(g.ID_POLIGONO).mean()
        q = pd.qcut(e.rank(method='first'), 4, labels=['Q1_menor_error', 'Q2', 'Q3', 'Q4_mayor_error'])
        salida[esc] = q.astype(str)
    return salida


def desgloses(oof, attr):
    """MAE, RMSE y sesgo por corte y categoría (repeticiones primero, después el promedio) y su ΔMAE frente a la referencia."""
    d = oof.copy()
    d = d.join(attr, on='ID_POLIGONO')
    cuart = cuartiles_referencia(d[d.candidato == REFERENCIA])
    d['cuartil_error_referencia'] = [cuart[e][i] for e, i in zip(d.escenario, d.ID_POLIGONO)]
    filas = []
    for sub in ('todas', 'sin_respaldo'):
        z = d if sub == 'todas' else d[d.fuente == 'municipio']
        for corte in CORTES:
            for (esc, cat), g in z.groupby(['escenario', corte]):
                base = g[g.candidato == REFERENCIA]
                for cand, x in g.groupby('candidato', sort=False):
                    m = metricas_por_repeticion(x)
                    filas.append(dict(
                        subconjunto=sub, escenario=esc, candidato=cand, desglose=corte, categoria=cat,
                        n_parcelas=x.ID_POLIGONO.nunique(), n_predicciones=len(x), MAE=m['MAE'], RMSE=m['RMSE'],
                        sesgo=m['sesgo'],
                        dMAE_vs_referencia=0.0 if cand == REFERENCIA else dmae(x, base, 'todas')))
    t = pd.DataFrame(filas)
    t['poco_informativo'] = t.n_parcelas < 5
    return t


def sensibilidad_sin_alerta(oof, attr):
    """Mismas métricas sin las parcelas con alerta de contorno (sólo en la evaluación; el entrenamiento no cambia)."""
    alerta = oof.ID_POLIGONO.map(attr.alerta_contorno_t03_bis == 'si').astype(bool)
    filas = []
    for sub in ('todas', 'sin_respaldo'):
        for esc in ('A', 'B'):
            base = {}
            for etiqueta, mascara in (('', pd.Series(True, index=oof.index)), ('_sin_alerta', ~alerta)):
                z = oof[mascara & (oof.escenario == esc)]
                z = z if sub == 'todas' else z[z.fuente == 'municipio']
                base[etiqueta] = z
            for cand in oof.candidato.unique():
                f = dict(subconjunto=sub, escenario=esc, candidato=cand)
                for etiqueta, z in base.items():
                    x, r = z[z.candidato == cand], z[z.candidato == REFERENCIA]
                    m = metricas_por_repeticion(x)
                    f.update({f'n_parcelas{etiqueta}': x.ID_POLIGONO.nunique(), f'MAE{etiqueta}': m['MAE'],
                              f'RMSE{etiqueta}': m['RMSE'], f'sesgo{etiqueta}': m['sesgo'],
                              f'dMAE{etiqueta}': 0.0 if cand == REFERENCIA else dmae(x, r, 'todas')})
                filas.append(f)
    return pd.DataFrame(filas)


def control_desgloses(principal, refs, attr):
    oof = pd.concat([principal, refs[refs.candidato == REFERENCIA]], ignore_index=True)
    return {'desglose_error_t12.csv': desgloses(oof, attr),
            'sensibilidad_sin_alerta_t12.csv': sensibilidad_sin_alerta(oof, attr)}


# ------------------------------------------------------------------ C5 qué aprendió
def reproducir_finales(entradas, cfg, principal, seleccion, candidatos, contextos=CONTEXTOS_A):
    """Reajusta con el entrenamiento externo la opción que el selector eligió (sin repetir la selección)
    y comprueba que reproduce las predicciones guardadas."""
    procs = {p['candidato']: p for p in cfg['procedimientos']}
    elegidas = seleccion[seleccion.elegida & (seleccion.escenario == 'A')]
    modelos = {}
    for cand in candidatos:
        proc = procs[cand]
        ops = {o['nombre']: o for o in t12.opciones_registradas(proc)}
        for esc, rep, fold in contextos:
            fila = elegidas[(elegidas.candidato == cand) & (elegidas.repeticion == rep) &
                            (elegidas.particion == fold)]
            exigir(len(fila) == 1, 'Selección guardada incompleta')
            fila = fila.iloc[0]
            tr, y, te = v3.preparar_contexto(entradas, esc, rep, fold)
            grupos = tuple(g for g in (fila.municipios_con_pendiente_propia if isinstance(
                fila.municipios_con_pendiente_propia, str) else '').split('|') if g)
            op = dict(nombre='referencia_sola', columnas=[], ventana='estatica') if fila.referencia_sola \
                else ops[fila.opcion]
            m = t12.fabrica(proc['familia'], op, grupos, t12.REFERENCIAS[proc['referencia']]).fit(tr, y)
            pred = m.predict(te)
            guardada = principal[(principal.candidato == cand) & (principal.escenario == esc) &
                                 (principal.repeticion == rep) & (principal.particion == fold)]
            guardada = guardada.set_index('ID_POLIGONO').prediccion.reindex(te.index)
            exigir(np.allclose(pred, guardada.to_numpy(), rtol=0, atol=1e-10),
                   f'No se reproduce la predicción guardada de {cand} en {esc}/{rep}/{fold}')
            modelos[cand, rep, fold] = (m, bool(fila.referencia_sola), fila.opcion)
    return modelos


def resumen_pendientes(modelos, cand):
    filas, n_ctx = [], 0
    for (c, rep, fold), (m, sola, opcion) in modelos.items():
        if c != cand:
            continue
        n_ctx += 1
        if sola:
            continue
        p = m.pendientes()
        for fila, v in p.iterrows():
            for var, coef in v.items():
                filas.append(dict(fila=fila, variable=var, coef=float(coef)))
    d = pd.DataFrame(filas)
    n_sola = sum(1 for (c, _, _), (_, s, _) in modelos.items() if c == cand and s)
    if d.empty:
        return pd.DataFrame()
    salida = []
    for (fila, var), g in d.groupby(['fila', 'variable'], sort=False):
        pos = float((g.coef > 0).mean())
        salida.append(dict(candidato=cand, fila='pendiente_comun' if fila == 'comun' else fila, variable=var,
                           n_contextos_con_coeficiente=len(g), n_contextos_total=n_ctx,
                           n_contextos_referencia_sola=n_sola, coef_estandarizado_medio=float(g.coef.mean()),
                           coef_estandarizado_sd=float(g.coef.std(ddof=0)), fraccion_positiva=pos,
                           fraccion_mismo_signo=max(pos, 1 - pos)))
    return pd.DataFrame(salida)


def resumen_importancia(modelos, cand):
    """Importancia media (descriptiva). Una variable sólo existe en los contextos cuya ventana la incluye;
    se informa tanto el promedio donde existe como el promedio sobre todos los contextos (0 si no existe)."""
    imp, n_ctx = [], 0
    for (c, rep, fold), (m, sola, opcion) in modelos.items():
        if c != cand:
            continue
        n_ctx += 1
        if not sola:
            imp.append(m.importancias())
    if not imp:
        return pd.DataFrame()
    d = pd.concat(imp, axis=1)
    t = pd.DataFrame(dict(candidato=cand, variable=d.index, n_contextos_con_la_variable=d.notna().sum(axis=1).to_numpy(),
                          n_contextos_total=n_ctx,
                          importancia_media_donde_existe=d.mean(axis=1).to_numpy(),
                          importancia_media_todos_los_contextos=(d.fillna(0.0).sum(axis=1) / n_ctx).to_numpy()))
    return t.sort_values('importancia_media_todos_los_contextos', ascending=False, kind='mergesort').reset_index(drop=True)


def control_que_aprendio(entradas, cfg, principal, seleccion, contextos=CONTEXTOS_A):
    modelos = reproducir_finales(entradas, cfg, principal, seleccion, (HET_GP, HET_G, GB_GP), contextos)
    pend = pd.concat([resumen_pendientes(modelos, c) for c in (HET_GP, HET_G)], ignore_index=True)
    return {'pendientes_por_municipio_t12.csv': pend,
            'importancia_gb_t12.csv': resumen_importancia(modelos, GB_GP)}


# ------------------------------------------------------------------ C6 parcelas extremas
def control_parcelas(principal, refs, attr, n=N_EXTREMAS):
    a = principal[(principal.escenario == 'A') & (principal.candidato == HET_GP)]
    r = refs[(refs.escenario == 'A') & (refs.candidato == REFERENCIA)]
    g = a.groupby('ID_POLIGONO').agg(real=('real', 'first'), prediccion_media=('prediccion', 'mean'),
                                     n_repeticiones=('repeticion', 'size'))
    g['referencia_media'] = r.groupby('ID_POLIGONO').prediccion.mean()
    g['error_abs_het_GP'] = (g.prediccion_media - g.real).abs()
    g['error_abs_referencia'] = (g.referencia_media - g.real).abs()
    g['d_error_abs'] = g.error_abs_het_GP - g.error_abs_referencia
    g = g.join(attr[['municipio', 'contorno', 'angosta_o_muy_pequena', 'vecina_etiquetada_menos_20m',
                     'alerta_contorno_t03_bis']])
    n = min(n, len(g) // 2)
    mejor = g.sort_values(['d_error_abs'], kind='mergesort').head(n).assign(grupo='mejora')
    peor = g.sort_values(['d_error_abs'], ascending=False, kind='mergesort').head(n).assign(grupo='empeora')
    t = pd.concat([mejor, peor])
    t['rango'] = t.groupby('grupo').cumcount() + 1
    t = t.reset_index().rename(columns={'index': 'ID_POLIGONO'})
    return {'parcelas_extremas_t12.csv': t[['grupo', 'rango', 'ID_POLIGONO', 'municipio', 'real', 'prediccion_media',
                                             'referencia_media', 'error_abs_het_GP', 'error_abs_referencia',
                                             'd_error_abs', 'n_repeticiones', 'contorno', 'angosta_o_muy_pequena',
                                             'vecina_etiquetada_menos_20m', 'alerta_contorno_t03_bis']]}


# ------------------------------------------------------------------ trabajadores (varios procesos)
_ESTADO = {}


def _iniciar(raiz):
    _ESTADO['limite'] = threadpool_limits(limits=1)
    _ESTADO['entradas'] = v3.cargar_entradas(raiz)
    _ESTADO['cfg'] = t12.cargar_diseno(raiz)
    r = referencias_df(raiz)
    _ESTADO['ref_a'] = r[(r.escenario == 'A') & (r.candidato == REFERENCIA)]


def _tarea_revuelto(k):
    return revuelto_una(_ESTADO['entradas'], _ESTADO['cfg'], _ESTADO['ref_a'], k)


def _tarea_curva(tarea):
    return curva_una(_ESTADO['entradas'], _ESTADO['cfg'], *tarea)


# ------------------------------------------------------------------ orquestación
def valor_observado(carpeta, principal, ref_a):
    """ΔMAE de t12_het_GP en A/sin_respaldo, recalculado y contrastado con la tabla guardada."""
    c = pd.read_csv(Path(carpeta) / 'comparacion_emparejada_t12.csv')
    fila = c[c.aplica_promocion]
    exigir(len(fila) == 1, 'La tabla principal no marca el candidato promovible')
    d = dmae(principal[(principal.escenario == 'A') & (principal.candidato == HET_GP)], ref_a)
    exigir(abs(d - float(fila.iloc[0].dMAE)) < 1e-12, 'ΔMAE observado distinto del de la tabla principal')
    return d


def escribir(salida, tablas):
    salida.mkdir(parents=True, exist_ok=True)
    for nombre, t in tablas.items():
        exigir(not (salida / nombre).exists(), f'Ya existe {nombre}')
        t.to_csv(salida / nombre, index=False, float_format='%.17g')
    return {n: sha(salida / n) for n in tablas}


def anotar(salida, raiz, control, huellas, procesos):
    import sklearn
    ruta = salida / MANIFEST
    m = json.loads(ruta.read_text(encoding='utf-8')) if ruta.exists() else dict(
        schema='manifest_t12_controles_v1', version=VERSION, controles={})
    exigir(control not in m['controles'], f'{control} ya está en el manifest')
    m['controles'][control] = dict(
        archivos_sha256=huellas, procesos=procesos,
        entorno=dict(sistema=platform.system(), python=platform.python_version(), numpy=np.__version__,
                     pandas=pd.__version__, sklearn=sklearn.__version__),
        codigo_sha256={f: sha(Path(raiz) / f) for f in ev.CODIGO + ('scripts/t12_controles.py',)})
    ruta.write_text(json.dumps(m, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def ejecutar(salida='registro/t12', raiz=RAIZ, solo=ORDEN, procesos=1, contextos=CONTEXTOS_A,
             n_permutaciones=N_PERMUTACIONES, fracciones=FRACCIONES, semillas=SEMILLAS_CURVA):
    raiz = Path(raiz)
    solo = [c for c in ORDEN if c in solo]
    cfg, m = compuertas(raiz, solo)
    destino = preparar_salida(salida, raiz, solo)
    carpeta = raiz / 'registro/t12'
    entradas = v3.cargar_entradas(raiz)
    principal = cargar_principal(carpeta)
    seleccion = pd.read_csv(carpeta / 'seleccion_interna_t12.csv')
    refs = referencias_df(raiz)
    ref_a = refs[(refs.escenario == 'A') & (refs.candidato == REFERENCIA)]
    part = pd.DataFrame(entradas['particiones'])
    attr = atributos(raiz / CALIDAD, part)
    for c in solo:
        print(f'{c} ...', flush=True)
        if c == 'C4':
            tablas = control_desgloses(principal, refs, attr)
        elif c == 'C6':
            tablas = control_parcelas(principal, refs, attr)
        elif c == 'C5':
            tablas = control_que_aprendio(entradas, cfg, principal, seleccion, contextos)
        elif c == 'C3':
            tablas = control_curva(entradas, cfg, principal, ref_a, fracciones, semillas, contextos, procesos, raiz)
        else:
            observado = valor_observado(carpeta, principal, ref_a)
            tablas = control_revuelto(entradas, cfg, ref_a, observado, n_permutaciones, contextos, procesos, raiz)
        anotar(destino, raiz, c, escribir(destino, tablas), procesos)
        print(f'{c} listo: {", ".join(tablas)}', flush=True)
    return destino


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--raiz', type=Path, default=RAIZ)
    p.add_argument('--controles', action='store_true', help='corre los controles C2 a C6')
    p.add_argument('--solo', nargs='+', choices=sorted(ARCHIVOS), default=list(ORDEN),
                   help='sólo estos controles (por defecto todos)')
    p.add_argument('--salida', type=Path, default=Path('registro/t12'))
    p.add_argument('--procesos', type=int, default=1, help='C2 y C3 en paralelo; no cambia el resultado')
    a = p.parse_args(argv)
    exigir(a.controles, 'Falta --controles')
    exigir(a.procesos >= 1, '--procesos debe ser al menos 1')
    destino = ejecutar(a.salida, a.raiz, a.solo, a.procesos)
    print(f'Guardado en {destino}')


if __name__ == '__main__':
    main()
