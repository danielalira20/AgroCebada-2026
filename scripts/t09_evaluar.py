"""Evaluación externa T09 v1; no congela T16 ni ajusta las 59 de T18."""
import argparse
import hashlib
import json
import platform
import time
from pathlib import Path

import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits

from scripts.t09_entradas import RAIZ, cargar_entradas, contexto_externo, sha
from scripts.t09_estimadores import columnas_clima, crear_estimador
from scripts.t09_seleccion import elegir_configuracion, particiones_internas

VERSION = 'T09-evaluacion-v1'
PROCEDIMIENTOS = ('T', 'CL', 'TC', 'R')
CLIMATICOS = PROCEDIMIENTOS[1:]


def contextos(entradas):
    for escenario in ('A', 'B'):
        for repeticion in range(1, 6):
            for particion in range(5):
                yield escenario, repeticion, particion
    for particion in range(entradas['X'].municipio.nunique()):
        yield 'C', 1, particion


def _identidad_ids(ids):
    return hashlib.sha256('\n'.join(ids).encode('utf-8')).hexdigest()


def _filas(detalle, Xte, yte, referencia, escenario, rep, fold, proc,
           variante, ventana, intensidad, n):
    if list(detalle.index) != list(Xte.index) or list(yte.index) != list(Xte.index):
        raise ValueError('Predicciones externas desalineadas por ID')
    r = Xte[['id_parcela', 'municipio', 'cultivo_origen', 'celda_chirps']].copy()
    for c in ('prediccion', 'referencia', 'correccion', 'fuente'):
        r[c] = detalle[c]
    r['real'] = yte
    r['escenario'], r['repeticion'], r['particion'] = escenario, rep, fold
    r['procedimiento'], r['variante'] = proc, variante
    r['ventana'], r['lambda_reg'] = ventana, intensidad
    r['n_entrenamiento'] = n
    r['fuente_referencia'] = referencia.fuente
    # CL es global por definición: la población comparable proviene de T08.
    r['sin_respaldo'] = referencia.fuente.eq('municipio')
    r['error'] = r.prediccion - r.real
    r['error_absoluto'] = r.error.abs()
    r['error_cuadrado'] = r.error.pow(2)
    r['ID_POLIGONO'], r['candidato'], r['version'] = r.id_parcela, proc, VERSION
    if not np.isfinite(r[['real', 'prediccion', 'referencia', 'correccion']]).all().all():
        raise ValueError('Salida externa no finita; no recortar ni rellenar')
    if not np.allclose(r.prediccion, r.referencia + r.correccion, rtol=0, atol=1e-12):
        raise ValueError('Descomposición de la predicción incompatible')
    return r.reset_index(drop=True)


def _coeficientes(modelo, escenario, rep, fold, proc, variante, ventana, intensidad):
    escala = modelo.preprocesado_['escala']
    return [dict(escenario=escenario, repeticion=rep, particion=fold,
                 procedimiento=proc, variante=variante, ventana=ventana,
                 lambda_reg=float(intensidad), alpha=modelo.alpha_,
                 n_entrenamiento=modelo.n_entrenamiento_, columna=c,
                 coef_estandarizado=float(modelo.coef_estandarizados_[i]),
                 coef_fisico=float(modelo.coef_fisicos_[i]),
                 media_escalado=float(escala.mean_[i]), escala=float(escala.scale_[i]),
                 constante=c in modelo.constantes_, interpretacion='asociacion_predictiva_no_causal')
            for i, c in enumerate(modelo.columnas_)]


