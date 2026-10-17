"""Verifica contrato y oráculos analíticos E2; no extrae atributos ni ajusta modelos."""
import argparse
import copy
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path


def exigir(ok, mensaje):
    if not ok:
        raise ValueError(mensaje)


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def validar(c):
    exigir(c['schema'] == 'agrocebada_E2_CEM3_contrato_v1', 'Otra versión de contrato')
    exigir(c['ejecutable'] is False, 'Este diseño no habilita entrenamientos')
    exigir(not any(c['puertas_para_ejecutar'].values()), 'No atribuir puertas ya superadas a este diseño')
    exigir(not c['fuente']['reescribir_CRS_original'] and not c['fuente']['transformacion_vertical'], 'Datum inventado')
    exigir(c['fuente']['CRS_declarado'] == 'EPSG:4326', 'CRS fuente distinto')
    exigir(c['rejilla']['CRS_destino'] == 'EPSG:32614' and c['rejilla']['resolucion_m'] == 15, 'Rejilla distinta')
    exigir(c['rejilla']['remuestreo'] == 'bilinear_una_vez', 'No multiplicar remuestreos')
    exigir(not c['rejilla']['red_PROJ'] and not c['rejilla']['ballpark_permitido'], 'Transformación no acreditada')
    exigir(c['TPI']['radio_m_UTM'] == 150 and c['TPI']['incluir_centro'] is False, 'Otro vecindario TPI')
    exigir(c['TPI']['n_vecinos'] == 316 and not c['TPI']['normalizado_por_desviacion'], 'TPI indefinido o distinto')
    exigir(c['validez']['TPI'] == 'centro_y_316_vecinos_validos' and c['validez']['Horn'] == '9_celdas_validas', 'No ignorar NoData')
    exigir(c['validez']['soporte_bilinear_min'] >= 1 - 1e-12, 'Bilineal con soporte incompleto')
    exigir(c['validez']['cobertura_parcela_min'] >= 1 - 1e-8, 'Cobertura insuficiente para esta versión')
    exigir(not c['agregacion']['all_touched_como_media'] and c['agregacion']['peso_contacto_borde'] == 0, 'Pesos físicos incorrectos')
    exigir(c['orientacion']['plano'] == 'ambos_0_observado_no_azimut_Norte_no_faltante', 'Plano con orientación ficticia')
    exigir(c['orientacion']['umbral_pendiente_predictivo'] is None, 'Umbral de pendiente no registrado')
    exigir(c['orientacion']['equivalencia'] == 'sin(inclinacion)*sin(azimut_verdadero),sin(inclinacion)*cos(azimut_verdadero)', 'Otra representación de orientación')
    exigir(c['modelo']['sin_centrado_en_197'] and c['modelo']['sin_intercepto'], 'Riesgo H3 o aprendizaje fuera de train')
    exigir(c['modelo']['version'] == 'comun-centrado-loo-v3' and not c['modelo']['imputacion_E2'], 'Otro estimador/faltante')
    exigir(c['modelo']['lambda_reg'] == [.01, .1, 1., 10.] and c['modelo']['n_internas'] == 4, 'Búsqueda no registrada')
    exigir(c['modelo']['ventanas'] == ['abr_oct', 'jun_oct'] and c['modelo']['referencia_sola_compite'], 'Menú cambiado')
    exigir(c['integracion']['n'] == 197 and c['integracion']['reservadas'] == 59 and not c['modelo']['seleccion_en59'], 'Población o filtración')
    exigir(c['columnas_modelo'] == ['e2_tpi150_media_m', 'e2_exposicion_este_media', 'e2_exposicion_norte_media'], 'Cambian predictores')
    arms = c['procedimientos']
    exigir([a['id'] for a in arms] == ['E2', 'E12', 'E2Q'], 'Cartera distinta')
    exigir([a['promocion'] for a in arms] == [True, True, False], 'Control Q promovido')
    budget = c['presupuesto'];n = len(arms);contexts = 2 * 5 * 5;options = 2 * 4;inner = 4
    expected = dict(nuevos_procedimientos=n, contextos=contexts, opciones_con_variables_total=n * options,
                    Ridge_internos=n * contexts * options * inner, referencias_internas_sin_cache=n * contexts * inner,
                    ajustes_externos=n * contexts, ajustes_internos_sin_cache=n * contexts * inner * (options + 1),
                    trazas_sin_cache=n * contexts * (inner * (options + 1) + 1), OOF_nuevas=n * 138 * 2 * 5,
                    OOF_reutilizadas=3 * 138 * 2 * 5, OOF_total=6 * 138 * 2 * 5,
                    contrastes_total=7 * 2 * 2, metricas_resumen=6 * 2 * 2, selecciones=n * contexts)
    for key, value in expected.items():
        exigir(budget[key] == value, 'Presupuesto inconsistente: ' + key)
    exigir(len(c['contrastes']) == 7, 'Contrastes incompletos')
    rule = c['decision']['T03']['promocion']
    exigir(rule == dict(dMAE_max=-.01, IC95_superior_max_exclusivo=0, repeticiones_mejoran_min=4, dRMSE_max=.01), 'Regla debilitada o cambiada')
    family = c['decision']['guardia_familia_E2']
    exigir(family['candidatos'] == ['E2', 'E12'] and family['percentiles'] == [1.25, 98.75], 'Guardia de familia distinta')
    exigir(c['tolerancias']['OOF_mismos_CSV_canonicos'] == 1e-12, 'No relajar OOF por diferencias de extracción')
    return expected


