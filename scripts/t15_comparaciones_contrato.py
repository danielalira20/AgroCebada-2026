"""Contrato T15 y preflight sin modelos. No habilita una evaluación por sí solo."""
import argparse
import copy
import json
from pathlib import Path

from scripts import evaluacion_comun_centrado_loo as v3
from scripts import evaluacion_comun_contrato as comun
from scripts.evaluacion_comun_modelo import preparar_contexto, divisiones_internas

RUTA = 'registro/t15_contrato/contrato_v1.json'
SHA_CONTRATO = 'ec725f603df78847c37366feef71c620c6ddef15cd0d11716019252fdfa6ad99'
exigir = comun.exigir


def cargar(raiz=comun.RAIZ):
    raiz = Path(raiz)
    exigir(comun.sha(raiz/RUTA) == SHA_CONTRATO, 'Contrato modificado: versionar y revisar')
    c = json.loads((raiz/RUTA).read_text())
    entradas = v3.cargar_entradas(raiz)
    validar(c, entradas, raiz)
    return c, entradas


def validar(c, entradas, raiz=comun.RAIZ):
    """Comprueba contenido y fuentes. No interpreta propuestas como aprobaciones."""
    raiz = Path(raiz)
    exigir(c.get('schema') == 'agrocebada_t15_contrato_comparaciones_v1', 'Schema ajeno')
    exigir(c.get('estado') == 'cerrado_tecnicamente_para_revision' and
           c.get('ejecucion_habilitada') is False, 'No convertir cierre técnico en autorización')
    for ruta, sha in c['fuentes_sha256'].items():
        exigir(comun.sha(raiz/ruta) == sha, 'Fuente modificada: '+ruta)
    fuente = json.loads((raiz/c['principal']['plantilla']).read_text())
    exigir(c['metodo']['version'] == v3.VERSION and c['metodo']['sha256'] == v3.DISENO_SHA,
           'Versión de método distinta')
    exigir(c['metodo']['lambda'] == [.01, .1, 1., 10.] and
           c['metodo']['ventanas'] == ['abr_oct', 'jun_oct'], 'Búsqueda ampliada')
    p = c['poblacion']
    exigir((p['total'], p['etiquetadas'], p['reservadas']) == (197, 138, 59) and
           p['corte'] == '2025-10-31' and p['excluir_por_error'] is False and
           p['prediccion_final_59_en_este_lote'] is False, 'Población o corte alterados')
    exigir(c['decision'] == entradas['config']['comparacion'], 'Regla T03 alterada')
    main = c['principal']
    exigir(main['procedimientos'] == fuente['procedimientos'] and
           main['contrastes_planificados'] == fuente['contrastes_planificados'],
           'Menú principal o contrastes distintos del registro previo')
    exigir(main['escenarios'] == ['A', 'B'] and main['referencia_sola_por_procedimiento'] is True,
           'Escenarios/referencia alterados')
    exigir(main['internas'] == dict(A='StratifiedKFold_municipio_min4_otros_semilla0',
                                    B='GroupKFold_celda_chirps_sin_shuffle', n=4), 'Internas distintas')
    exigir(main['desempate'] == entradas['config']['seleccion']['empate'], 'Desempate alterado')
    counts = comun.validar_opciones_y_presupuesto(main, entradas)
    exigir(counts['procedimientos'] == 8 and counts['opciones_con_variables'] == 60, 'Presupuesto alterado')
    exigir(main['presupuesto'] == dict(procedimientos=8, opciones_con_variables=60,
        contextos_externos=50, ajustes_Ridge_internos_max=12000, ajustes_Ridge_externos_max=400,
        valoraciones_referencia_internas_sin_cache=1600, referencias_internas_compartibles=200,
        referencias_externas_compartibles=50), 'Cómputo principal alterado')
    exigir(all(e['ejecutable'] is False for e in c['extensiones_no_incluidas_en_principal'].values()),
           'Extensión añadida sin revisión')
    sg = c['extensiones_no_incluidas_en_principal']['SG']
    s = next(p for p in main['procedimientos'] if p['bloques'] == ['S'])
    g = next(p for p in main['procedimientos'] if p['bloques'] == ['G'])
    esperado = [dict(o, columnas=o['columnas']+g['opciones'][0]['columnas']) for o in s['opciones']]
    exigir(sg['opciones'] == esperado and sg['area_explicita'] is True, 'SG no coincide con S+G')
    exigir(len(c['puertas_pendientes']) == 4 and
           all(p['estado'].startswith('pendiente') for p in c['puertas_pendientes']), 'Aprobación no acreditada')
    return counts


