"""Pruebas del comparador de tablas (comparar_tablas_con_referencia.py).

Uso (con el mismo entorno, desde cualquier carpeta):
    python analisis/auditoria_catalogo_y_etiquetas/scripts/probar_comparar_tablas.py

No lee el dataset ni cambia nada del repositorio. Las pruebas de carpetas usan carpetas
temporales del sistema, que se borran al terminar. Varias pruebas comprueban que el
comparador SÍ falla cuando debe: un entero convertido en decimal, carpetas vacías o
inexistentes, una tabla sin esquema.
"""
import contextlib
import io
import shutil
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True

import comparar_tablas_con_referencia as comparador
from comparar_tablas_con_referencia import comparar_tablas, leer_esquema, leer_tabla, revisar_contra_esquema

CARPETA_REPO = comparador.CARPETA.parents[1]

ENCABEZADO = "tabla,columna,tipo,decimales,tolerancia,motivo\n"
ESQUEMA_TEXTO = ENCABEZADO + (
    "t.csv,id_parcela,texto,,,texto\n"
    "t.csv,municipio,texto,,,texto\n"
    "t.csv,puntos_contorno,entero,,,conteo\n"
    "t.csv,area_ha_geodesica,decimal,6,0.000001,valor calculado\n"
    "t.csv,rendimiento_t_ha,decimal,2,0,copiado del dataset original\n"
    "t.csv,distancia_m,decimal,1,0.1,valor calculado\n")
ESQUEMA = leer_esquema(ESQUEMA_TEXTO.encode("utf-8"))
BASE = ("id_parcela,municipio,puntos_contorno,area_ha_geodesica,rendimiento_t_ha,distancia_m\n"
        "AGC_001,Apan,5,12.345678,3.5,350.5\n"
        "AGC_002,Apan,7,3.100000,,\n")


def estado(nueva: str, referencia: str = BASE) -> str:
    return comparar_tablas(referencia.encode("utf-8"), nueva.encode("utf-8"), ESQUEMA["t.csv"])[0]


def falla_con_mensaje(funcion) -> bool:
    """Cierto si la función se detiene con un mensaje de error (y no con un código 0)."""
    try:
        funcion()
    except SystemExit as salida:
        return salida.code not in (0, None)
    return False


def correr(*argumentos) -> int:
    """Corre el comparador completo sin mostrar su salida. Devuelve su código de salida."""
    with contextlib.redirect_stdout(io.StringIO()):
        return comparador.main(list(argumentos))


def carpetas_de_prueba(base: Path, referencia: dict, nuevas: dict):
    """Crea el esquema y las carpetas ref/ y nuevas/ con los archivos indicados."""
    (base / "esquema.csv").write_text(ESQUEMA_TEXTO, encoding="utf-8")
    for nombre, tablas in (("ref", referencia), ("nuevas", nuevas)):
        (base / nombre).mkdir()
        for archivo, contenido in tablas.items():
            (base / nombre / archivo).write_text(contenido, encoding="utf-8")
    return ["--esquema", str(base / "esquema.csv"), "--referencia", str(base / "ref"), "--tablas", str(base / "nuevas")]


# --- Dos tablas iguales ---

def test_misma_tabla_es_igual():
    assert estado(BASE) == "igual"


def test_fin_de_linea_y_marca_inicial_no_cuentan():
    assert estado(BASE.replace("\n", "\r\n")) == "igual"
    assert estado("﻿" + BASE) == "igual"


# --- Decimales calculados: se tolera lo declarado y nada más ---

def test_la_tolerancia_declarada_se_acepta():
    assert estado(BASE.replace("12.345678", "12.345679")) == "tolerancia"
    assert estado(BASE.replace("350.5", "350.4")) == "tolerancia"


def test_mas_que_la_tolerancia_declarada_es_distinta():
    assert estado(BASE.replace("12.345678", "12.345680")) == "distinta"
    assert estado(BASE.replace("350.5", "350.3")) == "distinta"


