"""T06 · Frente satelital: series por sensor, cobertura y rasgos observables.

Uso (desde la raíz del repositorio, con el entorno de requirements.txt):
    python scripts/t06_satelite.py --datos RUTA/DATASET_RETO_AGRO_2026

Genera:
    --series (por omisión data/interim/t06/, no versionado):
        serie_sentinel2.csv, serie_landsat.csv, serie_planet.csv
        Una fila por ID_POLIGONO × fecha_observada, todas las fechas del archivo
        original. Básico y PRO no se unen por ID: cada sensor queda en su tabla.
    --salida (por omisión registro/t06/):
        cobertura_mensual.csv    sensor × umbral × parcela × mes (abr–oct 2025).
        cobertura_ventana.csv    sensor × umbral × ventana × parcela.
        cobertura_resumen.csv    lo anterior resumido por CONJUNTO.
        calidad_nubosidad.csv    relación entre nubosidad, índices vacíos y sesgo.
        rasgos_observables.csv   parcela × sensor (abr_oct, referencia): si se observan inicio,
                                 pico y final antes del corte; banderas de calidad de ciclo
                                 doble y meseta en el pico.
        comparacion_ventanas.csv  base, amplitud y día de inicio del NDVI en abr_oct frente a jun_oct.
        figura_curvas_6_parcelas.png
        variables_satelitales.csv              197 filas × variables compactas, sin rendimiento.
        variables_satelitales_diccionario.csv  definición, sensor, ventana y umbral de cada columna.
        diagnosticos_variables.csv             campaña completa frente al corte y fechas barajadas.

Reglas: un faltante no es cero; la nubosidad se usa sólo como umbral de calidad
(no se interpreta como fracción de píxeles válidos); todo cálculo derivado se
recorta al 31-oct-2025 antes de cualquier suavizado o interpolación. No se leen
rendimientos: el catálogo sólo aporta ID y CONJUNTO.
"""
import argparse
import hashlib
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
CORTE = pd.Timestamp("2025-10-31")
VENTANAS = {"abr_oct": pd.Timestamp("2025-04-01"), "jun_oct": pd.Timestamp("2025-06-01")}
UMBRALES = [0, 5, 20]  # candidatos de nubosidad máxima (%) evaluados en la cobertura
UMBRAL = {"Sentinel-2": 5, "Planet": 20, "Landsat": 5}  # D002 y D006; Landsat sólo calidad y nivel de VI6T
FECHA_DISPONIBLE = "no documentada"  # ni el diccionario ni la descripción la informan

ARCHIVOS = {"BASICO": "Conjunto_datos_BASICO_AgroCebada2026.csv", "PRO": "Conjunto_datos_PRO_AgroCebada.csv"}
SENSORES = {  # sensor: (fuente, abreviatura, índices que trae ese sensor, índice de referencia)
    "Sentinel-2": ("BASICO", "s2", ["ndvi", "evi", "crc", "mcrc", "ndsvi", "srndi", "mra", "lai", "fapar",
                                     "savi", "ndti", "sti", "ndwi", "endwi", "msi", "emsi", "dswi2", "dswi3",
                                     "dswi4", "dswi5", "nddi", "enddi"], "ndvi"),
    "Landsat": ("BASICO", "ls", ["vi6t"], "vi6t"),
    "Planet": ("PRO", "pl", ["ndvi", "evi", "lai", "msavi"], "ndvi"),
}
ESTADISTICOS = ["promedio", "std", "min", "max"]
# LAI del PRO = LAI2 del documento de ecuaciones de FIRA (D005); no equivale al LAI de Sentinel-2.
RENOMBRAR = {"Planet": {"lai": "lai2"}}


def md5(ruta: Path) -> str:
    return hashlib.md5(ruta.read_bytes()).hexdigest()


def series(datos: Path) -> dict:
    """Tabla larga por sensor, sin unir Básico y PRO."""
    crudos = {f: pd.read_csv(datos / a, encoding="utf-8-sig", dtype={"ID_POLIGONO": str, "fecha_captura": str})
              for f, a in ARCHIVOS.items()}
    out = {}
    for sensor, (fuente, _, indices, ref) in SENSORES.items():
        x = crudos[fuente]
        x = x[x.sensor == sensor]
        cols = [f"{i}_{e}" for i in indices for e in ESTADISTICOS]
        # Las columnas de otros sensores deben venir vacías; si no, la separación sería incorrecta.
        otras = [c for c in x.columns if c.endswith(tuple(f"_{e}" for e in ESTADISTICOS)) and c not in cols]
        assert x[otras].isna().all().all(), f"{sensor}: valores en columnas ajenas"
        s = pd.DataFrame({
            "ID_POLIGONO": x.ID_POLIGONO,
            "fecha_observada": pd.to_datetime(x.fecha_captura, format="%d/%m/%Y").dt.date,
            "fecha_disponible": FECHA_DISPONIBLE,
            "sensor": sensor,
            "fuente": ARCHIVOS[fuente],
        })
        s[cols] = x[cols]
        for viejo, nuevo in RENOMBRAR.get(sensor, {}).items():
            s = s.rename(columns={f"{viejo}_{e}": f"{nuevo}_{e}" for e in ESTADISTICOS})
        s["porcentaje_nubosidad"] = x.porcentaje_nubosidad
        s["tiene_dato"] = x[f"{ref}_promedio"].notna()
        s["posterior_al_corte"] = pd.to_datetime(s.fecha_observada) > CORTE
        s = s.sort_values(["ID_POLIGONO", "fecha_observada"]).reset_index(drop=True)
        assert not s.duplicated(["ID_POLIGONO", "fecha_observada"]).any()
        out[sensor] = s
    return out


