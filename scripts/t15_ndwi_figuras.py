"""Figuras de QA D.1 con casos/controles fijados antes; no lee rendimientos."""
import argparse
from datetime import date,datetime,timedelta
from pathlib import Path
from statistics import median
import os
import tempfile

os.environ.setdefault('MPLCONFIGDIR',str(Path(tempfile.gettempdir())/'agrocebada_d1_mpl'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from scripts.t15_ndwi_factibilidad import ROOT,read_csv,catalogue,observations,csv_write


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--salida',type=Path,required=True)
    ap.add_argument('--figuras',type=Path,required=True)
    a=ap.parse_args()
    if a.figuras.exists():raise FileExistsError('Usar directorio de figuras nuevo')
    a.figuras.mkdir(parents=True)
    profiles=read_csv(a.salida/'perfil_ndwi_postpico.csv')
    data={r['id_parcela']:r for r in profiles if r['ventana']=='abr_oct'}
    meta=catalogue(read_csv(ROOT/'registro/t07/catalogo_base.csv'))
    groups,_=observations(ROOT/'data/raw/DATASET_RETO_AGRO_2026/Conjunto_datos_BASICO_AgroCebada2026.csv',meta)
    pairs=read_csv(ROOT/'registro/t15_d1/casos_controles_fijos.csv')
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,
                         'axes.spines.right':False,'axes.titleweight':'bold'})
    green='#246A52';blue='#2466A3';gold='#D0AA4E'
    plotted_ids={r[k] for r in pairs for k in ['caso','control']}
    plotted_values=[v for pid in plotted_ids for o in groups[pid]
                    if date(2025,4,1)<=o.fecha<=date(2025,10,31) and o.ndvi is not None
                    and o.nube is not None and o.nube<=5 for v in [o.ndvi,o.ndwi] if v is not None]
    ymin,ymax=min(plotted_values)-.04,max(plotted_values)+.04
    fig,axes=plt.subplots(4,2,figsize=(13,13.8),sharex=True)
    qa=[]
    for i,pair in enumerate(pairs):
        for j,(role,pid) in enumerate([('Caso fijo',pair['caso']),('Control fijo',pair['control'])]):
            ax=axes[i,j];r=data[pid]
            seq=[o for o in groups[pid] if date(2025,4,1)<=o.fecha<=date(2025,10,31)
                 and o.ndvi is not None and o.nube is not None and o.nube<=5]
            sm=[median([o.ndvi for o in seq[max(0,k-1):k+2]]) for k in range(len(seq))]
            peak=date.fromisoformat(r['fecha_maximo'])
            ax.plot([o.fecha for o in seq],sm,color=green,lw=1.7,label='NDVI: mediana de 3 capturas')
            water=[o for o in seq if o.ndwi is not None]
            ax.plot([o.fecha for o in water],[o.ndwi for o in water],color=blue,marker='.',ms=5,lw=1.1,
                    label='NDWI observado')
            postdates=set(r['fechas_post'].split(';'))
            selected=[o for o in water if o.fecha.isoformat() in postdates]
            if selected:ax.scatter([o.fecha for o in selected],[o.ndwi for o in selected],s=36,
                                    facecolors='white',edgecolors=blue,zorder=5)
            left=peak+timedelta(days=15);right=min(peak+timedelta(days=45),date(2025,10,31))
            if left<=right:ax.axvspan(left,right,color=gold,alpha=.2,label='Intervalo posterior hasta el corte')
            ax.axvline(peak,color='#666666',lw=.8,ls='--')
            ax.scatter([peak],[float(r['ndwi_ancla'])],color=blue,s=40,marker='D',zorder=6)
            val=f"{float(r['contraste_ndwi']):+.4f}" if r['contraste_ndwi'] else 'ausente'
            quality='; intervalo truncado' if r['intervalo_truncado']=='True' else ''
            ax.set_title(f'{role} {pid} · {r["municipio"]}',fontsize=10,loc='left')
            ax.text(.02,.04,f'Δ NDWI: {val} · n={r["n_fechas_post"]} fechas{quality}',
                    transform=ax.transAxes,fontsize=9,va='bottom',bbox=dict(facecolor='white',alpha=.85,edgecolor='none'))
            ax.set_ylim(ymin,ymax);ax.set_xlim(date(2025,4,1),date(2025,10,31))
            ax.grid(alpha=.17);ax.xaxis.set_major_locator(mdates.MonthLocator())
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%Y'))
            if j==0:ax.set_ylabel('Índice adimensional')
            qa.append(dict(caso=pair['caso'],id_parcela=pid,rol=role,ventana='abr_oct',fecha_maximo=r['fecha_maximo'],
                           n_fechas_post=r['n_fechas_post'],contraste_ndwi=r['contraste_ndwi'],
                           intervalo_truncado=r['intervalo_truncado'],motivo=r['motivo'],
                           seleccion='fija_F0_antes_D1_no_por_contraste_ni_rendimiento'))
    handles,labels=axes[0,0].get_legend_handles_labels()
    fig.suptitle('D.1 · Revisión temporal de los cuatro casos compartidos y sus controles',fontsize=15,x=.06,ha='left',y=.985)
    fig.legend(handles,labels,loc='upper left',bbox_to_anchor=(.055,.968),ncol=3,frameon=False,fontsize=9)
    fig.text(.06,.015,'Ancla: primera fecha del máximo NDVI. Círculos: NDWI usados entre +15 y +45 días. Corte: 31-oct-2025.\n'
             'Líneas unen observaciones; no rellenan fechas. No confirman daño, cosecha o etapa agronómica. Sin etiquetas ni errores.',fontsize=9)
    fig.subplots_adjust(top=.92,bottom=.07,left=.06,right=.98,hspace=.30,wspace=.15)
    fig.savefig(a.figuras/'casos_controles_ndwi.png',dpi=160,facecolor='white');plt.close(fig)
    csv_write(a.figuras/'revision_visual_casos_controles.csv',qa)

    fig,axes=plt.subplots(1,2,figsize=(12,5.2))
    summary={r['categoria']:r for r in read_csv(a.salida/'resumen_conjunto.csv') if r['ventana']=='abr_oct'}
    cats=['ENTRENAMIENTO','PREDICCION'];good=[int(summary[c]['n_calculables']) for c in cats]
    bad=[int(summary[c]['n_ausentes']) for c in cats]
    axes[0].barh([0,1],good,color=green,label='Calculable')
    axes[0].barh([0,1],bad,left=good,color='#D6AB55',label='Sin dos fechas posteriores válidas')
    for i,(g,b) in enumerate(zip(good,bad)):
        axes[0].text(g/2,i,str(g),ha='center',va='center',color='white',weight='bold')
        axes[0].text(g+b/2,i,str(b),ha='center',va='center',weight='bold')
    axes[0].set_yticks([0,1],['138 etiquetadas','59 reservadas']);axes[0].invert_yaxis()
    axes[0].set_xlabel('Parcelas');axes[0].set_title('Cobertura de la fórmula registrada',loc='left',fontsize=11)
    axes[0].legend(loc='lower left',bbox_to_anchor=(0,-.32),frameon=False,fontsize=9)
    x=[int(r['n_fechas_post']) for r in data.values()]
    axes[1].hist(x,bins=[n-.5 for n in range(max(x)+2)],color=blue,rwidth=.85)
    axes[1].axvline(1.5,color='#A87218',ls='--',lw=1)
    axes[1].set_xlabel('Fechas válidas de NDWI entre +15 y +45 días');axes[1].set_ylabel('Parcelas')
    axes[1].set_title('Soporte: no se inventan las fechas faltantes',loc='left',fontsize=11)
    fig.suptitle('NDWI posterior al máximo · 169 de 197 calculables',fontsize=15,x=.06,ha='left',y=.97)
    fig.text(.06,.045,'Ambas ventanas dan el mismo contraste donde existe. 18 de los 169 cálculos tienen intervalo truncado por el corte.\n'
             'La disponibilidad no demuestra una mejora de MAE. Fuente: series FIRA, umbral Sentinel-2 ≤5 %. Sin entrenamiento.',fontsize=9)
    fig.subplots_adjust(left=.12,right=.98,top=.82,bottom=.26,wspace=.35)
    fig.savefig(a.figuras/'cobertura_ndwi_postpico.png',dpi=160,facecolor='white');plt.close(fig)


if __name__=='__main__':main()
