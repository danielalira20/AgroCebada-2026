import csv
from pathlib import Path
import tempfile
import unittest
from scripts.t07_fuentes import leer_csv, leer_json, validar_catalogo, validar_mensuales


def parcela(pid="AGC_001", y="3.5", grupo="ENTRENAMIENTO"):
    return dict(id_parcela=pid, rendimiento_t_ha=y, conjunto_origen=grupo,
                area_ha_origen="7.61", municipio="Calpulalpan", estado="Tlaxcala",
                cultivo_origen="Cebada")


def mes(periodo="2025-04", variable="PREC", media="10", estado="cobertura_completa", cobertura="1"):
    return dict(id_parcela="AGC_001", periodo=periodo, variable=variable,
                unidad="mm/mes" if variable == "PREC" else "grados Celsius",
                media_ponderada=media, estado=estado, cobertura_valida=cobertura,
                valor_centroide="", diferencia_media_menos_centroide="",
                centroide_dentro_parcela="True", posterior_al_corte="False")


class Fuentes(unittest.TestCase):
    def test_catalogo_conserva_texto_etiqueta_y_orden(self):
        r = [parcela("AGC_002", "", "PREDICCION"), parcela()]
        out = validar_catalogo(r, 2, 1)
        self.assertEqual([x["id_parcela"] for x in out], ["AGC_001", "AGC_002"])
        self.assertEqual([x["rendimiento_t_ha"] for x in out], ["3.5", ""])
        self.assertEqual(out[0]["campania"], "2025")

    def test_catalogo_duplicados(self):
        with self.assertRaises(ValueError): validar_catalogo([parcela(), parcela()], 2, 2)

    def test_etiqueta_reservada_rechazada(self):
        with self.assertRaises(ValueError): validar_catalogo([parcela(grupo="PREDICCION")], 1, 1)

    def test_catalogo_no_finito(self):
        with self.assertRaises(ValueError): validar_catalogo([parcela(y="nan")], 1, 1)

    def test_mes_duplicado(self):
        with self.assertRaises(ValueError): validar_mensuales([mes(), mes()], {"AGC_001"}, "2025-10-31")

    def test_unidad_y_corte(self):
        for campo, valor in [("unidad", "mm"), ("posterior_al_corte", "True"), ("id_parcela", "OTRO")]:
            r = mes(); r[campo] = valor
            with self.subTest(campo=campo), self.assertRaises(ValueError):
                validar_mensuales([r], {"AGC_001"}, "2025-10-31")

    def test_nodata_no_es_cero(self):
        self.assertEqual(len(validar_mensuales([mes(media="", estado="todo_nodata", cobertura="0")],
                                               {"AGC_001"}, "2025-10-31")), 1)
        with self.assertRaises(ValueError):
            validar_mensuales([mes(media="0", estado="todo_nodata", cobertura="0")], {"AGC_001"}, "2025-10-31")

    def test_prec_cero_real_y_temperatura_negativa(self):
        self.assertEqual(len(validar_mensuales([mes(media="0"), mes(variable="Tmin", media="-2")],
                                               {"AGC_001"}, "2025-10-31")), 2)

    def test_csv_y_json_estrictos(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "a.csv"
            for contenido in ["", "id,x\n", "id,id\na,b\n", "id,x\na,1,2\n", "id,x\na\n"]:
                p.write_text(contenido)
                with self.subTest(contenido=contenido), self.assertRaises(ValueError): leer_csv(p)
            q = Path(t) / "a.json"
            for contenido in ['{"a":1,"a":2}', '{"a":NaN}']:
                q.write_text(contenido)
                with self.assertRaises(ValueError): leer_json(q)


if __name__ == "__main__":
    unittest.main()
