"""Integridad de entrega, semántica temporal y conciliación sin etiquetas."""
import copy
import csv
import json
from pathlib import Path
import tempfile
import unittest

from tests import test_extraer_clima as fixture_extractor
from scripts.t04_control import preparar_centroides
from scripts.t04_t02 import conciliar, area_t02, sha as sha_t02
from scripts.preparar_entrega_clima import (COLUMNAS, UNIDADES, posterior, validar_filas,
                                          verificar, guardar_json, sha, preparar)


class EntregaTests(unittest.TestCase):
    def filas(self):
        return [{"id_parcela": "A", "periodo": "2025-10", "variable": v, "unidad": UNIDADES[v],
                 "media_ponderada": "50.00000000000001", "estado": "cobertura_completa",
                 "cobertura_valida": "1.0", "valor_centroide": "40.0",
                 "diferencia_media_menos_centroide": "10.000000000000007",
                 "centroide_dentro_parcela": "False", "posterior_al_corte": "False"} for v in UNIDADES]

    def validar(self, filas):
        return validar_filas(filas, ["A"], ["2025-10"], "2025-10-31")

    def test_corte_es_observacion_y_respeta_fin_de_mes(self):
        self.assertFalse(posterior("2025-10", "2025-10-31"))
        self.assertTrue(posterior("2025-11", "2025-10-31"))
        self.assertTrue(posterior("2025-10", "2025-10-30"))
        self.assertTrue(posterior("2024-02", "2024-02-28"))
        self.assertFalse(posterior("2023-02", "2023-02-28"))

    def test_fecha_y_periodo_invalidos_se_rechazan(self):
        for p, corte in (("2025-13", "2025-10-31"), ("2025-1", "2025-10-31"), ("2025-10", "2025-02-30")):
            with self.subTest(p=p, corte=corte), self.assertRaises(ValueError):
                posterior(p, corte)

    def test_tabla_conserva_centroide_exterior_y_precision(self):
        control = self.validar(self.filas())
        self.assertEqual(control["filas_centroide_exterior"], 3)
        self.assertEqual(control["filas_posteriores_al_corte"], 0)

    def test_cero_lluvia_es_dato_no_ausencia(self):
        filas = self.filas(); filas[0].update(media_ponderada="0.0", valor_centroide="0.0", diferencia_media_menos_centroide="0.0")
        self.validar(filas)

    def test_ausencias_y_temperaturas_negativas_se_preservan(self):
        filas = self.filas()
        filas[0].update(media_ponderada="", estado="todo_nodata", cobertura_valida="0.0", diferencia_media_menos_centroide="")
        filas[1].update(media_ponderada="-4.0", valor_centroide="", diferencia_media_menos_centroide="")
        self.validar(filas)

    def test_claves_duplicadas_faltantes_y_ajenas(self):
        filas = self.filas()
        for f in (filas[:-1], filas+[filas[0]], [{**r, "id_parcela": "B"} for r in filas]):
            with self.subTest(f=f), self.assertRaisesRegex(ValueError, "Claves"):
                self.validar(f)

    def test_campos_semanticamente_incompatibles_no_se_publican(self):
        errores = {"unidad": "mm/dia", "estado": "inventado", "media_ponderada": "nan",
                   "cobertura_valida": "1.01", "valor_centroide": "-1",
                   "diferencia_media_menos_centroide": "0", "posterior_al_corte": "True",
                   "centroide_dentro_parcela": ""}
        for k, v in errores.items():
            filas = self.filas(); filas[0][k] = v
            with self.subTest(campo=k), self.assertRaises(ValueError):
                self.validar(filas)

    def test_ausencia_no_equivale_a_media_cero_o_diferencia_cero(self):
        for cambios in ({"estado": "todo_nodata"}, {"media_ponderada": ""},
                        {"valor_centroide": "", "diferencia_media_menos_centroide": "0"}):
            filas = self.filas(); filas[0].update(cambios)
            with self.subTest(cambios=cambios), self.assertRaises(ValueError):
                self.validar(filas)

    def entrega(self, carpeta):
        filas = self.filas()
        with (carpeta/"clima_parcela_mes.csv").open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=COLUMNAS); w.writeheader(); w.writerows(filas)
        guardar_json(carpeta/"controles.json", self.validar(filas))
        guardar_json(carpeta/"conciliacion_t02.json", {"estado": "conciliada_con_referencia_identificada", "ids_verificados": 1})
        guardar_json(carpeta/"procedencia.json", {"mapas": [{"variable": v, "periodo": "2025-10", "unidad": u, "cuadricula_id": "q"} for v, u in UNIDADES.items()],
                                               "soportes": [{"id_parcela": "A", "cuadricula_id": "q"}]})
        guardar_json(carpeta/"manifest.json", {"schema": "t04_entrega_compacta_v1", "ids": ["A"], "periodos": ["2025-10"],
            "corte_observacional_provisional": "2025-10-31", "archivos_sha256": {p: sha(carpeta/p) for p in ("clima_parcela_mes.csv", "controles.json", "conciliacion_t02.json", "procedencia.json")}})

    def test_verificar_no_necesita_datos_originales_ni_docker(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d); self.entrega(p)
            self.assertEqual(verificar(p)["resultado"], "aprobado")
            self.assertFalse(verificar(p)["disponibilidad_historica_certificada"])

    def test_archivo_cambiado_se_detecta_por_huella(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d); self.entrega(p)
            with (p/"clima_parcela_mes.csv").open("a") as f: f.write("\n")
            with self.assertRaisesRegex(ValueError, "Huella distinta"):
                verificar(p)

    def test_procedencia_incompleta_se_detecta_aun_con_huella_actualizada(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d); self.entrega(p)
            pro = json.loads((p/"procedencia.json").read_text()); pro["mapas"].pop()
            guardar_json(p/"procedencia.json", pro)
            m = json.loads((p/"manifest.json").read_text()); m["archivos_sha256"]["procedencia.json"] = sha(p/"procedencia.json")
            guardar_json(p/"manifest.json", m)
            with self.assertRaisesRegex(ValueError, "Procedencia de mapas"):
                verificar(p)

    def test_entrega_existente_no_se_sobrescribe(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(FileExistsError):
                preparar(Path(d)/"inexistente", Path(d), "2025-10-31")


class ConciliacionTests(unittest.TestCase):
    def setUp(self):
        fixture = fixture_extractor.ExtractorTests()
        self.parcelas = [fixture.parcela()]
        self.mapas = fixture.mapas()
        self.soportes = fixture.soportes(self.parcelas, self.mapas)
        self.centroides = preparar_centroides(self.parcelas, self.mapas)
        g = self.parcelas[0]["geometria"]
        self.manifest = {"catalogo": {"sha256": "cat"}, "geometrias": {"miembros": [{"archivo": "g.shp", "sha256": "geo"}]}}
        self.ref = {"schema": "t04_referencia_t02_v1", "revision": "revision_identificada", "ruta_en_repo": "t02", "archivos_sha256": {"tablas/catalogo_parcelas.csv": "huella"},
                    "entradas_sha256": {"ID_area_rendimiento_70_30_Reto_AgroCebada.csv": "cat", "g.shp": "geo"},
                    "parcelas": [{"id_parcela": "A", "area_ha_origen": "7.44", "area_ha_geodesica": str(round(area_t02(g)/10000, 6)),
                    "centroide_lon": str(round(g.centroid.x, 7)), "centroide_lat": str(round(g.centroid.y, 7)),
                    "celdas_clima_tocadas": "2", "celda_clima_principal": "0_0", "fraccion_en_celda_principal": "0.8"}]}

    def ejecutar(self, ref):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)/"referencia.json"; guardar_json(p, ref)
            return conciliar(self.parcelas, self.mapas, self.soportes, self.centroides, self.manifest, p, Path(d))

    def test_referencia_compatible_con_dos_metodos_no_modifica_soportes(self):
        anterior = json.dumps(list(self.soportes.values()), sort_keys=True)
        c = self.ejecutar(self.ref)
        self.assertEqual(c["estado"], "conciliada_con_referencia_identificada")
        self.assertEqual(c["ids_verificados"], 1)
        self.assertEqual(anterior, json.dumps(list(self.soportes.values()), sort_keys=True))

    def test_id_duplicado_y_diferente_se_rechazan(self):
        for filas in (self.ref["parcelas"]*2, [{**self.ref["parcelas"][0], "id_parcela": "B"}]):
            r = copy.deepcopy(self.ref); r["parcelas"] = filas
            with self.assertRaisesRegex(ValueError, "IDs"):
                self.ejecutar(r)

    def test_entradas_distintas_o_incompletas_no_se_concilian(self):
        for entradas in ({"g.shp": "geo"}, {**self.ref["entradas_sha256"], "g.shp": "alterado"}):
            r = copy.deepcopy(self.ref); r["entradas_sha256"] = entradas
            with self.assertRaisesRegex(ValueError, "Huellas"):
                self.ejecutar(r)

    def test_discrepancias_reales_detienen_con_id_y_campo(self):
        for campo, valor in (("area_ha_origen", "9"), ("centroide_lon", "-80"), ("area_ha_geodesica", "1"),
                             ("celdas_clima_tocadas", "1"), ("fraccion_en_celda_principal", ".7")):
            r = copy.deepcopy(self.ref); r["parcelas"][0][campo] = valor
            with self.subTest(campo=campo), self.assertRaisesRegex(ValueError, "T02 no se reproduce: A/"+campo):
                self.ejecutar(r)

    def test_area_cerca_del_limite_de_redondeo_y_fuera_del_intervalo(self):
        r = copy.deepcopy(self.ref)
        a = area_t02(self.parcelas[0]["geometria"])/10000
        r["parcelas"][0]["area_ha_geodesica"] = str(a + 0.5e-6 + a*0.5e-8)
        self.assertEqual(self.ejecutar(r)["estado"], "conciliada_con_referencia_identificada")
        r["parcelas"][0]["area_ha_geodesica"] = str(a + 0.5e-6 + a*2e-8)
        with self.assertRaisesRegex(ValueError, "A/area_ha_geodesica"):
            self.ejecutar(r)

    def test_celda_principal_distinta_no_se_oculta(self):
        r = copy.deepcopy(self.ref); r["parcelas"][0]["celda_clima_principal"] = "0_1"
        with self.assertRaisesRegex(ValueError, "Soporte T02/T04 incompatible"):
            self.ejecutar(r)

    def test_referencia_ausente_no_declara_conciliacion(self):
        with tempfile.TemporaryDirectory() as d:
            r = conciliar(self.parcelas, self.mapas, self.soportes, self.centroides, self.manifest, Path(d)/"ausente", Path(d))
            self.assertEqual(r["estado"], "no_disponible")

    def test_nueva_version_local_requiere_nueva_referencia(self):
        with tempfile.TemporaryDirectory() as d:
            b = Path(d); p = b/"referencia.json"; guardar_json(p, self.ref)
            tabla = b/"t02/tablas/catalogo_parcelas.csv"; tabla.parent.mkdir(parents=True); tabla.write_text("otra versión")
            with self.assertRaisesRegex(ValueError, "T02 local cambió"):
                conciliar(self.parcelas, self.mapas, self.soportes, self.centroides, self.manifest, p, b)


if __name__ == "__main__":
    unittest.main()
