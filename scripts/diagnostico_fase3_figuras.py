"""Figuras científicas de fase3; sin tiles externos ni imágenes inventadas."""
from pathlib import Path
import textwrap
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.colors import TwoSlopeNorm
from matplotlib.ticker import NullFormatter
from PIL import Image
from shapely.affinity import translate

from scripts import diagnostico_fase3 as f3


def save(fig,out,name):
    fig.savefig(out/(name+'.png'),dpi=120,facecolor='white')
    fig.savefig(out/(name+'.pdf'),metadata={'CreationDate':None,'ModDate':None})
    plt.close(fig)


def curva(ax,record,sensor):
    raw,valid,row=record
    start=pd.Timestamp('2025-04-01');end=pd.Timestamp('2025-12-31');cut=f3.END
    all2025=raw.loc[(raw.f>=start)&(raw.f<=end)&raw.ndvi_promedio.notna()]
    excluded=all2025.loc[(all2025.f<=cut)&~all2025.index.isin(valid.index)]
    post=all2025.loc[all2025.f>cut]
    ax.axvspan(cut,end,color='.92',label='posterior: sólo diagnóstico')
    ax.scatter(excluded.f,excluded.ndvi_promedio,c='.6',s=13,marker='x',label='excluidas por T06')
    ax.scatter(valid.f,valid.ndvi_promedio,c='#16697a',s=13,label='válidas')
    ax.plot(valid.f,f3.suavizar(valid.ndvi_promedio.to_list()),c='#16697a',lw=1.1,label='mediana móvil T06')
    ax.scatter(post.f,post.ndvi_promedio,c='#884488',s=10,marker='x')
    ax.axvline(cut,color='.25',ls='--',lw=.8)
    gaps=valid.f.diff().dt.days
    if len(valid)>1:
        k=int(np.argmax(gaps.fillna(0).to_numpy()))
        ax.axvspan(valid.f.iloc[k-1],valid.f.iloc[k],color='#efb366',alpha=.18)
    for key,color in [('fecha_inicio','#6f8b3c'),('fecha_pico','#cf7b22'),('fecha_final','#644c92')]:
        if row[key]:ax.axvline(pd.Timestamp(row[key]),color=color,lw=.6,ls=':')
    ax.set_ylim(-.05,1.02);ax.set_xlim(start,end)
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2));ax.xaxis.set_major_formatter(mdates.DateFormatter('%b'))
    ax.set_ylabel('NDVI, sin unidad');ax.grid(alpha=.15)
    ax.set_title(f"{sensor}: {len(valid)} válidas · hueco {row['hueco_max_dias']} d · final {('sí' if row['final_observado'] else 'no')}",fontsize=10)


