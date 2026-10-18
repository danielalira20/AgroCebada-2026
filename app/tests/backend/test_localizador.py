"""Pruebas del localizador de fuentes:  python tests/backend/test_localizador.py  (desde app/)."""
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agrocebada_app.backend.rutas.localizador import rutas  # noqa: E402

anterior = os.environ.get("AGRO_T04")
try:
    with tempfile.TemporaryDirectory() as tmp:
        archivo = Path(tmp) / "clima_parcela_mes.csv"
        archivo.write_text("id_parcela,periodo,variable,media_ponderada\n")
        os.environ["AGRO_T04"] = str(archivo)                    # el archivo
        assert rutas()["t04"] == archivo, rutas()["t04"]
        os.environ["AGRO_T04"] = tmp                             # o la carpeta que lo contiene
        assert rutas()["t04"] == archivo, rutas()["t04"]
    os.environ.pop("AGRO_T04")
    t04 = rutas()["t04"]                                         # sin variable: lo busca en el repo
    assert t04 is None or t04.name == "clima_parcela_mes.csv", t04
finally:
    if anterior is None:
        os.environ.pop("AGRO_T04", None)
    else:
        os.environ["AGRO_T04"] = anterior
print("OK")
