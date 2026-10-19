"""Arma el paquete compacto `datos_app/` que lee la app: las mismas cifras, en archivos chicos y rápidos de leer.

Lee las fuentes originales del repo (dataset del reto, T08, T03 y T04) y guarda sólo lo que la app muestra:
parcelas con su geometría, series de índices de la temporada 2025 (Sentinel-2 y Planet, nubosidad <= 20 %), clima
mensual, predicciones de validación de los dos modelos, las 59 oficiales y el soporte de datos por parcela.

Uso (desde app/):  python herramientas/preparar_datos.py
Volver a correrlo si cambian T08, T03, T04 o el dataset.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))   # para importar agrocebada_app desde app/

from agrocebada_app.backend.datos import lectura  # noqa: E402
from agrocebada_app.backend.datos.paquete import FALTA_DATASET, exigir_datos  # noqa: E402
from agrocebada_app.backend.rutas.localizador import rutas  # noqa: E402
from agrocebada_app.config import CLAVE_DATASET, PAQ  # noqa: E402


def main():
    exigir_datos()                       # mensaje claro si falta el dataset del reto
    r = rutas()
    if r["datos"] is None or not (Path(r["datos"]) / CLAVE_DATASET).exists() or r["t08"] is None:
        raise SystemExit(FALTA_DATASET if r["datos"] is None or not (Path(r["datos"]) / CLAVE_DATASET).exists() else "No encontré las salidas de T08 en registro/; fija AGRO_T08.")
    PAQ.mkdir(exist_ok=True)
    d = lectura.leer_parcelas(r["datos"])
    d.to_parquet(PAQ / "parcelas.parquet")
    lectura.leer_series(r["datos"]).to_parquet(PAQ / "series.parquet", index=False)
    if r["t04"]:
        lectura.leer_clima(r["t04"]).to_parquet(PAQ / "clima.parquet", index=False)
        lectura.leer_clima_normal(r["t04"]).to_parquet(PAQ / "clima_normal.parquet", index=False)
    v = lectura.leer_validacion(r["t08"])
    v[["ID_POLIGONO", "repeticion", "particion", "escenario", "real", "prediccion", "candidato", "fuente"]].to_parquet(
        PAQ / "validacion.parquet", index=False)
    lectura.leer_oficial(r["t08"])[["ID_POLIGONO", "candidato", "prediccion"]].to_csv(PAQ / "oficial_59.csv", index=False)
    if r["t03"]:
        lectura.leer_soporte(r["t03"]).to_parquet(PAQ / "soporte.parquet")
    if r.get("t07"):
        c = lectura.leer_calidad(r["t07"])
        if c is not None:
            c.to_parquet(PAQ / "calidad.parquet")
    total = sum(f.stat().st_size for f in PAQ.iterdir())
    print(f"datos_app/ listo: {len(list(PAQ.iterdir()))} archivos, {total / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
