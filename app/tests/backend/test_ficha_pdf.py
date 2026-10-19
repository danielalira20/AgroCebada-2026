"""Pruebas de la ficha PDF:  python tests/backend/test_ficha_pdf.py  (desde app/).
Deja las fichas de ejemplo en la carpeta que diga AGRO_FICHAS (si no, no guarda nada)."""
import os
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agrocebada_app.backend.datos import paquete  # noqa: E402
from agrocebada_app.backend.dominio.confianza import confianza_parcela  # noqa: E402
from agrocebada_app.backend.dominio.rangos import ANIO, rango_de  # noqa: E402
from agrocebada_app.backend.ficha_pdf.armado import armar_ficha, datos_ficha  # noqa: E402
from agrocebada_app.backend.ficha_pdf.ficha import PIE, figura_ficha  # noqa: E402
from agrocebada_app.config import MODELO_OFICIAL, MODELOS  # noqa: E402
from agrocebada_app.frontend.estado.contexto import calcular  # noqa: E402

paquete.exigir_datos()
d, S, C = paquete.parcelas(), paquete.series(), paquete.clima()
ctx = calcular(d, paquete.soporte(), S, C, MODELO_OFICIAL, False)
FICHA, cosecha = ctx.FICHA, d[d.CONJUNTO == "ENTRENAMIENTO"]


def primera(municipio, conjunto):
    return d.index[(d.municipio == municipio) & (d.CONJUNTO == conjunto)][0]


casos = {"AGC_011_chignahuapan": "AGC_011", "calpulalpan": primera("Calpulalpan", "PREDICCION"),
         "cuautepec_minimo_maximo": primera("Cuautepec de Hinojosa", "PREDICCION"),
         "AGC_120_nanacamilpa_sin_rango": "AGC_120", "con_cosecha": primera("Chignahuapan", "ENTRENAMIENTO")}
assert d.loc["AGC_011"].municipio == "Chignahuapan" and d.loc["AGC_120"].municipio.startswith("Nanacamilpa")
assert d.loc["AGC_011"].CONJUNTO == "PREDICCION" and d.loc["AGC_120"].CONJUNTO == "PREDICCION"


def textos(fig):
    return [t.get_text() for t in fig.texts]


def paginas(pdf):
    return len(re.findall(rb"/Type\s*/Page(?!s)", pdf))


confianza = {"nivel": "media", "motivo": "El municipio tiene pocas parcelas con cosecha registrada."}
calculadora = [("Hectáreas", "12.0 ha"), ("Producción estimada", "54.0 t"), ("Con un año bajo del municipio", "45.0 t")]
carpeta = Path(os.environ["AGRO_FICHAS"]) if os.environ.get("AGRO_FICHAS") else None
if carpeta:
    carpeta.mkdir(parents=True, exist_ok=True)

for nombre, pid in casos.items():
    info, pol, serie, clima, mascota = datos_ficha(pid, FICHA)
    muni = d.loc[pid].municipio
    # lo que se manda a dibujar: rango (de M02), modelo legible y sin "±"
    assert info["rango"] == rango_de(cosecha, muni)["texto"], pid
    assert info["modelo"] == MODELOS[MODELO_OFICIAL] and "__" not in info["modelo"], info["modelo"]
    assert "error" not in info and not any("±" in str(v) for v in info.values()), pid
    assert not any(x in str(info["nota"]) + info["rango"] for x in ("tu parcela dará", "de cada 10")), pid
    assert info["confianza"] is None and info["calculadora"] is None
    fig = figura_ficha(info, pol, serie, clima, mascota)
    t = textos(fig)
    assert not any("±" in x for x in t), pid
    assert any(x.startswith("Modelo: ") for x in t) and PIE in t, pid
    assert PIE == f"Estimación retrospectiva de la campaña {ANIO} · Orientativa, no es un dictamen"
    assert f"Generada el {date.today():%d/%m/%Y}" in " ".join(t), pid
    assert any("LO QUE DIERON LAS PARCELAS DE TU MUNICIPIO" in x for x in t)
    assert not any("Confianza" in x or "CALCULADORA" in x for x in t), pid          # sin hueco ni título vacío
    pdf = armar_ficha(pid, FICHA)
    assert pdf[:5] == b"%PDF-" and len(pdf) > 20000 and paginas(pdf) == 1, (pid, paginas(pdf))
    if carpeta:
        (carpeta / f"ficha_{nombre}.pdf").write_bytes(pdf)
    print(f"  {pid} ({muni}): una página · {info['rango']}")

# tipos de rango en las fichas
assert datos_ficha("AGC_120", FICHA)[0]["rango"].startswith("Nanacamilpa de Mariano Arista sólo tiene 1 parcela")
assert "entre 4.40 y 4.79" in datos_ficha(casos["cuautepec_minimo_maximo"], FICHA)[0]["rango"]

# los íconos de la ficha son los de formato.py (el backend no lo importa; aquí se comparan)
from agrocebada_app.backend.ficha_pdf.ficha import CONFIANZA  # noqa: E402
from agrocebada_app.frontend.componentes.validacion.formato import NIVELES  # noqa: E402
assert {k: v[0] for k, v in CONFIANZA.items()} == {k: v[0] for k, v in NIVELES.items()}

# con la confianza real de M01 (por parcela, con su fuente) y la calculadora (M05) también sale en una página,
# con palabra e ícono; una parcela con cosecha registrada no lleva confianza
for nombre, pid in casos.items():
    if d.loc[pid].CONJUNTO != "PREDICCION":
        continue
    conf_real = confianza_parcela(ctx.conf, d.loc[pid].municipio, ctx.pred.loc[pid, "fuente"])
    info, pol, serie, clima, mascota = datos_ficha(pid, FICHA, confianza=conf_real, calculadora=calculadora)
    t = textos(figura_ficha(info, pol, serie, clima, mascota))
    palabra = conf_real["nivel"]
    assert any(f"Confianza {palabra}" in x and CONFIANZA[palabra][0] in x for x in t), (pid, palabra)
    assert "CALCULADORA" in t and "54.0 t" in t, pid
    pdf = armar_ficha(pid, FICHA, confianza=conf_real, calculadora=calculadora)
    assert paginas(pdf) == 1 and pdf[:5] == b"%PDF-", pid
    if carpeta and nombre == "AGC_011_chignahuapan":
        (carpeta / "ficha_AGC_011_con_confianza_y_calculadora.pdf").write_bytes(pdf)
    if carpeta:
        (carpeta / f"ficha_{pid}_confianza_{palabra}.pdf").write_bytes(armar_ficha(pid, FICHA, confianza=conf_real))
assert confianza_parcela(ctx.conf, "Nanacamilpa de Mariano Arista", "municipio")["nivel"] == "baja"   # AGC_120
niveles = {confianza_parcela(ctx.conf, d.loc[i].municipio, ctx.pred.loc[i, "fuente"])["nivel"] for i in ctx.pred.index}
assert niveles == {"alta", "media", "baja"}
# cada modelo conserva su etiqueta y la cifra de su contexto
for modelo, cifra in [("media_mun__resp_grupo", 4.477323943661971), ("mediana_mun__resp_grupo", 4.52)]:
    otro = calcular(d, paquete.soporte(), S, C, modelo, False)
    info = datos_ficha("AGC_011", otro.FICHA, modelo=modelo)[0]
    assert info["modelo"] == MODELOS[modelo] and abs(info["valor"] - cifra) < 1e-9, (modelo, info)
print("OK")
