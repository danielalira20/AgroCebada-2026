# Fase 0 · cierre de alcance y base de comparación

Estado: **cerrada para preparar fase 1**, sujeto a las exclusiones y pendientes expresos de este documento. Fecha de captura: consultar `base.json`, en UTC. No implica que las funcionalidades del planeador estén implementadas.

## Autorización y rama

El usuario autorizó comenzar exclusivamente fase 0 después de recibir la auditoría, y aplazó fase 5 y todo cambio relacionado con Cebi por trabajo paralelo. Se siguió en la rama existente `feature/agriultor-prediccion`; el nombre escrito en la solicitud omite la «n» final y no existe como rama local. No se creó ni cambió una rama.

Se aplicaron las opciones conservadoras recomendadas en [el plan](../../planeador-campana-auditoria-y-plan.md), sin pedir una confirmación adicional de decisiones reversibles de implementación. Esto **no** equivale a aprobación de Dani/Migue sobre T16 ni a autorización para publicar datos.

## Entregables

- [Contratos v1](contratos-v1.md): decisiones cerradas, estructuras futuras, estado de sesión, precisión y aceptación.
- [Base congelada](base.json): resultados actuales, fuentes identificadas por SHA-256 y entorno de captura. Se conserva como referencia, no se usa como dataset de producción.
- Herramienta `app/herramientas/verificar_base_planeador.py`: verifica la base por lectura del catálogo activo. No crea, actualiza ni corrige datos. No importa Streamlit ni módulos del bot.
- [Verificación y pendientes](verificacion.md): comprobaciones realmente ejecutadas y lo que no está acreditado.

## Decisiones cerradas para ejecutar las fases siguientes

| Decisión | Resolución v1 | Motivo y fuente |
|---|---|---|
| Producto | Referencia histórica 2025 y cuentas con supuestos del usuario; no pronóstico anual. | `backend/modelo/estimador.py:10`, `backend/dominio/rangos.py:25` bajo `app/agrocebada_app/`. |
| Navegación | Dos modos dentro de Agricultor: «Consulta rápida» y «Parcela del catálogo». Inicial: catálogo. | Continuidad con flujo actual, sin añadir rutas ni autenticación. Selección consciente, no requisito accidental de una prueba. |
| Cobertura | Consulta rápida únicamente en los municipios del catálogo con cosecha válida de ENTRENAMIENTO. | No se deduce un grupo de registro para un usuario nuevo. Municipio sin soporte: ausencia explícita de referencia local; no fallback global automático. |
| Modelo | Usar `MODELO_OFICIAL` explícitamente desde el llamador; hoy mediana. | Es el comportamiento vigente, no una nueva decisión científica. Analista conserva media/mediana. `config.py:17`. |
| Escenarios | «Rendimiento bajo», «Referencia del municipio», «Rendimiento alto», con 2025 junto a las cifras. Con 3–9 cosechas: menor/mayor observado. | Son diferencias entre parcelas de una campaña. No se usarán «año bajo/alto» en componentes nuevos. |
| Parcela con cosecha | Central = «Cosecha registrada 2025», sin renombrarla como típica. | El flujo actual usa su cosecha real, no el valor típico municipal. |
| Superficie | Una sola editable en consulta rápida; área de la cuenta separada del área del catálogo. | Evitar dos cantidades distintas en resumen, tarjetas y tabla. |
| Precio/costo | Vacíos o cero esperan captura positiva; área mínima 0.01. | Conservar comportamiento actual de UI en esta extracción; aceptar costo cero sería otra decisión. Dominio puro existente no se modifica. |
| C2 | Estado estructurado siempre que exista una cuenta: falta/cubre/equilibrio. Sin cuenta no hay monto. | Eliminar contradicción del plan entre bloque siempre disponible y retorno None con saldo positivo. |
| Precisión | Cuentas con valores crudos; formateo al dibujar. Tolerancias y precisión T18 explícitas. | No recalcular a partir de tarjetas redondeadas ni exigir igualdad binaria de CSV decimal. |
| Estética | Tokens, tipografía, superficies y breakpoints existentes. | Contrato visual resumido abajo; sin cambiar escalas del mapa ni rediseñar analista. |
| Cebi | **Aplazado completo**: sin cambios, nuevos textos/preguntas, pruebas del bot ni hashes que bloqueen su trabajo paralelo. | Instrucción directa del usuario. La compatibilidad de claves compartidas se conserva por el PDF y flujo actual, pero su integración con el bot se revisará cuando termine su cambio. |

## Qué quedó congelado

La captura observó 197 parcelas, 138 etiquetas, 59 reservadas y nueve municipios. Para **cada uno de los dos modelos** guarda 59 filas con predicción/fuente/área/soporte municipal, cuatro poblaciones de validación A/B, confianza por municipio y ejemplos económicos calculados para los nueve municipios. Guarda también rangos, temporada, disponibilidad de contexto y once rutas de archivos presentes o explícitamente ausentes.

Los ejemplos usan 10 ha, precio 5,500 por tonelada y costo 22,000 por hectárea: son supuestos ilustrativos de regresión, no precios precargados, recomendados ni futuros. Los rótulos antiguos que aparecen en `base.json` documentan exactamente las cuentas existentes; no son los textos aprobados para la nueva UI.

La base identifica el paquete activo. No afirma haber conciliado originales contra un maestro, ni garantiza que otro paquete equivalente tenga el mismo Parquet byte por byte. Si se cambia de fuente, el verificador falla de forma intencional: primero debe explicarse y revisarse ese cambio; no regenerar la base para silenciar una diferencia.

## Uso de la comprobación

Desde la raíz del repositorio y un entorno con las dependencias de `app/`:

```powershell
.\.venv\Scripts\python.exe -B -X utf8 app/herramientas/verificar_base_planeador.py
```

El programa compara estructura/categorías, valores numéricos con tolerancias documentadas y SHA-256 de fuentes, y retorna 0 sólo si coinciden. Cambiar Cebi no forma parte de la comparación. No verifica visuales, código del bot ni aprobación metodológica; tampoco convierte la huella histórica de T18 en válida.

## Pendientes independientes y límites del cierre

1. **Aprobación T16:** sigue documentada como propuesta condicionada en `docs/t16_procedimiento_final.md:3`; no se inspeccionó el PR y no se atribuyó aprobación. Se congela el comportamiento actual, sin cambiar la selección.
2. **T18:** la huella de los bytes LF actuales difiere de la traza CRLF. La base conserva los bytes actuales para detectar nuevos cambios, pero no certifica su procedencia histórica. Reparación separada, sin regenerar las 59 en esta fase.
3. **Interfaz:** las pruebas AppTest de la auditoría anterior no fueron evaluables por el bloqueo de inicialización del entorno. No se inventa un baseline visual aprobado; fase 1 necesita un entorno donde ejecutar sus regresiones y fase 4 la inspección visual.
4. **Publicación/orientación:** la v1 fija texto general de organización de cuentas, sin programas/garantías de apoyo; revisión editorial antes de publicar y permisos de datos permanecen fuera de esta fase.
5. **Integración con Cebi:** aplazada expresamente. Cambios paralelos del bot no invalidan esta base numérica. Cuando termine ese trabajo se revisarán sus lectores de sesión y compatibilidad como tarea separada.

La siguiente unidad de trabajo es P1-1/P1-2 del plan. Esta entrega se detiene en fase 0; no crea `backend/dominio/planeador.py`, pantallas nuevas ni widgets.
