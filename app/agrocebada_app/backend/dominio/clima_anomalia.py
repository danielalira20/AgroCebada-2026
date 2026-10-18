"""Clima de 2025 contra el promedio 2022–2024 de la misma parcela, mes a mes, y las frases que salen de esa comparación.
Es contexto: no entra en el cálculo de la estimación."""

NOMBRE_MES = {3: "marzo", 4: "abril", 5: "mayo", 6: "junio", 7: "julio", 8: "agosto", 9: "septiembre", 10: "octubre"}
# Por debajo de estos umbrales el mes se considera cerca del promedio y no se dice nada.
LLUVIA_PCT = 20   # % de diferencia en lluvia...
LLUVIA_MM = 10    # ...y al menos 10 mm, para no exagerar en meses en que casi no llueve
TEMP_C = 1.0      # °C de diferencia
PROMEDIO = "el promedio 2022–2024"


def comparar(c, cn, pid):
    """Tabla por mes con PREC, Tmax y Tmin de 2025 y su promedio 2022–2024 (columnas *_normal).
    None si falta alguna de las dos tablas o la parcela no aparece."""
    if c is None or cn is None:
        return None
    a = c[c.id_parcela == pid]
    b = cn[cn.id_parcela == pid]
    if a.empty or b.empty:
        return None
    a = a.assign(mes=a.periodo.str[5:].astype(int))[["mes", "PREC", "Tmax", "Tmin"]]
    t = a.merge(b[["mes", "PREC", "Tmax", "Tmin"]], on="mes", suffixes=("", "_normal"))
    return t.sort_values("mes").reset_index(drop=True) if len(t) else None


def frases(t, maximo=4):
    """Frases de los meses que más se apartaron del promedio, en orden de mes. Lista vacía si todo quedó cerca."""
    if t is None:
        return []
    hallazgos = []   # (qué tanto se apartó, mes, frase)
    for r in t.itertuples():
        mes = NOMBRE_MES.get(r.mes, str(r.mes))
        dif = r.PREC - r.PREC_normal
        if r.PREC_normal > 0 and abs(dif) >= LLUVIA_MM:
            pct = 100 * dif / r.PREC_normal
            if abs(pct) >= LLUVIA_PCT:
                if r.PREC >= 2 * r.PREC_normal:   # más del doble: se entiende mejor en veces que en %
                    texto = f"En {mes} cayó {r.PREC / r.PREC_normal:.1f} veces la lluvia promedio de 2022–2024 en tu zona."
                else:
                    como = "más lluvioso" if pct > 0 else "más seco"
                    texto = f"{mes.capitalize()} fue {abs(pct):.0f} % {como} que {PROMEDIO} en tu zona."
                hallazgos.append((abs(pct) / LLUVIA_PCT, r.mes, texto))
        dmax = r.Tmax - r.Tmax_normal
        if abs(dmax) >= TEMP_C:
            como = "más calurosos" if dmax > 0 else "más frescos"
            hallazgos.append((abs(dmax) / TEMP_C, r.mes,
                              f"En {mes}, los días fueron {abs(dmax):.1f} °C {como} que {PROMEDIO}."))
        dmin = r.Tmin - r.Tmin_normal
        if abs(dmin) >= TEMP_C:
            como = "más templadas" if dmin > 0 else "más frías"
            hallazgos.append((abs(dmin) / TEMP_C, r.mes,
                              f"En {mes}, las noches fueron {abs(dmin):.1f} °C {como} que {PROMEDIO}."))
    elegidos = sorted(hallazgos, key=lambda h: -h[0])[:maximo]
    return [h[2] for h in sorted(elegidos, key=lambda h: h[1])]
