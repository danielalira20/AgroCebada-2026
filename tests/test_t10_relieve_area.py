"""T10: pruebas sintéticas (docs/T10_relieve_area.md, D_T10_001).

Con datos inventados se comprueba que todo lo aprendido sale sólo del entrenamiento,
que la opción «referencia sola» existe y gana los empates, y que la salida tiene el
formato de T03 §7. No usan el dataset ni corren configuraciones con datos reales.
"""
import unittest

import numpy as np
import pandas as pd

from scripts.t10_relieve_area import (
    ALFAS, AREA, CONFIGS, ELEV, PEND, PROCEDIMIENTOS, REFERENCIA_SOLA, decidir, desempatar, elegir_opcion,
    estrato_interno, evaluar, marcar_candidatas, particiones_internas, referencia_municipal,
    referencia_sin_la_fila, revolver_dentro_de_municipio, transformar,
)


def datos(n_por_mun=(12, 10, 8, 1), semilla=0, señal=0.0):
    """Parcelas sintéticas: municipios de distinto tamaño, dos grupos y variables de T10."""
    rng = np.random.RandomState(semilla)
    filas = []
    for i, n in enumerate(n_por_mun):
        for j in range(n):
            elev = 2600 + 50 * i + rng.normal(0, 20)
            filas.append(dict(ID_POLIGONO=f"P{i}_{j}", municipio=f"M{i}", grupo_registro="G1" if i % 2 else "G2",
                              **{ELEV: elev, PEND: abs(rng.normal(2, 1)), AREA: rng.normal(1.5, 0.6)}))
    d = pd.DataFrame(filas)
    d["real"] = 3 + 0.3 * d.municipio.str[1].astype(int) + señal * (d[ELEV] - 2600) / 50 + rng.normal(0, 0.2, len(d))
    return d


def referencia_sin_la_fila_lenta(tr):
    """Versión directa (como T11): quitar la fila y aplicar la referencia municipal."""
    out = np.empty(len(tr))
    for i in range(len(tr)):
        resto = tr.drop(index=tr.index[i])
        out[i] = referencia_municipal(resto, tr.iloc[[i]])[0][0]
    return out


class Referencia(unittest.TestCase):
    def test_sin_la_fila_igual_a_la_version_directa(self):
        tr = datos()
        np.testing.assert_allclose(referencia_sin_la_fila(tr), referencia_sin_la_fila_lenta(tr), rtol=0, atol=1e-12)

    def test_cascada_municipio_grupo_global(self):
        tr = datos((5, 5))
        te = pd.DataFrame(dict(municipio=["M0", "M9", "M9"], grupo_registro=["G2", "G1", "G7"]))
        ref, fuente = referencia_municipal(tr, te)
        self.assertEqual(list(fuente), ["municipio", "grupo", "global"])
        self.assertAlmostEqual(ref[0], tr[tr.municipio == "M0"].real.mean())
        self.assertAlmostEqual(ref[1], tr[tr.grupo_registro == "G1"].real.mean())
        self.assertAlmostEqual(ref[2], tr.real.mean())


class Transformacion(unittest.TestCase):
    def test_relleno_con_mediana_del_entrenamiento(self):
        d = datos()
        tr, te = d.iloc[:20].copy(), d.iloc[20:].copy()
        te.loc[te.index[0], PEND] = np.nan
        tr.loc[tr.index[0], PEND] = np.nan
        _, xte = transformar(tr, te, [PEND], False)
        mediana = tr[PEND].median()
        esperado = (mediana - tr[PEND].fillna(mediana).mean()) / tr[PEND].fillna(mediana).std(ddof=0)
        self.assertAlmostEqual(xte[0, 0], esperado)

    def test_la_evaluacion_no_cambia_lo_aprendido(self):
        d = datos()
        tr, te = d.iloc[:20], d.iloc[20:].copy()
        xtr1, _ = transformar(tr, te, [ELEV, PEND, AREA], True)
        te[[ELEV, PEND, AREA]] = 999.0
        xtr2, _ = transformar(tr, te, [ELEV, PEND, AREA], True)
        np.testing.assert_array_equal(xtr1, xtr2)

    def test_centrado_con_medias_del_entrenamiento_y_global_si_falta(self):
        d = datos((6, 6))
        tr, te = d.iloc[:10], d.iloc[10:].copy()
        te.loc[te.index[-1], "municipio"] = "M_nuevo"
        xtr, xte = transformar(tr, te, [ELEV], True)
        cent = tr[ELEV] - tr.groupby("municipio")[ELEV].transform("mean")
        mu, sd = cent.mean(), cent.std(ddof=0)
        esperado_m1 = (te[ELEV].iloc[0] - tr[tr.municipio == "M1"][ELEV].mean() - mu) / sd
        esperado_nuevo = (te[ELEV].iloc[-1] - tr[ELEV].mean() - mu) / sd
        self.assertAlmostEqual(xte[0, 0], esperado_m1)
        self.assertAlmostEqual(xte[-1, 0], esperado_nuevo)


