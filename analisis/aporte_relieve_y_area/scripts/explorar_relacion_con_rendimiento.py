"""T10 · Diagnóstico EXPLORATORIO con rendimientos (anexo de selección de atributos, §2.2).

Se corre DESPUÉS de la evaluación (registro/t10/) y no decide nada: no elige variables,
no cambia configuraciones ni la conclusión de T10. Usa las 138 parcelas etiquetadas.

- Pearson de cada variable de T10 con el rendimiento, global y dentro de municipio
  (restando a ambas la media de su municipio), con número de pares y Spearman como
  complemento. Faltantes: se excluye el par, no se rellena.
- «Dentro de municipio» sólo con municipios de al menos 5 etiquetas (T03 marca n < 5 como
  poco informativo); también se reporta por municipio.
- Figura: dispersión global y dentro de municipio para las tres variables.

Uso, desde la raíz del repositorio:
    python analisis/aporte_relieve_y_area/scripts/explorar_relacion_con_rendimiento.py
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

RAIZ = Path(__file__).resolve().parents[3]
CARPETA = Path(__file__).resolve().parents[1]
TABLA = RAIZ / "registro" / "t07" / "tabla_comun.csv"
SALIDA_TABLA = CARPETA / "tablas" / "correlaciones_con_rendimiento.csv"
SALIDA_FIGURA = CARPETA / "figuras" / "dispersion_relieve_area_rendimiento.png"
MIN_MUNICIPIO = 5
VARIABLES = {"elevacion_media_m": "Elevación (m s.n.m.)",
             "pendiente_media_t10_grados": "Pendiente (grados, piso D020)",
             "log_area_ha": "Log del área declarada (ln ha)"}
# Paleta de referencia (una sola serie por panel: sin leyenda).
SERIE, TEXTO, TEXTO_2, SUPERFICIE, REJILLA = "#2a78d6", "#0b0b0b", "#52514e", "#fcfcfb", "#e4e3df"


def cargar():
    t = pd.read_csv(TABLA)
    t["log_area_ha"] = np.log(t.area_ha_origen.astype(float))
    e = t[t.rendimiento_t_ha.notna()].copy()
    assert len(e) == 138
    return e


def correlaciones(x, y):
    ok = x.notna() & y.notna()
    x, y = x[ok], y[ok]
    r, p = stats.pearsonr(x, y)
    rho, _ = stats.spearmanr(x, y)
    return dict(n_pares=int(ok.sum()), pearson_r=r, pearson_p=p, spearman_rho=rho)


def centrar(e, col, municipios):
    sub = e[e.municipio.isin(municipios)]
    return (sub[col] - sub.groupby("municipio")[col].transform("mean"),
            sub.rendimiento_t_ha - sub.groupby("municipio").rendimiento_t_ha.transform("mean"))


def tabla_correlaciones(e):
    conteo = e.municipio.value_counts()
    grandes = conteo[conteo >= MIN_MUNICIPIO].index
    filas = []
    for col in VARIABLES:
        filas.append(dict(variable=col, ambito="global", municipio="todos",
                          **correlaciones(e[col], e.rendimiento_t_ha)))
        xc, yc = centrar(e, col, grandes)
        filas.append(dict(variable=col, ambito="dentro_de_municipio",
                          municipio=f"{len(grandes)} municipios con >= {MIN_MUNICIPIO} etiquetas",
                          **correlaciones(xc, yc)))
        for m in grandes:
            s = e[e.municipio == m]
            filas.append(dict(variable=col, ambito="por_municipio", municipio=m,
                              **correlaciones(s[col], s.rendimiento_t_ha)))
    r = pd.DataFrame(filas)
    r["nota"] = "Exploratorio con las 138 etiquetas; no decide nada; p no es puerta de entrada (anexo §2.2)"
    return r, grandes


def figura(e, grandes, r):
    fig, ejes = plt.subplots(2, 3, figsize=(12, 7.4), facecolor=SUPERFICIE)
    for j, (col, nombre) in enumerate(VARIABLES.items()):
        paneles = [(e[col], e.rendimiento_t_ha, "global", "Rendimiento (t/ha)"),
                   (*centrar(e, col, grandes), "dentro_de_municipio", "Rendimiento menos media municipal (t/ha)")]
        for i, (x, y, ambito, ylab) in enumerate(paneles):
            ax = ejes[i, j]
            ok = x.notna() & y.notna()
            ax.set_facecolor(SUPERFICIE)
            ax.scatter(x[ok], y[ok], s=26, color=SERIE, alpha=0.75, edgecolor=SUPERFICIE, linewidth=1)
            pendiente, intercepto = np.polyfit(x[ok], y[ok], 1)
            xs = np.linspace(x[ok].min(), x[ok].max(), 50)
            ax.plot(xs, intercepto + pendiente * xs, color=TEXTO_2, linewidth=1.5)
            fila = r[(r.variable == col) & (r.ambito == ambito)].iloc[0]
            ax.set_title(f"r = {fila.pearson_r:+.2f}   (n = {fila.n_pares})", fontsize=10, color=TEXTO, loc="left")
            ax.grid(color=REJILLA, linewidth=0.8)
            ax.set_axisbelow(True)
            for s in ax.spines.values():
                s.set_color(REJILLA)
            ax.tick_params(colors=TEXTO_2, labelsize=8)
            ax.set_xlabel(nombre if i == 0 else nombre + ", menos media municipal", fontsize=9, color=TEXTO_2)
            if j == 0:
                ax.set_ylabel(ylab, fontsize=9, color=TEXTO_2)
    fig.suptitle("T10 · Relieve y área frente al rendimiento (138 etiquetadas) — EXPLORATORIO, no decide",
                 fontsize=12, color=TEXTO, x=0.01, ha="left")
    fig.text(0.01, 0.005, f"Fila superior: global. Fila inferior: dentro de municipio ({len(grandes)} municipios con "
             f">= {MIN_MUNICIPIO} etiquetas). Línea: ajuste lineal sólo para guiar la vista.",
             fontsize=8, color=TEXTO_2)
    fig.tight_layout(rect=(0, 0.02, 1, 0.96))
    return fig


def main():
    e = cargar()
    r, grandes = tabla_correlaciones(e)
    for ruta in (SALIDA_TABLA, SALIDA_FIGURA):
        if ruta.exists():
            raise FileExistsError(f"{ruta} ya existe; no se sobrescribe evidencia")
        ruta.parent.mkdir(parents=True, exist_ok=True)
    SALIDA_TABLA.write_bytes(r.to_csv(index=False, lineterminator="\n").encode("utf-8"))
    fig = figura(e, grandes, r)
    fig.savefig(SALIDA_FIGURA, dpi=150, facecolor=SUPERFICIE, metadata={"Software": None})
    pd.set_option("display.width", 200)
    print(r.drop(columns="nota").round(3).to_string(index=False))


if __name__ == "__main__":
    main()
