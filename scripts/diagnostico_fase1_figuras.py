"""Figuras científicas descriptivas; todos los puntos proceden de T08 OOF."""
from pathlib import Path
import os

os.environ.setdefault('MPLCONFIGDIR', '/tmp/agrocebada_mpl_fase1')
os.environ.setdefault('SOURCE_DATE_EPOCH', '1791849600')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np

COLORES = {'municipio': '#176B8A', 'grupo': '#D17A15', 'global': '#7256A0'}
NOMBRES = {'municipio': 'Referencia municipal', 'grupo': 'Respaldo por grupo', 'global': 'Respaldo global'}
ROJO = '#AC2942'


def guardar(fig, dest, nombre, nota, estabilidad=False):
    fig.text(.02, .025, nota, ha='left', va='bottom', fontsize=9, color='#444444')
    fig.subplots_adjust(left=.08, right=.89 if estabilidad else .97, bottom=.18, top=.78,
                        wspace=.6 if estabilidad else .24)
    for ax in fig.axes:
        ax.spines[['top', 'right']].set_visible(False)
        ax.grid(alpha=.16, zorder=0)
    fig.savefig(Path(dest) / (nombre + '.png'), dpi=170, facecolor='white')
    fig.savefig(Path(dest) / (nombre + '.pdf'), metadata={'CreationDate': None, 'ModDate': None})
    plt.close(fig)


