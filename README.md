# AgroCebada 2026

Repositorio de trabajo de Dani, Jass, Migue, Daf y Diego para estimar el rendimiento de cebada de las 59 parcelas reservadas y mostrar los resultados en una aplicación funcional.

La [pestaña «Plan unificado corregido»](https://docs.google.com/document/d/1G2-cyDyIHyaQsGjbdzdvvsU65rnc6Tc4SrnIZAoNynk/edit?tab=t.q0k09ka9rtmy) es la fuente de responsabilidades y decisiones. Las tareas vigentes son T01–T22. Las versiones anteriores sirven como antecedentes.

## Estado de trabajo

T01 sigue en curso: falta cerrar la verificación del equipo completo. T03 está integrado y en revisión. T04 tiene 28,368 registros históricos; Jass informó una validación independiente del cálculo. El PR 6 está abierto hacia `dev`. Esta actualización incorpora las correcciones de entrega autorizadas por Dani para el PR y pendientes de nueva revisión de Jass: [tabla mensual compartida y conciliación T02](docs/t04_entrega_equipo.md), [diccionario de columnas](docs/t04_diccionario_columnas.md) y [versión/disponibilidad temporal](docs/t04_version_disponibilidad.md). La tabla compacta conserva todos los valores y puede verificarse sin el ZIP ni Docker. T04 sigue en revisión; disponibilidad histórica y ventanas de integración siguen pendientes de acuerdo. El [informe de extracción completa](docs/t04_fase3_completa.md) y la [fase 2 con QGIS](docs/t04_fase2.md) conservan la evidencia anterior.

## Preparar el entorno

Se usará Python 3.12 para el proyecto. Comprobar que `python3.12 --version` funciona en Mac o que `py -3.12 --version` funciona en Windows; si falta, instalar Python 3.12 antes de continuar. En Mac con Homebrew puede usarse `brew install python@3.12`. Crear el entorno:

```text
Mac:     python3.12 -m venv .venv
Windows: py -3.12 -m venv .venv
```

Activar el entorno con `source .venv/bin/activate` en Mac o `.\.venv\Scripts\Activate.ps1` en PowerShell de Windows. Después:

```sh
python -m pip install --only-binary=:all: -r requirements.txt
python -m pip check
python scripts/verificar_entorno.py --salida reports/entorno_dani.json
```

Sustituir `dani` en el nombre del archivo por quien ejecuta la prueba. Las dependencias están fijadas para el entorno mínimo. Mac Intel usa Rasterio 1.4.3; Apple Silicon, Windows y Docker usan 1.4.4, según los paquetes binarios disponibles. Los paquetes fijados para Apple Silicon requieren macOS 14 o posterior. La salida identifica Python, sistema, arquitectura y versiones. `reports/` se crea localmente y Git lo excluye. Cada integrante debe comprobar su equipo; Diego repite la instalación desde una copia nueva y revisa la evidencia. Una instalación correcta en Mac no demuestra que Windows funcione.

Con Docker instalado y en ejecución:

```sh
docker build -t agrocebada-entorno .
docker run --rm agrocebada-entorno
```

En Mac, si se usa Docker CLI con Colima, iniciar primero el motor con `colima start --vm-type vz`. Al terminar puede liberarse memoria con `colima stop`. Si se usa Docker Desktop, abrir la aplicación antes de ejecutar los comandos anteriores.

La imagen ejecuta seis comprobaciones sintéticas: ponderación entre celdas, `NoData`, borde, ausencia de cobertura y CRS incompatible. No usa datos del concurso. Esta prueba sólo verifica el entorno geoespacial; no valida la extracción real, la evaluación ni los modelos.

Para cerrar T01 se necesitan las salidas aprobadas en los cinco equipos, una ejecución Docker en Mac y otra en Windows, acceso comprobado al repositorio para los cinco, capitán registrado y la revisión independiente de Diego. Registrar fallos y soluciones en la tarea T01 antes de marcarla completa.

## Ejecutar con Docker (entorno común)

Para que todo el equipo obtenga los mismos resultados en Mac y Windows, las tareas se ejecutan dentro de la imagen `agrocebada-entorno` con la carpeta del proyecto montada. La imagen tiene Python 3.12.15, las librerías de `requirements.txt`, `git` y lectura de texto en UTF-8. Los datos no van dentro de la imagen: se leen de `data/` local.

**Una sola vez por equipo (sólo si ya tenías el repositorio clonado en Windows antes de esta versión).** El repositorio fija fin de línea LF en `.gitattributes`. No cambia ningún archivo del repositorio: sólo decide cómo se descargan en cada equipo. Un clon nuevo ya descarga con LF y no necesita este paso. Si tu copia es anterior, hay que volver a descargar los archivos para que queden con LF. Este paso **borra los cambios locales sin commit**, así que el bloque primero comprueba con `git status --porcelain` que no haya nada sin guardar y, si lo hay, se detiene sin tocar nada (guarda antes con commit o `git stash`):

```sh
# Mac o Git Bash
if [ -n "$(git status --porcelain)" ]; then
  echo "Hay cambios sin commit: guárdalos (commit o git stash) antes de continuar"
else
  git pull
  git rm --cached -r . -q
  git reset --hard
  git ls-files --eol | grep "w/crlf"     # sólo debe aparecer registro/t04/clima_parcela_mes.csv
fi
```

```powershell
# PowerShell
if (git status --porcelain) {
  "Hay cambios sin commit: guárdalos (commit o git stash) antes de continuar"
} else {
  git pull
  git rm --cached -r . -q
  git reset --hard
  git ls-files --eol | Select-String "w/crlf"     # sólo debe aparecer registro/t04/clima_parcela_mes.csv
}
```

**Ejecutar.** Desde la raíz del repositorio:

```text
Windows (PowerShell):  .\ejecutar.ps1 [--amd64] [comando]
Mac o Git Bash:        ./ejecutar.sh  [--amd64] [comando]
```

Cada llamada construye la imagen (con caché), comprueba los datos con `scripts/comprobar_datos.py` y ejecuta el comando. Sin comando corre las pruebas (`python -m unittest discover -s tests`). La comprobación exige que `data/raw/DataSet.zip` tenga la huella registrada por T04 y que cada archivo extraído en `data/raw/DATASET_RETO_AGRO_2026` sea idéntico a su original del ZIP; si no, se detiene. **Sin datos locales** (ni el ZIP ni la carpeta extraída) no se detiene: imprime `AVISO: datos originales NO comprobados` y continúa, porque las pruebas y las tareas que sólo leen `registro/` no los necesitan; las tareas que sí leen el dataset fallarán por su cuenta. Si hay carpeta extraída pero falta el ZIP, sí se detiene, porque esos datos no se pueden verificar. Si Windows bloquea scripts: `powershell -ExecutionPolicy Bypass -File .\ejecutar.ps1 …`.

`--amd64` fija la plataforma `linux/amd64`. En Mac con chip Apple corre emulado (con Colima: `colima start --vm-type vz --vz-rosetta`). Se usa para comparar resultados byte a byte entre equipos y para T18 y T21. En el trabajo diario puede omitirse: entre procesadores ARM y x86 algunos decimales difieren en la última cifra (del orden de 1e-15), dentro de las tolerancias de los verificadores.

Al registrar una ejecución de pruebas, anotar el commit, el entorno, el total observado y el resultado. Los conteos de las bitácoras y de `registro/uso_ia.csv` describen ejecuciones históricas, no el tamaño permanente de la suite.

**Reproducir cada tarea.** Los comandos van después de `.\ejecutar.ps1` o `./ejecutar.sh`:

| Tarea | Comando | Resultado esperado |
|---|---|---|
| T01 | `docker run --rm agrocebada-entorno` | Seis comprobaciones aprobadas |
| Pruebas | (sin comando) | Todas las pruebas descubiertas terminan en `OK`; el total depende del commit |
| T02 | `bash -c "for s in 'construir_catalogo.py --datos data/DATASET_RETO_AGRO_2026' cruzar_contorno_y_rendimiento.py senalar_parcelas_extremas.py 'diagnosticar_soporte.py --datos data/DATASET_RETO_AGRO_2026' 'comparar_con_soporte_t03.py --datos data/DATASET_RETO_AGRO_2026' comparar_tablas_con_referencia.py; do python analisis/auditoria_catalogo_y_etiquetas/scripts/`$s || exit 1; done"` | «16 iguales … 0 distintas»; `git status` sin cambios |
| T03 | `python scripts/t03_evaluacion.py --datos data/raw/DATASET_RETO_AGRO_2026` | `git status` sin cambios en `registro/t03` |
| T04 | `python scripts/preparar_entrega_clima.py --verificar registro/t04` | `"resultado": "aprobado"` |
| T05 | `python -m scripts.t05_relieve --verificar registro/t05 --reproducir --dataset data/DATASET_RETO_AGRO_2026` | `"reproduccion": "aprobada"` |
| T06 | `python scripts/t06_satelite.py --datos data/raw/DATASET_RETO_AGRO_2026` | `git status`: sólo cambia la figura PNG (revisar a ojo y restaurar con `git restore registro/t06/figura_curvas_6_parcelas.png`) |
| T07 | Pasos de [docs/t07_fase_4_5.md](docs/t07_fase_4_5.md) con salida nueva en `reports/` | 13 archivos idénticos a `registro/t07` |

T02 requiere la copia `data/DATASET_RETO_AGRO_2026` (ver `analisis/auditoria_catalogo_y_etiquetas/README.md`). En Mac/Git Bash, en el comando de T02 quitar el acento grave antes de `$s` (en PowerShell evita que se interprete la variable). T03, T02 y T06 sobrescriben sus archivos publicados: después de ejecutarlas, `git status` debe quedar sin cambios (salvo la figura de T06). Si algo cambia, se registra como hallazgo; nunca se hace commit de una salida distinta sólo para que coincida.

La regeneración completa de T04 desde los mapas (`scripts/extraer_clima.py --completa` y `preparar_entrega_clima.py`) reproduce los valores con diferencias de hasta 1e-13 en `media_ponderada` y 4e-16 en `cobertura_valida`: la entrega publicada se generó en un procesador ARM. Su procedencia registra además el código de la extracción original. El verificador de T04 y la tabla de T07 usan la entrega publicada.

**Reglas del equipo (propuestas en la decisión `D_ENT_001` de `registro/decisiones.csv`; quedan vigentes cuando se apruebe este PR).** Toda revisión de PR que reproduzca resultados se corre con estos scripts. En Windows no se ejecutan tareas con Python nativo: algunas lecturas dependen de la codificación del sistema y sólo Docker garantiza UTF-8. T18 y T21 se ejecutan con `--amd64`. Alternativas descartadas y condiciones para reabrir están en la decisión.

## Datos y trabajo en equipo

El orden inmediato y las responsabilidades de Dani están en [tareas de Dani](docs/tareas_dani.md). T04 empieza con el inventario reproducible del ZIP original mediante `scripts/inventariar_clima.py`; el comando y su alcance están documentados allí. Sus pruebas se ejecutan con `python -m unittest discover -s tests -v` en el entorno local.

Guardar el paquete original de FIRA fuera del repositorio o bajo `data/raw/` local, sin modificarlo. `data/` y `reports/` se excluyen de Git. La tabla derivada mensual compacta de T04 y su procedencia se comparten en `registro/t04/`, según el acuerdo del equipo; los originales y el detalle por celda siguen locales. Nadie une tablas por posición de fila: se conserva el identificador de parcela y se comprueban los conteos. El [contrato inicial](docs/contrato_datos.md) fija los campos comunes sin inventar valores ausentes.

Cada experimento deberá registrar entradas, versión, corte temporal, particiones, variables, parámetros, predicciones fuera de entrenamiento y resultados, incluso si no mejora. Los acuerdos y el uso de IA se anotan en `registro/`. Las tareas del documento se trasladarán a GitHub Issues con su ID, responsable, revisor, dependencia y evidencia.

La primera referencia global y municipal puede construirse tras T02–T03 sin esperar todos los bloques de clima y satélite. Las 59 etiquetas reservadas permanecen vacías en entrenamiento y validación.

## T07: catálogo y ventanas climáticas

T07 conserva 197 parcelas, 138 etiquetas originales y 59 ausentes.
`registro/t07/` contiene la tabla común completa de 197 filas y 60 columnas:
catálogo, seis variables climáticas por ventanas, 44 columnas T06 y dos
candidatas de relieve T05. Conserva 138 etiquetas originales y 59 vacías,
con calidad separada, diccionario de columnas, contrato de roles y huellas.
Jass revisó el PR14. Las [correcciones locales 1–5](docs/t07_correcciones_pr14.md)
atienden compatibilidad Windows, grupo de referencia/evaluación y calidad
climática por ventana, área candidata de T10 y calidad por parcela para T03 bis.
Las correcciones se integraron en `dev` por el PR14 el 11 de octubre de 2026
(02:59 UTC). El manifiesto conserva el estado histórico de su ejecución.
El [complemento de fichas de atributos](docs/t07_fichas_atributos.md), en
`registro/t07_fichas/`, amplía disponibilidad y requisitos futuros; tiene revisión propia pendiente.
Consultar el [contrato](docs/t07_contrato.md), los
[antecedentes de fases 0–2](docs/t07_fases_0_2.md), la
[integración inicial por ventanas](docs/t07_fase_3.md) y la
[entrega completa y pasos de reproducción](docs/t07_fase_4_5.md).
Los borradores anteriores permanecen en `reports/` con su procedencia histórica.
La integración T07 ya está en `dev`; las columnas candidatas no son entradas
automáticas de un modelo. El nuevo complemento documental no inicia T09 ni el
diagnóstico estadístico de atributos.