class SeleccionInterna(unittest.TestCase):
    def test_estrato_otros(self):
        tr = datos((12, 3, 1))
        self.assertEqual(set(estrato_interno(tr)), {"M0", "otros"})

    def test_la_validacion_interna_no_entra_a_su_referencia(self):
        tr = datos()
        antes = particiones_internas(tr)
        _, b0, _, _ = antes[0]
        tr2 = tr.copy()
        tr2.loc[b0.index, "real"] = 100.0
        despues = particiones_internas(tr2)
        for (a, b, res_a, ref_b), (_, _, res_a2, ref_b2) in zip(antes, despues):
            if set(b.index) == set(b0.index):
                np.testing.assert_array_equal(ref_b, ref_b2)
                np.testing.assert_array_equal(res_a, res_a2)

    def test_empate_gana_lo_mas_simple(self):
        opciones = [REFERENCIA_SOLA] + ALFAS
        self.assertIs(desempatar([1.0] * len(opciones), opciones), REFERENCIA_SOLA)
        errores = [2.0, 1.0, 1.0] + [3.0] * (len(ALFAS) - 2)
        self.assertEqual(desempatar(errores, opciones), ALFAS[1])
        self.assertEqual(desempatar([1.0] * len(ALFAS), list(ALFAS)), max(ALFAS))

    def test_procedimientos(self):
        self.assertIn(REFERENCIA_SOLA, PROCEDIMIENTOS["t10"]["opciones"])
        self.assertNotIn(REFERENCIA_SOLA, PROCEDIMIENTOS["puente_t11"]["opciones"])
        self.assertTrue(PROCEDIMIENTOS["t10"]["decide"])
        self.assertFalse(PROCEDIMIENTOS["puente_t11"]["decide"])
        self.assertEqual(len(CONFIGS), 6)

    def test_con_senal_fuerte_no_elige_referencia_sola(self):
        tr = datos((20, 20, 20), señal=1.0)
        op = elegir_opcion(particiones_internas(tr), CONFIGS[1], "t10")
        self.assertIsNot(op, REFERENCIA_SOLA)

    def test_sin_senal_con_variable_constante_elige_referencia_sola(self):
        tr = datos((20, 20, 20))
        tr[ELEV] = 2600.0
        op = elegir_opcion(particiones_internas(tr), CONFIGS[1], "t10")
        self.assertIs(op, REFERENCIA_SOLA)


