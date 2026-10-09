# T07 · Sincronización con dev y preparación del catálogo

## Actualización vigente · contrato T02 v2, 9 de octubre

Base dev identificada sigue 9d5861c. T04 local `43b7560` migra la referencia y
sus metadatos, pendiente de publicar y revisar. T07 comparte el código de contrato
sin fusionar esa entrega ni marcarla aceptada. Las dos tablas son bloqueantes;
los tres auxiliares quedan identificados como procedencia archivada.

Pasaron 132 pruebas. Ambas entregas se reprodujeron dos veces: ocho archivos
satélite y once completos, con idénticas cifras, calidad, roles y diccionarios.
Sólo cambia la identidad de las entradas y del código en inventario/manifiesto.
Los 1,182 contrastes climáticos independientes mantienen máximo 1.02e-13.
La tabla compartida permanece 197 × 52; el clima completo sólo en borrador local.

Bitácoras T07: 25 decisiones y 20 entradas IA, sin pérdidas ni IDs duplicados.
Evidencia: reports/t04_contrato_tablas_20261009/. La rama remota t05-relieve
apareció en la consulta del 9 de octubre; no se ha revisado ni integrado en esta
base ni en T07. La actualización anterior se conserva debajo como historia.


## Actualización vigente · dev 9d5861c

8 de octubre de 2026, posterior a la fusión del PR #10. Base actual:
`9d5861c81713f2022d9fb9d1952c1feeb236a2f8`. Merge local T07: `25247c7`.

### Problema que resuelve

El inventario y los documentos todavía identificaban la base anterior y el PR
#10 como pendiente. Ambas ramas añadieron registros IA al mismo lugar.

### Solución que implementa

Incorporar dev sin perder historial y conciliar uso_ia.csv por ID contra el
ancestro común. Se preservan IA014 y las cuatro entradas T07, sin renumerar.
Actualizar sólo la identidad de fuentes T07: el catálogo, la tabla común,
la calidad, el diccionario y el contrato conservan sus cifras y definiciones.

| Comprobación actual | Resultado |
|---|---|
| Conflicto del merge | Sólo uso_ia.csv; 18 registros conservados antes de registrar esta tarea |
| Bitácoras finales | 24 decisiones y 19 entradas IA; IDs únicos, campos CSV válidos |
| Reproducción | Dos salidas idénticas de ocho archivos y dos verificaciones aprobadas |
| Diferencia con entrega anterior | Sólo inventario y manifiesto; otros seis archivos idénticos |
| Universo y satélite | 197 IDs, 138 etiquetas, 59 ausentes y 8,668 valores conservados |
| Compatibilidad | 16 pruebas aprobadas de preparación/integración con T03 vigente |
| Originales | ZIP, proyectos QGIS, particiones T03 y clima compartido intactos |

T03 ya recoge D019: todas/sin_respaldo y referencia media_mun__resp_grupo;
la decisión corresponde a sin_respaldo. Se conserva el corte provisional y las
dos ventanas. No se recalcularon métricas T08 ni se cambiaron reglas en T07.
T04 actualizada (`842f4c4`) sigue en rama propia, pendiente de publicación
con autorización y revisión de Jass. Sus cinco huellas T02 coinciden con dev.
T05 continúa pendiente; registro/t07/ sigue sin clima ni relieve. Los borradores
climáticos anteriores se preservan como evidencia con su base original.

Evidencia local: reports/t04_t07_sincronizacion_dev_20261008/.

## Etapa anterior · base 11d9470

Lo siguiente conserva la revisión anterior; sus estados y cifras de bitácora
corresponden a ese momento. El estado vigente es el de la sección anterior.

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
