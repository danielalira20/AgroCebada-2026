"""Agregación temporal T07 sobre medias espaciales ya calculadas en T04."""
from datetime import date
import math

from scripts.t07_fuentes import fin_mes, numero

VENTANAS = {
    "abr_oct": tuple(f"2025-{m:02d}" for m in range(4, 11)),
    "jun_oct": tuple(f"2025-{m:02d}" for m in range(6, 11)),
}
VARIABLES = {"PREC": "prec_acumulada_mm", "Tmin": "tmin_media_c", "Tmax": "tmax_media_c"}
LARGA = ("id_parcela", "ventana", "inicio", "fin", "dias_esperados", *VARIABLES.values())
ANCHA = ("id_parcela", *(f"{campo}_{w}" for w in VENTANAS for campo in VARIABLES.values()))
CALIDAD = ("id_parcela", "ventana", "variable", "unidad", "meses_esperados",
           "meses_presentes", "meses_validos", "dias_esperados", "dias_validos",
           "cobertura_minima", "estado", "motivo", "periodos_con_problema",
           "celdas_lluvia_tocadas_t02", "centroide_dentro_parcela", "meses_centroide_validos",
           "dias_centroide_validos", "periodos_sin_centroide", "valor_centroide_ventana",
           "diferencia_media_menos_centroide", "estado_comparacion_centroide")


def agregar_serie(indice, pid, periodos, variable):
    """Un mes ausente/NoData o parcial nunca se convierte en total completo."""
    if not periodos or len(set(periodos)) != len(periodos):
        raise ValueError("Ventana vacía o meses duplicados")
    if variable not in VARIABLES:
        raise ValueError("Variable desconocida")
    dias = {p: fin_mes(p).day for p in periodos}
    presentes = {p: indice[(pid, p, variable)] for p in periodos if (pid, p, variable) in indice}
    validos = {p: numero(r["media_ponderada"]) for p, r in presentes.items() if r["media_ponderada"] != ""}
    faltantes = sorted(set(periodos) - presentes.keys())
    nodata = sorted(p for p in presentes if p not in validos)
    parciales = sorted(p for p, r in presentes.items() if r["estado"] == "cobertura_parcial")
    problemas = sorted(set(faltantes + nodata + parciales))
    motivo = []
    if faltantes: motivo.append("mes_ausente")
    if nodata: motivo.append("mes_sin_media")
    if parciales: motivo.append("cobertura_parcial_sin_extrapolacion")
    estado = "incompleta" if faltantes or nodata else "cobertura_parcial" if parciales else "completa"
    valor = ""
    if estado == "completa":
        if any(r["estado"] != "cobertura_completa" for r in presentes.values()):
            raise ValueError("Estado mensual incompatible con una ventana completa")
        valor = math.fsum(validos[p] for p in periodos) if variable == "PREC" else (
            math.fsum(validos[p] * dias[p] for p in periodos) / sum(dias.values()))
        if not math.isfinite(valor):
            raise ValueError("Agregado no finito")
    coberturas = [numero(r["cobertura_valida"]) for r in presentes.values()]
    control = dict(variable=variable, unidad="mm" if variable == "PREC" else "grados Celsius",
                   meses_esperados=len(periodos), meses_presentes=len(presentes), meses_validos=len(validos),
                   dias_esperados=sum(dias.values()), dias_validos=sum(dias[p] for p in validos),
                   cobertura_minima=min(coberturas) if coberturas else "", estado=estado,
                   motivo=";".join(motivo), periodos_con_problema=";".join(problemas))
    banderas = {r['centroide_dentro_parcela'] for r in presentes.values()}
    if len(banderas) > 1 or not banderas <= {'True', 'False'}:
        raise ValueError('Bandera de centroide cambió entre meses')
    centros = {p: numero(r['valor_centroide']) for p, r in presentes.items() if r['valor_centroide'] != ''}
    sin_centro = sorted(set(periodos) - centros.keys())
    centro = ''
    if not sin_centro:
        centro = math.fsum(centros[p] for p in periodos) if variable == 'PREC' else (
            math.fsum(centros[p] * dias[p] for p in periodos) / sum(dias.values()))
        if not math.isfinite(centro):
            raise ValueError('Agregado de centroide no finito')
    comparacion = ('ventana_no_completa' if estado != 'completa' else
                  'centroide_incompleto' if sin_centro else 'comparable')
    control.update(centroide_dentro_parcela=next(iter(banderas)) if banderas else '',
                   meses_centroide_validos=len(centros),
                   dias_centroide_validos=sum(dias[p] for p in centros),
                   periodos_sin_centroide=';'.join(sin_centro), valor_centroide_ventana=centro,
                   diferencia_media_menos_centroide=valor-centro if comparacion == 'comparable' else '',
                   estado_comparacion_centroide=comparacion)
    return valor, control


def agregar(indice, ids, soporte_lluvia=None):
    if not ids or len(set(ids)) != len(ids):
        raise ValueError("IDs vacíos o duplicados")
    if soporte_lluvia is not None and set(soporte_lluvia) != set(ids):
        raise ValueError('IDs de soporte climático T02 incompatibles')
    larga, ancha, calidad = [], [], []
    for pid in sorted(ids):
        fila = {"id_parcela": pid}
        for w, periodos in VENTANAS.items():
            resumen = dict(id_parcela=pid, ventana=w,
                           inicio=date.fromisoformat(periodos[0] + "-01").isoformat(),
                           fin=fin_mes(periodos[-1]).isoformat(),
                           dias_esperados=sum(fin_mes(p).day for p in periodos))
            for v, campo in VARIABLES.items():
                valor, control = agregar_serie(indice, pid, periodos, v)
                resumen[campo] = valor
                fila[f"{campo}_{w}"] = valor
                calidad.append(dict(id_parcela=pid, ventana=w, **control,
                                    celdas_lluvia_tocadas_t02=soporte_lluvia[pid] if soporte_lluvia is not None else ''))
            if resumen["tmin_media_c"] != "" and resumen["tmax_media_c"] != "":
                if resumen["tmin_media_c"] > resumen["tmax_media_c"]:
                    raise ValueError(f"Tmin supera Tmax: {pid}/{w}")
            larga.append(resumen)
        ancha.append(fila)
    return larga, ancha, calidad
