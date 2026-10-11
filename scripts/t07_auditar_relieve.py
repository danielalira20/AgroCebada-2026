"""Recalcula T05 desde sus celdas con Decimal, sin reutilizar el extractor ni PROJ."""
from collections import Counter
from decimal import Decimal, InvalidOperation, localcontext

TOL_MEDIA = Decimal('1e-9')
TOL_AREA_RELATIVA = Decimal('1e-9')
TOL_BALANCE_RELATIVA = Decimal('1e-6')
PREDICTORES = ('elevacion_media_m', 'pendiente_media_t10_grados')


def exigir(condicion, mensaje):
    if not condicion:
        raise ValueError('Contraste relieve: '+mensaje)


def decimal(valor):
    try:
        n = Decimal(valor)
    except (InvalidOperation, TypeError, ValueError) as e:
        raise ValueError('Contraste relieve: número incompatible') from e
    exigir(n.is_finite(), 'número no finito')
    return n


def indice(filas):
    ids = [r['id_parcela'] for r in filas]
    exigir(len(ids) == len(set(ids)), 'IDs duplicados')
    return {r['id_parcela']:r for r in filas}


def auditar(comun, calidad, resumen, celdas):
    """Transferencia literal y reconstrucción numérica independiente por ID, no por fila."""
    ci, qi, ri = (indice(filas) for filas in (comun, calidad, resumen))
    exigir(len(ri) == 197 and set(ci) == set(qi) == set(ri), 'universo de parcelas distinto')
    por_id = {pid:[] for pid in ri}; claves = set()
    for r in celdas:
        pid = r['id_parcela']
        exigir(pid in ri, 'celda de parcela ajena')
        coords = [decimal(r[c]) for c in ('fila','columna')]
        exigir(all(v >= 0 and v == v.to_integral_value() for v in coords), 'índice de celda inválido')
        clave = (pid,*coords)
        exigir(clave not in claves, 'celda duplicada'); claves.add(clave)
        area = decimal(r['area_interseccion_m2']); exigir(area > 0, 'intersección sin área positiva')
        for v,col in [('elevacion','elevacion_m'),('pendiente','pendiente_grados')]:
            exigir(r[v+'_valida'] in {'True','False'}, 'máscara inválida')
            exigir((r[v+'_valida']=='True') == (r[col] != ''), 'máscara y dato contradictorios')
            if r[col]: decimal(r[col])
        por_id[pid].append(r)
    errores=[]; coberturas=[]; balances=[]
    with localcontext() as ctx:
        ctx.prec=40
        for pid,r in ri.items():
            exigir(all(ci[pid][c] == r[c] for c in PREDICTORES), 'valor candidato alterado: '+pid)
            esperado = {c:x for c,x in r.items() if c not in PREDICTORES}
            exigir(qi[pid] == esperado, 'calidad alterada: '+pid)
            area = decimal(r['area_parcela_6372_m2']); exigir(area>0, 'área del polígono inválida')
            espacial=decimal(r['cobertura_espacial'])
            exigir(0<=espacial<=Decimal(1)+Decimal('1e-12'), 'cobertura espacial fuera de rango')
            filas = por_id[pid]
            total = sum((decimal(x['area_interseccion_m2']) for x in filas), Decimal(0))
            balance = abs(total-area*decimal(r['cobertura_espacial']))/area
            exigir(balance <= TOL_BALANCE_RELATIVA, 'balance espacial fuera de tolerancia: '+pid)
            balances.append(balance)
            for v,media,sufijo,col in [('elevacion','elevacion_media_m','m','elevacion_m'),
                                      ('pendiente','pendiente_media_grados','grados','pendiente_grados')]:
                validas = [x for x in filas if x[v+'_valida']=='True']
                exigir(decimal(r[v+'_celdas_intersectadas']) == len(filas)
                        and decimal(r[v+'_celdas_validas']) == len(validas), 'conteos distintos: '+pid)
                av = sum((decimal(x['area_interseccion_m2']) for x in validas), Decimal(0))
                exigir(abs(av-decimal(r[v+'_area_valida_m2'])) <= max(TOL_MEDIA,av*TOL_AREA_RELATIVA), 'área válida distinta: '+pid)
                cov = min(Decimal(1),av/area)
                ec = abs(cov-decimal(r[v+'_cobertura_valida']))
                exigir(ec <= TOL_MEDIA, 'cobertura distinta: '+pid); coberturas.append(ec)
                estado = ('sin_cobertura_espacial' if not filas else 'todo_nodata' if not validas else
                          'cobertura_completa' if cov >= Decimal(1)-TOL_MEDIA else 'cobertura_parcial')
                exigir(r['estado_'+v] == estado, 'estado contradictorio: '+pid)
                if not validas:
                    exigir(all(r[c]=='' for c in (media,v+'_min_'+sufijo,v+'_max_'+sufijo)), 'resumen sin datos')
                else:
                    valores = [decimal(x[col]) for x in validas]
                    media_ref = sum(decimal(x[col])*decimal(x['area_interseccion_m2']) for x in validas)/av
                    error = abs(decimal(r[media])-media_ref)
                    exigir(error <= TOL_MEDIA, 'media ponderada distinta: '+pid+'/'+v); errores.append(error)
                    exigir(decimal(r[v+'_min_'+sufijo]) == min(valores)
                            and decimal(r[v+'_max_'+sufijo]) == max(valores), 'extremos distintos: '+pid)
                centro = r[v+'_centroide_'+sufijo]; delta = r['diferencia_'+v+'_centroide_'+sufijo]
                if r[media] and centro:
                    exigir(abs(decimal(delta)-(decimal(r[media])-decimal(centro))) <= TOL_MEDIA, 'sensibilidad centroide distinta')
                else: exigir(delta=='', 'diferencia sin media o centroide')
                if v=='pendiente':
                    seguro = r[media] if cov>=Decimal('0.5') else ''
                    exigir(ci[pid]['pendiente_media_t10_grados']==seguro, 'piso D020 incumplido: '+pid)
    reservadas = {pid for pid,r in ci.items() if r['conjunto_origen']=='PREDICCION'}
    controles = dict(parcelas=len(ri), candidatas_verificadas=len(ri)*2,
        estados_elevacion=dict(Counter(r['estado_elevacion'] for r in ri.values())),
        estados_pendiente=dict(Counter(r['estado_pendiente'] for r in ri.values())),
        pendiente_t10_ausente=sorted(pid for pid,r in ri.items() if r['pendiente_media_t10_grados']==''),
        elevacion_ausente=sorted(pid for pid,r in ri.items() if r['elevacion_media_m']==''),
        reservadas_incompletas=sorted(pid for pid in reservadas if any(ri[pid]['estado_'+v]!='cobertura_completa' for v in ('elevacion','pendiente'))),
        parcelas_con_avisos=sum(bool(r['avisos']) for r in ri.values()))
    return dict(celdas=len(celdas), medias_recalculadas=len(errores), valores_literales=197*2,
        diferencia_maxima_media=str(max(errores,default=Decimal(0))), tolerancia_media=str(TOL_MEDIA),
        diferencia_maxima_cobertura=str(max(coberturas,default=Decimal(0))),
        diferencia_relativa_maxima_balance=str(max(balances,default=Decimal(0))),
        controles=controles)
