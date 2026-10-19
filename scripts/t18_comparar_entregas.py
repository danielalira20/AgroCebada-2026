"""T18 · Compara dos archivos de entrega de predicciones (el nuestro y el de otra persona del equipo).

Uso:
    python -m scripts.t18_comparar_entregas --a registro/t18/predicciones_finales.csv \
        --b registro/t18/predicciones_59_T16-MEDIANA-MUNICIPAL-2025-v1.csv [--tolerancia 1e-9] [--estricto]

Separa dos cosas:
    CONTENIDO (decide el resultado): encabezado, número de filas, IDs (faltantes, duplicados, orden),
        AREA_HA, CONJUNTO y RENDIMIENTO_T_HA (numérico; 3.2 y 3.20 son iguales).
    FORMATO (informativo): BOM, saltos de línea, salto final, separador, coma final, decimales.
        Con --estricto una diferencia de formato también hace fallar.

Códigos de salida: 0 coinciden · 1 hay diferencias · 2 no se pudo leer un archivo.
"""
import argparse
import csv
import io
import math
import sys
from pathlib import Path

ENCABEZADO = ["ID_POLIGONO", "AREA_HA", "RENDIMIENTO_T_HA", "CONJUNTO"]


def describir_formato(raw: bytes) -> dict:
    texto = raw.decode("utf-8-sig")
    crlf, lf = texto.count("\r\n"), texto.count("\n") - texto.count("\r\n")
    primera = texto.splitlines()[0] if texto else ""
    lineas = [l for l in texto.splitlines() if l]
    rend = []
    for fila in csv.reader(io.StringIO(texto)):
        if len(fila) >= 3 and fila[0] != "ID_POLIGONO":
            rend.append(fila[2])
    decimales = sorted({len(r.split(".")[1]) if "." in r else 0 for r in rend})
    return {
        "BOM UTF-8": raw.startswith(b"\xef\xbb\xbf"),
        "saltos de línea": "CRLF" if crlf and not lf else "LF" if lf and not crlf else "mixtos" if crlf and lf else "ninguno",
        "termina en salto de línea": raw.endswith(b"\n"),
        "separador": ";" if primera.count(";") > primera.count(",") else ",",
        "coma final en las líneas": any(l.endswith(",") for l in lineas),
        "decimales en RENDIMIENTO_T_HA": decimales,
    }


def leer(raw: bytes):
    """Devuelve (encabezado, filas); quita la columna vacía que deja una coma final."""
    filas = list(csv.reader(io.StringIO(raw.decode("utf-8-sig"))))
    filas = [f for f in filas if any(c.strip() for c in f)]
    if not filas:
        raise ValueError("archivo vacío")
    limpias = []
    for f in filas:
        while f and f[-1] == "":
            f = f[:-1]
        limpias.append(f)
    return limpias[0], limpias[1:]


def numero(texto):
    try:
        v = float(texto)
        return v if math.isfinite(v) else None
    except (TypeError, ValueError):
        return None


