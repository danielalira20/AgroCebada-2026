"""Fases 0–2 T07: fuentes identificadas, catálogo y ventanas; no aprende del objetivo."""
import argparse
from collections import Counter
import hashlib
import importlib.metadata
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.t07_fuentes import BASE, leer_csv, leer_json, leer_entrega, sha, validar_catalogo, guardar_csv, guardar_json
from scripts.t07_ventanas import agregar, LARGA, ANCHA, CALIDAD, VENTANAS
from scripts.t07_diccionario import diccionario, CAMPOS

RAIZ = Path(__file__).resolve().parents[1]
T02 = "analisis/auditoria_catalogo_y_etiquetas"
T02_ARCHIVOS = {"tablas/catalogo_parcelas.csv", "tablas/soporte_por_parcela.csv",
                "tablas/huellas_archivos_leidos.csv", "scripts/construir_catalogo.py", "scripts/diagnosticar_soporte.py"}
T04_ARCHIVOS = ("manifest.json", "clima_parcela_mes.csv", "procedencia.json", "conciliacion_t02.json", "controles.json")


def git(*args, raiz=RAIZ):
    return subprocess.check_output(["git", *args], cwd=raiz, stderr=subprocess.PIPE)


def revision(ref, raiz=RAIZ):
    if ref.startswith("-"):
        raise ValueError("Revisión Git inválida")
    return git("rev-parse", "--verify", ref + "^{commit}", raiz=raiz).decode().strip()


def comprobar_fuente(ruta, ref, esperado=None, raiz=RAIZ):
    h = sha(raiz / ruta)
    if h != hashlib.sha256(git("show", f"{ref}:{ruta}", raiz=raiz)).hexdigest():
        raise ValueError(f"Fuente local distinta de la base identificada: {ruta}")
    if esperado is not None and h != esperado:
        raise ValueError(f"Referencia T02 cambió: {ruta}. Actualizar y revalidar T04; no saltar esta comprobación.")
    return h


def comprobar_copia(clima, ref, raiz=RAIZ):
    origen = leer_json(clima / "origen_git.json")
    if (origen.get("schema") != "t07_copia_t04_v1" or origen.get("revision_git") != ref or
            origen.get("prefijo_git") != "registro/t04" or
            origen.get("estado_revision_declarado") not in {"en_revision", "aceptada"} or
            set(origen.get("archivos_sha256", {})) != set(T04_ARCHIVOS)):
        raise ValueError("Copia T04 sin identidad de revisión compatible")
    hashes = {}
    for n in T04_ARCHIVOS:
        h = sha(clima / n)
        if h != origen["archivos_sha256"][n] or h != hashlib.sha256(git("show", f"{ref}:registro/t04/{n}", raiz=raiz)).hexdigest():
            raise ValueError(f"Copia T04 alterada o de otra revisión: {n}")
        hashes[n] = h
    return origen, hashes


