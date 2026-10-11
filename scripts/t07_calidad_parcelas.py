"""Desgloses T03 bis por ID; nunca entradas automáticas de un modelo."""
from collections import Counter
from decimal import Decimal, InvalidOperation

from scripts.t07_fuentes import leer_csv
from scripts.t07_preparar import T02, comprobar_fuente

FUENTES = tuple(T02+'/tablas/'+n for n in
                ('pares_de_parcelas_cercanas.csv', 'precision_etiqueta_por_municipio.csv'))
COLUMNAS = ('id_parcela', 'contorno_categoria', 'contorno_angosta_o_muy_pequena',
            'alerta_contorno_t03_bis', 'escalon_etiqueta_municipio',
            'vecina_etiquetada_menos_20m', 'numero_vecinas_etiquetadas_menos_20m')
CONTRATO = dict(archivo='calidad_parcelas.csv', clave='id_parcela', union='uno_a_uno',
    columnas=list(COLUMNAS), predictor_automatico=False,
    poblacion_vecindad='138 etiquetas presentes en el catálogo completo; excluye la propia parcela',
    vecindad='pertenencia a pares_de_parcelas_cercanas.csv (orillas <20 m antes del redondeo)',
    distancia_publicada_no_redefine_umbral=True,
    escalon='caracterización municipal T02 del catálogo completo; sólo auditoría, no predictor',
    vecindad_como_predictor_requeriria_recalculo_solo_con_entrenamiento=True,
    alerta_contorno='B o C o angosta/muy pequeña; sensibilidad secundaria T03, no exclusión principal')


def indexar(filas):
    out={r['id_parcela']:r for r in filas}
    if len(out)!=len(filas) or not out or any(not pid for pid in out):
        raise ValueError('Claves de calidad de parcela duplicadas/vacías')
    return out


def validar(catalogo, soporte, pares, precision):
    cat=indexar(catalogo);sup=indexar(soporte)
    if set(cat)!=set(sup): raise ValueError('Soporte de calidad T02 incompleto/ajeno')
    pasos={}
    for r in precision:
        if r['agrupacion']!='municipio': continue
        m=r['grupo'];p=r['paso_comun']
        if m in pasos or p not in {'','0.5','0.1','0.01'}:
            raise ValueError('Precisión municipal T02 duplicada/incompatible')
        pasos[m]=p
    conocidas={pid for pid,r in cat.items() if r['rendimiento_t_ha']!=''}
    vecinas={pid:set() for pid in cat};vistos=set()
    for r in pares:
        a,b=r['id_parcela_a'],r['id_parcela_b'];key=tuple(sorted((a,b)))
        if a not in cat or b not in cat or a==b or key in vistos:
            raise ValueError('Par cercano ajeno, propio o duplicado')
        vistos.add(key)
        try: distancia=Decimal(r['distancia_orillas_m'])
        except InvalidOperation: raise ValueError('Distancia publicada incompatible') from None
        # T02 eligió pares con distancia sin redondear <20 m. 20.00 publicado
        # puede venir de 19.999 m: no volver a seleccionar con la cifra redondeada.
        if not distancia.is_finite() or not 0<=distancia<=20:
            raise ValueError('Distancia publicada incompatible')
        if r['ambas_conocidas']!=('si' if a in conocidas and b in conocidas else 'no'):
            raise ValueError('Condición de etiquetas del par contradictoria')
        if b in conocidas: vecinas[a].add(b)
        if a in conocidas: vecinas[b].add(a)
    filas=[]
    for pid in sorted(cat):
        r=cat[pid];s=sup[pid];c=r['contorno_categoria'];ang=r['contorno_angosta_o_muy_pequena']
        if c not in {'A','B','C'} or ang not in {'si','no'}:
            raise ValueError('Categoría/bandera de contorno incompatible')
        if r['municipio'] not in pasos or s['municipio']!=r['municipio']:
            raise ValueError('Municipio sin referencia de precisión o contradictorio')
        if s['escalon_etiqueta_municipio']!=pasos[r['municipio']]:
            raise ValueError('Escalón T02 contradictorio entre soporte y precisión')
        filas.append(dict(id_parcela=pid,contorno_categoria=c,contorno_angosta_o_muy_pequena=ang,
            alerta_contorno_t03_bis='si' if c in {'B','C'} or ang=='si' else 'no',
            escalon_etiqueta_municipio=s['escalon_etiqueta_municipio'],
            vecina_etiquetada_menos_20m='si' if vecinas[pid] else 'no',
            numero_vecinas_etiquetadas_menos_20m=len(vecinas[pid])))
    control=dict(parcelas=len(filas),categorias_contorno=dict(Counter(r['contorno_categoria'] for r in filas)),
        etiquetadas_con_alerta_contorno=sum(r['id_parcela'] in conocidas and r['alerta_contorno_t03_bis']=='si' for r in filas),
        vecina_etiquetada_en_etiquetadas=sum(r['id_parcela'] in conocidas and r['vecina_etiquetada_menos_20m']=='si' for r in filas),
        vecina_etiquetada_en_reservadas=sum(r['id_parcela'] not in conocidas and r['vecina_etiquetada_menos_20m']=='si' for r in filas),
        escalon_ausente=sorted(r['id_parcela'] for r in filas if r['escalon_etiqueta_municipio']==''),
        pares_cercanos=len(pares),universo_vecindad='catálogo completo; sólo para desgloses')
    return filas,control


def leer(raiz,base,catalogo):
    hashes={n:comprobar_fuente(n,base,raiz=raiz) for n in FUENTES}
    _,sup=leer_csv(raiz/T02/'tablas/soporte_por_parcela.csv')
    _,pares=leer_csv(raiz/FUENTES[0]);_,precision=leer_csv(raiz/FUENTES[1])
    filas,control=validar(catalogo,sup,pares,precision)
    return filas,control,hashes


def diccionario():
    defs={
        'id_parcela':('Clave original; une uno a uno a tabla_comun.csv','sin unidad','No permitido'),
        'contorno_categoria':('Categoría A/B/C original T02; desglose de error T03','categoría','No permitido'),
        'contorno_angosta_o_muy_pequena':('Marca original si/no de T02; sin recalificar geometrías','si/no','No permitido'),
        'alerta_contorno_t03_bis':('si cuando categoría B/C o angosta/muy pequeña; sensibilidad secundaria, no filtro de población principal','si/no','No permitido'),
        'escalon_etiqueta_municipio':('Paso publicado por municipio en T02; derivado de etiquetas del catálogo completo, sólo auditoría','t/ha','No identificable con las etiquetas municipales disponibles; no se imputa'),
        'vecina_etiquetada_menos_20m':('si si existe otra parcela con etiqueta presente entre los pares T02 de orillas <20 m; catálogo completo, no respaldo de cada entrenamiento','si/no','No permitido; no significa ausencia de cualquier vecina'),
        'numero_vecinas_etiquetadas_menos_20m':('Número de otras parcelas etiquetadas distintas en los pares cercanos T02; 0 real es ausencia de vecina etiquetada en el catálogo completo','parcelas','No permitido')}
    out=[]
    for c in COLUMNAS:
        d,u,v=defs[c]
        out.append(dict(archivo='calidad_parcelas.csv',columna=c,definicion=d,unidad=u,
            funcion='metadato' if c=='id_parcela' else 'solo_auditoria',producto='auditoría T02',
            periodo='campaña 2025',agregacion='unión por ID; pares seleccionados en T02 antes de redondear; sin aprender predictores',
            significado_vacio=v,procedencia='inventario_fuentes.json; catálogo/soporte/pares/precisión T02'))
    return out
