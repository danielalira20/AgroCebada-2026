# AgroCebada · índice de auditoría

Verificado: 19 de octubre de 2026 contra `efbb2dd` y cambios locales de fases 1–4. Planeador integrado y validado localmente: suite 17/17, revisión visual/teclado y confirmación del usuario al 200%. Fase 5/Cebi aplazados. No acredita despliegue, certificación WCAG integral ni aprobación científica de decisiones pendientes.

## Lectura recomendada

- **Trabajo más reciente:** [fase 4, integración y aceptación local](planeador/fase-4/README.md), con [matriz y evidencias](planeador/fase-4/matriz-aceptacion.md). Antecedentes: [fase 3](planeador/fase-3/README.md), [fase 2](planeador/fase-2/README.md), [fase 1](planeador/fase-1/README.md) y [contratos/base de fase 0](planeador/fase-0/README.md). Cebi continúa aplazado por instrucción humana.

1. [Dictamen y plan del planeador](planeador-campana-auditoria-y-plan.md): comparación C1–C7, correcciones, arquitectura propuesta, fases, tareas y criterios de aceptación.
2. [Auditoría de pantallas y UI/UX](auditoria-frontend.md): qué se muestra, controles, estados, estética, móvil y patrones a conservar.
3. [Auditoría de backend](auditoria-backend.md): fuentes, estimación, cálculos de dominio, carga segura, exportaciones y persistencia.
4. [Auditoría del repositorio científico](auditoria-investigacion.md): procedencia, T01–T22, validación y límites de la evidencia.
5. [Arquitectura y flujos](architecture.md), [mapa de responsabilidades](project-map.md), [entornos y comprobaciones](environments.md), [hallazgos y pendientes](investigation-log.md).

## Identidad del sistema

| Aspecto | Estado y evidencia |
|---|---|
| Propósito | CONFIRMED: estimación retrospectiva 2025 y consulta contextual para agricultor y analista; `app/app.py:1`, `app/agrocebada_app/frontend/tema/estilos.py:15`. |
| Runtime | CONFIRMED: Python 3.12.15 previsto por `app/Dockerfile:3`; Python local observado 3.12.14. |
| UI | CONFIRMED: Streamlit, pydeck, Altair y CSS; `app/requirements.txt:1`, `app/agrocebada_app/frontend/componentes/mapa/mapa.py:2`. |
| Datos | CONFIRMED: pandas/GeoPandas; paquete Parquet/CSV o fuentes del repo; `app/agrocebada_app/backend/datos/paquete.py:13`. |
| Modelo vigente en código | CONFIRMED: mediana municipal, respaldo grupo/global; `app/agrocebada_app/config.py:17`, `app/agrocebada_app/backend/modelo/estimador.py:10`. Aprobación metodológica: ver hallazgos. |
| Población local observada | CONFIRMED por lectura de paquete: 197 parcelas, 138 con etiqueta, 59 por estimar, 9 municipios. Comprobación de esta auditoría registrada en `environments.md`. |
| Base de datos de usuarios | UNKNOWN: no se halló un servicio persistente; las entradas revisadas usan sesión y archivos. No equivale a garantía sobre una instalación externa. |
| Publicación real | UNKNOWN: el repositorio no acredita un despliegue accesible ni las aprobaciones de publicación. |

## Cobertura y límites

Se revisó la estructura de todo el repositorio; código de `app/`, sus vistas, componentes, dominio, herramientas y pruebas; pipelines y contratos científicos relevantes, manifiestos y documentación T03/T07/T08/T13–T18; configuración y contenedores. Los informes detallados declaran sus exclusiones.

No se inspeccionó cada imagen, fila histórica, raster ni archivo binario, ni se reejecutó el entrenamiento científico completo. No se comprobó una app pública ni la interfaz en un navegador real. Las comprobaciones de ejecución se delimitan en `environments.md`; lectura de código, pruebas y verificación visual son evidencias distintas.

Los informes usan CONFIRMED para hechos respaldados, INFERRED para inferencias, UNKNOWN para asuntos no establecidos y PROPOSED para recomendaciones. El código vigente prevalece sobre notas históricas y sobre esta memoria.
