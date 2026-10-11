"""Contrato T05→T07: dos candidatas literales, calidad separada y fuente identificada."""
from collections import Counter
from decimal import Decimal
import csv
import hashlib
import io
import json

from scripts.t07_fuentes import leer_csv, leer_json, numero, sha
from scripts.t07_preparar import comprobar_fuente, git

CANDIDATAS = ('elevacion_media_m', 'pendiente_media_t10_grados')
COLUMNAS = ('id_parcela', 'area_parcela_6372_m2', 'cobertura_espacial',
    'elevacion_media_m', 'elevacion_cobertura_valida', 'elevacion_celdas_intersectadas',
    'elevacion_celdas_validas', 'elevacion_area_valida_m2', 'elevacion_min_m', 'elevacion_max_m',
    'estado_elevacion', 'pendiente_media_grados', 'pendiente_cobertura_valida',
    'pendiente_celdas_intersectadas', 'pendiente_celdas_validas', 'pendiente_area_valida_m2',
    'pendiente_min_grados', 'pendiente_max_grados', 'estado_pendiente',
    'pendiente_media_t10_grados', 'elevacion_centroide_m', 'pendiente_centroide_grados',
    'diferencia_elevacion_centroide_m', 'diferencia_pendiente_centroide_grados',
    'centroide_dentro_parcela', 'avisos')
CALIDAD = tuple(c for c in COLUMNAS if c not in CANDIDATAS)
ARCHIVOS = tuple('registro/t05/' + n for n in
    ('manifest.json', 'relieve_parcela.csv', 'relieve_celdas.csv', 'procedencia.json', 'controles.json'))
AUXILIARES = ('docs/t05_relieve.md', 'scripts/t05_relieve.py')
ESTADOS = {'cobertura_completa', 'cobertura_parcial', 'todo_nodata', 'sin_cobertura_espacial'}
PISO = Decimal('0.5')


def decision_d020(texto):
    filas = list(csv.DictReader(io.StringIO(texto)))
    encontrados = [r for r in filas if r.get('id') == 'D020']
    if len(encontrados) != 1 or None in encontrados[0]:
        raise ValueError('Decisión D020 ausente, duplicada o mal formada')
    return encontrados[0]


def huella_decision(fila):
    return hashlib.sha256(json.dumps(fila, ensure_ascii=False, sort_keys=True,
                                    separators=(',', ':')).encode()).hexdigest()


def validar(columnas, filas, catalogo):
    ids = {r['id_parcela'] for r in catalogo}
    rids = [r.get('id_parcela') for r in filas]
    if list(columnas) != list(COLUMNAS) or any(set(r) != set(COLUMNAS) for r in filas):
        raise ValueError('Columnas T05 incompatibles')
    if len(rids) != len(ids) or len(set(rids)) != len(ids) or set(rids) != ids:
        raise ValueError('IDs T05 ausentes, ajenos o duplicados')
    indice = {}
    for r in filas:
        pid = r['id_parcela']
        for c in COLUMNAS:
            if c not in {'id_parcela', 'estado_elevacion', 'estado_pendiente', 'centroide_dentro_parcela', 'avisos'}:
                numero(r[c], vacio=True)
        if numero(r['area_parcela_6372_m2']) <= 0 or not 0 <= Decimal(r['cobertura_espacial']) <= Decimal(1)+Decimal('1e-12'):
            raise ValueError('Área/cobertura espacial T05 incompatible')
        if r['centroide_dentro_parcela'] not in {'True', 'False'}:
            raise ValueError('Bandera de centroide T05 incompatible')
        for v, media in [('elevacion', 'elevacion_media_m'), ('pendiente', 'pendiente_media_grados')]:
            cov = numero(r[v+'_cobertura_valida']); estado = r['estado_'+v]
            ni = numero(r[v+'_celdas_intersectadas']); nv = numero(r[v+'_celdas_validas'])
            if (estado not in ESTADOS or not 0 <= cov <= 1 or ni < 0 or not ni.is_integer()
                    or nv < 0 or not nv.is_integer() or nv > ni):
                raise ValueError('Estado/cobertura/conteos T05 incompatibles')
            ausente = estado in {'todo_nodata', 'sin_cobertura_espacial'}
            if (ausente != (r[media] == '') or ausente != (cov == 0)
                    or (not ausente and (estado == 'cobertura_completa') != (cov >= 1-1e-9))):
                raise ValueError('Media/cobertura/estado T05 contradictorios')
        original = r['pendiente_media_grados']
        esperado = original if Decimal(r['pendiente_cobertura_valida']) >= PISO else ''
        if r['pendiente_media_t10_grados'] != esperado:
            raise ValueError('Pendiente T10 viola D020: '+pid)
        if original and not 0 <= numero(original) <= 90:
            raise ValueError('Pendiente fuera de grados admisibles')
        indice[pid] = r
    calidad = [{c: indice[pid][c] for c in CALIDAD} for pid in sorted(ids)]
    return indice, calidad


