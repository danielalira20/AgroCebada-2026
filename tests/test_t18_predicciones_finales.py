"""T18: la entrega de las 59 predicciones es correcta, completa y reproducible.

Bloque 1 (datos sintéticos): el procedimiento hace lo que dice y el script se detiene ante
errores (reservada con rendimiento, municipio sin etiquetas, diferencia con T08).
Bloque 2 (datos reales): el archivo entregado en registro/t18/ tiene el formato pedido,
coincide con el CSV oficial y con T08, y es el que se regenera hoy desde las entradas.
El bloque 2 se omite si no están los datos originales o aún no existe registro/t18/.
"""
import hashlib
import json
import statistics
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np
import pandas as pd

from scripts import t18_comparar_corridas as comparador
from scripts import t18_comparar_entregas as entregas
from scripts import t18_predicciones_finales as t18

RAIZ = Path(__file__).resolve().parent.parent
DATOS = RAIZ / "data" / "DATASET_RETO_AGRO_2026"
SALIDA = RAIZ / "registro" / "t18"
T08 = RAIZ / "registro" / "t03" / "predicciones_59_referencias.csv"


def sintetico(reservada_con_rendimiento=False, municipio_extra_reservado=False):
    """197 parcelas: 138 etiquetadas (A:68, B:69, C:1) y 59 reservadas (A:30, B:28, C:1)."""
    ids = [f"AGC_{i:03d}" for i in range(1, 198)]
    reservadas = set(ids[2::3][:t18.N_RESERVADAS])
    mun_etiquetadas = ["A"] * 68 + ["B"] * 69 + ["C"]
    mun_reservadas = ["A"] * 30 + ["B"] * 28 + ["C"]
    if municipio_extra_reservado:
        mun_reservadas[-1] = "D"  # municipio sin ninguna etiqueta
    it_e, it_r = iter(mun_etiquetadas), iter(mun_reservadas)
    filas, crudo = [], []
    for k, i in enumerate(ids):
        if i in reservadas:
            mun, real, conj = next(it_r), np.nan, "PREDICCION"
            if reservada_con_rendimiento and k == 2:
                real = 9.0
        else:
            mun, conj = next(it_e), "ENTRENAMIENTO"
            real = 1.0 + 0.5 * (k % 9) if mun != "C" else 5.0
        filas.append((i, conj, real, mun, "Cebada"))
        crudo.append((i, f"{1 + k % 7}.5", "" if np.isnan(real) else str(real), conj))
    d = pd.DataFrame(filas, columns=["ID_POLIGONO", "CONJUNTO", "real", "municipio", "grupo_registro"]).set_index("ID_POLIGONO")
    return d, pd.DataFrame(crudo, columns=t18.ENCABEZADO)


class SinteticosTests(unittest.TestCase):
    def correr(self, **kw):
        d, crudo = sintetico(**{k: v for k, v in kw.items() if k in ("reservada_con_rendimiento", "municipio_extra_reservado")})
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        esperado = {m: statistics.median(d[(d.CONJUNTO == "ENTRENAMIENTO") & (d.municipio == m)].real) for m in "ABC"}
        t08 = pd.DataFrame({"ID_POLIGONO": d.index[d.CONJUNTO == "PREDICCION"]})
        t08["candidato"] = t18.CANDIDATO
        t08["prediccion"] = d.loc[t08.ID_POLIGONO, "municipio"].map(esperado).values + kw.get("sesgo_t08", 0.0)
        ruta = Path(tmp.name) / "t08.csv"
        t08.to_csv(ruta, index=False)
        with mock.patch.object(t18, "cargar", return_value=d), mock.patch.object(t18, "leer_oficial_crudo", return_value=crudo):
            return d, esperado, t18.predecir(Path("no_se_usa"), ruta)

    def test_prediccion_es_la_mediana_municipal_de_las_etiquetadas(self):
        d, esperado, (filas, detalle, controles, n_mun) = self.correr()
        self.assertEqual(len(filas), 59)
        for fila in filas.itertuples():
            m = d.loc[fila.ID_POLIGONO, "municipio"]
            self.assertAlmostEqual(float(fila.RENDIMIENTO_T_HA), esperado[m], places=6)
        self.assertEqual(controles["respaldos_activados"], 0)
        self.assertEqual(dict(n_mun), {"A": 68, "B": 69, "C": 1})

    def test_una_sola_etiqueta_en_el_municipio_queda_advertida(self):
        _, _, (_, detalle, controles, _) = self.correr()
        marcadas = detalle[detalle.advertencia != ""]
        self.assertEqual(list(marcadas.municipio), ["C"])
        self.assertEqual(controles["parcelas_con_advertencia_una_sola_etiqueta"], list(marcadas.ID_POLIGONO))

    def test_el_archivo_conserva_orden_y_area_oficiales_y_solo_cambia_el_rendimiento(self):
        d, _, (filas, _, _, _) = self.correr()
        _, crudo = sintetico()
        oficial = crudo[crudo.CONJUNTO == "PREDICCION"]
        self.assertEqual(list(filas.ID_POLIGONO), list(oficial.ID_POLIGONO))
        self.assertEqual(list(filas.AREA_HA), list(oficial.AREA_HA))
        self.assertEqual(set(filas.CONJUNTO), {"PREDICCION"})

    def test_formato_de_bytes_bom_crlf_y_sin_coma_final(self):
        _, _, (filas, _, _, _) = self.correr()
        b = t18.bytes_csv(filas)
        self.assertTrue(b.startswith(b"\xef\xbb\xbf"))
        texto = b.decode("utf-8-sig")
        self.assertTrue(texto.endswith("\r\n"))
        lineas = texto.split("\r\n")[:-1]
        self.assertEqual(lineas[0], "ID_POLIGONO,AREA_HA,RENDIMIENTO_T_HA,CONJUNTO")
        self.assertEqual(len(lineas), 60)
        self.assertTrue(all(l.count(",") == 3 and not l.endswith(",") for l in lineas))
        self.assertNotIn("\n", texto.replace("\r\n", ""))

    def test_se_detiene_si_una_reservada_trae_rendimiento(self):
        with self.assertRaises(t18.ValidacionError):
            self.correr(reservada_con_rendimiento=True)

    def test_se_detiene_si_un_municipio_reservado_no_tiene_etiquetas(self):
        with self.assertRaises(t18.ValidacionError) as e:
            self.correr(municipio_extra_reservado=True)
        self.assertIn("sin etiquetas", str(e.exception))

    def test_se_detiene_si_las_predicciones_difieren_de_t08(self):
        with self.assertRaises(t18.ValidacionError) as e:
            self.correr(sesgo_t08=0.01)
        self.assertIn("T08", str(e.exception))


