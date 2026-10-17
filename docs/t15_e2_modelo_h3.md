# T15 E2 · adaptación al modelo común, H3 y registro previo

## Problema que resuelve

La extracción INEGI ya estaba verificada, pero sus columnas aún no estaban conectadas
al procedimiento común. Antes de evaluar su utilidad era necesario comprobar el
centrado de todas las entradas, el aislamiento del entrenamiento y la conservación
de los comparadores, las particiones y las reglas ya acordadas.

## Solución que implementa

Se añaden módulos separados para cargar la tabla canónica, adaptar el modelo,
comprobarlo numéricamente, auditarlo por otra ruta y registrar la evaluación futura.
No se modifican el núcleo `comun-centrado-loo-v3`, E1, T07, T03 ni ejecuciones anteriores.

| Procedimiento | Entradas | Dimensión | Papel |
|---|---|---:|---|
| E2 | cinco variables S + tres INEGI | 8 | candidata |
| E12 | S + INEGI + valor E1 e indicador de ausencia | 10 | candidata |
| E2Q | S + INEGI + sólo indicador E1 | 9 | control diagnóstico, no promovible |

Cada uno conserva dos ventanas, cuatro valores de λ y la opción de referencia sola.
Las tres variables INEGI son estáticas: no crean observaciones ni etiquetas adicionales.

## Separación de entradas

`t15_e2_entradas.py` exige la huella exacta de la entrega Linux aceptada, revisa sus
archivos y comprobaciones, verifica los mismos 197 IDs y une exclusivamente por ID.
Una reproducción Mac, aunque sea numéricamente cercana, no sustituye silenciosamente
la tabla canónica. Una fuente modificada requiere registrar otra versión.

El bloque lateral contiene únicamente tres columnas INEGI y las dos de E1. La calidad,
los desplazamientos de geometría, las etiquetas y los metadatos no se incorporan como
predictores. E2 debe estar completo y finito: no se imputa, filtra ni renormaliza.
Los ceros observados son válidos, incluso cuando las tres columnas son constantes.

Se conserva la preparación E1 ya comprobada: mediana aprendida sólo con admisibles
del entrenamiento de cada ajuste; indicador siempre presente. Si no hay admisibles
en ese entrenamiento, ambas columnas quedan desactivadas también al consultar.
E2Q no aprende del valor NDWI: cambiar ese valor dentro de su dominio no cambia el
estado ni las predicciones del control.

Se acreditan **4,140 predicciones previas reutilizables** de S, E1 y referencia,
sin recalcular esos comparadores ni sustituir versiones. Las 59 reservadas quedan
fuera de las etiquetas y de todas las separaciones de entrenamiento/validación.

## Qué se comprobó de H3

En entrenamiento, cada fila se representa respecto al mismo conjunto de otras filas
que define su residuo: primero municipio sin la propia fila; si no queda respaldo,
grupo de origen sin la fila y finalmente resto global. Esto se aplica a **todas**
las columnas transformadas, incluido el indicador de E1.

En consulta, escala, mediana y centros provienen del entrenamiento guardado. No se
recalculan con la validación ni con las 59 reservadas. La consulta usa el centro
municipal, del grupo o global que corresponde a su referencia territorial.

La media de la corrección por municipio en las filas de entrenamiento fue
aproximadamente `2.43e-17 t/ha` como máximo absoluto. Es una identidad numérica para
detectar corrimientos añadidos; no es una estimación de error predictivo. **No se
impone media cero a las correcciones de la validación.**

El auditor conserva una copia de control a la que se retira el centrado y se ajusta
la predicción total para que siga siendo referencia + corrección. La rechaza por
discrepar con el cálculo independiente, incluso sin un fallo de huellas de archivo.

## Evidencia y alcance

- **27 pruebas nuevas**: unión por ID, cardinalidad, fuentes alteradas, faltantes,
  dominio vectorial, columnas no autorizadas, ceros, datos reservados, preparación
  sólo con entrenamiento, respaldo municipal/grupo/global, fallo de reajuste,
  búsqueda interna, trazas y mutaciones del registro.
- **49 pruebas de regresión** del núcleo v3 y E1. Las 76 pasan en Mac; las mismas
  76 pasan en Linux/amd64 con Python optimizado, imagen común, sin red y datos de
  sólo lectura. Los controles no dependen de `assert` eliminable al optimizar Python.
- **50 contextos externos y 200 separaciones internas** revisados sin entrenar toda
  la evaluación. En B, las celdas CHIRPS no se comparten entre los dos lados.
- Comprobación acotada: A/B, repetición 1, partición 0; ambas ventanas; λ=0.1 fijo.
  Son **12 ajustes Ridge y cuatro referencias** del adaptador, más sus 16 equivalentes
  del antecedente para comprobar el puente. No se eligió ese λ por sus resultados.
- El puente coincide exactamente. El auditor independiente reconstruye los 16
  ajustes del adaptador: **6,128 comprobaciones por entorno**, diferencia máxima
  `1.23e-15` en Mac y `1.14e-15` en Linux, con límite previo `1e-12`.
