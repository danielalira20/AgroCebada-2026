# T09 · R centrado por municipio · diseño v2

Responsable: Dani. Revisor previsto: Migue. Fecha: 13 de octubre de 2026. Rama local: `t09-centrado-municipal`, desde PR18/7ad99b2.

**Estado:** Dani autorizó precisar el diseño e implementar entrenamiento/predicción (pasos 1 y 2). La revisión independiente, las pruebas ampliadas, selección interna y evaluación completa de esta variante siguen pendientes. No se afirma mejora de MAE, cierre de H3, aprobación humana ni actualización del método común T15.

## Problema que resuelve

R-v1 corrige los residuos LOO de la referencia municipal utilizando clima estandarizado globalmente. Su corrección incluye un componente constante por municipio: la media municipal estandarizada multiplicada por los coeficientes. El diseño v1 prescribía ese comportamiento y los cálculos publicados lo reproducen, pero no permite interpretar la corrección como exclusivamente intramunicipal.

La nueva variante busca mantener la referencia y aprender la corrección de las desviaciones climáticas dentro de cada municipio. Es un cambio metodológico posterior a resultados conocidos y a la revisión H3. No constituye un experimento ciego ni garantiza mejorar.

## Solución que implementa

Identificador explícito `R_centrado`, versión `T09-R-centrado-v2`, experimento propuesto `T09_R_centrado_v2`. Conserva referencia T08, residuos LOO, tres variables por ventana, escala global, Ridge/SVD sin intercepto adicional y α=nλ.

Sea Z el clima estandarizado con media y desviación del entrenamiento. Se aprende su media por municipio, por grupo de respaldo y global. Para entrenar se usa:

    D_i = Z_i − media_Z_del_municipio_i_en_entrenamiento
    r_i = y_i − referencia_T(entrenamiento sin i, parcela i)
    beta = argmin media((r − D beta)²) + lambda × suma(beta²)

Para predecir se utiliza:

    predicción = referencia_T_del_entrenamiento + (Z_nueva − centro_aplicable) beta

La misma resta se aplica en fit y predict. Centrar sólo al predecir dejaría el entrenamiento y la aplicación con representaciones distintas.

## Secuencia y aislamiento de información

1. Validar IDs, columnas climáticas y etiquetas alineadas. Las etiquetas quedan fuera de X.
2. Ajustar referencia y sus residuos LOO exclusivamente con X/y del entrenamiento recibido. La propia etiqueta no integra su referencia LOO.
3. Ajustar una escala global por variable sólo con las filas de ese entrenamiento.
4. Aprender las medias territoriales de Z sólo con esas mismas filas. Estas medias son estadísticas de X; no usan y ni requieren retirar la propia X de cada media.
5. Restar la media municipal a cada fila de entrenamiento y resolver el Ridge con los residuos LOO.
6. Transformar las entradas nuevas con la escala y los centros guardados; nunca aprender estadísticas durante predict.

Cada futuro entrenamiento interno debe rehacer escala, referencia, residuos y centros con su propia parte de entrenamiento. No calcularlos una vez sobre las 138 para reutilizarlos dentro de las particiones. Las 59 nunca participan en el ajuste de centros o parámetros.

## Centros, respaldos y casos especiales

| Caso de la parcela nueva | Centro de Z | Referencia de rendimiento |
|---|---|---|
| Municipio presente en entrenamiento | Media de Z de ese municipio | Media de rendimiento de ese municipio |
| Municipio ausente, grupo presente | Media de Z de ese grupo en entrenamiento | Media de rendimiento del grupo |
| Municipio y grupo ausentes | Media global de Z en entrenamiento | Media global de rendimiento |

El grupo conserva el significado de `cultivo_origen` en el respaldo T08; no se interpreta como variedad ni manejo. No se calcula un centro usando las parcelas del municipio nuevo. La transferencia sin municipio conocido sigue siendo una extrapolación que debe informarse por separado en C.

Municipio con una sola etiqueta: su X centrada es cero, aunque su residuo LOO utilice respaldo y no sea cero. La fila permanece en el entrenamiento y en n para α=nλ; no se elimina ni se inventa señal climática municipal. Si todas las variables son constantes dentro de los municipios, la corrección se reduce numéricamente a cero. La ausencia de variación global se trata con escala 1, como StandardScaler; el clima faltante se rechaza según el contrato original.

