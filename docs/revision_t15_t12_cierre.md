# T15 y T12 · estado de revisión y conciliación

16 de octubre de 2026. Revisión de Dani con apoyo técnico de Codex. Lectura de GitHub y comprobación local; no aprobación externa, publicación, comentario, merge ni edición de la rama ajena.

## Dictamen sobre T15

[PR21](https://github.com/danielalira20/AgroCebada-2026/pull/21) está OPEN/CLEAN, head `6f970d8b9dc40f99905c1afcf28230da1d6a13cd`, hacia dev. El paquete completo está publicado y la integridad se volvió a comprobar en Docker común sin ajustar modelos: 11 artefactos originales, 19 componentes del paquete, 821 fuentes fijadas/25 computacionales actuales. Su auditoría numérica de 554,410 controles publicada se conserva; esta revisión no vuelve a ejecutar la evaluación principal.

Jass figura como revisora solicitada, pero todavía no existe una revisión suya del HEAD actual en GitHub. Las revisiones anteriores de Daf/Migue son COMMENTED sobre `e152abb` (v2): se conservan como antecedentes, no como aprobación de la evaluación v3 ni de la publicación nueva. El último comentario de Migue pedía la comparación LOO de avisos; ese complemento ya está en PR21, sin retirarlo ni recalcularlo aquí.

La revisión que queda a Jass puede acotarse al HEAD publicado: coherencia H3/v3, selección y referencia sola, máscaras/poblaciones, regla principal e integridad de trazas/reportes. Los controles G/P/GP se cotejaron con T12 en la revisión previa: 4,140 OOF y 150 selecciones, diferencia máxima 8.88e-16. No se necesita repetir T15 para ese cotejo.

## T12: qué sigue pendiente

[PR24](https://github.com/danielalira20/AgroCebada-2026/pull/24), head `1331e4f90898e3b806c57f87e8fc296c4e1fc88a`, sigue apuntando a t15-centrado-municipal. El código y los números examinados son la misma versión de la revisión previa; no hay un nuevo commit de corrección. GitHub ahora lo marca DIRTY.

Se mantienen cinco observaciones de alcance/documentación para Jass:

1. Limitar las conclusiones a los modelos y atributos probados: el resultado no descarta todas las formas de modelo ni toda heterogeneidad real.
2. `init='zero'` sólo inicializa el boosting en cero. Los árboles posteriores pueden aprender una constante; la evaluación no queda invalidada, pero su mejora no puede atribuirse exclusivamente a nuevos atributos por esa opción.
3. El p≈0.047619 con 20 revueltos no sustituye los IC por celdas ni demuestra mejora útil; conservar las cautelas de dependencia espacial.
4. Aclarar barreras/revisión: el diseño exige revisión metodológica previa y el manifiesto la da por cumplida, mientras el informe la declara pendiente. Documentar qué se confirmó y cuándo, sin inferir ausencia de una autorización privada ni inventar una aprobación.
5. Actualizar la cronología: nuestra corrida T15 terminó antes de leer este PR/comentarios. Ya está publicada; no registrar retrospectivamente una exposición a este análisis anterior a aquella corrida.

Corregir estas explicaciones no exige rehacer todos los modelos. Cambiar un estimador, imponer una restricción nueva o añadir un control de calibración sí requeriría otro registro y repetir ajuste/selección del procedimiento afectado; no retocar OOF a mano. La revisión previa reprodujo el auditor T12 y las opciones externas gb elegidas en Mac, no toda su selección interna ni todas las permutaciones desde cero.

## Conflictos diagnosticados y solución preparada

Se usó `git merge-tree` sin cambiar el índice, el checkout ni fusionar. Ancestro común: `cc7d0ae`. Los conflictos actuales están sólo en:

| Bitácora | Filas T15 | Filas T12 | Unión propuesta | Entradas nuevas de T12 |
|---|---:|---:|---:|---|
| decisiones.csv |60|61|62|D_T12_001/002|
| experimentos.csv |22|29|30|E_T12_001 a E_T12_008|
| uso_ia.csv |57|58|59|IA_T12_001/002|

La unión por ID encuentra cero colisiones semánticas y conserva todas las filas de ambos lados; no requiere renumerar ni sustituir aportaciones. El resumen verificable está en [conciliacion_propuesta.json](../registro/t16_revision_mediana/conciliacion_propuesta.json). Las tres copias conciliadas están preparadas localmente para las versiones exactas indicadas. No se aplicaron a ninguna rama ajena ni a dev; si cambia algún HEAD hay que conciliarlas de nuevo, no copiar a ciegas estos CSV.

No se debe fusionar PR24 dentro de nuestra rama como atajo. El orden previsto, tras revisión y autorización, es integrar PR21 en dev y después actualizar la base/integración de PR24, conservando su revisión independiente. Esta nota no ejecuta ese orden ni declara los PR aprobados.

## Mensaje preparado para Jass

Jass, ya están en el PR21 los resultados completos de T15 y las instrucciones para auditarlos. El commit a revisar es 6f970d8. ¿Puedes comprobar v3/H3, las selecciones, las poblaciones y los reportes? Los controles G/P/GP coinciden con los tuyos; no hace falta repetir toda T15 para ese cotejo. De tu PR24 quedan precisiones de interpretación: limitar las conclusiones a los modelos probados, aclarar init=zero, el alcance del revuelto, el estado de revisión y la cronología. No encontré un error de cálculo que obligue a rehacer todo. También quedaron conflictos sólo en las tres bitácoras; ya comprobé una unión por ID que conserva todo sin renumerar. Tu PR sigue sobre la rama T15: mantengamos separada su integración a dev.

Mensaje preparado, no enviado. La revisión externa sigue pendiente.
