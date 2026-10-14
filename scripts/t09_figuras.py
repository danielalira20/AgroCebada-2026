"""Figuras de T09 v1 a partir de resultados completos, sin entrenar ni elegir modelo.

MAE se resume primero por repetición; ΔMAE se resume primero por parcela.
Las dos cantidades tienen denominadores distintos cuando cambia la elegibilidad.
Los intervalos por celdas describen un contraste de desempeño, no una parcela.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

PROCEDIMIENTOS = ('T', 'CL', 'TC', 'R')
CANDIDATOS = ('TC', 'CL', 'R')
ESCENARIOS = ('A', 'B', 'C')
VENTANAS = ('abr_oct', 'jun_oct')
INTENSIDADES = (0.01, 0.1, 1.0, 10.0)
COLORES = dict(T='#515B66', CL='#0072B2', TC='#D55E00', R='#009E73')
ETIQUETAS = dict(T='Referencia territorial', CL='Clima solo',
                 TC='Territorio + clima', R='Corrección con clima')
ENTRADAS = ('metricas_resumen.csv', 'comparaciones_emparejadas.csv',
            'diferencias_por_parcela.csv', 'seleccion_interna.csv',
            'resultado.json', 'procedencia.json')
VERSION = 'T09-figuras-v1'
SHA_DISENO = '1072e4196df68359fa3728e504f23ec28dd94b637715854a6635d36d4478081f'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _requeridas(tabla, columnas, nombre):
    if tabla.empty or tabla.columns.duplicated().any() or set(columnas) - set(tabla):
        raise ValueError(f'Tabla {nombre} vacía o sin columnas requeridas')


def leer_resultados(entrada):
    """Exige resultados reales completos y conserva la precisión del CSV."""
    entrada = Path(entrada).resolve()
    if not entrada.is_dir() or any(not (entrada/n).is_file() for n in ENTRADAS):
        raise ValueError('Se requiere una carpeta de evaluación completa con sus tablas y procedencia')
    resultado = json.loads((entrada/'resultado.json').read_text(encoding='utf-8'))
    procedencia = json.loads((entrada/'procedencia.json').read_text(encoding='utf-8'))
    if (resultado.get('resultado') != 'evaluacion_completa_pendiente_revision' or
            resultado.get('diseno_sha256') != SHA_DISENO or
            resultado.get('contextos_externos') != 59 or
            resultado.get('ajustes_climaticos') != 6018 or
            resultado.get('reservadas_evaluadas') != 0 or
            resultado.get('ajuste_final_59') is not False or
            resultado.get('ganador_T16') is not None):
        raise ValueError('Las figuras sólo describen la evaluación externa completa de T09 v1')
    huellas = {n: sha(entrada/n) for n in ENTRADAS}
    publicadas = procedencia.get('salidas_sha256', {})
    for n in ENTRADAS[:-1]:
        if huellas[n] != publicadas.get(n):
            raise ValueError('Entrada modificada o ausente de la procedencia: '+n)
    tablas = {n[:-4]: pd.read_csv(entrada/n, float_precision='round_trip')
              for n in ENTRADAS if n.endswith('.csv')}
    m = tablas['metricas_resumen']
    c = tablas['comparaciones_emparejadas']
    d = tablas['diferencias_por_parcela']
    s = tablas['seleccion_interna']
    _requeridas(m, ('escenario', 'variante', 'procedimiento', 'poblacion', 'sensibilidad',
                   'MAE', 'n_repeticiones', 'n_predicciones', 'n_parcelas'), 'métricas')
    _requeridas(c, ('escenario', 'variante', 'poblacion', 'candidato', 'frente_a',
                   'dMAE', 'IC95_celdas_inf', 'IC95_celdas_sup', 'n_celdas',
                   'n_predicciones', 'n_parcelas', 'intervalo'), 'comparaciones')
    _requeridas(d, ('escenario', 'variante', 'poblacion', 'candidato', 'frente_a',
                   'id_parcela', 'd_error_absoluto', 'n_repeticiones_elegibles'), 'diferencias')
    _requeridas(s, ('escenario', 'variante', 'procedimiento', 'repeticion',
                   'particion', 'ventana', 'lambda_reg'), 'selecciones')
    m = m[m.variante.eq('seleccionada') & m.sensibilidad.eq('principal')].copy()
    m = m[((m.escenario.isin(['A', 'B'])) & m.poblacion.eq('sin_respaldo')) |
          (m.escenario.eq('C') & m.poblacion.eq('todas'))]
    if len(m) != 12 or m.duplicated(['escenario', 'procedimiento']).any():
        raise ValueError('Resumen incompleto: se requieren los cuatro procedimientos en A/B/C')
    for esc, nrep, nobs in (('A', 5, 675), ('B', 5, 659), ('C', 1, 138)):
        z = m[m.escenario.eq(esc)]
        if (set(z.procedimiento) != set(PROCEDIMIENTOS) or
                not z.n_repeticiones.eq(nrep).all() or not z.n_predicciones.eq(nobs).all() or
                z.n_parcelas.nunique() != 1):
            raise ValueError('Poblaciones/repeticiones incompletas en '+esc)
    if not np.isfinite(m.MAE).all() or m.MAE.lt(0).any():
        raise ValueError('MAE no finito o negativo')
    c = c[c.escenario.isin(['A', 'B']) & c.variante.eq('seleccionada') &
          c.poblacion.eq('sin_respaldo') & c.frente_a.eq('T') & c.candidato.isin(CANDIDATOS)].copy()
    if len(c) != 6 or c.duplicated(['escenario', 'candidato']).any():
        raise ValueError('Faltan contrastes seleccionados frente a T')
    if (not np.isfinite(c[['dMAE', 'IC95_celdas_inf', 'IC95_celdas_sup']]).all().all() or
            c.IC95_celdas_inf.gt(c.IC95_celdas_sup).any() or c.n_celdas.lt(1).any()):
        raise ValueError('Intervalos por celdas no válidos')
    for r in c.itertuples():
        x = d[d.escenario.eq(r.escenario) & d.variante.eq('seleccionada') &
              d.poblacion.eq('sin_respaldo') & d.candidato.eq(r.candidato) & d.frente_a.eq('T')]
        if (len(x) != r.n_parcelas or x.id_parcela.duplicated().any() or
                int(x.n_repeticiones_elegibles.sum()) != r.n_predicciones or
                not np.isfinite(x.d_error_absoluto).all() or
                not np.isclose(x.d_error_absoluto.mean(), r.dMAE, rtol=0, atol=1e-12)):
            raise ValueError('ΔMAE no coincide con las diferencias medias por parcela')
        principal = r.escenario == 'A' and r.candidato == 'TC'
        esperado = 'principal_predeclarado' if principal else 'nominal_secundario_no_simultaneo'
        if r.intervalo != esperado:
            raise ValueError('Clasificación de intervalo incompatible con diseño v1')
    s = s[s.variante.eq('seleccionada')].copy()
    if (len(s) != 177 or s.duplicated(['escenario', 'procedimiento', 'repeticion', 'particion']).any()
            or set(s.escenario) != set(ESCENARIOS) or set(s.procedimiento) != set(CANDIDATOS)
            or not s.ventana.isin(VENTANAS).all() or not s.lambda_reg.isin(INTENSIDADES).all()):
        raise ValueError('Selección incompleta o menú distinto de ocho configuraciones')
    for esc, n in (('A', 25), ('B', 25), ('C', 9)):
        for proc in CANDIDATOS:
            if len(s[s.escenario.eq(esc) & s.procedimiento.eq(proc)]) != n:
                raise ValueError('Conteo de contextos externos incompatible')
    return dict(metricas=m, comparaciones=c, selecciones=s, huellas=huellas,
                diseno_sha256=resultado['diseno_sha256'], procedencia=procedencia)


def _guardar(fig, salida, nombre):
    fig.savefig(salida/(nombre+'.png'), dpi=200, facecolor='white',
                metadata={'Software': VERSION})
    fig.savefig(salida/(nombre+'.svg'), facecolor='white',
                metadata={'Date': None, 'Creator': VERSION})


def _mae(datos, salida, plt):
    m = datos['metricas']
    fig, axes = plt.subplots(1, 3, figsize=(12.5, 5.6), sharey=True)
    ymax = max(float(m.MAE.max()) * 1.25, .01)
    for ax, esc in zip(axes, ESCENARIOS):
        z = m[m.escenario.eq(esc)].set_index('procedimiento').loc[list(PROCEDIMIENTOS)]
        ax.bar(range(4), z.MAE, color=[COLORES[p] for p in PROCEDIMIENTOS], width=.64)
        for i, value in enumerate(z.MAE):
            ax.text(i, value+ymax*.022, f'{value:.3f}', ha='center', fontsize=10)
        ax.set_xticks(range(4), PROCEDIMIENTOS)
        ax.set_ylim(0, ymax)
        ax.set_axisbelow(True)
        ax.grid(axis='y', color='#DDDDDD', linewidth=.6)
        nparc = int(z.n_parcelas.iloc[0])
        nobs = int(z.n_predicciones.iloc[0])
        poblacion = 'Soporte municipal común' if esc != 'C' else 'Todas las etiquetadas'
        definicion = {'A': 'Particiones estratificadas', 'B': 'Separación por celdas',
                      'C': 'Municipios excluidos'}[esc]
        ax.set_title(f'{esc} · {definicion}\n{poblacion}', fontsize=11)
        ax.set_xlabel(f'{nparc} parcelas · {nobs} predicciones\n'
                      + ('Promedio de 5 repeticiones' if esc != 'C' else 'Una predicción por parcela'), fontsize=9)
        ax.spines[['top', 'right']].set_visible(False)
    axes[0].set_ylabel('Error absoluto medio, MAE (t/ha)')
    fig.suptitle('Error de las predicciones externas · T09 · 2025', fontsize=16, fontweight='bold')
    fig.text(.5, .14, 'T: referencia territorial   ·   CL: clima solo   ·   '
             'TC: territorio + clima   ·   R: corrección con clima', ha='center', fontsize=9)
    fig.text(.5, .09, 'Menor MAE significa menor error. Valores sin redondear en las tablas; '
             'las barras no representan intervalos de incertidumbre.', ha='center', fontsize=9)
    fig.text(.5, .04, 'C es un diagnóstico de municipios nuevos; no elige el procedimiento '
             'para las 59 parcelas reservadas.', ha='center', fontsize=9)
    fig.subplots_adjust(left=.07, right=.985, top=.78, bottom=.29, wspace=.17)
    _guardar(fig, salida, '01_mae_externo')
    plt.close(fig)


def _contrastes(datos, salida, plt):
    c = datos['comparaciones']
    liminf = min(float(c.IC95_celdas_inf.min()), -.01, 0)
    limsup = max(float(c.IC95_celdas_sup.max()), 0)
    margen = max((limsup-liminf)*.13, .008)
    fig, axes = plt.subplots(1, 2, figsize=(12.5, 5.8), sharex=True, sharey=True)
    for ax, esc in zip(axes, ('A', 'B')):
        z = c[c.escenario.eq(esc)].set_index('candidato').loc[list(CANDIDATOS)]
        for i, (proc, r) in enumerate(z.iterrows()):
            # Extremos absolutos: un percentil bootstrap no está obligado a contener el punto.
            ax.hlines(i, r.IC95_celdas_inf, r.IC95_celdas_sup, color=COLORES[proc], linewidth=2)
            ax.vlines([r.IC95_celdas_inf, r.IC95_celdas_sup], i-.065, i+.065,
                      color=COLORES[proc], linewidth=1.2)
            ax.plot(r.dMAE, i, 'o', color=COLORES[proc], markersize=8)
            tipo = 'principal' if esc == 'A' and proc == 'TC' else 'nominal'
            ax.annotate(f'Δ={r.dMAE:+.3f} · {tipo}', (r.dMAE, i),
                        xytext=(0, 15), textcoords='offset points', ha='center', fontsize=9)
        ax.axvline(0, color='#444444', linewidth=1.0)
        if esc == 'A':
            ax.axvline(-.01, color='#888888', linewidth=1.2, linestyle=':')
        ax.set_xlim(liminf-margen, limsup+margen)
        ax.set_yticks(range(3), ['TC frente a T', 'CL frente a T', 'R frente a T'])
        ax.set_ylim(2.45, -.5)
        ax.tick_params(axis='y', labelleft=True)
        ax.set_xlabel('Diferencia del error absoluto medio (t/ha)')
        ax.set_title(f'{esc} · Soporte municipal común\n'
                     f'{int(z.n_parcelas.iloc[0])} parcelas · {int(z.n_celdas.iloc[0])} celdas', fontsize=12)
        ax.grid(axis='x', color='#E5E5E5', linewidth=.6)
        ax.set_axisbelow(True)
        ax.spines[['top', 'right', 'left']].set_visible(False)
    fig.suptitle('Cambio de error frente a la referencia territorial · 2025',
                 fontsize=15, fontweight='bold')
    fig.text(.5, .16, 'Δ < 0: menor error que T. Línea continua: sin cambio. '
             'Línea punteada en A: umbral predefinido −0.01 t/ha.', ha='center', fontsize=9)
    fig.text(.5, .11, 'Cada punto promedia primero las repeticiones elegibles de cada parcela; '
             'los IC95 remuestrean celdas (5,000 réplicas).', ha='center', fontsize=9)
    fig.text(.5, .06, 'TC frente a T en A es el contraste principal. Los demás intervalos son '
             'nominales, no simultáneos; no son intervalos de predicción individuales.', ha='center', fontsize=9)
    fig.subplots_adjust(left=.115, right=.985, top=.77, bottom=.29, wspace=.40)
    _guardar(fig, salida, '02_diferencia_mae_celdas')
    plt.close(fig)


def _selecciones(datos, salida, plt):
    s = datos['selecciones']
    fig, axes = plt.subplots(3, 3, figsize=(12.5, 9.4))
    for row, (esc, n) in enumerate((('A', 25), ('B', 25), ('C', 9))):
        for col, proc in enumerate(CANDIDATOS):
            ax = axes[row, col]
            z = s[s.escenario.eq(esc) & s.procedimiento.eq(proc)]
            tabla = pd.crosstab(z.ventana, z.lambda_reg).reindex(index=VENTANAS,
                                                               columns=INTENSIDADES, fill_value=0)
            imagen = ax.imshow(tabla.to_numpy(), vmin=0, vmax=25, cmap='Blues', aspect='auto')
            for i in range(2):
                for j in range(4):
                    value = int(tabla.iloc[i, j])
                    ax.text(j, i, str(value), ha='center', va='center', fontsize=12,
                            color='white' if value >= 18 else '#111111')
            ax.set_xticks(range(4), ['0.01', '0.1', '1', '10'])
            ax.set_yticks(range(2), ['Abr–Oct', 'Jun–Oct'])
            ax.set_xlabel('Intensidad de regularización λ', fontsize=9)
            ax.set_title(f'{esc} · {proc} · {n} contextos', fontsize=11)
            ax.set_xticks(np.arange(-.5, 4, 1), minor=True)
            ax.set_yticks(np.arange(-.5, 2, 1), minor=True)
            ax.grid(which='minor', color='white', linewidth=1.5)
            ax.tick_params(which='minor', bottom=False, left=False)
            for spine in ax.spines.values():
                spine.set_visible(False)
    colorbar_ax = fig.add_axes([.925, .24, .014, .56])
    fig.colorbar(imagen, cax=colorbar_ax, label='Número de selecciones internas')
    fig.suptitle('Selección interna de ventana e intensidad · T09, 2025',
                 fontsize=15, fontweight='bold', y=.97)
    fig.text(.5, .085, 'CL: clima solo   ·   TC: territorio + clima   ·   R: corrección con clima',
             ha='center', fontsize=10)
    fig.text(.5, .045, 'Cada panel suma 25 contextos en A/B o 9 en C. Frecuencia de selección '
             'no equivale a importancia de una variable ni a evidencia de causalidad.', ha='center', fontsize=9)
    fig.subplots_adjust(left=.08, right=.885, top=.89, bottom=.17, wspace=.35, hspace=.6)
    _guardar(fig, salida, '03_seleccion_interna')
    plt.close(fig)


def generar(entrada, salida):
    datos = leer_resultados(entrada)
    entrada, salida = Path(entrada).resolve(), Path(salida).resolve()
    if salida.exists() or salida == entrada or entrada.is_relative_to(salida):
        raise ValueError('Elegir una carpeta de salida nueva; no reemplazar resultados existentes')
    # El import ocurre sólo después de validar; no escribe caché sobre el repo.
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    salida.mkdir(parents=True)
    estilo = {'font.family': 'DejaVu Sans', 'font.size': 11,
              'axes.titleweight': 'normal', 'svg.fonttype': 'none',
              'svg.hashsalt': VERSION, 'axes.unicode_minus': True}
    with plt.rc_context(estilo):
        _mae(datos, salida, plt)
        _contrastes(datos, salida, plt)
        _selecciones(datos, salida, plt)
    if any(sha(entrada/n) != h for n, h in datos['huellas'].items()):
        raise ValueError('Los resultados cambiaron durante la creación de figuras')
    manifest = dict(schema='agrocebada_t09_figuras_v1', version=VERSION,
                    diseno_sha256=datos['diseno_sha256'], entradas_sha256=datos['huellas'],
                    codigo_sha256=sha(Path(__file__)), matplotlib=matplotlib.__version__,
                    figuras_sha256={p.name: sha(p) for p in sorted(salida.iterdir()) if p.is_file()},
                    datos='evaluacion_externa_real_138_etiquetadas',
                    variante='seleccionada', modelos_ajustados=0, decisiones_nuevas=False,
                    ganador_elegido=False, reservadas_evaluadas=0,
                    mae='media_de_metricas_por_repeticion; sin barras de incertidumbre',
                    delta_mae='media_por_parcela_de_diferencias_medias_en_repeticiones_elegibles',
                    intervalos='IC95_percentiles_por_celda_5000_replicas_semilla_20261006',
                    secundarios='nominales_no_simultaneos; no intervalos individuales',
                    selecciones='conteos_contextos_A25_B25_C9; no importancia ni causalidad',
                    revision_visual='pendiente_inspeccion_de_los_tres_PNG')
    (salida/'manifest_figuras.json').write_text(json.dumps(manifest, ensure_ascii=False,
                                                         indent=2, allow_nan=False)+'\n', encoding='utf-8')
    return salida


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--entrada', type=Path, required=True)
    p.add_argument('--salida', type=Path, required=True)
    args = p.parse_args()
    r = generar(args.entrada, args.salida)
    print(json.dumps(dict(resultado='figuras_generadas_pendientes_revision_visual',
                          ruta=str(r), modelos_ajustados=0), ensure_ascii=False))


if __name__ == '__main__':
    main()
