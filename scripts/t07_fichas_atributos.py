"""Fichas documentales T07: no perfila valores, selecciona atributos ni entrena.

Complemento reproducible de una entrega T07 identificada. El diccionario y el
contrato existentes conservan la autoridad sobre definición, unidad y función.
"""
import argparse
from collections import Counter
import csv
import hashlib
import io
import json
from pathlib import Path
import shutil
import tempfile

RAIZ = Path(__file__).resolve().parents[1]
ENTREGA = 'registro/t07'
DICCIONARIO = ('archivo', 'columna', 'definicion', 'unidad', 'funcion', 'producto',
               'periodo', 'agregacion', 'significado_vacio', 'procedencia')
CAMPOS = (*DICCIONARIO, 'tarea_fuente', 'responsable_fuente', 'revisa_fuente',
          'frente_de_uso', 'condicion_de_uso', 'unidad_estado', 'version_producto',
          'periodo_resumen', 'periodo_insumos_necesarios', 'fecha_publicacion',
          'disponibilidad_al_corte', 'evidencia_disponibilidad', 'soporte_espacial',
          'control_calidad', 'requisitos_campania_futura', 'acceso_futuro',
          'limite_interpretacion', 'aclaracion_faltante', 'pendientes', 'fuentes')
PENDIENTES = {
    'P01': ('T04', 'Dani', 'Jass', 'Versiones y disponibilidad del paquete climático',
            'Confirmar número/variante de CHIRPS y CHIRTS-ERA5, fecha de publicación de la edición mensual recibida y acceso a una campaña nueva.',
            'Limita la afirmación de predicción operacional; no invalida la reconstrucción retrospectiva.'),
    'P02': ('T06', 'Daf', 'Jass', 'Publicación, procesamiento y acceso futuro al satélite',
            'Confirmar fechas de disponibilidad y edición/procesamiento de las series; cómo obtener series equivalentes de cada sensor, con permisos y costes si aplican.',
            'No atribuir disponibilidad a la fecha de captura ni garantizar continuidad del servicio.'),
    'P03': ('T06', 'Daf', 'Jass', 'Unidad física y escala de LAI2/VI6T',
            'Documentar unidad, escala y significado de los índices exactos del paquete; no sustituir por otro LAI/índice de nombre parecido.',
            'Interpretación física pendiente; conservar valores y papel candidato, sin conversión ni exclusión automática.'),
    'P04': ('T06', 'Daf', 'Jass', 'Definición espacial de nubosidad y estadísticas',
            'Confirmar cálculo de nubosidad, máscara de píxeles y tratamiento de bordes en estadísticas de parcela.',
            '100 menos nubosidad no equivale a cobertura válida; puede reflejar ubicación/calidad.'),
    'P05': ('T05', 'Jass', 'Dani', 'Antigüedad y acceso a la edición de relieve',
            'Confirmar fecha de adquisición/edición y disponibilidad histórica del CEM4 recibido; acceso y cobertura para parcelas nuevas.',
            'Estático no significa conocido desde cualquier fecha ni válido sin revisar cambios de contorno.'),
    'P06': ('T02', 'Jass', 'Dani', 'Etiqueta, superficie y grupo de registro',
            'Confirmar denominador sembrado/cosechado, protocolo/humedad del rendimiento y equivalencia de área; documentar procedencia del grupo de registro.',
            'No calcular producción confirmada ni inferir variedad/manejo a partir de Cebada/CEBADA.'),
    'P07': ('T02', 'Jass', 'Dani', 'Catálogo disponible para una campaña nueva',
            'Obtener contornos, IDs, municipio y fecha de vigencia; verificar cómo se obtienen antes de predecir.',
            'Tener el catálogo 2025 no acredita información de otra campaña.'),
    'P08': ('T03', 'Migue', 'Jass', 'Fecha objetivo y admisibilidad operacional',
            'Antes de cambiar el uso retrospectivo, acordar fecha objetivo y exigir evidencias de publicación/edición de cada entrada.',
            'No cambiar corte, ventanas, particiones o presupuesto desde estas fichas.'),
}
FUENTES = (
    'docs/t04_version_disponibilidad.md', 'registro/t04/manifest.json',
    'docs/T06_satelite.md', 'registro/t06/variables_satelitales_diccionario.csv',
    'scripts/t06_satelite.py', 'docs/t05_relieve.md', 'registro/t05/procedencia.json',
    'docs/T03_protocolo_evaluacion.md',
)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def cargar_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def exigir(condicion, mensaje):
    if not condicion:
        raise ValueError(mensaje)


