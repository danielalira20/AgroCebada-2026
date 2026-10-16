"""Pruebas del contrato de entrada de T14 (revisión de Diego). Usan una tabla sintética, sin datos reales."""
import sys
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from t14_clima import UNIDADES, centros, restar_centro, validar_clima, validar_particiones  # noqa: E402


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
        with self.assertRaises(ValueError):
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


def particiones_y_datos():
    ids = [f"AGC_{i:03d}" for i in range(1, 9)]
    d = pd.DataFrame({"CONJUNTO": ["ENTRENAMIENTO"] * 6 + ["PREDICCION"] * 2}, index=ids)
    part = pd.DataFrame([dict(ID_POLIGONO=i, repeticion=r, particion_principal=k % 2, particion_espacial=k % 3,
                              celda_chirps=f"c{k % 3}") for r in (1, 2) for k, i in enumerate(ids[:6])])
    return part, d


class ContratoParticiones(unittest.TestCase):
    def test_correctas_pasan(self):
        part, d = particiones_y_datos()
        self.assertEqual(len(validar_particiones(part, d)), 6)

    def test_id_repetido(self):
        part, d = particiones_y_datos()
        with self.assertRaises(ValueError):
            validar_particiones(pd.concat([part, part.iloc[[0]]]), d)

    def test_reservada_en_particiones(self):
        part, d = particiones_y_datos()
        extra = part.iloc[[0]].assign(ID_POLIGONO="AGC_007")
        with self.assertRaises(ValueError):
            validar_particiones(pd.concat([part, extra]), d)

    def test_celda_ausente(self):
        part, d = particiones_y_datos()
        part.loc[0, "celda_chirps"] = None
        with self.assertRaises(ValueError):
            validar_particiones(part, d)

    def test_celda_inconsistente(self):
        part, d = particiones_y_datos()
        part.loc[part.index[-1], "celda_chirps"] = "otra"
        with self.assertRaises(ValueError):
            validar_particiones(part, d)


class Centrado(unittest.TestCase):
    def test_media_cero_por_municipio_y_respaldo(self):
        tr = pd.DataFrame({"municipio": ["a", "a", "b", "b"], "grupo_registro": ["g"] * 4, "x": [1.0, 3.0, 10.0, 14.0]})
        c = centros(tr, ["x"])
        self.assertTrue((restar_centro(tr, ["x"], c).groupby(tr.municipio).x.mean().abs() < 1e-12).all())
        nuevo = pd.DataFrame({"municipio": ["z"], "grupo_registro": ["g"], "x": [7.0]})
        self.assertAlmostEqual(restar_centro(nuevo, ["x"], c).x.iloc[0], 7.0 - 7.0)   # centro del grupo = 7


if __name__ == "__main__":
    unittest.main()