- Comparación íntegra Mac/Linux de estados, centros, coeficientes y consultas:
  **71,421 comprobaciones**, diferencia máxima `8.89e-16`, sin ampliar tolerancias.

La búsqueda interna se comprobó contra el selector v3 existente dentro de un
entrenamiento de prueba. No se calculó MAE externo, RMSE, R² ni intervalos para
decidir el aporte E2; no se retocaron ventanas, variables, geometrías o parámetros.
Las predicciones de comprobación quedan identificadas como técnicas y no se usan
como entrega definitiva ni como modelos finales entrenados con las 138 etiquetas.

El auditor reutiliza las ecuaciones normales, los conjuntos explícitos y la preparación
independiente de `t15_e1_auditar.py`, ya contrastada. No importa el productor E2 ni
scikit-learn. Reutilizar esa auditoría no equivale a una nueva revisión humana externa.

## Incidentes y resolución

1. La primera prueba intentó comparar el selector E2 con `seleccionar(..., 'S', ...)`
   de E1, cuya interfaz admite únicamente Q y E1. Rechazó el modo antes de ajustar.
   La prueba correcta compara E2 con el selector del núcleo v3. Se conservó intacta
   la API E1 y se verificó igualdad de opciones, puntuaciones y decisión interna.
2. Se inició una auditoría Linux cuando su comprobación previa seguía en proceso.
   La guardia `No es comprobación previa completa` la bloqueó y no produjo dictamen.
   Se corrigió el orden: esperar el cierre del manifiesto y después auditar. La
   ejecución final pasó. No se aceptó evidencia incompleta ni se cambió tolerancia.

No se detectó una nueva discrepancia H3 en la adaptación. Estos incidentes fueron
de interfaz de prueba y secuencia de comprobación, no correcciones a rendimientos,
geometrías o resultados anteriores del equipo.

## Registro y siguiente ejecución

`registro/t15_e2_modelo/registro_ejecucion_v1.json` identifica datos, código, controles,
cartera, ventanas, búsqueda, contrastes y reglas antes de la evaluación de aporte.
Verifica 48 fuentes y seis archivos nuevos de código/pruebas. Los registros históricos
de diseño y extracción mantienen sus estados originales.

La evaluación prevista requiere 4,800 Ridge internos, 600 referencias internas sin
caché y 150 ajustes externos: **5,550 trazas**, 4,140 OOF nuevas y 4,140 reutilizadas.
La opción de referencia sola compite en cada procedimiento. Continúan MAE como
principal, veto RMSE y R² descriptivo; la regla T03 y la guardia adicional para los
dos candidatos E2/E12 no cambian. E2Q permanece como diagnóstico.

Esta inscripción **no autoriza la corrida completa**. Faltan conectar al ejecutor y
a sus reportes los tres procedimientos y la guardia familiar registrada, comprobar
esa conexión y recibir la solicitud de evaluación completa. También siguen pendientes
la aplicabilidad predictiva final a las 59 reservadas y T16.

Las mejoras de esta etapa son trazabilidad, control de interfaces y verificación del
cálculo. **Todavía no hay una reducción de MAE demostrada por INEGI.** Continúan los
límites de datum vertical, disponibilidad de estos mismos bytes en 2025 y una única
campaña de etiquetas; no se convierten en información acreditada por pasar pruebas.

## Reproducir

```bash
.venv/bin/python -m unittest discover -s tests -p test_t15_e2_modelo.py -v
.venv/bin/python -m scripts.t15_e2_verificar_modelo --salida reports/e2_previa_nueva
.venv/bin/python -m scripts.t15_e2_auditar_modelo --entrega reports/e2_previa_nueva --salida reports/e2_auditoria_nueva.json
```

Usar salidas nuevas. Para revisar el paquete compartido se puede sustituir la
carpeta de entrega por `registro/t15_e2_modelo/previa_linux`. No se necesitan los
rasters INEGI originales para esta comprobación del modelo: usa sus columnas
canónicas y la evidencia de extracción conservadas en el repositorio.

Docker/Colima sólo se necesita para reproducir el entorno común; no para consultar
las tablas o informes. Se detiene al terminar las comprobaciones.

## Referencias

- [scikit-learn: evitar filtración en preparación y validación](https://scikit-learn.org/stable/common_pitfalls.html).
- [scikit-learn: objetivo, regularización e intercepto Ridge](https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.Ridge.html).
- Diseño del equipo: `registro/t15_e2/contrato_tecnico_v1.json` y
  `registro/evaluacion_comun/procedimiento_centrado_loo_v3.json`.
- Kassis, T.; Agarwal, V.; He, Y.; Patel, D.; Brueckner, A. M. (2026).
  [Scientific Agent Skills: A Library of Procedural Knowledge for Research Agents](https://doi.org/10.48550/arXiv.2609.00065).
  Skills scikit-learn y pensamiento crítico usadas para preparación, validación,
  unidades y alcance de las conclusiones; referencia vigente comprobada en esta tarea.
