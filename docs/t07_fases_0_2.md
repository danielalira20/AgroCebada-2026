# T07 · Catálogo preparado y clima pendiente

Responsable: Dani. Revisora: Jass. Estado actualizado el 7 de octubre de 2026.

## Problema que resuelve

T07 debe avanzar sin confundir una entrega provisional con el clima revisado.
No hace falta fabricar observaciones ni rellenar columnas para reservar un bloque.

## Solución que implementa

Se comparte el catálogo real y se registra T04 como pendiente_entrega_revisada.
El agregador climático queda preparado, pero rechaza entradas marcadas en revisión.
La aceptación debe proceder de la revisión humana; cambiar una marca no la sustituye.

## Estado por fase

- Fase 0: base dev 540193d6cdc48c90b4b361e6044ae52f9d6f9b0a identificada.
  T02 requiere sus correcciones; T04 espera la entrega revisada; T05 no tiene
  entrega identificada en esta base; T06 se inventaría, todavía sin unir a T07.
- Fase 1: catálogo de 197 IDs, 138 etiquetas conservadas y 59 ausentes.
  Diccionario de las ocho columnas del catálogo, con roles y significado del vacío.
- Fase 2: código y contrato de ventanas preparados. Cálculo e integración con
  la entrega definitiva pendientes; no se considera esta fase terminada.

## Archivos compartidos ahora

registro/t07/ contiene catalogo_base.csv, diccionario_columnas.csv,
inventario_fuentes.json, controles.json y manifest.json.
No contiene tablas climáticas, valores simulados o filas de relleno.
El espacio para T04 es su estado en el inventario, no una tabla ficticia.

La ejecución anterior utilizó datos reales de la versión provisional bfd8184 de
T04. Sus tablas, evidencia y documentación se retiraron de la entrega actual y
se conservaron bajo reports/t07_20261007/, ignorado por Git. No son resultados
vigentes para modelar ni evidencia de aceptación de T04.

## Reproducir el catálogo sin clima

Desde la raíz, con el entorno existente del proyecto:

```sh
.venv/bin/python scripts/t07_preparar.py --sin-clima \
  --base-dev 540193d6cdc48c90b4b361e6044ae52f9d6f9b0a \
  --salida reports/t07_catalogo_nueva_ejecucion

.venv/bin/python -m unittest discover -s tests -v
```

En Windows usar .venv\Scripts\python.exe como ejecutable equivalente.
La salida debe ser nueva; no se sobrescriben originales. Docker no es necesario.
Las 29 pruebas pasan, incluidas la ausencia total de T04 en modo catálogo y
el rechazo de T04 provisional. Los ejemplos artificiales de pruebas unitarias
sólo viven en carpetas temporales; no alimentan las tablas del proyecto.

## Cuando llegue la entrega revisada

Identificar la revisión aceptada, comprobar referencias compatibles T02/T04 y
revisar unidades, agregación y disponibilidad. Sólo entonces ejecutar ventanas
abr_oct/jun_oct con datos reales, revalidar y compartir los resultados.
La lluvia se suma; Tmin/Tmax se promedian por días. NoData no equivale a cero.
Las siguientes fases integrarán T06 y T05 por ID. No se entrenan modelos ni se
elige ventana en esta entrega. Guías y nuevas fuentes mantienen los hitos del
contrato; no se añadieron productos externos.

Skills privadas T07/T04 y las cuatro científicas apoyan el trabajo; su referencia
está documentada en docs/t07_contrato.md. Skills y AGENTS.md quedan fuera de Git.
