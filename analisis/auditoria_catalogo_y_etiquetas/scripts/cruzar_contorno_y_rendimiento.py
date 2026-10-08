"""Cruza la calidad de contorno con el rendimiento, dentro de cada municipio.

Uso (después de construir_catalogo.py, con el mismo entorno):
    python scripts/cruzar_contorno_y_rendimiento.py

Lee tablas/catalogo_parcelas.csv y escribe en tablas/:
    cruce_contorno_rendimiento.csv     Las siete comparaciones fijadas antes de mirar el resultado.
    cruce_contorno_por_municipio.csv   Desglose por municipio de la comparación principal.
    cruce_contorno_parcelas_b_c.csv    Las 13 parcelas conocidas en B o C, una por una.

La regla de lectura se fijó antes de mirar el resultado y está en la bitácora de esta carpeta.
Las dos últimas tablas se añadieron después de ver el resultado, para poder entenderlo:
son descriptivas y no cambian el veredicto de la regla.
No entrena ningún modelo: usa promedios por municipio y una prueba de barajar.
"""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd

CARPETA = Path(__file__).resolve().parents[1]
TABLAS_POR_OMISION = CARPETA / "tablas"

BARAJADAS = 10_000
SEMILLA = 20261005
UMBRAL_PRINCIPAL_T_HA = 0.25     # mitad del escalón más grueso del rendimiento
CASUALIDAD_PRINCIPAL = 5.0       # de cada 100 barajadas
CASUALIDAD_SECUNDARIA = 1.0      # de cada 100 barajadas


def desviacion_municipal(conocidas: pd.DataFrame) -> pd.Series:
    """Rendimiento de cada parcela menos el promedio de las demás conocidas de su municipio.

    Queda vacía en los municipios con una sola parcela conocida.
    """
    y = conocidas.rendimiento_t_ha.astype(float)
    suma = y.groupby(conocidas.municipio).transform("sum")
    n = y.groupby(conocidas.municipio).transform("count")
    return (y - (suma - y) / (n - 1)).where(n > 1)