def calidad_nubosidad(ser: dict) -> pd.DataFrame:
    """Qué acompaña a cada tramo de nubosidad: índice vacío y diferencia frente a una despejada cercana."""
    filas = []
    tramos = [(-np.inf, 0), (0, 1), (1, 5), (5, 10), (10, 20), (20, 50), (50, 99.999), (99.999, 100)]
    for sensor, s in ser.items():
        ref = SENSORES[sensor][3] + "_promedio"
        f = pd.to_datetime(s.fecha_observada)
        x = s.assign(f=f, v=s[ref])
        x = x[(x.f >= VENTANAS["abr_oct"]) & (x.f <= CORTE)]
        desp = x[(x.porcentaje_nubosidad == 0) & x.tiene_dato][["ID_POLIGONO", "f", "v"]]
        par = x.merge(desp.rename(columns={"f": "fd", "v": "vd"}), on="ID_POLIGONO")
        par = par[((par.f - par.fd).dt.days.abs()).between(1, 3)]
        par = par.assign(dd=(par.f - par.fd).dt.days.abs()).sort_values("dd").drop_duplicates(["ID_POLIGONO", "f"])
        par["dif"] = par.v - par.vd
        for a, b in tramos:
            sel = x.porcentaje_nubosidad.gt(a) & x.porcentaje_nubosidad.le(b)
            selp = par.porcentaje_nubosidad.gt(a) & par.porcentaje_nubosidad.le(b)
            filas.append(dict(
                sensor=sensor, indice_referencia=ref,
                tramo_nubosidad="0" if b == 0 else ("100" if a == 99.999 else f"({a:g}, {b:g}]"),
                capturas=int(sel.sum()), capturas_sin_indice=int((sel & ~x.tiene_dato).sum()),
                pares_con_despejada_1a3_dias=int(selp.sum()),
                dif_mediana_vs_despejada=round(par.dif[selp].median(), 4) if selp.any() else np.nan,
            ))
        filas.append(dict(sensor=sensor, indice_referencia=ref, tramo_nubosidad="NaN",
                          capturas=int(x.porcentaje_nubosidad.isna().sum()),
                          capturas_sin_indice=int((x.porcentaje_nubosidad.isna() & ~x.tiene_dato).sum())))
    return pd.DataFrame(filas)


def huecos(fechas: pd.Series, ini: pd.Timestamp, fin: pd.Timestamp):
    """Hueco máximo en días: interno (entre capturas) y con bordes (incluye inicio→1.ª y última→fin)."""
    f = np.sort(fechas.values)
    if len(f) == 0:
        return np.nan, (fin - ini).days
    d = np.diff(f).astype("timedelta64[D]").astype(int)
    interno = d.max() if len(d) else np.nan
    bordes = [(pd.Timestamp(f[0]) - ini).days, (fin - pd.Timestamp(f[-1])).days]
    return interno, max([*bordes, *(d.tolist())])


def cobertura(ser: dict, ids: pd.DataFrame):
    mens, vent = [], []
    meses = pd.period_range("2025-04", "2025-10", freq="M")
    for sensor, s in ser.items():
        f = pd.to_datetime(s.fecha_observada)
        x = s.assign(f=f)[(f >= VENTANAS["abr_oct"]) & (f <= CORTE) & s.tiene_dato]
        for u in UMBRALES:
            ok = x[x.porcentaje_nubosidad <= u]
            por_id = dict(tuple(ok.groupby("ID_POLIGONO").f))
            vacia = pd.Series([], dtype="datetime64[ns]")
            for pid in ids.ID_POLIGONO:
                fp = por_id.get(pid, vacia)
                for m in meses:
                    ini, fin = m.start_time, m.end_time.normalize()
                    fm = fp[(fp >= ini) & (fp <= fin)]
                    hi, hb = huecos(fm, ini, fin)
                    mens.append(dict(sensor=sensor, umbral_nubosidad=u, ID_POLIGONO=pid, mes=str(m),
                                     capturas=len(fm), hueco_max_dias=hb))
                for v, ini in VENTANAS.items():
                    fv = fp[(fp >= ini) & (fp <= CORTE)]
                    hi, hb = huecos(fv, ini, CORTE)
                    mv = fv.dt.to_period("M").nunique()
                    vent.append(dict(sensor=sensor, umbral_nubosidad=u, ventana=v, ID_POLIGONO=pid,
                                     capturas=len(fv), hueco_max_dias=hb, hueco_max_interno_dias=hi,
                                     primera=fv.min().date() if len(fv) else None,
                                     ultima=fv.max().date() if len(fv) else None,
                                     meses_sin_captura=len(pd.period_range(ini, CORTE, freq="M")) - mv))
    mens, vent = pd.DataFrame(mens), pd.DataFrame(vent)
    mens = mens.merge(ids, on="ID_POLIGONO")
    vent = vent.merge(ids, on="ID_POLIGONO")
    return mens, vent


