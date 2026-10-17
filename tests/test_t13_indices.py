"""Pruebas de T13 con los datos del repositorio (D024)."""
import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import t11_aporte_satelital as t11  # noqa: E402
import t13_indices as t13  # noqa: E402

HAY_DATOS = t11.TABLA.exists() and t11.PARTICIONES.exists()


class TestDisenoD024(unittest.TestCase):
    def test_configuraciones_como_en_d024(self):
        cols = {n: cfg["cols"] for n, cfg in t13.CONFIGS.items()}
        self.assertEqual(sorted(cols), list(range(1, 9)))
        self.assertEqual(cols[1], ["pl_ndvi_max_abr_oct"])
        self.assertEqual(cols[2], ["pl_lai2_max_abr_oct"])
        self.assertEqual(cols[3], ["s2_ndvi_max_abr_oct"])
        self.assertEqual(cols[4], ["s2_ndwi_en_maximo_abr_oct"])
        self.assertEqual(cols[5], ["ls_vi6t_mediana_abr_oct"])
        self.assertEqual(set(cols[6]), {c[0] for n, c in cols.items() if n <= 5})
        self.assertEqual(set(cols[7]), set(cols[6]) - {"pl_ndvi_max_abr_oct", "s2_ndvi_max_abr_oct"})
        self.assertEqual(set(cols[8]), set(cols[6]) - {"ls_vi6t_mediana_abr_oct"})
        self.assertTrue(all(c.endswith("abr_oct") for cfg in cols.values() for c in cfg))
        self.assertFalse(any(cfg["centrar"] for cfg in t13.CONFIGS.values()))

    def test_usa_el_estimador_de_t11_sin_tocar_t11(self):
        m = t13.cargar_estimador()
        self.assertEqual(m.CONFIGS, t13.CONFIGS)
        self.assertEqual(m.SALIDA, t13.SALIDA)
        self.assertEqual((m.ALFAS, m.N_INTERNAS, m.SEMILLA_INTERNA, m.N_BOOT, m.SEMILLA_BOOT),
                         (t11.ALFAS, t11.N_INTERNAS, t11.SEMILLA_INTERNA, t11.N_BOOT, t11.SEMILLA_BOOT))
        # El módulo de T11 que usan sus propias pruebas sigue igual
        self.assertEqual(t11.VERSION, "T11-v2.1")
        self.assertEqual(t11.CANDIDATOS[1], "t11_c1_calidad_planet_abr_oct")
        self.assertEqual(t11.SALIDA.name, "t11")


@unittest.skipUnless(HAY_DATOS, "faltan registro/t07/tabla_comun.csv o registro/t03/particiones.csv")
class TestT13ConDatosReales(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tabla = pd.read_csv(t11.TABLA)

    def test_columnas_existen_y_sin_faltantes(self):
        entr = self.tabla[self.tabla.conjunto_origen == "ENTRENAMIENTO"]
        self.assertEqual(len(entr), 138)
        for col in t13.CINCO:
            with self.subTest(columna=col):
                self.assertIn(col, self.tabla.columns)
                self.assertEqual(int(self.tabla[col].isna().sum()), 0)

    def test_redundancia_no_usa_el_rendimiento(self):
        antes = t13.redundancia(self.tabla)
        mod = self.tabla.copy()
        mod["rendimiento_t_ha"] = np.random.RandomState(0).permutation(mod.rendimiento_t_ha.values)
        despues = t13.redundancia(mod)
        pd.testing.assert_frame_equal(antes, despues)
        self.assertEqual(len(antes), 2 * 2 * 10)  # 2 poblaciones × 2 métodos × 10 pares


if __name__ == "__main__":
    unittest.main()