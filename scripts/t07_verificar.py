"""Contraste independiente T07: Decimal/calendario y conservación literal de fuentes."""
import argparse
import calendar
import csv
import hashlib
import io
import json
from collections import Counter
from datetime import date
from decimal import Decimal, localcontext
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.t07_fuentes import BASE, leer_csv, leer_json, sha
from scripts.t07_preparar import RAIZ, T02, comprobar_fuente, comprobar_copia, procedencia_t02, compatibilidad_t02, git
from scripts.t02_contrato import separar_huellas
from scripts.t07_diccionario import GRUPO_REGISTRO, AREA_T10
from scripts.t07_calidad_parcelas import FUENTES as FUENTES_CALIDAD, COLUMNAS as COLUMNAS_CALIDAD, CONTRATO as CONTRATO_CALIDAD

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
    exigir(m['schema']=='t07_integracion_bloques_v2', 'Manifiesto T07 incompatible')
    exigir(set(m['archivos_sha256'])=={p.name for p in entrega.iterdir()}-{'manifest.json'}, 'Archivos de salida distintos del manifiesto')
    for n,h in m['archivos_sha256'].items(): exigir(sha(entrega/n)==h, f'Huella de salida distinta: {n}')
    for n,h in m['codigo_sha256'].items(): exigir(sha(raiz/n)==h, f'Código distinto de la ejecución: {n}')
    exigir(m['entradas']['base_dev']==inv['base_dev'], 'Bases distintas en inventario y manifiesto')
    t02 = inv['bloques']['T02']
    prefijo = T02+'/'
    datos, audit = separar_huellas(
        {n.removeprefix(prefijo):h for n,h in t02['archivos_sha256'].items()},
        ({n.removeprefix(prefijo):h for n,h in t02['procedencia_sha256'].items()}
         if 'procedencia_sha256' in t02 else None))
    for n,h in datos.items(): comprobar_fuente(prefijo+n,inv['base_dev'],h,raiz)
    exigir({prefijo+n:h for n,h in audit.items()}==procedencia_t02(inv['base_dev'],raiz),
           'Procedencia T02 distinta de la revisión archivada')
    huellas_calidad=t02.get('fuentes_calidad_t03_bis_sha256',{})
    exigir(set(huellas_calidad)==set(FUENTES_CALIDAD), 'Fuentes calidad T03 bis incompletas')
    for n,h in huellas_calidad.items(): comprobar_fuente(n,inv['base_dev'],h,raiz)
    for bloque in ('T03','T06'):
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
    exigir(dc['cultivo_origen']['funcion']=='referencia_y_evaluacion', 'Grupo de registro debe conservarse para referencia y evaluación, no predictor automático')
    for d in dsat:
        exigir(dc[d['columna']]['funcion']==('calidad' if d['tipo']=='calidad' else 'predictor_candidato'), 'Rol T06 cambiado')
        exigir(dc[d['columna']]['definicion']==d['definicion'], 'Definición T06 alterada')
    contrato=leer_json(entrega/'contrato_columnas.json')
    exigir(contrato.get('schema')=='t07_columnas_por_funcion_v2' and contrato.get('tabla')=='tabla_comun.csv', 'Versión del contrato T07 incompatible')
    exigir(contrato.get('area_t10')==AREA_T10 and dc['area_ha_origen']['funcion']=='metadato', 'Contrato del área T10 incompatible')
    exigir(contrato.get('grupo_registro')==GRUPO_REGISTRO, 'Uso del grupo de registro incompatible con T03/D019')
    roles={}
    for c in cab: roles.setdefault(dc[c]['funcion'],[]).append(c)
    exigir({k:set(v) for k,v in roles.items()}=={k:set(v) for k,v in contrato['columnas_por_funcion'].items()}, 'Roles del contrato contradictorios')
    exigir(contrato.get('calidad_t03_bis')==CONTRATO_CALIDAD, 'Contrato calidad T03 bis incompatible')
    campos_calidad,cp=leer_csv(entrega/'calidad_parcelas.csv')
    pc=indexar(cp,('id_parcela',))
    exigir(tuple(campos_calidad)==COLUMNAS_CALIDAD and len(pc)==197 and set(pc)==set(comun), 'Calidad de parcelas incompleta/ajena')
    _, soporte_calidad=leer_csv(raiz/T02/'tablas/soporte_por_parcela.csv')
    sc=indexar(soporte_calidad,('id_parcela',))
    _, pares_cercanos=leer_csv(raiz/FUENTES_CALIDAD[0])
    _, precision=leer_csv(raiz/FUENTES_CALIDAD[1])
    municipal=[x for x in precision if x['agrupacion']=='municipio']
    pasos={x['grupo']:x['paso_comun'] for x in municipal}
    exigir(len(pasos)==len(municipal), 'Precisión municipal duplicada')
    conocidas={pid for pid,x in fuente.items() if x['rendimiento_t_ha']!=''}
    cercanas={pid:set() for pid in fuente}; vistos=set()
    for par in pares_cercanos:
        a,b=par['id_parcela_a'],par['id_parcela_b']; pareja=frozenset((a,b))
        exigir(a in fuente and b in fuente and a!=b and pareja not in vistos, 'Par de calidad incompatible')
        vistos.add(pareja)
        exigir(par['ambas_conocidas']==('si' if a in conocidas and b in conocidas else 'no'), 'Etiquetas de par contradictorias')
        # La pertenencia publicada corresponde al umbral previo al redondeo.
        if b in conocidas: cercanas[a].add(b)
        if a in conocidas: cercanas[b].add(a)
    for pid,x in fuente.items():
        q=pc[(pid,)];sup=sc[(pid,)]
        for c in ('contorno_categoria','contorno_angosta_o_muy_pequena'):
            exigir(q[c]==x[c], 'Contorno de parcela alterado')
        alerta='si' if x['contorno_categoria'] in ('B','C') or x['contorno_angosta_o_muy_pequena']=='si' else 'no'
        exigir(q['alerta_contorno_t03_bis']==alerta, 'Alerta de contorno contradictoria')
        exigir(sup['municipio']==x['municipio'] and q['escalon_etiqueta_municipio']==sup['escalon_etiqueta_municipio']==pasos[x['municipio']], 'Escalón municipal alterado/imputado')
        exigir(q['vecina_etiquetada_menos_20m']==('si' if cercanas[pid] else 'no') and q['numero_vecinas_etiquetadas_menos_20m']==str(len(cercanas[pid])), 'Vecindad etiquetada contradictoria')
    exigir(all(d['funcion']==('metadato' if d['columna']=='id_parcela' else 'solo_auditoria') for d in dic if d['archivo']=='calidad_parcelas.csv'), 'Calidad de parcelas usada como predictor')
    control_parcelas=dict(parcelas=197,categorias_contorno=dict(Counter(x['contorno_categoria'] for x in origen_cat)),
        etiquetadas_con_alerta_contorno=sum(pid in conocidas and pc[(pid,)]['alerta_contorno_t03_bis']=='si' for pid in fuente),
        vecina_etiquetada_en_etiquetadas=sum(bool(cercanas[pid]) for pid in conocidas),
        vecina_etiquetada_en_reservadas=sum(bool(cercanas[pid]) for pid in fuente if pid not in conocidas),
        escalon_ausente=sorted(pid for pid in fuente if sc[(pid,)]['escalon_etiqueta_municipio']==''),
        pares_cercanos=len(pares_cercanos),universo_vecindad='catálogo completo; sólo para desgloses')
    errores=[]; errores_centroide=[]; estados=[]
    if m['clima_integrado']:
        exigir(clima is not None, 'Contraste climático requiere la copia T04 original')
        estado, ht04=comprobar_copia(Path(clima),m['entradas']['revision_t04'],raiz)
        exigir(ht04==inv['bloques']['T04']['archivos_sha256'], 'Fuente T04 distinta del inventario')
        compatibilidad_t02(leer_json(Path(clima)/'conciliacion_t02.json'),inv['base_dev'],raiz)
        exigir(m['clima_aceptado']==(estado['estado_revision_declarado']=='aceptada'), 'Aceptación declarada contradictoria')
        exigir(inv['bloques']['T04']['estado']==estado['estado_revision_declarado'], 'Estado T04 contradictorio')
        _, mensuales=leer_csv(Path(clima)/'clima_parcela_mes.csv'); mi=indexar(mensuales,('id_parcela','periodo','variable'))
        _, larga=leer_csv(entrega/'clima_ventanas.csv'); li=indexar(larga,('id_parcela','ventana'))
        _, ancha=leer_csv(entrega/'clima_variables.csv'); ai=indexar(ancha,('id_parcela',))
        _, calidad=leer_csv(entrega/'calidad_ventanas.csv'); qi=indexar(calidad,('id_parcela','ventana','variable'))
        _, soporte=leer_csv(raiz/T02/'tablas/soporte_por_parcela.csv')
        soporte_por_id=indexar(soporte, ('id_parcela',))
        exigir(set(soporte_por_id)==set(comun), 'Claves de soporte climático T02 distintas')
        roles_nuevos={'celdas_lluvia_tocadas_t02':'calidad', 'centroide_dentro_parcela':'calidad',
            'meses_centroide_validos':'calidad', 'dias_centroide_validos':'calidad',
            'periodos_sin_centroide':'calidad', 'valor_centroide_ventana':'solo_auditoria',
            'diferencia_media_menos_centroide':'solo_auditoria', 'estado_comparacion_centroide':'calidad'}
        exigir(all(r['funcion']==roles_nuevos[r['columna']] for r in dic
                   if r['archivo']=='calidad_ventanas.csv' and r['columna'] in roles_nuevos),
               'Rol de sensibilidad climática incompatible')
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
                    n=soporte_por_id[(pid,)]['celdas_clima_tocadas']
                    exigir(n.isdigit() and int(n)>0 and q['celdas_lluvia_tocadas_t02']==str(int(n)), 'Conteo de celdas de lluvia T02 distinto')
                    flags={x['centroide_dentro_parcela'] for x in rows}
                    exigir(len(flags)==1 and q['centroide_dentro_parcela'] in flags, 'Bandera de centroide climático distinta')
                    centros_validos=[x['valor_centroide']!='' for x in rows]
                    faltan_centros=[p for p,x in zip(periodos,rows) if x['valor_centroide']=='']
                    exigir(int(q['meses_centroide_validos'])==sum(centros_validos) and
                           int(q['dias_centroide_validos'])==sum(d for ok,d in zip(centros_validos,dias) if ok) and
                           q['periodos_sin_centroide']==';'.join(faltan_centros), 'Conteos/meses de centroide distintos')
                    comparable=completos and all(centros_validos)
                    esperado_estado='ventana_no_completa' if not completos else 'centroide_incompleto' if faltan_centros else 'comparable'
                    exigir(q['estado_comparacion_centroide']==esperado_estado, 'Estado de sensibilidad al centroide contradictorio')
                    with localcontext() as ctx:
                        ctx.prec=40
                        if all(centros_validos):
                            cs=[Decimal(x['valor_centroide']) for x in rows]
                            esperado_centro=sum(cs) if v=='PREC' else sum(x*d for x,d in zip(cs,dias))/sum(dias)
                            exigir(q['valor_centroide_ventana']!='', 'Centroide completo ausente')
                            error=abs(Decimal(q['valor_centroide_ventana'])-esperado_centro)
                            exigir(error<=TOLERANCIA, 'Agregado del centroide distinto (Decimal)')
                            errores_centroide.append(error)
                        else: exigir(q['valor_centroide_ventana']=='', 'Centroide incompleto presentado como completo')
                        if comparable:
                            ms=[Decimal(x['media_ponderada']) for x in rows]
                            esperado_media=sum(ms) if v=='PREC' else sum(x*d for x,d in zip(ms,dias))/sum(dias)
                            exigir(q['diferencia_media_menos_centroide']!='', 'Sensibilidad completa ausente')
                            exigir(abs(Decimal(q['diferencia_media_menos_centroide'])-(esperado_media-esperado_centro))<=TOLERANCIA,
                                   'Diferencia con centroide distinta (Decimal)')
                        else: exigir(q['diferencia_media_menos_centroide']=='', 'Sensibilidad incompleta presentada como completa')
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
    auditoria_relieve=None
    relieve_integrado=m.get('relieve_integrado',False)
    exigir(type(relieve_integrado) is bool, 'Bandera relieve incompatible')
    if relieve_integrado:
        from scripts.t07_auditar_relieve import auditar
        bloque=inv['bloques']['T05']
        archivos={'registro/t05/'+n for n in ('manifest.json','relieve_parcela.csv','relieve_celdas.csv','procedencia.json','controles.json')}
        exigir(set(bloque['archivos_sha256'])==archivos, 'Fuentes T05 incompletas')
        for n,h in bloque['archivos_sha256'].items(): comprobar_fuente(n,inv['base_dev'],h,raiz)
        aux=('docs/t05_relieve.md','scripts/t05_relieve.py')
        exigir(bloque['procedencia_sha256']=={n:hashlib.sha256(git('show',f"{inv['base_dev']}:{n}",raiz=raiz)).hexdigest() for n in aux}, 'Procedencia T05 distinta de la base')
        def d020(texto):
            filas=[r for r in csv.DictReader(io.StringIO(texto)) if r['id']=='D020']
            exigir(len(filas)==1, 'D020 ausente o duplicada')
            return filas[0]
        decision=d020(git('show',f"{inv['base_dev']}:registro/decisiones.csv",raiz=raiz).decode())
        exigir(decision==d020((raiz/'registro/decisiones.csv').read_text(encoding='utf-8')), 'D020 alterada')
        huella=hashlib.sha256(json.dumps(decision,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        exigir(bloque['decision_sha256']==huella and bloque['piso_pendiente']==0.5 and bloque['decision']=='D020', 'Referencia D020 incompatible')
        exigir(bloque['unidades']=={'elevacion':'m s.n.m.','pendiente':'grados'} and bloque['crs']=='EPSG:6372', 'Unidades/CRS T05 distintos')
        _,resumen=leer_csv(raiz/'registro/t05/relieve_parcela.csv')
        _,celdas=leer_csv(raiz/'registro/t05/relieve_celdas.csv')
        _,calidad_relieve=leer_csv(entrega/'calidad_relieve.csv')
        auditoria_relieve=auditar(tabla,calidad_relieve,resumen,celdas)
        for c in ('elevacion_media_m','pendiente_media_t10_grados'):
            exigir(dc[c]['funcion']=='predictor_candidato', 'Rol relieve incompatible')
        for d in dic:
            if d['archivo']=='calidad_relieve.csv':
                exigir(d['funcion']==('metadato' if d['columna']=='id_parcela' else 'solo_auditoria'), 'Calidad relieve usada como predictor')
        exigir('pendiente_media_grados' not in cab, 'Pendiente sin filtro D020 presentada como candidata')
    else:
        exigir(not (entrega/'calidad_relieve.csv').exists() and not set(cab)&{'elevacion_media_m','pendiente_media_t10_grados'}, 'Relieve generado sin atribución')
    clima_cols=[f'{col}_{w}' for w in PERIODOS for col in VARIABLES.values()] if m['clima_integrado'] else []
    relieve_cols=['elevacion_media_m','pendiente_media_t10_grados'] if relieve_integrado else []
    exigir(cab==[*BASE,*clima_cols,*satcols,*relieve_cols], 'Columnas comunes fuera del contrato de bloques')
    control=leer_json(entrega/'controles.json')
    exigir(control['parcelas']==197 and control['etiquetas_originales']==138 and control['etiquetas_ausentes']==59, 'Conteo declarado distinto')
    exigir(sum(r['rendimiento_t_ha']!='' for r in tabla)==138, '138 etiquetas no preservadas')
    exigir(control.get('calidad_parcelas')==control_parcelas, 'Controles de calidad de parcelas distintos')
    exigir(control['columnas_tabla_comun']==len(cab), 'Columnas declaradas distintas')
    exigir(control['estados_calidad_satelite']==dict(Counter(r['estado'] for r in calidad_sat)), 'Estados satelitales declarados distintos')
    if auditoria_relieve: exigir(control['relieve']==auditoria_relieve['controles'], 'Controles relieve distintos')
    if estados:
        exigir(control['estados_ventanas']==dict(Counter(estados)), 'Estados climáticos declarados distintos')
        esperado=dict(fuente_conteo_celdas=T02+'/tablas/soporte_por_parcela.csv',
            cuadricula_del_conteo='lluvia T02; no conteo de temperatura',
            parcelas_varias_celdas_lluvia=sum(int(r['celdas_clima_tocadas'])>1 for r in soporte),
            centroides_exteriores=sorted({r['id_parcela'] for r in calidad if r['centroide_dentro_parcela']=='False'}),
            estados_comparacion=dict(Counter(r['estado_comparacion_centroide'] for r in calidad)))
        exigir(control['calidad_climatica_espacial']==esperado, 'Control de calidad climática espacial distinto')
    exigir(m['cierre_t07'] is False and control['cierre_t07'] is False, 'Revisión humana no puede inferirse del cálculo')
    return dict(resultado='verificado', parcelas=197, etiquetas_originales=138, etiquetas_ausentes=59,
                valores_satelitales_literales=len(satcols)*197, controles_satelitales=1182,
                contrastes_climaticos=len(errores), diferencia_maxima_decimal=str(max(errores,default=Decimal(0))),
                tolerancia_decimal=str(TOLERANCIA), contrastes_centroide=len(errores_centroide),
                diferencia_maxima_decimal_centroide=str(max(errores_centroide,default=Decimal(0))),
                estados_climaticos=dict(Counter(estados)),
                calidad_parcelas=control_parcelas, estado_entrega=m['estado_entrega'], relieve=auditoria_relieve, cierre_t07=False)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--entrega',type=Path,required=True);p.add_argument('--clima',type=Path)
    a=p.parse_args()
    try: resultado=verificar(a.entrega,a.clima)
    except (ValueError,KeyError,OSError) as e:p.exit(1,f'T07 no verificada: {e}\n')
    print(json.dumps(resultado,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
