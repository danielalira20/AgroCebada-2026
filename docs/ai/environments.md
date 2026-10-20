# Entornos y comprobaciones de esta auditoría

Verificado: 2026-10-19. Referencia `efbb2dd`; rama observada `feature/agriultor-prediccion`. No se cambió de rama ni se modificó un archivo de producto.

**Actualización fase 3 (CONFIRMED):** consulta de nueve municipios con confianza real, recorridos de producción/lector PDF y regresiones de cuentas/escenarios/tema/fichas OK en runtime autorizado. Base fase 0 intacta. [Evidencia y límites](planeador/fase-3/README.md). Inspección visual/teclado y Docker pendientes.

**Actualización fase 4 (CONFIRMED):** entorno de aceptación final con cwd app/, configuración nativa real y 17/17 scripts OK. Navegador actual cua_repl permitió localhost: 24 capturas finales, medidas de reflow/contraste y teclado; zoom 200% confirmado por el usuario. Los intentos anteriores desde raíz están separados como exploratorios. [Evidencia](planeador/fase-4/README.md). Docker/publicación y lector de pantalla real no certificados.

**Actualización posterior:** la [fase 1](planeador/fase-1/README.md) modifica calculadora/estado/lector PDF. Sus AppTest de integración, descargas y tema terminaron OK en un proceso local autorizado fuera del aislamiento que bloqueaba socketpair. Las limitaciones descritas abajo corresponden a las ejecuciones iniciales de auditoría, no a una imposibilidad general de probar esta copia. No se ejecutó navegador ni Docker.

**Actualización fase 2 (CONFIRMED):** pruebas nuevas de dominio/presentación, tarjetas con ambos temas, C3 sin clima y regresiones de cuenta/PDF/tema aprobadas en el mismo runtime autorizado. Base fase 0 conservada. Evidencia y limitaciones en [fase 2](planeador/fase-2/README.md). Inspección visual en navegador y Docker pendientes.

## Entornos que el repositorio define

| Entorno | Estado y evidencia |
|---|---|
| Investigación reproducible | CONFIRMED: Docker raíz usa Python 3.12.15 y requirements fijados; `ejecutar.ps1`/`ejecutar.sh` verifican datos y, sin comando, ejecutan `tests/`. No incluyen por ese hecho la suite `app/tests/`. `Dockerfile:1`, `:20`; `ejecutar.ps1:22`, `:29`. |
| Aplicación en contenedor | CONFIRMED: `app/Dockerfile:3` instala `app/requirements.txt`, usa usuario no root y arranca Streamlit en 8501. Datos se montan aparte según la documentación. No se construyó ni arrancó durante esta auditoría. |
| Aplicación local | CONFIRMED por imports: `.venv/Scripts/python.exe` tiene Python 3.12.14, Streamlit 1.65.0, pandas 3.0.6 y GeoPandas 1.2.0. No equivale al entorno Docker 3.12.15. |
| Publicación | UNKNOWN: README describe opciones y pendientes, no una instalación acreditada. `app/.streamlit/config.toml` existe dentro de app; al arrancar desde otra carpeta debe verificarse qué configuración se aplica. No se verificaron proveedores externos. |
| Automatización | CONFIRMED por inventario: `.github/` contiene plantillas de PR/issue, sin workflows inspeccionables en este checkout. No se halló IaC de nube en la búsqueda realizada. No prueba ausencia de procesos externos al repositorio. |

Variables de localización confirmadas en `backend/rutas/localizador.py:17`, `:28`, `:44`, `:63`: `AGRO_DATOS`, `AGRO_T03`, `AGRO_T04`, `AGRO_T07`, `AGRO_T08`, `AGRO_T18`. `AGRO_SIN_PAQUETE` evita paquete (`backend/datos/paquete.py:13`). Son ubicaciones/selección de fuentes; no se guardan valores de variables ni secretos en esta memoria.

## Datos realmente disponibles en esta copia