def csv_bytes(campos, filas):
    texto = io.StringIO(newline='')
    w = csv.DictWriter(texto, fieldnames=campos, lineterminator='\n')
    w.writeheader()
    w.writerows(filas)
    return texto.getvalue().encode('utf-8')


def json_bytes(obj):
    return (json.dumps(obj, ensure_ascii=False, indent=2) + '\n').encode('utf-8')


def leer_contrato(raiz):
    entrega = raiz / ENTREGA
    m = cargar_json(entrega / 'manifest.json')
    exigir(m['schema'] == 't07_integracion_bloques_v2', 'Revisar versión de entrega T07')
    exigir(set(m['archivos_sha256']) == {p.name for p in entrega.iterdir()} - {'manifest.json'},
           'Inventario de entrega T07 incompleto')
    for n, h in m['archivos_sha256'].items():
        exigir(sha(entrega / n) == h, f'Entrega T07 alterada: {n}')
    contrato = cargar_json(entrega / 'contrato_columnas.json')
    exigir(contrato['schema'] == 't07_columnas_por_funcion_v2', 'Revisar versión de roles T07')
    with (entrega / 'tabla_comun.csv').open(encoding='utf-8', newline='') as f:
        columnas = next(csv.reader(f))  # No se leen los valores ni el rendimiento.
    with (entrega / 'diccionario_columnas.csv').open(encoding='utf-8', newline='') as f:
        lector = csv.DictReader(f)
        exigir(tuple(lector.fieldnames) == DICCIONARIO, 'Revisar esquema del diccionario')
        dic = [r for r in lector if r['archivo'] == 'tabla_comun.csv']
    exigir(len(columnas) == len(set(columnas)), 'Cabecera duplicada')
    exigir(len(columnas) == 60, 'Cambió la entrega de 60 columnas; revisar alcance de las fichas')
    exigir(len(dic) == len(columnas) and {r['columna'] for r in dic} == set(columnas),
           'Ficha sin definición única por columna')
    roles = [(c, rol) for rol, cols in contrato['columnas_por_funcion'].items() for c in cols]
    exigir(len(roles) == len(columnas) and {c for c, _ in roles} == set(columnas),
           'Roles incompletos o duplicados')
    por_columna = {r['columna']: r for r in dic}
    exigir(all(por_columna[c]['funcion'] == rol for c, rol in roles), 'Rol contradictorio')
    exigir({r['columna'] for r in dic if 'no documentada' in r['unidad']} ==
           set(contrato['unidades_fisicas_pendientes']), 'Unidades pendientes contradictorias')
    exigir(contrato['experimentos_definidos'] is False, 'Revisar contrato de experimentos nuevo')
    exigir(contrato['area_t10']['candidata']['columna'] == 'area_ha_origen' and
           contrato['area_t10']['rol_en_t07'] == 'metadato', 'Contrato de área T10 cambió')
    return [por_columna[c] for c in columnas], contrato, m


def periodo(ficha, contrato):
    c = ficha['columna']
    for w, v in contrato['ventanas'].items():
        if c.endswith('_' + w):
            exigir(v['inicio'] in ('2025-04-01', '2025-06-01') and v['fin'] == '2025-10-31',
                   'Revisar campaña/corte antes de reutilizar fichas')
            return f"{v['inicio']}/{v['fin']}"
    if c in contrato['al_corte']['columnas']:
        v = contrato['al_corte']
        exigir((v['inicio'], v['fin']) == ('2025-10-17', '2025-10-31'), 'Corte cambió')
        return f"{v['inicio']}/{v['fin']}"
    return ficha['periodo']


