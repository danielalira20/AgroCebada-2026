"""Evaluación registrada R_centrado v2. Preserva íntegros los consumidores v1."""
import argparse
import json
import platform
from pathlib import Path

import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits

from scripts.t09_entradas import RAIZ, cargar_entradas, contexto_externo, sha
from scripts.t09_estimadores import crear_estimador
from scripts.t09_evaluar import contextos, _filas, _coeficientes, verificar_referencia
from scripts.t09_seleccion import (Seleccion, particiones_internas, ajustar_particion,
                                  _clave)
from scripts.t09_reportes import metricas, _por_repeticion, _resumir, _bootstrap

VERSION = 'T09-evaluacion-R-centrado-v2'
DISENO = 'ac28ebdd6b2b5c67650f55a6c33ddfc1f24742a0358e9e0f8b819f2cc93fc429'
REGISTRO = 'bac0ca3ba04c99cb7269392c7b15464c7745fca0fca2976b4d821c9b23c1922b'
ARCH_DISENO = 'registro/t09/diseno_R_centrado_v2.json'
ARCH_REGISTRO = 'registro/t09/registro_R_centrado_v2.json'
CODIGO = ('scripts/t09_centrado_evaluar.py', 'scripts/t09_residual_centrado.py',
          'scripts/t09_estimadores.py', 'scripts/t09_entradas.py',
          'scripts/t09_evaluar.py', 'scripts/t09_seleccion.py',
          'scripts/t09_reportes.py', 'scripts/t09_diagnostico_atributos.py',
          'scripts/t07_fichas_atributos.py')
CLAVE = ['escenario', 'repeticion', 'particion', 'id_parcela']


def mismos_valores(a,b):
    """Igualdad exacta por ID; object y StringDtype pueden representar igual texto."""
    return a.index.equals(b.index) and np.array_equal(a.to_numpy(),b.to_numpy())


def contrato(raiz=RAIZ):
    raiz = Path(raiz)
    if sha(raiz/ARCH_DISENO) != DISENO or sha(raiz/ARCH_REGISTRO) != REGISTRO:
        raise ValueError('Diseño/registro v2 cambiado; versionar antes de ampliar búsqueda')
    cfg = json.loads((raiz/ARCH_DISENO).read_text())
    reg = json.loads((raiz/ARCH_REGISTRO).read_text())
    for nombre, huella in reg['historicos_sha256'].items():
        if sha(raiz/nombre) != huella:
            raise ValueError('Histórico de comparación modificado: '+nombre)
    # Preflight v1 acredita las fuentes comunes, no el nuevo procedimiento.
    entradas = cargar_entradas(raiz)
    if cfg['fuentes_sha256'] != entradas['configuracion']['fuentes_sha256']:
        raise ValueError('v2 no utiliza las mismas fuentes/particiones que v1')
    return entradas, cfg, reg


def seleccionar(X, y, escenario, cfg, cfg_v1):
    """Sólo entrenamiento externo; nunca recibe y externo ni las 59."""
    if sha(RAIZ/ARCH_DISENO) != DISENO or cfg != json.loads((RAIZ/ARCH_DISENO).read_text()):
        raise ValueError('Selección fuera del diseño v2 registrado')
    partes = particiones_internas(X, escenario, cfg_v1)
    filas = []
    for ventana in cfg['ventanas']:
        for intensidad in cfg['regularizacion']['lambda']:
            elegibles, todos = [], []
            for p in partes:
                _, pred = ajustar_particion(X, y, p, 'R_centrado', ventana, intensidad)
                e = np.abs(pred.to_numpy()-y.loc[pred.index].to_numpy())
                elegibles.extend(e[np.array(p.elegibles, dtype=bool)])
                todos.extend(e)
            filas.append(dict(procedimiento='R_centrado', escenario=escenario,
                              ventana=ventana, lambda_reg=float(intensidad),
                              MAE=float(np.mean(elegibles)), MAE_todas=float(np.mean(todos)),
                              n_elegibles=len(elegibles), n_validacion=len(todos), n_ajustes=4))
    if len(filas) != 8 or not np.isfinite([f['MAE'] for f in filas]).all():
        raise ValueError('Selección incompleta/no finita')
    mejor = min(filas, key=_clave)
    por_ventana = {w:min([f for f in filas if f['ventana']==w], key=_clave)
                   for w in cfg['ventanas']}
    return Seleccion(mejor['ventana'], mejor['lambda_reg'], pd.DataFrame(filas),
                     por_ventana, 32), partes