def resumen(vent: pd.DataFrame, mens: pd.DataFrame) -> pd.DataFrame:
    filas = []
    sin_mes = (mens.assign(vacio=mens.capturas.eq(0))
               .groupby(["sensor", "umbral_nubosidad", "ID_POLIGONO"]).vacio.sum())
    for (s, u, v, c), x in vent.groupby(["sensor", "umbral_nubosidad", "ventana", "CONJUNTO"]):
        filas.append(dict(
            sensor=s, umbral_nubosidad=u, ventana=v, CONJUNTO=c, parcelas=len(x),
            capturas_min=x.capturas.min(), capturas_p10=x.capturas.quantile(.1), capturas_mediana=x.capturas.median(),
            hueco_mediana=x.hueco_max_dias.median(), hueco_p90=x.hueco_max_dias.quantile(.9),
            hueco_max=x.hueco_max_dias.max(),
            parcelas_hueco_gt30=int((x.hueco_max_dias > 30).sum()),
            parcelas_hueco_gt45=int((x.hueco_max_dias > 45).sum()),
            parcelas_con_mes_vacio=int((x.meses_sin_captura > 0).sum()),
            parcelas_menos_de_5_capturas=int((x.capturas < 5).sum()),
        ))
    return pd.DataFrame(filas).round(1)


def validas(s: pd.DataFrame, sensor: str, ini: pd.Timestamp, fin: pd.Timestamp = CORTE) -> pd.DataFrame:
    """Capturas con dato y nubosidad ≤ umbral, recortadas a [ini, fin]. El corte va primero."""
    f = pd.to_datetime(s.fecha_observada)
    x = s.assign(f=f)[(f >= ini) & (f <= fin) & s.tiene_dato]
    return x[x.porcentaje_nubosidad <= UMBRAL[sensor]].sort_values(["ID_POLIGONO", "f"])


# Rasgos del ciclo sobre NDVI suavizado con mediana móvil de 3 capturas (después del corte).
AMPLITUD_MIN = 0.10   # por debajo no se considera que haya un ciclo detectable
FRAC_INICIO = 0.20    # cruce ascendente al 20 % de la amplitud
FRAC_FINAL = 0.50     # cruce descendente al 50 % de la amplitud
CAIDA_PICO = 0.20     # el máximo cuenta como pico si antes y después baja al menos 20 % de la amplitud
FRAC_DOBLE = 0.30     # ciclo doble: tras el inicio cae ≥ 30 % de la amplitud y vuelve a subir ≥ 30 %
FRAC_MESETA = 0.05    # meseta: capturas a ≤ 5 % de la amplitud del máximo...
DIAS_MESETA = 45      # ...separadas por al menos 45 días (a ≤ 10 % la mediana normal es ~40 días)
FENOLOGIA = ["Sentinel-2", "Planet"]  # Landsat no se usa para rasgos del ciclo (D002)


def curva(v: np.ndarray):
    """Curva suavizada, posición del máximo, base previa al máximo y amplitud."""
    sv = pd.Series(v).rolling(3, center=True, min_periods=1).median().values
    k = int(np.argmax(sv))
    base = sv[: k + 1].min()
    return sv, k, base, sv[k] - base


def cruce(f, v, umbral, asc):
    """Fecha interpolada del primer cruce entre dos capturas observadas, y días entre ellas."""
    for i in range(1, len(v)):
        if (v[i - 1] < umbral <= v[i]) if asc else (v[i - 1] > umbral >= v[i]):
            t = (umbral - v[i - 1]) / (v[i] - v[i - 1])
            return (f[i - 1] + (f[i] - f[i - 1]) * t).normalize(), (f[i] - f[i - 1]).days
    return pd.NaT, np.nan


