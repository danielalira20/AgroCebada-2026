"""Cobertura municipal exacta, sin depender de las parcelas reservadas."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd
from agrocebada_app.backend.dominio.planeador import municipios_disponibles


class MunicipiosTests(unittest.TestCase):
    def test_incluye_municipio_sin_reservadas_y_excluye_sin_cosechas(self):
        d = pd.DataFrame({"municipio": ["A", "B", "B", "C"],
                          "CONJUNTO": ["ENTRENAMIENTO", "ENTRENAMIENTO", "PREDICCION", "PREDICCION"],
                          "real": [3., 4., None, None]})
        self.assertEqual(municipios_disponibles(d), ["A", "B"])
        self.assertEqual(municipios_disponibles(d.iloc[3:]), [])

    def test_no_oculta_cosecha_invalida(self):
        for valor in (0., float('nan'), float('inf'), -1., True):
            d = pd.DataFrame({"municipio": ["A"], "CONJUNTO": ["ENTRENAMIENTO"], "real": [valor]})
            with self.assertRaises(ValueError):
                municipios_disponibles(d)


if __name__ == "__main__":
    unittest.main()
