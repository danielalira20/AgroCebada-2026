"""Diagnóstico descriptivo previo a T09; no selecciona, imputa ni entrena.

Lee la entrega T07 completa y verificada. Escribe sólo agregados en una salida
nueva de reports/. Las correlaciones con rendimiento usan las 138 etiquetas;
su lectura no autoriza fijar filtros antes de la validación anidada.
"""
import argparse
import hashlib
import json
import platform
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd

from scripts.t07_fichas_atributos import leer_contrato

RAIZ = Path(__file__).resolve().parents[1]
CLIMA = [f'{v}_{w}' for w in ('abr_oct', 'jun_oct')
         for v in ('prec_acumulada_mm', 'tmin_media_c', 'tmax_media_c')]
OBJETIVO = 'rendimiento_t_ha'
VERSION = 't09_diagnostico_descriptivo_v1'


def exigir(condicion, mensaje):
    if not condicion:
        raise ValueError(mensaje)


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def validar_tabla(d, dic):
    exigir(len(d) == 197 and d.id_parcela.notna().all() and d.id_parcela.is_unique,
           'Se requieren 197 IDs únicos y no vacíos')
    exigir(list(d.columns) == [r['columna'] for r in dic], 'Columnas fuera de contrato')
    exigir(d.campania.eq(2025).all(), 'Campaña fuera del alcance 2025')
    exigir(d.municipio.notna().all(), 'Municipio ausente')
    exigir(d.conjunto_origen.value_counts().to_dict() == {'ENTRENAMIENTO': 138, 'PREDICCION': 59},
           'Poblaciones distintas de 138/59')
    entr = d.conjunto_origen.eq('ENTRENAMIENTO')
    exigir(d.loc[entr, OBJETIVO].notna().all() and d.loc[~entr, OBJETIVO].isna().all(),
           'Etiquetas ausentes en entrenamiento o presentes en reservadas')
    texto = {'id_parcela', 'municipio', 'estado', 'cultivo_origen', 'conjunto_origen'}
    exigir(all(pd.api.types.is_numeric_dtype(d[c]) for c in d if c not in texto),
           'Texto inesperado en una columna numérica')
    for c in d.select_dtypes(include='number'):
        exigir(np.isfinite(d[c].dropna()).all(), f'Valor no finito: {c}')
    exigir(d[CLIMA].notna().all().all(), 'Clima incompleto; revisar la entrega antes del diagnóstico')


def cargar(raiz):
    dic, contrato, _ = leer_contrato(raiz)
    d = pd.read_csv(raiz / 'registro/t07/tabla_comun.csv')
    validar_tabla(d, dic)
    return d, dic, contrato


def variable(x):
    """No confundir residuos de redondeo con variación interpretable."""
    a = np.asarray(x, dtype=float)
    return len(a) >= 2 and np.ptp(a) > 32 * np.finfo(float).eps * max(1., np.max(np.abs(a)))


def pearson(x, y):
    x, y = np.asarray(x, dtype=float), np.asarray(y, dtype=float)
    mask = np.isfinite(x) & np.isfinite(y)
    x, y = x[mask], y[mask]
    if not variable(x) or not variable(y):
        return None
    xc, yc = x - x.mean(), y - y.mean()
    return float(np.clip(np.dot(xc, yc) / np.sqrt(np.dot(xc, xc) * np.dot(yc, yc)), -1, 1))


def relacion(d, x, y):
    a = d[['municipio', x, y]].dropna()
    xc = a[x] - a.groupby('municipio')[x].transform('mean')
    yc = a[y] - a.groupby('municipio')[y].transform('mean')
    total = float(((a[x] - a[x].mean()) ** 2).sum())
    dentro = float((xc ** 2).sum())
    return dict(n=len(a), municipios=a.municipio.nunique(),
                pearson_global=pearson(a[x], a[y]), pearson_dentro_municipio=pearson(xc, yc),
                fraccion_variacion_x_entre_municipios=(1 - dentro / total) if variable(a[x]) else None)


