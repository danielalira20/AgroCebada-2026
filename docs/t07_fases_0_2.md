# T07 · Catálogo sincronizado y bloques pendientes

Documento histórico de fases 0–2 sobre base 11d9470. Para el estado vigente,
ver [sincronización](t07_sincronizacion.md) y [entrega completa de fases 4–5](t07_fase_4_5.md).
Desde el 10 de octubre, catálogo, clima, satélite y relieve están integrados;
la revisión de T07 por Jass sigue pendiente. Los estados y comandos siguientes
describen la etapa anterior.

Responsable: Dani. Revisora: Jass. Estado actualizado el 8 de octubre de 2026.

## Problema que resuelve

T07 debe avanzar sin confundir una entrega provisional con el clima revisado.
No hace falta fabricar observaciones ni rellenar columnas para reservar un bloque.

## Solución que implementa

Se comparte el catálogo real de la base actual y se registra T04 como pendiente_integracion_revisada.
El agregador climático queda preparado, pero rechaza entradas marcadas en revisión.
La aceptación debe proceder de la revisión humana; cambiar una marca no la sustituye.

## Estado por fase

- Fase 0: base dev 11d947098d8d6e56902a7f09a2c75953f09fdb21 identificada.
  T02 corregida, T04 mensual, T06 y T08 están integradas en dev. La referencia
  T02 de T04 tiene actualización local pendiente de publicar/revisar. T05 no
  tiene entrega identificada; T06 se inventaría, todavía sin unir a T07.
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
  --base-dev 11d947098d8d6e56902a7f09a2c75953f09fdb21 \
  --salida reports/t07_catalogo_nueva_ejecucion

.venv/bin/python -m unittest discover -s tests -v
```

En Windows usar .venv\Scripts\python.exe como ejecutable equivalente.
La salida debe ser nueva; no se sobrescriben originales. Docker no es necesario.
La rama sincronizada pasó 97 pruebas: 68 del proyecto/T04 y 29 de T07.
Incluyen la ausencia total de T04 en modo catálogo y el rechazo de T04 provisional. Los ejemplos artificiales de pruebas unitarias
sólo viven en carpetas temporales; no alimentan las tablas del proyecto.

## Antes de integrar el clima

Publicar/revisar la actualización T04 en su propia rama; después identificar la
base aceptada, comprobar referencias compatibles T02/T04 y
revisar unidades, agregación y disponibilidad. Sólo entonces ejecutar ventanas
abr_oct/jun_oct con datos reales, revalidar y compartir los resultados.
La lluvia se suma; Tmin/Tmax se promedian por días. NoData no equivale a cero.
Las siguientes fases integrarán T06 y T05 por ID. No se entrenan modelos ni se
elige ventana en esta entrega. Guías y nuevas fuentes mantienen los hitos del
contrato; no se añadieron productos externos.

Skills privadas T07/T04 y las cuatro científicas apoyan el trabajo; su referencia
está documentada en docs/t07_contrato.md. Skills y AGENTS.md quedan fuera de Git.

La [sincronización del 8 de octubre](t07_sincronizacion.md) registra base,
conciliación de bitácoras, reproducción y pendientes de integración.