def evaluar_contexto(e, cfg, esc, rep, fold):
    tr, ytr, te, yte = contexto_externo(e, esc, rep, fold)
    seleccion, partes = seleccionar(tr, ytr, esc, cfg, e['configuracion'])
    referencia = crear_estimador('T').fit(tr,ytr).predict_with_details(te)
    oof = [_filas(referencia,te,yte,referencia,esc,rep,fold,'T','seleccionada','',np.nan,len(tr))]
    estados, coef, elecciones = [], [], []
    for ventana, op in seleccion.por_ventana.items():
        m = crear_estimador('R_centrado',ventana,op['lambda_reg']).fit(tr,ytr)
        if tuple(tr.index) != m.ids_entrenamiento_:
            raise ValueError('Fit externo con IDs distintos del entrenamiento')
        train_d = m.predict_with_details(tr)
        media = float(train_d.correccion.groupby(tr.municipio).mean().abs().max())
        if media > 1e-12:
            raise ValueError('La corrección tiene corrimiento municipal de entrenamiento')
        estados.append(dict(escenario=esc,repeticion=rep,particion=fold,
                            max_media_municipal_correccion_train=media,estado=m.estado()))
        detalle = m.predict_with_details(te)
        variantes = [ventana]
        if ventana == seleccion.ventana:
            variantes.insert(0,'seleccionada')
        for variante in variantes:
            f = _filas(detalle,te,yte,referencia,esc,rep,fold,'R_centrado',variante,
                       ventana,op['lambda_reg'],len(tr))
            f['fuente_centrado'] = detalle.fuente_centrado.to_numpy()
            oof.append(f)
            coef.extend(_coeficientes(m,esc,rep,fold,'R_centrado',variante,ventana,op['lambda_reg']))
            elecciones.append(dict(escenario=esc,repeticion=rep,particion=fold,
                                   procedimiento='R_centrado',variante=variante,ventana=ventana,
                                   lambda_reg=op['lambda_reg'],alpha=m.alpha_,n_entrenamiento=len(tr),
                                   MAE_interno=op['MAE'],n_elegibles_internos=op['n_elegibles']))
    oof = pd.concat(oof,ignore_index=True)
    oof['version'] = VERSION
    puntuaciones = seleccion.puntuaciones.assign(repeticion=rep,particion=fold)
    puntuaciones['seleccionada'] = (puntuaciones.ventana.eq(seleccion.ventana)&
                                   puntuaciones.lambda_reg.eq(seleccion.lambda_reg))
    contexto = dict(escenario=esc,repeticion=rep,particion=fold,
                    entrenamiento=list(tr.index),evaluacion=list(te.index),
                    internas=[dict(entrenamiento=list(p.entrenamiento),validacion=list(p.validacion),
                                   elegibles=[bool(v) for v in p.elegibles]) for p in partes])
    return dict(oof=oof,puntuaciones=puntuaciones,selecciones=pd.DataFrame(elecciones),
                coeficientes=pd.DataFrame(coef),estados=estados,contexto=contexto,n_ajustes=34)


