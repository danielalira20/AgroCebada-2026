"""Entradas E2 selladas y unión por ID; no modifica T07 ni aprende estadísticas."""
import copy
import json
from pathlib import Path
import numpy as np
import pandas as pd
from scripts import t15_e1_ejecutar as e1
from scripts.t15_e1_contrato import read_csv, read_json, VALUE, FLAG
from scripts.evaluacion_comun_contrato import exigir, sha, validar_oof

ROOT = Path(__file__).resolve().parents[1]
DISENO = 'registro/t15_e2/contrato_tecnico_v1.json'
DISENO_SHA = 'd7c30ca6572373a78b78348df64e5fda50556f197bbcce03872d92a0735a2d9c'
ENTREGA = 'registro/t15_e2_extraccion/entrega.json'
ENTREGA_SHA = 'a5cd3d78183dcb71a38ea7988c85c774b187fc2c6c62b629fa90f63605a602bd'
E2 = ('e2_tpi150_media_m', 'e2_exposicion_este_media', 'e2_exposicion_norte_media')
MODOS = ('E2', 'E12', 'E2Q')


def cargar(root=ROOT):
    root=Path(root)
    cfg1, entradas, side1, anteriores=e1.cargar(root)
    exigir(sha(root/DISENO)==DISENO_SHA, 'Diseño INEGI alterado')
    exigir(sha(root/ENTREGA)==ENTREGA_SHA,'Entrega E2 sustituida: registrar nueva versión')
    cfg=read_json(root/DISENO);package=read_json(root/ENTREGA)
    exigir(package['schema']=='E2_entrega_compacta_v1' and
           package['estado']=='extraccion_y_QA_verificadas_localmente' and
           package['canonico']=='Linux_amd64' and package['contrato_sha256']==DISENO_SHA,
           'Entrega E2 no canónica/verificada')
    base=(root/ENTREGA).parent
    for name,h in package['archivos_sha256'].items():
        exigir(sha(base/name)==h, 'Archivo E2 modificado: '+name)
    for name,h in package['codigo_sha256'].items():
        exigir(sha(root/name)==h, 'Productor/auditor de extracción modificado: '+name)
    for name,h in cfg['fuentes_sha256'].items():
        exigir(sha(root/name)==h, 'Fuente común modificada: '+name)
    for name in ['auditoria_mac.json','auditoria_linux.json','comparacion_plataformas.json']:
        exigir(read_json(base/name)['resultado']=='aprobado', 'QA E2 pendiente: '+name)
    rows=read_csv(base/'atributos_parcela.csv');quality=read_csv(base/'calidad.csv')
    exigir(len(rows)==197 and len({r['id_parcela'] for r in rows})==197, 'IDs E2 duplicados/incompletos')
    exigir(list(rows[0])==['id_parcela',*E2], 'Esquema E2 distinto; no añadir calidad/etiquetas')
    exigir(len(quality)==197 and len({r['id_parcela'] for r in quality})==197, 'IDs QA inválidos')
    expected=set(side1.index)
    exigir({r['id_parcela'] for r in rows}=={r['id_parcela'] for r in quality}==expected, 'E2/E1/T07 no 1:1')
    for row in quality:
        exigir(all(1-1e-8<=float(row[c])<=1+1e-8 for c in
               ['cobertura_tpi_fraccion','cobertura_exposicion_fraccion']), 'Cobertura E2 incompleta')
    side2=pd.DataFrame(rows).set_index('id_parcela').astype(float).sort_index()
    exigir(np.isfinite(side2.to_numpy()).all(), 'E2 requiere valores finitos: no imputar')
    exigir((np.abs(side2[list(E2[1:])].to_numpy())<=1+1e-12).all() and
           (np.linalg.norm(side2[list(E2[1:])],axis=1)<=1+1e-12).all(), 'Exposición fuera del dominio')
    exigir(not set(side1)&set(side2), 'Extensiones pisan columnas')
    side=side1.join(side2,how='left',validate='one_to_one').sort_index()
    opts=[dict(o,columnas=list(o['columnas'])+list(E2)) for o in cfg1['S_comparador']['opciones']]
    exigir(len(opts)==8 and all(len(o['columnas'])==8 for o in opts), 'Menú E2 no registrado')
    names={'comun_centrado_loo_v3_S','comun_centrado_loo_v3_E1','media_mun__resp_grupo'}
    reused=[r for r in read_csv(root/'registro/t15_e1_evaluacion/resultados/predicciones_oof.csv') if r['candidato'] in names]
    exigir(len(reused)==4140 and {r['candidato'] for r in reused}==names,'Comparadores reutilizables incompletos')
    validar_oof(reused,entradas['contextos'])
    old={(r['candidato'],r['escenario'],r['repeticion'],r['ID_POLIGONO']):r for r in anteriores}
    for row in reused:
        key=(row['candidato'],row['escenario'],row['repeticion'],row['ID_POLIGONO'])
        if key in old:
            exigir(abs(float(row['prediccion'])-float(old[key]['prediccion']))<=1e-12,'S/referencia reutilizada difiere')
    return dict(diseno=cfg,antecedente=cfg1,entradas=entradas,side=side,opciones=opts,
                fuentes_reutilizadas=reused,entrega_sha256=sha(root/ENTREGA))


def contexto(datos, escenario, repeticion, particion):
    X,y,q=e1.contexto(datos['entradas'],datos['side'],escenario,repeticion,particion)
    exigir(not set(X.index)&set(q.index), 'IDs solapados')
    exigir(set(X.index)|set(q.index)==datos['entradas']['conocidos'], '59 reservadas en contexto')
    exigir('rendimiento_t_ha' not in X and 'rendimiento_t_ha' not in q, 'Objetivo en X')
    exigir(np.isfinite(X[list(E2)]).all().all() and np.isfinite(q[list(E2)]).all().all(), 'Unión con faltantes E2')
    return X,y,q


def opciones(datos):
    return [dict(copy.deepcopy(o),nombre=f"{o['ventana']}__lambda_{o['lambda_reg']:g}") for o in datos['opciones']]
