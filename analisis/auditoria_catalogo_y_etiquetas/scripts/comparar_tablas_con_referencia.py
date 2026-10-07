"""Compara las tablas recién generadas con una versión de referencia, aceptando diferencias mínimas.

Uso (después de correr los scripts de la auditoría, desde la raíz del repositorio):
    python analisis/auditoria_catalogo_y_etiquetas/scripts/comparar_tablas_con_referencia.py

Por omisión compara los CSV de tablas/ con los de la última versión guardada en Git (HEAD).
Solo lee: no cambia Git ni escribe ningún archivo.

Opciones:
    --tablas CARPETA       Tablas recién generadas. Por omisión, tablas/ de esta auditoría.
    --referencia CARPETA   Carpeta con las tablas de referencia, en lugar de Git.
    --version NOMBRE       Versión de Git que sirve de referencia. Por omisión, HEAD.

Qué cuenta como «igual»:
    - El fin de línea (Windows o Mac/Linux) no se toma en cuenta.
    - Mismas columnas en el mismo orden y mismas filas en el mismo orden.
    - Texto, enteros, marcas si/no y huellas: deben coincidir exactamente.
    - Columnas con decimales: se acepta una diferencia de hasta una unidad en el último
      decimal con que está escrita la columna. Por ejemplo, 0.000001 ha en un área escrita
      con 6 decimales, o 0.1 m en una distancia escrita con 1 decimal. Esa diferencia puede
      aparecer al redondear en otro sistema operativo o con otra versión de las librerías.

Termina con código 0 si todas las tablas son iguales o iguales dentro de la tolerancia,
y con código 1 si alguna es distinta, falta o sobra.
"""
import argparse
import csv
import io
import re
import subprocess
import sys
from decimal import Decimal
from pathlib import Path

sys.dont_write_bytecode = True

CARPETA = Path(__file__).resolve().parents[1]
TABLAS_POR_OMISION = CARPETA / "tablas"
NUMERO = re.compile(r"-?\d+(\.\d+)?")
MAXIMO_A_MOSTRAR = 5


def leer_tabla(contenido: bytes):
    """Devuelve (columnas, filas) de un CSV, sin importar el fin de línea ni la marca inicial."""
    texto = contenido.decode("utf-8-sig").replace("\r\n", "\n").replace("\r", "\n")
    filas = list(csv.reader(io.StringIO(texto)))
    return (filas[0], filas[1:]) if filas else ([], [])


def decimales(valor: str) -> int:
    return len(valor.split(".")[1]) if "." in valor else 0


def tolerancias_por_columna(columnas, filas_a, filas_b):
    """Para cada columna con decimales, una unidad de su último decimal. Las demás no tienen tolerancia."""
    tolerancias = {}
    for i, nombre in enumerate(columnas):
        valores = [f[i] for f in filas_a + filas_b if i < len(f) and f[i] != ""]
        if valores and all(NUMERO.fullmatch(v) for v in valores):
            d = max(decimales(v) for v in valores)
            if d > 0:
                tolerancias[nombre] = Decimal(1).scaleb(-d)
    return tolerancias


