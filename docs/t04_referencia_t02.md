# T04 · Actualización de referencia T02 y revalidación

8 de octubre de 2026. Rama local: `t04-actualizar-referencia-t02`.
Base de revalidación y referencia T02: `11d947098d8d6e56902a7f09a2c75953f09fdb21`, que integra la T02 corregida por el PR #9.
Base actual del PR: dev `9d5861c81713f2022d9fb9d1952c1feeb236a2f8`, incorporada mediante merge local `9347017`.
Responsable: Dani. Revisora: Jass. PR #11 publicado; Jass revisó la versión 842f4c4 sin correcciones obligatorias.
La mejora del contrato descrita abajo se prepara localmente el 9 de octubre y requiere publicación y revisión del nuevo cambio.

## Corrección inicial · evidencia del 8 de octubre

Las secciones siguientes conservan la primera revalidación, anterior a separar
compatibilidad y procedencia. La política vigente está en la sección final.

## Problema que resuelve

La entrega T04 integrada por el PR #6 identifica T02 en `eef8d95ae47d45d877d5a32f769ad01dec2c92fc`.
Tras integrar las correcciones T02, cambiaron las huellas de `huellas_archivos_leidos.csv`,
`construir_catalogo.py` y `diagnosticar_soporte.py`. El catálogo y la tabla de soporte
permanecen idénticos. El control de identidad rechaza la referencia anterior;
sin actualizar y revalidar no puede reproducirse la conciliación sobre la base común.

## Solución que implementa

Regenerar `registro/referencia_t02_t04.json` desde los cinco archivos T02 de la base
identificada, mediante `referencia_desde_tablas`. Se conservan los ocho campos
espaciales de las 197 parcelas, las definiciones y las huellas de los originales.
No se leen etiquetas para esta actualización ni se cambian métodos o tolerancias.

Reejecutar el piloto y la extracción completa desde el maestro; preparar y verificar
una entrega compacta nueva antes de actualizar los metadatos compartidos.
`conciliacion_t02.json` ahora identifica la base vigente y registra «tablas locales
verificadas». `procedencia.json` conserva código, entorno, mapas, geometrías y
soportes; sólo cambia la huella de `requirements.txt`, que en dev incorpora T06.
El manifiesto actualiza las huellas de procedencia, conciliación y ejecución fuente.
El CSV climático y `controles.json` permanecen idénticos byte a byte.

## Evidencia

| Comprobación | Resultado |
|---|---|
| Referencia anterior sobre la T02 nueva | Rechazo esperado; no publica carpeta de resultados |
| Referencia nueva | 197 filas espaciales y originales idénticos; tres huellas actualizadas |
| Pruebas del proyecto en la rama T04 | 68 aprobadas |
| Piloto | 135 filas; conciliación verificada |
| Extracción completa | 144 mapas, dos cuadrículas, 394 soportes, 28,368 filas |
| Comparación con la entrega integrada | 28,368 filas × 11 columnas iguales; CSV y controles idénticos |
| Error relativo máximo de contraste de área | 4.618416202523308e-8; límite T04 1e-6 conservado |
| Entrega compacta | Verificador aprobado también con Python `-S` |
| Archivos protegidos | Maestro, proyectos QGIS y particiones T03 intactos |

La evidencia local queda en `reports/t04_referencia_t02_20261008/` y la nueva
extracción en `data/processed/t04/referencia_t02_20261008/`; ambas rutas se ignoran.
La extracción y la revisión independiente anteriores se conservan. Estos controles
nuevos corresponden a Dani/Codex y no se atribuyen a Jass.

## Reproducir

Usar nombres de salida nuevos; la ruta de extracción debe estar bajo
`data/processed/t04/`, como exige el extractor. En Windows sustituir
`.venv/bin/python` por `.venv\Scripts\python.exe`.

```sh
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python scripts/extraer_clima.py --paquete data/raw/DataSet.zip --salida data/processed/t04/referencia_t02_nueva/piloto --piloto
.venv/bin/python scripts/extraer_clima.py --paquete data/raw/DataSet.zip --salida data/processed/t04/referencia_t02_nueva/completa --completa
.venv/bin/python scripts/preparar_entrega_clima.py --origen data/processed/t04/referencia_t02_nueva/completa --salida reports/t04_referencia_t02_nueva --corte 2025-10-31
.venv/bin/python -S scripts/preparar_entrega_clima.py --verificar reports/t04_referencia_t02_nueva
```