Se conserva la **escala global anterior al centrado**. No se vuelven a dividir las desviaciones por su desviación intramunicipal: eso cambiaría también la penalización y amplificaría variación pequeña. El cambio acotado es restar el centro territorial.

La corrección media por municipio debe ser cero en las filas de entrenamiento, dentro de tolerancia numérica. No se impone cero sobre las predicciones de evaluación: las parcelas nuevas pueden tener un perfil medio distinto del entrenamiento. R centrado no equivale a TC, pues TC usa residuos contra la media municipal ordinaria y R conserva LOO y sus respaldos.

## Búsqueda futura y reglas que se conservan

- Una sola ventana por ajuste: `abr_oct` o `jun_oct`.
- λ=0.01, 0.1, 1, 10; α=n del entrenamiento × λ. Ocho opciones, sin ampliación automática.
- Misma referencia T08 y particiones externas de T03; A principal, B sensibilidad obligatoria, C diagnóstico.
- Mismas políticas internas del diseño T09 v1: A estratificada, B por celda y C por municipio; MAE y poblaciones comunes ya registradas.
- Mismos desempates y regla de promoción. Las 59 no eligen parámetros.

Estas reglas son herencia para preparar la evaluación futura; escribirlas no registra una nueva ejecución como realizada. La referencia sola permanece comparador de T09. Incluirla en la selección interna adaptativa sería otra modificación, fuera de este cambio H3; el método común ya la propone por separado.

## Históricos y protección contra mezcla de versiones

Se mantienen sin modificar `registro/t09/diseno.json`, la evaluación, CSV, figuras y demás resultados v1. T, CL, TC y R-v1 conservan su comportamiento. La fábrica de estimadores añade `R_centrado` como identificador distinto; pedir `R` continúa reproduciendo el histórico.

El ejecutor, selector completo y verificador matricial v1 siguen ligados al diseño original y no acreditan ni ejecutan automáticamente R centrado. Antes de evaluar v2 habrá que adaptar y versionar sus consumidores, guardar los centros aprendidos, configurar su registro y contrastar sus matrices. No etiquetar una salida nueva como `T09-evaluacion-v1` ni sustituir cifras originales.

El nuevo diseño máquina está en `registro/t09/diseno_R_centrado_v2.json`; referencia por huella el diseño original y conserva las identidades de sus datos. El estado guardado del estimador identifica versión, entrenamiento, ventana/λ/α, coeficientes, escala, centros y conteos de municipio/grupo. Permite aplicar la misma transformación después de serializar y auditar qué respaldo se utilizó.

## Implementación y comprobaciones de estos pasos

Implementado en `scripts/t09_residual_centrado.py`, reutilizando validación, referencia y LOO existentes. La fábrica `crear_estimador('R_centrado', ventana, lambda_reg)` construye esta variante de forma explícita. Pasan 41 pruebas de componentes tanto en Mac como en Docker Linux/amd64: 33 existentes y 8 nuevas. Los controles esenciales contrastan matrices independientes, centros, respaldo, ausencia de aprendizaje durante predict y persistencia del ajuste. No se ejecuta aquí la búsqueda externa completa ni se producen predicciones finales de las 59.

La validación ampliada, evaluación con búsqueda interna, revisión de variantes de otras tareas, actualización del PR y actualización de T15 corresponden a los pasos siguientes. T10/T11/T14 y la rama `t15-procedimiento-comun` se conservan en este alcance.

## Fuentes y apoyo

Diseño y estimadores T09-v1 de PR18/7ad99b2; observación H3 recibida por Dani; reconstrucción local del 13 de octubre. [StandardScaler](https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.StandardScaler.html) y [Ridge](https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.Ridge.html), documentación oficial consultada el 13 de octubre de 2026. El centrado territorial es una decisión explícita del proyecto, no una garantía proporcionada por scikit-learn.

Apoyo de las skills scikit-learn y pensamiento crítico científico. Kassis, T., Agarwal, V., He, Y., Patel, D. y Brueckner, A. M. (2026), [Scientific Agent Skills](https://doi.org/10.48550/arXiv.2609.00065), registro vigente consultado el 13 de octubre de 2026.
