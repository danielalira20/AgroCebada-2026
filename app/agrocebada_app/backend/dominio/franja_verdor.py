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



NOMBRE_MES = {1: "enero", 2: "febrero", 3: "marzo", 4: "abril", 5: "mayo", 6: "junio", 7: "julio", 8: "agosto",
              9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre"}


def pico_verdor(s, pid, col="ndvi_promedio"):
    """(valor, número de mes) del punto más verde de la parcela, o None si no tiene datos del índice.

    Con un solo sensor y la mediana de cada semana, igual que la gráfica y la franja del municipio: mezclar sensores
    o quedarse con la captura más alta hace que un solo día nublado o una calibración distinta mueva el mes."""
    sensor = sensor_para(s, pid, col)
    if sensor is None:
        return None
    x = s[(s.ID_POLIGONO == pid) & (s.sensor == sensor) & s[col].notna()]
    semanal = x.assign(semana=x.fecha.dt.to_period("W-SUN").dt.start_time).groupby("semana")[col].median()
    cima = semanal.idxmax()
    return float(semanal.loc[cima]), cima.month


def mes_mas_verde(d, s, pid, col="ndvi_promedio"):
    """(mes de la parcela, mes de su municipio o None): en qué mes llegó el índice a su punto más alto, semana a
    semana y con el mismo sensor de la franja. Para el municipio usa el centro de la franja. None si no hay datos."""
    pico = pico_verdor(s, pid, col)
    if pico is None:
        return None
    mes_parcela = NOMBRE_MES[pico[1]]
    f = franja_municipio(d, s, pid, col, sensor_para(s, pid, col))
    mes_municipio = None
    if f is not None:
        centro = (f.p25 + f.p75) / 2
        mes_municipio = NOMBRE_MES[f.loc[centro.idxmax(), "semana"].month]
    return mes_parcela, mes_municipio

def frase_verdor(d, s, pid, col="ndvi_promedio"):
    """En qué mes se puso más verde la parcela frente a su municipio, en una frase.

    Vive aquí y no en la pantalla porque la dicen dos lugares —la tarjeta de verdor y Cebi— y tienen que decir lo
    mismo."""
    meses = mes_mas_verde(d, s, pid, col)
    if meses is None:
        return "No hay imágenes de satélite suficientes de tu parcela."
    parcela, municipio = meses
    if municipio is None:
        return f"Tu parcela llegó a su verdor más alto en {parcela}."
    if municipio == parcela:
        return f"Tu parcela y las de tu municipio llegaron a su verdor más alto en {parcela}."
    return f"Tu parcela llegó a su verdor más alto en {parcela}; las de tu municipio, en {municipio}."
