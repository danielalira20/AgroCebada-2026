# T07 · Sincronización con dev y preparación del catálogo

Actualización posterior del 8 de octubre: ver [fase 3](t07_fase_3.md).
Catálogo + T06 ya integrados; ventanas reales sólo en borrador local para
revisión. Este documento conserva la evidencia de la etapa anterior.

8 de octubre de 2026. Rama: `t07-tabla-comun`. Responsable: Dani. Revisora: Jass.
Base compartida incorporada: `11d947098d8d6e56902a7f09a2c75953f09fdb21`.
Merge local: `b615810a93727a990a71dbda36938b7a0c1d003b`.

## Problema que resuelve

T07 se había preparado desde dev `540193d`, antes de la entrega corregida T02 y
la integración de T04/T08. Su inventario conservaba esos estados históricos.
Ambas ramas añadieron entradas al final de las bitácoras; un merge textual no
podía elegir entre ellas sin perder registros.

## Solución que implementa

Incorporar el dev identificado a la rama T07 mediante un merge local, conservando
los ocho commits previos. Resolver las dos bitácoras por ID y comparación de
filas contra el ancestro común; conservar todas las entradas y cambios aceptados.
No se renumeraron IDs, pues los de T07 ya incluyen el nombre de la tarea.

IA003 tenía comas sin proteger en el campo producto del ancestro. Se comprobó
que nuestra corrección anterior era sólo formato CSV y se conservó el contenido
corregido de dev, que distingue especificación T03 de implementación T08.
Las bitácoras conciliadas tuvieron 21 decisiones y 15 registros IA; con la entrada
de esta sincronización quedan 22 y 16, sin duplicados y con ocho/nueve campos.

Regenerar sólo el catálogo real y sus metadatos desde esta base. El estado T02
pasa a `base_dev_identificada`, sin declarar correcciones pendientes como texto
fijo. El modo sin clima registra T04 como `pendiente_integracion_revisada` y
mantiene los controles de copia, aceptación declarada y compatibilidad de huellas.
No se generan tablas climáticas ni columnas de relleno.

## Evidencia

| Comprobación | Resultado |
|---|---|
| Historial | dev es ancestro de T07; ocho commits anteriores conservados |
| Conflictos | Sólo decisiones.csv y uso_ia.csv; ninguna entrada perdida |
| Catálogo/diccionario | Idénticos byte a byte a la preparación anterior |
| Universo | 197 IDs únicos; 138 etiquetas originales y 59 ausentes |
| Reproducción | Cinco archivos iguales entre dos salidas independientes |
| Pruebas | 97 aprobadas: 68 del proyecto/T04 y 29 T07 |
| Fuentes protegidas | DataSet.zip, proyectos QGIS y particiones T03 intactos |
| Privacidad | AGENTS.md, skills, data/ y reports/ fuera de Git |

La revisión de espacios conserva el CRLF del CSV climático recibido de dev;
no se normaliza ese archivo ni se alteran sus huellas. La evidencia local queda
en `reports/t07_sincronizacion_20261008/`. El inventario compartido no es una
aprobación científica de las entregas por el hecho de haberlas fusionado.

## Pendientes

La referencia T02 de T04 se actualizó y revalidó en una rama independiente,
`t04-actualizar-referencia-t02`, commit `7b2b4b4`. Ese commit no se incorpora
prematuramente a T07 ni se declara presente en dev. Falta autorización de
publicación, revisión de Jass e incorporación a dev; luego se actualizará T07.

T07 conserva catálogo y código de ventanas preparado. Aún no integra valores
climáticos, variables satelitales o relieve. Las siguientes fases trabajarán con
las entregas reales; T05 no aparece en la base identificada. El PR #10 de T03 está cerrado sin merge en la consulta posterior del 8 de octubre. No se entrenan modelos ni cambian reglas de selección.