def integrar_historicos(oof, e, raiz):
    """Reutilización identificada v1; no reentrena ni cambia sus etiquetas/versiones."""
    old = pd.read_csv(Path(raiz)/'registro/t09/predicciones_oof.csv',float_precision='round_trip')
    t = oof[oof.procedimiento.eq('T')].set_index(CLAVE).sort_index()
    antiguo = old[old.procedimiento.eq('T')].set_index(CLAVE).sort_index()
    if not t.index.equals(antiguo.index) or len(t)!=1518:
        raise ValueError('Referencia histórica con contextos incompletos')
    for col in ['real','prediccion','fuente','sin_respaldo','n_entrenamiento','celda_chirps']:
        if not mismos_valores(t[col],antiguo[col]):
            raise ValueError('Contexto/máscara/referencia histórica incompatible: '+col)
    for (esc,rep,proc,variante),g in oof.groupby(['escenario','repeticion','procedimiento','variante']):
        if len(g)!=138 or set(g.id_parcela)!=set(e['X'].index):
            raise ValueError('OOF incompleta o incluye reservadas')
        if not np.array_equal(e['y'].reindex(g.id_parcela).to_numpy(),g.real.to_numpy()):
            raise ValueError('OOF con etiquetas distintas')
    if len(oof)!=6072 or oof.duplicated(CLAVE+['procedimiento','variante']).any():
        raise ValueError('OOF duplicada/conteo inesperado')
    for proc in ('R','TC'):
        g=old[old.procedimiento.eq(proc)].set_index(CLAVE).sort_index()
        if not g.index.equals(t.index): raise ValueError('Comparador histórico incompleto')
        for c in ['real','fuente_referencia','sin_respaldo','n_entrenamiento','celda_chirps']:
            if not mismos_valores(g[c],t[c]): raise ValueError('Comparador incompatible: '+c)
    return pd.concat([oof,old[old.procedimiento.isin(['R','TC'])]],ignore_index=True)


def reportes(x,cfg):
    if (set(x.procedimiento)!={'T','R','TC','R_centrado'} or
            x.celda_chirps.isna().any() or not x.celda_chirps.map(lambda c:isinstance(c,str) and bool(c.strip())).all() or
            not pd.api.types.is_bool_dtype(x.sin_respaldo)):
        raise ValueError('Procedimientos/celdas/máscara incompatibles; no omitir parcelas')
    # T se duplica sólo para métricas de ventanas fijas, nunca para entrenar.
    expanded=pd.concat([x,*[x[x.procedimiento.eq('T')].assign(variante=w)
                              for w in cfg['ventanas']]],ignore_index=True)
    reps=_por_repeticion(expanded)
    resumen=_resumir(reps)
    comp, difs=[],[]
    for esc,g in expanded.groupby('escenario',sort=True):
        for pob,z in [('todas',g)]+([] if esc=='C' else [('sin_respaldo',g[g.sin_respaldo])]):
            for variante,s in z.groupby('variante',sort=True):
                a=s[s.procedimiento.eq('R_centrado')].set_index(['id_parcela','repeticion']).sort_index()
                for proc in (['T','R','TC'] if variante=='seleccionada' else ['T']):
                    b=s[s.procedimiento.eq(proc)].set_index(['id_parcela','repeticion']).sort_index()
                    if a.empty or not a.index.equals(b.index): raise ValueError('Contraste no emparejado')
                    delta=(a.prediccion-a.real).abs()-(b.prediccion-b.real).abs()
                    dp=delta.groupby(level='id_parcela').mean()
                    dr=delta.groupby(level='repeticion').mean()
                    cel=a.reset_index().drop_duplicates('id_parcela').set_index('id_parcela').celda_chirps
                    ci=_bootstrap(dp,cel,cfg['evaluacion_heredada']['bootstrap'])
                    drmse=float(np.mean([metricas(a.xs(r,level='repeticion').real,a.xs(r,level='repeticion').prediccion)['RMSE']-
                                        metricas(b.xs(r,level='repeticion').real,b.xs(r,level='repeticion').prediccion)['RMSE'] for r in dr.index]))
                    aplica=esc=='A' and pob=='sin_respaldo' and variante=='seleccionada' and proc=='T'
                    condiciones=dict(condicion_dMAE=bool(dp.mean()<=-.01),condicion_IC95=bool(ci['IC95_celdas_sup']<0),
                                     condicion_repeticiones=bool((dr<0).sum()>=4),condicion_dRMSE=bool(drmse<=.01))
                    comp.append(dict(escenario=esc,poblacion=pob,variante=variante,candidato='R_centrado',frente_a=proc,
                                     n_predicciones=len(a),n_parcelas=len(dp),dMAE=float(dp.mean()),dMAE_media_rep=float(dr.mean()),
                                     dRMSE=drmse,reps_que_mejoran=int((dr<0).sum()),**ci,**condiciones,
                                     aplica_regla_promocion=aplica,estado_promocion=('cumple' if all(condiciones.values()) else 'no_cumple') if aplica else 'no_aplica',
                                     intervalo='nominal_post_revision_no_confirmacion_independiente'))
                    for pid,d in dp.items():
                        difs.append(dict(escenario=esc,poblacion=pob,variante=variante,candidato='R_centrado',frente_a=proc,
                                         id_parcela=pid,celda_chirps=cel.loc[pid],d_error_absoluto=float(d),
                                         n_repeticiones_elegibles=int(delta.groupby(level='id_parcela').size().loc[pid])))
    return dict(metricas_por_repeticion=reps,metricas_resumen=resumen,
                comparaciones_emparejadas=pd.DataFrame(comp),diferencias_por_parcela=pd.DataFrame(difs))