def comparar_tablas(referencia: bytes, nueva: bytes):
    """Compara dos CSV. Devuelve (estado, detalles); estado es 'igual', 'tolerancia' o 'distinta'."""
    columnas_r, filas_r = leer_tabla(referencia)
    columnas_n, filas_n = leer_tabla(nueva)
    if columnas_r != columnas_n:
        return "distinta", [f"columnas distintas: referencia {columnas_r}; nueva {columnas_n}"]
    if len(filas_r) != len(filas_n):
        return "distinta", [f"número de filas distinto: referencia {len(filas_r)}; nueva {len(filas_n)}"]
    tolerancias = tolerancias_por_columna(columnas_r, filas_r, filas_n)
    distintas, toleradas, mayor = [], 0, {}
    for numero, (fr, fn) in enumerate(zip(filas_r, filas_n), start=2):
        if len(fr) != len(columnas_r) or len(fn) != len(columnas_r):
            distintas.append(f"línea {numero}: número de celdas inesperado")
            continue
        for nombre, a, b in zip(columnas_r, fr, fn):
            if a == b:
                continue
            tolerancia = tolerancias.get(nombre)
            if tolerancia is not None and a != "" and b != "":
                diferencia = abs(Decimal(a) - Decimal(b))
                if diferencia <= tolerancia:
                    toleradas += 1
                    mayor[nombre] = max(mayor.get(nombre, Decimal(0)), diferencia)
                    continue
            distintas.append(f"línea {numero}, columna {nombre}: referencia «{a}»; nueva «{b}»")
    if distintas:
        return "distinta", distintas
    if toleradas:
        return "tolerancia", [f"{toleradas} celdas con diferencia mínima; la mayor por columna: "
                              + ", ".join(f"{c} {d}" for c, d in mayor.items())]
    return "igual", []


def tablas_de_git(tablas: Path, version: str):
    """Lee de Git, sin modificarlo, los CSV de la carpeta de tablas en la versión indicada."""
    def git(carpeta, *argumentos):
        return subprocess.run(["git", "--no-optional-locks", *argumentos], cwd=carpeta, capture_output=True, check=True).stdout
    try:
        raiz = Path(git(tablas, "rev-parse", "--show-toplevel").decode().strip())
        relativa = tablas.resolve().relative_to(raiz.resolve()).as_posix()
        nombres = git(raiz, "ls-tree", "--name-only", f"{version}:{relativa}").decode().split("\n")
        return {n: git(raiz, "show", f"{version}:{relativa}/{n}") for n in nombres if n.endswith(".csv")}
    except (subprocess.CalledProcessError, FileNotFoundError, ValueError) as error:
        raise SystemExit(f"No se pudo leer la versión {version} de Git ({error}). "
                         "Indica una carpeta de referencia con --referencia.")


def tablas_de_carpeta(carpeta: Path):
    return {r.name: r.read_bytes() for r in sorted(carpeta.glob("*.csv"))}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tablas", type=Path, default=TABLAS_POR_OMISION)
    ap.add_argument("--referencia", type=Path, default=None)
    ap.add_argument("--version", default="HEAD")
    a = ap.parse_args()

    nuevas = tablas_de_carpeta(a.tablas)
    if a.referencia is not None:
        referencia, origen = tablas_de_carpeta(a.referencia), f"la carpeta {a.referencia}"
    else:
        referencia, origen = tablas_de_git(a.tablas, a.version), f"la versión {a.version} de Git"
    print(f"Tablas de {a.tablas} comparadas con {origen}\n")

    conteo = dict(igual=0, tolerancia=0, distinta=0)
    for nombre in sorted(set(referencia) | set(nuevas)):
        if nombre not in nuevas:
            estado, detalles = "distinta", ["falta entre las tablas nuevas"]
        elif nombre not in referencia:
            estado, detalles = "distinta", ["no está en la referencia (tabla nueva)"]
        else:
            estado, detalles = comparar_tablas(referencia[nombre], nuevas[nombre])
        conteo[estado] += 1
        etiqueta = dict(igual="igual", tolerancia="igual dentro de la tolerancia", distinta="DISTINTA")[estado]
        print(f"{etiqueta:<30} {nombre}")
        for detalle in detalles[:MAXIMO_A_MOSTRAR]:
            print(f"    {detalle}")
        if len(detalles) > MAXIMO_A_MOSTRAR:
            print(f"    … y {len(detalles) - MAXIMO_A_MOSTRAR} diferencias más")
    print(f"\n{conteo['igual']} iguales, {conteo['tolerancia']} iguales dentro de la tolerancia, "
          f"{conteo['distinta']} distintas")
    sys.exit(1 if conteo["distinta"] else 0)


if __name__ == "__main__":
    main()