def leer(raiz, base, catalogo):
    """Huella contra Git y manifiesto. No ejecuta PROJ ni extrae los originales."""
    hashes = {p: comprobar_fuente(p, base, raiz=raiz) for p in ARCHIVOS}
    carpeta = raiz/'registro/t05'
    m = leer_json(carpeta/'manifest.json'); prov = leer_json(carpeta/'procedencia.json')
    control = leer_json(carpeta/'controles.json')
    nombres = {p.rsplit('/', 1)[1] for p in ARCHIVOS if not p.endswith('/manifest.json')}
    if m.get('schema') != 't05_entrega_v1' or set(m.get('archivos_sha256', {})) != nombres:
        raise ValueError('Esquema/manifiesto T05 incompatible')
    if any(sha(carpeta/n) != h for n, h in m['archivos_sha256'].items()):
        raise ValueError('Huella de entrega T05 distinta')
    if (prov.get('unidades') != {'elevacion': 'm s.n.m.', 'pendiente': 'grados'}
            or prov.get('metodo_area') != 'plana_crs_raster_v1'
            or prov.get('piso_pendiente_t10') != 0.5 or prov.get('decision_de_uso') != 'D020'
            or prov.get('cuadricula_relieve', {}).get('crs') != 'EPSG:6372'
            or prov.get('cuadricula_relieve', {}).get('resolucion_m') != [120.0, 120.0]):
        raise ValueError('Unidades/CRS/método/piso T05 incompatible')
    cols, filas = leer_csv(carpeta/'relieve_parcela.csv')
    _, celdas = leer_csv(carpeta/'relieve_celdas.csv')
    if (m.get('parcelas') != len(filas) or m.get('celdas') != len(celdas)
            or m.get('resultado_controles') != 'aprobado' or control.get('resultado') != 'aprobado'):
        raise ValueError('Conteos/controles T05 incompatibles')
    indice, calidad = validar(cols, filas, catalogo)
    archivada = decision_d020(git('show', f'{base}:registro/decisiones.csv', raiz=raiz).decode())
    if decision_d020((raiz/'registro/decisiones.csv').read_text(encoding='utf-8')) != archivada:
        raise ValueError('Decisión D020 distinta de la base identificada')
    audit = {p: hashlib.sha256(git('show', f'{base}:{p}', raiz=raiz)).hexdigest() for p in AUXILIARES}
    inventario = dict(estado='fuente_revisada_integrada', integrado_en_t07=True,
        archivos_sha256=hashes, procedencia_sha256=audit, fuente='registro/t05',
        candidatas=list(CANDIDATAS), calidad='calidad_relieve.csv', decision='D020',
        decision_sha256=huella_decision(archivada), piso_pendiente=0.5,
        unidades=prov['unidades'], crs='EPSG:6372', resolucion_m=[120.0,120.0],
        metodo_area=prov['metodo_area'], no_reextrae_geometrias=True,
        revision_humana_fuente='PR12 revisado por Dani y fusionado en dev; T07 pendiente Jass')
    return indice, calidad, inventario


def incorporar(campos, filas, relieve):
    ids = [r['id_parcela'] for r in filas]
    if len(ids) != len(set(ids)) or set(ids) != set(relieve):
        raise ValueError('Unión T05 con claves incompatibles')
    if set(campos) & set(CANDIDATAS):
        raise ValueError('Colisión de columnas entre bloques T05')
    return (*campos, *CANDIDATAS), [{**r, **{c: relieve[r['id_parcela']][c] for c in CANDIDATAS}}
                                 for r in sorted(filas, key=lambda r:r['id_parcela'])]


