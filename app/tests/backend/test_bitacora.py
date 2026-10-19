"""Pruebas de la bitácora de cosecha:  python tests/backend/test_bitacora.py  (desde app/)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd  # noqa: E402

from agrocebada_app.backend.dominio.bitacora import (  # noqa: E402
    AUDIO, COLUMNAS, EN_SESION, Dato, a_csv, agregar, desde_csv, faltan_para_subir, nueva_entrada,
    quitar, resumen, vacia)
from agrocebada_app.backend.dominio.confianza import MIN_ALTA, MIN_MEDIA  # noqa: E402

# --- una anotación: el productor dice toneladas; el rendimiento se deriva de su superficie
e = nueva_entrada(2025, 32.0, 7.17, estimacion_app=4.52, nota="Buen temporal")
assert e["anio"] == 2025 and e["toneladas"] == 32.0
assert e["rendimiento"] == round(32.0 / 7.17, 2) == 4.46
assert e["estimacion_app"] == 4.52 and e["diferencia"] == round(4.46 - 4.52, 2) == -0.06
assert e["nota"] == "Buen temporal"
# sin estimación previa (parcela sin cifra de la app) no se inventa una diferencia
assert nueva_entrada(2024, 30.0, 7.17)["diferencia"] is None

# --- lo que no se puede usar se rechaza con un motivo en su idioma, no con un error técnico
for args, pista in [((1800, 32.0, 7.17), "año"), (("x", 32.0, 7.17), "año"), ((2025, 0, 7.17), "mayores que cero"),
                    ((2025, 900.0, 7.17), "fuera de lo creíble"), ((2025, 0.01, 7.17), "fuera de lo creíble"),
                    ((2025, 32.0, 0), "superficie")]:
    try:
        nueva_entrada(*args)
        raise AssertionError(f"debió rechazar {args}")
    except Dato as ex:
        assert pista in str(ex).lower() or pista in str(ex), (args, str(ex))
# la nota se recorta, no rompe
assert len(nueva_entrada(2025, 32.0, 7.17, nota="x" * 500)["nota"]) == 140

# --- la libreta: ordenada por año, y anotar dos veces el mismo año corrige en vez de duplicar
lb = vacia()
assert list(lb.columns) == EN_SESION
for anio, t in [(2023, 28.0), (2025, 32.0), (2024, 30.0)]:
    lb = agregar(lb, nueva_entrada(anio, t, 7.17, estimacion_app=4.52))
assert lb.anio.tolist() == [2023, 2024, 2025]
lb = agregar(lb, nueva_entrada(2024, 31.0, 7.17, estimacion_app=4.52))      # corrige el dedazo
assert lb.anio.tolist() == [2023, 2024, 2025] and len(lb) == 3
assert float(lb[lb.anio == 2024].toneladas.iloc[0]) == 31.0
assert quitar(lb, 2023).anio.tolist() == [2024, 2025] and len(quitar(vacia(), 2023)) == 0

# --- la nota de voz viaja con su renglón, pero no en el archivo: un minuto de audio pesa más que toda la bitácora
voz = b"RIFF....da igual el contenido: aqui solo se comprueba que viaja con su anio"
con_voz = agregar(agregar(vacia(), nueva_entrada(2024, 30.0, 7.17)),
                  nueva_entrada(2025, 32.0, 7.17, nota="granizo en julio", audio=voz))
assert con_voz[con_voz.anio == 2025][AUDIO].iloc[0] == voz, "la grabación se queda con su año"
assert con_voz[con_voz.anio == 2024][AUDIO].iloc[0] is None, "el año sin grabación no hereda la de otro"
# anotar otro año no le quita la voz al anterior: era justo lo que se perdía cuando el audio vivía en la grabadora
con_voz = agregar(con_voz, nueva_entrada(2023, 28.0, 7.17))
assert con_voz[con_voz.anio == 2025][AUDIO].iloc[0] == voz
texto_csv = a_csv(con_voz, "P1", "M").decode("utf-8")
assert AUDIO not in texto_csv.splitlines()[0], "el audio no va al archivo"
assert "granizo en julio" in texto_csv, "lo escrito sí"
vuelta = desde_csv(a_csv(con_voz, "P1", "M"))
assert list(vuelta.columns) == EN_SESION and vuelta[AUDIO].isna().all(), "al volver del archivo no hay audio"
assert list(vuelta.nota) == ["", "", "granizo en julio"]

# --- el tablero
assert resumen(vacia()) is None
r = resumen(lb, valor_municipio=4.52)
assert r["anios"] == 3
assert r["mejor"]["anio"] == 2025 and r["peor"]["anio"] == 2023
assert abs(r["total_toneladas"] - (28.0 + 31.0 + 32.0)) < 1e-9
assert abs(r["promedio"] - lb.rendimiento.mean()) < 1e-9
assert r["error_app"] is not None and r["error_app"] >= 0
assert abs(r["vs_municipio"] - (lb.rendimiento.mean() - 4.52)) < 1e-9
assert abs(r["cambio"] - (lb.rendimiento.iloc[-1] - lb.rendimiento.iloc[0])) < 1e-9
assert resumen(agregar(vacia(), nueva_entrada(2025, 32.0, 7.17)))["cambio"] is None   # con un solo año no hay cambio

# --- cuántos vecinos faltan para subir de nivel (la regla de M01 leída hacia adelante)
f1 = faltan_para_subir(1)
assert (f1["faltan"], f1["nivel"], f1["siguiente"]) == (MIN_MEDIA - 1, "baja", "media") and not f1["condicionado"]
f5 = faltan_para_subir(5)
assert (f5["faltan"], f5["siguiente"]) == (MIN_ALTA - 5, "alta") and f5["condicionado"]   # llegar a 10 no la garantiza
assert faltan_para_subir(MIN_ALTA)["faltan"] == 0 and faltan_para_subir(71)["siguiente"] is None
assert faltan_para_subir(MIN_MEDIA)["siguiente"] == "alta"

# --- se descarga y se vuelve a abrir sin perder nada
ida = a_csv(lb, parcela="AGC_011", municipio="Chignahuapan")
vuelta = desde_csv(ida)
assert vuelta.anio.tolist() == lb.anio.tolist()
assert vuelta.rendimiento.tolist() == lb.rendimiento.tolist()
assert "AGC_011" in ida.decode() and "Chignahuapan" in ida.decode()

# --- un archivo que no es una bitácora, o con renglones rotos, no pasa
for malo, pista in [(b"hola mundo", "faltan columnas"), (b"", "no pude leer"),
                    ("anio,toneladas,rendimiento\n1800,5,0.5\n".encode(), "ninguna cosecha"),
                    ("anio,toneladas,rendimiento\n2025,-3,99\n".encode(), "ninguna cosecha")]:
    try:
        desde_csv(malo)
        raise AssertionError(f"debió rechazar: {malo[:30]}")
    except Dato as ex:
        assert pista in str(ex).lower(), (malo[:30], str(ex))
# renglones rotos mezclados con buenos: se queda con los buenos
mixto = "anio,toneladas,rendimiento\n2025,32,4.46\n1800,5,0.5\n2024,31,4.32\n".encode()
assert desde_csv(mixto).anio.tolist() == [2024, 2025]
# el mismo año repetido en el archivo se queda con el último
rep = "anio,toneladas,rendimiento\n2025,32,4.46\n2025,30,4.18\n".encode()
assert desde_csv(rep).rendimiento.tolist() == [4.18]
print("OK")
