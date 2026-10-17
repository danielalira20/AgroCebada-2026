"""Pruebas de la extensión de T13 (D025)."""
import sys
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import t11_aporte_satelital as t11  # noqa: E402
import t13_extension_indices as ext  # noqa: E402
import t13_indices as t13  # noqa: E402

HAY_SERIES = (ext.SERIES / "serie_sentinel2.csv").exists() and (ext.SERIES / "serie_planet.csv").exists()


class TestDisenoD025(unittest.TestCase):
    def test_configuraciones_como_en_d025(self):
        c = {n: cfg["cols"] for n, cfg in ext.CONFIGS.items()}
        self.assertEqual(sorted(c), list(range(1, 8)))
        nombres = lambda cols: [x.split("_")[1] for x in cols]  # noqa: E731
        self.assertEqual(nombres(c[1]), ["evi", "savi", "fapar", "mra"])
        self.assertEqual(nombres(c[2]), ["endwi", "dswi4", "dswi5"])
        self.assertEqual(nombres(c[3]), ["crc", "mcrc", "srndi", "nddi", "enddi"])
        self.assertEqual(nombres(c[4]), ["ndti", "ndsvi"])
        self.assertEqual(c[5], ["pl_evi_max_abr_oct", "pl_msavi_max_abr_oct"])
        self.assertEqual(c[6], ["s2_ndvi_max_abr_oct"] + c[3])
        self.assertEqual(c[7], t13.CONFIGS[3]["cols"])  # control = t13_c3
        quitados = set(ext.S2_QUITADOS)
        self.assertFalse(quitados & {x.split("_")[1] for cfg in c.values() for x in cfg})

    def test_usa_t11_sin_tocar_t11_ni_t13(self):
        m = ext.cargar_estimador()
        self.assertEqual(m.CONFIGS, ext.CONFIGS)
        self.assertEqual(t11.VERSION, "T11-v2.1")
        self.assertEqual(t11.SALIDA.name, "t11")
        self.assertEqual(len(t13.CONFIGS), 8)
        self.assertEqual(t13.CANDIDATOS[3], "t13_c3_ndvi_s2")


@unittest.skipUnless(HAY_SERIES, "faltan las series de T06 en data/interim/t06/")
class TestResumenConSeriesReales(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.var = ext.resumir_indices()
        cls.tabla = pd.read_csv(t11.TABLA)

    def test_reproduce_las_columnas_de_t06(self):
        ext.comprobar_resumen(self.var, self.tabla)  # se detiene si no coinciden

    def test_pares_quitados_son_casi_identicos(self):
        c = self.var.corr(method="spearman", numeric_only=True)
        for quitado, se_queda in ext.S2_QUITADOS.items():
            with self.subTest(quitado=quitado):
                self.assertGreaterEqual(abs(c.loc[ext.s2(quitado), ext.s2(se_queda)]), 0.99)

    def test_ningun_par_usado_es_casi_identico(self):
        usadas = sorted({x for cfg in ext.CONFIGS.values() for x in cfg["cols"]})
        c = self.var[usadas].corr(method="spearman").abs()
        for i, a in enumerate(usadas):
            for b in usadas[i + 1:]:
                with self.subTest(a=a, b=b):
                    self.assertLess(c.loc[a, b], 0.99)

    def test_detiene_si_no_reproduce_t06(self):
        mal = self.var.copy()
        mal.loc[0, "s2_ndvi_max_abr_oct"] += 0.01
        with self.assertRaises(ValueError):
            ext.comprobar_resumen(mal, self.tabla)


if __name__ == "__main__":
    unittest.main()