# AgroCebada 2026

- [T15: evaluación completa, resultados y auditoría del 16-oct](docs/t15_resultados.md) · [paquete para revisión](registro/t15_resultados/README.md)

**Estado T15 al 16-oct:** evaluación principal completa sobre `cc7d0ae`, con 12,420 OOF y auditoría de 554,410 comprobaciones. Ningún bloque cumple la promoción; se conserva la referencia. Las notas históricas que siguen explican la preparación previa y no sustituyen este resultado. No hay predicciones finales de las 59 ni ganador T16. Esta publicación no fusiona el PR21 en `dev`.

- [T15: contexto LOO de alertas en las 138 frente a las 59](docs/t15_observacion_migue_loo.md)
- [Revisión PR22: protocolo, cifras comprobadas y precisiones pendientes](docs/revision_pr22_protocolo.md)

- [T15: guía de revisión del PR #21 — método v3, propuesta B y aplicabilidad C](docs/t15_guia_revision_pr21.md)

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

## T09: evaluación climática para revisión

El [diseño](docs/t09_diseno.md) y los [componentes verificados](docs/t09_estimadores.md) se ejecutaron con las 138 etiquetas de 2025. El [informe con gráficas](docs/t09_evaluacion.md) compara referencia territorial, clima solo, municipio + clima y corrección residual en A/B/C. Ningún procedimiento climático cumple la promoción en A; T sigue como base para T15. [Estado y evidencia](registro/t09/evaluacion.json), OOF principales y tablas compactas están en `registro/t09/`; el diccionario explica unidades y vacíos.

Dos ejecuciones Docker reproducen exactamente 15 CSV y 3 JSON; los verificadores independientes reconstruyen métricas y matrices. Pasan 324 pruebas Mac y 84 controles Docker. La revisión de Migue sigue pendiente; T16/T18 aún deben elegir y ajustar el procedimiento final para las 59. No se evaluaron sus etiquetas ni se generó una entrega definitiva. Docker se detuvo al terminar.

### T09 · corrección H3, pasos 1 y 2 · 13 de octubre de 2026

El [diseño R centrado v2](docs/t09_R_centrado_v2.md) y su componente de entrenamiento/predicción se prepararon en `t09-centrado-municipal`. La corrección usa desviaciones respecto al centro municipal del entrenamiento, con respaldo de grupo/global, conservando la escala global. `crear_estimador("R_centrado")` identifica la variante nueva; `R` sigue reproduciendo v1. Pasan 41 pruebas de componentes en Mac y Docker. Evaluación completa v2, revisión independiente, publicación y actualización de T15 pendientes. Los resultados originales de `registro/t09/` y sus fuentes permanecen intactos.


## T09: reevaluación de R centrado · 13 de octubre de 2026

Los controles y la evaluación completa de R_centrado v2 están verificados técnicamente, pendientes de revisión de Migue. La corrección de H3 no supera la referencia municipal en MAE ni cumple la regla de mejora. Se preservan los resultados v1 y las59 reservadas. Consulta [diseño, resultados, incidencias y reproducción](docs/t09_centrado_evaluacion_v2.md) y la [entrega versionada](registro/t09/centrado_v2/verificacion.json). T15 y la actualización de otros consumidores siguen pendientes; no se modificaron con esta entrega.

## Preparación de comparación común T15/T16

El [procedimiento común histórico v1](docs/evaluacion_comun.md) fija familia, selección interna, regularización y reglas para comparar bloques. El [registro](docs/evaluacion_comun_registro.md) limita búsquedas y explicita atributos/ventanas. [Evidencia técnica](registro/evaluacion_comun/verificacion.json):294 pruebas Mac,41Docker y41conPython optimizado. Está preparado para revisión Daf/Migue; no se ejecutó la evaluación completa nueva ni se eligió ganadorT16.

El verificador `python -m scripts.evaluacion_comun_contrato` comprueba datos,particiones yreferencia sin ajustar estimadores. Mantiene T09/T11/T14 como procedimientos históricos.


## Revisión y coordinación para T15 · 13 de octubre

[Revisión T10/T11 reproducida](docs/revision_T10_T11_20261013.md) y [propuesta concreta T15](docs/t15_comparaciones_propuestas.md). Solicitudes a Daf y Migue enviadas; conformidad metodológica pendiente. La propuesta JSON no es ejecutable hasta cerrar el acuerdo y registrarlo antes de correr. T09 y los históricos conservan sus ramas y resultados.

[Alternativas para reducir MAE](docs/alternativas_MAE_20261013.md): investigación de modelos, curvas existentes, suelo y clima diario. Hipótesis priorizadas, sin nuevos datos o evaluaciones incorporados.

### Corrección H3 en el procedimiento común · para revisión

La [versión centrada v2](docs/evaluacion_comun_centrado_v2.md) resta centros aprendidos sólo en entrenamiento a todas las variables transformadas, incluido el indicador D020. Conserva datos y búsqueda; la propuesta T15 sigue pendiente y no ejecutable. [Evidencia propia](registro/evaluacion_comun/verificacion_centrado_v2.json): controles matemáticos por bloques, prevención de filtraciones e identidad de versión. Los históricos permanecen identificados como tales.

## T15 · fase A: coherencia y versiones · 14 de octubre de 2026

La [entrega local de fase A](docs/t15_fase_a_coherencia.md) identifica dev actualizado y conserva los históricos. El [método LOO v3](docs/evaluacion_comun_centrado_loo_v3.md) alinea referencia residual y centro por fila, incluidos respaldos de municipios pequeños, y añade frecuencia explícita de referencia sola. Verificado en Mac y Docker; revisión del nuevo código pendiente. La propuesta sigue no ejecutable: no se ejecutó T15 completo ni se produjeron las 59 finales. T06/T03 conservan pendientes concretos de sus responsables.


## T15: planificación B y aplicabilidad C

[B documental](docs/t15_fase_b_documental.md) conserva las ocho comparaciones y separa las extensiones propuestas; sigue sin habilitar entrenamientos. [C descriptiva](docs/diagnostico_aplicabilidad59.md) entrega soporte de las59 reservadas por territorio, atributos y calidad, con errores históricos T08 como contexto, reproducción Mac/Docker y revisión humana pendiente.

Las tablas compactas están en `registro/diagnostico/aplicabilidad59/`. El detalle OOF se genera localmente en `data/processed/`; las instrucciones del informe conservan destinos nuevos. No son nuevas predicciones ni sustituyen T16/T18.

## Contrato de comparaciones T15 · 15 de octubre

El [contrato de comparaciones y pruebas](docs/t15_contrato_comparaciones.md) fija las ocho comparaciones, las fuentes y los criterios de v3, añade trazas por ajuste y registra aparte las extensiones. La [verificación técnica](registro/t15_contrato/verificacion.json) conserva la evidencia Mac/Docker. Cierre técnico local para revisión; no se ha ejecutado T15 completa ni se ha seleccionado un ganador.

## Ejecutor T15 y cierre operativo con Dani

El [ejecutor T15](docs/t15_ejecutor.md) completa las selecciones, trazas y reportes del contrato. El [registro operativo](registro/t15_contrato/registro_operativo_v1.json) recoge la decisión de Dani de continuar sin esperar revisiones externas; conserva el método y las ocho comparaciones. La [verificación](registro/t15_contrato/verificacion_ejecutor.json) acredita 64 pruebas en Mac/Docker y comprobaciones limitadas. La evaluación completa requiere una solicitud posterior y confirmación explícita; no se ha ejecutado.

## T15 · evaluación completa publicada · 16 de octubre de 2026

El [informe final de la corrida](docs/t15_resultados.md) y el [paquete completo](registro/t15_resultados/README.md) reúnen predicciones OOF, 400 selecciones con puntuaciones, métricas, contrastes, desgloses y todas las trazas/estados comprimidos sin pérdida. La auditoría separada verifica H3, particiones y cálculos; puede repetirse sin reentrenar mediante `python -O scripts/t15_auditar_entrega.py --salida reports/t15_revision_nueva/auditoria.json`.

Principal A/sin_respaldo: referencia MAE 0.320490 t/ha, RMSE medio por repetición 0.492593 y R² medio por repetición 0.658577 (135 parcelas). La mínima reducción puntual, GP −0.000300 t/ha, no satisface la regla. A/todas y B tienen denominadores distintos; se publican por separado. E1/Q y otras extensiones siguen pendientes; no se ampliaron las comparaciones tras mirar resultados.

## T15 · extensión E1/Q evaluada · 16 de octubre de 2026

El [informe E1/Q](docs/t15_e1_evaluacion.md) y su [entrega completa](registro/t15_e1_evaluacion/README.md) cierran la comparación registrada: MAE principal E1 0.321531 frente a referencia 0.320490 t/ha; no promueve. El control de disponibilidad y la sensibilidad del ancla están separados. Son resultados locales de esta rama, pendientes de publicación; los estados anteriores de planificación se conservan como historia. No cambia la referencia, T03/T07 ni las 59 finales.

La [factibilidad INEGI](docs/t15_inegi_factibilidad.md) confirma acceso y cobertura de las 197 parcelas con el CEM3.0 de 15 m. El original local de unos 29 MB queda ignorado por Git; el registro comparte QA y procedencia. Faltan contrato técnico E2, extracción y evaluación de su aporte, con límites de datum y disponibilidad histórica explícitos.
