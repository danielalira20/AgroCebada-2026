# TASK-003 — Auditar sistema de investigación y procedencia

Type: INVESTIGATION. Status: DONE. Owner: investigador científico. Fecha: 2026-10-19.
Depends On: ninguna. Blocks: síntesis de root. ADR: ninguno. Invariantes: PROBLEM_MODEL.md.
## Objective
Construir mapa del repositorio fuera de app/, su ciclo de datos T01–T22 y límites de transferir el modelo histórico a decisiones de nuevas campañas.
## Allowed Scope
Leer scripts/, tests/, docs/, registro/ (preferir manifiestos/resúmenes a salidas masivas), analisis/ (scripts e informes), README, requirements, Dockerfile, ejecutar.*, .github. Escribir exclusivamente este contrato (resultados) y docs/ai/auditoria-investigacion.md.
## Out of Scope
Implementar, ejecutar pipelines o generar datos, cambios a fuentes, leer propuesta de planeador antes del mapa actual; no analizar datos privados en masa ni reproducir geoprocesamiento costoso. No usar web.
## Inputs
Repo efbb2dd; .agent/memory/PROBLEM_MODEL.md. Evidencia científica T03/T08/T15/T16/T18, app config para contraste permitido.
## Expected Outputs
Mapa español de responsabilidades, contratos/particiones/validación, decisión final y procedencia, disponibilidad temporal/espacial de fuentes, infraestructura real y pruebas; contradicciones doc/código, riesgos relevantes y alcance inspeccionado. Evidencia ruta:línea.
## Contracts
CONFIRMED con evidencia, INFERRED/UNKNOWN explícitos. Afirmaciones de README contrastadas con fuentes más recientes. No inventar resultados ni afirmar validación prospectiva.
## Acceptance Criteria
Explicar quién produce qué, cómo alimenta la app, 138/59, particiones y fallback, resultados vigentes y límites de generalización. Separar investigación offline de comportamiento online.
## Definition of Done
Informe guardado; exclusiones explícitas; sólo archivos permitidos escritos; resumen a root con fuentes importantes. Completar resultados abajo.
## Findings / Deviations / Final Result / Handoff
Informe: `docs/ai/auditoria-investigacion.md`.

CONFIRMED: mapa T01–T18 con responsables registrados, contratos T07 (197/138/59), particiones A/B/C, LOO v3, selección interna y regla de promoción. T19 tiene consumo/aporte documentado; responsabilidades y cierres T20–T22 quedan UNKNOWN en el alcance inspeccionado. No se inventa validación prospectiva ni aprobación humana.

Hallazgos principales:
- T15 no promueve ningún bloque; mediana MAE principal 0.312585 frente a media 0.320490, pero falla umbral e IC espacial. La propuesta T16 sigue condicionada (`docs/t16_procedimiento_final.md:3`, `registro/decisiones.csv:68`); app ya marca mediana oficial (`app/agrocebada_app/config.py:16`) y T18 existe.
- Defecto confirmado de procedencia T18: CSV versionado con LF tiene SHA256 `4cbe214d056e79b8c81d890a0c27b078a2f78807c3b397f4027f366a8e712d7c`; la traza declara CRLF y SHA `27bc277d...` (`registro/t18/trazabilidad.json:56`, `:73`). Convertir sólo en memoria a CRLF produce exactamente la huella registrada; `.gitattributes:4` normaliza LF sin excepción T18. Datos numéricos no evidencian alteración; identidad de bytes y pruebas reales de entrega quedan afectadas.
- Disponibilidad histórica de ediciones de clima/satélite y acceso futuro no acreditados; una campaña etiquetada 2025 impide afirmar efecto del año, probabilidad de pérdida o desempeño prospectivo (`docs/t04_version_disponibilidad.md:36`, `docs/t16_procedimiento_final.md:183`).
- Tras mapa actual, root autorizó leer `context/planeador_campaña.md`; se añadió contraste científico: percentiles entre parcelas de 2025 no son años bajos/altos, tres años de clima no acreditan «año normal», T13/T14/T15 comparan con media y no mediana, municipio solo no identifica el grupo de respaldo para un territorio nuevo. No se redactó plan integrado.

Comprobación: lectura de fuentes/manifiestos/resúmenes compactos, huellas SHA256 de dos salidas T18 y dos scripts, conteo de saltos/consulta eol, reconstrucción CRLF en memoria; 146 referencias ruta:línea del informe comprobadas existentes/no vacías. No se ejecutaron pipelines, geoprocesamiento, entrenamientos, pruebas ni web. Sólo se escribieron este contrato y el informe permitido. Se preservó la propuesta y las fuentes.

Handoff a root: integrar riesgos de aprobación/identidad de modelo, procedencia de entrega y semántica de escenarios antes de planificar implementación; no tratar coincidencia con T18 como validación de otra campaña. Informe completo incluye n/rangos municipales y exclusiones.
