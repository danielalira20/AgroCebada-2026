# T04 · Actualización de referencia T02 y revalidación

8 de octubre de 2026. Rama local: `t04-actualizar-referencia-t02`.
Base: `dev` en `11d947098d8d6e56902a7f09a2c75953f09fdb21`, que integra T02 corregida por el PR #9.
Responsable: Dani. Revisora: Jass. Cambio preparado localmente; publicación y revisión de esta actualización pendientes.

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
El PR #10 del protocolo T03 sigue separado de esta corrección.
