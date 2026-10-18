"""Resúmenes de una parcela: datos clave y texto del recuadro al pasar el ratón."""
import pandas as pd

from agrocebada_app.config import MESES


def resumen_parcela(d, pid, elevaciones, clima, series):
    """Pares (etiqueta, valor) de la parcela. `elevaciones`, `clima` y `series` son las tablas de la app (o None)."""
    r, out = d.loc[pid], []
    out.append(("Área", f"{r.AREA_HA:.2f} ha"))
    E = elevaciones
    if E is not None and pid in E.index:
        out.append(("Altitud", f"{E[pid]:,.0f} m"))
    if clima is not None:
        x = clima[(clima.id_parcela == pid) & (clima.periodo.between("2025-04", "2025-10"))]
        if len(x):
            out.append(("Lluvia abr–oct", f"{x.PREC.sum():,.0f} mm"))
    s = series[(series.ID_POLIGONO == pid) & series.ndvi_promedio.notna()]
    if len(s):
        top = s.sort_values("ndvi_promedio").iloc[-1]
        out.append(("Verdor máximo", f"{top.ndvi_promedio:.2f} · {MESES[top.fecha.month]}"))
    out.append(("Corte de información", "31 oct 2025"))
    return out


def detalles(d, pred, oof_parcela):
    """Texto del recuadro que aparece al pasar el ratón por cada parcela."""
    out = {}
    for pid, r in d.iterrows():
        if r.CONJUNTO == "PREDICCION" and pid in pred.index:
            p = pred.loc[pid]
            lin = [f"Estimación: {p.prediccion:.2f} t/ha" +
                   (f" (error típico ± {p.error_tipico:.2f})" if pd.notna(p.get("error_tipico")) else ""),
                   f"Área: {r.AREA_HA:.2f} ha · producción {p.prediccion * r.AREA_HA:.1f} t",
                   (f"Base: {int(p.n_municipio)} parcelas con cosecha de {r.municipio}" if p.fuente == "municipio"
                    else f"Base: respaldo por {p.fuente} (su municipio no tiene parcelas con cosecha)")]
            if p.get("aviso"):
                lin.append(f"Aviso: {p.aviso}")
        else:
            lin = [f"Rendimiento registrado: {r.real:.2f} t/ha"]
            if pid in oof_parcela.index:
                lin.append(f"Lo que estimó el método sin conocerla: {oof_parcela[pid]:.2f} t/ha")
            lin.append(f"Área: {r.AREA_HA:.2f} ha")
        out[pid] = "\n".join(lin)
    return out
