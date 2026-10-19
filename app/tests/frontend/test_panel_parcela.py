"""Prueba del panel «Tu parcela» (M04) sin navegador:  python tests/frontend/test_panel_parcela.py  (desde app/)."""
import sys
from pathlib import Path

APP = Path(__file__).resolve().parents[2]       # app/
sys.path.insert(0, str(APP))

from streamlit.testing.v1 import AppTest

from agrocebada_app.backend.datos import paquete

paquete.exigir_datos()

MEDIA, MEDIANA = "media_mun__resp_grupo", "mediana_mun__resp_grupo"
CON_ESTIMACION = {"Almoloya", "Calpulalpan", "Chignahuapan", "Cuautepec de Hinojosa", "Nanacamilpa de Mariano Arista",
                  "Singuilucan"}                # los otros 3 municipios sólo tienen parcelas con cosecha registrada
# el productor siempre ve el modelo oficial (la mediana), aunque la sesión traiga otro; la base con la media (3.96 + 0.52 =
# 4.48) se prueba en tests/backend/test_desglose.py
# la ecuación del panel: Región 4.34 + Tu municipio 0.18 = Estimación 4.52
CHIGNAHUAPAN = ("4.34", "0.18", "4.52")


def nueva(modelo, **estado):
    at = AppTest.from_file(str(APP / "app.py"), default_timeout=300)
    at.session_state["modelo"] = modelo
    for k, v in estado.items():
        at.session_state[k] = v
    return at.run()


def panel(at):
    """El HTML de la cifra del panel (el bloque que trae la cifra grande)."""
    x = [m.value for m in at.markdown if "class='big'" in m.value]
    assert x, "el panel no muestra la cifra"
    return x[0]


def desglose(p):
    """Lo del panel que no depende de la parcela: de la ecuación al plegable (sin la producción)."""
    return p[p.index("class='fila eq'"):p.index("<details")]


for modelo in (MEDIA, MEDIANA):
    valor, dif, est = CHIGNAHUAPAN
    at = nueva(modelo)
    assert not at.exception, (modelo, at.exception)
    munis = next(x for x in at.selectbox if x.label == "Municipio").options
    assert len(munis) == 9
    for m in munis:
        at = nueva(modelo, agri_muni=m)
        assert not at.exception, (modelo, m, at.exception)
        p = panel(at)
        assert "Error típico" not in p and "± " not in p and "tu parcela dará" not in p.lower(), (m, p)
        if m in CON_ESTIMACION:
            assert "Rendimiento estimado" in p and "<span>Tu municipio</span>" in p, (modelo, m)
            assert "Confianza</span><b>" in p and "Confianza " in desglose(p), (modelo, m)
            assert "Lo que el método no ve: fecha de siembra, variedad y manejo." in p, (modelo, m)
            assert "no entran al cálculo" in p and "Cómo leer esta estimación" in p, (modelo, m)
            assert "dieron" in p or "no alcanza para dar un rango" in p, (modelo, m)    # el rango del municipio (M02)
            assert "<details class='mas'><summary>Cómo leer esta estimación</summary>" in p, (modelo, m)
            assert "Se parte de la mediana de la región" in p, (modelo, m)              # el desglose en una frase, plegado
            if m == "Nanacamilpa de Mariano Arista":                                   # una sola parcela: confianza baja, resta
                assert "⚠ Baja" in p and "class='op'>−<" in p and "<span>Tu municipio</span><b>1.84</b>" in p, p
        else:
            assert "Rendimiento registrado" in p and "Tu municipio" not in p, (modelo, m)
    # Chignahuapan con la base del modelo: base + diferencia = estimación
    at = nueva(modelo, agri_muni="Chignahuapan", agri_parcela="AGC_011")
    p = panel(at)
    for t in (f"<span>Región</span><b>{valor}</b>", f"<span>Tu municipio</span><b>{dif}</b>",
              f"<span>Estimación</span><b>{est}</b>", "class='op'>+<", f"class='big'>{est}<", "Confianza</span><b>▲ Media"):
        assert t in p, (modelo, t, p)
    # AGC_011 y AGC_036 dan lo mismo: la estimación sólo mira el municipio, no el área ni el entorno
    otra = panel(nueva(modelo, agri_muni="Chignahuapan", agri_parcela="AGC_036"))
    assert f"class='big'>{est}<" in otra and desglose(p) == desglose(otra), modelo
    print(f"panel ({modelo}): {len(CON_ESTIMACION)} municipios con desglose, 3 con cosecha registrada · "
          f"Chignahuapan {valor} {dif} = {est}")
print("OK")
