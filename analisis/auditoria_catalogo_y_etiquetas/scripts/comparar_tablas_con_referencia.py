"""Compara las tablas recién generadas con una versión de referencia, según un esquema declarado.

Uso (después de correr los scripts de la auditoría, desde la raíz del repositorio):
    python analisis/auditoria_catalogo_y_etiquetas/scripts/comparar_tablas_con_referencia.py

Por omisión compara los CSV de tablas/ con los de la última versión guardada en Git (HEAD).
Solo lee: no cambia Git ni escribe ningún archivo.

Opciones:
    --tablas CARPETA       Tablas recién generadas. Por omisión, tablas/ de esta auditoría.
    --referencia CARPETA   Carpeta con las tablas de referencia, en lugar de Git.
    --version NOMBRE       Versión de Git que sirve de referencia. Por omisión, HEAD.
    --esquema ARCHIVO      Esquema de las tablas. Por omisión, esquema_de_tablas.csv.

El esquema (esquema_de_tablas.csv) declara, para cada columna de cada tabla, su tipo y cuánta
diferencia se acepta. Lo que decide es el esquema, no lo que traiga la tabla nueva:
    texto     Debe coincidir exactamente.
    entero    Debe ser un entero y coincidir exactamente.
    decimal   Debe ser un número con a lo sumo los decimales declarados (se acepta la notación
              científica, como 1e-05, que escribe pandas con los números muy chicos). Se acepta una
              diferencia de hasta la tolerancia declarada; si la tolerancia es 0, el texto debe
              coincidir exactamente (3.5 y 3.50 cuentan como distintos, y 0.0 y -0.0 también).
El fin de línea (Windows o Mac/Linux) no se toma en cuenta.

Además del esquema se usa la referencia como segunda comprobación: antes de comparar se revisa
que la propia referencia cumpla el esquema. Si no lo cumple, se avisa y cuenta como falla.

Termina con código 0 solo si todas las tablas del esquema se compararon y son iguales o iguales
dentro de la tolerancia. Termina con código 1 si alguna es distinta, falta, sobra o no cumple el
esquema, y también si una carpeta no existe, no hay ninguna tabla que comparar, la carpeta de
referencia es la misma que la de las tablas nuevas, o un archivo no se puede leer como CSV UTF-8.
"""
import argparse
import csv
import io
import re
import subprocess
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path

sys.dont_write_bytecode = True

CARPETA = Path(__file__).resolve().parents[1]
TABLAS_POR_OMISION = CARPETA / "tablas"
ESQUEMA_POR_OMISION = CARPETA / "esquema_de_tablas.csv"
COLUMNAS_DEL_ESQUEMA = ["tabla", "columna", "tipo", "decimales", "tolerancia", "motivo"]
TIPOS = ("texto", "entero", "decimal")
ENTERO = re.compile(r"-?\d+", re.ASCII)
NUMERO = re.compile(r"-?\d+(\.\d+)?([eE][-+]?\d+)?", re.ASCII)   # solo dígitos 0-9, no los de otros alfabetos
LIMITE_EXPONENTE = 300      # un valor más grande o más chico que esto no es un dato plausible de estas tablas
MAXIMO_A_MOSTRAR = 5
ETIQUETAS = {"igual": "igual", "tolerancia": "igual dentro de la tolerancia", "distinta": "DISTINTA",
             "referencia": "LA REFERENCIA NO CUMPLE EL ESQUEMA", "sin_esquema": "SIN ESQUEMA"}


def leer_tabla(contenido: bytes):
    """Devuelve (columnas, filas) de un CSV, sin importar el fin de línea ni la marca inicial.

    Si el archivo no es un CSV legible en UTF-8 lanza ValueError con un mensaje claro."""
    try:
        texto = contenido.decode("utf-8-sig").replace("\r\n", "\n").replace("\r", "\n")
        filas = list(csv.reader(io.StringIO(texto)))
    except (UnicodeDecodeError, csv.Error) as error:
        raise ValueError(f"no se puede leer como CSV en UTF-8 ({error})") from None
    return (filas[0], filas[1:]) if filas else ([], [])


def decimales_de(valor: str):
    """Cuántos decimales tiene un número escrito (1.50 tiene 2; 1e-05 tiene 5), o None si no es un número normal."""
    if not NUMERO.fullmatch(valor):
        return None
    try:
        numero = Decimal(valor)
    except InvalidOperation:
        return None
    if not numero.is_finite() or abs(numero.adjusted()) > LIMITE_EXPONENTE:
        return None
    return max(0, -numero.as_tuple().exponent)