def test_mas_decimales_que_los_declarados_es_distinta():
    assert estado(BASE.replace("12.345678", "12.3456781")) == "distinta"


# --- Enteros y texto: exactos (caso señalado en la revisión: 2 frente a 2.1) ---

def test_un_entero_convertido_en_decimal_es_distinta():
    assert estado(BASE.replace("AGC_001,Apan,5,", "AGC_001,Apan,5.1,")) == "distinta"
    assert estado(BASE.replace("AGC_001,Apan,5,", "AGC_001,Apan,5.01,")) == "distinta"
    assert estado(BASE.replace("AGC_001,Apan,5,", "AGC_001,Apan,5.0,")) == "distinta"


def test_un_entero_o_un_texto_que_cambia_es_distinta():
    assert estado(BASE.replace("AGC_001,Apan,5,", "AGC_001,Apan,6,")) == "distinta"
    assert estado(BASE.replace("AGC_002,Apan", "AGC_002,APAN")) == "distinta"
    assert estado(BASE.replace("AGC_001,Apan,5,", "AGC_001,Apan,cinco,")) == "distinta"


# --- Decimales copiados del original: exactos ---

def test_un_valor_copiado_del_original_no_tiene_tolerancia():
    assert estado(BASE.replace(",3.5,350.5", ",3.51,350.5")) == "distinta"
    assert estado(BASE.replace(",3.5,350.5", ",3.50,350.5")) == "distinta"


# --- Forma de la tabla ---

def test_un_valor_que_aparece_o_desaparece_es_distinta():
    assert estado(BASE.replace("3.100000,,\n", "3.100000,,10.0\n")) == "distinta"
    assert estado(BASE.replace("350.5", "")) == "distinta"


def test_columnas_o_filas_distintas():
    assert estado(BASE.replace("distancia_m", "distancia")) == "distinta"
    assert estado(BASE + "AGC_003,Apan,5,1.000000,3,1.0\n") == "distinta"
    filas = BASE.split("\n")
    assert estado("\n".join([filas[0], filas[2], filas[1], ""])) == "distinta"


# --- La referencia también debe cumplir el esquema ---

def test_una_referencia_fuera_del_esquema_se_avisa():
    referencia_mala = BASE.replace("AGC_001,Apan,5,", "AGC_001,Apan,5.5,")
    assert estado(BASE, referencia_mala) == "referencia"
    assert estado(referencia_mala, referencia_mala) == "referencia"      # aunque las dos tablas sean iguales


# --- El esquema mismo ---

def test_un_esquema_mal_escrito_se_rechaza():
    assert falla_con_mensaje(lambda: leer_esquema((ENCABEZADO + "t.csv,a,numero,,,x\n").encode()))
    assert falla_con_mensaje(lambda: leer_esquema((ENCABEZADO + "t.csv,a,decimal,2,,x\n").encode()))
    assert falla_con_mensaje(lambda: leer_esquema((ENCABEZADO + "t.csv,a,entero,,0.1,x\n").encode()))
    assert falla_con_mensaje(lambda: leer_esquema((ENCABEZADO + "t.csv,a,texto,,,x\nt.csv,a,texto,,,x\n").encode()))
    assert falla_con_mensaje(lambda: leer_esquema(ENCABEZADO.encode()))
    assert falla_con_mensaje(lambda: leer_esquema(b"tabla,columna,tipo\n"))


def test_el_esquema_del_repositorio_describe_las_tablas_guardadas():
    esquema = leer_esquema(comparador.ESQUEMA_POR_OMISION.read_bytes())
    tablas = sorted(comparador.TABLAS_POR_OMISION.glob("*.csv"))
    assert sorted(esquema) == [t.name for t in tablas], "el esquema y la carpeta tablas/ no listan las mismas tablas"
    for tabla in tablas:
        columnas, filas = leer_tabla(tabla.read_bytes())
        problemas = revisar_contra_esquema(columnas, filas, esquema[tabla.name])
        assert not problemas, f"{tabla.name}: {problemas[:3]}"


