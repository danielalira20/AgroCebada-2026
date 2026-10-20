"""Retención del estado de cuentas sin depender de un runtime Streamlit."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agrocebada_app.frontend.estado.planeador import (
    guardar_entrada, hidratar_compatibilidad, iniciar_planeador, preparar_area,
)


class EstadoPlaneadorTests(unittest.TestCase):
    def test_migra_sesion_existente_sin_cruzar_area_rapida(self):
        estado = {"calc_precio": 5500.0, "calc_costo": 22000.0, "calc_area_A": 12.0, "calc_area_rapida": 7.0}
        p = iniciar_planeador(estado)
        self.assertEqual(p["areas_parcela_ha"], {"A": 12.0})
        self.assertEqual(p["area_rapida_ha"], 7.0)
        self.assertEqual(p["precio_t"], 5500.0)

    def test_restaurar_tras_desmontar_widgets(self):
        estado = {}
        hidratar_compatibilidad(estado)
        preparar_area(estado, "calc_area_A", 5.0, "A")
        for clave, campo, valor, pid in (("calc_precio", "precio_t", 6000.0, None),
                                         ("calc_costo", "costo_ha", 18000.0, None),
                                         ("calc_area_A", "area", 9.0, "A")):
            estado[clave] = valor
            guardar_entrada(estado, clave, campo, pid)
        for clave in ("calc_precio", "calc_costo", "calc_area_A"):
            del estado[clave]
        hidratar_compatibilidad(estado)
        preparar_area(estado, "calc_area_A", 5.0, "A")
        self.assertEqual([estado[k] for k in ("calc_precio", "calc_costo", "calc_area_A")], [6000, 18000, 9])

    def test_areas_separadas_y_limpiar_none(self):
        estado = {}
        preparar_area(estado, "calc_area_A", 5.0, "A")
        preparar_area(estado, "calc_area_B", 8.0, "B")
        estado["calc_area_A"] = None
        guardar_entrada(estado, "calc_area_A", "area", "A")
        estado["calc_precio"] = None
        guardar_entrada(estado, "calc_precio", "precio_t")
        del estado["calc_area_A"]
        hidratar_compatibilidad(estado)
        preparar_area(estado, "calc_area_A", 5.0, "A")
        self.assertIsNone(estado["calc_area_A"])
        self.assertIsNone(estado["calc_precio"])
        self.assertEqual(estado["calc_area_B"], 8.0)

    def test_area_rapida_limpiada_no_reaparece_al_remontar(self):
        estado = {}
        preparar_area(estado, "calc_area_rapida", 10.0)
        self.assertEqual(estado["calc_area_rapida"], 10.0)
        estado["calc_area_rapida"] = None
        guardar_entrada(estado, "calc_area_rapida", "area_rapida_ha")
        del estado["calc_area_rapida"]
        preparar_area(estado, "calc_area_rapida", 10.0)
        self.assertIsNone(estado["calc_area_rapida"])
        self.assertEqual(estado["planeador"]["areas_parcela_ha"], {})

    def test_estado_v1_sin_marca_interna_conserva_area_existente(self):
        estado = {}
        p = iniciar_planeador(estado)
        p.pop("_area_rapida_inicializada")
        p["area_rapida_ha"] = 7.0
        preparar_area(estado, "calc_area_rapida", 10.0)
        self.assertEqual(estado["calc_area_rapida"], 7.0)


if __name__ == "__main__":
    unittest.main()