def complementar(d, contrato):
    c, producto, rol = d['columna'], d['producto'], d['funcion']
    r = dict(d, periodo_resumen=periodo(d, contrato),
             fecha_publicacion='no documentada', disponibilidad_al_corte='no acreditada',
             unidad_estado='pendiente' if c in contrato['unidades_fisicas_pendientes'] else 'documentada',
             aclaracion_faltante=d['significado_vacio'])
    if producto == 'catálogo T02':
        exigir(c in {'id_parcela', 'campania', 'rendimiento_t_ha', 'area_ha_origen', 'municipio',
                     'estado', 'cultivo_origen', 'conjunto_origen'}, f'Catálogo nuevo sin ficha: {c}')
        r.update(tarea_fuente='T02', responsable_fuente='Jass', revisa_fuente='Dani',
                 version_producto='Catálogo original FIRA identificado por la entrega T02/T07; edición no documentada',
                 evidencia_disponibilidad='Paquete y catálogo presentes; no prueba de disponibilidad antes del corte',
                 soporte_espacial='Una fila por ID y contorno original; municipio declarado',
                 control_calidad='registro/t07/calidad_parcelas.csv; catálogo y auditoría T02',
                 requisitos_campania_futura='Obtener catálogo de la nueva campaña, contornos e identidad estable; verificar municipio y vigencia. Las etiquetas futuras se reservan para evaluar después.',
                 acceso_futuro='Por confirmar con quien provea el catálogo de la nueva campaña',
                 limite_interpretacion='No inferir variedad ni manejo del texto Cultivo; área declarada no confirma denominador de rendimiento.',
                 pendientes='P07', fuentes='registro/t07/contrato_columnas.json; registro/t07/inventario_fuentes.json')
        usos = {
            'municipio': ('T08/T09 y frentes territoriales', 'Candidata categórica; referencias y respaldos sólo con entrenamiento conforme T03'),
            'area_ha_origen': ('T10', 'Candidata explícita T10; conserva rol metadato; no entrada automática T09'),
            'cultivo_origen': ('T08/T03', 'Referencia y evaluación; respaldo aprendido sólo en entrenamiento; no predictor automático'),
            'rendimiento_t_ha': ('Evaluación/entrenamiento', 'Objetivo; nunca entrada del modelo ni imputación de las 59 etiquetas'),
        }
        r['frente_de_uso'], r['condicion_de_uso'] = usos.get(c, ('Identidad/auditoría', 'Metadato; no predictor'))
        if c in {'area_ha_origen', 'cultivo_origen', 'rendimiento_t_ha'}:
            r['pendientes'] += ';P06'
        if c in {'id_parcela', 'campania', 'conjunto_origen', 'rendimiento_t_ha'}:
            r['disponibilidad_al_corte'] = 'no aplica como entrada predictiva'
        if c == 'rendimiento_t_ha':
            r['fecha_publicacion'] = 'no documentada; no requerida como entrada para predecir'
    elif producto in {'CHIRPS', 'CHIRTS-ERA5'}:
        exigir(rol == 'predictor_candidato' and c.startswith(('prec_acumulada_mm_', 'tmin_media_c_', 'tmax_media_c_')), 'Clima sin ficha explícita')
        r.update(tarea_fuente='T04', responsable_fuente='Dani', revisa_fuente='Jass',
                 frente_de_uso='T09; T14/T15 con experimento definido',
                 condicion_de_uso='Candidata retrospectiva; ventana y variables elegidas dentro del entrenamiento según T03',
                 version_producto=f'{producto}; número y variante preliminar/final no documentados en FIRA',
                 evidencia_disponibilidad='docs/t04_version_disponibilidad.md: los plazos generales del proveedor no certifican los TIFF mensuales recibidos',
                 soporte_espacial='Rejilla nativa 0.05 grados EPSG:4326; media por área física intersectada; no resolución parcelaria independiente',
                 control_calidad='registro/t07/calidad_ventanas.csv por ID/ventana/variable; T04 por mes',
                 requisitos_campania_futura='Obtener mensuales y ediciones del nuevo año, con publicación verificable al instante objetivo; repetir extracción para los contornos y exigir todos los meses de la ventana.',
                 acceso_futuro='Confirmar canal, edición y continuidad de los productos; el ZIP 2025 no abastece otra campaña',
                 limite_interpretacion='Mes observado no equivale a mes publicado; Tmin/Tmax mensuales no identifican días de helada; sin inferir siembra.',
                 pendientes='P01;P08', fuentes='docs/t04_version_disponibilidad.md; registro/t04/manifest.json; registro/t07/inventario_fuentes.json')
    elif producto in {'Planet', 'Sentinel-2', 'Landsat'}:
        pref = {'Planet': 'pl_', 'Sentinel-2': 's2_', 'Landsat': 'ls_'}[producto]
        exigir(c.startswith(pref) and rol in {'calidad', 'predictor_candidato'}, 'Sensor/rol sin ficha explícita')
        r.update(tarea_fuente='T06', responsable_fuente='Daf', revisa_fuente='Jass',
                 frente_de_uso='T11; T13/T15 con experimento definido',
                 condicion_de_uso=('Calidad; T11 ya prevé controles explícitos con calidad; no predictor automático' if rol == 'calidad' else
                                   'Candidata; mantener sensor y ventana; selección/preprocesado dentro del entrenamiento'),
                 version_producto=f'{producto} del paquete FIRA; edición y versión de procesamiento no documentadas en T06',
                 evidencia_disponibilidad='docs/T06_satelite.md §1: fecha_disponible no documentada; fecha_observada no la sustituye',
                 soporte_espacial='Estadísticas por parcela y captura; conservar sensor; máscara/bordes no documentados; no asignar resolución del sensor a una estadística independiente',
                 control_calidad='registro/t07/calidad_satelite.csv; registro/t06/cobertura_ventana.csv; umbral heredado de T06',
                 requisitos_campania_futura='Obtener series equivalentes del mismo sensor, índices, escala, nubosidad y fechas; recortar al corte antes de suavizar. Confirmar definición/procesamiento y acceso; no intercambiar sensores.',
                 acceso_futuro='No acreditado para las series equivalentes de FIRA; verificar permisos, canal, procesamiento y costes si corresponden',
                 limite_interpretacion='Rasgos de la curva no son fechas de siembra confirmadas; mínimo previo al máximo no demuestra suelo desnudo; nubosidad no es cobertura válida.',
                 pendientes='P02;P04;P08', fuentes='docs/T06_satelite.md; registro/t06/variables_satelitales_diccionario.csv; scripts/t06_satelite.py')
        if r['unidad_estado'] == 'pendiente':
            r['pendientes'] += ';P03'
        if c.endswith('_al_corte'):
            # La selección final es de 15 días, pero la curva se suaviza en abr_oct.
            r['periodo_insumos_necesarios'] = '2025-04-01/2025-10-31 (curva abr_oct); puede usar una captura válida anterior al 17-oct para suavizar la primera seleccionada'
            r['aclaracion_faltante'] = 'Sin captura válida entre 17 y 31 de octubre; no equivale a NDVI cero. Se selecciona al final de la curva abr_oct suavizada.'
    elif producto == 'INEGI CEM4':
        exigir(c in {'elevacion_media_m', 'pendiente_media_t10_grados'} and rol == 'predictor_candidato', 'Relieve sin ficha explícita')
        r.update(tarea_fuente='T05', responsable_fuente='Jass', revisa_fuente='Dani',
                 frente_de_uso='T10; T15 con experimento definido', condicion_de_uso='Candidata; conservar D020 para pendiente; cualquier imputación se aprende en entrenamiento',
                 version_producto='CEM4 según entrega; adquisición/edición y publicación del recorte no documentadas',
                 evidencia_disponibilidad='docs/t05_relieve.md; registro/t05/procedencia.json: producto/huellas conocidos, antigüedad no acreditada',
                 soporte_espacial='EPSG:6372; celdas de 120 m; media por intersección de área plana válida; muchas parcelas son menores que una celda',
                 control_calidad='registro/t07/calidad_relieve.csv; cobertura, NoData, celdas, centroide y D020',
                 requisitos_campania_futura='Comprobar vigencia y acceso a la edición del relieve; reextraer si cambian contornos/cobertura; conservar CRS, resolución y controles, sin copiar ciegamente valores por ID.',
                 acceso_futuro='La copia actual existe; acceso/edición para otro territorio o momento requiere verificación',
                 limite_interpretacion='Relieve estático suministrado no acredita fecha de adquisición; medias de celdas no son medición fina de toda la parcela.',
                 pendientes='P05;P08', fuentes='docs/t05_relieve.md; registro/t05/procedencia.json; registro/t07/contrato_columnas.json')
        r['aclaracion_faltante'] = ('Sin media válida de elevación; D020 no se aplica a elevación.' if c == 'elevacion_media_m' else
                                   'Sin media válida o cobertura de pendiente menor que 0.5 (D020); el original queda en calidad_relieve.csv.')
    else:
        raise ValueError(f'Producto sin ficha: {producto}')
    r.setdefault('periodo_insumos_necesarios', r['periodo_resumen'])
    exigir(set(r) == set(CAMPOS) and all(str(v).strip() for v in r.values()), f'Ficha incompleta: {c}')
    return r