class ComparadorTests(unittest.TestCase):
    def corrida(self, raiz, nombre, csv=b"x", commit="c1", fecha="f1", python="3.12.15"):
        c = Path(raiz) / nombre
        c.mkdir()
        (c / "predicciones_finales.csv").write_bytes(csv)
        (c / "detalle_predicciones_59.csv").write_bytes(b"d")
        traza = {k: {} for k in comparador.DEBEN_SER_IGUALES}
        traza.update(git={"commit": commit}, generado_utc=fecha,
                     entorno={"python": python, "pandas": "3", "numpy": "2", "geopandas": "1", "arquitectura": "x86_64"})
        (c / "trazabilidad.json").write_text(json.dumps(traza), encoding="utf-8")
        return c

    def test_iguales_aunque_cambien_commit_y_fecha(self):
        with tempfile.TemporaryDirectory() as t:
            dif, info = comparador.comparar(self.corrida(t, "a"), self.corrida(t, "b", commit="c2", fecha="f2"))
        self.assertEqual(dif, [])
        self.assertEqual(len(info), 2)

    def test_detecta_un_byte_distinto_en_el_csv(self):
        with tempfile.TemporaryDirectory() as t:
            dif, _ = comparador.comparar(self.corrida(t, "a"), self.corrida(t, "b", csv=b"y"))
        self.assertTrue(any("predicciones_finales.csv" in d for d in dif))

    def test_detecta_otra_version_de_python(self):
        with tempfile.TemporaryDirectory() as t:
            dif, _ = comparador.comparar(self.corrida(t, "a"), self.corrida(t, "b", python="3.11.0"))
        self.assertTrue(any("entorno.python" in d for d in dif))


class CompararEntregasTests(unittest.TestCase):
    BASE = [("AGC_003", "18.68", "3.20"), ("AGC_011", "7.17", "4.52"), ("AGC_120", "7.47", "2.50")]

    def csv(self, filas=None, bom=True, eol="\r\n", dec2=True, coma_final=False, encabezado=None):
        filas = self.BASE if filas is None else filas
        enc = encabezado or "ID_POLIGONO,AREA_HA,RENDIMIENTO_T_HA,CONJUNTO"
        cola = "," if coma_final else ""
        lineas = [enc + cola] + [f"{i},{a},{r if dec2 else r.rstrip('0').rstrip('.')},PREDICCION{cola}" for i, a, r in filas]
        return (("\ufeff" if bom else "") + eol.join(lineas) + eol).encode("utf-8")

    def test_mismo_contenido_con_formato_distinto_coincide(self):
        dif, fmt, r = entregas.comparar(self.csv(), self.csv(bom=False, eol="\n", dec2=False))
        self.assertEqual(dif, [])
        self.assertGreaterEqual(len(fmt), 3)
        self.assertEqual(r["max_dif_rendimiento"], 0.0)

    def test_la_coma_final_se_detecta_como_formato_no_como_contenido(self):
        dif, fmt, _ = entregas.comparar(self.csv(), self.csv(coma_final=True))
        self.assertEqual(dif, [])
        self.assertTrue(any("coma final" in f for f in fmt))

    def test_detecta_un_valor_distinto_y_dice_cual(self):
        otro = [("AGC_003", "18.68", "3.21"), *self.BASE[1:]]
        dif, _, r = entregas.comparar(self.csv(), self.csv(otro), municipios={"AGC_003": "Singuilucan"})
        self.assertEqual(r["filas_con_rendimiento_distinto"], 1)
        self.assertTrue(any("AGC_003 (Singuilucan)" in d for d in dif))

    def test_detecta_id_faltante_y_numero_de_filas(self):
        dif, _, _ = entregas.comparar(self.csv(), self.csv(self.BASE[:2]))
        self.assertTrue(any("IDs solo en A" in d for d in dif))
        self.assertTrue(any("número de filas" in d for d in dif))

    def test_detecta_mismo_contenido_en_otro_orden(self):
        dif, _, _ = entregas.comparar(self.csv(), self.csv(list(reversed(self.BASE))))
        self.assertTrue(any("distinto orden" in d for d in dif))

    def test_detecta_encabezado_distinto_y_valor_no_numerico(self):
        dif, _, _ = entregas.comparar(self.csv(), self.csv(encabezado="ID_POLIGON,AREA_HA,RENDIMIENTO_T_HA,CONJUNTO"))
        self.assertTrue(any("encabezado distinto" in d for d in dif))
        malo = [("AGC_003", "18.68", "XX"), *self.BASE[1:]]
        dif, _, _ = entregas.comparar(self.csv(), self.csv(malo))
        self.assertTrue(any("no numérico" in d for d in dif))


