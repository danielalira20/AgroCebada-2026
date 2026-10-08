"""Pruebas del comparador de tablas (comparar_tablas_con_referencia.py).

Uso (con el mismo entorno, desde cualquier carpeta):
    python analisis/auditoria_catalogo_y_etiquetas/scripts/probar_comparar_tablas.py

No lee el dataset ni cambia nada del repositorio. Las pruebas de carpetas usan carpetas
temporales del sistema, que se borran al terminar. Varias pruebas comprueban que el
comparador SÍ falla cuando debe: un entero convertido en decimal, carpetas vacías o
inexistentes, una tabla sin esquema.
"""
import contextlib
import csv
import io
import random
import shutil
import sys
import tempfile
from decimal import Decimal
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


def ejecutar(*argumentos):
    """Corre el comparador completo y devuelve (código de salida, texto que imprimió)."""
    salida = io.StringIO()
    with contextlib.redirect_stdout(salida):
        codigo = comparador.main(list(argumentos))
    return codigo, salida.getvalue()


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
    for tolerancia in ("NaN", "sNaN", "Infinity", "-1", "abc", ""):
        assert falla_con_mensaje(lambda: leer_esquema((ENCABEZADO + f"t.csv,a,decimal,2,{tolerancia},x\n").encode("utf-8"))), tolerancia
    assert falla_con_mensaje(lambda: leer_esquema((ENCABEZADO + "t.csv,a,decimal,2.5,0,x\n").encode("utf-8")))


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


# --- Notación científica, ceros y formato ---

def test_la_notacion_cientifica_se_acepta_si_cabe_en_los_decimales():
    # pandas escribe 1e-05 en lugar de 0.00001: es el mismo número y no debe dar un falso «distinta»
    de = lambda valor: BASE.replace("12.345678", valor)
    assert estado(de("1e-05"), referencia=de("0.00001")) == "tolerancia"   # mismo valor, otra escritura
    assert estado(de("0.00001"), referencia=de("1e-05")) == "tolerancia"
    for escrito in ("1e-3", "1E-3", "1e-06", "1.5e1", "-1e-3"):
        assert estado(de(escrito), referencia=de(escrito)) == "igual", escrito
    assert estado(de("1e-07")) == "distinta"                                # 7 decimales: más de los 6 declarados
    assert estado(de("3e-06"), referencia=de("1e-06")) == "distinta"        # 2 unidades de diferencia


def test_la_notacion_cientifica_no_vale_en_enteros_y_no_oculta_cambios_en_valores_copiados():
    assert estado(BASE.replace(",5,", ",5e0,")) == "distinta"      # un entero no se escribe así
    assert estado(BASE.replace("3.5,", "3.5e0,")) == "distinta"    # valor copiado (tolerancia 0): el texto cambió


def test_lo_que_no_es_un_numero_normal_se_rechaza():
    for raro in ("nan", "NaN", "inf", "-inf", "Infinity", "+1.0", ".5", "5.", " 1", "1 ", "1,5", "1e", "1e+", "e5",
                 "1e999", "1e-999", "0x10", "\u0661\u0662\u0663", "1_000", "--1", "1.2.3"):
        columnas, filas = leer_tabla(BASE.replace("12.345678", raro).encode("utf-8"))
        assert revisar_contra_esquema(columnas, filas, ESQUEMA["t.csv"]), f"se aceptó «{raro}»"
    # y los dígitos de otros alfabetos tampoco valen como enteros
    columnas, filas = leer_tabla(BASE.replace(",5,", ",\u0665,").encode("utf-8"))
    assert revisar_contra_esquema(columnas, filas, ESQUEMA["t.csv"])


def test_cero_y_cero_negativo():
    assert estado(BASE.replace("350.5", "0.0"), referencia=BASE.replace("350.5", "-0.0")) == "tolerancia"   # tolerancia > 0
    assert estado(BASE.replace("3.5,", "0.0,"), referencia=BASE.replace("3.5,", "-0.0,")) == "distinta"     # tolerancia 0: el texto cambió


def test_en_un_valor_copiado_3_5_y_3_50_son_distintos():
    assert estado(BASE.replace("3.5,", "3.50,")) == "distinta"


# --- Filas reordenadas, repetidas o faltantes ---

def test_filas_reordenadas_repetidas_o_faltantes_son_distintas():
    encabezado, fila_1, fila_2 = BASE.splitlines(keepends=True)
    assert estado(encabezado + fila_2 + fila_1) == "distinta"           # reordenadas
    assert estado(encabezado + fila_1 + fila_1) == "distinta"           # una repetida y otra que falta
    assert estado(encabezado + fila_1 + fila_2 + fila_2) == "distinta"  # una de más
    assert estado(encabezado + fila_1) == "distinta"                    # una de menos
    assert estado(encabezado) == "distinta"                             # sin filas


# --- Archivos que no se pueden leer ---

def test_un_archivo_que_no_es_utf8_se_avisa_sin_romper():
    ilegible = b"id_parcela,municipio\nAGC_001,Apan\xff\n"
    assert comparar_tablas(BASE.encode("utf-8"), ilegible, ESQUEMA["t.csv"])[0] == "distinta"
    assert comparar_tablas(ilegible, BASE.encode("utf-8"), ESQUEMA["t.csv"])[0] == "referencia"
    assert falla_con_mensaje(lambda: leer_esquema(ilegible))
    with tempfile.TemporaryDirectory() as d:
        argumentos = carpetas_de_prueba(Path(d), {"t.csv": BASE}, {"t.csv": BASE})
        (Path(d) / "nuevas" / "t.csv").write_bytes(ilegible)
        assert correr(*argumentos) == 1