def clima_objetivo(d):
    # La etiqueta de las reservadas nunca participa, ni siquiera si el llamador la aporta.
    entr = d[d.conjunto_origen.eq('ENTRENAMIENTO')]
    filas = []
    for c in CLIMA:
        r = relacion(entr, c, OBJETIVO)
        sensibilidad = [pearson(g[c], g[OBJETIVO]) for g in
                        (entr.drop(index=i) for i in entr.index)]
        sensibilidad = [v for v in sensibilidad if v is not None]
        filas.append(dict(columna=c, **r,
                          pearson_global_loo_min=min(sensibilidad, default=None),
                          pearson_global_loo_max=max(sensibilidad, default=None)))
    return pd.DataFrame(filas)


def perfiles(d, dic):
    filas = []
    roles = {r['columna']: r['funcion'] for r in dic}
    for nombre, a in [('total', d), ('etiquetadas', d[d.conjunto_origen.eq('ENTRENAMIENTO')]),
                      ('reservadas', d[d.conjunto_origen.eq('PREDICCION')])]:
        for c in d.columns:
            s = a[c]
            r = dict(poblacion=nombre, columna=c, rol=roles[c], n=len(s),
                     ausentes=int(s.isna().sum()), distintos=int(s.nunique()),
                     constante=s.nunique() == 1, minimo=None, q25=None, mediana=None,
                     q75=None, maximo=None, media=None, sd=None, mad=None,
                     fuera_cerca_iqr=None)
            if pd.api.types.is_numeric_dtype(s) and s.notna().any():
                v = s.dropna()
                q1, med, q3 = v.quantile([.25, .5, .75])
                iqr = q3 - q1
                r.update(minimo=v.min(), q25=q1, mediana=med, q75=q3, maximo=v.max(),
                         media=v.mean(), sd=v.std(), mad=(v - med).abs().median(),
                         fuera_cerca_iqr=int(((v < q1 - 1.5 * iqr) | (v > q3 + 1.5 * iqr)).sum()))
            filas.append(r)
    return pd.DataFrame(filas)


def ventanas(d, roles):
    filas = []
    for c in d.columns:
        otra = c.replace('_abr_oct', '_jun_oct')
        if not c.endswith('_abr_oct') or otra not in d:
            continue
        completos = d[[c, otra]].dropna()
        filas.append(dict(columna_abr=c, columna_jun=otra, rol=roles[c],
                          n_pares=len(completos), ausencias_iguales=d[c].isna().equals(d[otra].isna()),
                          iguales_observados=int(completos[c].eq(completos[otra]).sum()),
                          identicas_197=bool(len(completos) == len(d) and completos[c].eq(completos[otra]).all()),
                          diferencia_maxima=float((completos[c] - completos[otra]).abs().max()),
                          pearson=pearson(completos[c], completos[otra])))
    return pd.DataFrame(filas)


def distancia_ecdf(x, y):
    """Estadístico D de KS descriptivo; no p-valor IID en parcelas dependientes."""
    x, y = np.sort(np.asarray(x, dtype=float)), np.sort(np.asarray(y, dtype=float))
    exigir(len(x) > 0 and len(y) > 0, 'ECDF sin observaciones')
    puntos = np.unique(np.concatenate([x, y]))
    return float(np.max(np.abs(np.searchsorted(x, puntos, side='right') / len(x)
                              - np.searchsorted(y, puntos, side='right') / len(y))))


def soporte(d):
    tr, te = d[d.conjunto_origen.eq('ENTRENAMIENTO')], d[d.conjunto_origen.eq('PREDICCION')]
    filas = []
    for c in CLIMA + ['area_ha_origen']:
        a, b = tr[c].dropna(), te[c].dropna()
        filas.append(dict(columna=c, n_etiquetadas=len(a), n_reservadas=len(b),
                          ks_D_descriptivo=distancia_ecdf(a, b),
                          mediana_etiquetadas=a.median(), mediana_reservadas=b.median(),
                          reservadas_fuera_rango=int(((b < a.min()) | (b > a.max())).sum())))
    return pd.DataFrame(filas)


