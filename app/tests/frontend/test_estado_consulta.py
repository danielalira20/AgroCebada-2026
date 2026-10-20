"""Modo y municipio canónicos sobreviven al desmontaje de controles."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agrocebada_app.frontend.estado.planeador import (
    guardar_catalogo, guardar_entrada, guardar_modo, preparar_catalogo, preparar_modo, preparar_municipio,
)


class EstadoConsultaTests(unittest.TestCase):
    def test_catalogo_restaura_seleccion_sin_sobrescribir_clic(self):
        estado = {"agri_muni": "A", "agri_parcela": "P1", "encuadre_agri": "P1"}
        guardar_catalogo(estado)
        del estado["agri_muni"], estado["agri_parcela"]
        preparar_catalogo(estado)
        self.assertEqual(estado["agri_parcela"], "P1")
        estado["agri_parcela"] = "P2"
        preparar_catalogo(estado)
        self.assertEqual(estado["agri_parcela"], "P2")

    def test_catalogo_inicial_y_recorrido_retenido(self):
        estado = {}
        preparar_modo(estado)
        self.assertEqual(estado["agri_modo_control"], "Parcela del catálogo")
        estado["agri_modo_control"] = "Consulta rápida"
        guardar_modo(estado)
        del estado["agri_modo_control"]
        preparar_modo(estado)
        self.assertEqual(estado["agri_modo_control"], "Consulta rápida")

    def test_municipio_independiente_del_catalogo(self):
        estado = {"agri_muni": "A"}
        preparar_municipio(estado, ["A", "B"])
        self.assertIsNone(estado["calc_municipio_rapido"])
        estado["calc_municipio_rapido"] = "B"
        guardar_entrada(estado, "calc_municipio_rapido", "municipio_rapido")
        del estado["calc_municipio_rapido"]
        preparar_municipio(estado, ["A", "B"])
        self.assertEqual(estado["calc_municipio_rapido"], "B")
        self.assertEqual(estado["agri_muni"], "A")
        preparar_municipio(estado, ["A"])
        self.assertIsNone(estado["calc_municipio_rapido"])
        self.assertIsNone(estado["planeador"]["municipio_rapido"])

    def test_selector_invalido_y_catalogo_vacio(self):
        estado = {"agri_modo": "inexistente"}
        preparar_modo(estado)
        self.assertEqual(estado["agri_modo"], "Parcela del catálogo")
        preparar_municipio(estado, [])
        self.assertIsNone(estado["calc_municipio_rapido"])


if __name__ == "__main__":
    unittest.main()
