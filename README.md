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

## Diagnóstico de errores · fase 0 para revisión

La [fase 0](docs/diagnostico_fase0.md) prepara fuentes/compatibilidad, preguntas y selección de casos, y alcance temporal. [Evidencia](registro/diagnostico/fase0_verificacion.json):154 archivos fijados por commit,71,208 predicciones históricas verificadas,10 casos y10 controles;sin nuevos ajustes. Los procedimientos conservan sus versiones y estados. El ledger completo es local y regenerable;La [fase 1](docs/diagnostico_fase1.md) describe magnitud, dirección y persistencia de T08 OOF sobre estas fuentes, con respaldos separados; revisión humana pendiente.
La [fase 2](docs/diagnostico_fase2.md) cruza 51 series históricas con sus métodos/versiones, errores compartidos y soporte municipal. Conserva 138 parcelas, respaldos y controles fijados; ocho tablas y tres figuras, sin nuevos ajustes ni selección de ganador. Revisión humana pendiente.

## Diagnóstico de errores · fase3

Revisión local de mapas, curvas y calidad de los diez casos y sus controles, empezando por los cuatro fallos compartidos. [Informe](docs/diagnostico_fase3.md), [fichas en PDF](registro/diagnostico/fase3_fichas.pdf), [tablas y fuentes](registro/diagnostico/fase3/manifest.json) y [observación numérica T06](registro/diagnostico/fase3_observaciones_T06.json). Datos originales, particiones y predicciones conservados; no es un nuevo modelo ni una mejora de MAE demostrada.


## Diagnóstico de errores · fase 4

La [fase 4](docs/diagnostico_fase4.md) concilia las etiquetas originales, distingue escritura de precisión de medición y revisa factores locales no registrados. Las 197 identidades y las etiquetas de 71,208 evaluaciones históricas coinciden con el original. [Entrega numérica](registro/diagnostico/fase4/manifest.json), [14 hallazgos](registro/diagnostico/fase4_hallazgos.csv), [seis preguntas preparadas para FIRA](registro/diagnostico/fase4_preguntas_FIRA.csv) y [verificación](registro/diagnostico/fase4_verificacion.json). No se enviaron preguntas, corrigieron etiquetas ni entrenaron nuevos modelos; revisión independiente pendiente.