def comprobar_matematica():
    checks = []
    def check(ok, name):
        exigir(ok, 'Oráculo de diseño: ' + name)
        checks.append(name)
    cells = [(dr, dc) for dr in range(-10, 11) for dc in range(-10, 11) if 0 < dr*dr + dc*dc <= 100]
    check(len(cells) == 316, '316 vecinos, centro excluido')
    check(sum(i for i, _ in cells) == sum(j for _, j in cells) == 0, 'Simetría espacial')
    def tpi(fn):
        return fn(0, 0) - sum((fn(15*dc, -15*dr) for dr, dc in cells), Fraction()) / len(cells)
    def horn(fn):
        a, b, c, d, e, f, g, h, i = [fn(x, y) for y in [15, 0, -15] for x in [-15, 0, 15]]
        return ((c+2*f+i)-(a+2*d+g))/120, ((a+2*b+c)-(g+2*h+i))/120
    for z0 in [0, 100, 2500]:
        fn = lambda x, y, z0=z0: Fraction(z0)
        check(tpi(fn) == 0 and horn(fn) == (0, 0), f'Plano a Z={z0}')
    for p, q in [(1, 0), (-1, 0), (0, 1), (0, -1), (Fraction(1, 10), Fraction(-1, 5))]:
        fn = lambda x, y, p=p, q=q: p*x+q*y+Fraction(2000)
        check(tpi(fn) == 0 and horn(fn) == (p, q), f'Rampa exacta p={p},q={q}')
    expected_bowl = -Fraction(225 * sum(dr*dr+dc*dc for dr, dc in cells), 316)
    check(tpi(lambda x, y: Fraction(x*x+y*y)) == expected_bowl, 'Cuenco: TPI negativo analítico')
    check(tpi(lambda x, y: Fraction(x*x+y*y+500)) == expected_bowl, 'Invariancia offset vertical TPI')
    def vector(p, q, gamma=0, k=1):
        den = math.sqrt(1+(k*p)**2+(k*q)**2)
        return ((-k*p*math.cos(gamma)-k*q*math.sin(gamma))/den,
                (k*p*math.sin(gamma)-k*q*math.cos(gamma))/den)
    check(vector(0, 0) == (0, 0), 'Plano da vector cero, no norte')
    for p, q, expected in [(1, 0, (-1/math.sqrt(2), 0)), (-1, 0, (1/math.sqrt(2), 0)),
                            (0, 1, (0, -1/math.sqrt(2))), (0, -1, (0, 1/math.sqrt(2)))]:
        v = vector(p, q)
        check(max(abs(a-b) for a, b in zip(v, expected)) < 1e-12, f'Signo descenso {p},{q}')
    for p, q in [(0, 0), (1e-15, -1e-15), (1, 2), (1e8, -1e8)]:
        v = vector(p, q, .03, .9997)
        check(math.hypot(*v) <= 1+1e-12, f'Norma vectorial {p},{q}')
    gamma = .02;p, q = math.sin(gamma), -math.cos(gamma)
    v = vector(p, q, gamma)
    check(abs(v[0]) < 1e-12 and abs(v[1]-1/math.sqrt(2)) < 1e-12, 'Corrección meridiano, verdadero norte')
    e = (math.sin(math.radians(359))+math.sin(math.radians(1)))/2
    n = (math.cos(math.radians(359))+math.cos(math.radians(1)))/2
    check(abs(e) < 1e-12 and n > .99, 'Circularidad 359 y1, no promedio180')
    check(Fraction(80, 100)*100 + Fraction(20, 100)*200 == 120, 'Peso80_20')
    check(Fraction(0, 100)*99999 == 0, 'Contacto de borde sin área no cuenta')
    check(sum([.25, .25, .25, 0]) < 1-1e-12, 'NoData bilineal no se renormaliza')
    check(math.isclose(.05/2/2*100, 1.25), 'Colas de guardia por dos candidatos')
    return dict(comprobaciones=len(checks), casos=checks, cuenco_TPI_analitico=str(expected_bowl), superficies='oraculos_de_formula_no_datos_de_rendimiento')