def figuras(d, salida):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    e = d[d.conjunto_origen.eq('ENTRENAMIENTO')]
    colores = pd.Categorical(e.municipio).codes
    fig, axs = plt.subplots(2, 3, figsize=(12, 7), constrained_layout=True)
    nombres = ['Lluvia acumulada (mm)', 'Temperatura mínima media (°C)', 'Temperatura máxima media (°C)']
    for j, c in enumerate(CLIMA[:3]):
        for fila in (0, 1):
            x, y = e[c], e[OBJETIVO]
            if fila:
                x = x - e.groupby('municipio')[c].transform('mean')
                y = y - e.groupby('municipio')[OBJETIVO].transform('mean')
            ax = axs[fila,j]
            ax.scatter(x,y,c=colores,cmap='tab10',s=22,alpha=.65,edgecolors='none')
            ax.set_xlabel(('Desviación municipal: ' if fila else '') + nombres[j])
            ax.set_ylabel('Desviación del rendimiento (t/ha)' if fila else 'Rendimiento (t/ha)')
            ax.set_title(f"{'Dentro del municipio' if fila else 'Global'} · r = {pearson(x,y):.3f}")
            ax.grid(alpha=.2)
    fig.suptitle('Clima y rendimiento · abril–octubre de 2025\n138 parcelas; color por municipio · descripción, sin selección ni predicción', fontsize=13)
    fig.savefig(salida/'clima_abr_oct.png', dpi=160)
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(8,7), constrained_layout=True)
    m = e[CLIMA].corr().to_numpy()
    im = ax.imshow(m, vmin=-1, vmax=1, cmap='RdBu_r')
    nombres = ['Lluvia abr–oct','Tmin abr–oct','Tmax abr–oct','Lluvia jun–oct','Tmin jun–oct','Tmax jun–oct']
    ax.set_xticks(range(6),nombres,rotation=45,ha='right')
    ax.set_yticks(range(6),nombres)
    for i in range(6):
        for j in range(6):
            ax.text(j,i,f'{m[i,j]:.2f}',ha='center',va='center',color='white' if abs(m[i,j])>.65 else 'black')
    ax.set_title('Relaciones entre entradas climáticas\n138 parcelas · no determina qué ventana usar')
    fig.colorbar(im,ax=ax,label='Pearson descriptivo')
    fig.savefig(salida/'correlaciones_clima.png',dpi=160)
    plt.close(fig)


