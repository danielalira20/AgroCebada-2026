"""Figuras descriptivas de históricos, sin oráculo ni incertidumbre inferida."""
from pathlib import Path
from scripts.diagnostico_fase1_figuras import plt, np


def save(fig,dest,name,nota,bottom=.15):
    fig.text(.015,.025,nota,fontsize=9,color='#444444',va='bottom')
    fig.savefig(Path(dest)/(name+'.png'),dpi=150,facecolor='white')
    fig.savefig(Path(dest)/(name+'.pdf'),metadata={'CreationDate':None,'ModDate':None})
    plt.close(fig)


def label(m):
    s=m['candidato']
    s=s.replace('puente_t11_config','puente c').replace('t10_config','T10 c').replace('t11_c','T11 c').replace('ref_mas_','clima ')
    if m['fuente']=='T09':s+=' ['+m['variante']+']'
    return m['serie_id']+' · '+s


def crear(tables,cases,dest):
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'pdf.fonttype':42})
    catalog=tables['catalogo_series.csv'];matrix=tables['matriz_procedimientos_por_caso.csv'];summary=tables['resumen_comparaciones.csv']
    ids=[r['id_parcela'] for r in cases]
    ms=[m for m in catalog if not m['es_referencia'] and m['ambito']!='suplementario']
    look={(r['serie_id'],r['escenario'],r['poblacion'],r['id_parcela']):r for r in matrix}
    fig,axes=plt.subplots(1,2,figsize=(15,12),sharey=True)
    fig.suptitle('Casos fijados · ¿qué procedimientos comparten los errores?',x=.03,ha='left',fontsize=16,y=.98)
    vmax=max(look[m['serie_id'],e,'sin_respaldo',pid]['mae'] for m in ms for e in ('A','B') for pid in ids)
    for e,ax in zip(('A','B'),axes):
        a=np.array([[look[m['serie_id'],e,'sin_respaldo',pid]['mae'] for pid in ids] for m in ms])
        im=ax.imshow(a,aspect='auto',vmin=0,vmax=vmax,cmap='YlOrRd',interpolation='nearest')
        ax.set_xticks(range(10),labels=ids,rotation=55,ha='right',fontsize=9)
        ax.set_yticks(range(len(ms)),labels=[label(m) for m in ms],fontsize=8)
        ax.set_title(e+' · promedio de error absoluto por parcela (t/ha)',loc='left',fontsize=11)
    fig.subplots_adjust(left=.30,right=.92,top=.91,bottom=.16,wspace=.09)
    cax=fig.add_axes([.935,.22,.012,.65]);fig.colorbar(im,cax=cax,label='MAE de parcela (t/ha)')
    save(fig,dest,'errores_compartidos_casos','Históricos T09–T11/T14, versiones en catálogo. Casos/orden fijados en T08 A; sólo registros municipales.\n'
         'Sxxx identifica una serie. No son modelos independientes, ganador por parcela ni efecto causal del bloque. T13/T13e quedan en las tablas suplementarias.')
    colors={'T09':'#247D94','T10':'#CD7937','T11':'#7056A3','T13':'#708A4B','T14':'#AD4465'}
    sm={(r['serie_id'],r['escenario']):r for r in summary if r['poblacion']=='sin_respaldo'}
    fig,ax=plt.subplots(figsize=(9,7))
    fig.suptitle('Cambios de error frente a T08 · A y B',x=.09,ha='left',fontsize=16,y=.98)
    for task,color in colors.items():
        mm=[m for m in catalog if m['fuente']==task and not m['es_referencia']]
        ax.scatter([sm[m['serie_id'],'A']['delta_mae_parcelas'] for m in mm],
                   [sm[m['serie_id'],'B']['delta_mae_parcelas'] for m in mm],s=45,color=color,label=task,alpha=.75)
    active=[m for m in catalog if not m['es_referencia']]
    chosen=set()
    for e in ('A','B'):
        chosen.update([min(active,key=lambda m:sm[m['serie_id'],e]['delta_mae_parcelas'])['serie_id'],
                       max(active,key=lambda m:sm[m['serie_id'],e]['delta_mae_parcelas'])['serie_id']])
    for sid in sorted(chosen):
        a=sm[sid,'A']['delta_mae_parcelas'];b=sm[sid,'B']['delta_mae_parcelas']
        ax.annotate(sid,(a,b),xytext=(5,5),textcoords='offset points',fontsize=9)
    ax.axvline(0,color='#444444',lw=1,linestyle='--');ax.axhline(0,color='#444444',lw=1,linestyle='--')
    ax.set_xlabel('ΔMAE A por parcela (t/ha) · negativo = menor error')
    ax.set_ylabel('ΔMAE B por parcela (t/ha) · negativo = menor error')
    ax.grid(alpha=.15);ax.spines[['top','right']].set_visible(False);ax.legend(frameon=False,fontsize=9)
    fig.subplots_adjust(left=.12,right=.96,top=.9,bottom=.22)
    save(fig,dest,'cambios_A_B','44 candidatos históricos; 135 IDs sin respaldo con sus repeticiones elegibles. Referencias duplicadas excluidas.\n'
         'Cada punto es un procedimiento/versionado; ni una prueba de significación ni una nueva selección T15.\n'
         'T13/T13e son suplementarios; se anotan sólo extremos descriptivos, no se promueven modelos.')
    support=tables['ficha_soporte_municipal.csv'];mun=sorted({r['municipio'] for r in support})
    fig,axes=plt.subplots(1,2,figsize=(12,6.8),sharey=True)
    fig.suptitle('Referencia municipal · sensibilidad a una etiqueta de entrenamiento',x=.04,ha='left',fontsize=15,y=.98)
    for e,ax in zip(('A','B'),axes):
        for j,municipality in enumerate(mun):
            row=next(r for r in support if r['escenario']==e and r['municipio']==municipality and r['fuente_referencia']=='municipio')
            if row['influencia_max_abs']=='':
                ax.text(.015,j,'Sin estimación municipal calculable',transform=ax.get_yaxis_transform(),fontsize=8,va='center',color='#666666')
                continue
            ax.scatter(row['influencia_max_abs'],j,s=35,color='#247D94')
            ax.annotate(f'n={row["n_municipal_min"]}–{row["n_municipal_max"]}',(row['influencia_max_abs'],j),xytext=(5,0),textcoords='offset points',fontsize=8,va='center')
        ax.set_title(e+' · máximo cambio absoluto de la media (t/ha)',loc='left',fontsize=11)
        ax.set_yticks(range(len(mun)),labels=mun,fontsize=9);ax.set_ylim(len(mun)-.4,-.6)
        ax.set_xlabel('|Media sin etiqueta − media| (t/ha)');ax.grid(alpha=.15);ax.spines[['top','right']].set_visible(False)
    x=max(r['influencia_max_abs'] for r in support if r['fuente_referencia']=='municipio' and r['influencia_max_abs']!='')
    for ax in axes:ax.set_xlim(-.02*x,1.5*x)
    fig.subplots_adjust(left=.20,right=.97,top=.87,bottom=.22,wspace=.2)
    save(fig,dest,'influencia_referencia_municipal','n = etiquetas municipales disponibles en entrenamiento externo; máximo sobre contextos y etiquetas de entrenamiento.\n'
         'Comprobación analítica de la media; no elimina parcelas ni reajusta modelos. Un pool unitario queda sin estimación de retiro.\n'
         'Respaldos por grupo/global se conservan por separado en la ficha de soporte.')
