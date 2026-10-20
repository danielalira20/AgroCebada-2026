# Evidencia de cierre de fase 0

Fecha: 19 de octubre de 2026. Archivos locales, sin servicios externos ni ejecución de Streamlit. Base Git: `efbb2dd3c82b254550232f42e1ff7b1c51c351c0`, rama `feature/agriultor-prediccion`.

## Captura y resultados

`base.json` se creó una sola vez, con protección contra sobrescritura y JSON estricto (sin NaN/Infinity). Captura UTC: `2026-10-19T23:47:04.890880+00:00` (17:47 del 19 de octubre en Ciudad de México).

SHA-256 de la base congelada: `04688c4bb1694fdad14f7c5534126d0232cdfb5ca9bd44241c0e80d8c663a2e3`.

Entorno observado en esta fase: Python 3.12.14, NumPy 2.5.4, pandas 3.0.6, GeoPandas 1.2.0. Es el entorno local, no una reproducción del Docker científico. Las versiones se registran como procedencia, no se modifica ninguna dependencia ni se exige el mismo sistema operativo para comparar valores dentro de tolerancia.

| Comprobación | Resultado observado |
|---|---|
| Población del paquete | 197 filas: 138 ENTRENAMIENTO, 59 PREDICCION; 9 municipios. |
| Media municipal | 59 predicciones; A/sin respaldo MAE `0.32048971038707874`, R² `0.6585767448496691`. |
| Mediana municipal | 59 predicciones; A/sin respaldo MAE `0.3125851851851852`, R² `0.6612225271174903`. |
| Validación | Cuatro poblaciones por modelo: A/B × sin respaldo/todas. No se reentrenó ni reconstruyó la evaluación científica; se leyeron sus OOF existentes. |
| Contexto | Clima/soporte disponibles; normal climática/calidad ausentes en el paquete activo. Se registraron explícitamente dos ausencias entre once rutas. |
| Cuentas | Nueve municipios por cada modelo, con supuestos ilustrativos comunes; no se capturaron precios reales de un productor. |
| Verificador positivo | Ejecutado contra base: código 0, mensaje OK. Predicciones, métricas, confianza, rangos, cuentas y huellas coinciden. |

## Controles negativos ejecutados

Se hicieron copias profundas en memoria de la base y se comprobó que el verificador detecta:

1. Modificar +0.1 t/ha la primera predicción oficial.
2. Cambiar el modelo oficial declarado de mediana a media.
3. Declarar ausente la fuente de parcelas que sí está presente (mismatch de presencia/huella).
4. Cambiar el total declarado de parcelas de 197 a 196.

También se comprobó tolerancia de una perturbación de 1e−14, rechazo de bool donde se esperaba número, detección de campo faltante y rechazo de comparaciones NaN/Infinity como iguales. Las mutaciones no se guardaron ni alteraron fuentes; no se desplazó ni borró un dato para simular ausencia.

Se ejecutó el CLI con una ruta de base inexistente: retornó 1 y `NO VERIFICADO`, en lugar de aprobar o crear una base nueva. Se verificó además que la base original conserva exactamente sus bytes tras las comprobaciones.

Comprobación final: el verificador también terminó en código 0 ejecutándolo desde `app/`, confirmando que sus ubicaciones no dependen de la carpeta de trabajo. Sintaxis Python, JSON, enlaces Markdown locales y SHA-256 de la base comprobados; no existe aún el módulo de funcionalidad `backend/dominio/planeador.py`. El diff de fuentes de producto, datos, configuración y pruebas existentes permaneció vacío.

Inspección de imports del nuevo archivo: no importa frontend, Streamlit ni módulos de Cebi. Las huellas de fuentes tampoco incluyen archivos del bot, CSS o recursos de mascota; cambiar esos archivos o realizar un commit paralelo no invalida por sí mismo la base. Si el cambio paralelo altera una fuente numérica compartida, sí debe detectarse.

## Revisión del alcance

La única adición bajo `app/` es `herramientas/verificar_base_planeador.py`. Es una herramienta de lectura y comparación, sin opción de captura/regeneración. Los demás archivos de esta fase son contratos, base y memoria de operación. No se cambió el estimador, el modelo seleccionado, una fuente de datos, T18, la calculadora de usuario, una vista, configuración, dependencia o prueba existente. No se tocaron archivos de Cebi.

Se preservaron `.pr-suggestions/`, `Claude outputs/` y documentos previos de auditoría; se actualizaron sólo índices/estado y la anotación del plan vigente. No hubo commit, cambio de rama, publicación ni envío externo.

## No verificado en esta fase

- No se repitió AppTest: el bloqueo de inicialización documentado en [la auditoría](../../environments.md) no cambió por estos archivos. No se declara aprobada una interfaz ni una regresión visual.
- No se ejecutó Docker ni suite científica completa; esta herramienta verifica resultados publicados y entradas activas, no certifica el protocolo científico desde cero.
- No se verificó aprobación humana T16 ni se corrigió el formato/huella histórica de T18. Capturar una huella nueva no resuelve esa discrepancia.
- No se implementaron contratos futuros, UI nueva, transiciones de widgets ni integración con el bot. Deben verificarse en la fase que los implemente.

Resultado de fase 0: **contratos y base listos para fase 1**, con aprobación metodológica, procedencia histórica, verificación visual e integración del bot delimitadas como pendientes separados.