def generar(raiz, salida, con_figuras=False):
    raiz, salida = Path(raiz).resolve(), Path(salida).resolve()
    exigir(salida.is_relative_to(raiz / 'reports') and salida != raiz / 'reports',
           'La salida debe ser una carpeta nueva dentro de reports/')
    exigir(not salida.exists(), 'La salida ya existe; conservar evidencia anterior')
    if con_figuras:
        try:
            import matplotlib
        except ImportError as exc:
            raise ValueError('Las figuras requieren matplotlib del entorno común; ejecutar sin --figuras para las tablas') from exc
    fuentes = sorted((raiz / 'registro/t07').iterdir()) + [raiz / 'registro/t03/particiones.csv']
    hashes = {str(p.relative_to(raiz)): sha(p) for p in fuentes}
    d, dic, contrato = cargar(raiz)
    roles = {r['columna']: r['funcion'] for r in dic}
    candidatas = [c for c in contrato['columnas_por_funcion']['predictor_candidato']
                  if pd.api.types.is_numeric_dtype(d[c])]
    entr = d[d.conjunto_origen.eq('ENTRENAMIENTO')]
    correlaciones = []
    for i, x in enumerate(candidatas):
        for y in candidatas[i+1:]:
            a = entr[[x, y]].dropna()
            correlaciones.append(dict(x=x, y=y, n=len(a), pearson=pearson(a[x], a[y]),
                                      pearson_dentro_municipio=relacion(entr,x,y)['pearson_dentro_municipio']))
    municipios = []
    for _, g in entr.groupby('municipio', sort=True):
        # Token local estable: los agregados no publican identificadores geográficos.
        token = 'municipio_' + hashlib.sha256(str(g.municipio.iloc[0]).encode()).hexdigest()[:8]
        for c in CLIMA:
            municipios.append(dict(grupo=token, columna=c, n=len(g),
                                    n_menor_5=len(g) < 5, x_distintos=g[c].nunique(),
                                    y_distintos=g[OBJETIVO].nunique(), pearson=pearson(g[c], g[OBJETIVO])))
    perfil_clima = []
    for nombre, a in [('total', d), ('etiquetadas', entr), ('reservadas', d[d.conjunto_origen.eq('PREDICCION')])]:
        for w in ('abr_oct', 'jun_oct', 'ambas'):
            cols = CLIMA if w == 'ambas' else [c for c in CLIMA if c.endswith(w)]
            exactos = a.groupby(cols, dropna=False).size()
            redondeados = a[cols].round(6).drop_duplicates()
            perfil_clima.append(dict(poblacion=nombre, ventana=w, n=len(a),
                                      perfiles_exactos=len(exactos), perfiles_redondeados_6=len(redondeados),
                                      grupo_exacto_mas_grande=int(exactos.max())))
    # Diagnóstico de soporte en entrenamientos externos: no ajusta ni cambia particiones.
    part = pd.read_csv(raiz / 'registro/t03/particiones.csv')
    exigir(len(part) == 690 and not part.duplicated(['ID_POLIGONO', 'repeticion']).any(),
           'Particiones incompletas o duplicadas')
    exigir(set(part.ID_POLIGONO) == set(entr.id_parcela), 'IDs de particiones distintos')
    exigir(part.repeticion.nunique() == 5, 'Se requieren cinco repeticiones')
    entrenamientos = []
    for esc, col in [('A', 'particion_principal'), ('B', 'particion_espacial')]:
        for rep, bloque in part.groupby('repeticion'):
            exigir(len(bloque) == 138, 'Repetición incompleta')
            exigir(bloque[col].notna().all() and bloque[col].nunique() == 5, 'Se requieren cinco particiones')
            for fold in sorted(bloque[col].unique()):
                ids = bloque.loc[bloque[col] != fold, 'ID_POLIGONO']
                tr = entr[entr.id_parcela.isin(ids)]
                for c in CLIMA:
                    entrenamientos.append(dict(escenario=esc, repeticion=rep, particion=fold,
                                                columna=c, n=len(tr), **{k:v for k,v in relacion(tr,c,OBJETIVO).items() if k != 'n'}))
    tablas = {'perfil_columnas.csv': perfiles(d, dic), 'pares_ventanas.csv': ventanas(d, roles),
              'pearson_entradas_etiquetadas.csv': pd.DataFrame(correlaciones),
              'clima_rendimiento.csv': clima_objetivo(d),
              'clima_por_municipio.csv': pd.DataFrame(municipios),
              'soporte_reservadas.csv': soporte(d), 'perfiles_climaticos.csv': pd.DataFrame(perfil_clima),
              'clima_entrenamientos_externos.csv': pd.DataFrame(entrenamientos)}
    exigir(hashes == {p: sha(raiz / p) for p in hashes}, 'Las entradas cambiaron durante el diagnóstico')
    salida.mkdir(parents=True)
    for nombre, tabla in tablas.items():
        tabla.to_csv(salida / nombre, index=False, lineterminator='\n', float_format='%.12g')
    nombres = list(tablas)
    if con_figuras:
        figuras(d, salida)
        nombres += ['clima_abr_oct.png','correlaciones_clima.png']
    info = dict(schema=VERSION, poblacion=197, etiquetas=138, reservadas=59, columnas=60,
                cobertura='tabla completa; sin muestreo ni truncamiento',
                exploratorio=True, selecciona_atributos=False, entrena_modelos=False,
                candidatas_numericas=len(candidatas),
                candidatas_categoricas=[c for c in contrato['columnas_por_funcion']['predictor_candidato'] if c not in candidatas],
                semilla=None, p_valores=False, ks='D descriptivo; empates y dependencia espacial',
                centrar_municipio='sólo para diagnóstico descriptivo, nunca exportado como entrada al modelo',
                preparacion_T09=True, T09_implementada=False, validacion_docker='pendiente entorno común de Jass',
                figuras_incluidas=con_figuras,
                git_base=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=raiz, text=True).strip(),
                versiones=dict(python=platform.python_version(), sistema=platform.system(),
                               arquitectura=platform.machine(), numpy=np.__version__, pandas=pd.__version__),
                fuentes_sha256=hashes, script_sha256=sha(Path(__file__)),
                resultados_sha256={n: sha(salida/n) for n in nombres})
    (salida/'manifest.json').write_text(json.dumps(info, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
    return info


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--raiz', type=Path, default=RAIZ)
    ap.add_argument('--salida', type=Path, required=True)
    ap.add_argument('--figuras', action='store_true', help='Añadir figuras; requiere matplotlib')
    args = ap.parse_args()
    r = generar(args.raiz, args.salida, args.figuras)
    print(json.dumps({k:r[k] for k in ('schema', 'poblacion', 'etiquetas', 'reservadas', 'selecciona_atributos', 'entrena_modelos')}, ensure_ascii=False))