def ciclo_doble(sv, desde, amp) -> bool:
    """Desde el inicio: caída ≥ FRAC_DOBLE·amp respecto al máximo acumulado y recuperación ≥ FRAC_DOBLE·amp."""
    tope, minimo, cayo = -np.inf, np.inf, False
    for y in sv[desde:]:
        if not cayo:
            tope = max(tope, y)
            cayo = y <= tope - FRAC_DOBLE * amp
            minimo = y
        else:
            minimo = min(minimo, y)
            if y >= minimo + FRAC_DOBLE * amp:
                return True
    return False


def rasgos_parcela(f: np.ndarray, v: np.ndarray) -> dict:
    r = dict(capturas=len(v), hay_ciclo=False, inicio_observado=False, pico_observado=False,
             final_observado=False, fecha_inicio=pd.NaT, fecha_pico=pd.NaT, fecha_final=pd.NaT,
             posible_ciclo_doble=False, meseta_en_pico=False)
    if len(v) < 5:
        return {**r, "motivo": "menos de 5 capturas válidas"}
    f = pd.DatetimeIndex(f)
    sv, k, base, amp = curva(v)
    r.update(base=round(base, 4), valor_maximo=round(sv[k], 4), amplitud=round(amp, 4),
             fecha_maximo_observado=f[k].date())
    if amp < AMPLITUD_MIN:
        return {**r, "motivo": f"amplitud < {AMPLITUD_MIN}"}
    r["hay_ciclo"] = True
    fi, hi = cruce(f[: k + 1], sv[: k + 1], base + FRAC_INICIO * amp, asc=True)
    ff, hf = cruce(f[k:], sv[k:], base + FRAC_FINAL * amp, asc=False)
    baja_antes = (sv[:k] <= sv[k] - CAIDA_PICO * amp).any()
    baja_despues = (sv[k + 1:] <= sv[k] - CAIDA_PICO * amp).any()
    cerca = f[sv >= sv[k] - FRAC_MESETA * amp]
    desde = int(np.searchsorted(f, fi)) if pd.notna(fi) else 0
    r.update(inicio_observado=pd.notna(fi), fecha_inicio=fi, dias_entre_capturas_inicio=hi,
             pico_observado=bool(baja_antes and baja_despues),
             final_observado=pd.notna(ff), fecha_final=ff, dias_entre_capturas_final=hf,
             posible_ciclo_doble=ciclo_doble(sv, desde, amp),
             meseta_en_pico=(cerca.max() - cerca.min()).days >= DIAS_MESETA)
    if r["pico_observado"]:
        r["fecha_pico"] = f[k]
    motivos = []
    if not r["inicio_observado"]:
        motivos.append("la primera captura ya supera el umbral de inicio")
    if not baja_despues:
        motivos.append("el NDVI no baja tras el máximo antes del corte")
    elif not r["final_observado"]:
        motivos.append("no cae al 50 % de la amplitud antes del corte")
    return {**r, "motivo": "; ".join(motivos)}


def rasgos(ser: dict, ids: pd.DataFrame) -> pd.DataFrame:
    """Rasgos de referencia: ventana abr_oct (D007). Las banderas de ciclo doble y meseta son de calidad."""
    filas = []
    for sensor in FENOLOGIA:
        x = validas(ser[sensor], sensor, VENTANAS["abr_oct"])
        por_id = dict(tuple(x.groupby("ID_POLIGONO")))
        for pid in ids.ID_POLIGONO:
            p = por_id.get(pid, x.iloc[:0])
            filas.append(dict(ID_POLIGONO=pid, sensor=sensor, ventana="abr_oct",
                              umbral_nubosidad=UMBRAL[sensor], indice="ndvi_promedio",
                              **rasgos_parcela(p.f.values, p.ndvi_promedio.values)))
    r = pd.DataFrame(filas).merge(ids, on="ID_POLIGONO")
    for c in ["fecha_inicio", "fecha_pico", "fecha_final"]:
        r[c] = pd.to_datetime(r[c]).dt.date
    return r


