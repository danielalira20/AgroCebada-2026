"""T12 paso 7: comparador de reproducciones.

Compara una carpeta de reproducción (la que escribe `python -m scripts.t12_evaluar --salida reports/...`,
por ejemplo en Docker sobre Windows, Mac o amd64 emulado) contra la evidencia oficial de `registro/t12/`.
Solo lee: no modifica `registro/t12/` ni la reproducción. Escribe un informe `reproduccion_t12.json` dentro
de la carpeta de reproducción (nunca sobrescribe y nunca escribe en la carpeta oficial).

Qué comprueba, en este orden:
  1. Que las dos carpetas tengan los 5 CSV y el manifest, y que los manifests describan lo mismo:
     diseño, comprobaciones, procedimientos, contextos, entradas y código con las mismas huellas.
     Si no coinciden, el resultado es `no_comparable`: no se compara aritmética de otro código u otras entradas.
  2. Que las huellas `salidas_sha256` de cada manifest correspondan a los archivos que hay en su carpeta
     (nadie editó una salida a mano).
  3. Tabla por tabla, alineando por las claves de cada una (no por posición): mismas filas, mismas columnas,
     texto y banderas idénticos, números iguales con el criterio de T15 (`atol=1e-12`, `rtol=1e-10`).
  4. Que cada contexto haya elegido la misma opción en la selección interna.

Resultados posibles: `identica_byte_a_byte`, `reproduce_dentro_de_tolerancia`, `no_reproduce`, `no_comparable`.
El código de salida es 0 solo en los dos primeros. El entorno (sistema, Python, numpy, pandas, scikit-learn) se
reporta como información: una diferencia de entorno no invalida nada por sí sola.
"""
import argparse
import csv
import json
import math
from pathlib import Path

from scripts.evaluacion_comun_contrato import ATOL, RTOL, exigir, sha

VERSION = 't12-reproducir-v1'
RAIZ = Path(__file__).resolve().parents[1]
CARPETA_OFICIAL = 'registro/t12'
SALIDA = 'reproduccion_t12.json'
MANIFEST = 'manifest.json'
MAX_EJEMPLOS = 5

CLAVES = {
    'predicciones_oof_t12.csv': ('ID_POLIGONO', 'repeticion', 'particion', 'escenario', 'candidato'),
    'seleccion_interna_t12.csv': ('candidato', 'escenario', 'repeticion', 'particion', 'opcion', 'internas'),
    'metricas_t12.csv': ('candidato', 'escenario', 'subconjunto', 'repeticion'),
    'comparacion_emparejada_t12.csv': ('tipo', 'candidato', 'frente_a', 'escenario', 'subconjunto'),
    'predicciones_59_t12.csv': ('candidato', 'ID_POLIGONO'),
}
# Campos del manifest que deben coincidir exactamente para que la comparación tenga sentido.
IGUALES_EN_MANIFEST = ('schema', 'version', 'version_modelos', 'sha_diseno_t12', 'sha_comprobaciones',
                       'contextos_externos', 'procedimientos', 'filas_oof', 'ajustes_finales_59',
                       'entradas_sha256', 'codigo_sha256')
# Campos que se reportan pero no invalidan.
INFORMATIVOS_EN_MANIFEST = ('entorno', 'procesos')


# ------------------------------------------------------------------ lectura
def leer_tabla(ruta):
    """Lee un CSV como texto crudo: lista de columnas y lista de diccionarios sin interpretar."""
    with Path(ruta).open(encoding='utf-8-sig', newline='') as f:
        lector = csv.DictReader(f)
        columnas = list(lector.fieldnames or [])
        filas = list(lector)
    return columnas, filas


def a_numero(texto):
    """Devuelve float si el texto es un número (incluye nan e inf), si no None."""
    try:
        return float(texto)
    except (TypeError, ValueError):
        return None


def comparar_celda(a, b):
    """(igual_en_texto, dentro_de_tolerancia, dif_abs, dif_rel). Los vacíos solo igualan a vacíos."""
    if a == b:
        return True, True, 0.0, 0.0
    x, y = a_numero(a), a_numero(b)
    if x is None or y is None:
        return False, False, math.nan, math.nan
    if math.isnan(x) and math.isnan(y):
        return False, True, 0.0, 0.0
    if math.isnan(x) or math.isnan(y) or math.isinf(x) or math.isinf(y):
        return False, False, math.inf, math.inf
    dif = abs(x - y)
    escala = max(abs(x), abs(y))
    rel = dif / escala if escala > 0 else 0.0
    return False, math.isclose(x, y, rel_tol=RTOL, abs_tol=ATOL), dif, rel


