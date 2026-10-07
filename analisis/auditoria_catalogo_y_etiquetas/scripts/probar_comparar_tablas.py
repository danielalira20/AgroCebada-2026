"""Pruebas de la comparación de tablas con tolerancia (comparar_tablas_con_referencia.py).

Uso (con el mismo entorno, desde la carpeta de la auditoría):
    python scripts/probar_comparar_tablas.py

No lee el dataset ni escribe ningún archivo.
"""
import sys

sys.dont_write_bytecode = True

from comparar_tablas_con_referencia import comparar_tablas

BASE = "id_parcela,municipio,puntos_contorno,area_ha_geodesica,distancia_m\nAGC_001,Apan,5,12.345678,350.5\nAGC_002,Apan,7,3.100000,\n"


def estado(nueva: str, referencia: str = BASE) -> str:
    return comparar_tablas(referencia.encode("utf-8"), nueva.encode("utf-8"))[0]


def test_misma_tabla_es_igual():
    assert estado(BASE) == "igual"


def test_fin_de_linea_y_marca_inicial_no_cuentan():
    assert estado(BASE.replace("\n", "\r\n")) == "igual"
    assert estado("﻿" + BASE) == "igual"


def test_una_unidad_del_ultimo_decimal_se_tolera():
    assert estado(BASE.replace("12.345678", "12.345679")) == "tolerancia"
    assert estado(BASE.replace("350.5", "350.4")) == "tolerancia"


def test_mas_de_una_unidad_del_ultimo_decimal_es_distinta():
    assert estado(BASE.replace("12.345678", "12.345680")) == "distinta"
    assert estado(BASE.replace("350.5", "350.3")) == "distinta"


def test_enteros_y_texto_deben_coincidir_exactamente():
    assert estado(BASE.replace("AGC_001,Apan,5", "AGC_001,Apan,6")) == "distinta"
    assert estado(BASE.replace("AGC_002,Apan", "AGC_002,APAN")) == "distinta"


def test_un_valor_que_aparece_o_desaparece_es_distinta():
    assert estado(BASE.replace("3.100000,\n", "3.100000,10.0\n")) == "distinta"
    assert estado(BASE.replace("350.5", "")) == "distinta"


def test_columnas_o_filas_distintas():
    assert estado(BASE.replace("distancia_m", "distancia")) == "distinta"
    assert estado(BASE + "AGC_003,Apan,5,1.000000,1.0\n") == "distinta"
    filas = BASE.split("\n")
    assert estado("\n".join([filas[0], filas[2], filas[1], ""])) == "distinta"


if __name__ == "__main__":
    pruebas = [(nombre, f) for nombre, f in sorted(globals().items()) if nombre.startswith("test_")]
    for nombre, prueba in pruebas:
        prueba()
        print(f"cumple  {nombre}")
    print(f"{len(pruebas)} de {len(pruebas)} pruebas cumplen")
