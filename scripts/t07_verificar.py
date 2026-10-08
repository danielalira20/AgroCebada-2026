"""Contraste independiente T07: Decimal/calendario y conservación literal de fuentes."""
import argparse
import calendar
from collections import Counter
from datetime import date
from decimal import Decimal, localcontext
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.t07_fuentes import BASE, leer_csv, leer_json, sha
from scripts.t07_preparar import RAIZ, T02, comprobar_fuente, comprobar_copia

# Se explicitan aquí para no reutilizar el agregador ni sus constantes de meses.
PERIODOS = {'abr_oct': tuple(f'2025-{m:02d}' for m in range(4,11)),
            'jun_oct': tuple(f'2025-{m:02d}' for m in range(6,11))}
VARIABLES = {'PREC':'prec_acumulada_mm', 'Tmin':'tmin_media_c', 'Tmax':'tmax_media_c'}
TOLERANCIA = Decimal('1e-9')


def exigir(condicion, mensaje):
    if not condicion: raise ValueError(mensaje)


def indexar(filas, clave):
    idx={tuple(r[c] for c in clave):r for r in filas}
    exigir(len(idx)==len(filas), 'Claves duplicadas en salida')
    return idx


def verificar(entrega, clima=None, raiz=RAIZ):
    raiz, entrega=Path(raiz).resolve(), Path(entrega).resolve()
    m=leer_json(entrega/'manifest.json'); inv=leer_json(entrega/'inventario_fuentes.json')
    exigir(m['schema']=='t07_integracion_bloques_v1', 'Manifiesto T07 incompatible')
    exigir(set(m['archivos_sha256'])=={p.name for p in entrega.iterdir()}-{'manifest.json'}, 'Archivos de salida distintos del manifiesto')
    for n,h in m['archivos_sha256'].items(): exigir(sha(entrega/n)==h, f'Huella de salida distinta: {n}')
    for n,h in m['codigo_sha256'].items(): exigir(sha(raiz/n)==h, f'Código distinto de la ejecución: {n}')
    exigir(m['entradas']['base_dev']==inv['base_dev'], 'Bases distintas en inventario y manifiesto')
    for bloque in ('T02','T03','T06'):
        for n,h in inv['bloques'][bloque]['archivos_sha256'].items():
            comprobar_fuente(n,inv['base_dev'],h,raiz)
    _, origen_cat=leer_csv(raiz/T02/'tablas/catalogo_parcelas.csv')
    fuente={r['id_parcela']:r for r in origen_cat}
    cab, tabla=leer_csv(entrega/'tabla_comun.csv'); comun=indexar(tabla,('id_parcela',))
    _, cat=leer_csv(entrega/'catalogo_base.csv'); base=indexar(cat,('id_parcela',))
    exigir(len(comun)==197 and set(comun)==set(base)=={(p,) for p in fuente}, 'Universo de parcelas alterado')
    for pid,r in fuente.items():
        esperado={c:'2025' if c=='campania' else r[c] for c in BASE}
        exigir(base[(pid,)]==esperado, 'Catálogo/etiqueta original alterado')
        exigir(all(comun[(pid,)][c]==v for c,v in esperado.items()), 'Etiqueta o metadato alterado en tabla común')
    nsat,sat=leer_csv(raiz/'registro/t06/variables_satelitales.csv')
    exigir(len(sat)==197, 'Fuente T06 sin universo completo')
    satcols=nsat[1:]
    for r in sat:
        exigir(all(comun[(r['ID_POLIGONO'],)][c]==r[c] for c in satcols), 'Valor satelital alterado en unión')
    _, cobertura=leer_csv(raiz/'registro/t06/cobertura_ventana.csv')
    cv=indexar(cobertura,('ID_POLIGONO','sensor','umbral_nubosidad','ventana'))
    _, calidad_sat=leer_csv(entrega/'calidad_satelite.csv')
    exigir(len(calidad_sat)==1182, 'Calidad T06 incompleta')
    sq=indexar(calidad_sat,('id_parcela','sensor','ventana'))
    _, dsat=leer_csv(raiz/'registro/t06/variables_satelitales_diccionario.csv')
    umbrales={'Planet':'20','Sentinel-2':'5','Landsat':'5'}
    prefijos={'Planet':'pl','Sentinel-2':'s2','Landsat':'ls'}
    for pid in fuente:
        for s,u in umbrales.items():
            for w,meses in PERIODOS.items():
                q=sq[(pid,s,w)]; x=cv[(pid,s,u,w)]
                exigir(q['umbral_nubosidad']==u, 'Umbral satelital cambiado')
                for c in ('capturas','hueco_max_dias','hueco_max_interno_dias','primera','ultima','meses_sin_captura'):
                    exigir(q[c]==x[c], 'Cobertura satelital cambiada')
                dias=sum(calendar.monthrange(2025,int(p[-2:]))[1] for p in meses)
                exigir(int(q['dias_esperados'])==dias, 'Calendario satelital cambiado')
                span=(date.fromisoformat(x['ultima'])-date.fromisoformat(x['primera'])).days if x['primera'] else ''
                exigir(q['dias_entre_primera_y_ultima']==str(span), 'Distancia entre capturas cambiada')
                exigir(q['nubosidad_media']==comun[(pid,)][f'{prefijos[s]}_nubosidad_media_{w}'], 'Nubosidad cambiada')
                faltantes=sorted(d['columna'] for d in dsat if d['sensor']==s and d['ventana']==w and comun[(pid,)][d['columna']]=='')
                exigir(q['variables_ausentes']==';'.join(faltantes), 'Ausencias satelitales no informadas')
                exigir(q['estado']==('valores_ausentes' if faltantes else 'valores_presentes'), 'Estado satelital contradictorio')
    _, dic=leer_csv(entrega/'diccionario_columnas.csv')
    pares={(r['archivo'],r['columna']) for r in dic}
    esperados=set()
    for p in entrega.glob('*.csv'):
        if p.name!='diccionario_columnas.csv':
            campos,_=leer_csv(p); esperados.update((p.name,c) for c in campos)
    exigir(len(pares)==len(dic) and pares==esperados, 'Diccionario incompleto/duplicado')
    dc={r['columna']:r for r in dic if r['archivo']=='tabla_comun.csv'}
    exigir(dc['rendimiento_t_ha']['funcion']=='objetivo', 'Objetivo mal clasificado')
    for c in ('id_parcela','campania','conjunto_origen'): exigir(dc[c]['funcion']=='metadato', 'Identidad/conjunto no debe ser predictor')
    exigir(dc['cultivo_origen']['funcion']=='solo_auditoria', 'Cultivo sin experimento explícito')
    for d in dsat:
        exigir(dc[d['columna']]['funcion']==('calidad' if d['tipo']=='calidad' else 'predictor_candidato'), 'Rol T06 cambiado')
        exigir(dc[d['columna']]['definicion']==d['definicion'], 'Definición T06 alterada')
    contrato=leer_json(entrega/'contrato_columnas.json')
    roles={}
    for c in cab: roles.setdefault(dc[c]['funcion'],[]).append(c)
    exigir({k:set(v) for k,v in roles.items()}=={k:set(v) for k,v in contrato['columnas_por_funcion'].items()}, 'Roles del contrato contradictorios')
    errores=[]; estados=[]
    if m['clima_integrado']:
        exigir(clima is not None, 'Contraste climático requiere la copia T04 original')
        estado, ht04=comprobar_copia(Path(clima),m['entradas']['revision_t04'],raiz)
        exigir(ht04==inv['bloques']['T04']['archivos_sha256'], 'Fuente T04 distinta del inventario')
        exigir(m['clima_aceptado']==(estado['estado_revision_declarado']=='aceptada'), 'Aceptación declarada contradictoria')
        exigir(inv['bloques']['T04']['estado']==estado['estado_revision_declarado'], 'Estado T04 contradictorio')
        _, mensuales=leer_csv(Path(clima)/'clima_parcela_mes.csv'); mi=indexar(mensuales,('id_parcela','periodo','variable'))
        _, larga=leer_csv(entrega/'clima_ventanas.csv'); li=indexar(larga,('id_parcela','ventana'))
        _, ancha=leer_csv(entrega/'clima_variables.csv'); ai=indexar(ancha,('id_parcela',))
        _, calidad=leer_csv(entrega/'calidad_ventanas.csv'); qi=indexar(calidad,('id_parcela','ventana','variable'))
        exigir((len(mi),len(li),len(ai),len(qi))==(28368,394,197,1182), 'Cardinalidad climática distinta')
        for pid in fuente:
            for w,periodos in PERIODOS.items():
                dias=[calendar.monthrange(2025,int(p[-2:]))[1] for p in periodos]
                r=li[(pid,w)]
                exigir((r['inicio'],r['fin'],int(r['dias_esperados']))==(periodos[0]+'-01','2025-10-31',sum(dias)), 'Calendario climático cambiado')
                for v,col in VARIABLES.items():
                    rows=[mi[(pid,p,v)] for p in periodos];q=qi[(pid,w,v)]
                    completos=all(x['estado']=='cobertura_completa' and x['media_ponderada']!='' for x in rows)
                    exigir(all(x['posterior_al_corte']=='False' for x in rows), 'Mes posterior al corte utilizado')
                    parciales=[p for p,x in zip(periodos,rows) if x['estado']=='cobertura_parcial']
                    nodata=[p for p,x in zip(periodos,rows) if x['media_ponderada']=='']
                    estado='incompleta' if nodata else 'cobertura_parcial' if parciales else 'completa'
                    motivo=('mes_sin_media' if nodata else '')+(';' if nodata and parciales else '')+('cobertura_parcial_sin_extrapolacion' if parciales else '')
                    exigir(q['estado']==estado and q['motivo']==motivo and q['periodos_con_problema']==';'.join(sorted(set(nodata+parciales))), 'Diagnóstico climático distinto')
                    exigir(int(q['meses_esperados'])==int(q['meses_presentes'])==len(periodos), 'Conteo mensual distinto')
                    exigir(int(q['meses_validos'])==len(periodos)-len(nodata), 'Meses válidos distintos')
                    exigir(int(q['dias_esperados'])==sum(dias) and int(q['dias_validos'])==sum(d for x,d in zip(rows,dias) if x['media_ponderada']!=''), 'Días válidos distintos')
                    exigir(abs(Decimal(q['cobertura_minima'])-min(Decimal(x['cobertura_valida']) for x in rows))<=Decimal('1e-15'), 'Cobertura climática distinta')
                    exigir(q['unidad']==('mm' if v=='PREC' else 'grados Celsius'), 'Unidad de ventana incorrecta')
                    valores=[r[col],ai[(pid,)][f'{col}_{w}'],comun[(pid,)][f'{col}_{w}']]
                    if completos:
                        with localcontext() as ctx:
                            ctx.prec=40
                            datos=[Decimal(x['media_ponderada']) for x in rows]
                            esperado=sum(datos) if v=='PREC' else sum(x*d for x,d in zip(datos,dias))/sum(dias)
                            for valor in valores:
                                exigir(valor!='','Resumen completo ausente')
                                error=abs(Decimal(valor)-esperado)
                                exigir(error<=TOLERANCIA, f'Contraste Decimal falló: {pid}/{w}/{v}')
                            errores.append(max(abs(Decimal(x)-esperado) for x in valores))
                    else: exigir(valores==['','',''], 'Ventana parcial/incompleta presentada como completa')
                    estados.append(estado)
    else:
        exigir(clima is None, 'Entrada T04 no utilizada: no atribuirle esta entrega')
        exigir(not any(p.name.startswith('clima_') or p.name=='calidad_ventanas.csv' for p in entrega.iterdir()), 'Tablas climáticas de relleno')
    control=leer_json(entrega/'controles.json')
    exigir(control['parcelas']==197 and control['etiquetas_originales']==138 and control['etiquetas_ausentes']==59, 'Conteo declarado distinto')
    exigir(sum(r['rendimiento_t_ha']!='' for r in tabla)==138, '138 etiquetas no preservadas')
    exigir(control['columnas_tabla_comun']==len(cab), 'Columnas declaradas distintas')
    exigir(control['estados_calidad_satelite']==dict(Counter(r['estado'] for r in calidad_sat)), 'Estados satelitales declarados distintos')
    if estados: exigir(control['estados_ventanas']==dict(Counter(estados)), 'Estados climáticos declarados distintos')
    exigir(m['cierre_t07'] is False and control['cierre_t07'] is False, 'Revisión humana no puede inferirse del cálculo')
    return dict(resultado='verificado', parcelas=197, etiquetas_originales=138, etiquetas_ausentes=59,
                valores_satelitales_literales=len(satcols)*197, controles_satelitales=1182,
                contrastes_climaticos=len(errores), diferencia_maxima_decimal=str(max(errores,default=Decimal(0))),
                tolerancia_decimal=str(TOLERANCIA), estados_climaticos=dict(Counter(estados)),
                estado_entrega=m['estado_entrega'], cierre_t07=False)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--entrega',type=Path,required=True);p.add_argument('--clima',type=Path)
    a=p.parse_args()
    try: resultado=verificar(a.entrega,a.clima)
    except (ValueError,KeyError,OSError) as e:p.exit(1,f'T07 no verificada: {e}\n')
    import json
    print(json.dumps(resultado,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
