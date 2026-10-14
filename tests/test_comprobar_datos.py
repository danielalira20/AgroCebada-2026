"""Comprobación de datos originales (scripts/comprobar_datos.py): casos con y sin datos locales."""
import hashlib
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from scripts.comprobar_datos import comprobar


def _zip_con(ruta, miembros):
    with zipfile.ZipFile(ruta, "w") as z:
        for nombre, datos in miembros.items():
            z.writestr(nombre, datos)
    return hashlib.sha256(Path(ruta).read_bytes()).hexdigest()


class ComprobarDatos(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.raiz = Path(self._tmp.name)
        (self.raiz / "registro/t04").mkdir(parents=True)
        (self.raiz / "data/raw").mkdir(parents=True)

    def _procedencia(self, sha):
        (self.raiz / "registro/t04/procedencia.json").write_text(
            json.dumps({"sha256_paquete": sha}), encoding="utf-8")

    def test_sin_datos_locales_se_omite_con_aviso(self):
        self._procedencia("0" * 64)
        r = comprobar(self.raiz)
        self.assertEqual(r["resultado"], "omitida")
        self.assertIn("DataSet.zip", r["motivo"])

    def test_carpeta_extraida_sin_zip_se_detiene(self):
        self._procedencia("0" * 64)
        (self.raiz / "data/raw/DATASET_RETO_AGRO_2026").mkdir()
        with self.assertRaises(SystemExit) as c:
            comprobar(self.raiz)
        self.assertIn("no se puede verificar", str(c.exception))

    def test_zip_distinto_al_registrado_se_detiene(self):
        _zip_con(self.raiz / "data/raw/DataSet.zip", {"DATASET_RETO_AGRO_2026/a.txt": "uno"})
        self._procedencia("0" * 64)
        with self.assertRaises(SystemExit) as c:
            comprobar(self.raiz)
        self.assertIn("distinto", str(c.exception))

    def test_zip_correcto_y_carpeta_idéntica_aprueba(self):
        sha = _zip_con(self.raiz / "data/raw/DataSet.zip", {"DATASET_RETO_AGRO_2026/a.txt": "uno"})
        self._procedencia(sha)
        carpeta = self.raiz / "data/raw/DATASET_RETO_AGRO_2026"
        carpeta.mkdir()
        (carpeta / "a.txt").write_text("uno", encoding="utf-8")
        r = comprobar(self.raiz)
        self.assertEqual(r["resultado"], "aprobado")
        self.assertEqual(r["carpeta_extraida"], "idéntica al ZIP")

    def test_carpeta_extraida_distinta_del_zip_se_detiene(self):
        sha = _zip_con(self.raiz / "data/raw/DataSet.zip", {"DATASET_RETO_AGRO_2026/a.txt": "uno"})
        self._procedencia(sha)
        carpeta = self.raiz / "data/raw/DATASET_RETO_AGRO_2026"
        carpeta.mkdir()
        (carpeta / "a.txt").write_text("otro", encoding="utf-8")
        with self.assertRaises(SystemExit) as c:
            comprobar(self.raiz)
        self.assertIn("no coincide", str(c.exception))


if __name__ == "__main__":
    unittest.main()
