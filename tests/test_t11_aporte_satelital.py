"""Pruebas de T11 con los datos del repositorio (revisión de Dani al PR #15).

Repite la comprobación de Dani: cambiar una etiqueta de validación interna no debe cambiar
nada de lo que se entrena en esa partición interna (residuos ni referencia de validación).
v2.1: los controles detienen el programa ante entradas incorrectas (revisión de Dani).
"""
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import t11_aporte_satelital as t11  # noqa: E402

HAY_DATOS = t11.TABLA.exists() and t11.PARTICIONES.exists()
PEQUENOS = {"Apan", "Tepeapulco", "Nanacamilpa de Mariano Arista", "Emiliano Zapata"}  # T03 §5


def entrenamientos(d, escenario, repeticion=None):
    """Entrenamientos externos de un escenario (todas las repeticiones o una)."""
    col = t11.ESCENARIOS[escenario]
    for rep, dr in d.groupby("repeticion"):
        if repeticion is not None and rep != repeticion:
            continue
        for k in sorted(dr[col].unique()):
            yield rep, k, dr[dr[col] != k]


@unittest.skipUnless(HAY_DATOS, "faltan registro/t07/tabla_comun.csv o registro/t03/particiones.csv")
class TestT11ConDatosReales(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = t11.preparar(pd.read_csv(t11.TABLA), pd.read_csv(t11.PARTICIONES))

    def test_control_v1_si_tenia_fuga(self):
        """Control: con el cálculo de v1 (residuos con todo el entrenamiento externo), cambiar una
        etiqueta de validación interna sí mueve residuos de entrenamiento. Si esto no fallara en v1,
        la prueba de abajo no demostraría nada."""
        _, _, tr = next(entrenamientos(self.d, "A", 1))
        a, b, _, _ = t11.particiones_internas(tr)[0]
        mod = tr.copy()
        mod.loc[b.index[0], "real"] += 1
        antes = pd.Series(t11.referencia_sin_la_fila(tr), index=tr.index).loc[a.index]
        despues = pd.Series(t11.referencia_sin_la_fila(mod), index=tr.index).loc[a.index]
        cambian = int((np.abs(antes - despues) > 1e-12).sum())
        print(f"\n  v1: cambiar una etiqueta de validación movía {cambian} residuos de entrenamiento")
        self.assertGreater(cambian, 0)

    def test_v2_etiquetas_de_validacion_no_cambian_lo_que_se_entrena(self):
        for esc in ["A", "B"]:
            for rep, k, tr in entrenamientos(self.d, esc, 1):
                for i, (a, b, residuo_a, ref_b) in enumerate(t11.particiones_internas(tr)):
                    mod = tr.copy()
                    mod.loc[b.index[0], "real"] += 1
                    _, _, residuo_a2, ref_b2 = t11.particiones_internas(mod)[i]
                    with self.subTest(escenario=esc, repeticion=rep, particion=k, interna=i):
                        np.testing.assert_allclose(residuo_a, residuo_a2)
                        np.testing.assert_allclose(ref_b, ref_b2)

    def test_estrato_otros_en_los_25_entrenamientos_de_A(self):
        for rep, k, tr in entrenamientos(self.d, "A"):
            estrato = t11.estrato_interno(tr)
            presentes = PEQUENOS & set(tr.municipio)
            with self.subTest(repeticion=rep, particion=k):
                self.assertTrue((estrato[tr.municipio.isin(presentes)] == "otros").all())
                self.assertTrue((estrato.value_counts() >= 1).all())
                self.assertFalse(set(estrato.unique()) & PEQUENOS)


    # ---------------------------------------------------------------- controles (v2.1)
    def test_detiene_parcela_repetida_en_una_repeticion(self):
        part = pd.read_csv(t11.PARTICIONES)
        dup = part[part.repeticion == 1].head(1).copy()
        dup["particion_principal"] = (dup.particion_principal + 1) % 5
        with self.assertRaises(ValueError):
            t11.preparar(pd.read_csv(t11.TABLA), pd.concat([part, dup], ignore_index=True))

    def test_detiene_parcela_en_entrenamiento_y_evaluacion(self):
        dr = self.d[self.d.repeticion == 1]
        dup = dr.head(1).copy()
        k = int(dup.particion_principal.iloc[0])
        dup["particion_principal"] = (k + 1) % 5
        with self.assertRaises(ValueError):
            t11.separar(pd.concat([dr, dup]), "particion_principal", k)

    def test_detiene_si_la_referencia_no_reproduce_t08(self):
        t08 = t11.referencia_oof(self.d).rename(columns={"ref": "prediccion", "fuente_t11": "fuente"})
        with tempfile.TemporaryDirectory() as tmp:
            ruta = Path(tmp) / "t08.csv"
            t08.to_csv(ruta, index=False)
            t11.comprobar_referencia(self.d, ruta)  # copia fiel: no se detiene
            t08.loc[0, "prediccion"] += 0.01
            t08.to_csv(ruta, index=False)
            with self.assertRaises(ValueError):
                t11.comprobar_referencia(self.d, ruta)


if __name__ == "__main__":
    unittest.main()