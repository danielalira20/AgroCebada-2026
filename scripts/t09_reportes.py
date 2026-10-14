"""T09: métricas emparejadas del diseño v1, sin ajustar ni elegir un ganador.

La unidad de ΔMAE es la parcela, tras promediar sus repeticiones elegibles.
Los intervalos remuestrean bloques del centroide y describen desempeño conjunto;
no son intervalos de predicción individuales ni pruebas causales.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

PROCEDIMIENTOS = ('T', 'CL', 'TC', 'R')
VARIANTES = ('seleccionada', 'abr_oct', 'jun_oct')
PARES = (('TC', 'T'), ('CL', 'T'), ('TC', 'CL'), ('R', 'T'), ('R', 'TC'))
PARES_FIJOS = (('TC', 'T'), ('TC', 'CL'))
CLAVE = ['id_parcela', 'repeticion']
GRUPO = ['escenario', 'variante', 'procedimiento', 'poblacion']
METRICAS = ('MAE', 'RMSE', 'sesgo', 'R2')
CALIDAD = ('contorno_categoria', 'contorno_angosta_o_muy_pequena',
           'alerta_contorno_t03_bis', 'escalon_etiqueta_municipio',
           'vecina_etiquetada_menos_20m')
REQUERIDAS = ('escenario', 'procedimiento', 'variante', 'id_parcela',
              'repeticion', 'particion', 'municipio', 'cultivo_origen',
              'celda_chirps', 'real', 'prediccion', 'referencia', 'correccion',
              'fuente', 'fuente_referencia', 'sin_respaldo', 'ventana',
              'lambda_reg', 'n_entrenamiento')


def metricas(y, prediccion):
    """Métricas con signo predicción-real y R² explícitamente indefinido."""
    y, p = np.asarray(y, dtype=float), np.asarray(prediccion, dtype=float)
    if y.ndim != 1 or p.shape != y.shape or not np.isfinite(y).all() or not np.isfinite(p).all():
        raise ValueError('Etiquetas/predicciones incompatibles o no finitas')
    if len(y) == 0:
        return dict(MAE=np.nan, RMSE=np.nan, sesgo=np.nan, R2=np.nan,
                    estado_R2='sin_casos')
    e = p - y
    ss = np.square(y - y.mean()).sum()
    estado = 'n_menor_2' if len(y) < 2 else ('y_constante' if np.all(y == y[0]) else 'definido')
    r2 = np.nan if estado != 'definido' else 1 - np.square(e).sum() / ss
    return dict(MAE=float(np.abs(e).mean()), RMSE=float(np.sqrt(np.square(e).mean())),
                sesgo=float(e.mean()), R2=float(r2), estado_R2=estado)


def _config(config):
    ev = config['evaluacion']
    if (ev['primaria'] != 'MAE' or not ev['por_repeticion_luego_resumen'] or
            tuple(ev['contraste_principal']) != PARES[0] or
            tuple(tuple(x) for x in ev['contrastes_secundarios']) != PARES[1:]):
        raise ValueError('El reporte sólo implementa contrastes del diseño T09 v1')
    b = ev['bootstrap']
    if b['replicas'] != 5000 or b['semilla'] != 20261006 or b['percentiles'] != [2.5, 97.5]:
        raise ValueError('Bootstrap distinto del diseño congelado')
    p = ev['promocion_A_sin_respaldo']
    if p != dict(dMAE_max=-0.01, limite_IC95_celdas_superior_menor_0=True,
                 repeticiones_mejora_min=4, dRMSE_max=0.01):
        raise ValueError('Regla de promoción distinta del diseño congelado')
    return ev


def _validar(oof, calidad):
    if not isinstance(oof, pd.DataFrame) or oof.empty or oof.columns.duplicated().any():
        raise ValueError('OOF vacío/incompatible')
    if set(REQUERIDAS) - set(oof):
        raise ValueError(f'Faltan columnas OOF: {sorted(set(REQUERIDAS)-set(oof))}')
    x = oof.copy()
    if x.duplicated(['escenario', 'procedimiento', 'variante'] + CLAVE).any():
        raise ValueError('Predicción OOF duplicada por procedimiento/variante/ID/repetición')
    for c in ('escenario', 'procedimiento', 'variante', 'id_parcela', 'municipio',
              'cultivo_origen', 'celda_chirps', 'fuente', 'fuente_referencia'):
        if not x[c].map(lambda v: isinstance(v, str) and bool(v.strip())).all():
            raise ValueError(f'Identificador/categoría vacía: {c}')
    if not set(x.escenario) <= {'A', 'B', 'C'} or set(x.procedimiento) != set(PROCEDIMIENTOS):
        raise ValueError('Escenario/procedimiento desconocido o incompleto')
    if not set(x.variante) <= set(VARIANTES) or not x.loc[x.procedimiento == 'T', 'variante'].eq('seleccionada').all():
        raise ValueError('Variantes incompatibles; la referencia T sólo se almacena una vez')
    for c in ('real', 'prediccion', 'referencia', 'correccion', 'n_entrenamiento'):
        if not pd.api.types.is_numeric_dtype(x[c]) or pd.api.types.is_bool_dtype(x[c]) or not np.isfinite(x[c]).all():
            raise ValueError(f'Columna OOF no numérica/finita: {c}')
    if not x.n_entrenamiento.gt(0).all() or not x.n_entrenamiento.eq(np.floor(x.n_entrenamiento)).all():
        raise ValueError('El número de filas de entrenamiento debe ser entero positivo')
    for c in ('repeticion', 'particion'):
        if not pd.api.types.is_integer_dtype(x[c]) or pd.api.types.is_bool_dtype(x[c]):
            raise ValueError(f'Clave de contexto no entera: {c}')
    if not np.allclose(x.prediccion, x.referencia + x.correccion, atol=1e-9, rtol=1e-12):
        raise ValueError('Predicción no coincide con referencia más corrección')
    if not pd.api.types.is_bool_dtype(x.sin_respaldo) or x.sin_respaldo.isna().any():
        raise ValueError('La máscara común requiere booleanos reales')
    if not x.sin_respaldo.eq(x.fuente_referencia.eq('municipio')).all():
        raise ValueError('La máscara común no corresponde a la referencia T08')
    for c in ('real', 'municipio', 'cultivo_origen', 'celda_chirps'):
        if x.groupby('id_parcela')[c].nunique(dropna=False).gt(1).any():
            raise ValueError(f'Metadato/etiqueta cambia entre predicciones: {c}')
    for esc, s in x.groupby('escenario', sort=True):
        base = s[s.procedimiento == 'T'].set_index(CLAVE).sort_index()
        esperadas = [1] if esc == 'C' else [1, 2, 3, 4, 5]
        if sorted(base.index.get_level_values('repeticion').unique()) != esperadas:
            raise ValueError(f'Repeticiones incompletas en {esc}')
        if not base.fuente.eq(base.fuente_referencia).all():
            raise ValueError('Fuente de T no coincide con su referencia')
        for _, g in s[s.procedimiento != 'T'].groupby(['procedimiento', 'variante']):
            c = g.set_index(CLAVE).sort_index()
            if not c.index.equals(base.index):
                raise ValueError('Candidato/variante no cubre las mismas claves que T')
            for col in ('real', 'particion', 'sin_respaldo', 'fuente_referencia', 'n_entrenamiento'):
                if not c[col].equals(base[col]):
                    raise ValueError(f'Candidato altera contexto/máscara común: {col}')
        if esc == 'C' and base.sin_respaldo.any():
            raise ValueError('C excluye el municipio; no tiene población sin_respaldo')
    if not isinstance(calidad, pd.DataFrame) or 'id_parcela' not in calidad or set(CALIDAD) - set(calidad):
        raise ValueError('Tabla de calidad T07 incompleta')
    q = calidad[['id_parcela', *CALIDAD]].copy()
    if q.id_parcela.isna().any() or q.id_parcela.duplicated().any():
        raise ValueError('Claves de calidad duplicadas/vacías')
    if set(x.id_parcela) - set(q.id_parcela):
        raise ValueError('Calidad no cubre todas las parcelas evaluadas')
    if not q.contorno_categoria.isin(['A', 'B', 'C']).all():
        raise ValueError('Categoría de contorno desconocida')
    for c in ('contorno_angosta_o_muy_pequena', 'alerta_contorno_t03_bis', 'vecina_etiquetada_menos_20m'):
        if not q[c].isin(['si', 'no']).all():
            raise ValueError(f'Bandera de calidad incompatible: {c}')
    esperada = q.contorno_categoria.isin(['B', 'C']) | q.contorno_angosta_o_muy_pequena.eq('si')
    if not q.alerta_contorno_t03_bis.eq(esperada.map({True: 'si', False: 'no'})).all():
        raise ValueError('Alerta de contorno inconsistente')
    x = x.merge(q, on='id_parcela', how='left', validate='many_to_one')
    x['contorno'] = np.where(x.contorno_categoria.eq('A'), 'A', 'B/C')
    x['escalon_etiqueta'] = x.escalon_etiqueta_municipio.fillna('no_identificable').map(str)
    return x


def _expandir_t(x):
    # Los duplicados existen sólo dentro del cálculo de reportes de ventana fija.
    base = x[x.procedimiento == 'T']
    disponibles = sorted(set(x.variante) - {'seleccionada'})
    extras = [base.assign(variante=v) for v in disponibles]
    return pd.concat([x, *extras], ignore_index=True)


def _poblaciones(x):
    for esc, s in x.groupby('escenario', sort=True):
        yield esc, 'todas', s
        if esc != 'C':
            yield esc, 'sin_respaldo', s[s.sin_respaldo]


def _por_repeticion(x, sensibilidad='principal', desglose=None):
    filas = []
    for esc, pob, s in _poblaciones(x):
        claves = ['variante', 'procedimiento', 'repeticion'] + ([desglose] if desglose else [])
        for key, g in s.groupby(claves, sort=True, dropna=False):
            v, proc, rep = key[:3]
            f = dict(escenario=esc, variante=v, procedimiento=proc, poblacion=pob,
                     repeticion=rep, n_predicciones=len(g), n_parcelas=g.id_parcela.nunique(),
                     sensibilidad=sensibilidad, **metricas(g.real, g.prediccion))
            if desglose:
                f.update(desglose=desglose, categoria=str(key[3]))
            universo = s[s.variante.eq(v) & s.procedimiento.eq(proc)]
            if desglose:
                universo = universo[universo[desglose].eq(key[3])]
            f['n_parcelas_union_reps'] = universo.id_parcela.nunique()
            filas.append(f)
    return pd.DataFrame(filas)


def _resumir(rep):
    claves = GRUPO + ['sensibilidad'] + (['desglose', 'categoria'] if 'desglose' in rep else [])
    filas = []
    for key, g in rep.groupby(claves, sort=True, dropna=False):
        f = dict(zip(claves, key))
        for m in METRICAS:
            f[m] = float(g[m].mean())
            f[f'{m}_sd_rep'] = float(g[m].std(ddof=0))
        f.update(n_repeticiones=len(g), n_predicciones=int(g.n_predicciones.sum()),
                 n_parcelas=int(g.n_parcelas_union_reps.max()),
                 n_parcelas_min_rep=int(g.n_parcelas.min()),
                 n_R2_definidas=int(g.estado_R2.eq('definido').sum()),
                 estado_R2=('definido' if g.estado_R2.eq('definido').all() else
                            'parcialmente_indefinido' if g.estado_R2.eq('definido').any() else 'indefinido'),
                 poco_informativo=bool(g.n_parcelas_union_reps.max() < 5))
        filas.append(f)
    return pd.DataFrame(filas)


def _bootstrap(d_parcela, celdas, b):
    orden = d_parcela.sort_index()
    v = orden.to_numpy(dtype=float)
    rng = np.random.RandomState(b['semilla'])
    bp = v[rng.randint(0, len(v), (b['replicas'], len(v)))].mean(axis=1)
    g = pd.DataFrame({'d': orden, 'celda': celdas.reindex(orden.index)}).groupby('celda', sort=True).d
    suma, n = g.sum().to_numpy(), g.size().to_numpy()
    rng = np.random.RandomState(b['semilla'])
    k = rng.randint(0, len(suma), (b['replicas'], len(suma)))
    bc = suma[k].sum(axis=1) / n[k].sum(axis=1)
    lp, hp = np.percentile(bp, b['percentiles'])
    lc, hc = np.percentile(bc, b['percentiles'])
    return dict(IC95_celdas_inf=float(lc), IC95_celdas_sup=float(hc),
                IC95_parcelas_inf=float(lp), IC95_parcelas_sup=float(hp), n_celdas=len(suma))


def _comparaciones(x, ev):
    filas, diferencias = [], []
    for esc, pob, s in _poblaciones(x):
        for variante, z in s.groupby('variante', sort=True):
            for candidato, frente_a in (PARES if variante == 'seleccionada' else PARES_FIJOS):
                a = z[z.procedimiento == candidato].set_index(CLAVE).sort_index()
                base = z[z.procedimiento == frente_a].set_index(CLAVE).sort_index()
                if a.empty and base.empty:
                    continue
                if a.empty or not a.index.equals(base.index):
                    raise ValueError('Contraste no emparejado')
                dae = (a.prediccion-a.real).abs() - (base.prediccion-base.real).abs()
                d_rep = dae.groupby(level='repeticion').mean()
                d_parc = dae.groupby(level='id_parcela').mean()
                n_rep = dae.groupby(level='id_parcela').size()
                celdas = a.reset_index().drop_duplicates('id_parcela').set_index('id_parcela').celda_chirps
                bs = _bootstrap(d_parc, celdas, ev['bootstrap'])
                drmse = []
                for r in d_rep.index:
                    aa, bb = a.xs(r, level='repeticion'), base.xs(r, level='repeticion')
                    drmse.append(metricas(aa.real, aa.prediccion)['RMSE']-metricas(bb.real, bb.prediccion)['RMSE'])
                condiciones = dict(condicion_dMAE=bool(d_parc.mean() <= -0.01),
                                   condicion_IC95=bool(bs['IC95_celdas_sup'] < 0),
                                   condicion_repeticiones=bool((d_rep < 0).sum() >= 4),
                                   condicion_dRMSE=bool(np.mean(drmse) <= 0.01))
                aplica = esc == 'A' and pob == 'sin_respaldo' and variante == 'seleccionada' and frente_a == 'T'
                f = dict(escenario=esc, variante=variante, poblacion=pob, candidato=candidato,
                         frente_a=frente_a, contraste=('principal' if (candidato, frente_a) == PARES[0] else 'secundario'),
                         n_predicciones=len(a), n_parcelas=len(d_parc), n_repeticiones=len(d_rep),
                         dMAE=float(d_parc.mean()), dMAE_media_rep=float(d_rep.mean()),
                         dRMSE=float(np.mean(drmse)), reps_que_mejoran=int((d_rep < 0).sum()),
                         parcelas_mejoran=int((d_parc < 0).sum()), parcelas_empeoran=int((d_parc > 0).sum()),
                         parcelas_empatan=int((d_parc == 0).sum()), **bs, **condiciones,
                         aplica_regla_promocion=aplica,
                         cumple_regla_promocion=(all(condiciones.values()) if aplica else None),
                         estado_promocion=('cumple' if all(condiciones.values()) else 'no_cumple') if aplica else 'no_aplica',
                         intervalo=('principal_predeclarado' if (candidato, frente_a) == PARES[0] and aplica
                                    else 'nominal_secundario_no_simultaneo'))
                filas.append(f)
                for pid, d in d_parc.items():
                    diferencias.append(dict(escenario=esc, variante=variante, poblacion=pob,
                                            candidato=candidato, frente_a=frente_a, id_parcela=pid,
                                            celda_chirps=celdas.loc[pid], d_error_absoluto=float(d),
                                            n_repeticiones_elegibles=int(n_rep.loc[pid])))
    return pd.DataFrame(filas), pd.DataFrame(diferencias)


def _orden_sensibilidad(principal, sensibilidad):
    filas = []
    for key, g in principal.groupby(['escenario', 'variante', 'poblacion'], sort=True):
        s = sensibilidad
        for col, val in zip(('escenario', 'variante', 'poblacion'), key):
            s = s[s[col] == val]
        if s.empty:
            continue
        p = g.sort_values(['MAE', 'procedimiento']).procedimiento.tolist()
        q = s.sort_values(['MAE', 'procedimiento']).procedimiento.tolist()
        filas.append(dict(escenario=key[0], variante=key[1], poblacion=key[2],
                         orden_principal=';'.join(p), orden_sin_alertas=';'.join(q),
                         mantiene_orden=p == q, uso='sensibilidad_no_decide', reentrenado=False))
    return pd.DataFrame(filas)


def calcular_reportes(oof: pd.DataFrame, calidad: pd.DataFrame, config: dict) -> dict[str, pd.DataFrame]:
    """Produce tablas sin redondear, con máscara común y uniones verificadas por ID.

    T se almacena únicamente con variante seleccionada; se reutiliza para las dos
    ventanas fijas. Los resúmenes promedian métricas por repetición, no por fold.
    Las banderas derivadas de etiquetas/calidad se usan únicamente para auditar.
    """
    ev = _config(config)
    original = _validar(oof, calidad)
    x = _expandir_t(original)
    rep = _por_repeticion(x)
    resumen = _resumir(rep)
    comp, diferencias = _comparaciones(x, ev)
    desgloses = ('municipio', 'cultivo_origen', 'contorno', 'contorno_angosta_o_muy_pequena',
                 'escalon_etiqueta', 'vecina_etiquetada_menos_20m')
    drep = pd.concat([_por_repeticion(x, desglose=c) for c in desgloses], ignore_index=True)
    # Calidad fijada: sólo se filtran métricas sobre las mismas OOF; no hay fits.
    sin = x[x.alerta_contorno_t03_bis.eq('no')]
    srep = _por_repeticion(sin, sensibilidad='sin_alertas_contorno')
    sres = _resumir(srep)
    nalerta = original.loc[original.alerta_contorno_t03_bis.eq('si'), 'id_parcela'].nunique()
    sres['n_alertas_excluidas'] = nalerta
    sres['reentrenado'] = False
    return dict(metricas_por_repeticion=rep, metricas_resumen=resumen,
                comparaciones_emparejadas=comp, diferencias_por_parcela=diferencias,
                desgloses_por_repeticion=drep, desgloses_resumen=_resumir(drep),
                sensibilidad_por_repeticion=srep, sensibilidad_resumen=sres,
                sensibilidad_orden=_orden_sensibilidad(resumen, sres))