def comparar(k, tipo, grupo, referencia, en_grupo, en_referencia, absoluta, rng):
    """Compara dos conjuntos de parcelas y baraja las etiquetas dentro de cada municipio."""
    medida = k.desviacion.abs() if absoluta else k.desviacion
    y = k.rendimiento_t_ha.astype(float)
    usa = (en_grupo | en_referencia) & k.desviacion.notna()
    valores = medida[usa].values
    marca = en_grupo[usa].values
    municipios = k.municipio[usa].values

    def diferencia(m):
        return valores[m].mean() - valores[~m].mean()

    observada = diferencia(marca)
    posiciones = [np.flatnonzero(municipios == nombre) for nombre in np.unique(municipios)]
    al_azar = np.empty(BARAJADAS)
    for b in range(BARAJADAS):
        barajada = marca.copy()
        for pos in posiciones:
            barajada[pos] = rng.permutation(marca[pos])
        al_azar[b] = diferencia(barajada)
    casualidad = 100 * (np.sum(np.abs(al_azar) >= abs(observada) - 1e-12) + 1) / (BARAJADAS + 1)

    if tipo == "principal":
        hay = abs(observada) >= UMBRAL_PRINCIPAL_T_HA and casualidad < CASUALIDAD_PRINCIPAL
        lectura = "se ve una diferencia" if hay else "no se detecta diferencia"
    else:
        lectura = "pista" if casualidad < CASUALIDAD_SECUNDARIA else "no se detecta diferencia"

    return dict(
        tipo=tipo, grupo=grupo, referencia=referencia,
        medida="desviacion_municipal_absoluta" if absoluta else "desviacion_municipal",
        parcelas_grupo=int(en_grupo.sum()), parcelas_referencia=int(en_referencia.sum()),
        rendimiento_medio_grupo=round(y[en_grupo].mean(), 3),
        rendimiento_medio_referencia=round(y[en_referencia].mean(), 3),
        parcelas_grupo_comparables=int(marca.sum()), parcelas_referencia_comparables=int((~marca).sum()),
        media_grupo=round(valores[marca].mean(), 3), media_referencia=round(valores[~marca].mean(), 3),
        diferencia=round(observada, 3),
        azar_minimo=round(float(np.percentile(al_azar, 2.5)), 3),
        azar_maximo=round(float(np.percentile(al_azar, 97.5)), 3),
        casualidad_de_cada_100=round(casualidad, 1), lectura=lectura)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tablas", type=Path, default=TABLAS_POR_OMISION,
                    help="Carpeta donde está catalogo_parcelas.csv y donde se escribe el resultado")
    a = ap.parse_args()

    catalogo = pd.read_csv(a.tablas / "catalogo_parcelas.csv", dtype=str, keep_default_na=False,
                           encoding="utf-8-sig")
    k = catalogo[catalogo.rendimiento_t_ha != ""].reset_index(drop=True)
    assert len(k) == 138, "Se esperaban 138 parcelas con rendimiento"
    k["desviacion"] = desviacion_municipal(k)

    cat = k.contorno_categoria
    A, B, C = cat == "A", cat == "B", cat == "C"
    divisiones = k.contorno_divisiones_internas == "si"
    arboles = k.contorno_arboles_dentro == "si"
    angosta = k.contorno_angosta_o_muy_pequena == "si"

    rng = np.random.default_rng(SEMILLA)
    filas = [
        comparar(k, "principal", "B o C", "A", B | C, A, False, rng),
        comparar(k, "secundaria", "B", "A", B, A, False, rng),
        comparar(k, "secundaria", "C", "A", C, A, False, rng),
        comparar(k, "secundaria", "con divisiones internas", "sin divisiones internas", divisiones, ~divisiones, False, rng),
        comparar(k, "secundaria", "con árboles dentro", "sin árboles dentro", arboles, ~arboles, False, rng),
        comparar(k, "secundaria", "angosta o muy pequeña", "las demás", angosta, ~angosta, False, rng),
        comparar(k, "secundaria", "B o C", "A", B | C, A, True, rng),
    ]
    tabla = pd.DataFrame(filas)
    tabla.to_csv(a.tablas / "cruce_contorno_rendimiento.csv", index=False, encoding="utf-8-sig", lineterminator="\n")
    print(tabla.to_string(index=False))

    # --- Añadido después de ver el resultado: desglose descriptivo de la comparación principal.
    k["grupo"] = np.where(A, "A", "B o C")
    k["area"] = k.area_ha_origen.astype(float)
    con_bc = sorted(k.municipio[B | C].unique())
    filas = []
    for nombre, parte in [(m, k[k.municipio == m]) for m in con_bc] + [("todos", k[k.desviacion.notna()])]:
        for grupo in ("A", "B o C"):
            g = parte[parte.grupo == grupo]
            filas.append(dict(municipio=nombre, grupo=grupo, parcelas=len(g),
                              desviacion_media=round(g.desviacion.mean(), 3),
                              desviacion_mediana=round(g.desviacion.median(), 3),
                              parcelas_por_encima=int((g.desviacion > 1e-9).sum()),
                              parcelas_por_debajo=int((g.desviacion < -1e-9).sum()),
                              area_mediana_ha=round(g.area.median(), 2)))
    por_municipio = pd.DataFrame(filas)
    por_municipio.to_csv(a.tablas / "cruce_contorno_por_municipio.csv", index=False, encoding="utf-8-sig",
                         lineterminator="\n")
    detalle = k[B | C].sort_values(["municipio", "contorno_categoria", "id_parcela"])
    detalle = pd.DataFrame({
        "id_parcela": detalle.id_parcela, "municipio": detalle.municipio,
        "contorno_categoria": detalle.contorno_categoria,
        "contorno_angosta_o_muy_pequena": detalle.contorno_angosta_o_muy_pequena,
        "area_ha_origen": detalle.area_ha_origen, "rendimiento_t_ha": detalle.rendimiento_t_ha,
        "desviacion_municipal": detalle.desviacion.round(3)})
    detalle.to_csv(a.tablas / "cruce_contorno_parcelas_b_c.csv", index=False, encoding="utf-8-sig",
                   lineterminator="\n")
    print()
    print(por_municipio.to_string(index=False))
    print()
    print(detalle.to_string(index=False))
    print(f"\nParcelas conocidas sin desviación municipal (municipios con una sola): {int(k.desviacion.isna().sum())}")


if __name__ == "__main__":
    main()
