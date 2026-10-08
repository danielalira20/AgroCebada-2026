"""Fase 3 T07: integración por bloques; borradores T04 sólo en reports/."""
import argparse
from collections import Counter
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.t07_fuentes import BASE, leer_csv, leer_entrega, sha, validar_catalogo, guardar_csv, guardar_json
from scripts.t07_ventanas import agregar, LARGA, ANCHA, CALIDAD, VENTANAS
from scripts.t07_diccionario import diccionario, CAMPOS
from scripts.t07_preparar import RAIZ, T02, T02_ARCHIVOS, revision, comprobar_fuente, comprobar_copia
from scripts.t07_satelite import validar, unir, diccionario_satelite, diccionario_calidad, CALIDAD as CALIDAD_SAT, CORTE, META

T06_ARCHIVOS = ("registro/t06/variables_satelitales.csv", "registro/t06/variables_satelitales_diccionario.csv",
                "registro/t06/cobertura_ventana.csv", "docs/T06_satelite.md", "scripts/t06_satelite.py")
CODIGO = ("t07_integrar.py", "t07_satelite.py", "t07_preparar.py", "t07_fuentes.py", "t07_ventanas.py",
          "t07_diccionario.py", "t07_preparar_insumos.py")


def comprobar_protocolo(texto):
    """Contrato explícito: un nuevo corte/ventana requiere revisar esta interfaz."""
    t = texto.replace('**', '')
    corte = re.findall(r'Momento de la estimación:([^\n]+)', t)
    ventanas = re.findall(r'Ventanas candidatas[^\n]+', t)
    if (len(corte) != 1 or 'hasta el 31 de octubre de 2025.' not in corte[0] or
            len(ventanas) != 1 or '1 de abril–31 de octubre y 1 de junio–31 de octubre.' not in ventanas[0]):
        raise ValueError("Corte/ventanas T03 cambió o no se reconoce; revisar contrato T07")


