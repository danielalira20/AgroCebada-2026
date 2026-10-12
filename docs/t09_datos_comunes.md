# Preparación de T09 · datos locales y aclaraciones de Tab 8

Fecha: 11-oct-2026. Responsable: Dani. Trabajo autorizado: puntos 1 y 3 del
plan de continuación. El acuerdo experimental con Migue y el entrenamiento
de T09 siguen pendientes.

## Problema que resuelve

El comando Docker común de Jass rechazaba nuestra copia local: faltaban las
subcarpetas de los cuatro ZIP y dos archivos ZIP tenían auxiliares de QGIS
añadidos. Tab 8 también mezclaba cifras de ventanas distintas y referencias
históricas que debían distinguirse de resultados reproducidos.

## Solución que implementa

La carpeta raw anterior se conservó completa como respaldo de visualización.
Se colocó en su ruta habitual una copia fiel del paquete, con la estructura
que exige el comprobador común. `DataSet.zip`, las tablas T07, las particiones,
la copia de visualización y ambos proyectos QGIS de Dani conservaron sus
huellas. No se modificaron cálculos, etiquetas ni el diseño de T09.

```text
data/
├── raw/
│   ├── DataSet.zip                      # maestro intacto
│   └── DATASET_RETO_AGRO_2026/          # 166 archivos verificados
│       ├── [CSV y documentos originales]
│       ├── Parcelas_Reto_AGC_CONJUNTO_70_30.zip
│       ├── Parcelas_Reto_AGC_CONJUNTO_70_30/
│       ├── Reto_AgroCebada_CHIRPS_Precipitacion_2022_2025.zip
│       ├── Reto_AgroCebada_CHIRPS_Precipitacion_2022_2025/
│       ├── Reto_AgroCebada_Temperatura_2022_2025_RECORTADA_CHIRPS.zip
│       ├── Reto_AgroCebada_Temperatura_2022_2025_RECORTADA_CHIRPS/
│       ├── Reto_AgroCebada_Topografia_INEGI_CEM4.zip
│       └── Reto_AgroCebada_Topografia_INEGI_CEM4/
└── processed/qgis/
    ├── DATASET_RETO_AGRO_2026/          # visualización actual, intacta
    └── historico_raw_20261011/          # nueve archivos anteriores, idénticos
reports/
├── t04_revision.qgz                    # sesión histórica, intacta
└── t04_revision_trabajo.qgz            # continuar QGIS en éste
```

Cada ZIP interno se descomprime dentro de una carpeta con el nombre del ZIP
sin extensión; conserva sus rutas internas. Por ejemplo, lluvia tiene la
carpeta contenedora `Reto_AgroCebada_CHIRPS_Precipitacion_2022_2025` y, dentro,
la carpeta del mismo nombre que ya traía el archivo. Esto es la estructura
literal que verifica `scripts/comprobar_datos.py` de la configuración de Jass.
No aplanar esos nombres sin acordar un cambio del comprobador.

La sesión de trabajo apunta a `data/processed/qgis`, por lo que sus cuatro
fuentes permanecen válidas. Para evitar que estadísticas de QGIS vuelvan a
modificar los ZIP de raw, seguir usando `reports/t04_revision_trabajo.qgz`.
El proyecto histórico permanece como referencia. Los proyectos de Jass que
apuntan a sus propias rutas no fueron adaptados como parte de este trabajo.

## Comprobación del punto 1

- `DataSet.zip` conserva SHA-256
  `d74dbaba1764e026da8ce38f7f3476f80523f479a6c141827887e09326061bb5`, el de T04.
- **166 archivos** de la carpeta actual coinciden con el contenido del paquete
  y de sus ZIP internos; **cero archivos adicionales**.
- El mismo comprobador de Jass pasó en Python local y en Docker común
  **linux/amd64**, esta vez sobre la carpeta real del proyecto.
- **170 archivos protegidos** mantienen sus huellas, incluida la visualización,
  la entrega T07, las particiones y los proyectos QGIS. Las cuatro fuentes de
  la sesión de trabajo existen y pertenecen a la copia de visualización.
- Los nueve archivos de la copia raw anterior se conservaron completos en
  el respaldo; la sustitución tenía reversión ante fallo.

Esta comprobación reemplaza el pendiente de adecuación local identificado en
la [revisión Docker](t09_revision_docker_comun.md). Sus intentos y manifiestos
anteriores conservan el estado histórico; no se reescriben como aprobados.
La configuración Docker usada es la publicada por Jass en
`feature/configracion-docker`, commit `87467c7`; el uso aquí no equivale a
fusionar esa rama ni a afirmar que los lanzadores ya están en nuestra rama.

## Aclaraciones del punto 3

Se editó únicamente **Tab 8** del documento común, conservando las tablas
nativas y comprobando que las otras siete pestañas no cambiaron:

1. La tabla original se identifica como **abr_oct**; se añadieron sus
   equivalentes **jun_oct** y se aclaró que `clima_zona.py` calcula ambas.
   No se eligió una ventana ganadora.
2. Se retiró **p=0.81** como resultado confirmado de KS. Se documentó
   `D=0.139401`, `p nominal=0.355929`, con población, columna y método,
   además de las limitaciones de empates y dependencia espacial.
3. La respuesta de FIRA se describe como documentación del muestreo, no
   garantía de equivalencia ni de desempeño futuro.
4. Se distinguieron las **siete** parcelas de la regla T02 actual de las
   **nueve** de la auditoría anterior, con los casos AGC_048 y AGC_069.
   Se precisó media de las demás parcelas, en lugar de mediana.

Se guardó un respaldo de Tab 8 antes de editar y una copia de la lectura final
verificada en la carpeta de salida privada de esta conversación.

## Evidencia y siguiente paso

`reports/ajustes_raw_tab8_20261011/antes.json`, `validacion_raw.json` y
`comprobacion_raw_docker.json` identifican el respaldo, las huellas y el control.
Datos, respaldo y reportes permanecen fuera de Git; AGENTS y skills son privados.
Docker se apagó al terminar. No hubo push, merge ni mensajes a compañeros.

Los puntos 1 y 3 están resueltos dentro del alcance autorizado. Lo siguiente
es acordar con Migue la propuesta de T09 y después implementar sus modelos y
evaluación; esta preparación no los entrena ni los aprueba.
