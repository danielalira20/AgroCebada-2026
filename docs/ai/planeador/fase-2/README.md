# Fase 2 · escenarios, equilibrio y orientación

Estado: **implementada y verificada funcionalmente**, 19 de octubre de 2026, rama `feature/agriultor-prediccion`. Inspección visual en navegador pendiente. No se implementan fases 3–5; Cebi continúa aplazado por trabajo paralelo.

## Resultado

CONFIRMED por código y pruebas listadas abajo:

- La calculadora presenta tres tarjetas: rendimiento bajo, referencia de la parcela y rendimiento alto. Con 3–9 cosechas, los extremos se llaman menor/mayor rendimiento registrado. Con menos de tres, se muestra sólo la referencia disponible, sin inventar extremos ni barra.
- La referencia central distingue estimación de parcela, cosecha registrada de 2025 y referencia municipal. Una cosecha registrada puede estar fuera de los extremos municipales; su posición y cifra se conservan.
- El punto de equilibrio aparece junto a las tarjetas. La escala incluye tanto los escenarios como el equilibrio, incluso cuando éste queda fuera del rango histórico. Marcas coincidentes o demasiado próximas se sustituyen por una explicación textual, sin desplazar valores para aparentar distancia. En móvil, las tarjetas se apilan y contienen la información necesaria sin depender de la barra.
- «Si este escenario no cubre tus costos» utiliza el escenario bajo, o la única referencia disponible si no hay rango. Abre ante faltante y se pliega cuando cubre o queda en equilibrio. Incluye el importe calculado, los tres pasos del contrato y una nota de orientación general.
- El contexto pasa a llamarse «Verdor y clima de 2025» y explica su carácter retrospectivo. No cambia la lectura de satélite, clima ni sus gráficas.
- Tabla, tarjetas y lector PDF comparten la cuenta preparada; no se recalculan escenarios en el componente visual. Los importes menores de un peso conservan centavos; los menores de medio centavo se describen sin aparentar cero. Se reutiliza la tolerancia económica existente.

## Diseño y límites de arquitectura

El backend `app/agrocebada_app/backend/dominio/planeador.py` adapta la tabla existente a escenarios, calcula posiciones y compone orientación sin importar Streamlit. `frontend/componentes/escenarios/vista.py` sólo presenta esos resultados. La calculadora conserva su adaptador por parcela y el estado persistente de fase 1.

El CSS añadido usa exclusivamente selectores `esc-*`, tokens existentes, Inter, superficies, radios y colores de la app. No introduce dependencias, fuentes ni animaciones nuevas. Texto e iconos acompañan a los estados económicos. La barra es un apoyo visual redundante; tarjetas y equilibrio contienen las mismas cifras accesibles.

No se cambiaron estimador, datos, configuración, fórmulas de cuentas/rangos ni retornos legacy que consumen otros módulos. Las nuevas etiquetas históricas sólo adaptan la presentación de calculadora y ficha. No se modificaron archivos, diálogo, activos ni pruebas propias de Cebi. Conservar claves compartidas no certifica la integración del bot tras su trabajo paralelo.

## Verificación ejecutada

Python local de `.venv`; AppTest se ejecutó en proceso autorizado fuera del aislamiento que bloquea los sockets internos de Streamlit en Windows. Sin servidor ni despliegue.

| Comprobación | Resultado |
|---|---|
| `app/tests/backend/test_escenarios.py` | 8 pruebas OK: correspondencia exacta con tabla, percentiles/mínimos, poco soporte, C2 en los tres estados, umbral externo, escala degenerada, valores extremos y centavos. |
| `app/tests/frontend/test_calculadora_visual.py` | AppTest OK: cifras de tarjetas/tabla, apertura y cierre al cambiar costo, equilibrio, faltante de $0.50, borrado de superficie, una/dos cosechas, marcas coincidentes, cosecha fuera del rango y escape de etiquetas; estilos claro/oscuro con cuenta calculada y C3 sin clima disponible. |
| `app/tests/backend/test_planeador.py` y `app/tests/frontend/test_estado_planeador.py` | 7 + 5 pruebas OK; referencia/evaluación y persistencia de fase 1 conservadas. |
| `app/tests/frontend/test_calculadora_base.py` | AppTest OK; cuenta por parcela/municipio, superficie única, cambio de vista, retención, borrado y lector PDF. |
| `app/tests/frontend/test_descargas_ficha.py` | Regresión OK: ambas vistas, ambos modelos en Analista, confianza, cosecha registrada/respaldo y PDF de una página en memoria. |
| `app/tests/frontend/test_tema.py` | OK: contraste de tokens y alternancia claro/oscuro, con cifras y filtros conservados. No prueba píxeles de las tarjetas. |
| `app/tests/backend/test_calculadora.py`, `test_rangos.py`, `test_confianza.py` | Regresiones OK; advertencia conocida de R² con datos constantes en fixture, sin cambio en esa fórmula. |
| `app/herramientas/verificar_base_planeador.py` | OK: 197/138/59, ambos modelos, métricas, rangos, confianza y cuentas conservados. |
| `git diff --check` | OK. |

Evidencia local: `.agent/fase2-backend.log`, `fase2-visual.log`, `fase2-regresion-cuenta.log`, `fase2-regresion-ficha.log`, `fase2-regresion-tema.log`. Las advertencias de testing sobre ScriptRunContext no impidieron finalizar en OK. Revisión independiente: `.agent/revision-fase-2.md`; contrato TASK-008. Sin defectos materiales confirmados; root verificó el log PDF final y completó una segunda pasada de contratos, precisión y límites. Los snapshots en `.agent/fase2/antes/` distinguen esta fase de los cambios previos aún sin commit.

La base de fase 0 no se regeneró. SHA-256 de `base.json`: `04688c4bb1694fdad14f7c5534126d0232cdfb5ca9bd44241c0e80d8c663a2e3`.

## Pendientes explícitos

UNKNOWN: apariencia real, desbordamientos y navegación por teclado en navegador de escritorio/móvil. El único navegador accesible fue el integrado, cuyas restricciones impiden usar un servidor local; no se afirma aceptación visual a partir de AppTest. No se probaron Docker ni una instalación pública.

La aprobación metodológica T16 y la huella histórica T18 siguen en el estado documentado en fase 0. Esta fase no cambia sus cifras ni resuelve esas decisiones.

La fase 3 podrá integrar selector de modo y consulta rápida sobre estos componentes. No se inició. Fase 5 y toda integración nueva con Cebi siguen pendientes.
