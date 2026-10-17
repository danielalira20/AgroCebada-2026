"""Arma el paquete compacto `datos_app/` que lee la app: las mismas cifras, en archivos chicos y rápidos de leer.

Lee las fuentes originales del repo (dataset del reto, T08, T03 y T04) y guarda sólo lo que la app muestra:
parcelas con su geometría, series de índices de la temporada 2025 (Sentinel-2 y Planet, nubosidad <= 20 %), clima
mensual, predicciones de validación de los dos modelos, las 59 oficiales y el soporte de datos por parcela.

Uso (desde esta carpeta):  python preparar_datos.py
Volver a correrlo si cambian T08, T03, T04 o el dataset.
"""
import os

os.environ["AGRO_SIN_PAQUETE"] = "1"          # leer siempre las fuentes originales

import agro_datos as A  # noqa: E402


def main():
    r = A.rutas()
    if r["datos"] is None or r["t08"] is None:
        raise SystemExit("No encontré el dataset o T08. Fija AGRO_DATOS y AGRO_T08.")
    A.PAQ.mkdir(exist_ok=True)
    d = A.leer_parcelas(r["datos"])
    d.to_parquet(A.PAQ / "parcelas.parquet")
    A.leer_series(r["datos"]).to_parquet(A.PAQ / "series.parquet", index=False)
    if r["t04"]:
        A.leer_clima(r["t04"]).to_parquet(A.PAQ / "clima.parquet", index=False)
    v = A.leer_validacion(r["t08"])
    v[["ID_POLIGONO", "repeticion", "particion", "escenario", "real", "prediccion", "candidato", "fuente"]].to_parquet(
        A.PAQ / "validacion.parquet", index=False)
    A.leer_oficial(r["t08"])[["ID_POLIGONO", "candidato", "prediccion"]].to_csv(A.PAQ / "oficial_59.csv", index=False)
    if r["t03"]:
        A.leer_soporte(r["t03"]).to_parquet(A.PAQ / "soporte.parquet")
    total = sum(f.stat().st_size for f in A.PAQ.iterdir())
    print(f"datos_app/ listo: {len(list(A.PAQ.iterdir()))} archivos, {total / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