def evaluar_contexto(entradas, escenario, repeticion, particion):
    cfg = entradas['configuracion']
    Xtr, ytr, Xte, yte = contexto_externo(entradas, escenario, repeticion, particion)
    if set(Xtr.index) & set(Xte.index) or set(Xtr.index) | set(Xte.index) != set(entradas['X'].index):
        raise ValueError('IDs externos no disjuntos/completos')
    partes = particiones_internas(Xtr, escenario, cfg)
    huella = dict(escenario=escenario, repeticion=repeticion, particion=particion,
                  entrenamiento=list(Xtr.index), evaluacion=list(Xte.index),
                  sha_ids_entrenamiento=_identidad_ids(Xtr.index),
                  sha_ids_evaluacion=_identidad_ids(Xte.index),
                  internas=[dict(entrenamiento=list(p.entrenamiento),
                                 validacion=list(p.validacion),
                                 elegibles=[bool(b) for b in p.elegibles]) for p in partes])
    base = crear_estimador('T').fit(Xtr, ytr)
    referencia = base.predict_with_details(Xte)
    resultados = [_filas(referencia, Xte, yte, referencia, escenario, repeticion,
                         particion, 'T', 'seleccionada', '', np.nan, len(Xtr))]
    puntuaciones, selecciones, coeficientes = [], [], []
    n_ajustes = 0
    for proc in CLIMATICOS:
        seleccion = elegir_configuracion(Xtr, ytr, proc, escenario, cfg)
        scores = seleccion.puntuaciones.copy()
        scores['repeticion'], scores['particion'] = repeticion, particion
        scores['seleccionada'] = (scores.ventana.eq(seleccion.ventana)
                                  & scores.lambda_reg.eq(seleccion.lambda_reg))
        scores['seleccionada_en_ventana'] = [
            s.lambda_reg == seleccion.por_ventana[s.ventana]['lambda_reg']
            for s in scores.itertuples()]
        scores['sha_ids_entrenamiento'] = huella['sha_ids_entrenamiento']
        puntuaciones.append(scores)
        n_ajustes += seleccion.n_ajustes
        # Dos reajustes: el elegido se reutiliza para su ventana fija, sin tercer fit.
        for ventana, opcion in seleccion.por_ventana.items():
            intensidad = float(opcion['lambda_reg'])
            modelo = crear_estimador(proc, ventana, intensidad).fit(Xtr, ytr)
            if tuple(Xtr.index) != modelo.ids_entrenamiento_:
                raise ValueError('Estimador ajustado con IDs distintos del entrenamiento externo')
            n_ajustes += 1
            detalle = modelo.predict_with_details(Xte)
            variantes = [ventana]
            if ventana == seleccion.ventana:
                if intensidad != seleccion.lambda_reg:
                    raise ValueError('Configuración elegida distinta de la mejor en su ventana')
                variantes.insert(0, 'seleccionada')
            for variante in variantes:
                resultados.append(_filas(detalle, Xte, yte, referencia, escenario,
                                         repeticion, particion, proc, variante,
                                         ventana, intensidad, len(Xtr)))
                coeficientes.extend(_coeficientes(modelo, escenario, repeticion, particion,
                                                  proc, variante, ventana, intensidad))
                selecciones.append(dict(escenario=escenario, repeticion=repeticion,
                                        particion=particion, procedimiento=proc,
                                        variante=variante, ventana=ventana,
                                        lambda_reg=intensidad, alpha=modelo.alpha_,
                                        MAE_interno=float(opcion['MAE']),
                                        n_elegibles_internos=int(opcion['n_elegibles']),
                                        n_entrenamiento=len(Xtr),
                                        sha_ids_entrenamiento=huella['sha_ids_entrenamiento']))
    if n_ajustes != 102:
        raise ValueError('Presupuesto externo distinto del diseño: 3×(8×4+2)')
    return dict(oof=pd.concat(resultados, ignore_index=True),
                puntuaciones=pd.concat(puntuaciones, ignore_index=True),
                selecciones=pd.DataFrame(selecciones),
                coeficientes=pd.DataFrame(coeficientes),
                contexto=huella, n_ajustes=n_ajustes)


def validar_oof(oof, entradas):
    llave = ['escenario', 'repeticion', 'id_parcela', 'procedimiento', 'variante']
    if oof[llave].duplicated().any():
        raise ValueError('Predicciones externas repetidas por ID/contexto/procedimiento')
    conocidos = set(entradas['X'].index)
    for (esc, rep, proc, variante), g in oof.groupby(
            ['escenario', 'repeticion', 'procedimiento', 'variante'], sort=True):
        if set(g.id_parcela) != conocidos or len(g) != len(conocidos):
            raise ValueError(f'Evaluación incompleta: {esc}/{rep}/{proc}/{variante}')
        esperado = entradas['y'].reindex(g.id_parcela).to_numpy()
        if not np.array_equal(esperado, g.real.to_numpy()):
            raise ValueError('Rendimiento externo distinto de la etiqueta real')
    selected = oof[oof.variante.eq('seleccionada')]
    if len(selected[selected.escenario.isin(['A', 'B'])]) != 5520 or len(selected[selected.escenario.eq('C')]) != 552:
        raise ValueError('Conteos externos distintos de T09 v1')
    if len(oof) != 15180:
        raise ValueError('Diagnósticos de ventana fija incompletos')
    ref = selected[selected.procedimiento.eq('T')]
    for esc, n in entradas['configuracion']['evaluacion']['n_predicciones_sin_respaldo'].items():
        if int(ref.loc[ref.escenario.eq(esc), 'sin_respaldo'].sum()) != n:
            raise ValueError('Población sin respaldo distinta de T08')
    # Las 59 no aparecen ni como etiquetas ni como casos de evaluación.
    if set(oof.id_parcela) & set(entradas['reservadas'].index):
        raise ValueError('Reservadas incluidas en evaluación')
    return selected