class Salida(unittest.TestCase):
    def setUp(self):
        d = datos((14, 12, 10))
        reps = []
        rng = np.random.RandomState(1)
        for rep in (1, 2):
            x = d.copy()
            x["repeticion"] = rep
            x["particion_principal"] = rng.permutation(np.arange(len(x)) % 3)
            x["particion_espacial"] = x.municipio.map({"M0": 0, "M1": 1, "M2": 2})
            reps.append(x)
        self.d = pd.concat(reps, ignore_index=True)

    def test_formato_y_cada_parcela_una_vez_por_repeticion(self):
        cfg = {1: CONFIGS[1], 6: CONFIGS[6]}
        oof, _ = evaluar(self.d, configs=cfg, verbose=False)
        for c in ["ID_POLIGONO", "repeticion", "particion", "escenario", "real", "prediccion", "candidato",
                  "version", "fuente", "procedimiento"]:
            self.assertIn(c, oof.columns)
        n = oof.groupby(["escenario", "procedimiento", "config", "repeticion", "ID_POLIGONO"]).size()
        self.assertTrue((n == 1).all())
        self.assertEqual(len(oof), 2 * 2 * len(self.d) // 2 * 5)
        self.assertTrue(np.isfinite(oof.prediccion).all())
        ref = oof[oof.procedimiento == "referencia"]
        sola = oof[oof.opcion == "referencia_sola"]
        if len(sola):
            m = sola.merge(ref, on=["escenario", "repeticion", "ID_POLIGONO"], suffixes=("", "_r"))
            np.testing.assert_allclose(m.prediccion, m.prediccion_r)

    def test_revuelto_conserva_valores_dentro_de_cada_municipio(self):
        x = revolver_dentro_de_municipio(self.d, [ELEV, PEND], np.random.RandomState(0))
        for m, g in self.d.drop_duplicates("ID_POLIGONO").groupby("municipio"):
            g2 = x.drop_duplicates("ID_POLIGONO")
            g2 = g2[g2.municipio == m]
            self.assertEqual(sorted(g[ELEV]), sorted(g2[ELEV]))
        a = x.drop_duplicates("ID_POLIGONO").set_index("ID_POLIGONO")
        b = x[x.repeticion == 2].set_index("ID_POLIGONO")
        np.testing.assert_array_equal(a[ELEV].reindex(b.index), b[ELEV])


def comparacion(escenario="A", subconjunto="sin_respaldo", cumple=True, elegible=True, candidato=5):
    """Una fila mínima de comparacion_emparejada para probar la decisión."""
    return dict(escenario=escenario, subconjunto=subconjunto, cumple_regla_T03=cumple, elegible=elegible,
                candidato=candidato, procedimiento="t10" if elegible else "puente_t11",
                tipo="frente_a_referencia", dMAE=-0.02)


def revuelto(filas):
    return pd.DataFrame(filas, columns=["escenario", "config", "dMAE_observado", "revueltos",
                                        "fraccion_igual_o_mejor", "dMAE_revueltos", "se_sostiene"])


class Decision(unittest.TestCase):
    """D_T10_001 §7–8: sólo A promueve, y sólo si además supera el control de revuelto."""

    def test_ganar_solo_en_b_no_promueve(self):
        comp = marcar_candidatas(pd.DataFrame([comparacion("A", cumple=False), comparacion("B", cumple=True)]))
        self.assertEqual(list(comp.candidata_a_promover), [False, False])
        d = decidir(comp, revuelto([]))
        self.assertFalse(d.promueve.any())
        self.assertIn("sólo en B", d.motivo.iloc[1])

    def test_el_revuelto_frena_la_promocion(self):
        comp = marcar_candidatas(pd.DataFrame([comparacion("A")]))
        self.assertTrue(comp.candidata_a_promover.iloc[0])
        no = decidir(comp, revuelto([dict(escenario="A", config=5, dMAE_observado=-0.02, revueltos=20,
                                          fraccion_igual_o_mejor=0.5, dMAE_revueltos="", se_sostiene=False)]))
        self.assertFalse(no.promueve.iloc[0])
        self.assertFalse(bool(no.supera_revuelto.iloc[0]))
        self.assertIn("no supera", no.motivo.iloc[0])
        si = decidir(comp, revuelto([dict(escenario="A", config=5, dMAE_observado=-0.02, revueltos=20,
                                          fraccion_igual_o_mejor=0.0, dMAE_revueltos="", se_sostiene=True)]))
        self.assertTrue(si.promueve.iloc[0])
        self.assertIn("supera el control", si.motivo.iloc[0])

    def test_sin_control_de_revuelto_no_promueve(self):
        d = decidir(marcar_candidatas(pd.DataFrame([comparacion("A")])), revuelto([]))
        self.assertFalse(d.promueve.iloc[0])

    def test_puente_y_subconjunto_todas_nunca_promueven(self):
        comp = marcar_candidatas(pd.DataFrame([comparacion("A", elegible=False),
                                               comparacion("A", subconjunto="todas")]))
        self.assertFalse(comp.candidata_a_promover.any())
        d = decidir(comp, revuelto([dict(escenario="A", config=5, dMAE_observado=-0.02, revueltos=20,
                                         fraccion_igual_o_mejor=0.0, dMAE_revueltos="", se_sostiene=True)]))
        self.assertFalse(d.promueve.any())
        self.assertIn("no elegible", d.motivo.iloc[0])
        self.assertIn("informativo", d.motivo.iloc[1])


if __name__ == "__main__":
    unittest.main()