def exigir_ejecucion(c):
    # La incorporación de aceptación requiere otro registro versionado con sus
    # evidencias; no basta sustituir False por True o escribir "aprobado".
    raise ValueError('Evaluación no habilitada por este contrato: ' +
                     ', '.join(p['id'] for p in c['puertas_pendientes']))


def experimento_para_revision(c):
    """Representación no ejecutable; evita editar la propuesta histórica v3."""
    return dict(schema='experimento_comun_centrado_loo_v3',
                id=c['principal']['id'], responsable=c['responsable'],
                hipotesis=c['pregunta'], sha_procedimiento=v3.DISENO_SHA,
                estado='propuesto_pendiente_cierre_revisiones',
                procedimientos=copy.deepcopy(c['principal']['procedimientos']),
                contrastes_planificados=copy.deepcopy(c['principal']['contrastes_planificados']))


def preflight(entradas):
    """Reconstruye las 200 internas reales, sin ajustar ni usar y para agrupar."""
    trazas = []
    for escenario in ['A', 'B']:
        for rep in range(1, 6):
            for fold in range(5):
                X, _, externa = preparar_contexto(entradas, escenario, rep, fold)
                for num, d in enumerate(divisiones_internas(X, escenario)):
                    tr, va = X.loc[list(d.entrenamiento)], X.loc[list(d.validacion)]
                    exigir(not set(tr.index)&set(va.index) and not set(X.index)&set(externa.index),
                           'Solapamiento entre entrenamientos y evaluaciones')
                    exigir(not (set(tr.index)|set(va.index)|set(externa.index)) & entradas['reservados'],
                           'Reservadas en evaluación')
                    exigir(set(tr.index)|set(va.index) == set(X.index), 'Interna incompleta')
                    if escenario == 'B':
                        exigir(not set(tr.celda_chirps)&set(va.celda_chirps), 'Celda compartida en B interna')
                        exigir(not set(X.celda_chirps)&set(externa.celda_chirps), 'Celda compartida en B externa')
                    counts = tr.municipio.value_counts()
                    n = [int(counts.get(m, 0)) for m in va.municipio]
                    exigir(tuple(k > 0 for k in n) == d.elegibles, 'Elegibilidad incorrecta')
                    trazas.append(dict(escenario=escenario, repeticion=rep, particion=fold,
                        division_interna=num, n_entrenamiento=len(tr), n_validacion=len(va),
                        n_elegibles=sum(d.elegibles), n_respaldados=sum(k == 0 for k in n),
                        n_validacion_referencia_una_etiqueta=sum(k == 1 for k in n),
                        n_singleton_entrenamiento=int((counts == 1).sum()),
                        ids_entrenamiento=list(d.entrenamiento), ids_validacion=list(d.validacion),
                        ids_evaluacion_externa=list(externa.index),
                        n_pendientes_observadas=int(tr.pendiente_media_t10_grados.notna().sum())))
    exigir(len(trazas) == 200, 'Se requieren 200 divisiones internas')
    exigir(all(t['n_pendientes_observadas'] > 0 for t in trazas),
           'Pendiente totalmente ausente en una interna: revisar antes de evaluar')
    return dict(resultado='verificado', contrato_sha256=SHA_CONTRATO, version=v3.VERSION,
                etiquetadas=len(entradas['conocidos']), reservadas=len(entradas['reservados']),
                contextos_externos=50, divisiones_internas=len(trazas),
                modelos_ajustados=0, evaluacion_habilitada=False, trazas=trazas)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--raiz', type=Path, default=comun.RAIZ)
    p.add_argument('--salida', type=Path)
    p.add_argument('--exigir-ejecucion', action='store_true')
    args = p.parse_args()
    try:
        c, e = cargar(args.raiz)
        if args.exigir_ejecucion:
            exigir_ejecucion(c)
        resultado = preflight(e)
        if args.salida:
            path = args.salida.resolve()
            exigir(path.is_relative_to(args.raiz.resolve()/'reports') or
                   not path.is_relative_to(args.raiz.resolve()), 'Salida sólo local; no sobrescribir fuentes')
            exigir(not path.exists(), 'No sobrescribir evidencia existente')
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(resultado, ensure_ascii=False, indent=2)+'\n')
        print(json.dumps({k:v for k,v in resultado.items() if k != 'trazas'}, ensure_ascii=False, indent=2))
    except (ValueError, OSError, KeyError, TypeError) as exc:
        p.exit(1, 'Contrato T15 rechazado: '+str(exc)+'\n')


if __name__ == '__main__':
    main()