def construir(raiz=RAIZ):
    raiz = Path(raiz).resolve()
    dic, contrato, entrega = leer_contrato(raiz)
    fichas = [complementar(d, contrato) for d in dic]
    pendientes = []
    for k, (t, r, rev, asunto, accion, efecto) in PENDIENTES.items():
        cols = [f['columna'] for f in fichas if k in f['pendientes'].split(';')]
        if cols:
            pendientes.append(dict(id=k, tarea=t, responsable=r, revisa=rev, asunto=asunto,
                                   accion=accion, efecto=efecto, columnas=';'.join(cols),
                                   estado='pendiente_documental; no es un fallo de cálculo'))
    archivos = {'fichas_atributos.csv': csv_bytes(CAMPOS, fichas),
                'pendientes_documentales.csv': csv_bytes(tuple(pendientes[0]), pendientes)}
    fuentes = sorted({*FUENTES, f'{ENTREGA}/manifest.json',
                      *(f'{ENTREGA}/{n}' for n in entrega['archivos_sha256'])})
    manifest = dict(schema='t07_fichas_atributos_v1',
        alcance='Punto 1: documentación de las 60 columnas de tabla_comun; no incluye análisis estadístico ni selección de atributos',
        estado='complemento_local_para_revision_Jass', fuentes_sha256={n: sha(raiz / n) for n in fuentes},
        codigo_sha256={'scripts/t07_fichas_atributos.py': sha(raiz / 'scripts/t07_fichas_atributos.py')},
        archivos_sha256={n: hashlib.sha256(b).hexdigest() for n, b in archivos.items()},
        fichas=len(fichas), roles=dict(Counter(r['funcion'] for r in fichas)),
        unidades_pendientes=[r['columna'] for r in fichas if r['unidad_estado'] == 'pendiente'],
        pendientes_documentales=len(pendientes), lee_valores_para_analisis=False,
        selecciona_atributos=False, entrena=False, disponibilidad_operacional_certificada=False,
        origen_estado_entrega=entrega['estado_entrega'], cierre_en_manifest_original=entrega['cierre_t07'],
        aclaracion_estado='Estado del cálculo original conservado; merge/revisión GitHub se documentan aparte y no se infieren de una ejecución.')
    archivos['manifest.json'] = json_bytes(manifest)
    return archivos