def comparar_ventanas(ser: dict, ids: pd.DataFrame) -> pd.DataFrame:
    """Forma de la curva de NDVI en abr_oct frente a jun_oct, por parcela y sensor (sin rendimientos)."""
    filas = []
    for sensor in FENOLOGIA:
        r = {}
        for v, ini in VENTANAS.items():
            x = validas(ser[sensor], sensor, ini)
            r[v] = {pid: (rasgos_parcela(p.f.values, p.ndvi_promedio.values),
                          curva(p.ndvi_promedio.values)[0][0] if len(p) else np.nan)
                    for pid, p in x.groupby("ID_POLIGONO")}
        for pid in ids.ID_POLIGONO:
            (a, _), (j, primero_j) = r["abr_oct"][pid], r["jun_oct"][pid]
            umbral_inicio_abr = a["base"] + FRAC_INICIO * a["amplitud"]
            doy = {k: pd.Timestamp(d["fecha_inicio"]).dayofyear if pd.notna(d["fecha_inicio"]) else np.nan
                   for k, d in [("abr_oct", a), ("jun_oct", j)]}
            filas.append(dict(
                ID_POLIGONO=pid, sensor=sensor,
                base_abr_oct=a["base"], base_jun_oct=j["base"], dif_base=round(j["base"] - a["base"], 4),
                amplitud_abr_oct=a["amplitud"], amplitud_jun_oct=j["amplitud"],
                dif_amplitud=round(j["amplitud"] - a["amplitud"], 4),
                ndvi_primera_captura_jun_oct=round(primero_j, 4),
                jun_oct_empieza_sobre_umbral_inicio_abr_oct=bool(primero_j >= umbral_inicio_abr),
                dia_inicio_abr_oct=doy["abr_oct"], dia_inicio_jun_oct=doy["jun_oct"],
                dif_dia_inicio=doy["jun_oct"] - doy["abr_oct"],
                final_observado_abr_oct=a["final_observado"], final_observado_jun_oct=j["final_observado"]))
    return pd.DataFrame(filas).merge(ids, on="ID_POLIGONO")


def elegir_parcelas(ras: pd.DataFrame) -> list:
    """6 parcelas para la figura, sin mirar rendimientos: Planet abr_oct, tres categorías de rasgos
    × CONJUNTO; en cada una, la de capturas más cercanas a la mediana de la categoría (empate: ID)."""
    x = ras[ras.sensor == "Planet"].copy()
    x["categoria"] = np.select([x.final_observado, x.pico_observado],
                               ["pico y final observados", "pico observado, final no"], "pico no observado")
    elegidas = []
    for cat in ["pico y final observados", "pico observado, final no", "pico no observado"]:
        for conj in ["ENTRENAMIENTO", "PREDICCION"]:
            c = x[(x.categoria == cat) & (x.CONJUNTO == conj)]
            if len(c):
                c = c.assign(d=(c.capturas - c.capturas.median()).abs()).sort_values(["d", "ID_POLIGONO"])
                elegidas.append((c.ID_POLIGONO.iloc[0], conj, cat))
    return elegidas