def controles(indice, catalogo):
    reservadas = {r['id_parcela'] for r in catalogo if r['conjunto_origen']=='PREDICCION'}
    return dict(parcelas=len(indice), candidatas_verificadas=len(indice)*2,
        estados_elevacion=dict(Counter(r['estado_elevacion'] for r in indice.values())),
        estados_pendiente=dict(Counter(r['estado_pendiente'] for r in indice.values())),
        pendiente_t10_ausente=sorted(pid for pid,r in indice.items() if r['pendiente_media_t10_grados']==''),
        elevacion_ausente=sorted(pid for pid,r in indice.items() if r['elevacion_media_m']==''),
        reservadas_incompletas=sorted(pid for pid in reservadas if any(indice[pid]['estado_'+v]!='cobertura_completa'
                                     for v in ('elevacion','pendiente'))),
        parcelas_con_avisos=sum(bool(r['avisos']) for r in indice.values()))


def diccionario():
    des = {
        'id_parcela': ('Clave original de parcela', 'sin unidad'),
        'area_parcela_6372_m2': ('Área plana del polígono en EPSG:6372; distinta del área declarada del catálogo', 'm²'),
        'cobertura_espacial': ('Fracción del polígono dentro de la cuadrícula de relieve; conserva el redondeo original T05 (hasta 1 + 1e-12)' , 'fracción 0–1'),
        'elevacion_media_m': ('Media de elevación ponderada por área de intersección válida', 'm s.n.m.'),
        'pendiente_media_t10_grados': ('Media de pendiente original si cobertura válida ≥ 0.5; vacío bajo el piso D020', 'grados'),
        'pendiente_media_grados': ('Media original de pendiente sobre el área válida; auditoría aunque sea menor del piso D020', 'grados'),
        'centroide_dentro_parcela': ('Bandera geométrica T05, sin cambiar el punto de consulta', 'booleano'),
        'avisos': ('Diagnósticos T05 separados por ;, sin excluir parcelas ni cambiar el rendimiento', 'categoría'),
    }
    for v, unidad in [('elevacion','m s.n.m.'),('pendiente','grados')]:
        des.update({v+'_cobertura_valida':('Fracción del área del polígono con dato válido en '+v,'fracción 0–1'),
            v+'_celdas_intersectadas':('Número de celdas con intersección de área positiva','celdas'),
            v+'_celdas_validas':('Número de celdas intersectadas con dato válido','celdas'),
            v+'_area_valida_m2':('Área válida intersectada para '+v+' en EPSG:6372','m²'),
            v+'_min_'+('m' if v=='elevacion' else 'grados'):('Mínimo de las celdas válidas intersectadas a 120 m; no extremo real del terreno',unidad),
            v+'_max_'+('m' if v=='elevacion' else 'grados'):('Máximo de las celdas válidas intersectadas a 120 m; no extremo real del terreno',unidad),
            'estado_'+v:('cobertura_completa, cobertura_parcial, todo_nodata o sin_cobertura_espacial','categoría'),
            v+'_centroide_'+('m' if v=='elevacion' else 'grados'):('Valor de celda en el centroide; sensibilidad, sin desplazarlo si falta dato',unidad),
            'diferencia_'+v+'_centroide_'+('m' if v=='elevacion' else 'grados'):('Media ponderada menos valor del centroide, copiada literalmente de T05',unidad)})
    out=[]
    for archivo, campos in [('tabla_comun.csv',CANDIDATAS),('calidad_relieve.csv',CALIDAD)]:
        for c in campos:
            out.append(dict(archivo=archivo,columna=c,definicion=des[c][0],unidad=des[c][1],
                funcion='predictor_candidato' if archivo=='tabla_comun.csv' else 'metadato' if c=='id_parcela' else 'solo_auditoria',
                producto='INEGI CEM4',periodo='relieve estático suministrado; no fecha de adquisición confirmada',
                agregacion='Selección literal T05, sin agregación temporal ni imputación',
                significado_vacio='Sin media válida o pendiente bajo piso D020; no equivale a cero' if c in CANDIDATAS else
                    'Ningún aviso' if c=='avisos' else 'Sin dato válido/centroide con NoData en T05; no equivale a cero' if c not in
                    {'id_parcela','area_parcela_6372_m2','cobertura_espacial','estado_elevacion','estado_pendiente','centroide_dentro_parcela', *(v+suf for v in ('elevacion','pendiente') for suf in ('_cobertura_valida','_celdas_intersectadas','_celdas_validas','_area_valida_m2'))} else 'No permitido',
                procedencia='registro/t05; inventario_fuentes.json; decisión D020; calidad_relieve.csv'))
    return out