def leer_esquema(contenido: bytes) -> dict:
    """Devuelve {tabla: [(columna, tipo, decimales, tolerancia), ...]} y comprueba que el esquema esté bien escrito."""
    try:
        columnas, filas = leer_tabla(contenido)
    except ValueError as error:
        raise SystemExit(f"El esquema {error}")
    if columnas != COLUMNAS_DEL_ESQUEMA:
        raise SystemExit(f"El esquema debe tener las columnas {COLUMNAS_DEL_ESQUEMA}; tiene {columnas}")
    esquema = {}
    for numero, fila in enumerate(filas, start=2):
        if len(fila) != len(COLUMNAS_DEL_ESQUEMA):
            raise SystemExit(f"Esquema, línea {numero}: número de celdas inesperado")
        tabla, columna, tipo, decimales, tolerancia, _ = fila
        if tipo not in TIPOS:
            raise SystemExit(f"Esquema, línea {numero}: el tipo «{tipo}» no es uno de {TIPOS}")
        if tipo == "decimal":
            try:
                decimales, tolerancia = int(decimales), Decimal(tolerancia)
            except (ValueError, InvalidOperation):
                raise SystemExit(f"Esquema, línea {numero}: una columna decimal necesita decimales y tolerancia")
            if decimales < 0 or not tolerancia.is_finite() or tolerancia < 0:
                raise SystemExit(f"Esquema, línea {numero}: decimales y tolerancia deben ser números finitos no negativos")
        elif decimales or tolerancia:
            raise SystemExit(f"Esquema, línea {numero}: solo las columnas decimales llevan decimales y tolerancia")
        else:
            decimales, tolerancia = 0, Decimal(0)
        if columna in [c for c, *_ in esquema.get(tabla, [])]:
            raise SystemExit(f"Esquema, línea {numero}: la columna {columna} de {tabla} está repetida")
        esquema.setdefault(tabla, []).append((columna, tipo, decimales, tolerancia))
    if not esquema:
        raise SystemExit("El esquema no declara ninguna tabla")
    return esquema


def valor_cumple(valor: str, tipo: str, decimales: int) -> bool:
    """Una celda vacía significa «no hay dato» y se admite en cualquier tipo."""
    if valor == "" or tipo == "texto":
        return True
    if tipo == "entero":
        return bool(ENTERO.fullmatch(valor))
    lugares = decimales_de(valor)
    return lugares is not None and lugares <= decimales


def revisar_contra_esquema(columnas, filas, esquema_tabla):
    """Lista de problemas de una tabla frente a su esquema; vacía si lo cumple."""
    declaradas = [c for c, *_ in esquema_tabla]
    if columnas != declaradas:
        return [f"columnas distintas de las del esquema: esquema {declaradas}; tabla {columnas}"]
    problemas = []
    for numero, fila in enumerate(filas, start=2):
        if len(fila) != len(declaradas):
            problemas.append(f"línea {numero}: número de celdas inesperado")
            continue
        for (columna, tipo, decimales, _), valor in zip(esquema_tabla, fila):
            if not valor_cumple(valor, tipo, decimales):
                esperado = "un entero" if tipo == "entero" else f"un número con a lo sumo {decimales} decimales"
                problemas.append(f"línea {numero}, columna {columna}: «{valor}» no es {esperado}")
    return problemas


def comparar_tablas(referencia: bytes, nueva: bytes, esquema_tabla):
    """Compara dos CSV según el esquema. Devuelve (estado, detalles).

    El estado es 'igual', 'tolerancia', 'distinta' o 'referencia' (la referencia no cumple el esquema).
    """
    try:
        columnas_r, filas_r = leer_tabla(referencia)
    except ValueError as error:
        return "referencia", [f"la referencia {error}"]
    try:
        columnas_n, filas_n = leer_tabla(nueva)
    except ValueError as error:
        return "distinta", [f"la tabla nueva {error}"]
    problemas = revisar_contra_esquema(columnas_r, filas_r, esquema_tabla)
    if problemas:
        return "referencia", problemas
    problemas = revisar_contra_esquema(columnas_n, filas_n, esquema_tabla)
    if problemas:
        return "distinta", ["la tabla nueva no cumple el esquema"] + problemas
    if len(filas_r) != len(filas_n):
        return "distinta", [f"número de filas distinto: referencia {len(filas_r)}; nueva {len(filas_n)}"]
    distintas, toleradas, mayor = [], 0, {}
    for numero, (fr, fn) in enumerate(zip(filas_r, filas_n), start=2):
        for (columna, tipo, _, tolerancia), a, b in zip(esquema_tabla, fr, fn):
            if a == b:
                continue
            if tipo == "decimal" and tolerancia > 0 and a != "" and b != "":
                diferencia = abs(Decimal(a) - Decimal(b))
                if diferencia <= tolerancia:
                    toleradas += 1
                    mayor[columna] = max(mayor.get(columna, Decimal(0)), diferencia)
                    continue
            distintas.append(f"línea {numero}, columna {columna}: referencia «{a}»; nueva «{b}»")
    if distintas:
        return "distinta", distintas
    if toleradas:
        return "tolerancia", [f"{toleradas} celdas con diferencia mínima; la mayor por columna: "
                              + ", ".join(f"{c} {d}" for c, d in mayor.items())]
    return "igual", []