def indexar(filas, claves, etiqueta):
    indice = {}
    for i, fila in enumerate(filas):
        k = tuple(fila[c] for c in claves)
        exigir(k not in indice, f'{etiqueta}: clave repetida {k}')
        indice[k] = fila
    return indice


# ------------------------------------------------------------------ una tabla
def comparar_tabla(nombre, ruta_oficial, ruta_repro):
    """Informe de una tabla. Nunca lanza por diferencias: las reporta."""
    claves = CLAVES[nombre]
    col_o, fil_o = leer_tabla(ruta_oficial)
    col_r, fil_r = leer_tabla(ruta_repro)
    inf = dict(archivo=nombre, filas_oficial=len(fil_o), filas_reproduccion=len(fil_r),
               columnas_iguales=col_o == col_r, byte_a_byte=sha(ruta_oficial) == sha(ruta_repro),
               claves=list(claves))
    problemas = []
    if col_o != col_r:
        problemas.append(f'columnas distintas: solo oficial {sorted(set(col_o) - set(col_r))}, '
                         f'solo reproducción {sorted(set(col_r) - set(col_o))}')
    faltan = [c for c in claves if c not in col_o or c not in col_r]
    if faltan:
        problemas.append(f'faltan columnas clave: {faltan}')
        inf.update(celdas_comparadas=0, celdas_distintas_en_texto=0, celdas_fuera_de_tolerancia=0,
                   max_dif_abs=None, max_dif_rel=None, filas_solo_oficial=None, filas_solo_reproduccion=None,
                   ejemplos=[], problemas=problemas, aprobada=False)
        return inf
    try:
        idx_o, idx_r = indexar(fil_o, claves, f'{nombre} (oficial)'), indexar(fil_r, claves, f'{nombre} (reproducción)')
    except ValueError as error:
        problemas.append(str(error))
        inf.update(celdas_comparadas=0, celdas_distintas_en_texto=0, celdas_fuera_de_tolerancia=0,
                   max_dif_abs=None, max_dif_rel=None, filas_solo_oficial=None, filas_solo_reproduccion=None,
                   ejemplos=[], problemas=problemas, aprobada=False)
        return inf
    solo_o, solo_r = sorted(set(idx_o) - set(idx_r)), sorted(set(idx_r) - set(idx_o))
    if solo_o or solo_r:
        problemas.append(f'filas que no se corresponden: {len(solo_o)} solo en lo oficial, {len(solo_r)} solo en la reproducción')
    comunes = [c for c in col_o if c in col_r]
    comparadas = distintas_texto = fuera = 0
    max_abs = max_rel = 0.0
    por_columna = {}
    ejemplos = []
    for k in sorted(set(idx_o) & set(idx_r)):
        for c in comunes:
            a, b = idx_o[k][c], idx_r[k][c]
            comparadas += 1
            igual, dentro, dif, rel = comparar_celda(a, b)
            if igual:
                continue
            distintas_texto += 1
            if dentro:
                max_abs = max(max_abs, dif)
                max_rel = max(max_rel, rel)
                continue
            fuera += 1
            por_columna[c] = por_columna.get(c, 0) + 1
            if math.isfinite(dif):
                max_abs = max(max_abs, dif)
            if len(ejemplos) < MAX_EJEMPLOS:
                ejemplos.append(dict(clave=dict(zip(claves, k)), columna=c, oficial=a, reproduccion=b))
    if fuera:
        problemas.append(f'{fuera} celdas fuera de tolerancia (atol={ATOL:g}, rtol={RTOL:g}) en {sorted(por_columna)}')
    inf.update(celdas_comparadas=comparadas, celdas_distintas_en_texto=distintas_texto,
               celdas_fuera_de_tolerancia=fuera, max_dif_abs=max_abs, max_dif_rel=max_rel,
               celdas_fuera_por_columna=por_columna, filas_solo_oficial=len(solo_o),
               filas_solo_reproduccion=len(solo_r), ejemplos=ejemplos, problemas=problemas,
               aprobada=not problemas)
    return inf


def opciones_elegidas(ruta):
    """{(candidato, escenario, repeticion, particion): opcion elegida} de la selección interna."""
    _, filas = leer_tabla(ruta)
    elegidas = {}
    for f in filas:
        if f['elegida'] == 'True':
            k = (f['candidato'], f['escenario'], f['repeticion'], f['particion'])
            exigir(k not in elegidas, f'selección interna: más de una opción elegida en {k}')
            elegidas[k] = f['opcion']
    return elegidas


