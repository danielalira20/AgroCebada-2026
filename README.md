# AgroCebada 2026

Repositorio de trabajo de Dani, Jass, Migue, Daf y Diego para estimar el rendimiento de cebada de las 59 parcelas reservadas y mostrar los resultados en una aplicación funcional.

La [pestaña «Plan unificado corregido»](https://docs.google.com/document/d/1G2-cyDyIHyaQsGjbdzdvvsU65rnc6Tc4SrnIZAoNynk/edit?tab=t.q0k09ka9rtmy) es la fuente de responsabilidades y decisiones. Las tareas vigentes son T01–T22. Las versiones anteriores sirven como antecedentes.

## Estado inicial

T01 está en curso. El repositorio contiene sólo el arranque común, un contrato de datos preliminar y una comprobación con datos de ejemplo. Aún faltan el catálogo de 197 parcelas, las particiones acordadas, los modelos, la aplicación y la reproducción cruzada en Mac y Windows. No se declara completo el entorno hasta fijar dependencias, ejecutar Docker y comprobar ambos tipos de equipo.

## Preparar el entorno

Se usará Python 3.12 para el proyecto. En Mac o Windows, con Python 3.12 instalado:

```sh
python -m venv .venv
```

Activar el entorno con `source .venv/bin/activate` en Mac o `.venv\Scripts\Activate.ps1` en PowerShell de Windows. Después:

```sh
python -m pip install -r requirements.txt
python scripts/verificar_entorno.py
```

La lista de dependencias contiene rangos provisionales. Antes de cerrar T01 se fijarán versiones exactas a partir de una instalación comprobada en Mac y Windows. No usar el resultado del proyecto si ambos equipos instalan versiones distintas sin registrarlas.

Con Docker instalado:

```sh
docker build -t agrocebada-entorno .
docker run --rm agrocebada-entorno
```

La imagen ejecuta una lectura de ráster en memoria y una intersección de polígonos sintéticos. No usa datos del concurso. Esta prueba sólo verifica el entorno geoespacial; no valida la extracción real, la evaluación ni los modelos.

## Datos y trabajo en equipo

Guardar el paquete original de FIRA fuera del repositorio o bajo `data/raw/` local, sin modificarlo. `data/` y `reports/` se excluyen de Git. Nadie une tablas por posición de fila: se conserva el identificador de parcela y se comprueban los conteos. El [contrato inicial](docs/contrato_datos.md) fija los campos comunes sin inventar valores ausentes.

Cada experimento deberá registrar entradas, versión, corte temporal, particiones, variables, parámetros, predicciones fuera de entrenamiento y resultados, incluso si no mejora. Los acuerdos y el uso de IA se anotan en `registro/`. Las tareas del documento se trasladarán a GitHub Issues con su ID, responsable, revisor, dependencia y evidencia.

La primera referencia global y municipal puede construirse tras T02–T03 sin esperar todos los bloques de clima y satélite. Las 59 etiquetas reservadas permanecen vacías en entrenamiento y validación.
