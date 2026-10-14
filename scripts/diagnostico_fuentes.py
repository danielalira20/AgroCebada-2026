"""Materializa sólo blobs declarados de commits exactos; sin red ni ejecución de modelos."""
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import tempfile
import os


def exigir(ok,message):
    if not ok:raise ValueError(message)


def json_estricto(path):
    path=Path(path)
    exigir(path.is_file() and not path.is_symlink() and path.stat().st_nlink==1 and path.stat().st_size<=64*1024*1024,'JSON no regular/excede contrato')
    def pairs(values):
        result={}
        for k,v in values:
            exigir(k not in result,'Clave JSON duplicada');result[k]=v
        return result
    def bad(value):raise ValueError('Número JSON no finito')
    return json.loads(Path(path).read_text(encoding='utf-8'),object_pairs_hook=pairs,parse_constant=bad)


def hash_archivo(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def ruta_segura(root,rel):
    relpath=PurePosixPath(rel)
    exigir(isinstance(rel,str) and not relpath.is_absolute() and '..' not in relpath.parts and relpath.parts and all(p not in ['.',''] for p in relpath.parts),'Ruta relativa inválida')
    root=Path(root).resolve();path=root.joinpath(*relpath.parts)
    exigir(root in path.resolve().parents,'Ruta fuera del root')
    cursor=root
    for part in relpath.parts:
        cursor/=part;exigir(not cursor.is_symlink(),'Enlace simbólico no permitido')
    return path


def preparar(repo,manifest,destino):
    repo=Path(repo).resolve();destino=Path(destino)
    exigir(not destino.exists(),'La copia de fuentes requiere destino nuevo')
    destino.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.fuentes_',dir=destino.parent) as temp:
        stage=Path(temp)/'datos';stage.mkdir()
        for name,src in manifest['fuentes'].items():
            exigir(re.fullmatch('[a-z0-9_]+',name) and re.fullmatch('[0-9a-f]{40}',src['commit']),'Identidad Git inválida')
            for f in src['archivos']:
                rel=f['ruta'];out=ruta_segura(stage,name+'/'+rel)
                result=subprocess.run(['git','show',src['commit']+':'+rel],cwd=repo,capture_output=True,check=False)
                exigir(result.returncode==0,'Commit/blob no disponible localmente: recuperar commits registrados antes de preparar fuentes')
                b=result.stdout
                exigir(len(b)==f['bytes'] and hashlib.sha256(b).hexdigest()==f['sha256'],'Blob distinto de la fuente fijada')
                out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(b);out.chmod(0o444)
        os.rename(stage,destino)
    return destino