def generar(salida, raiz=RAIZ):
    raiz, salida = Path(raiz).resolve(), Path(salida).resolve()
    protegidas = [raiz / 'data', raiz / 'scripts', raiz / 'docs', raiz / 'tests', raiz / 'analisis',
                  raiz / '.git', raiz / 'registro/t07', raiz / 'registro/t02', raiz / 'registro/t03',
                  raiz / 'registro/t04', raiz / 'registro/t05', raiz / 'registro/t06', raiz / 'registro/t08']
    exigir(salida != raiz and not any(salida == p or salida.is_relative_to(p) for p in protegidas), 'Salida protegida')
    exigir(not salida.exists(), 'La salida ya existe; usar carpeta nueva para no sobrescribir evidencia')
    archivos = construir(raiz)
    salida.parent.mkdir(parents=True, exist_ok=True)
    temp = Path(tempfile.mkdtemp(prefix='.t07-fichas-', dir=salida.parent))
    try:
        for n, b in archivos.items():
            (temp / n).write_bytes(b)
        temp.rename(salida)
    except BaseException:
        shutil.rmtree(temp)
        raise
    return {'resultado': 'generado', 'fichas': cargar_json(salida / 'manifest.json')['fichas']}


def verificar(salida, raiz=RAIZ):
    salida = Path(salida)
    esperados = construir(raiz)
    exigir({p.name for p in salida.iterdir()} == set(esperados), 'Archivos de fichas incompletos o ajenos')
    for n, b in esperados.items():
        exigir((salida / n).read_bytes() == b, f'Ficha/procedencia desactualizada o alterada: {n}')
    return dict(resultado='verificado', fichas=json.loads(esperados['manifest.json'])['fichas'], punto_2_iniciado=False)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    modos = p.add_mutually_exclusive_group(required=True)
    modos.add_argument('--generar', type=Path)
    modos.add_argument('--verificar', type=Path)
    a = p.parse_args()
    try:
        r = generar(a.generar) if a.generar else verificar(a.verificar)
    except (ValueError, KeyError, OSError, StopIteration) as e:
        p.exit(1, f'Fichas T07 detenidas: {e}\n')
    print(json.dumps(r, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