def comparar_carpetas(referencia: dict, nuevas: dict, esquema: dict):
    """Compara todas las tablas. Devuelve una lista de (nombre, estado, detalles), ordenada por nombre."""
    resultados = []
    for nombre in sorted(set(esquema) | set(referencia) | set(nuevas)):
        if nombre not in esquema:
            resultados.append((nombre, "sin_esquema", ["la tabla no está declarada en el esquema"]))
        elif nombre not in referencia and nombre not in nuevas:
            resultados.append((nombre, "distinta", ["falta en la referencia y entre las tablas nuevas"]))
        elif nombre not in nuevas:
            resultados.append((nombre, "distinta", ["falta entre las tablas nuevas"]))
        elif nombre not in referencia:
            resultados.append((nombre, "distinta", ["no está en la referencia (tabla nueva)"]))
        else:
            resultados.append((nombre, *comparar_tablas(referencia[nombre], nuevas[nombre], esquema[nombre])))
    return resultados


def tablas_de_git(version: str):
    """Lee de Git, sin modificarlo, los CSV de tablas/ de esta auditoría en la versión indicada.

    La referencia es siempre tablas/ de esta auditoría, esté donde esté la carpeta nueva (--tablas)."""
    def git(carpeta, *argumentos):
        return subprocess.run(["git", "--no-optional-locks", *argumentos], cwd=carpeta, capture_output=True, check=True).stdout
    try:
        raiz = Path(git(CARPETA, "rev-parse", "--show-toplevel").decode().strip())
        relativa = TABLAS_POR_OMISION.resolve().relative_to(raiz.resolve()).as_posix()
        nombres = git(raiz, "ls-tree", "--name-only", f"{version}:{relativa}").decode().split("\n")
        return {n: git(raiz, "show", f"{version}:{relativa}/{n}") for n in nombres if n.endswith(".csv")}
    except (subprocess.CalledProcessError, FileNotFoundError, ValueError) as error:
        raise SystemExit(f"No se pudo leer la versión {version} de Git ({error}). "
                         "Indica una carpeta de referencia con --referencia.")


def tablas_de_carpeta(carpeta: Path, papel: str):
    if not carpeta.is_dir():
        raise SystemExit(f"No existe la carpeta de {papel}: {carpeta}")
    try:
        return {r.name: r.read_bytes() for r in sorted(carpeta.glob("*.csv")) if r.is_file()}
    except OSError as error:
        raise SystemExit(f"No se pudo leer la carpeta de {papel} ({error})")


def main(argumentos=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tablas", type=Path, default=TABLAS_POR_OMISION)
    ap.add_argument("--referencia", type=Path, default=None)
    ap.add_argument("--version", default="HEAD")
    ap.add_argument("--esquema", type=Path, default=ESQUEMA_POR_OMISION)
    a = ap.parse_args(argumentos)

    if not a.esquema.is_file():
        raise SystemExit(f"No existe el esquema: {a.esquema}")
    if a.referencia is not None and a.referencia.resolve() == a.tablas.resolve():
        raise SystemExit("La carpeta de referencia es la misma que la de las tablas nuevas: "
                         "compararía cada tabla consigo misma y siempre saldría igual.")
    esquema = leer_esquema(a.esquema.read_bytes())
    nuevas = tablas_de_carpeta(a.tablas, "tablas nuevas")
    if a.referencia is not None:
        referencia, origen = tablas_de_carpeta(a.referencia, "referencia"), f"la carpeta {a.referencia}"
    else:
        referencia, origen = tablas_de_git(a.version), f"la versión {a.version} de Git"
    if not referencia:
        raise SystemExit(f"No hay ninguna tabla CSV en {origen}: no hay contra qué comparar.")
    if not nuevas:
        raise SystemExit(f"No hay ninguna tabla CSV en {a.tablas}: no hay nada que comparar.")
    print(f"Tablas de {a.tablas} comparadas con {origen}, según {a.esquema.name}\n")

    resultados = comparar_carpetas(referencia, nuevas, esquema)
    conteo = {estado: 0 for estado in ETIQUETAS}
    for nombre, estado, detalles in resultados:
        conteo[estado] += 1
        print(f"{ETIQUETAS[estado]:<30} {nombre}")
        for detalle in detalles[:MAXIMO_A_MOSTRAR]:
            print(f"    {detalle}")
        if len(detalles) > MAXIMO_A_MOSTRAR:
            print(f"    … y {len(detalles) - MAXIMO_A_MOSTRAR} más")
    fallas = conteo["distinta"] + conteo["referencia"] + conteo["sin_esquema"]
    print(f"\n{conteo['igual']} iguales, {conteo['tolerancia']} iguales dentro de la tolerancia, "
          f"{conteo['distinta']} distintas, {conteo['referencia']} con la referencia fuera del esquema, "
          f"{conteo['sin_esquema']} sin esquema")
    return 1 if fallas else 0


if __name__ == "__main__":
    sys.exit(main())
