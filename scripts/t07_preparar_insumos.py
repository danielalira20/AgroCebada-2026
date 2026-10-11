"""Copia T04 desde una revisión Git explícita, sin integrar su rama ni tocar ZIP."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

ARCHIVOS = ("manifest.json", "clima_parcela_mes.csv", "procedencia.json",
            "conciliacion_t02.json", "controles.json")
RAIZ = Path(__file__).resolve().parents[1]


def git(*args):
    return subprocess.check_output(["git", "-C", str(RAIZ), *args])


def preparar(revision, salida, estado):
    revision = git("rev-parse", "--verify", revision + "^{commit}").decode().strip()
    salida = Path(salida).resolve()
    if salida.exists():
        raise FileExistsError("La salida ya existe; usar una carpeta nueva")
    if (RAIZ / "data" / "raw").resolve() in (salida, *salida.parents):
        raise ValueError("No escribir insumos derivados en data/raw")
    contenido = {n: git("show", f"{revision}:registro/t04/{n}") for n in ARCHIVOS}
    m = json.loads(contenido["manifest.json"])
    if m.get("schema") != "t04_entrega_compacta_v1":
        raise ValueError("Esquema T04 incompatible")
    esperados = set(ARCHIVOS) - {"manifest.json"}
    if set(m["archivos_sha256"]) != esperados:
        raise ValueError("Lista de archivos T04 incompatible")
    for n in esperados:
        if hashlib.sha256(contenido[n]).hexdigest() != m["archivos_sha256"][n]:
            raise ValueError(f"Huella de entrega T04 distinta: {n}")
    origen = {"schema": "t07_copia_t04_v1", "revision_git": revision,
              "prefijo_git": "registro/t04", "estado_revision_declarado": estado,
              "archivos_sha256": {n: hashlib.sha256(b).hexdigest() for n, b in contenido.items()},
              "no_equivale_a_merge_o_aprobacion": True}
    salida.parent.mkdir(parents=True, exist_ok=True)
    temporal = Path(tempfile.mkdtemp(prefix=".t07-insumos-", dir=salida.parent))
    try:
        for n, b in contenido.items():
            (temporal / n).write_bytes(b)
        (temporal / "origen_git.json").write_text(
            json.dumps(origen, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temporal.rename(salida)
    finally:
        if temporal.exists():
            shutil.rmtree(temporal)
    return origen


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--revision-t04", required=True)
    p.add_argument("--salida", type=Path, required=True)
    p.add_argument("--estado-t04", choices=["en_revision", "aceptada"], required=True,
                   help="Estado humano declarado; el script no aprueba un PR")
    a = p.parse_args()
    try:
        resultado = preparar(a.revision_t04, a.salida, a.estado_t04)
    except (ValueError, FileExistsError, subprocess.CalledProcessError) as e:
        p.exit(1, f"T07: {e}\n")
    print(json.dumps(resultado, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
