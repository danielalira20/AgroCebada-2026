"""T12 paso 6: auditor independiente.

Rehace, con NumPy y sin importar nada del código de producción (`t12_heterogeneidad`, `t12_evaluar`,
`t12_controles` ni los módulos de T15), lo que la evaluación principal guardó en `registro/t12/`:

  1. Los ajustes de la familia `het` (t12_het_GP, t12_het_G, t12_het_P y el control de mediana) en todos los
     contextos externos: referencia, residuo sin la fila, transformaciones, centro sin la fila y mínimos
     cuadrados aumentados resueltos con la ecuación normal (no `Ridge` ni SVD). Compara las predicciones y el
     respaldo con `predicciones_oof_t12.csv`.
  2. La selección interna: MAE interno de cada opción (con la referencia sola compitiendo), población elegible,
     lista de municipios con pendiente propia, desempate registrado y opción elegida.
  3. Las métricas por repetición y los ΔMAE, ΔRMSE, repeticiones que mejoran, IC95 por remuestreo de celdas y
     la regla de T03 de las 13 comparaciones.
  4. Con --controles, los controles C2 a C6 que se pueden rehacer desde las predicciones guardadas.

Lo único que comparte con la producción es lo declarado en el diseño y no es aritmética del modelo: la semilla
y el sorteo del remuestreo de celdas, y las particiones internas de scikit-learn (`StratifiedKFold`,
`GroupKFold`). El auditor solo lee: no modifica nada de `registro/t12/` y escribe `auditoria_t12.json`
(nunca sobrescribe).
"""
import argparse
import csv
import hashlib
import json
import platform
from collections import Counter
from math import sqrt
from pathlib import Path

import numpy as np
from sklearn.model_selection import GroupKFold, StratifiedKFold

RAIZ = Path(__file__).resolve().parents[1]
VERSION = 't12-auditor-v1'
CARPETA = 'registro/t12'
SALIDA = 'auditoria_t12.json'
TOL_PREDICCION = 1e-10
TOL_MAE_INTERNO = 1e-10
TOL_METRICA = 1e-12
N_MIN_PENDIENTE = 12
SEMILLA_BOOTSTRAP = 20261006
REPLICAS = 5000
N_CONTEXTOS_ESPERADOS = 50
REF_MEDIA, REF_MEDIANA = 'media_mun__resp_grupo', 'mediana_mun__resp_grupo'
REFERENCIAS_T03 = {REF_MEDIA: 'registro/t03/predicciones_oof_referencias_media_mun__resp_grupo.csv',
                   REF_MEDIANA: 'registro/t03/predicciones_oof_referencias_mediana_mun__resp_grupo.csv'}
ESTADISTICO = {REF_MEDIA: np.mean, REF_MEDIANA: np.median}
PENDIENTE = 'pendiente_media_t10_grados'
PRINCIPALES = ('predicciones_oof_t12.csv', 'seleccion_interna_t12.csv', 'comparacion_emparejada_t12.csv',
               'metricas_t12.csv', 'predicciones_59_t12.csv')


def exigir(ok, mensaje):
    if not ok:
        raise ValueError(mensaje)


def sha(ruta):
    return hashlib.sha256(Path(ruta).read_bytes()).hexdigest()


