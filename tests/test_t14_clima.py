"""Pruebas del contrato de entrada de T14 (revisión de Diego). Usan una tabla sintética, sin datos reales."""
import sys
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from t14_clima import UNIDADES, validar_clima  # noqa: E402


def tabla():
    filas = []
    for pid in ["AGC_001", "AGC_002"]:
        for anio in range(2022, 2026):
            for mes in range(1, 13):
                for var, u in UNIDADES.items():
                    filas.append(dict(id_parcela=pid, periodo=f"{anio}-{mes:02d}", variable=var, unidad=u,
                                      media_ponderada=10.0, estado="cobertura_completa", cobertura_valida=1.0,
                                      posterior_al_corte=(anio, mes) > (2025, 10)))
    return pd.DataFrame(filas)


class ContratoClima(unittest.TestCase):
    def test_tabla_correcta_pasa(self):
        self.assertEqual(len(validar_clima(tabla())), 2 * 3 * 7)

    def falla(self, c):
        with self.assertRaises(AssertionError):
            validar_clima(c)

    def test_clave_repetida(self):
        c = tabla()
        self.falla(pd.concat([c, c.iloc[[100]]]))

    def test_mes_faltante(self):
        c = tabla()
        self.falla(c.drop(c[(c.periodo == "2025-07") & (c.variable == "PREC")].index[:1]))

    def test_unidad_incorrecta(self):
        c = tabla()
        c.loc[0, "unidad"] = "K"
        self.falla(c)

    def test_variable_inesperada(self):
        c = tabla()
        c.loc[0, "variable"] = "HUM"
        self.falla(c)

    def test_estado_no_permitido(self):
        c = tabla()
        c.loc[0, "estado"] = "otro"
        self.falla(c)

    def test_cobertura_fuera_de_rango(self):
        c = tabla()
        c.loc[0, "cobertura_valida"] = 1.5
        self.falla(c)

    def test_bandera_de_corte_incoherente(self):
        c = tabla()
        c.loc[0, "posterior_al_corte"] = True
        self.falla(c)

    def test_valor_vacio_en_temporada(self):
        c = tabla()
        c.loc[(c.periodo == "2025-08") & (c.variable == "Tmin"), "media_ponderada"] = float("nan")
        self.falla(c)


if __name__ == "__main__":
    unittest.main()