def figura(ser: dict, ras: pd.DataFrame, ruta: Path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates

    color = {"Planet": "#2a78d6", "Sentinel-2": "#eb6834"}  # categóricos 1 y 2 de la paleta de referencia
    forma = {"Planet": "o", "Sentinel-2": "s"}
    tinta, tinta2, rejilla = "#0b0b0b", "#52514e", "#e4e3df"
    plt.rcParams.update({"font.size": 9, "axes.edgecolor": rejilla, "axes.labelcolor": tinta2,
                         "xtick.color": tinta2, "ytick.color": tinta2, "text.color": tinta})
    elegidas = elegir_parcelas(ras)
    fig, ejes = plt.subplots(3, 2, figsize=(11, 9.5), sharex=True, sharey=True)
    for ax, (pid, conj, cat) in zip(ejes.flat, elegidas):
        for sensor in ["Planet", "Sentinel-2"]:
            p = validas(ser[sensor], sensor, VENTANAS["abr_oct"])
            p = p[p.ID_POLIGONO == pid]
            suave = p.ndvi_promedio.rolling(3, center=True, min_periods=1).median()
            ax.plot(p.f, p.ndvi_promedio, forma[sensor], ms=3.5, color=color[sensor], alpha=.35, mec="none")
            ax.plot(p.f, suave, "-", lw=2, color=color[sensor],
                    label=f"{sensor} (≤ {UMBRAL[sensor]} % nubosidad)")
            r = ras[(ras.ID_POLIGONO == pid) & (ras.sensor == sensor) & (ras.ventana == "abr_oct")].iloc[0]
            if sensor == "Planet":  # rasgos marcados sólo para Planet para no saturar el panel
                for clave, marca, txt in [("fecha_inicio", "^", "inicio"), ("fecha_pico", "o", "pico"),
                                          ("fecha_final", "v", "final")]:
                    if pd.notna(r[clave]):
                        fx = pd.Timestamp(r[clave])
                        ns = p.f.values.astype("datetime64[ns]").astype("int64")
                        fy = np.interp(np.datetime64(fx, "ns").astype("int64"), ns, suave.values)
                        ax.plot(fx, fy, marca, ms=9, color=tinta, mfc="white", mew=1.5, zorder=5)
                        ax.annotate(txt, (fx, fy), xytext=(0, 9 if marca != "v" else -15),
                                    textcoords="offset points", ha="center", fontsize=8, color=tinta2)
                no_obs = [n for n, k in [("inicio", "inicio_observado"), ("pico", "pico_observado"),
                                         ("final", "final_observado")] if not r[k]]
        ax.axvline(CORTE, color=tinta2, lw=1, ls="--")
        nombre = {"ENTRENAMIENTO": "etiquetada", "PREDICCION": "reservada"}[conj]
        ax.set_title(f"{pid} · {nombre} · {cat}", fontsize=9.5, loc="left", color=tinta)
        if no_obs:
            ax.text(.02, .95, "Planet, no observado antes del corte: " + ", ".join(no_obs),
                    transform=ax.transAxes, fontsize=8, color=tinta2, va="top")
        ax.grid(axis="y", color=rejilla, lw=.8)
        ax.spines[["top", "right"]].set_visible(False)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b"))
        ax.set_ylim(0, 1)
    for ax in ejes[:, 0]:
        ax.set_ylabel("NDVI promedio de la parcela")
    ejes[0, 0].text(CORTE, .02, " corte 31-oct ", ha="right", fontsize=8, color=tinta2)
    h, l = ejes[0, 0].get_legend_handles_labels()
    fig.legend(h, l, loc="upper left", ncol=2, frameon=False, bbox_to_anchor=(.015, .965))
    fig.suptitle("NDVI de 6 parcelas, 1-abr → 31-oct-2025: puntos = capturas válidas, "
                 "línea = mediana móvil de 3 capturas; rasgos marcados para Planet",
                 x=.02, y=.99, ha="left", fontsize=10.5)
    fig.tight_layout(rect=(0, 0, 1, .94))
    fig.savefig(ruta, dpi=150, facecolor="#fcfcfb")
    plt.close(fig)
    return elegidas


# Variables compactas aprobadas (D007). {v} = ventana; las «al_corte» no llevan ventana.
ALREDEDOR_MAXIMO = pd.Timedelta(days=15)
DIAS_AL_CORTE = pd.Timedelta(days=15)
DEFINICIONES = {
    "ndvi_max": "Máximo de la curva de NDVI (mediana móvil de 3 capturas válidas).",
    "ndvi_integral": "Área de la curva de NDVI por encima de la base previa al máximo, en NDVI·días; "
                     "interpolación lineal sólo entre la primera y la última captura válida.",
    "lai2_max": "Máximo de la curva de LAI2 (mediana móvil de 3 capturas válidas).",
    "ndvi_dias_sobre_mitad": "Días, hasta el corte, con la curva de NDVI interpolada por encima de "
                             "base + 50 % de la amplitud.",
    "ndvi_dia_inicio": "Día del año del cruce ascendente de base + 20 % de la amplitud, interpolado entre "
                       "dos capturas; vacío si no se observa.",
    "ndwi_en_maximo": "Mediana del NDWI de las capturas válidas a ±15 días del máximo de la curva de NDVI.",
    "ndvi_std_en_maximo": "Heterogeneidad: mediana de ndvi_std de las capturas válidas a ±15 días del máximo "
                          "de la curva de NDVI.",
    "vi6t_mediana": "Mediana del VI6T de las capturas válidas.",
    "capturas": "Calidad: número de capturas válidas (con índice y nubosidad ≤ umbral).",
    "hueco_max": "Calidad: hueco máximo en días entre capturas válidas, incluidos inicio de ventana→1.ª "
                 "y última→corte.",
    "nubosidad_media": "Calidad: media de porcentaje_nubosidad de todas las capturas con nubosidad informada, "
                       "incluidas las de 100. Puede actuar como indicador de zona.",
    "ndvi_al_corte": "Mediana de la curva de NDVI en las capturas válidas de los últimos 15 días antes del "
                     "31-oct-2025 (17 al 31 de octubre); vacío si no hay capturas.",
}
POR_SENSOR = {
    "Planet": ["ndvi_max", "ndvi_integral", "lai2_max", "ndvi_dias_sobre_mitad", "ndvi_dia_inicio",
               "ndvi_std_en_maximo", "capturas", "hueco_max", "nubosidad_media"],
    "Sentinel-2": ["ndvi_max", "ndvi_integral", "ndvi_dias_sobre_mitad", "ndwi_en_maximo",
                   "ndvi_std_en_maximo", "capturas", "hueco_max", "nubosidad_media"],
    "Landsat": ["vi6t_mediana", "capturas", "hueco_max", "nubosidad_media"],
}
AL_CORTE = ["Planet", "Sentinel-2"]


def a_ns(f) -> np.ndarray:
    return np.asarray(f).astype("datetime64[ns]").astype("int64")


def resumen_parcela(sensor: str, p: pd.DataFrame, todas: pd.DataFrame, ini, fin) -> dict:
    """Variables de una parcela en una ventana. p: capturas válidas ordenadas; todas: con nubosidad informada."""
    r = {"capturas": len(p), "hueco_max": huecos(p.f, ini, fin)[1],
         "nubosidad_media": todas.porcentaje_nubosidad.mean() if len(todas) else np.nan}
    if sensor == "Landsat":
        r["vi6t_mediana"] = p.vi6t_promedio.median() if len(p) else np.nan
        return r
    if len(p) < 5:
        return r
    f = pd.DatetimeIndex(p.f.values)
    sv, k, base, amp = curva(p.ndvi_promedio.values)
    dias = (f - f[0]).days.values
    r["ndvi_max"] = sv[k]
    r["ndvi_integral"] = np.trapezoid(np.clip(sv - base, 0, None), dias)
    cerca = (f >= f[k] - ALREDEDOR_MAXIMO) & (f <= f[k] + ALREDEDOR_MAXIMO)
    r["ndvi_std_en_maximo"] = np.median(p.ndvi_std.values[cerca])
    if sensor == "Planet":
        r["lai2_max"] = curva(p.lai2_promedio.values)[0].max()
    else:
        r["ndwi_en_maximo"] = np.median(p.ndwi_promedio.values[cerca])
    if amp >= AMPLITUD_MIN:
        diario = pd.date_range(f[0], f[-1], freq="D")
        y = np.interp(a_ns(diario), a_ns(f), sv)
        r["ndvi_dias_sobre_mitad"] = int((y >= base + 0.5 * amp).sum())
        if sensor == "Planet":
            fi, _ = cruce(f[: k + 1], sv[: k + 1], base + FRAC_INICIO * amp, asc=True)
            r["ndvi_dia_inicio"] = fi.dayofyear if pd.notna(fi) else np.nan
    return r


def variables(ser: dict, ids: pd.DataFrame, fin: pd.Timestamp = CORTE, semilla=None) -> pd.DataFrame:
    """Tabla de una fila por parcela. semilla ≠ None baraja las fechas de las capturas válidas de cada
    parcela sin cambiar sus valores (diagnóstico); fin ≠ CORTE resume una campaña más larga (diagnóstico)."""
    rng = np.random.default_rng(semilla)
    out = ids[["ID_POLIGONO"]].set_index("ID_POLIGONO")
    for sensor, nombres in POR_SENSOR.items():
        ab = SENSORES[sensor][1]
        s = ser[sensor]
        f_all = pd.to_datetime(s.fecha_observada)
        for v, ini in VENTANAS.items():
            x = validas(s, sensor, ini, fin)
            if semilla is not None:
                x = x.assign(f=x.groupby("ID_POLIGONO").f.transform(lambda z: rng.permutation(z.values)))
                x = x.sort_values(["ID_POLIGONO", "f"])
            todas = s.assign(f=f_all)[(f_all >= ini) & (f_all <= fin) & s.porcentaje_nubosidad.notna()]
            por_id, todas_id = dict(tuple(x.groupby("ID_POLIGONO"))), dict(tuple(todas.groupby("ID_POLIGONO")))
            filas = {pid: resumen_parcela(sensor, por_id.get(pid, x.iloc[:0]), todas_id.get(pid, todas.iloc[:0]),
                                          ini, fin) for pid in out.index}
            t = pd.DataFrame.from_dict(filas, orient="index").reindex(columns=nombres)
            out[[f"{ab}_{n}_{v}" for n in nombres]] = t.values
            if v == "abr_oct" and sensor in AL_CORTE:
                al = {}
                for pid, p in por_id.items():
                    ultimos = (p.f > fin - DIAS_AL_CORTE).values
                    al[pid] = np.median(curva(p.ndvi_promedio.values)[0][ultimos]) if ultimos.any() else np.nan
                out[f"{ab}_ndvi_al_corte"] = pd.Series(al).reindex(out.index)
    return out.reset_index()


def diccionario(cols) -> pd.DataFrame:
    filas = []
    for c in cols[1:]:
        ab = c.split("_")[0]
        sensor = {SENSORES[k][1]: k for k in SENSORES}[ab]
        ventana = next((v for v in VENTANAS if c.endswith(v)), "31-oct (sin ventana)")
        base = c[len(ab) + 1:].removesuffix("_" + ventana) if ventana in VENTANAS else c[len(ab) + 1:]
        filas.append(dict(columna=c, sensor=sensor, ventana=ventana, umbral_nubosidad=UMBRAL[sensor],
                          tipo=("calidad" if base in ("capturas", "hueco_max", "nubosidad_media") else
                                "heterogeneidad" if "std" in base else "compacta"),
                          definicion=DEFINICIONES[base]))
    return pd.DataFrame(filas)


def comparar(a: pd.DataFrame, b: pd.DataFrame, etiqueta: str) -> pd.DataFrame:
    filas = []
    for c in a.columns[1:]:
        x, y = a[c].astype(float), b[c].astype(float)
        ok = x.notna() & y.notna()
        filas.append(dict(columna=c, comparacion=etiqueta, parcelas_con_ambos=int(ok.sum()),
                          spearman=round(x[ok].corr(y[ok], method="spearman"), 3) if ok.sum() > 2 else np.nan,
                          dif_abs_mediana=round((x[ok] - y[ok]).abs().median(), 4),
                          parcelas_que_cambian=int(((x - y).abs() > 1e-9)[ok].sum())))
    return pd.DataFrame(filas)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--datos", type=Path, required=True)
    ap.add_argument("--series", type=Path, default=RAIZ / "data" / "interim" / "t06")
    ap.add_argument("--salida", type=Path, default=RAIZ / "registro" / "t06")
    a = ap.parse_args()
    a.series.mkdir(parents=True, exist_ok=True)
    a.salida.mkdir(parents=True, exist_ok=True)

    cat = pd.read_csv(a.datos / "ID_area_rendimiento_70_30_Reto_AgroCebada.csv", encoding="utf-8-sig",
                      usecols=["ID_POLIGONO", "CONJUNTO"], dtype=str)
    assert cat.ID_POLIGONO.is_unique and len(cat) == 197

    ser = series(a.datos)
    for sensor, s in ser.items():
        assert s.ID_POLIGONO.isin(cat.ID_POLIGONO).all()
        ruta = a.series / {"Sentinel-2": "serie_sentinel2.csv", "Landsat": "serie_landsat.csv",
                           "Planet": "serie_planet.csv"}[sensor]
        s.to_csv(ruta, index=False)
        print(f"{ruta.name}: {s.shape}, IDs={s.ID_POLIGONO.nunique()}, "
              f"con dato={int(s.tiene_dato.sum())}, md5={md5(ruta)}")

    calidad_nubosidad(ser).to_csv(a.salida / "calidad_nubosidad.csv", index=False)
    mens, vent = cobertura(ser, cat)
    mens.to_csv(a.salida / "cobertura_mensual.csv", index=False)
    vent.to_csv(a.salida / "cobertura_ventana.csv", index=False)
    r = resumen(vent, mens)
    r.to_csv(a.salida / "cobertura_resumen.csv", index=False)
    assert len(vent) == 3 * len(UMBRALES) * len(VENTANAS) * 197
    print(r.to_string(index=False))

    ras = rasgos(ser, cat)
    assert len(ras) == len(FENOLOGIA) * 197
    ras.to_csv(a.salida / "rasgos_observables.csv", index=False)
    flags = ["hay_ciclo", "inicio_observado", "pico_observado", "final_observado",
             "posible_ciclo_doble", "meseta_en_pico"]
    print(ras.groupby(["sensor", "ventana", "CONJUNTO"])[flags].sum().to_string())
    cv = comparar_ventanas(ser, cat)
    cv.to_csv(a.salida / "comparacion_ventanas.csv", index=False)
    print(cv.groupby("sensor")[["dif_base", "dif_amplitud", "dif_dia_inicio"]]
          .describe(percentiles=[.1, .5, .9]).round(3).T.to_string())
    print("figura:", figura(ser, ras, a.salida / "figura_curvas_6_parcelas.png"))

    var = variables(ser, cat)
    assert len(var) == 197 and var.ID_POLIGONO.is_unique and var.ID_POLIGONO.isin(cat.ID_POLIGONO).all()
    # La calidad debe coincidir con la tabla de cobertura en el umbral fijado de cada sensor.
    for sensor, ab in [("Planet", "pl"), ("Sentinel-2", "s2"), ("Landsat", "ls")]:
        for v in VENTANAS:
            cv = vent[(vent.sensor == sensor) & (vent.umbral_nubosidad == UMBRAL[sensor]) & (vent.ventana == v)]
            m = var.merge(cv, on="ID_POLIGONO")
            assert (m[f"{ab}_capturas_{v}"] == m.capturas).all()
            assert (m[f"{ab}_hueco_max_{v}"] == m.hueco_max_dias).all()
    var.to_csv(a.salida / "variables_satelitales.csv", index=False)
    diccionario(list(var.columns)).to_csv(a.salida / "variables_satelitales_diccionario.csv", index=False)
    print("variables_satelitales.csv:", var.shape, "| faltantes por columna:",
          {c: int(n) for c, n in var.isna().sum().items() if n})

    # Diagnósticos sin rendimientos: campaña completa frente al corte y fechas barajadas.
    completa = variables(ser, cat, fin=pd.Timestamp("2025-12-31"))
    diag = [comparar(var, completa, "campaña hasta 31-dic frente a corte 31-oct")]
    for semilla in range(5):
        diag.append(comparar(var, variables(ser, cat, semilla=semilla), f"fechas barajadas, semilla {semilla}"))
    diag = pd.concat(diag, ignore_index=True)
    diag.to_csv(a.salida / "diagnosticos_variables.csv", index=False)
    print(diag.assign(tipo=diag.comparacion.str.split(",").str[0])
          .groupby(["columna", "tipo"], sort=False).spearman.mean().unstack().round(3).to_string())


if __name__ == "__main__":
    main()
