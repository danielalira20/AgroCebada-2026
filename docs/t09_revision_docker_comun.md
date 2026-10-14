# T09 · reproducción del diagnóstico en Docker común

Fecha: 11-oct-2026. Responsable: Dani. Revisión humana: Migue, pendiente.
Actualización posterior: la carpeta raw actual ya pasó el comprobador común;
ver [adecuación local y aclaraciones de Tab 8](t09_datos_comunes.md).
La reproducción local del diagnóstico se completa con una ejecución Linux
x86_64; no implica aprobación de la configuración Docker ni de un modelo T09.

## Problema que resuelve

Tab 8 citaba p=0.81 para KS de área y nueve parcelas extremas, mientras que el
diagnóstico actual obtenía p=0.355929 y siete. Era necesario distinguir diferencias
de entorno de cambios de referencia, archivos y reglas.

## Solución que implementa

Se construyó la imagen con el Dockerfile y requirements exactos de la rama
`feature/configracion-docker` publicada por Jass, commit
`87467c7d9833474ff19753d87390efe88cbea82e`, usando la opción común de comparación
`linux/amd64`. La rama de configuración no se incorporó a la rama del diagnóstico.
Código ejecutado: `4402490`, con fuentes montadas en lectura y resultados en
`reports/`. En la base usada, la configuración todavía no estaba integrada en dev.

Imagen: `sha256:f47077f5bfdd4e6e05d17b8c5056bcbb79498f277ab5d38fee117a0bab5221f5`.
Python 3.12.15; Linux x86_64; NumPy 2.2.6; pandas 3.0.6; SciPy 1.18.1.
El Dockerfile, requirements, imagen, código, pruebas y salidas quedan identificados
en `reports/t09_docker_comun_20261011/`.

## Resultado numérico

- Las seis comprobaciones básicas del entorno se aprobaron.
- Pasaron las **26 pruebas relevantes** del diagnóstico y las fichas de atributos.
  Las 266 pruebas de la primera entrega corresponden a Mac; no se afirma que
  aquí se ejecutó otra vez toda la suite.
- Dos ejecuciones completas en Docker dieron ocho CSV y manifiesto idénticos.
- Frente a Mac, **siete CSV son idénticos byte a byte**. El octavo,
  `pearson_entradas_etiquetadas.csv`, sólo difiere en Pearson global en un máximo
  de `1.0000030317702802e-14`. Las claves, tamaños, ausencias y textos coinciden.
  Se aplicó el criterio de comparación fijado antes de ejecutar:
  tolerancia relativa 1e-10 y absoluta 1e-12 para los agregados numéricos.
- No se seleccionaron entradas ni se entrenaron modelos. La diferencia descrita
  no se utilizó para escoger variables, umbrales o resultados.

## KS: 0.355929 se confirma; 0.81 sigue sin fuente identificada

El cálculo bilateral por defecto de `scipy.stats.ks_2samp` produjo exactamente
lo mismo en Mac y Docker: `D=0.139400638663719`, `p=0.35592922053260273`.
Se reprodujo sobre tres representaciones de los mismos datos:

| Fuente | Columna de área | Poblaciones | p nominal |
|---|---|---|---:|
| T07 | area_ha_origen | 138/59 | 0.355929220533 |
| T03 | area_ha | 138/59 | 0.355929220533 |
| CSV original del paquete | AREA_HA | 138/59 | 0.355929220533 |

Por tanto, esta discrepancia no se explica por ejecutar Mac en vez de Linux.
No se identificó el archivo, población o comando que produjo p=0.81; Dani
confirmó que Jass no se lo indicó. No se atribuye un error a un cálculo
desconocido: el valor se conserva como no verificado hasta recuperar su fuente.

Estos p-valores se obtuvieron únicamente para auditar la cifra citada. Las
limitaciones de empates y dependencia espacial continúan: no se usan como
prueba de equivalencia o como criterio para aceptar el modelo.

## Siete frente a nueve: la explicación ya estaba en T02

Se ejecutó el cálculo de T02 de Jass dejando fuera cada parcela de la media
municipal: siete superan estrictamente 1 t/ha; tres municipios tienen una sola
etiqueta y no pueden tener referencia local de las demás. Los siete IDs
coinciden exactamente con `desviacion_municipal_por_parcela.csv` de Jass.