def comparar(raw_a: bytes, raw_b: bytes, tolerancia=1e-9, municipios=None):
    """Devuelve (diferencias_de_contenido, diferencias_de_formato, resumen)."""
    municipios = municipios or {}
    dif, resumen = [], {}
    enc_a, filas_a = leer(raw_a)
    enc_b, filas_b = leer(raw_b)
    if enc_a != enc_b:
        dif.append(f"encabezado distinto: A={enc_a} | B={enc_b}")
    if enc_a != ENCABEZADO:
        dif.append(f"el encabezado de A no es el de la plantilla: {enc_a}")
    if enc_b != ENCABEZADO:
        dif.append(f"el encabezado de B no es el de la plantilla: {enc_b}")
    resumen["filas"] = (len(filas_a), len(filas_b))
    if len(filas_a) != len(filas_b):
        dif.append(f"número de filas distinto: A={len(filas_a)} | B={len(filas_b)}")
    for nombre, filas in (("A", filas_a), ("B", filas_b)):
        malas = [f for f in filas if len(f) != 4]
        if malas:
            dif.append(f"{nombre}: {len(malas)} filas no tienen 4 columnas (primera: {malas[0]})")
    da = {f[0]: f for f in filas_a if len(f) == 4}
    db = {f[0]: f for f in filas_b if len(f) == 4}
    for nombre, filas in (("A", filas_a), ("B", filas_b)):
        ids = [f[0] for f in filas]
        dup = sorted({i for i in ids if ids.count(i) > 1})
        if dup:
            dif.append(f"{nombre}: IDs duplicados {dup}")
    solo_a, solo_b = sorted(set(da) - set(db)), sorted(set(db) - set(da))
    if solo_a:
        dif.append(f"IDs solo en A: {solo_a}")
    if solo_b:
        dif.append(f"IDs solo en B: {solo_b}")
    comunes = [f[0] for f in filas_a if f[0] in db]
    if not solo_a and not solo_b and comunes != [f[0] for f in filas_b]:
        dif.append("los mismos IDs, pero en distinto orden")
    max_dif, distintas = 0.0, []
    for i in comunes:
        a, b = da[i], db[i]
        if a[1] != b[1]:
            na, nb = numero(a[1]), numero(b[1])
            if na is None or nb is None or abs(na - nb) > tolerancia:
                dif.append(f"{i}: AREA_HA distinta (A={a[1]} | B={b[1]})")
        if a[3] != b[3]:
            dif.append(f"{i}: CONJUNTO distinto (A={a[3]} | B={b[3]})")
        va, vb = numero(a[2]), numero(b[2])
        if va is None or vb is None:
            dif.append(f"{i}: RENDIMIENTO_T_HA no numérico o no finito (A={a[2]!r} | B={b[2]!r})")
            continue
        d = abs(va - vb)
        max_dif = max(max_dif, d)
        if d > tolerancia:
            distintas.append((i, va, vb, d))
    for i, va, vb, d in distintas:
        dif.append(f"{i} ({municipios.get(i, '?')}): A={va} | B={vb} | diferencia {d:.6g}")
    resumen["max_dif_rendimiento"] = max_dif
    resumen["filas_con_rendimiento_distinto"] = len(distintas)
    fa, fb = describir_formato(raw_a), describir_formato(raw_b)
    dif_formato = [f"{k}: A={fa[k]} | B={fb[k]}" for k in fa if fa[k] != fb[k]]
    return dif, dif_formato, resumen


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--a", type=Path, required=True)
    ap.add_argument("--b", type=Path, required=True)
    ap.add_argument("--tolerancia", type=float, default=1e-9)
    ap.add_argument("--detalle", type=Path, default=Path("registro/t18/detalle_predicciones_59.csv"),
                    help="opcional: pone el municipio junto a cada diferencia")
    ap.add_argument("--estricto", action="store_true", help="una diferencia de formato también falla")
    x = ap.parse_args()
    try:
        raw_a, raw_b = x.a.read_bytes(), x.b.read_bytes()
    except OSError as e:
        print(f"No se pudo leer: {e}")
        sys.exit(2)
    municipios = {}
    if x.detalle.exists():
        with open(x.detalle, encoding="utf-8", newline="") as f:
            municipios = {r["ID_POLIGONO"]: r["municipio"] for r in csv.DictReader(f)}
    try:
        dif, dif_formato, r = comparar(raw_a, raw_b, x.tolerancia, municipios)
    except ValueError as e:
        print(f"No se pudo interpretar un archivo: {e}")
        sys.exit(2)
    print(f"A: {x.a}\nB: {x.b}")
    print(f"Filas: A={r['filas'][0]} | B={r['filas'][1]} | diferencia máxima en RENDIMIENTO_T_HA: {r['max_dif_rendimiento']:.3g}")
    print("\nFORMATO (informativo):" if dif_formato else "\nFORMATO: idéntico")
    for l in dif_formato:
        print(" -", l)
    if dif:
        print("\nCONTENIDO: HAY DIFERENCIAS")
        for l in dif:
            print(" -", l)
        sys.exit(1)
    print("\nCONTENIDO: COINCIDE (mismo encabezado, IDs, orden, áreas, conjunto y predicciones"
          f" dentro de {x.tolerancia:g})")
    if dif_formato and x.estricto:
        print("--estricto: el formato difiere")
        sys.exit(1)


if __name__ == "__main__":
    main()