CONFIRMED mediante llamadas de sólo lectura a `paquete` y `predecir` con la configuración vigente:

- Paquete compacto activo: 197 filas, 138 ENTRENAMIENTO, 59 PREDICCION, 9 municipios.
- Las 59 predicciones actuales tienen fuente municipal. Ninguna ejercita grupo/global.
- `clima_normal()` devuelve `None`, y `calidad()` devuelve `None`. El paquete local no contiene sus Parquet; por la política de lectura no se recuperan desde originales mientras esté activo el paquete. La app contempla estados de falta de contexto.
- T18 se encontró por rutas del repositorio. Diferencia máxima entre predicción cruda y CSV final: `8.881784197001252e-16`; cuatro filas difieren a nivel binario de float, todas coinciden con tolerancia absoluta `1e-12` y a dos decimales. No es un desacuerdo de procedimiento.
- Integridad de bytes T18: SHA-256 local `4cbe214d056e79b8c81d890a0c27b078a2f78807c3b397f4027f366a8e712d7c`, 60 saltos LF y 0 CRLF; no coincide con el hash declarado para CRLF. El [informe de procedencia](auditoria-investigacion.md) documenta la comprobación en memoria sin alterar el archivo.

## Pruebas ejecutadas

Fecha de ejecución: 2026-10-19. Python local Windows anterior, sin modificar pruebas.

| Comprobación | Resultado observado |
|---|---|
| `app/tests/backend/test_calculadora.py` | OK; datos sintéticos y comprobaciones reales indicadas por el propio script. |
| `app/tests/backend/test_rangos.py` | OK después de ubicar temporales en `.agent/tmp`; primer intento bloqueado por permisos del temporal del entorno. |
| `app/tests/backend/test_confianza.py` | OK. |
| `app/tests/backend/test_bitacora.py` | OK; no significa que cubra las observaciones de identidad/año del informe. |
| `app/tests/backend/test_respuestas.py` | OK. |
| `app/tests/frontend/test_app.py` y `test_tema.py` | Intentados, sin resultado funcional: detenidos al comprobar bloqueo del runtime AppTest. No se reportan como aprobados ni como regresiones de la app. |
| AppTest mínimo con sólo `st.write(123)` | Bloqueo reproducido antes de evaluar funcionalidad: creación del event loop Windows → `socket._fallback_socketpair` → `accept`. Traza obtenida con límite de diagnóstico de 15 s en `.agent/test-runtime-diagnostico.log`. El proceso terminó por ese límite. |

El grupo de cuatro pruebas de backend emitió además un RuntimeWarning de división por cero en `modelo/metricas.py:13` con un caso de datos constantes; los cuatro scripts terminaron en OK. La fórmula de R² carece de tratamiento para varianza cero; no presentar ese caso como métrica finita sin revisar.

La ubicación temporal de trabajo sólo se configuró dentro del proceso de comprobación (`tempfile.tempdir`), sin cambiar configuración del sistema ni código del proyecto. Evidencia de los cuatro OK: `.agent/test-backend.log`. Las advertencias de AppTest se conservan en `.agent/test-app.log` y `.agent/test-tema.log`.

No hubo pruebas en Docker: no se encontró el comando Docker en el shell disponible. No se reejecutaron las pruebas científicas de raíz, no se regeneraron resultados ni se verificó la publicación. No se inspeccionó la interfaz en navegador: el inventario accesible sólo expuso el navegador integrado; no se abrió un servidor ni una pestaña de datos.

## Cómo continuar la validación en la implementación

PROPOSED: usar un entorno con `app/requirements.txt` y originales/paquete identificados, distinguir suite de app de suite científica y comprobar primero AppTest mínimo. Ejecutar regresiones relevantes una vez; después verificar visualmente ambos modos, temas, escritorio/móvil y navegación por teclado. No dar por cumplida la aceptación visual con AppTest o con contraste calculado de tokens.
