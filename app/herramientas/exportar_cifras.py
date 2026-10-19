"""Arma la tabla única de cifras (M03): cifras_parcelas.csv, cifras_municipios.csv y cifras_validacion.csv, la
misma fuente que usa el botón «Descargar cifras» de la vista Analista. El informe (T19), el video y el CSV de
entrega deben leer estos archivos: si alguien cambia un cálculo, se vuelve a correr y se avisa a Jas.

Uso (desde app/):  python herramientas/exportar_cifras.py [carpeta_salida]
Sin argumento, escribe en ../registro/t17/.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))   # para importar agrocebada_app desde app/

from agrocebada_app.backend.datos import paquete  # noqa: E402
from agrocebada_app.backend.datos.exportar import exportar_todo  # noqa: E402
from agrocebada_app.backend.dominio.confianza import confianza_municipios  # noqa: E402
from agrocebada_app.backend.modelo.estimador import predecir  # noqa: E402
from agrocebada_app.config import MODELO_OFICIAL  # noqa: E402

CARPETA_SALIDA = Path(__file__).resolve().parents[2] / "registro" / "t17"


def main():
    paquete.exigir_datos()
    carpeta = Path(sys.argv[1]) if len(sys.argv) > 1 else CARPETA_SALIDA
    d = paquete.parcelas()
    pred = predecir(d, MODELO_OFICIAL)
    O = paquete.validacion(MODELO_OFICIAL, d.municipio)
    OA = O[(O.escenario == "A") & (O.fuente == "municipio")] if O is not None else None
    conf = confianza_municipios(d, OA)
    rutas = exportar_todo(d, pred, conf, MODELO_OFICIAL, O, carpeta)
    for nombre, ruta in rutas.items():
        print(f"{nombre}: {ruta}")


if __name__ == "__main__":
    main()
