"""Franja normal de verdor del municipio: percentiles 25 y 75 de un índice, semana a semana,
calculados sólo con las parcelas con cosecha registrada del mismo municipio. Es contexto: no entra en la estimación."""
import pandas as pd


def sensor_para(s, pid, col="ndvi_promedio", minimo=5):
    """Planet si la parcela tiene al menos `minimo` capturas de Planet; si no, el sensor con más capturas.
    None si la parcela no tiene datos del índice."""
    x = s[(s.ID_POLIGONO == pid) & s[col].notna()]
    if x.empty:
        return None
    cuenta = x.sensor.value_counts()
    if cuenta.get("Planet", 0) >= minimo:
        return "Planet"
    return cuenta.idxmax()


def franja_municipio(d, s, pid, col="ndvi_promedio", sensor="Planet", minimo=3):
    """Tabla con semana (lunes), p25, p75 y n (parcelas con dato esa semana), usando sólo parcelas con cosecha
    del municipio de `pid` y sin contar a `pid`. None si hay menos de `minimo` parcelas para comparar."""
    muni = d.loc[pid, "municipio"]
    vecinas = d.index[(d.municipio == muni) & (d.CONJUNTO == "ENTRENAMIENTO") & (d.index != pid)]
    if len(vecinas) < minimo:
        return None
    x = s[s.ID_POLIGONO.isin(vecinas) & (s.sensor == sensor) & s[col].notna()]
    if x.empty:
        return None
    x = x.assign(semana=x.fecha.dt.to_period("W-SUN").dt.start_time)
    # un valor por parcela y semana, para que una parcela con muchas capturas no pese más que las demás
    por_parcela = x.groupby(["semana", "ID_POLIGONO"])[col].median().reset_index()
    g = por_parcela.groupby("semana")[col]
    out = pd.DataFrame({"p25": g.quantile(0.25), "p75": g.quantile(0.75), "n": g.size()}).reset_index()
    out = out[out.n >= minimo]
    return out if len(out) else None