def verificar_referencia(oof, raiz=RAIZ):
    # Restaurar los doubles publicados: el parser habitual puede cambiar un último bit.
    publicada = pd.read_csv(Path(raiz) / 'registro/t03/predicciones_oof_referencias_media_mun__resp_grupo.csv',
                            float_precision='round_trip')
    ref = oof[oof.procedimiento.eq('T') & oof.escenario.isin(['A', 'B'])]
    claves = ['escenario', 'repeticion', 'particion', 'ID_POLIGONO']
    m = ref.merge(publicada, on=claves, how='outer', validate='one_to_one',
                  suffixes=('_t09', '_t08'), indicator=True)
    if len(m) != 1380 or not m['_merge'].eq('both').all():
        raise ValueError('Referencia T08 incompleta o IDs/contextos diferentes')
    for c in ['prediccion', 'real']:
        if not np.array_equal(m[c+'_t09'].to_numpy(), m[c+'_t08'].to_numpy()):
            raise ValueError('Referencia T09 no reproduce exactamente T08: '+c)
    if not m.fuente_t09.eq(m.fuente_t08).all():
        raise ValueError('Fuentes de referencia diferentes de T08')
    return dict(predicciones=1380, diferencia_maxima=0.0, fuentes_identicas=True)


def aplicabilidad_reservadas(entradas):
    """Sólo metadatos/rangos de entradas; no ajusta modelos con las138."""
    tr, te = entradas['X'], entradas['reservadas']
    filas = []
    perfiles = {}
    for ventana in entradas['configuracion']['ventanas']:
        cols = columnas_clima(ventana)
        valores = tr[cols].to_numpy(dtype=float)
        sd = valores.std(axis=0, ddof=0)
        # Escala aprendida sólo de entradas etiquetadas; no usa y ni elige parámetros.
        perfiles[ventana] = (cols, valores, np.where(sd == 0, 1., sd))
    for pid, r in te.iterrows():
        n = int(tr.municipio.eq(r.municipio).sum())
        fuera_global, fuera_municipio = [], []
        for c in [c for w in entradas['configuracion']['ventanas'] for c in columnas_clima(w)]:
            if not tr[c].min() <= r[c] <= tr[c].max():
                fuera_global.append(c)
            local = tr.loc[tr.municipio.eq(r.municipio), c]
            if n and not local.min() <= r[c] <= local.max():
                fuera_municipio.append(c)
        perfil = {}
        for ventana, (cols, valores, sd) in perfiles.items():
            diferencias = valores - r[cols].to_numpy(dtype=float)
            distancias = np.linalg.norm(diferencias / sd, axis=1)
            j = int(np.argmin(distancias))
            perfil['perfil_observado_'+ventana] = bool(np.equal(diferencias, 0).all(axis=1).any())
            perfil['distancia_clima_estandarizada_min_'+ventana] = float(distancias[j])
            perfil['id_perfil_mas_proximo_'+ventana] = tr.index[j]
        filas.append(dict(id_parcela=pid, municipio=r.municipio, n_etiquetas_municipio=n,
                          fuente_referencia_prevista='municipio' if n else ('grupo' if tr.cultivo_origen.eq(r.cultivo_origen).any() else 'global'),
                          soporte_municipal_escaso=n < 4,
                          fuera_rango_global=';'.join(fuera_global),
                          fuera_rango_municipio=';'.join(fuera_municipio),
                          clima_completo=True, modelo_ajustado=False,
                          significado='diagnostico_de_entradas_no_error_ni_intervalo', **perfil))
    return pd.DataFrame(filas)


def preparar_salida(salida, raiz=RAIZ):
    raiz, salida = Path(raiz).resolve(), Path(salida).resolve()
    permitidos = [raiz/'reports', raiz/'data/processed/t09']
    if not any(salida.is_relative_to(p) and salida != p for p in permitidos):
        raise ValueError('La evaluación sólo escribe en una subcarpeta local reports/ o data/processed/t09/')
    if salida.exists():
        raise FileExistsError('La salida ya existe; conservar ejecución anterior y elegir otra ruta')
    salida.mkdir(parents=True)
    return salida


