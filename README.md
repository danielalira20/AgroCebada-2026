# AgroCebada 2026

Repositorio de trabajo de Dani, Jass, Migue, Daf y Diego para estimar el rendimiento de cebada de las 59 parcelas reservadas y mostrar los resultados en una aplicación funcional.

La [pestaña «Plan unificado corregido»](https://docs.google.com/document/d/1G2-cyDyIHyaQsGjbdzdvvsU65rnc6Tc4SrnIZAoNynk/edit?tab=t.q0k09ka9rtmy) es la fuente de responsabilidades y decisiones. Las tareas vigentes son T01–T22. Las versiones anteriores sirven como antecedentes.

## Estado inicial

T01 está en curso. El repositorio contiene sólo el arranque común, un contrato de datos preliminar y una comprobación con datos de ejemplo. Aún faltan el catálogo de 197 parcelas, las particiones acordadas, los modelos, la aplicación y la reproducción cruzada en Mac y Windows. No se declara completo el entorno hasta fijar dependencias, ejecutar Docker y comprobar ambos tipos de equipo.

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

Guardar el paquete original de FIRA fuera del repositorio o bajo `data/raw/` local, sin modificarlo. `data/` y `reports/` se excluyen de Git. Nadie une tablas por posición de fila: se conserva el identificador de parcela y se comprueban los conteos. El [contrato inicial](docs/contrato_datos.md) fija los campos comunes sin inventar valores ausentes.

Cada experimento deberá registrar entradas, versión, corte temporal, particiones, variables, parámetros, predicciones fuera de entrenamiento y resultados, incluso si no mejora. Los acuerdos y el uso de IA se anotan en `registro/`. Las tareas del documento se trasladarán a GitHub Issues con su ID, responsable, revisor, dependencia y evidencia.

La primera referencia global y municipal puede construirse tras T02–T03 sin esperar todos los bloques de clima y satélite. Las 59 etiquetas reservadas permanecen vacías en entrenamiento y validación.

## T07: catálogo y ventanas climáticas

El catálogo de T07 conserva las 197 parcelas, las 138 etiquetas y las 59
ausentes. `registro/t07/` comparte sólo catálogo, diccionario e identidad/estado
de bloques; T04 está pendiente de entrega revisada, sin valores de relleno.
Consultar el [contrato](docs/t07_contrato.md) y los
[pasos de reproducción](docs/t07_fases_0_2.md). La fase 2 tiene código preparado,
pero requiere la entrega definitiva para calcular e integrar clima. T05 y la
unión de T06 quedan para las siguientes fases. T07 permanece en revisión.