def crear(out,g,pm,cells,records,quality,errors,table):
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,'axes.spines.top':False,'axes.spines.right':False})
    q=f3.index(quality); e={(r['escenario'],r['poblacion'],r['id_parcela']):r for r in errors}
    pairs=f3.lectura('registro/diagnostico/fase0/controles_preseleccionados.csv')
    for order,pair in enumerate(pairs,1):
        ids=[pair['caso'],pair['control']]
        fig=plt.figure(figsize=(12,15));gs=fig.add_gridspec(5,2,height_ratios=[2.2,1.2,1.5,1.5,1.45],hspace=.45,wspace=.28)
        fig.suptitle(f"{order:02d} · Caso {ids[0]} y control fijado {ids[1]}"+(' · fallo compartido' if order<=4 else ''),fontsize=15,y=.985)
        for col,pid in enumerate(ids):
            role='CASO' if col==0 else 'CONTROL';r=q[pid];t=table[pid];er=e[('A','sin_respaldo',pid)];eb=e[('B','sin_respaldo',pid)]
            ax=fig.add_subplot(gs[0,col])
            img=Image.open(f3.RAIZ/(f3.ATLAS+pid+'/'+pid+'_esri.jpg'))
            ax.imshow(img);ax.axis('off')
            ax.set_title(f"{role} {pid} · {t['municipio']} · contorno {r['contorno_categoria']}\nAtlas Esri local; fecha de imagen no documentada",fontsize=11)
            ax=fig.add_subplot(gs[1,col]);poly=pm.loc[pid].geometry;center=poly.centroid
            span=max(poly.bounds[2]-poly.bounds[0],poly.bounds[3]-poly.bounds[1])*1.25
            bounds=(center.x-span/2,center.y-span/2,center.x+span/2,center.y+span/2)
            near=pm.loc[pm.intersects(f3.box(*bounds))]
            near=near.copy();near.geometry=near.geometry.map(lambda v:translate(v,-center.x,-center.y))
            near.boundary.plot(ax=ax,color='.7',lw=.7)
            import geopandas as gpd
            gpd.GeoSeries([translate(poly,-center.x,-center.y)],crs=6372).boundary.plot(ax=ax,color='#bd3846' if not col else '#16697a',lw=1.4)
            key=r['celda_principal'];c=cells[key][1]
            import geopandas as gpd
            gpd.GeoSeries([translate(c,-center.x,-center.y)],crs=6372).boundary.plot(ax=ax,color='#9c7721',lw=1)
            ax.set_xlim(-span/2,span/2);ax.set_ylim(-span/2,span/2);ax.set_aspect('equal')
            ax.ticklabel_format(style='plain',useOffset=False)
            ax.set_xlabel('Este relativo al centro, m',fontsize=7);ax.set_ylabel('Norte relativo, m',fontsize=7)
            ax.tick_params(labelsize=7)
            ax.set_title(f"Geometría en metros · celda {key} · fracción {r['fraccion_celda_principal']:.4f}",fontsize=9)
            # Reference square sizes, not a reconstruction of the unknown acquisition grid.
            x=-span/2+span*.07;y=-span/2+span*.09
            for size,color in [(10,'#16697a'),(3,'#bd3846')]:
                ax.add_patch(plt.Rectangle((x,y),size,size,fill=False,color=color,lw=1));x+=span*.1
            ax.text(.02,.96,'Cuadros 10 m y 3 m: escala nominal; no píxeles reales',transform=ax.transAxes,va='top',fontsize=7)
            for row,sensor in [(2,'Planet'),(3,'Sentinel-2')]:
                ax=fig.add_subplot(gs[row,col]);curva(ax,records[(pid,sensor,'abr_oct')],sensor)
                if row==3 and col==0:ax.legend(fontsize=6,loc='lower left',ncol=2)
            ax=fig.add_subplot(gs[4,col]);ax.axis('off')
            bval=eb['mae'] if eb['mae'] else 'ausente'
            lines=[f"Rendimiento: {t['rendimiento_t_ha']} t/ha · área declarada {r['area_ha_origen']:.2f} ha",
                f"MAE A {float(er['mae']):.3f} · sesgo A {float(er['sesgo']):+.3f} · MAE B {float(bval):.3f}" if bval!='ausente' else 'Sin evaluación municipal B',
                f"B: {eb['n_elegibles']}/5 registros municipales; respaldos separados en tablas",
                f"Ancho rectángulo: {r['ancho_rectangulo_m']:.1f} m · nube/píxeles válidos: sin máscara original",
                f"Cobertura elevación {r['elevacion_cobertura']:.3f} / pendiente {r['pendiente_cobertura']:.3f}",
                f"Clima mínimo 2025 hasta oct: {r['cobertura_clima_min_2025_ene_oct']:.3f} · celdas {r['celdas_tocadas']}",
                f"Vecinas etiquetadas <20 m: {r['n_vecinas_etiquetadas']} (sólo auditoría)",
                'Nota atlas: '+r['nota_contorno']]
            wrapped='\n'.join(textwrap.fill(s,84) for s in lines)
            ax.text(0,1,wrapped,va='top',fontsize=8.5,linespacing=1.35)
        fig.text(.04,.02,'Mismos ejes NDVI en 20 parcelas. Sombra naranja = mayor hueco interno; líneas punteadas = rasgos observables T06.\nNo equivalen a siembra/cosecha. Curvas conectadas entre capturas; ningún dato posterior entra en el resumen.\nEl control es el mejor disponible según fase0, no una equivalencia causal ni un caso elegido por su error.',fontsize=8)
        save(fig,out,f'ficha_{order:02d}_{ids[0]}')
    mapas(out,g,cells,e,table,pairs)
    calidad_error(out,q,e,pairs)


