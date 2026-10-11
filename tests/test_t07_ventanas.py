import random
import unittest
from scripts.t07_ventanas import agregar, agregar_serie, VENTANAS
from tests.test_t07_fuentes import mes


def historia():
    rows = [mes(periodo=f"2025-{m:02d}", variable=v, media="10" if v != "Tmax" else "20")
            for m in range(1, 13) for v in ("PREC", "Tmin", "Tmax")]
    return {(r["id_parcela"], r["periodo"], r["variable"]): r for r in rows}


class Ventanas(unittest.TestCase):
    def test_calendario_y_cardinalidad(self):
        larga, ancha, calidad = agregar(historia(), ["AGC_001"])
        self.assertEqual([r["dias_esperados"] for r in larga], [214, 153])
        self.assertEqual([r["prec_acumulada_mm"] for r in larga], [70, 50])
        self.assertEqual(len(ancha), 1)
        self.assertEqual(len(ancha[0]), 7)
        self.assertEqual(len(calidad), 6)
        self.assertEqual([r["meses_esperados"] for r in calidad], [7, 7, 7, 5, 5, 5])

    def test_promedio_30_31_dias(self):
        i = historia(); i[("AGC_001", "2025-05", "Tmin")]["media_ponderada"] = "20"
        valor, c = agregar_serie(i, "AGC_001", ("2025-04", "2025-05"), "Tmin")
        self.assertAlmostEqual(valor, 920 / 61, places=12)
        self.assertEqual(c["dias_validos"], 61)
        self.assertNotEqual(valor, 15)

    def test_febrero_bisiesto(self):
        r = mes(periodo="2024-02", variable="Tmin")
        _, c = agregar_serie({("AGC_001", "2024-02", "Tmin"): r}, "AGC_001", ("2024-02",), "Tmin")
        self.assertEqual(c["dias_esperados"], 29)

    def test_mes_ausente_conserva_parcela_y_otras_variables(self):
        i = historia(); del i[("AGC_001", "2025-04", "PREC")]
        larga, ancha, c = agregar(i, ["AGC_001"])
        self.assertEqual(larga[0]["prec_acumulada_mm"], "")
        self.assertEqual(larga[1]["prec_acumulada_mm"], 50)
        self.assertEqual(larga[0]["tmin_media_c"], 10)
        self.assertEqual(c[0]["motivo"], "mes_ausente")
        self.assertEqual(c[0]["meses_validos"], 6)
        self.assertEqual(c[0]["dias_validos"], 184)
        self.assertEqual(c[0]["periodos_con_problema"], "2025-04")
        self.assertEqual(len(ancha), 1)

    def test_todo_nodata_y_sin_cobertura(self):
        for estado in ("todo_nodata", "sin_cobertura_espacial"):
            i = historia(); i[("AGC_001", "2025-06", "PREC")] = mes(periodo="2025-06", media="", estado=estado, cobertura="0")
            with self.subTest(estado=estado):
                a, _, c = agregar(i, ["AGC_001"])
                self.assertEqual([r["prec_acumulada_mm"] for r in a], ["", ""])
                self.assertEqual(c[0]["cobertura_minima"], 0)
                self.assertEqual(c[0]["motivo"], "mes_sin_media")

    def test_parcial_no_se_extrapola(self):
        i = historia(); i[("AGC_001", "2025-04", "PREC")] = mes(estado="cobertura_parcial", cobertura="0.8")
        a, _, c = agregar(i, ["AGC_001"])
        self.assertEqual(a[0]["prec_acumulada_mm"], "")
        self.assertEqual(c[0]["estado"], "cobertura_parcial")
        self.assertEqual(c[0]["meses_validos"], 7)

    def test_cero_real_valido(self):
        i = historia()
        for r in i.values():
            if r["variable"] == "PREC": r["media_ponderada"] = "0"
        a, _, c = agregar(i, ["AGC_001"])
        self.assertEqual(a[0]["prec_acumulada_mm"], 0)
        self.assertEqual(c[0]["estado"], "completa")

    def test_meses_fuera_ventana_no_afectan(self):
        i = historia(); esperado = agregar(i, ["AGC_001"])
        for r in i.values():
            if r["periodo"] not in VENTANAS["abr_oct"]: r["media_ponderada"] = "1000000"
        self.assertEqual(agregar(i, ["AGC_001"]), esperado)

    def test_desorden_y_etiqueta_no_afectan(self):
        i = historia(); esperado = agregar(i, ["AGC_001"])
        items = list(i.items()); random.Random(7).shuffle(items)
        for _, r in items: r["rendimiento_t_ha"] = "9999"
        self.assertEqual(agregar(dict(items), ["AGC_001"]), esperado)

    def test_ventana_vacia_duplicada_e_id_duplicado(self):
        for p in [(), ("2025-04", "2025-04")]:
            with self.assertRaises(ValueError): agregar_serie({}, "AGC_001", p, "PREC")
        with self.assertRaises(ValueError): agregar({}, ["AGC_001", "AGC_001"])

    def test_sin_meses_no_da_exito(self):
        a, _, c = agregar({}, ["AGC_001"])
        self.assertEqual(a[0]["prec_acumulada_mm"], "")
        self.assertEqual(c[0]["meses_presentes"], 0)
        self.assertEqual(c[0]["cobertura_minima"], "")
        self.assertEqual(c[0]["estado"], "incompleta")

    def test_centroide_misma_agregacion_y_bandera_exterior(self):
        i = historia()
        for r in i.values():
            r['valor_centroide'] = '5' if r['variable']=='PREC' else '2'
            r['centroide_dentro_parcela'] = 'False'
        _, _, q = agregar(i, ['AGC_001'], {'AGC_001': 3})
        self.assertEqual(q[0]['celdas_lluvia_tocadas_t02'], 3)
        self.assertEqual(q[0]['valor_centroide_ventana'], 35)
        self.assertEqual(q[0]['diferencia_media_menos_centroide'], 35)
        self.assertEqual(q[0]['centroide_dentro_parcela'], 'False')
        self.assertEqual(q[0]['estado_comparacion_centroide'], 'comparable')
        i['AGC_001','2025-05','Tmin']['valor_centroide'] = '12'
        _, c = agregar_serie(i, 'AGC_001', ('2025-04','2025-05'), 'Tmin')
        self.assertAlmostEqual(c['valor_centroide_ventana'], 432/61, places=12)
        self.assertAlmostEqual(c['diferencia_media_menos_centroide'], 10-432/61, places=12)

    def test_centroide_nodata_no_es_cero_ni_comparacion_parcial(self):
        i = historia()
        for r in i.values(): r['valor_centroide'] = '0'
        i['AGC_001','2025-04','PREC']['valor_centroide'] = ''
        _, c = agregar_serie(i, 'AGC_001', VENTANAS['abr_oct'], 'PREC')
        self.assertEqual(c['valor_centroide_ventana'], '')
        self.assertEqual(c['diferencia_media_menos_centroide'], '')
        self.assertEqual(c['meses_centroide_validos'], 6)
        self.assertEqual(c['dias_centroide_validos'], 184)
        self.assertEqual(c['periodos_sin_centroide'], '2025-04')
        self.assertEqual(c['estado_comparacion_centroide'], 'centroide_incompleto')
        _, c = agregar_serie(i, 'AGC_001', VENTANAS['jun_oct'], 'PREC')
        self.assertEqual(c['valor_centroide_ventana'], 0)
        self.assertEqual(c['diferencia_media_menos_centroide'], 50)

    def test_media_parcial_no_comparable_aun_con_centroide_completo(self):
        i = historia()
        for r in i.values(): r['valor_centroide'] = '5'
        i['AGC_001','2025-04','PREC']['estado'] = 'cobertura_parcial'
        valor,c = agregar_serie(i, 'AGC_001', VENTANAS['abr_oct'], 'PREC')
        self.assertEqual(valor, '')
        self.assertEqual(c['valor_centroide_ventana'], 35)
        self.assertEqual(c['diferencia_media_menos_centroide'], '')
        self.assertEqual(c['estado_comparacion_centroide'], 'ventana_no_completa')

    def test_bandera_centroide_inconsistente_y_soporte_ajeno_rechazados(self):
        i = historia(); i['AGC_001','2025-04','PREC']['centroide_dentro_parcela']='False'
        with self.assertRaisesRegex(ValueError, 'Bandera de centroide'):
            agregar_serie(i, 'AGC_001', VENTANAS['abr_oct'], 'PREC')
        with self.assertRaisesRegex(ValueError, 'IDs de soporte'):
            agregar(historia(), ['AGC_001'], {'OTRA': 1})

    def test_tmin_superior_tmax_rechazada(self):
        i = historia()
        for r in i.values():
            if r["variable"] == "Tmin": r["media_ponderada"] = "21"
        with self.assertRaisesRegex(ValueError, "Tmin supera"): agregar(i, ["AGC_001"])


if __name__ == "__main__": unittest.main()