@unittest.skipUnless((DATOS / t18.CSV_OFICIAL).exists() and (SALIDA / "predicciones_finales.csv").exists(),
                     "faltan los datos originales o registro/t18/")
class EntregaRealTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.oficial = t18.leer_oficial_crudo(DATOS)
        cls.reservadas = cls.oficial[cls.oficial.CONJUNTO == "PREDICCION"]
        cls.bytes = (SALIDA / "predicciones_finales.csv").read_bytes()
        cls.entrega = pd.read_csv(SALIDA / "predicciones_finales.csv", encoding="utf-8-sig", dtype=str)

    def test_formato_pedido_por_la_plantilla(self):
        self.assertTrue(self.bytes.startswith(b"\xef\xbb\xbf"))
        self.assertEqual(list(self.entrega.columns), ["ID_POLIGONO", "AREA_HA", "RENDIMIENTO_T_HA", "CONJUNTO"])
        self.assertEqual(len(self.entrega), 59)
        self.assertEqual(set(self.entrega.CONJUNTO), {"PREDICCION"})
        self.assertNotIn(b"\n", self.bytes.replace(b"\r\n", b""))

    def test_mismos_ids_orden_y_areas_que_el_csv_oficial(self):
        self.assertEqual(list(self.entrega.ID_POLIGONO), list(self.reservadas.ID_POLIGONO))
        self.assertEqual(list(self.entrega.AREA_HA), list(self.reservadas.AREA_HA))
        self.assertTrue(self.entrega.ID_POLIGONO.is_unique)

    def test_predicciones_finitas_positivas_y_con_dos_decimales(self):
        v = self.entrega.RENDIMIENTO_T_HA
        self.assertTrue(v.str.fullmatch(r"\d+\.\d{2}").all())
        x = v.astype(float)
        self.assertTrue(np.isfinite(x).all() and (x > 0).all())

    def test_coincide_con_las_predicciones_de_t08(self):
        t08 = pd.read_csv(T08)
        t08 = t08[t08.candidato == t18.CANDIDATO].set_index("ID_POLIGONO").prediccion
        mios = self.entrega.set_index("ID_POLIGONO").RENDIMIENTO_T_HA.astype(float)
        self.assertEqual(len(t08), 59)
        self.assertLess(float(np.max(np.abs(t08.reindex(mios.index) - mios))), 1e-9)

    def test_una_parcela_con_la_misma_mediana_que_su_municipio(self):
        detalle = pd.read_csv(SALIDA / "detalle_predicciones_59.csv", dtype=str, keep_default_na=False)
        self.assertEqual(set(detalle.fuente), {"municipio"})
        por_mun = detalle.groupby("municipio").prediccion.nunique()
        self.assertTrue((por_mun == 1).all(), "dos parcelas del mismo municipio deben recibir el mismo valor")
        self.assertEqual(list(detalle[detalle.advertencia != ""].ID_POLIGONO), ["AGC_120"])

    def test_el_archivo_entregado_es_el_que_se_regenera_hoy(self):
        _, filas_hoy = None, t18.predecir(DATOS, T08)[0]
        self.assertEqual(t18.bytes_csv(filas_hoy), self.bytes, "registro/t18 está desactualizado: vuelve a correr el script")

    def test_la_trazabilidad_coincide_con_los_archivos(self):
        traza = json.loads((SALIDA / "trazabilidad.json").read_text(encoding="utf-8"))
        self.assertEqual(traza["salidas_sha256"]["predicciones_finales.csv"], hashlib.sha256(self.bytes).hexdigest())
        self.assertEqual(traza["entradas_sha256"][t18.CSV_OFICIAL], t18.sha256(DATOS / t18.CSV_OFICIAL))
        self.assertEqual(traza["procedimiento"], t18.CANDIDATO)
        self.assertEqual(traza["controles"]["n_reservadas"], 59)
        self.assertEqual(traza["controles"]["respaldos_activados"], 0)


if __name__ == "__main__":
    unittest.main()