def mapas(out,g,cells,e,table,pairs):
    ids=sorted(pid for pid in table if table[pid]['rendimiento_t_ha'])
    # These are the original T02 angular centroids for display, never metric distances.
    pts=g.loc[ids].geometry.map(lambda p:p.centroid)
    fig,axes=plt.subplots(2,2,figsize=(13,11),layout='constrained')
    norm=TwoSlopeNorm(vmin=-2.5,vcenter=0,vmax=2.5)
    caseids=[r['caso'] for r in pairs]
    for col,esc in enumerate(('A','B')):
        for row in (0,1):
            ax=axes[row,col]
            for shape,_ in cells.values():
                x,y=shape.exterior.xy;ax.plot(x,y,c='.85',lw=.6)
            vals=[float(e[(esc,'todas',pid)]['sesgo']) for pid in ids]
            sc=ax.scatter(pts.x,pts.y,c=vals,cmap='RdBu_r',norm=norm,s=24,zorder=2,linewidth=0)
            for pid in caseids:
                p=pts.loc[pid];ax.scatter(p.x,p.y,s=65,facecolors='none',edgecolors='black',lw=.8,zorder=3)
                if row:ax.annotate(pid,(p.x,p.y),xytext=(3,4),textcoords='offset points',fontsize=6)
            if row:
                ps=[pts.loc[p] for p in ids if table[p]['municipio']=='Chignahuapan']
                ax.set_xlim(min(p.x for p in ps)-.018,max(p.x for p in ps)+.018);ax.set_ylim(min(p.y for p in ps)-.015,max(p.y for p in ps)+.015)
            else:
                ax.set_xlim(pts.x.min()-.05,pts.x.max()+.05);ax.set_ylim(pts.y.min()-.04,pts.y.max()+.04)
            ax.set_title(f"Escenario {esc} · {'Chignahuapan' if row else '138 parcelas, todos los respaldos'}")
            ax.set_xlabel('Longitud WGS84 (grados)');ax.set_ylabel('Latitud WGS84 (grados)');ax.set_aspect('equal')
    fig.colorbar(sc,ax=axes,label='Sesgo medio OOF = predicción − rendimiento, t/ha',shrink=.7)
    fig.suptitle('Errores de T08 y soporte CHIRPS: colores fijos A/B; círculos = casos congelados\nRejilla compartida ≠ causa del error; proximidad ≠ independencia',fontsize=13)
    save(fig,out,'mapas_error_A_B')


def calidad_error(out,q,e,pairs):
    # Fixed library defaults: same layout alone and after the dossier figures.
    plt.rcdefaults()
    fields=[('area_ha_origen','Área declarada, ha'),('pl_capturas_validas','Planet: capturas válidas'),
        ('pl_hueco_max_dias','Planet: hueco máximo, días'),('s2_hueco_max_dias','Sentinel-2: hueco máximo, días'),
        ('pl_ndvi_std_en_maximo','Planet: STD NDVI en torno al máximo'),('ancho_rectangulo_m','Ancho rectángulo, m')]
    fig,axes=plt.subplots(2,3,figsize=(13,8),layout='constrained')
    cases={r['caso'] for r in pairs};controls={r['control'] for r in pairs}
    for ax,(col,label) in zip(axes.flat,fields):
        for role,color,marker in [('resto','.65','o'),('control','#16697a','s'),('caso','#bd3846','^')]:
            ids=[pid for pid in q if ('A','todas',pid) in e and (pid in cases if role=='caso' else pid in controls if role=='control' else pid not in cases|controls)]
            ax.scatter([q[p][col] for p in ids],[float(e[('A','todas',p)]['mae']) for p in ids],s=24,c=color,marker=marker,label=role,alpha=.75)
        if col in ('area_ha_origen','ancho_rectangulo_m'):
            ax.set_xscale('log');ax.xaxis.set_minor_formatter(NullFormatter())
        ax.set_xlabel(label);ax.set_ylabel('MAE medio por ID, t/ha');ax.grid(alpha=.15)
    axes[0,0].legend(fontsize=8)
    fig.suptitle('Calidad frente al error: todas las 138 etiquetas, sin descartar casos\nRelaciones exploratorias; municipio y selección de casos pueden confundirlas',fontsize=13)
    save(fig,out,'calidad_error_138')
