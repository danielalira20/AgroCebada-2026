"""Copia local para QGIS a partir del maestro, conservando el proyecto anterior.

Desde la raíz del repo: python scripts/preparar_qgis.py
Los originales bajo data/raw nunca se escriben. No requiere Docker ni QGIS API.
"""
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import xml.etree.ElementTree as ET
import zipfile

RAIZ = Path(__file__).resolve().parents[1]
PAQUETES = ("Parcelas_Reto_AGC_CONJUNTO_70_30.zip",
            "Reto_AgroCebada_CHIRPS_Precipitacion_2022_2025.zip",
            "Reto_AgroCebada_Temperatura_2022_2025_RECORTADA_CHIRPS.zip")


def preparar(raiz=RAIZ):
    maestro = raiz/"data/raw/DataSet.zip"
    anterior = raiz/"reports/t04_revision.qgz"
    destino = raiz/"data/processed/qgis/DATASET_RETO_AGRO_2026"
    nuevo = raiz/"reports/t04_revision_trabajo.qgz"
    sha = lambda datos: hashlib.sha256(datos).hexdigest()
    archivos = {}
    origenes = {}
    with zipfile.ZipFile(maestro) as exterior:
        for paquete in PAQUETES:
            with zipfile.ZipFile(io.BytesIO(exterior.read("DATASET_RETO_AGRO_2026/"+paquete))) as interior:
                for miembro in interior.infolist():
                    ruta = PurePosixPath(miembro.filename)
                    if miembro.is_dir() or "__MACOSX" in ruta.parts or ruta.name == ".DS_Store":
                        continue
                    if ruta.is_absolute() or ".." in ruta.parts or "\\" in miembro.filename:
                        raise ValueError("Ruta ZIP no segura")
                    if ruta.suffix == ".xml" and ruta.name.endswith(".aux.xml"):
                        raise ValueError("El maestro contiene auxiliares de visualización inesperados")
                    objetivo = destino.joinpath(*ruta.parts)
                    if not objetivo.resolve().is_relative_to(destino.resolve()):
                        raise ValueError("Destino fuera de la copia de visualización")
                    datos = interior.read(miembro)
                    if objetivo in archivos:
                        raise ValueError("Colisión de nombres en copia QGIS")
                    if objetivo.exists() and objetivo.read_bytes() != datos:
                        raise ValueError(f"La copia existente difiere; conservarla y revisar: {objetivo}")
                    archivos[objetivo] = datos
                    origenes[objetivo] = paquete+"!/"+miembro.filename
    with zipfile.ZipFile(anterior) as proyecto:
        qgs = next(n for n in proyecto.namelist() if n.endswith(".qgs"))
        original = proyecto.read(qgs)
        root = ET.fromstring(original)
        capas = []
        rutas_por_id = {}
        for layer in root.findall("./projectlayers/maplayer"):
            fuente = layer.find("datasource")
            if fuente is None or not fuente.text or ".zip/" not in fuente.text:
                raise ValueError("Fuente de proyecto distinta a la sesión revisada")
            miembro, separador, opciones = fuente.text.split(".zip/",1)[1].partition("|")
            objetivo = destino/PurePosixPath(miembro)
            if objetivo not in archivos:
                raise ValueError("Capa ausente en copia del maestro")
            ruta_relativa = Path(os.path.relpath(objetivo, nuevo.parent)).as_posix()
            fuente.text = ruta_relativa+(separador+opciones if separador else "")
            rutas_por_id[layer.findtext("id")] = fuente.text
            capas.append({"nombre": layer.findtext("layername"), "ruta": fuente.text})
        if len(capas) != 4:
            raise ValueError("Se esperaban cuatro capas")
        for nodo in root.iter("layer-tree-layer"):
            if nodo.get("id") not in rutas_por_id:
                raise ValueError("Capa de árbol sin fuente comprobada")
            nodo.set("source",rutas_por_id[nodo.get("id")])
        for nodo in root.iter():
            if any("data/raw" in v for v in nodo.attrib.values()) or (nodo.text and "data/raw" in nodo.text):
                raise ValueError("Referencia remanente a originales en proyecto de trabajo")
        contenido = io.BytesIO()
        with zipfile.ZipFile(contenido,"w") as salida:
            for info in proyecto.infolist():
                salida.writestr(info, ET.tostring(root, encoding="utf-8", xml_declaration=True) if info.filename == qgs else proyecto.read(info))
    nuevo_datos = contenido.getvalue()
    if nuevo.exists() and nuevo.read_bytes() != nuevo_datos:
        raise ValueError("El proyecto de trabajo ya existe con cambios; no sobrescribir")
    for objetivo, datos in archivos.items():
        objetivo.parent.mkdir(parents=True, exist_ok=True)
        if not objetivo.exists():
            objetivo.write_bytes(datos)
    if not nuevo.exists():
        nuevo.write_bytes(nuevo_datos)
    manifiesto = {"sha256_maestro":sha(maestro.read_bytes()),
                  "proyecto_anterior_sha256":sha(anterior.read_bytes()),
                  "proyecto_nuevo_sha256":sha(nuevo_datos),
                  "proyecto_nuevo":str(nuevo.relative_to(raiz)), "capas":capas,
                  "archivos":[{"ruta":str(p.relative_to(raiz)), "origen":origenes[p],
                               "bytes":len(b), "sha256":sha(b)} for p,b in archivos.items()]}
    informe = raiz/"reports/t04_fase2_20261006/copia_qgis.json"
    informe.parent.mkdir(parents=True, exist_ok=True)
    informe.write_text(json.dumps(manifiesto,ensure_ascii=False,indent=2)+"\n")
    return manifiesto


if __name__ == "__main__":
    resultado = preparar()
    print(json.dumps({"proyecto":resultado["proyecto_nuevo"],
                      "archivos":len(resultado["archivos"]),
                      "bytes":sum(a["bytes"] for a in resultado["archivos"]),
                      "capas":resultado["capas"]},ensure_ascii=False,indent=2))
