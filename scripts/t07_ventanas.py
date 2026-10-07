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
           "cobertura_minima", "estado", "motivo", "periodos_con_problema")


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
    return valor, control


def agregar(indice, ids):
    if not ids or len(set(ids)) != len(ids):
        raise ValueError("IDs vacíos o duplicados")
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
                calidad.append(dict(id_parcela=pid, ventana=w, **control))
            if resumen["tmin_media_c"] != "" and resumen["tmax_media_c"] != "":
                if resumen["tmin_media_c"] > resumen["tmax_media_c"]:
                    raise ValueError(f"Tmin supera Tmax: {pid}/{w}")
            larga.append(resumen)
        ancha.append(fila)
    return larga, ancha, calidad