def _json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf-8')


def ejecutar(salida, raiz=RAIZ):
    # Todo el preflight ocurre antes de crear la salida o ajustar modelos.
    entradas = cargar_entradas(raiz)
    salida = preparar_salida(salida, raiz)
    inicio = time.monotonic()
    from scripts.t09_reportes import calcular_reportes
    resultados, huellas, n_ajustes = [], [], 0
    with threadpool_limits(limits=1):
        for i, (esc, rep, fold) in enumerate(contextos(entradas), 1):
            r = evaluar_contexto(entradas, esc, rep, fold)
            resultados.append(r)
            huellas.append(r['contexto'])
            n_ajustes += r['n_ajustes']
            print(f'Contexto {i}/59: {esc}, repetición {rep}, partición {fold}; ajustes climáticos {n_ajustes}', flush=True)
    oof = pd.concat([r['oof'] for r in resultados], ignore_index=True)
    oof = oof.sort_values(['escenario', 'repeticion', 'particion', 'procedimiento', 'variante', 'id_parcela']).reset_index(drop=True)
    seleccionadas = validar_oof(oof, entradas)
    contraste = verificar_referencia(oof, raiz)
    if n_ajustes != 6018 or len(huellas) != 59:
        raise ValueError('Ejecución externa incompleta o fuera del presupuesto')
    tablas = dict(predicciones_oof=oof, predicciones_oof_seleccionadas=seleccionadas,
                  puntuaciones_internas=pd.concat([r['puntuaciones'] for r in resultados], ignore_index=True),
                  seleccion_interna=pd.concat([r['selecciones'] for r in resultados], ignore_index=True),
                  coeficientes=pd.concat([r['coeficientes'] for r in resultados], ignore_index=True),
                  aplicabilidad_59=aplicabilidad_reservadas(entradas))
    calidad = pd.read_csv(Path(raiz)/'registro/t07/calidad_parcelas.csv')
    if (int(calidad.loc[calidad.id_parcela.isin(entradas['X'].index),
                         'alerta_contorno_t03_bis'].eq('si').sum()) != 24):
        raise ValueError('Sensibilidad incompatible con las24alertas fijadas de T03')
    tablas.update(calcular_reportes(oof, calidad, entradas['configuracion']))
    # Detectar modificación concurrente de insumos también al terminar.
    cargar_entradas(raiz)
    for nombre, t in tablas.items():
        t.to_csv(salida/(nombre+'.csv'), index=False, float_format='%.17g', lineterminator='\n')
    _json(salida/'contextos.json', huellas)
    _json(salida/'resultado.json', dict(resultado='evaluacion_completa_pendiente_revision',
        version=VERSION, diseno_sha256=entradas['sha_diseno'],
        contextos_externos=59, internas=236, ajustes_climaticos=6018,
        referencia_T08=contraste, filas_oof_seleccionadas=6072,
        filas_oof_diagnosticas=9108, reservadas_evaluadas=0,
        ajuste_final_59=False, cierre_t09=False, revision_Migue='pendiente',
        ganador_T16=None, fuentes_protegidas=entradas['configuracion']['fuentes_sha256']))
    import scipy, sklearn
    _json(salida/'procedencia.json', dict(version=VERSION,
        entorno=dict(sistema=platform.system(), arquitectura=platform.machine(),
                     python=platform.python_version(), numpy=np.__version__, pandas=pd.__version__,
                     scipy=scipy.__version__, sklearn=sklearn.__version__, hilos=1),
        codigo_sha256={str(p.relative_to(Path(raiz))):sha(p) for p in
                      [Path(raiz)/'scripts'/n for n in ['t09_evaluar.py', 't09_reportes.py',
                       't09_entradas.py', 't09_estimadores.py', 't09_seleccion.py']]},
        salidas_sha256={p.name:sha(p) for p in sorted(salida.iterdir()) if p.is_file()}))
    print(json.dumps(dict(resultado='evaluacion_completa_pendiente_revision',
                         ruta=str(salida), segundos=round(time.monotonic()-inicio, 2),
                         ajustes_climaticos=n_ajustes), ensure_ascii=False), flush=True)
    return salida


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--salida', type=Path, required=True)
    parser.add_argument('--raiz', type=Path, default=RAIZ)
    args = parser.parse_args()
    ejecutar(args.salida, args.raiz)


if __name__ == '__main__':
    main()