def preparar_salida(salida,raiz):
    raiz,salida=Path(raiz).resolve(),Path(salida).resolve()
    if not any(salida.parent.is_relative_to(raiz/p) and salida.parent!=raiz/p
               for p in ('reports','data/processed/t09')):
        raise ValueError('Usar una subcarpeta nueva de reports/ o data/processed/t09/')
    if salida.exists(): raise ValueError('Conservar evidencia: salida ya existe')
    return salida


def ejecutar(salida,raiz=RAIZ):
    salida=preparar_salida(salida,raiz)
    e,cfg,reg=contrato(raiz) # Falla antes de crear resultados.
    filas=[]
    with threadpool_limits(limits=1):
        for i,(esc,rep,fold) in enumerate(contextos(e),1):
            filas.append(evaluar_contexto(e,cfg,esc,rep,fold))
            print(f'{i}/59 {esc}/{rep}/{fold}: 32 internos + 2 reajustes',flush=True)
        oof=pd.concat([f['oof'] for f in filas],ignore_index=True)
        t08=verificar_referencia(oof[oof.procedimiento.eq('T')],raiz)
        unidos=integrar_historicos(oof,e,raiz)
        tablas=reportes(unidos,cfg)
    if len(filas)!=59 or sum(f['n_ajustes'] for f in filas)!=2006:
        raise ValueError('Presupuesto de evaluación distinto del registro')
    tablas.update(predicciones_oof=unidos,puntuaciones_internas=pd.concat([f['puntuaciones'] for f in filas]),
                  seleccion_interna=pd.concat([f['selecciones'] for f in filas]),
                  coeficientes=pd.concat([f['coeficientes'] for f in filas]))
    # Sólo crear la carpeta final cuando todos los contextos/reportes son válidos.
    salida.mkdir(parents=True)
    for nombre,t in tablas.items():t.to_csv(salida/(nombre+'.csv'),index=False,float_format='%.17g')
    for nombre,valor in {'contextos':[f['contexto'] for f in filas],
                         'estados':[s for f in filas for s in f['estados']]}.items():
        (salida/(nombre+'.json')).write_text(json.dumps(valor,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    resultado=dict(version=VERSION,id_experimento=reg['id'],diseno_sha256=DISENO,registro_sha256=REGISTRO,
                   contextos_externos=59,fits_ridge_internos=1888,fits_ridge_externos=118,fits_ridge_totales=2006,
                   fits_T_externos=59,predicciones_nuevas=4554,predicciones_T=1518,predicciones_historicas_reutilizadas=3036,
                   filas_oof=len(unidos),ajuste_final_59=False,revision_humana='pendiente_Migue',T08=t08,
                   previos_conocidos=True,es_confirmacion_independiente=False)
    (salida/'resultado.json').write_text(json.dumps(resultado,ensure_ascii=False,indent=2)+'\n')
    import sklearn
    procedencia=dict(version=VERSION,diseno_sha256=DISENO,registro_sha256=REGISTRO,
                    codigo_sha256={p:sha(Path(raiz)/p) for p in CODIGO},
                    historicos_sha256=reg['historicos_sha256'],fuentes_sha256=cfg['fuentes_sha256'],
                    entorno=dict(sistema=platform.system(),arquitectura=platform.machine(),python=platform.python_version(),
                                 numpy=np.__version__,pandas=pd.__version__,sklearn=sklearn.__version__),
                    salidas_sha256={p.name:sha(p) for p in sorted(salida.iterdir()) if p.is_file()})
    (salida/'procedencia.json').write_text(json.dumps(procedencia,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(resultado,ensure_ascii=False,indent=2))
    return resultado


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--salida',type=Path,required=True)
    args=ap.parse_args();ejecutar(args.salida)


if __name__=='__main__': main()
