"""Regresión integrada del planeador; guarda logs y un manifiesto sin regenerar datos.

Desde la raíz: python app/herramientas/verificar_planeador.py
Cada ejecución crea su propia carpeta de evidencia. Requiere las dependencias de la app.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
import time

APP = Path(__file__).resolve().parents[1]
RAIZ = APP.parent
CASOS = (
    "tests/backend/test_planeador.py",
    "tests/backend/test_municipios_planeador.py",
    "tests/backend/test_escenarios.py",
    "tests/backend/test_calculadora.py",
    "tests/backend/test_rangos.py",
    "tests/backend/test_confianza.py",
    "tests/frontend/test_estado_planeador.py",
    "tests/frontend/test_estado_consulta.py",
    "tests/frontend/test_calculadora_base.py",
    "tests/frontend/test_calculadora_visual.py",
    "tests/frontend/test_consulta_rapida.py",
    "tests/frontend/test_recorridos_agricultor.py",
    "tests/frontend/test_tema.py",
    "tests/frontend/test_descargas_ficha.py",
    "tests/frontend/test_bitacora.py",
    "tests/frontend/test_app.py",
    "herramientas/verificar_base_planeador.py",
)
FUENTES = (
    "app.py", "agrocebada_app/backend/dominio/planeador.py",
    "agrocebada_app/frontend/estado/planeador.py", "agrocebada_app/frontend/estado/sesion.py",
    "agrocebada_app/frontend/tema/html.py", "agrocebada_app/frontend/componentes/escenarios/vista.py",
    "agrocebada_app/frontend/componentes/descargas/boton_ficha.py",
    "agrocebada_app/frontend/vistas/agricultor/calculadora.py",
    "agrocebada_app/frontend/vistas/agricultor/consulta_rapida.py",
    "agrocebada_app/frontend/vistas/agricultor/vista.py",
    "agrocebada_app/frontend/vistas/agricultor/verdor_clima.py",
    "assets/css/tema.css", "assets/css/claro.css", ".streamlit/config.toml", "requirements.txt",
    "agrocebada_app/config.py", "agrocebada_app/backend/dominio/calculadora.py",
    "agrocebada_app/backend/dominio/rangos.py", "agrocebada_app/backend/dominio/confianza.py",
    "agrocebada_app/backend/modelo/estimador.py", "agrocebada_app/backend/modelo/metricas.py",
)


def huella(ruta):
    return hashlib.sha256(ruta.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--salida", type=Path, default=RAIZ / "docs/ai/planeador/fase-4/evidencia/pruebas")
    parser.add_argument("--caso", action="append", choices=CASOS, help="Ejecuta sólo este caso; puede repetirse.")
    parser.add_argument("--timeout", type=int, default=300, help="Límite en segundos para cada script.")
    args = parser.parse_args()
    if args.timeout <= 0:
        parser.error("--timeout debe ser positivo")
    inicio = datetime.now(timezone.utc)
    salida = args.salida.resolve() / inicio.strftime("%Y%m%dT%H%M%S%fZ")
    salida.mkdir(parents=True)
    temporal = salida / "temporales"
    temporal.mkdir()
    casos = args.caso or CASOS
    versionados = tuple(dict.fromkeys((*FUENTES, *casos, "herramientas/verificar_planeador.py")))
    huellas = {str(p): huella(APP / p) for p in versionados}
    informe = {
        "inicio_utc": inicio.isoformat(), "python": sys.version, "plataforma": platform.platform(),
        "directorio_ejecucion": str(APP),
        "fuentes_sha256": huellas, "base_sha256": huella(RAIZ / "docs/ai/planeador/fase-0/base.json"),
        "completa": False, "resultado": "EN_CURSO", "casos": [],
    }
    manifiesto = salida / "resultado.json"

    def guardar():
        manifiesto.write_text(json.dumps(informe, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    guardar()
    print(f"Evidencia: {salida}", flush=True)
    lanzador = ("import runpy,sys,tempfile; tempfile.tempdir=sys.argv[1]; "
                "sys.argv=sys.argv[2:]; runpy.run_path(sys.argv[0],run_name='__main__')")
    for i, caso in enumerate(casos, 1):
        log = salida / f"{i:02d}-{Path(caso).stem}.log"
        reloj = time.monotonic()
        print(f"[{i}/{len(casos)}] {caso}", flush=True)
        with log.open("w", encoding="utf-8") as archivo:
            try:
                proceso = subprocess.run(
                    [sys.executable, "-B", "-X", "utf8", "-c", lanzador, str(temporal), str(APP / caso)],
                    cwd=APP, stdout=archivo, stderr=subprocess.STDOUT, timeout=args.timeout, check=False,
                )
                codigo = proceso.returncode
            except subprocess.TimeoutExpired:
                archivo.write(f"\nERROR: tiempo agotado ({args.timeout} s).\n")
                codigo = 124
            except OSError as exc:
                archivo.write(f"\nERROR al ejecutar: {exc}\n")
                codigo = 125
        informe["casos"].append({"script": caso, "codigo": codigo, "log": log.name,
                                  "segundos": round(time.monotonic() - reloj, 3)})
        guardar()
        print("  OK" if codigo == 0 else f"  ERROR ({codigo})", flush=True)
    informe["completa"] = True
    informe["fuentes_estables"] = all(huella(APP / p) == valor for p, valor in huellas.items())
    informe["base_estable"] = huella(RAIZ / "docs/ai/planeador/fase-0/base.json") == informe["base_sha256"]
    aprobado = (all(c["codigo"] == 0 for c in informe["casos"])
                and informe["fuentes_estables"] and informe["base_estable"])
    informe.update(resultado="OK" if aprobado else "ERROR", fin_utc=datetime.now(timezone.utc).isoformat())
    guardar()
    print(f"{informe['resultado']}: {manifiesto}", flush=True)
    return 0 if aprobado else 1


if __name__ == "__main__":
    raise SystemExit(main())