def negativos(c):
    cases = [(['ejecutable'], True), (['TPI', 'radio_m_UTM'], 100),
             (['fuente', 'reescribir_CRS_original'], True), (['rejilla', 'red_PROJ'], True),
             (['validez', 'TPI'], 'promediar_solo_validos'), (['agregacion', 'all_touched_como_media'], True),
             (['modelo', 'sin_centrado_en_197'], False), (['presupuesto', 'Ridge_internos'], 3200),
             (['decision', 'guardia_familia_E2', 'percentiles'], [2.5, 97.5]),
             (['procedimientos', 2, 'promocion'], True)]
    for path, value in cases:
        changed = copy.deepcopy(c);target = changed
        for key in path[:-1]:
            target = target[key]
        target[path[-1]] = value
        try:
            validar(changed)
        except ValueError:
            continue
        raise ValueError('Cambio no registrado aceptado: ' + '.'.join(map(str, path)))
    return len(cases)


def verificar(root, contract, output, local=False):
    root, contract, output = Path(root).resolve(), Path(contract).resolve(), Path(output).resolve()
    exigir(not output.exists(), 'Elegir salida nueva; no sobrescribir evidencia')
    exigir(not output.is_relative_to(root) or output.is_relative_to(root/'reports'), 'Dentro del repo escribir sólo reports/')
    c = json.loads(contract.read_text());budget = validar(c)
    for name, digest in c['fuentes_sha256'].items():
        exigir(sha(root/name) == digest, 'Fuente común modificada: ' + name)
    if local:
        exigir(sha(root/c['fuente']['ruta_relativa']) == c['fuente']['sha256'], 'Otro DEM')
        for name, digest in c['vectores']['archivos_sha256'].items():
            exigir(sha(root/c['vectores']['directorio_relativo']/name) == digest, 'Vector distinto: ' + name)
    proof = comprobar_matematica();negative_count = negativos(c)
    result = dict(schema='E2_verificacion_diseno_v1',resultado='aprobado',codigo_sha256=sha(__file__),
                  contrato_sha256=sha(contract),fuentes_comunes=len(c['fuentes_sha256']),
                  originales_locales_verificados=local,pruebas_analiticas=proof,mutaciones_peligrosas_rechazadas=negative_count,
                  presupuesto_recalculado=budget,atributos_E2_extraidos=False,modelos_ajustados=0,
                  datos_de_rendimiento_simulados=0,habilita_entrenamiento=False)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--raiz',type=Path,default=Path(__file__).resolve().parents[1])
    p.add_argument('--contrato',type=Path)
    p.add_argument('--salida',type=Path,required=True)
    p.add_argument('--con-datos-locales',action='store_true')
    a = p.parse_args()
    path = a.contrato or a.raiz/'registro/t15_e2/contrato_tecnico_v1.json'
    print(json.dumps(verificar(a.raiz,path,a.salida,a.con_datos_locales),ensure_ascii=False,indent=2))