def integrar(base_dev, salida, clima=None, revision_t04=None, para_revision=False, raiz=RAIZ):
    raiz, salida = Path(raiz).resolve(), Path(salida).resolve()
    clima = Path(clima).resolve() if clima is not None else None
    if ((clima is None) != (revision_t04 is None)) or (para_revision and clima is None):
        raise ValueError("Indicar clima y revisión conjuntamente; revisión local requiere clima real")
    if salida == raiz or salida.is_relative_to(raiz / 'data/raw') or (clima and (salida == clima or salida.is_relative_to(clima))):
        raise ValueError("Salida protegida: no escribir sobre originales/entradas")
    if salida.exists():
        raise ValueError("La salida ya existe; reproducir en una carpeta nueva")
    if para_revision and not salida.is_relative_to(raiz / 'reports'):
        raise ValueError("Entrega pendiente de revisión sólo puede generarse en reports/")
    base = revision(base_dev, raiz)
    ht02 = {f'{T02}/{n}': comprobar_fuente(f'{T02}/{n}', base, raiz=raiz) for n in sorted(T02_ARCHIVOS)}
    _, filas = leer_csv(raiz / T02 / 'tablas/catalogo_parcelas.csv')
    catalogo = validar_catalogo(filas)
    ids = [r['id_parcela'] for r in catalogo]
    protocolo = 'docs/T03_protocolo_evaluacion.md'
    ht03 = comprobar_fuente(protocolo, base, raiz=raiz)
    comprobar_protocolo((raiz / protocolo).read_text(encoding='utf-8'))
    ht06 = {n: comprobar_fuente(n, base, raiz=raiz) for n in T06_ARCHIVOS}
    columnas, filas_sat = leer_csv(raiz / T06_ARCHIVOS[0])
    _, dic_sat = leer_csv(raiz / T06_ARCHIVOS[1])
    _, cov = leer_csv(raiz / T06_ARCHIVOS[2])
    sat, calidad_sat, equivalencias = validar(columnas, filas_sat, dic_sat, cov, catalogo)
    tablas = {'catalogo_base.csv': (BASE, catalogo), 'calidad_satelite.csv': (CALIDAD_SAT, calidad_sat)}
    definiciones = [r for r in diccionario() if r['archivo'] == 'catalogo_base.csv']
    definiciones += diccionario_calidad()
    inventario = dict(schema='t07_inventario_v2', base_dev=base, corte_observacional=CORTE.isoformat(),
        alcance='Reconstrucción retrospectiva; fecha observada no acredita disponibilidad histórica',
        cierre_t07=False, bloques={
            'T02': dict(estado='base_dev_identificada', archivos_sha256=ht02),
            'T03': dict(estado='protocolo_base_identificado_corte_provisional', archivos_sha256={protocolo: ht03},
                        reglas_evaluacion_no_modificadas=True),
            'T04': dict(estado='pendiente_integracion_revisada', integrado_en_t07=False, valores_generados=False),
            'T05': dict(estado='sin_entrega_identificada_en_esta_base', integrado=False, valores_generados=False),
            'T06': dict(estado='integrado_en_base_dev_aceptacion_no_inferida', integrado_en_t07=True,
                        archivos_sha256=ht06, columnas=44, conciliaciones_cobertura=len(calidad_sat))})
    ancha = None
    if clima is not None:
        rt04 = revision(revision_t04, raiz)
        origen, ht04 = comprobar_copia(clima, rt04, raiz)
        if origen['estado_revision_declarado'] != 'aceptada' and not para_revision:
            raise ValueError("T04 pendiente de aceptación: usar --para-revision con salida local en reports/")
        indice, m, pro, con = leer_entrega(clima, ids)
        if set(con.get('archivos_t02_sha256', {})) != T02_ARCHIVOS:
            raise ValueError("Referencia T02 T04 sin cinco archivos requeridos")
        for n, h in sorted(con['archivos_t02_sha256'].items()):
            comprobar_fuente(f'{T02}/{n}', base, h, raiz)
        larga, ancha, calidad = agregar(indice, ids)
        tablas.update({'clima_ventanas.csv': (LARGA, larga), 'clima_variables.csv': (ANCHA, ancha),
                       'calidad_ventanas.csv': (CALIDAD, calidad)})
        definiciones += [r for r in diccionario() if r['archivo'] != 'catalogo_base.csv']
        inventario['bloques']['T04'] = dict(estado=origen['estado_revision_declarado'],
            integrado_en_t07=True, valores_generados=True, revision_git=rt04, archivos_sha256=ht04,
            referencia_t02=con['revision_t02'], conciliacion='compatible_con_base_identificada',
            sha256_paquete_original=pro['sha256_paquete'], disponibilidad_historica=m['disponibilidad_historica_fira'],
            versiones_producto=m['versiones_producto_fira'], destino='borrador_local' if para_revision else 'entrega_con_fuente_aceptada')
    campos, comun = unir(catalogo, columnas, sat, ancha)
    tablas['tabla_comun.csv'] = (campos, comun)
    # La tabla ancha conserva roles: calidad no se convierte en predictor por estar cerca del objetivo.
    definiciones += [dict(r, archivo='tabla_comun.csv') for r in definiciones
                     if r['archivo'] == 'catalogo_base.csv' or (r['archivo'] == 'clima_variables.csv' and r['columna'] != 'id_parcela')]
    definiciones += diccionario_satelite(dic_sat)
    pares = {(r['archivo'], r['columna']) for r in definiciones}
    esperados = {(n, c) for n, (cab, _) in tablas.items() for c in cab}
    if pares != esperados or len(pares) != len(definiciones):
        raise ValueError("Diccionario T07 incompleto o duplicado")
    roles = {}
    unidades_pendientes = []
    for r in definiciones:
        if r['archivo'] == 'tabla_comun.csv':
            roles.setdefault(r['funcion'], []).append(r['columna'])
            if 'no documentada' in r['unidad']: unidades_pendientes.append(r['columna'])
    contrato = dict(schema='t07_columnas_por_funcion_v1', tabla='tabla_comun.csv',
                    columnas_por_funcion=roles, experimentos_definidos=False,
                    todas_las_columnas_no_equivalen_a_entradas_del_modelo=True,
                    unidades_fisicas_pendientes=unidades_pendientes,
                    ventanas={w: dict(inicio=p[0]+'-01', fin=CORTE.isoformat(), meses=len(p),
                                     dias=214 if w == 'abr_oct' else 153) for w, p in VENTANAS.items()},
                    al_corte=dict(inicio='2025-10-17', fin=CORTE.isoformat(), columnas=['pl_ndvi_al_corte', 's2_ndvi_al_corte']))
    controles = dict(parcelas=len(ids), etiquetas_originales=sum(r['rendimiento_t_ha'] != '' for r in comun),
        etiquetas_ausentes=sum(r['rendimiento_t_ha'] == '' for r in comun), columnas_tabla_comun=len(campos),
        filas_por_tabla={n: len(r) for n, (_, r) in tablas.items()},
        valores_satelitales_verificados=len(ids)*len(META), conciliaciones_cobertura=len(calidad_sat),
        ausencias_satelitales=sum(r[c] == '' for r in comun for c in META),
        estados_calidad_satelite=dict(Counter(r['estado'] for r in calidad_sat)),
        equivalencias_observadas_entre_ventanas=equivalencias, diccionario_columnas=len(definiciones),
        roles_tabla_comun={k: len(v) for k, v in roles.items()}, etiquetas_sin_transformar=True,
        aprende_del_rendimiento=False, usa_meses_posteriores_al_corte=False,
        cierre_t07=False, estado_entrega='borrador_local_para_revision' if para_revision else 'integracion_por_bloques_para_revision')
    if clima is not None:
        controles.update(filas_mensuales_verificadas=len(indice),
                         estados_ventanas=dict(Counter(r['estado'] for r in calidad)),
                         resumenes_climaticos_completos=sum(r['estado'] == 'completa' for r in calidad))
    salida.parent.mkdir(parents=True, exist_ok=True)
    temp = Path(tempfile.mkdtemp(prefix='.t07-integracion-', dir=salida.parent))
    try:
        for n, (cab, rows) in tablas.items(): guardar_csv(temp / n, cab, rows)
        guardar_csv(temp / 'diccionario_columnas.csv', CAMPOS, definiciones)
        guardar_json(temp / 'inventario_fuentes.json', inventario)
        guardar_json(temp / 'contrato_columnas.json', contrato)
        guardar_json(temp / 'controles.json', controles)
        guardar_json(temp / 'manifest.json', dict(schema='t07_integracion_bloques_v1',
            codigo_sha256={f'scripts/{n}': sha(raiz / 'scripts' / n) for n in CODIGO},
            entradas=dict(base_dev=base, revision_t04=revision_t04 and rt04),
            archivos_sha256={p.name: sha(p) for p in sorted(temp.iterdir())},
            estado_entrega=controles['estado_entrega'], clima_integrado=clima is not None,
            clima_aceptado=clima is not None and origen['estado_revision_declarado'] == 'aceptada',
            metodo_temperatura='ponderado_por_dias_naturales', metodo_lluvia='suma_de_medias_espaciales_mensuales',
            cierre_t07=False))
        temp.rename(salida)
    except BaseException:
        shutil.rmtree(temp)
        raise
    return controles


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--base-dev', required=True)
    p.add_argument('--salida', required=True, type=Path)
    p.add_argument('--sin-clima', action='store_true')
    p.add_argument('--clima', type=Path)
    p.add_argument('--revision-t04')
    p.add_argument('--para-revision', action='store_true', help='T04 aún no aceptada; sólo salida local reports/')
    a = p.parse_args()
    if a.sin_clima and (a.clima or a.revision_t04 or a.para_revision): p.error('--sin-clima no admite fuente T04')
    if not a.sin_clima and not (a.clima and a.revision_t04): p.error('Indicar --sin-clima o --clima y --revision-t04')
    try:
        c = integrar(a.base_dev, a.salida, a.clima, a.revision_t04, a.para_revision)
    except (ValueError, KeyError, OSError, subprocess.CalledProcessError) as e:
        p.exit(1, f'T07 detenida: {e}\n')
    print(f"T07: {c['parcelas']} parcelas, {c['columnas_tabla_comun']} columnas; {c['estado_entrega']}; cierre pendiente.")


if __name__ == '__main__': main()
