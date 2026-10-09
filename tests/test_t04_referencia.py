"""Regresiones de la frontera datos/procedencia; originales y cifras protegidos."""
import copy
import csv
import json
from pathlib import Path
import tempfile
import unittest

from scripts.t02_contrato import DATOS_T02, PROCEDENCIA_T02, separar_huellas
from scripts.t04_t02 import CAMPOS, conciliar, referencia_desde_tablas
from tests import test_t04_entrega as fixture_entrega


class Referencia(unittest.TestCase):
    def setUp(self):
        fixture_entrega.ConciliacionTests.setUp(self)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.t02 = self.root / "analisis/auditoria_catalogo_y_etiquetas"
        fila = self.ref["parcelas"][0]
        for nombre, campos in [("tablas/catalogo_parcelas.csv", CAMPOS[:5]),
                                ("tablas/soporte_por_parcela.csv", ("id_parcela", "area_ha_origen", *CAMPOS[5:]))]:
            p = self.t02/nombre; p.parent.mkdir(parents=True, exist_ok=True)
            with p.open("w", newline="") as f:
                w = csv.DictWriter(f, fieldnames=campos); w.writeheader()
                w.writerow({c: fila[c] for c in campos})
        for nombre in PROCEDENCIA_T02:
            p = self.t02/nombre; p.parent.mkdir(parents=True, exist_ok=True); p.write_text("procedencia identificada\n")
        self.ref = referencia_desde_tablas(self.t02, "revision_identificada", self.ref["entradas_sha256"])

    def ejecutar(self, ref=None):
        p = self.root/"referencia.json"; p.write_text(json.dumps(ref or self.ref))
        return conciliar(self.parcelas, self.mapas, self.soportes, self.centroides, self.manifest, p, self.root)

    def test_comentarios_o_auxiliares_ausentes_no_invalidan_datos(self):
        anterior = self.ejecutar()
        for nombre in PROCEDENCIA_T02:
            p = self.t02/nombre; p.write_text(p.read_text()+"# comentario nuevo\n")
        nuevo = self.ejecutar()
        self.assertEqual(nuevo, anterior)
        for nombre in PROCEDENCIA_T02: (self.t02/nombre).unlink()
        self.assertEqual(self.ejecutar(), anterior)
        self.assertEqual(set(nuevo["archivos_t02_sha256"]), DATOS_T02)
        self.assertEqual(set(nuevo["procedencia_t02_sha256"]), PROCEDENCIA_T02)

    def test_cada_tabla_alterada_o_faltante_detiene(self):
        for nombre in DATOS_T02:
            p = self.t02/nombre; anterior = p.read_bytes()
            with self.subTest(nombre=nombre):
                try:
                    p.write_bytes(anterior.replace(b"7.44", b"9.99"))
                    with self.assertRaisesRegex(ValueError, "T02 local cambió"): self.ejecutar()
                    p.unlink()
                    with self.assertRaisesRegex(ValueError, "T02 local cambió"): self.ejecutar()
                finally: p.write_bytes(anterior)

    def test_lectura_legacy_conserva_datos_y_procedencia(self):
        legacy = copy.deepcopy(self.ref)
        legacy["schema"] = "t04_referencia_t02_v1"
        legacy["archivos_sha256"].update(legacy.pop("procedencia_t02_sha256"))
        (self.t02/"scripts/construir_catalogo.py").write_text("# sólo comentario\n")
        resultado = self.ejecutar(legacy)
        self.assertEqual(resultado["maximos"], self.ejecutar()["maximos"])
        self.assertEqual(set(resultado["procedencia_t02_sha256"]), PROCEDENCIA_T02)

    def test_esquemas_incompletos_o_huellas_invalidas_no_se_aceptan(self):
        for modificar in [lambda r: r["archivos_sha256"].pop(next(iter(DATOS_T02))),
                          lambda r: r["procedencia_t02_sha256"].pop(next(iter(PROCEDENCIA_T02))),
                          lambda r: r.update(schema="t04_referencia_t02_v1"),
                          lambda r: r["archivos_sha256"].update({next(iter(DATOS_T02)): "no es SHA256"})]:
            r = copy.deepcopy(self.ref); modificar(r)
            with self.subTest(ref=r), self.assertRaises(ValueError): self.ejecutar(r)


if __name__ == "__main__": unittest.main()