def crear(tables, cases, dest):
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10, 'axes.titlesize': 12,
                         'axes.labelsize': 11, 'pdf.fonttype': 42})
    rows = tables['errores_por_repeticion.csv']; ps = tables['errores_por_parcela.csv']
    mids = tables['resumen_metricas.csv']; ids = [c['id_parcela'] for c in cases]
    for signed, name, title in [(False, 'observado_frente_predicho', 'Referencia T08 · observado frente a predicho'),
                                (True, 'error_firmado_frente_prediccion', 'Referencia T08 · dirección del error')]:
        fig, axes = plt.subplots(1, 2, figsize=(12, 6.5), sharex=True, sharey=True)
        fig.suptitle(title, x=.08, ha='left', fontsize=16, y=.97)
        for esc, ax in zip(('A', 'B'), axes):
            rr = [r for r in rows if r['escenario'] == esc]
            for src in COLORES:
                ss = [r for r in rr if r['fuente_referencia'] == src]
                if not ss:
                    continue
                ax.scatter([r['prediccion'] if signed else r['real'] for r in ss],
                           [r['error_firmado'] if signed else r['prediccion'] for r in ss],
                           s=19, color=COLORES[src], alpha=.4, linewidths=0)
            ss = [r for r in rr if r['id_parcela'] in ids]
            ax.scatter([r['prediccion'] if signed else r['real'] for r in ss],
                       [r['error_firmado'] if signed else r['prediccion'] for r in ss],
                       s=34, facecolors='none', edgecolors=ROJO, linewidths=.65)
            if signed:
                ax.axhline(0, color='#333333', lw=1, linestyle='--')
                ax.set_xlabel('Predicción OOF (t/ha)'); ax.set_ylabel('Predicción − real (t/ha)')
            else:
                ax.set_xlabel('Rendimiento observado (t/ha)'); ax.set_ylabel('Predicción OOF (t/ha)')
                allvals = [r[k] for r in rows for k in ('real', 'prediccion')]
                lo, hi = min(allvals) - .2, max(allvals) + .2
                ax.plot([lo, hi], [lo, hi], color='#333333', lw=1, linestyle='--')
                ax.set_xlim(lo, hi); ax.set_ylim(lo, hi)
            counts = {s: sum(r['fuente_referencia'] == s for r in rr) for s in COLORES}
            ax.set_title(f'{esc} · 138 parcelas / 690 registros\n{counts["municipio"]} municipales + {690-counts["municipio"]} con respaldo', loc='left')
        handles = [Line2D([], [], marker='o', linestyle='', color=c, label=NOMBRES[s]) for s, c in COLORES.items()
                   if any(r['fuente_referencia'] == s for r in rows)]
        handles.append(Line2D([], [], marker='o', linestyle='', markerfacecolor='none', markeredgecolor=ROJO, label='Diez casos fijados en A'))
        fig.legend(handles=handles, loc='upper left', bbox_to_anchor=(.07, .93), ncols=3, frameon=False, fontsize=9)
        guardar(fig, dest, name, 'T08-v1 · cinco repeticiones por parcela, sin independencia entre ellas. Todos los puntos son OOF.\n'
                + ('Positivo = sobreestima; negativo = subestima. No se ajustó una calibración.' if signed else 'La diagonal indica predicción exacta. El contorno rojo no es un criterio de exclusión.'))
    fig, axes = plt.subplots(1, 2, figsize=(12, 6.5), sharex=True, sharey=True)
    fig.suptitle('Referencia T08 · distribución de la magnitud del error', x=.08, ha='left', fontsize=16, y=.97)
    for esc, ax in zip(('A', 'B'), axes):
        for pop, color, style in [('todas', '#555555', '-'), ('sin_respaldo', COLORES['municipio'], '-'),
                                  ('con_respaldo', COLORES['grupo'], '--')]:
            ss = [r for r in ps if r['escenario'] == esc and r['poblacion'] == pop and r['n_elegibles']]
            if not ss:
                continue
            xx = np.sort([r['mae'] for r in ss]); yy = np.arange(1, len(xx) + 1) / len(xx)
            label = {'todas': 'Todas', 'sin_respaldo': 'Sin respaldo', 'con_respaldo': 'Con respaldo'}[pop]
            ax.step(np.r_[0, xx], np.r_[0, yy], where='post', color=color, linestyle=style,
                    label=f'{label} · {len(ss)} parcelas')
        m = next(r for r in mids if r['escenario'] == esc and r['poblacion'] == 'sin_respaldo')
        ax.set_title(f'{esc} · sin respaldo\nmediana {m["mediana_mae_parcela"]:.3f} · p90 {m["p90_mae_parcela"]:.3f} t/ha', loc='left')
        ax.set_xlabel('Promedio del error absoluto por parcela (t/ha)'); ax.set_ylabel('Fracción acumulada de parcelas')
        ax.set_ylim(0, 1.04); ax.legend(frameon=False, fontsize=9, loc='lower right')
    guardar(fig, dest, 'distribucion_error_absoluto', 'T08-v1 · cada parcela elegible pesa una vez en cada curva; el error se calcula antes de promediar.\n'
            'En B una parcela puede aparecer en ambas máscaras en repeticiones distintas; no son grupos disjuntos de IDs.')
    fig, axes = plt.subplots(1, 2, figsize=(12, 7.8), sharex=True, sharey=True)
    fig.suptitle('Diez casos fijados · estabilidad del error de T08', x=.08, ha='left', fontsize=16, y=.97)
    for esc, ax in zip(('A', 'B'), axes):
        rr = [r for r in rows if r['escenario'] == esc and r['id_parcela'] in ids]
        for j, pid in enumerate(ids):
            ss = [r for r in rr if r['id_parcela'] == pid]
            es = [r['error_firmado'] for r in ss]
            ax.plot([min(es), max(es)], [j, j], color='#888888', lw=1.3)
            for r in ss:
                ax.scatter(r['error_firmado'], j + (r['repeticion'] - 3) * .045,
                           color=COLORES[r['fuente_referencia']], s=24, zorder=3)
            p = next(r for r in ps if r['escenario'] == esc and r['poblacion'] == 'sin_respaldo' and r['id_parcela'] == pid)
            ax.text(1.01, j, f'{p["n_elegibles"]}/5 · {p["apariciones_top10"]}/{p["n_elegibles"]}',
                    transform=ax.get_yaxis_transform(), fontsize=9, va='center')
        ax.set_title(f'{esc} · elegibles / 5 y top10 / elegibles →', loc='left', fontsize=11)
        ax.axvline(0, lw=1, color='#333333', linestyle='--'); ax.set_xlabel('Predicción − real (t/ha)')
        ax.set_yticks(range(10), labels=ids); ax.set_ylim(9.7, -.7)
    # Más espacio a la derecha de cada eje para los denominadores de B.
    fig.text(.08, .9, 'Puntos azules: referencia municipal. Naranjas: respaldo por grupo. Línea: mínimo–máximo de las cinco repeticiones.', fontsize=9)
    guardar(fig, dest, 'estabilidad_casos_repeticiones', 'T08-v1 · la aparición top10 se calcula por repetición en sin_respaldo, con desempate por ID.\n'
            'Los casos mantienen el orden fijado en A. Los rangos son sensibilidad al entrenamiento; no intervalos predictivos.', estabilidad=True)