La [bitácora de T02](../analisis/auditoria_catalogo_y_etiquetas/bitacora.md)
ya explicaba, en «Parcelas extremas (etapa 6)», la diferencia con una auditoría
anterior que había enumerado nueve:

- **AGC_048:** única etiquetada de Nanacamilpa. La auditoría anterior usó otra
  referencia; la regla actual no tiene otras parcelas del municipio para comparar.
- **AGC_069:** desviación actual `+0.9967142857142859` t/ha, inferior al umbral
  estricto de 1. El redondeo publicado a tres decimales es +0.997.

Así, nueve es un antecedente de otra auditoría; siete es el resultado de la
regla T02 actual. Tab 8 debe distinguir el antecedente de la definición vigente.
El reporte del diagnóstico anterior dejaba ese origen pendiente; esta lectura
lo identifica y cierra la aclaración del conteo. Ninguna lista autoriza exclusión.

## Problema real de la copia local y cómo se comprobó

El nuevo verificador de Jass comprobó que `DataSet.zip` conserva la huella
aceptada por T04, pero rechazó la carpeta local descomprimida por dos razones:

1. Faltan cuatro subcarpetas de descompresión que exige su comando común.
2. Los ZIP locales de precipitación y temperatura contienen tres miembros
   adicionales `.tif.aux.xml`, asociados a las capas de julio que se visualizaron
   en QGIS. No falta ni cambió ningún miembro original de esos ZIP; **ningún
   TIFF original es distinto**. Se compararon sus huellas internas, no sólo
   las huellas del contenedor ZIP.

Esto cambia la identidad de las copias de los ZIP y hace fallar legítimamente
el control de identidad exacta. No cambia los valores de los mapas originales.
T04 utiliza el paquete `DataSet.zip` identificado y T09 consume la tabla T07
verificada; no se tomaron esas copias de visualización como nuevos originales.

Para la comprobación se creó **una copia nueva de los datos reales**, extraída
desde DataSet.zip en `reports/t09_docker_comun_20261011/datos_originales_verificados/`.
El verificador común aprobó el paquete y esa copia completa. La carpeta local
anterior, el proyecto QGIS y los originales se conservaron. El fallo inicial
también quedó registrado; no se presenta la carpeta local anterior como aprobada.

Antes de usar sin excepciones `ejecutar.sh` o `ejecutar.ps1` del equipo, queda
pendiente alinear la carpeta raw con la estructura e identidad exigidas y
mantener visualización en una copia separada. Esa adecuación no se ejecutó
silenciosamente como parte de esta reproducción.

El primer intento de montar el verificador temporal también falló porque
Colima no compartía esa ruta. Se copió el verificador a la carpeta accesible de
reportes y se repitió. Ambos intentos fallidos se conservan separados de la
ejecución final aprobada.

## Evidencia y continuidad

En `reports/t09_docker_comun_20261011/`:

- `resultado_docker.json`: pruebas, comparación Mac/Docker, KS, siete IDs y casos.
- `procedencia_docker.json`: imagen, configuración, código y prueba básica.
- `datos_originales.json`, `auditoria_copias_zip.json` y
  `fallo_estructura_local.txt`: alcance de comprobación y diferencias de las copias.
- `docker_1/` y `docker_2/`: salidas nuevas; no reemplazan evidencia local anterior.
- `config_comun/revisar_diagnostico.py`: verificador de esta revisión, con los
  archivos de configuración exactos usados para construir la imagen.
- `pruebas_docker.log`, `ejecucion_docker.log` y `construccion_amd64.log`.

Los manifiestos previos conservan el estado documental de su generación,
incluido el pendiente de Docker. La evidencia de esta comprobación adicional
es el resultado y la procedencia externos citados aquí; no se reescriben
manifiestos históricos para simular otra ejecución o aprobación humana.

Docker se detuvo al terminar para liberar memoria. No hubo push, merge,
contacto con compañeros ni cambios a los originales. T09 sigue en preparación:
la reproducción respalda el diagnóstico; el diseño y su revisión con Migue
continúan pendientes.
