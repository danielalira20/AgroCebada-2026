"""T12 paso 4: evaluación principal de los 8 procedimientos registrados.

Corre los 50 contextos externos de T03 (A y B, 5 repeticiones, 5 particiones), con la selección interna
de cada familia, y escribe las tablas del registro. Reutiliza sin cambios los validadores y estadísticos
comunes de T15 (`validar_oof`, `resumen`, `comparar`) y los modelos de `t12_heterogeneidad`.

Antes de crear cualquier archivo exige, y se detiene si falta alguna:
  - el diseño registrado sin cambios y las comprobaciones del paso 3 aprobadas con el mismo código y las
    mismas entradas;
  - que la persona declare con --confirmo-barreras que las barreras externas del registro están cerradas;
  - que ninguna salida exista ya (no se sobrescribe evidencia).
Las tablas se calculan completas en memoria y sólo entonces se escriben.
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
from scripts import evaluacion_comun_reportes as comun
from scripts import t12_heterogeneidad as t12
from scripts.evaluacion_comun_contrato import exigir, leer_csv, sha, validar_oof

VERSION = 't12-evaluacion-v1'
RAIZ = t12.RAIZ
REFERENCIA = 'media_mun__resp_grupo'
REFERENCIA_MEDIANA = 'mediana_mun__resp_grupo'
PROMOVIBLE = 't12_het_GP'
N_ETIQUETADAS, N_RESERVADAS = 138, 59
CONTEXTOS = t12.CONTEXTOS
ARCHIVOS = ('predicciones_oof_t12.csv', 'seleccion_interna_t12.csv', 'metricas_t12.csv',
            'comparacion_emparejada_t12.csv', 'predicciones_59_t12.csv', 'manifest.json')
COLUMNAS_OOF = ['ID_POLIGONO', 'repeticion', 'particion', 'escenario', 'real', 'prediccion',
                'candidato', 'version', 'fuente']
ARCHIVOS_T03 = {REFERENCIA: 'registro/t03/predicciones_oof_referencias_media_mun__resp_grupo.csv',
                REFERENCIA_MEDIANA: 'registro/t03/predicciones_oof_referencias_mediana_mun__resp_grupo.csv'}
CODIGO = t12.CODIGO + ('scripts/t12_evaluar.py', 'scripts/evaluacion_comun_reportes.py')


# ------------------------------------------------------------------ compuertas
def compuertas(raiz, confirmo_barreras):
    """Se detiene antes de tocar etiquetas si algo registrado no coincide."""
    raiz = Path(raiz)
    cfg = t12.cargar_diseno(raiz)
    ruta = raiz / t12.SALIDA_COMPROBACIONES
    exigir(ruta.exists(), 'Faltan las comprobaciones del paso 3 (registro/t12/comprobaciones.json)')
    c = json.loads(ruta.read_text(encoding='utf-8'))
    exigir(c.get('schema') == 'comprobaciones_t12_v1' and c.get('resultado') == 'aprobado',
           'Las comprobaciones del paso 3 no están aprobadas')
    exigir(c.get('sha_diseno_t12') == t12.DISENO_SHA, 'Las comprobaciones son de otro diseño')
    for archivo, huella in c['codigo_sha256'].items():
        exigir(sha(raiz / archivo) == huella, f'El código cambió después de las comprobaciones: {archivo}')
    for archivo, huella in c['fuentes_sha256'].items():
        exigir(sha(raiz / archivo) == huella, f'Una entrada cambió después de las comprobaciones: {archivo}')
    exigir(confirmo_barreras is True,
           'Falta --confirmo-barreras: confirma que Dani y D026, Migue y los commits previos están cerrados '
           '(barreras_antes_de_ejecutar del registro)')
    return cfg, c


def preparar_salida(salida, raiz):
    """La carpeta puede existir (registro/t12), pero ningún archivo de salida."""
    raiz, salida = Path(raiz).resolve(), Path(salida)
    salida = (salida if salida.is_absolute() else raiz / salida).resolve()
    permitidas = [raiz / 'registro/t12', raiz / 'reports']
    exigir(any(salida == p or p in salida.parents for p in permitidas),
           'La salida debe estar en registro/t12 o en una subcarpeta de reports/')
    ocupados = [a for a in ARCHIVOS if (salida / a).exists()]
    exigir(not ocupados, f'Conservar evidencia: ya existen {ocupados}')
    return salida


# ------------------------------------------------------------------ un contexto externo
def evaluar_contexto(entradas, procedimientos, esc, rep, fold):
    """Ajusta los procedimientos con el entrenamiento externo y predice sólo su evaluación."""
    tr, y, te = v3.preparar_contexto(entradas, esc, rep, fold)
    exigir(not set(tr.index) & set(te.index), 'Entrenamiento y evaluación comparten parcelas')
    oof, seleccion = [], []
    for p in procedimientos:
        r = t12.ajustar_y_predecir(tr, y, te, p, esc)
        det, sel = r['detalle'], r['seleccion']
        exigir(list(det.index) == list(te.index) and np.isfinite(det.prediccion).all(), 'Predicción no válida')
        for pid, pred, fuente in zip(te.index, det.prediccion.to_numpy(), det.fuente.to_numpy()):
            real = entradas['contextos'][(esc, rep, pid)]['real']
            oof.append(dict(ID_POLIGONO=pid, repeticion=rep, particion=fold, escenario=esc, real=real,
                            prediccion=float(pred), candidato=p['candidato'], version=t12.VERSION,
                            fuente=str(fuente)))
        elegida = sel['elegida']['nombre']
        for q in sel['puntuaciones']:
            seleccion.append(dict(
                candidato=p['candidato'], escenario=esc, repeticion=rep, particion=fold, opcion=q['nombre'],
                ventana=q['ventana'], lambda_reg=q['lambda_reg'], kappa=q['kappa'], n_estimators=q['n_estimators'],
                referencia_sola=q['referencia_sola'], MAE_interno=q['MAE'], MAE_todas_internas=q['MAE_todas'],
                n_elegibles=q['n_elegibles'], n_validacion=q['n_validacion'], n_ajustes=q['n_ajustes'],
                elegida=q['nombre'] == elegida, internas=sel['internas'],
                n_excluidas_respaldo=sel['n_excluidas_respaldo'],
                n_validacion_referencia_una_etiqueta=sel['n_validacion_referencia_una_etiqueta'],
                n_municipios_con_pendiente_propia=len(sel['grupos_pendiente']),
                municipios_con_pendiente_propia='|'.join(sel['grupos_pendiente']),
                n_entrenamiento=len(tr)))
    return dict(oof=oof, seleccion=seleccion)


_ESTADO = {}


def _iniciar_trabajador(raiz, procedimientos):
    _ESTADO['limite'] = threadpool_limits(limits=1)
    _ESTADO['entradas'] = v3.cargar_entradas(raiz)
    _ESTADO['procedimientos'] = procedimientos


def _trabajar(contexto):
    return evaluar_contexto(_ESTADO['entradas'], _ESTADO['procedimientos'], *contexto)


def evaluar_todos(entradas, procedimientos, contextos=CONTEXTOS, procesos=1, raiz=None, avance=False):
    """Los contextos son independientes: el resultado no depende de cuántos procesos se usen."""
    if procesos == 1:
        resultados = []
        with threadpool_limits(limits=1):
            for i, c in enumerate(contextos, 1):
                resultados.append(evaluar_contexto(entradas, procedimientos, *c))
                if avance:
                    print(f'{i}/{len(contextos)} {c[0]}/{c[1]}/{c[2]}', flush=True)
    else:
        exigir(raiz is not None and procesos > 1, 'Varios procesos requieren la raíz del proyecto')
        with ProcessPoolExecutor(max_workers=procesos, initializer=_iniciar_trabajador,
                                 initargs=(str(raiz), procedimientos)) as ex:
            resultados = list(ex.map(_trabajar, contextos))
            if avance:
                print(f'{len(contextos)}/{len(contextos)} contextos', flush=True)
    orden = {p['candidato']: i for i, p in enumerate(procedimientos)}
    oof = sorted((f for r in resultados for f in r['oof']),
                 key=lambda f: (orden[f['candidato']], f['escenario'], f['repeticion'], f['ID_POLIGONO']))
    sel = sorted((f for r in resultados for f in r['seleccion']),
                 key=lambda f: (orden[f['candidato']], f['escenario'], f['repeticion'], f['particion'],
                                not f['referencia_sola'], f['opcion']))
    return oof, sel


# ------------------------------------------------------------------ las 59 (exploratorias)
def x_poblaciones(entradas):
    """X de las etiquetadas (con su y) y X de las reservadas; el rendimiento de las reservadas se descarta.

    Igual que `t12_heterogeneidad.entradas_x` pero sin fijar 138 y 59 (esas cifras se exigen en `ejecutar`),
    para poder probarlo con poblaciones inventadas. Una prueba compara ambas con los datos reales.
    """
    tabla = pd.DataFrame(list(entradas['tabla'].values())).set_index('id_parcela')
    conocidos, reservados = sorted(entradas['conocidos']), sorted(entradas['reservados'])
    exigir(conocidos and reservados and not set(conocidos) & set(reservados), 'Poblaciones inválidas')
    y = pd.to_numeric(tabla.loc[conocidos, 'rendimiento_t_ha'], errors='raise')
    tabla = tabla.drop(columns=['rendimiento_t_ha'])
    roles = entradas['roles']['columnas_por_funcion']
    for col in [c for c in roles['predictor_candidato'] if c != 'municipio'] + roles['calidad'] + ['area_ha_origen']:
        tabla[col] = pd.to_numeric(tabla[col], errors='raise')
    return tabla.loc[conocidos].copy(), y, tabla.loc[reservados].copy()


def ajustar_59(entradas, procedimientos):
    """Cada procedimiento con las 138 etiquetadas (selección interna A). No son la entrega T18."""
    X138, y, X59 = x_poblaciones(entradas)
    filas = []
    with threadpool_limits(limits=1):
        for p in procedimientos:
            r = t12.ajustar_y_predecir(X138, y, X59, p, 'A')
            det = r['detalle']
            exigir(len(det) == len(X59) and np.isfinite(det.prediccion).all(), 'Predicción de las reservadas no válida')
            for pid in X59.index:
                filas.append(dict(candidato=p['candidato'], ID_POLIGONO=pid, municipio=X59.loc[pid, 'municipio'],
                                  prediccion=float(det.prediccion.loc[pid]), referencia=float(det.referencia.loc[pid]),
                                  correccion=float(det.correccion.loc[pid]), fuente=str(det.fuente.loc[pid]),
                                  opcion_elegida=r['seleccion']['elegida']['nombre'], escenario_seleccion='A',
                                  n_municipios_con_pendiente_propia=len(r['seleccion']['grupos_pendiente']),
                                  version=t12.VERSION, exploratoria=True))
    return filas


# ------------------------------------------------------------------ métricas y comparaciones
def cargar_referencias(raiz):
    """Predicciones de referencia ya validadas por T03/T15 (media y mediana)."""
    filas = []
    for nombre, ruta in ARCHIVOS_T03.items():
        _, rows = leer_csv(Path(raiz) / ruta)
        exigir(all(r['candidato'] == nombre for r in rows), 'Archivo de referencia con otro candidato')
        filas.extend(rows)
    return filas


def tabla_metricas(filas, contextos):
    filas_m = []
    for r in comun.resumen(filas, contextos):
        base = dict(candidato=r['candidato'], escenario=r['escenario'], subconjunto=r['subconjunto'])
        for i, m in enumerate(r['metricas_por_repeticion'], 1):
            filas_m.append(dict(base, repeticion=str(i), n=m['n'], MAE=m['MAE'], RMSE=m['RMSE'],
                                sesgo=m['sesgo'], R2=m['R2']))
        filas_m.append(dict(base, repeticion='promedio', n=r['n_media'], MAE=r['MAE'], RMSE=r['RMSE'],
                            sesgo=r['sesgo'], R2=r['R2']))
    return pd.DataFrame(filas_m)


def pares_de_comparacion(cfg):
    """(candidato, base, tipo). Todas frente a la referencia de su familia; C1 frente a su control."""
    pares = []
    for p in cfg['procedimientos']:
        c = p['candidato']
        if p['referencia'] == REFERENCIA_MEDIANA:
            pares += [(c, REFERENCIA_MEDIANA, 'C8_misma_referencia'), (c, REFERENCIA, 'frente_a_referencia')]
        else:
            pares.append((c, REFERENCIA, 'frente_a_referencia'))
    pares += [(a, b, 'C1_ablacion') for a, b in cfg['controles']['C1_ablacion']['pares']]
    exigir(len(pares) == len(set(pares)), 'Comparaciones duplicadas')
    return pares


def tabla_comparaciones(filas, contextos, cfg):
    salida = []
    for candidato, base, tipo in pares_de_comparacion(cfg):
        for esc in ('A', 'B'):
            for sub in ('todas', 'sin_respaldo'):
                r = comun.comparar(filas, contextos, candidato, base, esc, sub)
                d = {k: v for k, v in r.items() if k not in ('dMAE_por_repeticion', 'IC95_celdas_MAE',
                                                              'IC95_celdas_RMSE', 'interpretacion',
                                                              'elegible_para_promocion_principal')}
                d = dict(tipo=tipo, **d)
                for i, v in enumerate(r['dMAE_por_repeticion'], 1):
                    d[f'dMAE_rep{i}'] = v
                d['IC95_MAE_inf'], d['IC95_MAE_sup'] = r['IC95_celdas_MAE']
                d['IC95_RMSE_inf'], d['IC95_RMSE_sup'] = r['IC95_celdas_RMSE']
                aplica = (candidato == PROMOVIBLE and base == REFERENCIA and esc == 'A' and sub == 'sin_respaldo')
                d['aplica_promocion'] = bool(aplica)
                d['estado_promocion'] = (('cumple_T03_pendiente_C2_revuelto' if r['cumple_regla_T03']
                                          else 'no_cumple_T03') if aplica else 'no_aplica')
                salida.append(d)
    return pd.DataFrame(salida)


def construir_tablas(entradas, cfg, procedimientos, oof, seleccion, filas_referencia):
    filas = list(filas_referencia) + oof
    validar_oof(filas, entradas['contextos'])
    exigir({p['candidato'] for p in procedimientos} <= {r['candidato'] for r in filas}, 'Faltan candidatos')
    return dict(
        predicciones_oof=pd.DataFrame(oof, columns=COLUMNAS_OOF),
        seleccion_interna=pd.DataFrame(seleccion),
        metricas=tabla_metricas(filas, entradas['contextos']),
        comparacion=tabla_comparaciones(filas, entradas['contextos'], cfg))


# ------------------------------------------------------------------ escritura
def escribir(salida, tablas, filas_59, manifest_base):
    """Todo está validado: ahora se crean los archivos y, al final, el manifest con sus huellas."""
    salida.mkdir(parents=True, exist_ok=True)
    nombres = {'predicciones_oof': 'predicciones_oof_t12.csv', 'seleccion_interna': 'seleccion_interna_t12.csv',
               'metricas': 'metricas_t12.csv', 'comparacion': 'comparacion_emparejada_t12.csv'}
    for clave, nombre in nombres.items():
        tablas[clave].to_csv(salida / nombre, index=False, float_format='%.17g')
    pd.DataFrame(filas_59).to_csv(salida / 'predicciones_59_t12.csv', index=False, float_format='%.17g')
    manifest = dict(manifest_base, salidas_sha256={n: sha(salida / n) for n in ARCHIVOS if n != 'manifest.json'})
    (salida / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n',
                                          encoding='utf-8')
    return manifest


def ejecutar(salida, raiz=RAIZ, confirmo_barreras=False, procesos=1):
    import sklearn
    raiz = Path(raiz)
    cfg, comprobaciones = compuertas(raiz, confirmo_barreras)
    destino = preparar_salida(salida, raiz)
    antes = {f: sha(raiz / f) for f in t12.FUENTES_ENTRADA + tuple(ARCHIVOS_T03.values())}
    entradas = v3.cargar_entradas(raiz)
    exigir((len(entradas['conocidos']), len(entradas['reservados'])) == (N_ETIQUETADAS, N_RESERVADAS),
           'Se esperan 138 etiquetadas y 59 reservadas')
    procedimientos = cfg['procedimientos']
    exigir(len(procedimientos) == 8, 'El registro declara 8 procedimientos')
    oof, seleccion = evaluar_todos(entradas, procedimientos, CONTEXTOS, procesos, raiz, avance=True)
    exigir(len(oof) == 8 * len(entradas['contextos']), 'OOF incompleta')
    tablas = construir_tablas(entradas, cfg, procedimientos, oof, seleccion, cargar_referencias(raiz))
    filas_59 = ajustar_59(entradas, procedimientos)
    despues = {f: sha(raiz / f) for f in antes}
    exigir(antes == despues, 'Una entrada cambió durante la corrida')
    manifest = dict(
        schema='manifest_t12_evaluacion_v1', version=VERSION, version_modelos=t12.VERSION,
        sha_diseno_t12=t12.DISENO_SHA, sha_comprobaciones=sha(raiz / t12.SALIDA_COMPROBACIONES),
        contextos_externos=len(CONTEXTOS), procedimientos=[p['candidato'] for p in procedimientos],
        filas_oof=len(oof), ajustes_internos_y_externos_por_contexto='ver seleccion_interna_t12.csv',
        ajustes_finales_59=len(procedimientos), predicciones_59_exploratorias=True,
        barreras_confirmadas_por_la_persona=True, MAE_externo_calculado=True,
        promocion='t12_het_GP sólo se promueve si además pasa C2 (revuelto, paso 5)',
        procesos=procesos, entorno=dict(sistema=platform.system(), python=platform.python_version(),
                                       numpy=np.__version__, pandas=pd.__version__, sklearn=sklearn.__version__),
        entradas_sha256=antes, codigo_sha256={f: sha(raiz / f) for f in CODIGO})
    escribir(destino, tablas, filas_59, manifest)
    return destino, tablas


def resumen_consola(tablas):
    c = tablas['comparacion']
    c = c[(c.tipo == 'frente_a_referencia') & (c.escenario == 'A') & (c.subconjunto == 'sin_respaldo')]
    cols = ['candidato', 'dMAE', 'IC95_MAE_inf', 'IC95_MAE_sup', 'repeticiones_mejoran_MAE', 'dRMSE']
    return c[cols].to_string(index=False, float_format=lambda v: f'{v:.4f}')


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--raiz', type=Path, default=RAIZ)
    p.add_argument('--salida', type=Path, required=True,
                   help='registro/t12 (oficial) o una subcarpeta de reports/ (reproducción); relativa a la raíz')
    p.add_argument('--confirmo-barreras', action='store_true', dest='confirmo')
    p.add_argument('--procesos', type=int, default=1, help='contextos en paralelo; no cambia el resultado')
    a = p.parse_args(argv)
    exigir(a.procesos >= 1, '--procesos debe ser al menos 1')
    destino, tablas = ejecutar(a.salida, a.raiz, a.confirmo, a.procesos)
    print(f'Guardado en {destino}')
    print(resumen_consola(tablas))


if __name__ == '__main__':
    main()