def test_un_campo_enorme_se_avisa_sin_romper():
    enorme = ("id_parcela,municipio,puntos_contorno,area_ha_geodesica,rendimiento_t_ha,distancia_m\n"
              "AGC_001," + "x" * 200_000 + ",5,1.0,,\n")
    assert comparar_tablas(BASE.encode("utf-8"), enorme.encode("utf-8"), ESQUEMA["t.csv"])[0] == "distinta"


# --- Propiedad con datos al azar y cambios sobre las tablas reales ---

def test_la_tolerancia_se_comporta_igual_con_miles_de_valores_al_azar():
    azar = random.Random(20261008)
    for _ in range(2000):
        decimales = azar.randint(0, 6)
        unidad = Decimal(1).scaleb(-decimales)
        tolerancia = azar.choice([Decimal(0), unidad])
        valor = Decimal(azar.randint(-10**7, 10**7)).scaleb(-decimales)
        pasos = azar.choice([0, 1, -1, 2, -2, 3, 37, -1000])
        nuevo = valor + pasos * unidad
        escribir = lambda x: f"v\n{x:.{decimales}f}\n".encode("utf-8")
        obtenido = comparar_tablas(escribir(valor), escribir(nuevo), [("v", "decimal", decimales, tolerancia)])[0]
        esperado = "igual" if pasos == 0 else ("tolerancia" if abs(pasos) * unidad <= tolerancia else "distinta")
        assert obtenido == esperado, (valor, nuevo, decimales, tolerancia, obtenido, esperado)


def test_cambiar_una_celda_de_cualquier_columna_de_las_tablas_reales_se_detecta():
    esquema = leer_esquema(comparador.ESQUEMA_POR_OMISION.read_bytes())
    revisadas = 0
    for tabla in sorted(comparador.TABLAS_POR_OMISION.glob("*.csv")):
        original = tabla.read_bytes()
        columnas, filas = leer_tabla(original)
        for j, (columna, tipo, decimales, tolerancia) in enumerate(esquema[tabla.name]):
            i = next((i for i, fila in enumerate(filas) if fila[j] != ""), None)
            if i is None:
                continue                                  # columna toda vacía: no hay valor que cambiar
            valor = filas[i][j]
            if tipo == "texto":
                casos = [(valor + "x", "distinta"), ("", "distinta")]
            elif tipo == "entero":
                casos = [(str(int(valor) + 1), "distinta"), ("", "distinta")]
            else:
                unidad = Decimal(1).scaleb(-decimales)
                mas = lambda n: f"{Decimal(valor) + n * unidad:.{decimales}f}"
                casos = [(mas(1), "tolerancia" if tolerancia >= unidad else "distinta"), (mas(2), "distinta"), ("", "distinta")]
            for nuevo, esperado in casos:
                copia = [fila[:] for fila in filas]
                copia[i][j] = nuevo
                salida = io.StringIO()
                csv.writer(salida, lineterminator="\n").writerows([columnas] + copia)
                obtenido = comparar_tablas(original, salida.getvalue().encode("utf-8"), esquema[tabla.name])[0]
                assert obtenido == esperado, f"{tabla.name}, {columna}: «{valor}» a «{nuevo}» dio {obtenido}, se esperaba {esperado}"
            revisadas += 1
    assert revisadas >= 150, f"solo se revisaron {revisadas} columnas"


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


def test_una_carpeta_con_un_subdirectorio_llamado_csv_se_ignora():
    with tempfile.TemporaryDirectory() as d:
        argumentos = carpetas_de_prueba(Path(d), {"t.csv": BASE}, {"t.csv": BASE})
        (Path(d) / "nuevas" / "carpeta.csv").mkdir()
        assert correr(*argumentos) == 0


def test_la_misma_carpeta_como_tablas_y_referencia_termina_con_error():
    with tempfile.TemporaryDirectory() as d:
        argumentos = carpetas_de_prueba(Path(d), {"t.csv": BASE}, {"t.csv": BASE})
        carpeta = str(Path(d) / "ref")
        assert falla_con_mensaje(lambda: correr("--esquema", argumentos[1], "--referencia", carpeta, "--tablas", carpeta))
        con_rodeo = str(Path(d) / "ref" / ".." / "ref")        # la misma carpeta escrita de otra forma
        assert falla_con_mensaje(lambda: correr("--esquema", argumentos[1], "--referencia", carpeta, "--tablas", con_rodeo))


def test_el_mensaje_final_no_acusa_rutas_malas_cuando_solo_una_tabla_es_distinta():
    with tempfile.TemporaryDirectory() as d:
        codigo, texto = ejecutar(*carpetas_de_prueba(Path(d), {"t.csv": BASE}, {"t.csv": BASE.replace("Apan", "Otro")}))
    assert codigo == 1
    assert "0 iguales" in texto and "1 distintas" in texto
    assert "revisa las rutas" not in texto


if __name__ == "__main__":
    pruebas = [(nombre, f) for nombre, f in sorted(globals().items()) if nombre.startswith("test_")]
    for nombre, prueba in pruebas:
        prueba()
        print(f"cumple  {nombre}")
    print(f"{len(pruebas)} de {len(pruebas)} pruebas cumplen")