def comparar_elecciones(ruta_oficial, ruta_repro):
    try:
        o, r = opciones_elegidas(ruta_oficial), opciones_elegidas(ruta_repro)
    except (ValueError, KeyError) as error:
        return dict(contextos_oficial=0, contextos_reproduccion=0, contextos_con_otra_opcion=0,
                    contextos_sin_pareja=0, ejemplos=[], error=str(error), aprobada=False)
    distintas = sorted(k for k in set(o) & set(r) if o[k] != r[k])
    solo = sorted(set(o) ^ set(r))
    return dict(contextos_oficial=len(o), contextos_reproduccion=len(r),
                contextos_con_otra_opcion=len(distintas), contextos_sin_pareja=len(solo),
                ejemplos=[dict(candidato=k[0], escenario=k[1], repeticion=k[2], particion=k[3],
                               oficial=o[k], reproduccion=r[k]) for k in distintas[:MAX_EJEMPLOS]],
                aprobada=not distintas and not solo)


# ------------------------------------------------------------------ manifests
def leer_manifest(carpeta):
    return json.loads((Path(carpeta) / MANIFEST).read_text(encoding='utf-8'))


def verificar_integridad(carpeta, manifest, etiqueta):
    """Las huellas del manifest corresponden a los archivos presentes."""
    problemas = []
    huellas = manifest.get('salidas_sha256', {})
    if set(huellas) != set(CLAVES):
        problemas.append(f'{etiqueta}: el manifest no lista exactamente los 5 CSV')
    for nombre, huella in huellas.items():
        ruta = Path(carpeta) / nombre
        if not ruta.exists():
            problemas.append(f'{etiqueta}: falta {nombre}')
        elif sha(ruta) != huella:
            problemas.append(f'{etiqueta}: {nombre} no coincide con la huella de su manifest')
    return problemas


def comparar_manifests(oficial, repro):
    distintos = {c: dict(oficial=oficial.get(c), reproduccion=repro.get(c))
                 for c in IGUALES_EN_MANIFEST if oficial.get(c) != repro.get(c)}
    info = {c: dict(oficial=oficial.get(c), reproduccion=repro.get(c),
                    iguales=oficial.get(c) == repro.get(c)) for c in INFORMATIVOS_EN_MANIFEST}
    return distintos, info


# ------------------------------------------------------------------ comparación completa
def resolver(carpeta, raiz):
    carpeta = Path(carpeta)
    return (carpeta if carpeta.is_absolute() else Path(raiz) / carpeta).resolve()


def comparar(reproduccion, raiz=RAIZ, oficial=CARPETA_OFICIAL, etiqueta=''):
    """Devuelve el informe completo. Lanza ValueError solo ante errores de uso (carpeta inexistente, misma carpeta)."""
    raiz = Path(raiz).resolve()
    ruta_o, ruta_r = resolver(oficial, raiz), resolver(reproduccion, raiz)
    exigir(ruta_o.is_dir(), f'No existe la carpeta oficial: {ruta_o}')
    exigir(ruta_r.is_dir(), f'No existe la carpeta de reproducción: {ruta_r}')
    exigir(ruta_o != ruta_r, 'La reproducción no puede ser la propia carpeta oficial')
    informe = dict(schema='reproduccion_t12_v1', version=VERSION, etiqueta=etiqueta,
                   tolerancia=dict(atol=ATOL, rtol=RTOL, criterio='T15: |a-b| <= max(rtol*max(|a|,|b|), atol)'),
                   carpeta_oficial=str(ruta_o), carpeta_reproduccion=str(ruta_r))
    faltantes = [f'{c}/{n}' for c, p in (('oficial', ruta_o), ('reproduccion', ruta_r))
                 for n in list(CLAVES) + [MANIFEST] if not (p / n).exists()]
    if faltantes:
        informe.update(resultado='no_comparable', aprobada=False, problemas=[f'faltan archivos: {faltantes}'])
        return informe
    m_o, m_r = leer_manifest(ruta_o), leer_manifest(ruta_r)
    distintos, entorno = comparar_manifests(m_o, m_r)
    integridad = verificar_integridad(ruta_o, m_o, 'oficial') + verificar_integridad(ruta_r, m_r, 'reproduccion')
    informe.update(manifest=dict(campos_distintos=distintos, informativos=entorno), integridad=integridad)
    if distintos:
        informe.update(resultado='no_comparable', aprobada=False,
                       problemas=[f'el manifest difiere en {sorted(distintos)}: la reproducción no usó el mismo '
                                  'diseño, código o entradas'])
        return informe
    if integridad:
        informe.update(resultado='no_reproduce', aprobada=False, problemas=integridad)
        return informe
    tablas = [comparar_tabla(n, ruta_o / n, ruta_r / n) for n in CLAVES]
    elecciones = comparar_elecciones(ruta_o / 'seleccion_interna_t12.csv', ruta_r / 'seleccion_interna_t12.csv')
    ok = all(t['aprobada'] for t in tablas) and elecciones['aprobada']
    identica = ok and all(t['byte_a_byte'] for t in tablas)
    problemas = [f"{t['archivo']}: {p}" for t in tablas for p in t['problemas']]
    if elecciones.get('error'):
        problemas.append(f"selección interna ilegible: {elecciones['error']}")
    elif not elecciones['aprobada']:
        problemas.append(f"{elecciones['contextos_con_otra_opcion']} contextos eligieron otra opción en la selección interna "
                         f"y {elecciones['contextos_sin_pareja']} no tienen pareja")
    maximos = [t['max_dif_abs'] for t in tablas if t['max_dif_abs'] is not None]
    informe.update(tablas=tablas, selecciones=elecciones, problemas=problemas, aprobada=ok,
                   max_dif_abs=max(maximos) if maximos else None,
                   max_dif_rel=max([t['max_dif_rel'] for t in tablas if t['max_dif_rel'] is not None], default=None),
                   resultado='identica_byte_a_byte' if identica else
                   ('reproduce_dentro_de_tolerancia' if ok else 'no_reproduce'))
    return informe