El equipo puede verificar la entrega compartida con
`python scripts/preparar_entrega_clima.py --verificar registro/t04`, sin el maestro
ni Docker. Esa verificación comprueba el paquete; no vuelve a extraer los mapas.

## Alcance y pendientes

No se cambian valores climáticos, calendario, etiquetas, particiones ni reglas T03.
No se agregan ventanas, satélite o relieve a T07. El ajuste necesita publicación
con autorización de Dani y revisión de Jass antes de incorporarlo a dev.
El PR #10 de T03 ya está fusionado en la base actual y no forma parte del diff de esta corrección.

## Comprobación tras actualizar dev

La nueva base sólo modifica el protocolo T03 y añade IA014 a uso_ia.csv.
Los cinco archivos T02 identificados y el código/entradas T04 son idénticos a
la base revalidada. Se mantiene la referencia a 11d9470: identifica esa revisión
espacial comprobada y sigue siendo compatible con dev 9d5861c. No se cambia
una referencia ni se repite la extracción para actualizar sólo el nombre del commit.

El único conflicto del merge fue uso_ia.csv. Se resolvió por ID contra el ancestro,
conservando IA014 y nuestras entradas T04 sin renumerar ni perder contenido.
Tras el merge, los seis archivos de referencia/entrega corregidos mantuvieron
sus huellas. El CSV de 28,368 filas y los controles también coinciden byte a
byte con dev. Pasaron las 20 pruebas de entrega/conciliación y el verificador
con Python -S, sin ZIP ni Docker. La revalidación completa de 68 pruebas, piloto
y 144 mapas se conserva como evidencia previa porque ninguna entrada o función
de cálculo cambió. Evidencia nueva: reports/t04_t07_sincronizacion_dev_20261008/.

La revisión de Jass sigue pendiente. El PR propuesto apunta a dev y contiene
sólo los ocho archivos propios de esta corrección; no publica T07 ni originales.

## Mejora vigente · contrato de dos tablas, 9 de octubre

### Problema que resuelve

Jass observó en el PR #11 que las huellas de los scripts T02 hacían depender la
conciliación de cambios sin efecto en los datos. Un comentario disparaba una
actualización de referencia aun con las dos tablas idénticas. Dani autorizó
resolverlo ahora; no es un error de cálculo ni una mejora predictiva.

### Solución que implementa

scripts/t02_contrato.py fija un contrato común para T04 y T07. La referencia
nueva t04_referencia_t02_v2 conserva sólo catalogo_parcelas.csv y
soporte_por_parcela.csv en archivos_sha256. Las tres huellas auxiliares pasan
a procedencia_t02_sha256; identifican la revisión histórica documentada y no
exigen que los scripts actuales sigan iguales. Ambas tablas siguen requiriendo
igualdad byte a byte: este ajuste no omite cambios de datos o formato en ellas.

El lector también acepta la referencia v1 completa de cinco huellas y las
separa al leer, sin editar archivos de entregas anteriores. Rechaza versiones
contradictorias, archivos adicionales, huellas inválidas y contratos incompletos.
Los originales, los IDs y los ocho campos espaciales siguen comprobándose; las
tolerancias, cuadrículas, áreas, centroides y fórmulas climáticas no cambian.

### Comprobación y actualización de la entrega

Pasaron 72 pruebas T04, incluidas cuatro regresiones: comentarios/auxiliares
ausentes; cada tabla cambiada o faltante; lectura v1; contrato mal formado.
Se reconciliaron las 197 parcelas usando los 394 soportes ya verificados, tras
comprobar sus huellas e identidades contra las geometrías y cuadrículas del ZIP
original. El detalle y los máximos espaciales coinciden con la conciliación
anterior. CSV climático y controles son idénticos byte a byte y el verificador
Python -S aprueba las 28,368 filas.

Se actualizan la referencia y los tres metadatos de entrega. El código y las
huellas de la extracción original se conservan; actualizacion_referencia_t02
registra aparte la migración, su código y la entrega anterior. No se afirma que
la versión nueva del lector produjo los valores antiguos ni se repiten los 144
mapas sin una modificación de entradas o fórmulas que lo justifique.

Evidencia local: reports/t04_contrato_tablas_20261009/. La revisión anterior de
Jass corresponde a 842f4c4; este nuevo cambio debe presentarse para su revisión.
T07 necesita el mismo contrato antes de incorporar la entrega v2. El nuevo lote
no está publicado y no autoriza fusionar el PR ni cerrar T04/T07 automáticamente.
