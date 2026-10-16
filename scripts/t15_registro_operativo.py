"""Registro operativo: cierre Dani/Codex explícito; sin aprobaciones externas inventadas."""
import json
from pathlib import Path
from scripts import evaluacion_comun_contrato as comun
from scripts import t15_comparaciones_contrato as contrato

RUTA='registro/t15_contrato/registro_operativo_v1.json'
SHA_REGISTRO='efa766beccc74f1a53459462f07a84ddff30651cb05d44531cb2694a2e4783df'


def cargar(raiz,c):
    raiz=Path(raiz)
    comun.exigir(comun.sha(raiz/RUTA)==SHA_REGISTRO,'Registro operativo alterado: versionar')
    r=json.loads((raiz/RUTA).read_text())
    comun.exigir(r['schema']=='agrocebada_t15_registro_operativo_v1' and
                 r['contrato_sha256']==contrato.SHA_CONTRATO,'Registro de otro contrato')
    comun.exigir(r['criterios']==c['decision'] and r['extensiones_activadas']==[],
                 'Criterios/extensiones distintos del principal')
    comun.exigir(r['principal_candidatos']==[p['candidato'] for p in c['principal']['procedimientos']],
                 'Candidatos ajenos al principal')
    comun.exigir(r['cierre']['responsable_humana']=='Dani' and
                 r['cierre']['revision_externa_requerida'] is False and
                 r['cierre']['aprobacion_Daf_atribuida'] is False and
                 r['cierre']['aprobacion_Migue_atribuida'] is False,
                 'Gobernanza distinta de la instrucción de Dani')
    for path,h in r['codigo_sha256'].items():
        comun.exigir(comun.sha(raiz/path)==h,'Código operativo modificado: '+path)
    comun.exigir(comun.sha(raiz/'registro/t07/calidad_parcelas.csv')==r['control_calidad_sha256'],
                 'Calidad T03 bis modificada')
    return r