def leer_csv(ruta):
    with open(ruta, newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def num(texto):
    texto = (texto or '').strip()
    return float(texto) if texto else float('nan')


def cerca(a, b):
    """Diferencia absoluta; dos vacíos (NaN) coinciden."""
    a, b = float(a), float(b)
    if np.isnan(a) and np.isnan(b):
        return 0.0
    if np.isnan(a) or np.isnan(b):
        return float('inf')
    return abs(a - b)


# ------------------------------------------------------------------ datos
class Datos:
    """Tabla común y particiones de T03 leídas directamente de los CSV."""

    def __init__(self, raiz):
        raiz = Path(raiz)
        self.fila = {r['id_parcela']: r for r in leer_csv(raiz / 'registro/t07/tabla_comun.csv')}
        self.etiquetadas = sorted(i for i, r in self.fila.items() if r['rendimiento_t_ha'].strip())
        self.reservadas = sorted(i for i, r in self.fila.items() if not r['rendimiento_t_ha'].strip())
        self.part = {}
        for r in leer_csv(raiz / 'registro/t03/particiones.csv'):
            self.part.setdefault(int(r['repeticion']), []).append(r)
        for rep, recs in self.part.items():
            exigir(sorted(r['ID_POLIGONO'] for r in recs) == self.etiquetadas,
                   f'Las particiones de la repetición {rep} no cubren exactamente las etiquetadas')
        self.y = {i: float(self.fila[i]['rendimiento_t_ha']) for i in self.etiquetadas}

    def contexto(self, esc, rep, fold):
        col = 'particion_principal' if esc == 'A' else 'particion_espacial'
        recs = self.part[rep]
        entrenamiento = sorted(r['ID_POLIGONO'] for r in recs if int(r[col]) != fold)
        evaluacion = sorted(r['ID_POLIGONO'] for r in recs if int(r[col]) == fold)
        celda = {r['ID_POLIGONO']: r['celda_chirps'] for r in recs}
        return entrenamiento, evaluacion, celda


# ------------------------------------------------------------------ ajuste het con NumPy
def pools_sin_fila(mun, grp):
    """Para cada fila: las demás del municipio; si no hay, las del grupo; si no, todas las demás."""
    n = len(mun)
    pools = []
    for k in range(n):
        for mascara in (mun == mun[k], grp == grp[k], np.ones(n, bool)):
            m = mascara.copy()
            m[k] = False
            if m.any():
                pools.append(np.flatnonzero(m))
                break
        else:
            raise ValueError('Fila sin ninguna otra fila de respaldo')
    return pools


def crudo(datos, ids, columnas, mediana_pendiente=None):
    v = np.array([[num(datos.fila[i][c]) for c in columnas] for i in ids], dtype=float)
    if 'area_ha_origen' in columnas:
        j = columnas.index('area_ha_origen')
        v[:, j] = np.log(v[:, j])
    extra = []
    if PENDIENTE in columnas:
        j = columnas.index(PENDIENTE)
        falta = np.isnan(v[:, j])
        if mediana_pendiente is None:
            mediana_pendiente = float(np.median(v[~falta, j]))
        v[falta, j] = mediana_pendiente
        extra.append(falta.astype(float))
    if extra:
        v = np.column_stack([v, *extra])
    return v, mediana_pendiente


def ajustar(datos, entrenamiento, columnas, lam, kappa, grupos, referencia):
    """Referencia + corrección lineal con pendiente común y desviación municipal contraída.

    Minimiza ||r - A c||² + n·λ·(||β||² + κ·Σ||γ_g||²) con A = [D | D·1{g}/√κ ...]; se resuelve la ecuación
    normal (AᵀA + n·λ·I) c = Aᵀ r.
    """
    estadistico = ESTADISTICO[referencia]
    mun = np.array([datos.fila[i]['municipio'] for i in entrenamiento])
    grp = np.array([datos.fila[i]['cultivo_origen'] for i in entrenamiento])
    y = np.array([datos.y[i] for i in entrenamiento])
    modelo = dict(columnas=list(columnas),
                  ref_mun={m: float(estadistico(y[mun == m])) for m in sorted(set(mun))},
                  ref_grp={g: float(estadistico(y[grp == g])) for g in sorted(set(grp))},
                  ref_global=float(estadistico(y)), grupos=tuple(grupos))
    if not columnas:
        return modelo
    pools = pools_sin_fila(mun, grp)
    residuo = y - np.array([estadistico(y[p]) for p in pools])
    x, mediana = crudo(datos, entrenamiento, list(columnas))
    mu, sd = x.mean(axis=0), x.std(axis=0)
    sd = np.where(sd == 0, 1.0, sd)
    z = (x - mu) / sd
    d = z - np.array([z[p].mean(axis=0) for p in pools])
    bloques = [d] + [d * (mun == g)[:, None] / sqrt(kappa) for g in grupos]
    a = np.hstack(bloques)
    alpha = len(entrenamiento) * float(lam)
    coef = np.linalg.solve(a.T @ a + alpha * np.eye(a.shape[1]), a.T @ residuo)
    p = d.shape[1]
    modelo.update(
        mediana_pendiente=mediana, mu=mu, sd=sd, beta=coef[:p],
        gamma={g: coef[p * (k + 1):p * (k + 2)] / sqrt(kappa) for k, g in enumerate(grupos)},
        centro_mun={m: z[mun == m].mean(axis=0) for m in sorted(set(mun))},
        centro_grp={g: z[grp == g].mean(axis=0) for g in sorted(set(grp))}, centro_global=z.mean(axis=0))
    return modelo


def predecir(modelo, datos, ids):
    pred, fuente = [], []
    z = None
    if modelo['columnas']:
        x, _ = crudo(datos, ids, modelo['columnas'], modelo['mediana_pendiente'])
        z = (x - modelo['mu']) / modelo['sd']
    for k, i in enumerate(ids):
        m, g = datos.fila[i]['municipio'], datos.fila[i]['cultivo_origen']
        if m in modelo['ref_mun']:
            base, fu, centro = modelo['ref_mun'][m], 'municipio', modelo.get('centro_mun', {}).get(m)
        elif g in modelo['ref_grp']:
            base, fu, centro = modelo['ref_grp'][g], 'grupo', modelo.get('centro_grp', {}).get(g)
        else:
            base, fu, centro = modelo['ref_global'], 'global', modelo.get('centro_global')
        if modelo['columnas']:
            pendiente = modelo['beta'] + (modelo['gamma'][m] if m in modelo['gamma'] else 0.0)
            base = base + float((z[k] - centro) @ pendiente)
        pred.append(base)
        fuente.append(fu)
    return np.array(pred), fuente


def grupos_con_pendiente(datos, entrenamiento):
    n = Counter(datos.fila[i]['municipio'] for i in entrenamiento)
    return tuple(sorted(m for m, c in n.items() if c >= N_MIN_PENDIENTE))


# ------------------------------------------------------------------ selección interna
def clave_desempate(p):
    """MAE a 6 decimales > referencia sola > λ mayor > κ mayor > jun_oct > nombre (diseño §5.1)."""
    return (round(p['MAE'], 6), 0 if p['referencia_sola'] else 1, -(p['lambda_reg'] or 0), -(p['kappa'] or 0),
            0 if p['ventana'] == 'jun_oct' else 1, p['nombre'])


def divisiones_internas(datos, entrenamiento, esc, celda):
    mun = [datos.fila[i]['municipio'] for i in entrenamiento]
    n = len(entrenamiento)
    if esc == 'A':
        cuentas = Counter(mun)
        estratos = np.array([m if cuentas[m] >= 4 else 'otros' for m in mun])
        return list(StratifiedKFold(4, shuffle=True, random_state=0).split(np.zeros(n), estratos))
    return list(GroupKFold(4, shuffle=False).split(np.zeros(n), groups=[celda[i] for i in entrenamiento]))


def reconstruir_seleccion(datos, entrenamiento, esc, celda, opciones, referencia, grupos=None):
    grupos = grupos_con_pendiente(datos, entrenamiento) if grupos is None else tuple(grupos)
    divisiones = divisiones_internas(datos, entrenamiento, esc, celda)
    alternativas = [dict(nombre='referencia_sola', columnas=[], ventana='estatica', lambda_reg=None, kappa=None)]
    alternativas += [dict(o) for o in opciones]
    puntuaciones = []
    for op in alternativas:
        errores, todos = [], []
        for ia, ib in divisiones:
            tr = [entrenamiento[i] for i in ia]
            va = [entrenamiento[i] for i in ib]
            modelo = ajustar(datos, tr, op['columnas'], op['lambda_reg'], op['kappa'], grupos, referencia)
            pred, _ = predecir(modelo, datos, va)
            err = np.abs(pred - np.array([datos.y[i] for i in va]))
            en_tr = {datos.fila[i]['municipio'] for i in tr}
            elegible = np.array([datos.fila[i]['municipio'] in en_tr for i in va])
            errores.extend(err[elegible])
            todos.extend(err)
        exigir(errores, 'Opción sin casos elegibles')
        puntuaciones.append(dict(nombre=op['nombre'], ventana=op['ventana'], lambda_reg=op['lambda_reg'],
                                 kappa=op['kappa'], referencia_sola=not op['columnas'],
                                 MAE=float(np.mean(errores)), MAE_todas=float(np.mean(todos)),
                                 n_elegibles=len(errores), n_validacion=len(todos)))
    ganadora = min(puntuaciones, key=clave_desempate)
    return dict(grupos=grupos, puntuaciones=puntuaciones, elegida=ganadora['nombre'],
                opciones={o['nombre']: o for o in alternativas})


def auditar_het(raiz, carpeta, datos, diseno, contextos, oof):
    """Selección interna y predicción final de cada procedimiento `het` en cada contexto."""
    seleccion_csv = {}
    for r in leer_csv(carpeta / 'seleccion_interna_t12.csv'):
        seleccion_csv.setdefault((r['candidato'], r['escenario'], int(r['repeticion']), int(r['particion'])),
                                 []).append(r)
    peor = dict(prediccion=0.0, MAE_interno=0.0, MAE_todas=0.0)
    problemas, filas, n_pred, n_sel = [], [], 0, 0
    for proc in diseno['procedimientos']:
        if proc['familia'] != 'het':
            continue
        cand, referencia = proc['candidato'], proc['referencia']
        for esc, rep, fold in contextos:
            entrenamiento, evaluacion, celda = datos.contexto(esc, rep, fold)
            sel = reconstruir_seleccion(datos, entrenamiento, esc, celda, proc['opciones'], referencia)
            guardadas = seleccion_csv.get((cand, esc, rep, fold), [])
            etiqueta = f'{cand}/{esc}/{rep}/{fold}'
            # --- selección
            exigir(len(guardadas) == len(sel['puntuaciones']), f'Opciones guardadas distintas en {etiqueta}')
            por_nombre = {g['opcion']: g for g in guardadas}
            d_sel = 0.0
            for p in sel['puntuaciones']:
                g = por_nombre.get(p['nombre'])
                if g is None:
                    problemas.append(f'{etiqueta}: opción {p["nombre"]} no está en la selección guardada')
                    continue
                d_sel = max(d_sel, abs(p['MAE'] - float(g['MAE_interno'])))
                peor['MAE_todas'] = max(peor['MAE_todas'], abs(p['MAE_todas'] - float(g['MAE_todas_internas'])))
                if (p['n_elegibles'], p['n_validacion']) != (int(g['n_elegibles']), int(g['n_validacion'])):
                    problemas.append(f'{etiqueta}: conteos internos distintos en {p["nombre"]}')
                if str(p['referencia_sola']) != g['referencia_sola']:
                    problemas.append(f'{etiqueta}: bandera de referencia sola distinta en {p["nombre"]}')
            peor['MAE_interno'] = max(peor['MAE_interno'], d_sel)
            elegida_csv = [g['opcion'] for g in guardadas if g['elegida'] == 'True']
            if elegida_csv != [sel['elegida']]:
                problemas.append(f'{etiqueta}: elegida {elegida_csv} guardada vs {sel["elegida"]} reconstruida')
            grupos_csv = tuple(g for g in (guardadas[0]['municipios_con_pendiente_propia'] or '').split('|') if g)
            if grupos_csv != sel['grupos']:
                problemas.append(f'{etiqueta}: municipios con pendiente propia {grupos_csv} vs {sel["grupos"]}')
            n_sel += 1
            # --- predicción final con la opción GUARDADA (aísla el álgebra de la selección)
            op = sel['opciones'][elegida_csv[0]] if len(elegida_csv) == 1 and elegida_csv[0] in sel['opciones'] \
                else sel['opciones'][sel['elegida']]
            modelo = ajustar(datos, entrenamiento, op['columnas'], op['lambda_reg'], op['kappa'], sel['grupos'],
                             referencia)
            pred, fuente = predecir(modelo, datos, evaluacion)
            d_pred = 0.0
            for i, p, fu in zip(evaluacion, pred, fuente):
                guardado = oof[cand].get((esc, rep, i))
                if guardado is None:
                    problemas.append(f'{etiqueta}: falta {i} en las predicciones guardadas')
                    continue
                d_pred = max(d_pred, abs(p - guardado[1]))
                if fu != guardado[2]:
                    problemas.append(f'{etiqueta}: respaldo de {i} {fu} vs {guardado[2]}')
                n_pred += 1
            peor['prediccion'] = max(peor['prediccion'], d_pred)
            filas.append(dict(candidato=cand, escenario=esc, repeticion=rep, particion=fold,
                              opcion_elegida=elegida_csv[0] if elegida_csv else None,
                              dif_max_prediccion=d_pred, dif_max_MAE_interno=d_sel))
    aprobado = (not problemas and peor['prediccion'] < TOL_PREDICCION and peor['MAE_interno'] < TOL_MAE_INTERNO
                and peor['MAE_todas'] < TOL_MAE_INTERNO)
    return dict(aprobado=bool(aprobado), procedimientos=sorted({f['candidato'] for f in filas}),
                contextos=len(contextos), selecciones_reconstruidas=n_sel, predicciones_comparadas=n_pred,
                dif_max_prediccion=peor['prediccion'], dif_max_MAE_interno=peor['MAE_interno'],
                dif_max_MAE_todas_internas=peor['MAE_todas'], tolerancia_prediccion=TOL_PREDICCION,
                tolerancia_MAE_interno=TOL_MAE_INTERNO, problemas=problemas[:50], n_problemas=len(problemas)), filas


# ------------------------------------------------------------------ OOF, métricas y comparaciones
def cargar_oof(raiz, carpeta):
    """candidato -> {(escenario, repeticion, id): (real, prediccion, fuente, particion)}."""
    oof = {}
    for ruta in [carpeta / 'predicciones_oof_t12.csv', *(Path(raiz) / r for r in REFERENCIAS_T03.values())]:
        for r in leer_csv(ruta):
            clave = (r['escenario'], int(r['repeticion']), r['ID_POLIGONO'])
            exigir(clave not in oof.setdefault(r['candidato'], {}), f'Predicción duplicada {clave}')
            oof[r['candidato']][clave] = (float(r['real']), float(r['prediccion']), r['fuente'], int(r['particion']))
    return oof


def integridad_oof(datos, oof, contextos):
    """Cada candidato tiene exactamente las 1,380 predicciones (en los contextos auditados), con la etiqueta de
    la tabla común, la partición de T03 y ninguna parcela reservada."""
    problemas = []
    esperado = set()
    for esc, rep, fold in contextos:
        _, evaluacion, _ = datos.contexto(esc, rep, fold)
        esperado |= {(esc, rep, i) for i in evaluacion}
    for cand, filas in sorted(oof.items()):
        if set(filas) != esperado:
            problemas.append(f'{cand}: claves distintas de las esperadas ({len(filas)} vs {len(esperado)})')
        for (esc, rep, i), (real, _, _, fold) in filas.items():
            if i not in datos.y or real != datos.y[i]:
                problemas.append(f'{cand}: etiqueta de {i} distinta de la tabla común')
                break
        if set(i for _, _, i in filas) & set(datos.reservadas):
            problemas.append(f'{cand}: contiene parcelas reservadas')
    return dict(aprobado=not problemas, candidatos=sorted(oof), predicciones_por_candidato=len(esperado),
                problemas=problemas[:50])


def metricas_rep(real, pred):
    e = pred - real
    constante = bool(np.all(real == real[0]))
    return dict(n=len(real), MAE=float(np.abs(e).mean()), RMSE=float(np.sqrt(np.mean(e ** 2))),
                sesgo=float(e.mean()),
                R2=float('nan') if constante else float(1 - np.sum(e ** 2) / np.sum((real - real.mean()) ** 2)))


def auditar_metricas(carpeta, oof):
    guardadas = {(r['candidato'], r['escenario'], r['subconjunto'], r['repeticion']): r
                 for r in leer_csv(carpeta / 'metricas_t12.csv')}
    usadas, peor, problemas = set(), 0.0, []
    for cand, filas in sorted(oof.items()):
        for esc in ('A', 'B'):
            for sub in ('todas', 'sin_respaldo'):
                por_rep = []
                for rep in range(1, 6):
                    f = [v for (e, r, _), v in sorted(filas.items())
                         if e == esc and r == rep and (sub == 'todas' or v[2] == 'municipio')]
                    por_rep.append(metricas_rep(np.array([v[0] for v in f]), np.array([v[1] for v in f])))
                esperadas = {str(i + 1): m for i, m in enumerate(por_rep)}
                esperadas['promedio'] = {k: float(np.mean([m[k] for m in por_rep]))
                                         for k in ('n', 'MAE', 'RMSE', 'sesgo', 'R2')}
                for rep, m in esperadas.items():
                    g = guardadas.get((cand, esc, sub, rep))
                    usadas.add((cand, esc, sub, rep))
                    if g is None:
                        problemas.append(f'falta {(cand, esc, sub, rep)} en metricas_t12.csv')
                        continue
                    for k in ('n', 'MAE', 'RMSE', 'sesgo', 'R2'):
                        peor = max(peor, cerca(m[k], num(g[k])))
    extra = set(guardadas) - usadas
    if extra:
        problemas.append(f'{len(extra)} filas de más en metricas_t12.csv')
    return dict(aprobado=bool(not problemas and peor <= TOL_METRICA), filas_comparadas=len(usadas),
                dif_max=peor, tolerancia=TOL_METRICA, problemas=problemas[:50])


def comparar(oof, referencia_media, celdas, cand, base, esc, sub):
    """ΔMAE por parcela, IC95 por remuestreo de celdas, ΔRMSE, repeticiones que mejoran y regla de T03."""
    por_parcela, por_rep = {}, {}
    for (e, rep, i), (real, _, fuente, _) in sorted(oof[referencia_media].items()):
        if e != esc or (sub == 'sin_respaldo' and fuente != 'municipio'):
            continue
        a, b = oof[cand][(e, rep, i)], oof[base][(e, rep, i)]
        ea, eb = a[1] - real, b[1] - real
        v = np.array([abs(ea), abs(eb), ea ** 2, eb ** 2])
        por_parcela.setdefault(i, []).append(v)
        por_rep.setdefault(rep, []).append(v)
    pp = {i: np.mean(v, axis=0) for i, v in por_parcela.items()}
    pr = {r: np.mean(v, axis=0) for r, v in por_rep.items()}
    exigir(sorted(pr) == [1, 2, 3, 4, 5], 'Repeticiones elegibles incompletas')
    d_mae = float(np.mean([v[0] - v[1] for v in pp.values()]))
    d_mae_rep = [float(pr[r][0] - pr[r][1]) for r in range(1, 6)]
    d_rmse_rep = [float(sqrt(pr[r][2]) - sqrt(pr[r][3])) for r in range(1, 6)]
    d_rmse = float(np.mean(d_rmse_rep))
    por_celda = {}
    for i, v in pp.items():
        por_celda.setdefault(celdas[i], []).append(v)
    nombres = sorted(por_celda)
    sumas = np.array([np.sum(por_celda[c], axis=0) for c in nombres])
    tamanos = np.array([len(por_celda[c]) for c in nombres], dtype=float)
    idx = np.random.RandomState(SEMILLA_BOOTSTRAP).randint(len(nombres), size=(REPLICAS, len(nombres)))
    total = tamanos[idx].sum(axis=1)
    medias = np.stack([sumas[:, j][idx].sum(axis=1) / total for j in range(4)], axis=1)
    lo, hi = np.percentile(medias[:, 0] - medias[:, 1], [2.5, 97.5])
    rlo, rhi = np.percentile(np.sqrt(medias[:, 2]) - np.sqrt(medias[:, 3]), [2.5, 97.5])
    mejoran = int(sum(d < 0 for d in d_mae_rep))
    return dict(n_parcelas=len(pp), n_predicciones=sum(len(v) for v in por_parcela.values()), n_celdas=len(nombres),
                dMAE=d_mae, dRMSE=d_rmse, repeticiones_mejoran_MAE=mejoran,
                diferencia_MAE_media_por_repeticion=float(np.mean(d_mae_rep)),
                IC95_MAE_inf=float(lo), IC95_MAE_sup=float(hi), IC95_RMSE_inf=float(rlo), IC95_RMSE_sup=float(rhi),
                cumple_regla_T03=bool(d_mae <= -0.01 and hi < 0 and mejoran >= 4 and d_rmse <= 0.01),
                **{f'dMAE_rep{r}': d_mae_rep[r - 1] for r in range(1, 6)})


def auditar_comparaciones(carpeta, oof, datos, diseno):
    celdas = {r['ID_POLIGONO']: r['celda_chirps'] for r in datos.part[1]}
    guardadas = leer_csv(carpeta / 'comparacion_emparejada_t12.csv')
    numericas = ['dMAE', 'dRMSE', 'diferencia_MAE_media_por_repeticion', 'IC95_MAE_inf', 'IC95_MAE_sup',
                 'IC95_RMSE_inf', 'IC95_RMSE_sup'] + [f'dMAE_rep{r}' for r in range(1, 6)]
    enteras = ['n_parcelas', 'n_predicciones', 'n_celdas', 'repeticiones_mejoran_MAE']
    problemas, peor = [], 0.0
    esperados = set()
    for p in diseno['procedimientos']:
        c = p['candidato']
        pares = [(c, REF_MEDIANA), (c, REF_MEDIA)] if p['referencia'] == REF_MEDIANA else [(c, REF_MEDIA)]
        esperados |= {(a, b, e, s) for a, b in pares for e in ('A', 'B') for s in ('todas', 'sin_respaldo')}
    for a, b in diseno['controles']['C1_ablacion']['pares']:
        esperados |= {(a, b, e, s) for e in ('A', 'B') for s in ('todas', 'sin_respaldo')}
    vistos = set()
    for g in guardadas:
        clave = (g['candidato'], g['frente_a'], g['escenario'], g['subconjunto'])
        vistos.add(clave)
        r = comparar(oof, REF_MEDIA, celdas, *clave)
        for k in numericas:
            peor = max(peor, cerca(r[k], num(g[k])))
        for k in enteras:
            if r[k] != int(g[k]):
                problemas.append(f'{clave}: {k} {r[k]} vs {g[k]}')
        if r['cumple_regla_T03'] != (g['cumple_regla_T03'] == 'True'):
            problemas.append(f'{clave}: regla de T03 distinta')
        aplica = (clave == ('t12_het_GP', REF_MEDIA, 'A', 'sin_respaldo'))
        if (g['aplica_promocion'] == 'True') != aplica:
            problemas.append(f'{clave}: marca de promoción incorrecta')
        estado = ('cumple_T03_pendiente_C2_revuelto' if r['cumple_regla_T03'] else 'no_cumple_T03') if aplica \
            else 'no_aplica'
        if g['estado_promocion'] != estado:
            problemas.append(f'{clave}: estado de promoción {g["estado_promocion"]} vs {estado}')
    if vistos != esperados or len(guardadas) != len(esperados):
        problemas.append(f'Comparaciones guardadas distintas de las del diseño ({len(guardadas)} vs {len(esperados)})')
    return dict(aprobado=bool(not problemas and peor <= TOL_METRICA), comparaciones=len(guardadas), dif_max=peor,
                tolerancia=TOL_METRICA, replicas=REPLICAS, semilla=SEMILLA_BOOTSTRAP, problemas=problemas[:50])


# ------------------------------------------------------------------ controles C2 a C6
def d_mae_parcela(oof, cand, base, esc, sub, ids=None, referencia_media=REF_MEDIA):
    """ΔMAE: promedio por parcela del promedio (en sus repeticiones elegibles) de |e_cand| - |e_base|."""
    d = {}
    for (e, rep, i), (real, _, fuente, _) in oof[referencia_media].items():
        if e != esc or (sub == 'sin_respaldo' and fuente != 'municipio') or (ids is not None and i not in ids):
            continue
        d.setdefault(i, []).append(abs(oof[cand][(e, rep, i)][1] - real) - abs(oof[base][(e, rep, i)][1] - real))
    return float(np.mean([np.mean(v) for v in d.values()])) if d else float('nan')


def mae_rmse_sesgo(oof, cand, esc, sub, ids=None, referencia_media=REF_MEDIA):
    por_rep = {}
    for (e, rep, i), (real, pred, fuente, _) in oof[cand].items():
        if e != esc or (sub == 'sin_respaldo' and fuente != 'municipio') or (ids is not None and i not in ids):
            continue
        por_rep.setdefault(rep, []).append((real, pred))
    m = [metricas_rep(np.array([a for a, _ in v]), np.array([b for _, b in v])) for _, v in sorted(por_rep.items())]
    return {k: float(np.mean([x[k] for x in m])) for k in ('MAE', 'RMSE', 'sesgo')}, \
        len({i for (e, _, i), (_, _, f, _) in oof[cand].items()
             if e == esc and (sub == 'todas' or f == 'municipio') and (ids is None or i in ids)})


def auditar_controles(raiz, carpeta, oof, datos):
    resultado, peor, problemas = {}, 0.0, []
    manifiesto = json.loads((carpeta / 'manifest_controles.json').read_text(encoding='utf-8'))
    for control, info in manifiesto['controles'].items():
        for nombre, huella in info['archivos_sha256'].items():
            if sha(carpeta / nombre) != huella:
                problemas.append(f'{nombre} cambió después de generarse')
    HET = 't12_het_GP'
    # --- C6: parcelas extremas
    por = {}
    for (e, rep, i), (real, pred, _, _) in oof[HET].items():
        if e == 'A':
            por.setdefault(i, []).append((real, pred, oof[REF_MEDIA][(e, rep, i)][1]))
    g = {i: (np.mean([x[0] for x in v]), np.mean([x[1] for x in v]), np.mean([x[2] for x in v]))
         for i, v in por.items()}
    d = {i: abs(p - y) - abs(r - y) for i, (y, p, r) in g.items()}
    orden = sorted(d, key=lambda i: (d[i], i))
    n = 20
    esperado = [('mejora', k + 1, i) for k, i in enumerate(orden[:n])] + \
               [('empeora', k + 1, i) for k, i in enumerate(sorted(d, key=lambda i: (-d[i], i))[:n])]
    tabla = leer_csv(carpeta / 'parcelas_extremas_t12.csv')
    if [(t['grupo'], int(t['rango']), t['ID_POLIGONO']) for t in tabla] != esperado:
        problemas.append('C6: parcelas o rangos distintos de los recalculados')
    else:
        dif = max(max(cerca(d[t['ID_POLIGONO']], num(t['d_error_abs'])),
                      cerca(g[t['ID_POLIGONO']][1], num(t['prediccion_media'])),
                      cerca(g[t['ID_POLIGONO']][2], num(t['referencia_media']))) for t in tabla)
        peor = max(peor, dif)
    resultado['C6'] = dict(filas=len(tabla))
    # --- C2: observado y p
    t2 = leer_csv(carpeta / 'control_revuelto_t12.csv')
    comp = [c for c in leer_csv(carpeta / 'comparacion_emparejada_t12.csv') if c['aplica_promocion'] == 'True']
    obs = d_mae_parcela(oof, HET, REF_MEDIA, 'A', 'sin_respaldo')
    peor = max(peor, cerca(obs, num(comp[0]['dMAE'])))
    b = sum(num(t['dMAE_revuelto']) <= obs for t in t2)
    ok_p = all(int(t['b']) == b and int(t['n_permutaciones']) == len(t2) and
               cerca((b + 1) / (len(t2) + 1), num(t['p'])) < TOL_METRICA and
               cerca(obs, num(t['dMAE_observado'])) < TOL_METRICA for t in t2)
    if not ok_p:
        problemas.append('C2: observado, b o p distintos de los recalculados')
    semillas = [int(t['semilla']) for t in t2]
    if len(set(semillas)) != len(semillas):
        problemas.append('C2: semillas repetidas')
    resultado['C2'] = dict(permutaciones=len(t2), observado=obs, b=b, p=(b + 1) / (len(t2) + 1))
    # --- C3: la fracción 1.0 es la evaluación principal
    t3 = leer_csv(carpeta / 'curva_aprendizaje_t12.csv')
    for t in t3:
        if t['fraccion'] in ('1.0', '1') and t['semilla'] == 'completo':
            cand = t['procedimiento']
            m, _ = mae_rmse_sesgo(oof, cand, 'A', t['subconjunto'])
            dm = 0.0 if cand == REF_MEDIA else d_mae_parcela(oof, cand, REF_MEDIA, 'A', t['subconjunto'])
            peor = max(peor, cerca(m['MAE'], num(t['MAE'])), cerca(m['RMSE'], num(t['RMSE'])),
                       cerca(dm, num(t['dMAE_vs_referencia'])))
    resultado['C3'] = dict(filas=len(t3))
    # --- C4: corte por municipio y sensibilidad sin alerta
    municipio = {i: datos.fila[i]['municipio'] for i in datos.etiquetadas}
    alerta = {r['id_parcela']: r['alerta_contorno_t03_bis'] for r in leer_csv(Path(raiz) / 'registro/t07/calidad_parcelas.csv')}
    t4 = [t for t in leer_csv(carpeta / 'desglose_error_t12.csv') if t['desglose'] == 'municipio']
    for t in t4:
        ids = {i for i, m in municipio.items() if m == t['categoria']}
        m, n_par = mae_rmse_sesgo(oof, t['candidato'], t['escenario'], t['subconjunto'], ids)
        dm = 0.0 if t['candidato'] == REF_MEDIA else d_mae_parcela(oof, t['candidato'], REF_MEDIA, t['escenario'],
                                                                   t['subconjunto'], ids)
        if n_par != int(t['n_parcelas']):
            problemas.append(f'C4: n_parcelas de {t["categoria"]}')
        peor = max(peor, cerca(m['MAE'], num(t['MAE'])), cerca(m['RMSE'], num(t['RMSE'])),
                   cerca(m['sesgo'], num(t['sesgo'])), cerca(dm, num(t['dMAE_vs_referencia'])))
    t4b = leer_csv(carpeta / 'sensibilidad_sin_alerta_t12.csv')
    sin_alerta = {i for i in datos.etiquetadas if alerta.get(i) != 'si'}
    for t in t4b:
        m, n_par = mae_rmse_sesgo(oof, t['candidato'], t['escenario'], t['subconjunto'], sin_alerta)
        dm = 0.0 if t['candidato'] == REF_MEDIA else d_mae_parcela(oof, t['candidato'], REF_MEDIA, t['escenario'],
                                                                   t['subconjunto'], sin_alerta)
        if n_par != int(t['n_parcelas_sin_alerta']):
            problemas.append('C4: n_parcelas_sin_alerta')
        peor = max(peor, cerca(m['MAE'], num(t['MAE_sin_alerta'])), cerca(dm, num(t['dMAE_sin_alerta'])))
    resultado['C4'] = dict(filas_municipio=len(t4), filas_sin_alerta=len(t4b))
    resultado.update(aprobado=bool(not problemas and peor <= TOL_METRICA), dif_max=peor, tolerancia=TOL_METRICA,
                     problemas=problemas[:50])
    return resultado


# ------------------------------------------------------------------ orquestación
def compuertas(raiz, carpeta, verificar_huellas=True):
    manifiesto = json.loads((carpeta / 'manifest.json').read_text(encoding='utf-8'))
    exigir(manifiesto.get('schema') == 'manifest_t12_evaluacion_v1', 'Manifest de la evaluación principal inválido')
    if verificar_huellas:
        for nombre in PRINCIPALES:
            exigir(sha(carpeta / nombre) == manifiesto['salidas_sha256'][nombre], f'Salida modificada: {nombre}')
        for archivo, huella in manifiesto['entradas_sha256'].items():
            exigir(sha(Path(raiz) / archivo) == huella, f'Entrada modificada: {archivo}')
    exigir(sha(Path(raiz) / 'registro/t12/procedimiento_t12.json') == manifiesto['sha_diseno_t12'],
           'El diseño registrado no es el de la evaluación')
    return manifiesto


def auditar(raiz=RAIZ, salida=CARPETA, controles=False, esperados=N_CONTEXTOS_ESPERADOS, verificar_huellas=True):
    raiz = Path(raiz).resolve()
    carpeta = (raiz / CARPETA)
    destino = Path(salida)
    destino = (destino if destino.is_absolute() else raiz / destino).resolve()
    permitidas = [raiz / 'registro/t12', raiz / 'reports']
    exigir(any(destino == p or p in destino.parents for p in permitidas),
           'La salida debe estar en registro/t12 o en una subcarpeta de reports/')
    exigir(not (destino / SALIDA).exists(), f'Conservar evidencia: ya existe {SALIDA}')
    manifiesto = compuertas(raiz, carpeta, verificar_huellas)
    diseno = json.loads((raiz / 'registro/t12/procedimiento_t12.json').read_text(encoding='utf-8'))
    datos = Datos(raiz)
    oof = cargar_oof(raiz, carpeta)
    contextos = sorted({(e, r, v[3]) for (e, r, _), v in oof['t12_het_GP'].items()})
    exigir(len(contextos) == esperados, f'Se esperaban {esperados} contextos y hay {len(contextos)}')
    integridad = integridad_oof(datos, oof, contextos)
    het, detalle = auditar_het(raiz, carpeta, datos, diseno, contextos, oof)
    metricas = auditar_metricas(carpeta, oof)
    comparaciones = auditar_comparaciones(carpeta, oof, datos, diseno)
    informe = dict(schema='auditoria_t12_v1', version=VERSION, sha_diseno_t12=manifiesto['sha_diseno_t12'],
                   independencia='NumPy y csv; sin importar el código de producción. Comparte solo la semilla y '
                                 'el sorteo del remuestreo de celdas y las particiones internas de scikit-learn.',
                   integridad_oof=integridad, ajustes_het=het, metricas=metricas, comparaciones=comparaciones)
    if controles:
        informe['controles'] = auditar_controles(raiz, carpeta, oof, datos)
    informe['aprobado'] = bool(all(v['aprobado'] for v in informe.values() if isinstance(v, dict) and 'aprobado' in v))
    import sklearn
    informe['entorno'] = dict(sistema=platform.system(), python=platform.python_version(), numpy=np.__version__,
                              sklearn=sklearn.__version__)
    informe['salidas_auditadas_sha256'] = {n: sha(carpeta / n) for n in PRINCIPALES}
    informe['auditor_sha256'] = sha(Path(__file__))
    destino.mkdir(parents=True, exist_ok=True)
    (destino / SALIDA).write_text(json.dumps(informe, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return informe, detalle, destino


def resumen(informe):
    f = lambda v: f'{v:.2e}'
    h, m, c = informe['ajustes_het'], informe['metricas'], informe['comparaciones']
    lineas = [f'Integridad de las predicciones : {"OK" if informe["integridad_oof"]["aprobado"] else "FALLA"}',
              f'Ajustes het ({h["contextos"]} contextos x {len(h["procedimientos"])} procedimientos): '
              f'{"OK" if h["aprobado"] else "FALLA"}  dif. máx. predicción {f(h["dif_max_prediccion"])}, '
              f'MAE interno {f(h["dif_max_MAE_interno"])}',
              f'Métricas ({m["filas_comparadas"]} filas)       : {"OK" if m["aprobado"] else "FALLA"}  '
              f'dif. máx. {f(m["dif_max"])}',
              f'Comparaciones ({c["comparaciones"]} filas, IC95)  : {"OK" if c["aprobado"] else "FALLA"}  '
              f'dif. máx. {f(c["dif_max"])}']
    if 'controles' in informe:
        k = informe['controles']
        lineas.append(f'Controles C2-C6                 : {"OK" if k["aprobado"] else "FALLA"}  '
                      f'dif. máx. {f(k["dif_max"])}')
    lineas.append(f'AUDITORÍA {"APROBADA" if informe["aprobado"] else "NO APROBADA"}')
    return '\n'.join(lineas)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--raiz', type=Path, default=RAIZ)
    p.add_argument('--salida', type=Path, default=Path(CARPETA), help='registro/t12 o una subcarpeta de reports/')
    p.add_argument('--controles', action='store_true', help='audita también C2 a C6')
    a = p.parse_args(argv)
    informe, _, destino = auditar(a.raiz, a.salida, a.controles)
    print(resumen(informe))
    print(f'Guardado en {destino / SALIDA}')
    return 0 if informe['aprobado'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
