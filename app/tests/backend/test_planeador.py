"""Referencia municipal y equivalencia de cuentas de fase 1; ejecutar este archivo."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np
import pandas as pd

from agrocebada_app.backend.datos import paquete
from agrocebada_app.backend.dominio.calculadora import columnas, cuentas, rango_municipio
from agrocebada_app.backend.dominio.planeador import estimacion_municipio, evaluar_cuenta
from agrocebada_app.backend.modelo.estimador import predecir
from agrocebada_app.config import MODELOS_CANDIDATOS


def datos(n=10):
    return pd.DataFrame({"municipio": ["M"] * n + ["M", "Sin cosechas"],
                         "CONJUNTO": ["ENTRENAMIENTO"] * n + ["PREDICCION"] * 2,
                         "real": [float(x + 1) for x in range(n)] + [999.0, np.nan]})


class PlaneadorTests(unittest.TestCase):
    def test_soporte_y_rango_sin_usar_predicciones(self):
        for n in (0, 1, 2, 3, 9, 10):
            d = datos(n)
            for modelo in MODELOS_CANDIDATOS:
                with self.subTest(n=n, modelo=modelo):
                    ref = estimacion_municipio(d, "M", modelo)
                    self.assertEqual(ref["n_cosecha_municipio"], n)
                    self.assertEqual(ref["n_cosecha_fuente"], n)
                    self.assertEqual(ref["estado"], "disponible" if n else "sin_soporte")
                    if n:
                        self.assertAlmostEqual(ref["rendimiento_t_ha"], (n + 1) / 2)
                        r = evaluar_cuenta(d, "M", ref["rendimiento_t_ha"], "Referencia", 5, 6000, 18000)
                        self.assertEqual(len(r["tabla"].columns), 3 if n >= 3 else 1)
                    else:
                        self.assertIsNone(ref["rendimiento_t_ha"])

    def test_sin_soporte_no_asigna_grupo_o_global(self):
        for municipio in ("Sin cosechas", "Fuera del catálogo"):
            ref = estimacion_municipio(datos(), municipio, MODELOS_CANDIDATOS[0])
            self.assertEqual(ref["estado"], "sin_soporte")
            self.assertIsNone(ref["fuente"])
            self.assertIsNone(ref["rendimiento_t_ha"])

    def test_rechaza_modelo_y_cosechas_invalidas(self):
        with self.assertRaises(ValueError):
            estimacion_municipio(datos(), "M", "inventado")
        for valor in (np.nan, np.inf, -np.inf, 0.0, -1.0, True, "4.0"):
            d = datos().astype({"real": object})
            d.loc[0, "real"] = valor
            with self.subTest(valor=valor), self.assertRaises(ValueError):
                estimacion_municipio(d, "M", MODELOS_CANDIDATOS[0])

    def test_cuenta_manual_y_registrada_fuera_del_rango(self):
        d = datos(3)
        antes = d.copy(deep=True)
        r = evaluar_cuenta(d, "M", 4.48, "Con tu cosecha registrada", 5, 6000, 18000)
        self.assertEqual(r["estado"], "calculada")
        self.assertEqual(r["umbral"], 3.0)
        t = r["tabla"]
        self.assertAlmostEqual(t.iloc[4, 0], 44400)
        self.assertGreater(t.iloc[0, 0], r["rango"]["alto"])
        pd.testing.assert_frame_equal(d, antes)

    def test_captura_pendiente_invalida_y_overflow(self):
        for area, precio, costo in ((None, 1, 1), (1, None, 1), (1, 1, None), (1, 0, 1), (1, 1, 0)):
            r = evaluar_cuenta(datos(), "M", 4, "Referencia", area, precio, costo)
            self.assertEqual(r["estado"], "pendiente")
            self.assertIsNone(r["tabla"])
        for area, precio, costo in ((0, 1, 1), (.009, 1, 1), (1, -1, 1), (1, 1, -1),
                                     (True, 1, 1), (1, np.inf, 1), (1, 1, np.nan),
                                     (1, 10 ** 1000, 1), (1e308, 1e308, 1)):
            r = evaluar_cuenta(datos(), "M", 4, "Referencia", area, precio, costo)
            self.assertEqual(r["estado"], "invalida")
            self.assertTrue(r["errores"])
            self.assertIsNone(r["tabla"])

    def test_rango_nulo_y_equilibrio(self):
        d = datos(3)
        d.loc[d.CONJUNTO == "ENTRENAMIENTO", "real"] = 3.5
        r = evaluar_cuenta(d, "M", 3.5, "Referencia", 10, 6000, 21000)
        self.assertEqual(r["rango"]["bajo"], r["rango"]["alto"])
        self.assertTrue((r["tabla"].loc["Ingreso menos costo"] == 0).all())
        self.assertTrue((r["tabla"].loc["¿Cubre costos?"] == "Sí").all())

    def test_catalogo_real_y_las_59_ambos_modelos(self):
        paquete.exigir_datos()
        d = paquete.parcelas()
        antes = d.copy(deep=True)
        self.assertEqual(d.municipio.nunique(), 9)
        for modelo in MODELOS_CANDIDATOS:
            refs = {m: estimacion_municipio(d, m, modelo) for m in d.municipio.unique()}
            self.assertTrue(all(r["estado"] == "disponible" for r in refs.values()))
            p = predecir(d, modelo)
            self.assertEqual(len(p), 59)
            for fila in p.itertuples():
                self.assertLessEqual(abs(refs[fila.municipio]["rendimiento_t_ha"] - fila.prediccion), 1e-12)
            for m, ref in refs.items():
                rend = ref["rendimiento_t_ha"]
                esperado = cuentas(columnas(rend, "Referencia", rango_municipio(d, m)), 10, 5500, 22000)
                actual = evaluar_cuenta(d, m, rend, "Referencia", 10, 5500, 22000)
                pd.testing.assert_frame_equal(actual["tabla"], esperado)
        pd.testing.assert_frame_equal(d, antes)


if __name__ == "__main__":
    unittest.main()