def preparar(clima, ref_t04, base_dev, salida, raiz=RAIZ):
    clima, salida, raiz = Path(clima).resolve(), Path(salida).resolve(), Path(raiz).resolve()
    if salida == raiz or salida.is_relative_to(raiz / "data" / "raw") or salida == clima or salida.is_relative_to(clima):
        raise ValueError("Salida protegida: no escribir en originales ni entradas")
    if salida.exists():
        raise ValueError("La salida ya existe; reproducir en una carpeta nueva")
    base, rt04 = revision(base_dev, raiz), revision(ref_t04, raiz)
    origen, ht04 = comprobar_copia(clima, rt04, raiz)
    ruta_cat = f"{T02}/tablas/catalogo_parcelas.csv"
    comprobar_fuente(ruta_cat, base, raiz=raiz)
    _, filas = leer_csv(raiz / ruta_cat)
    catalogo = validar_catalogo(filas)
    ids = [r["id_parcela"] for r in catalogo]
    indice, m, pro, con = leer_entrega(clima, ids)
    if set(con.get("archivos_t02_sha256", {})) != T02_ARCHIVOS:
        raise ValueError("Referencia T02 sin los cinco archivos requeridos")
    ht02 = {f"{T02}/{n}": comprobar_fuente(f"{T02}/{n}", base, h, raiz)
            for n, h in sorted(con["archivos_t02_sha256"].items())}
    protocolo = "docs/T03_protocolo_evaluacion.md"
    ht03 = comprobar_fuente(protocolo, base, raiz=raiz)
    ruta_t06, dic_t06 = "registro/t06/variables_satelitales.csv", "registro/t06/variables_satelitales_diccionario.csv"
    ht06 = {n: comprobar_fuente(n, base, raiz=raiz) for n in (ruta_t06, dic_t06, "docs/T06_satelite.md")}
    cab, sat = leer_csv(raiz / ruta_t06)
    _, dsat = leer_csv(raiz / dic_t06)
    sat_ids = [r["ID_POLIGONO"] for r in sat]
    if len(sat_ids) != 197 or len(set(sat_ids)) != 197 or set(sat_ids) != set(ids):
        raise ValueError("IDs T06 incompatibles")
    # La fase 0 inventaría T06; interpretar/unir su diccionario corresponde a fase 3.
    inventario = dict(schema="t07_inventario_v1", base_dev=base,
        bloques={
            "T02": dict(estado="base_dev_identificada_con_correcciones_pendientes", referencia_t04=con["revision_t02"], archivos_sha256=ht02),
            "T03": dict(estado="protocolo_base_identificado_corte_provisional", archivos_sha256={protocolo: ht03}),
            "T04": dict(estado=origen["estado_revision_declarado"], revision_git=rt04, archivos_sha256=ht04,
                        conciliacion="compatible_con_referencia_identificada", cierre_declarado=m["cierre_t04"],
                        sha256_paquete_original=pro["sha256_paquete"],
                        disponibilidad_historica=m["disponibilidad_historica_fira"],
                        version_producto=m["versiones_producto_fira"]),
            "T05": dict(estado="sin_entrega_identificada_en_esta_base", integrado=False),
            "T06": dict(estado="integrado_en_base_dev_aceptacion_no_inferida", integrado_en_t07=False,
                        archivos_sha256=ht06, ids=197, columnas=len(cab), entradas_diccionario=len(dsat))},
        corte_observacional=m["corte_observacional_provisional"],
        alcance="Reconstrucción retrospectiva; corte observado no prueba publicación histórica",
        cierre_t07=False, fases_implementadas=[0, 1, 2])
    larga, ancha, calidad = agregar(indice, ids)
    definiciones = diccionario()
    tablas = {"catalogo_base.csv": (BASE, catalogo), "clima_ventanas.csv": (LARGA, larga),
              "clima_variables.csv": (ANCHA, ancha), "calidad_ventanas.csv": (CALIDAD, calidad)}
    pares = {(r["archivo"], r["columna"]) for r in definiciones}
    esperados = {(n, c) for n, (campos, _) in tablas.items() for c in campos}
    if pares != esperados or len(pares) != len(definiciones):
        raise ValueError("Diccionario incompleto/duplicado")
    controles = dict(parcelas=len(ids), etiquetas_originales=138, etiquetas_ausentes=59,
                     filas_mensuales_verificadas=len(indice), filas_por_tabla={n: len(r) for n, (_, r) in tablas.items()},
                     ventanas={w: dict(meses=len(p), dias=next(r["dias_esperados"] for r in larga if r["ventana"] == w)) for w, p in VENTANAS.items()},
                     estados_ventanas=dict(Counter(r["estado"] for r in calidad)),
                     resumenes_completos=sum(r["estado"] == "completa" for r in calidad),
                     diccionario_columnas=len(definiciones), etiquetas_sin_transformar=True,
                     usa_meses_posteriores_al_corte=False, aprende_del_rendimiento=False,
                     cobertura_minima=min(r["cobertura_minima"] for r in calidad if r["cobertura_minima"] != ""))
    salida.parent.mkdir(parents=True, exist_ok=True)
    temp = Path(tempfile.mkdtemp(prefix=".t07-", dir=salida.parent))
    try:
        for n, (campos, r) in tablas.items(): guardar_csv(temp / n, campos, r)
        guardar_csv(temp / "diccionario_columnas.csv", CAMPOS, definiciones)
        guardar_json(temp / "inventario_fuentes.json", inventario)
        guardar_json(temp / "controles.json", controles)
        codigo = ["t07_preparar.py", "t07_fuentes.py", "t07_ventanas.py", "t07_diccionario.py", "t07_preparar_insumos.py"]
        guardar_json(temp / "manifest.json", dict(schema="t07_fases_0_2_v1",
                     codigo_sha256={f"scripts/{n}": sha(raiz / "scripts" / n) for n in codigo},
                     entradas= dict(base_dev=base, revision_t04=rt04, manifest_t04_sha256=ht04["manifest.json"]),
                     archivos_sha256={p.name: sha(p) for p in sorted(temp.iterdir())},
                     metodo_temperatura="ponderado_por_dias_naturales", metodo_lluvia="suma_de_medias_espaciales_mensuales",
                     cierre_t07=False))
        temp.rename(salida)
    except BaseException:
        shutil.rmtree(temp)
        raise
    return controles


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--clima", type=Path, required=True, help="Copia generada por t07_preparar_insumos.py")
    p.add_argument("--revision-t04", required=True)
    p.add_argument("--base-dev", required=True, help="Commit de dev que identifica catálogo, protocolo y T06")
    p.add_argument("--salida", type=Path, required=True, help="Carpeta nueva; no sobrescribe")
    a = p.parse_args()
    try:
        c = preparar(a.clima, a.revision_t04, a.base_dev, a.salida)
    except (ValueError, KeyError, OSError, subprocess.CalledProcessError) as e:
        p.exit(1, f"T07 detenida: {e}\n")
    print(f"T07 fases 0–2: {c['parcelas']} parcelas, {c['resumenes_completos']} resúmenes completos; cierre pendiente de revisión.")


if __name__ == "__main__": main()