def test_la_referencia_de_git_se_lee_aunque_las_tablas_nuevas_esten_fuera_del_repositorio():
    # Caso real: generar las tablas en una carpeta temporal y compararlas con la versión guardada en Git.
    if not (CARPETA_REPO / ".git").exists():
        print("          (se omite: esta copia del repositorio no tiene .git)")
        return
    with tempfile.TemporaryDirectory() as d:
        copia = Path(d) / "tablas_nuevas"
        shutil.copytree(comparador.TABLAS_POR_OMISION, copia)
        correr("--tablas", str(copia))     # no debe detenerse por no encontrar Git; el código de salida depende del contenido


# --- El programa completo: códigos de salida ---

def test_dos_carpetas_con_tablas_iguales_terminan_bien():
    with tempfile.TemporaryDirectory() as d:
        assert correr(*carpetas_de_prueba(Path(d), {"t.csv": BASE}, {"t.csv": BASE})) == 0


def test_una_diferencia_real_termina_con_error():
    with tempfile.TemporaryDirectory() as d:
        nueva = BASE.replace("AGC_001,Apan,5,", "AGC_001,Apan,5.1,")
        assert correr(*carpetas_de_prueba(Path(d), {"t.csv": BASE}, {"t.csv": nueva})) == 1


def test_dos_carpetas_vacias_terminan_con_error():
    with tempfile.TemporaryDirectory() as d:
        argumentos = carpetas_de_prueba(Path(d), {}, {})
        assert falla_con_mensaje(lambda: correr(*argumentos))


def test_una_carpeta_vacia_termina_con_error():
    with tempfile.TemporaryDirectory() as d:
        argumentos = carpetas_de_prueba(Path(d), {"t.csv": BASE}, {})
        assert falla_con_mensaje(lambda: correr(*argumentos))
    with tempfile.TemporaryDirectory() as d:
        argumentos = carpetas_de_prueba(Path(d), {}, {"t.csv": BASE})
        assert falla_con_mensaje(lambda: correr(*argumentos))


def test_una_carpeta_que_no_existe_termina_con_error():
    with tempfile.TemporaryDirectory() as d:
        argumentos = carpetas_de_prueba(Path(d), {"t.csv": BASE}, {"t.csv": BASE})
        sin_tablas = [a.replace("nuevas", "no_existe") for a in argumentos]
        sin_referencia = [a.replace("ref", "no_existe") if a.endswith("ref") else a for a in argumentos]
        sin_esquema = [a.replace("esquema.csv", "no_existe.csv") for a in argumentos]
        assert falla_con_mensaje(lambda: correr(*sin_tablas))
        assert falla_con_mensaje(lambda: correr(*sin_referencia))
        assert falla_con_mensaje(lambda: correr(*sin_esquema))


def test_una_tabla_que_falta_o_sobra_termina_con_error():
    with tempfile.TemporaryDirectory() as d:        # hay tablas, pero no la que declara el esquema
        assert correr(*carpetas_de_prueba(Path(d), {"otra.csv": BASE}, {"otra.csv": BASE})) == 1
    with tempfile.TemporaryDirectory() as d:        # una tabla de más, sin esquema
        assert correr(*carpetas_de_prueba(Path(d), {"t.csv": BASE, "extra.csv": BASE}, {"t.csv": BASE, "extra.csv": BASE})) == 1


if __name__ == "__main__":
    pruebas = [(nombre, f) for nombre, f in sorted(globals().items()) if nombre.startswith("test_")]
    for nombre, prueba in pruebas:
        prueba()
        print(f"cumple  {nombre}")
    print(f"{len(pruebas)} de {len(pruebas)} pruebas cumplen")
