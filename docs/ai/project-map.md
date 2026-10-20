# Mapa de responsabilidades

Verificado: 2026-10-19, `efbb2dd`. Entradas CONFIRMED por los archivos referidos; detalle y referencias de línea en los informes vinculados.

| Área | Responsabilidad y conexión |
|---|---|
| `app/app.py` | Arranque, sesión, estilos, fuentes, cabecera, contexto y elección de vista. |
| `app/agrocebada_app/config.py` | Modelo, temporada, nombres y fuentes cartográficas. |
| `app/agrocebada_app/backend/rutas/` | Descubrimiento de fuentes locales y variables AGRO_*. |
| `app/agrocebada_app/backend/datos/` | Lectura y paquete compacto; elevaciones, experimentos y cifras exportables. |
| `app/agrocebada_app/backend/modelo/` | Estadístico municipal con respaldos; métricas y validación rápida LOO. |
| `app/agrocebada_app/backend/dominio/` | Confianza, rango, avisos, desglose, cartera, calculadora, bitácora, clima y verdor, evidencia y respuestas Cebi. Fase 1 añade planeador.py: referencia municipal y evaluación de cuenta, sin cambiar el estimador. Ver [fase 1](planeador/fase-1/README.md) y [auditoría inicial](auditoria-backend.md). |
| `app/agrocebada_app/backend/carga_segura/` | Validación CSV/ZIP y geometrías de datos propios. |
| `app/agrocebada_app/backend/ficha_pdf/` | Preparación y dibujo del PDF de parcela en memoria. |
| `app/agrocebada_app/frontend/estado/` | Caché, sesión y Contexto compartido por las vistas. Fase 1 añade estado planeador independiente de widgets y compatibilidad de claves. |
| `app/agrocebada_app/frontend/tema/`, `app/assets/css/` | HTML escapado, paleta, tablas y variantes claro/oscuro. |
| `app/agrocebada_app/frontend/componentes/` | Mapas, gráficas, descargas, paneles y presentaciones de validación/evidencia/método. |
| `app/agrocebada_app/frontend/vistas/` | Bienvenida; agricultor; siete pestañas del analista y datos propios. Ver [detalle](auditoria-frontend.md). |
| `app/herramientas/` | Empaquetado de datos, elevación, cifras y tabla de experimentos; ejecución manual, fuera del recorrido del usuario. |
| `app/datos_app/` | Paquete local ignorado por Git; no asumir contenido completo o entrega nube. |
| `app/datos_estaticos/` | Elevación y catálogo de experimentos preparados para consulta. |
| `app/tests/` | Scripts de comprobación de dominio y AppTest de Streamlit; no confundir con suite científica raíz. |
| `scripts/` | Contratos, extracción, evaluación, comparaciones y entrega T18. |
| `tests/` | Pruebas científicas/geoespaciales; algunas dependen de insumos locales. |
| `registro/` | Evidencia publicada: contratos, decisiones, particiones, métricas, predicciones y trazabilidad. |
| `docs/` | Procedimientos y revisiones científicas. Ver [mapa T01–T22](auditoria-investigacion.md). |
| `analisis/` | Investigación auxiliar de catálogo, soporte geoespacial, etiquetas y QGIS. |
| `context/` | Propuestas y antecedentes locales ignorados; la propuesta del planeador no es comportamiento implementado. |
| `data/`, `reports/` | Insumos y resultados locales ignorados; no forman parte automáticamente de un despliegue. |
| `Dockerfile`, `ejecutar.*` | Entorno reproducible científico y comprobación de datos. |
| `app/Dockerfile`, `app/.streamlit/config.toml` | Contenedor y configuración de la app. |
| `.github/` | Plantillas de issues/PR; no se encontró workflow de despliegue en el árbol inspeccionado. |

`.agent/` contiene los contratos y estado de esta auditoría, no lógica de producto. Los archivos locales previos `.pr-suggestions/` y `Claude outputs/` quedaron fuera de cualquier modificación.

Actualización fase 2 (CONFIRMED): `app/agrocebada_app/frontend/componentes/escenarios/` presenta tarjetas, equilibrio y orientación. El dominio común y la calculadora consumen los mismos datos; pruebas nuevas `test_escenarios.py` y `test_calculadora_visual.py`. Ver [entrega](planeador/fase-2/README.md).

Actualización fase 3 (CONFIRMED): `vistas/agricultor/consulta_rapida.py` presenta referencia municipal sin parcela; `vista.py` enruta y `estado/planeador.py` conserva controles/selección al cambiar de recorrido. Cobertura validada por `dominio/planeador.py`. Pruebas nuevas de municipios, estado, consulta y recorridos. [Entrega](planeador/fase-3/README.md).

Actualización fase 4 (CONFIRMED): `app/herramientas/verificar_planeador.py` agrupa regresión del planeador con logs/huellas, cwd app/ y salida no cero ante errores. Evidencia funcional, visual y manual de usuario en [fase 4](planeador/fase-4/README.md). Sin cambios a dominio científico ni bot.