def escribir_informe(informe, destino):
    """Escribe el informe en la reproducción. Nunca sobrescribe ni escribe en lo oficial."""
    destino = Path(destino)
    exigir(destino != Path(informe['carpeta_oficial']), 'No se escribe en la carpeta oficial')
    ruta = destino / SALIDA
    exigir(not ruta.exists(), f'Conservar evidencia: ya existe {ruta}')
    ruta.write_text(json.dumps(informe, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return ruta


def resumen(informe):
    lineas = ['Reproducción de T12 contra registro/t12' + (f' · {informe["etiqueta"]}' if informe.get('etiqueta') else '')]
    for t in informe.get('tablas', []):
        estado = 'idéntica' if t['byte_a_byte'] else ('OK dentro de tolerancia' if t['aprobada'] else 'DIFERENTE')
        dif = '' if t['max_dif_abs'] is None else f"  (máx. dif. {t['max_dif_abs']:.2e})"
        lineas.append(f"  {t['archivo']:<34} {t['filas_oficial']:>6} filas  {estado}{dif}")
    if 'selecciones' in informe:
        s = informe['selecciones']
        lineas.append(f"  opciones elegidas: {s['contextos_oficial'] - s['contextos_con_otra_opcion']} de "
                      f"{s['contextos_oficial']} contextos coinciden")
    if 'manifest' in informe:
        e = informe['manifest']['informativos'].get('entorno', {})
        if e and not e.get('iguales'):
            lineas.append(f"  entorno distinto (informativo): oficial {e['oficial']} · reproducción {e['reproduccion']}")
    for p in informe.get('problemas', []):
        lineas.append(f'  PROBLEMA: {p}')
    titulo = {'identica_byte_a_byte': 'REPRODUCCIÓN IDÉNTICA BYTE A BYTE',
              'reproduce_dentro_de_tolerancia': 'REPRODUCCIÓN APROBADA (diferencias dentro de la tolerancia)',
              'no_reproduce': 'LA REPRODUCCIÓN NO COINCIDE', 'no_comparable': 'NO SE PUEDE COMPARAR'}[informe['resultado']]
    lineas.append(titulo)
    return '\n'.join(lineas)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--raiz', type=Path, default=RAIZ)
    p.add_argument('--reproduccion', type=Path, required=True,
                   help='carpeta escrita por t12_evaluar, p. ej. reports/t12_repro')
    p.add_argument('--oficial', type=Path, default=Path(CARPETA_OFICIAL))
    p.add_argument('--etiqueta', default='', help='texto libre, p. ej. "Mac arm64, Docker, amd64"')
    p.add_argument('--sin-informe', action='store_true', help='solo imprime; no escribe reproduccion_t12.json')
    a = p.parse_args(argv)
    informe = comparar(a.reproduccion, a.raiz, a.oficial, a.etiqueta)
    print(resumen(informe))
    if not a.sin_informe:
        print(f'Guardado en {escribir_informe(informe, informe["carpeta_reproduccion"])}')
    return 0 if informe['aprobada'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
