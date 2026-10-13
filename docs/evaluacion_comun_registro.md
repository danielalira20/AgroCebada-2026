# Registro para una comparación común

Cada experimento JSON declara `schema=experimento_comun_v1`, ID único, responsable, hipótesis, estado `registrado_antes_de_ejecutar`, huella del procedimiento y lista de procedimientos. Un estado escrito no prueba por sí mismo el orden temporal: conservar su commit antes de correr y el manifiesto de ejecución posterior. Nunca renombrar una búsqueda retrospectiva como registro previo.

Cada procedimiento declara `candidato` estable y `opciones`. Una opción tiene `columnas`, `ventana` y `lambda_reg`. Cada ventana usa las cuatro λ: 0.01, 0.1, 1, 10; las columnas no cambian entre λ. Se admiten una o dos ventanas por procedimiento, máximo ocho opciones con variables. La referencia sola se añade internamente sin búsqueda y sin contar como variante de atributos. Lo estático usa `estatica`, cuatro opciones y no duplica ventanas.

La revisión T10/T11 ya está documentada en [revisión del13-oct](revision_T10_T11_20261013.md). Hay una [propuesta concreta T15](t15_comparaciones_propuestas.md), con ocho procedimientos y18contrastes, comunicada a Daf y Migue. Su JSON conserva estado pendiente y el contrato lo rechaza como ejecutable; faltan las respuestas verificables y el registro definitivo previo a correr. Las plantillas aisladas de los tests no son experimentos del reto.

- `area_explicita=true` autoriza el área declarada, que el núcleo transforma con log natural.
- `calidad_explicita=true` autoriza los indicadores de observación de T07. Declarar cómo se separan de señal espectral en las comparaciones.
- No hay flag que autorice rendimiento, ID, escalón, contorno ni vecindad calculada con el catálogo completo como atributos. `cultivo_origen` sirve para respaldo/desglose.
- Una mezcla de nombres `_abr_oct` y `_jun_oct` en una opción se rechaza; requiere diseñar explícitamente otra búsqueda.
- Una columna no existente, columnas duplicadas, λ fuera de la rejilla, un procedimiento vacío, más de ocho procedimientos o más de ocho opciones detienen el trabajo.

Validación:

```bash
python -m scripts.evaluacion_comun_contrato --experimento RUTA/registro_experimento.json
```

Salida OOF común: `ID_POLIGONO,repeticion,particion,escenario,real,prediccion,candidato,version,fuente`. Conservar adicionalmente huella del procedimiento/registro, versión del código, columnas, estados aprendidos, α/λ, opción elegida y scores de todas las alternativas internas. Referencia: `candidato=media_mun__resp_grupo`; identificadores de nuevos candidatos deben señalar el procedimiento común y sus bloques.

El ejecutor posterior escribirá a un destino nuevo fuera de fuentes, validará antes de producir archivos y publicará un manifiesto al completar toda la ejecución. Una escritura parcial no se considera una entrega. Esta preparación no implementa ese ejecutor ni publica nuevos resultados.
