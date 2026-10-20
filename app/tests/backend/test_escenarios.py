"""Escenarios económicos, escala y orientación de fase 2, sin Streamlit."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd

from agrocebada_app.backend.dominio.planeador import (
    cobertura_saldo, escenarios_cuenta, evaluar_cuenta, importe, plan_si_sale_mal, posiciones_barra,
)


def cuenta(reales=(2., 3., 5.), referencia=4., costo=18000.):
    d = pd.DataFrame({"municipio": ["M"] * len(reales), "CONJUNTO": ["ENTRENAMIENTO"] * len(reales),
                      "real": list(reales)})
    return evaluar_cuenta(d, "M", referencia, "Original", 5., 6000., costo)


class EscenariosTests(unittest.TestCase):
    def test_tarjetas_desde_tabla_sin_cambiarla(self):
        resultado = cuenta()
        original = resultado["tabla"].copy(deep=True)
        ss = escenarios_cuenta(resultado, "Cosecha registrada 2025")
        self.assertEqual([s["id"] for s in ss], ["bajo", "referencia", "alto"])
        self.assertEqual(ss[1]["etiqueta"], "Cosecha registrada 2025")
        self.assertEqual(ss[0]["etiqueta"], "Menor rendimiento registrado")
        filas = {"rendimiento_t_ha": "Rendimiento (t/ha)", "produccion_t": "Producción (t)",
                 "ingreso": "Ingreso", "costo": "Costo", "saldo": "Ingreso menos costo"}
        for s in ss:
            for campo, fila in filas.items():
                self.assertEqual(s[campo], original.loc[fila, s["columna"]])
        pd.testing.assert_frame_equal(original, resultado["tabla"])

    def test_percentiles_y_menos_de_tres(self):
        ss = escenarios_cuenta(cuenta(tuple(float(x) for x in range(1, 11))), "Referencia")
        self.assertEqual(ss[0]["etiqueta"], "Rendimiento bajo")
        for reales in ((3.,), (3., 4.)):
            ss = escenarios_cuenta(cuenta(reales), "Referencia")
            self.assertEqual([s["id"] for s in ss], ["referencia"])
            self.assertIsNone(posiciones_barra(ss, 3.))

    def test_pendiente_sin_escenarios_ni_plan(self):
        ss = escenarios_cuenta({"estado": "pendiente"}, "Referencia")
        self.assertEqual(ss, [])
        self.assertIsNone(plan_si_sale_mal(ss))

    def test_plan_usa_bajo_aunque_referencia_cubra(self):
        ss = escenarios_cuenta(cuenta(), "Referencia")
        self.assertEqual(ss[1]["cobertura"], "cubre")
        p = plan_si_sale_mal(ss)
        self.assertEqual((p["estado"], p["escenario_id"], p["faltante"], p["abierto"]),
                         ("falta", "bajo", 30000., True))
        self.assertEqual(len(p["pasos"]), 3)
        self.assertIn("$30,000", p["apertura"])

    def test_plan_cubre_equilibrio_y_unica_referencia(self):
        for costo, estado in ((6000., "cubre"), (12000., "equilibrio")):
            p = plan_si_sale_mal(escenarios_cuenta(cuenta(costo=costo), "Referencia"))
            self.assertEqual(p["estado"], estado)
            self.assertEqual(p["faltante"], 0.)
            self.assertFalse(p["abierto"])
        p = plan_si_sale_mal(escenarios_cuenta(cuenta((3.,), costo=24000.), "Referencia"))
        self.assertEqual(p["escenario_id"], "referencia")
        self.assertIn("Con la única referencia disponible", p["apertura"])
        self.assertNotIn("escenario bajo", p["apertura"])

    def test_posiciones_preservan_valores_fuera_de_rango(self):
        ss = escenarios_cuenta(cuenta(referencia=8.), "Cosecha registrada 2025")
        for umbral in (0., 1., 4., 20., 1e308):
            barra = posiciones_barra(ss, umbral)
            self.assertTrue(all(0 <= m["posicion"] <= 100 for m in barra["marcas"]))
            marcas = sorted(barra["marcas"], key=lambda m: m["valor"])
            self.assertEqual([m["posicion"] for m in marcas], sorted(m["posicion"] for m in marcas))
            self.assertLessEqual(barra["minimo"], umbral)
            self.assertGreaterEqual(barra["maximo"], umbral)
        self.assertFalse(posiciones_barra(ss, 1e308)["legible"])
        for umbral in (float("nan"), float("inf"), -1., True):
            with self.assertRaises(ValueError):
                posiciones_barra(ss, umbral)

    def test_todas_las_marcas_iguales(self):
        ss = escenarios_cuenta(cuenta((3.5, 3.5, 3.5), referencia=3.5), "Referencia")
        barra = posiciones_barra(ss, 3.5)
        self.assertTrue(all(m["posicion"] == 50. for m in barra["marcas"]))
        self.assertFalse(barra["legible"])

    def test_importes_pequenos_y_tolerancia(self):
        self.assertEqual(importe(28600.), "$28,600")
        self.assertEqual(importe(-.50), "-$0.50")
        self.assertEqual(importe(.10), "$0.10")
        self.assertEqual(importe(.001), "menos de $0.01")
        self.assertEqual(importe(-.001), "entre -$0.01 y $0")
        self.assertEqual(importe(-1e-10), "$0")
        self.assertEqual(cobertura_saldo(-1e-10), "equilibrio")
        self.assertEqual(cobertura_saldo(-.10), "falta")


if __name__ == "__main__":
    unittest.main()
