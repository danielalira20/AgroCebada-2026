# Auditoría de frontend y experiencia vigente

Fecha: 19 de octubre de 2026. Contrato: TASK-001. Inspección estática del árbol de trabajo; referencia solicitada: `efbb2dd`.

**CONFIRMED** significa verificado en el código o en las afirmaciones de las pruebas citadas; no significa observado en navegador. **INFERRED** señala una consecuencia probable que necesita ejecución para comprobarse. **UNKNOWN** identifica una comprobación pendiente. **PROPOSED** distingue recomendaciones de lo que ya existe.

Se leyeron las vistas, componentes, estado, tema, los dos CSS, configuración Streamlit, SVG de Cebi y los catorce scripts de `app/tests/frontend/`. Se consultaron únicamente dependencias de backend necesarias para interpretar la interfaz. No se iniciaron servicios, navegador, pruebas ni generación de PDF. La propuesta `context/planeador_campaña.md` se leyó después de terminar el mapa actual, por indicación de root. Skills aplicadas: `code-architecture-explainer` y `ui-ux-pro-max`; la consulta local de esta última sobre foco visible devolvió orientación aplicable a controles web y modales. No se propone un nuevo sistema visual.

## 1. Estructura, entrada y navegación

**CONFIRMED.** Es una interfaz Streamlit con contenido HTML propio, Altair para gráficas y Pydeck para mapas. `app/app.py:14-25` importa estado, contexto y las dos vistas; `app/agrocebada_app/frontend/tema/html.py:7-12` concentra el HTML y el escape de texto. El flujo real es configurar página → inicializar sesión → inyectar CSS → verificar dataset → cargar datos → dibujar cabecera → calcular contexto → dibujar Agricultor o Analista → abrir bienvenida si falta completarla (`app/app.py:27-47`). No hay un enrutador de páginas adicional en este flujo.

**CONFIRMED.** La página es ancha, con barra lateral inicialmente cerrada. La sesión inicia en **claro**, **Agricultor**, modelo oficial, todas las parcelas y mapa 3D; el tema base nativo de Streamlit está configurado como oscuro. La apariencia clara se obtiene agregando CSS después del tema general, no cambiando `config.toml` por usuario (`app/app.py:27-30`; `app/agrocebada_app/frontend/estado/sesion.py:7-19`; `app/agrocebada_app/frontend/tema/estilos.py:5-10`; `app/.streamlit/config.toml:1-15`).

**CONFIRMED.** El contexto se recalcula en cada ejecución: estimaciones, validación A con fuente municipio, error/cobertura municipal, predicción fuera de entrenamiento por parcela, confianza, textos del mapa y contexto PDF. Las lecturas de parcelas, series, clima, soporte y validación usan `st.cache_data`; eso evita volver a leer los mismos archivos, pero no convierte todos los cálculos del contexto en caché (`app/agrocebada_app/frontend/estado/contexto.py:37-55`; `app/agrocebada_app/frontend/estado/cache.py:7-50`).

### Bienvenida

**CONFIRMED.** Diálogo de tres pasos: elegir Agricultor/Analista; explicar t/ha, confianza y rango; declarar límites del método. Tiene progreso, paso actual, radio horizontal, Anterior, Siguiente/Entrar y Omitir introducción. No se puede cerrar por fuera del diálogo. Anterior y Siguiente rerenderizan el fragmento; Entrar/Omitir actualizan sesión y rerenderizan la app. La elección pendiente se aplica antes de crear los controles de cabecera (`app/agrocebada_app/frontend/vistas/bienvenida.py:4-42,126-184`; `app/app.py:35-38`).

**CONFIRMED.** El diálogo tiene ancho máximo de 760 px, límite de altura y desplazamiento vertical; a ≤600 px usa 94vw y 88dvh. El CSS depende de `data-testid` y `role="dialog"` de Streamlit (`app/agrocebada_app/frontend/vistas/bienvenida.py:53-124`). **UNKNOWN.** No se verificaron foco inicial, recorrido de teclado, anuncio de pasos, escape ni comportamiento del modal al alternar vista.

### Cabecera común

**CONFIRMED.** Marca AgroCebada con Cebi y el texto retrospectivo de campaña 2025/corte 31 de octubre; selector Agricultor/Analista; selector Mediana oficial/Media referencia sólo para Analista; interruptor Satélite activo al inicio y botón Modo claro/oscuro. Agricultor fuerza el modelo oficial aunque la sesión contenga otra selección del analista (`app/agrocebada_app/frontend/tema/estilos.py:13-17`; `app/agrocebada_app/frontend/componentes/paneles/cabecera.py:10-30`; `app/agrocebada_app/config.py:16-19`).

**CONFIRMED.** El botón de tema conserva un nombre textual y CSS lo oculta sólo visualmente; su área mide 64×44 px y tiene foco visible. El tema se mantiene en sesión y se alterna por callback (`app/agrocebada_app/frontend/tema/paleta.py:5-14`; `app/assets/css/tema.css:565-595`). **UNKNOWN.** El archivo de pruebas comprueba conservación de cifras/vista al cambiar tema, pero en esta auditoría no se ejecutó (`app/tests/frontend/test_tema.py:51-68`).

## 2. Agricultor: recorrido completo

**CONFIRMED.** El orden vertical es hero de parcela/mapa/leyenda/resumen → Pregúntale a Cebi → Cómo fue tu temporada → ¿Me alcanza? → Tu libreta → explicación final. Todo se dibuja en una misma vista, sin pestañas internas (`app/agrocebada_app/frontend/vistas/agricultor/vista.py:20-44`).

### Tu parcela, mapa y resumen

**CONFIRMED.** El municipio inicial es Chignahuapan. El selector de parcela incluye IDs del municipio y aclara «por estimar» o «con cosecha registrada». Al cambiar municipio se elige la primera reservada ordenada por ID; si no hay, la primera registrada. Al cambiar parcela por selector también se cambia encuadre. Un clic en mapa actualiza municipio/parcela, pero preserva el encuadre para evitar saltos de cámara (`app/agrocebada_app/frontend/vistas/agricultor/panel_parcela.py:69-94`; `app/agrocebada_app/frontend/vistas/agricultor/seleccion.py:7-16`).

**CONFIRMED.** Para una reservada, el panel muestra rendimiento estimado grande, producción en toneladas (estimación × área registrada), confianza con palabra e icono, ecuación Región ± Municipio/Grupo = Estimación, motivo, rango y aviso si existe. El plegable «Cómo leer esta estimación» explica la base y los factores que el método no ve. Para una parcela registrada muestra rendimiento real y, si existe validación, lo que habría estimado el método sin conocerla y la diferencia. Ambas ramas ofrecen ficha PDF (`app/agrocebada_app/frontend/vistas/agricultor/panel_parcela.py:16-65,90-93`).

**CONFIRMED.** El mapa tiene 700 px de altura, se centra inicialmente en la parcela de encuadre desplazada ligeramente a la izquierda y representa sus vecinas. Los chips resumen área registrada, altitud si existe, lluvia abril–octubre, máximo NDVI/mes y corte informativo; se calculan para la parcela seleccionada aunque la cámara conserve otro encuadre (`app/agrocebada_app/frontend/vistas/agricultor/vista.py:31-38`; `app/agrocebada_app/backend/dominio/resumen.py:7-23`). La semántica de selección/color se detalla en §5 y presenta una discrepancia textual registrada en F-04.

### Pregúntale a Cebi

**CONFIRMED.** Una tarjeta breve abre un diálogo grande. Presenta preguntas fijas en dos columnas, sin texto libre ni llamada a un modelo generativo en este componente. Las respuestas se producen con los datos actuales, validación, precio/costo/área de calculadora, clima normal y libreta de esa parcela. Mantiene índices de preguntas hechas en una clave por ID, muestra las últimas cuatro, mueve una pregunta repetida al final y permite Empezar de nuevo (`app/agrocebada_app/frontend/vistas/agricultor/pregunta_cebi.py:19-41,44-56`).

**CONFIRMED.** La conversación está separada por parcela mediante `cebi_{pid}`; cambiar de parcela no borra explícitamente las listas previas. El comentario que dice que «empieza de nuevo al cambiar» debe leerse como conversación propia por parcela, no como borrado confirmado (`app/agrocebada_app/frontend/vistas/agricultor/pregunta_cebi.py:1-3,25-38`). **UNKNOWN.** Retención exacta tras ida/vuelta entre modos y limpieza de widgets no probadas.

### Cómo fue tu temporada

**CONFIRMED.** Dos tarjetas internas explican verdor y lluvia/temperatura de 2025; declaran que son contexto y no cambian la estimación. El verdor describe el mes máximo de la parcela y su comparación municipal. El clima compara con 2022–2024 para una zona de unos 5 km, o informa falta de datos. Las dos gráficas están en un expander: línea NDVI con franja municipal P25–P75 cuando hay evidencia; lluvia y temperatura contra normal o clima mensual simple (`app/agrocebada_app/frontend/vistas/agricultor/verdor_clima.py:12-16,29-83`; `app/agrocebada_app/frontend/componentes/graficas/indices.py:32-55`).

**CONFIRMED.** Las tarjetas usan flex-wrap con base de 300 px; las gráficas se solicitan en dos columnas y ancho adaptable. El clima normal distingue series por trazo además de color (`app/agrocebada_app/frontend/vistas/agricultor/verdor_clima.py:15-16,58-83`; `app/agrocebada_app/frontend/componentes/graficas/clima.py:29-54`). **UNKNOWN.** Legibilidad final a 320 px y coste de dibujar gráficas plegadas.

### ¿Me alcanza?

**CONFIRMED.** Solicita precio por tonelada y costo por hectárea inicialmente vacíos, ambos con mínimo 0; área con mínimo 0.01 y valor inicial registrado de la parcela. Precio y costo usan claves compartidas, área una clave por parcela. Enlaza a Agrocostos de FIRA. Si precio o costo son cero o vacíos, retorna sin mostrar cuentas (`app/agrocebada_app/frontend/vistas/agricultor/calculadora.py:27-48`).

**CONFIRMED.** Con datos, muestra una frase de cobertura/faltante, nota con escenarios y equilibrio, y un expander con rendimiento, producción, ingreso, costo, diferencia y Sí/No. La cifra de partida es predicción para reservadas y cosecha registrada para etiquetadas. El equilibrio es costo/ha ÷ precio/t; el texto compara ese umbral con las cosechas municipales de 2025. El rango usa P10–P90 con ≥10 cosechas, mínimo–máximo con 3–9 y sin rango con menos de 3 (`app/agrocebada_app/frontend/vistas/agricultor/calculadora.py:30-33,49-82`; `app/agrocebada_app/backend/dominio/calculadora.py:13-63`; `app/agrocebada_app/backend/dominio/rangos.py:10-11,22-48`).

**CONFIRMED.** Cambiar el área afecta la cuenta y puede incorporarse al PDF, pero no modifica área registrada, producción del panel ni chips. Son dos magnitudes distintas con la misma etiqueta «Área» en pantalla; no hay sincronización con el dato base (`app/agrocebada_app/frontend/vistas/agricultor/calculadora.py:44,50`; `app/agrocebada_app/frontend/vistas/agricultor/panel_parcela.py:48`; `app/agrocebada_app/backend/dominio/resumen.py:10`; `app/agrocebada_app/frontend/componentes/descargas/boton_ficha.py:25-37`). **PROPOSED.** Aclarar «Área para esta cuenta» sería un ajuste de significado conservando el patrón actual; no se implementó.

### Tu libreta

**CONFIRMED.** Tiene ayuda plegada, invitación vacía y un renglón por año con toneladas, t/ha, diferencia contra referencia de app y nota. Formulario: año 2000–2100 (inicial 2025), toneladas totales y nota opcional de hasta 140 caracteres. Un año duplicado reemplaza su entrada; toneladas cero se rechazan. Al existir registros aparecen progreso municipal de confianza y tablero plegado con promedio, mejor año, total y error medio, más barras anuales y referencia municipal (`app/agrocebada_app/frontend/vistas/agricultor/bitacora.py:18-23,40-101,104-152`; `app/agrocebada_app/backend/dominio/bitacora.py:18-19,30-63`).

**CONFIRMED.** La libreta vive en un diccionario de `st.session_state` por ID. Se descarga CSV con ID/municipio y se vuelve a subir desde un expander; la carga reemplaza la libreta de la parcela actual. El deduplicador de carga usa sólo `(pid, nombre, tamaño)` (`app/agrocebada_app/frontend/vistas/agricultor/bitacora.py:26-32,154-166`; `app/agrocebada_app/backend/dominio/bitacora.py:103-132`). Riesgos importantes de promesa de privacidad, historial y atribución: F-01 a F-03.

### Explicación final

**CONFIRMED.** Cebi cierra diciendo que la cifra viene de cosechas municipales, verdor/clima son seguimiento, no recomendación agronómica y rendimiento no implica calidad maltera ni capacidad de pago (`app/agrocebada_app/frontend/componentes/paneles/explicacion.py:8-20`).

## 3. Analista: hero y siete pestañas

### Hero, búsqueda y filtros

**CONFIRMED.** Los controles son Todas/Las 59/Las 138, municipio y buscador por ID sobre **todo** el catálogo. Una combinación capa/municipio sin resultados se revierte al último filtro válido y produce toast de 5 segundos, consumido una sola vez. El buscador fija encuadre; el clic de mapa selecciona un ID sin cambiar por sí mismo el encuadre. Con encuadre activo, se muestran vecinas de ese ID; sin él, se usan los IDs filtrados (`app/agrocebada_app/frontend/vistas/analista/vista.py:28-72`; `app/agrocebada_app/frontend/vistas/analista/seleccion.py:7-33`).

**CONFIRMED.** El resumen y «Descargar cifras» usan el contexto completo: cantidad total de predicciones, media y métricas principales; no reciben capa, municipio ni ID. Las siete pestañas reciben también el contexto completo. Los filtros del hero no filtran las tablas/pestañas ni el ZIP (`app/agrocebada_app/frontend/vistas/analista/vista.py:73-102`; `app/agrocebada_app/frontend/componentes/descargas/boton_cifras.py:21-26`).

**CONFIRMED.** Las siete funciones de pestaña están llamadas dentro de `st.tabs`, sin condición propia para cargar sólo la pestaña visible. El componente de dispersión documenta expresamente que todas se dibujan en cada ejecución; por eso usa claves distintas cuando se repite en Validación y Evidencia (`app/agrocebada_app/frontend/vistas/analista/vista.py:86-102`; `app/agrocebada_app/frontend/componentes/graficas/dispersion_validacion.py:12-16`). **UNKNOWN.** Latencia/coste efectivo de esa ejecución en el entorno desplegado.

| Pestaña | Contenido y acciones confirmadas | Evidencia |
|---|---|---|
| Cartera | Agrega reservadas por municipio. KPIs de parcelas, hectáreas, producción y mezcla de confianza cuando existe. Barras de producción con tramo bajo–alto, etiquetas y tooltips; tabla municipal con rango, notas y CSV. Advierte campaña 2025/demostración, no cifra oficial regional. | `app/agrocebada_app/frontend/vistas/analista/pestanas/cartera.py:17-20,30-52,55-99` |
| Las 59 estimaciones | Comprobaciones de conteo, IDs únicos, finitud y coincidencia con entrega final o archivo de referencia. Tabla con estimación, producción, confianza, motivo, rango, área, MAE, fuente, cantidad de cosechas y aviso. CSV de ID/rendimiento/confianza/motivo/límites de rango. En móvil, tarjetas reducidas a ID, confianza, municipio, estimación, producción, rango y aviso. | `app/agrocebada_app/frontend/vistas/analista/pestanas/estimaciones.py:17-28,31-89` |
| Ficha técnica | Selector de ID independiente del buscador del mapa. Área/grupo, rendimiento o predicción, referencia territorial, MAE y PDF. Disponibilidad por sensor; tarjeta de calidad; NDVI/EVI/LAI; clima si existe; comparador de hasta tres parcelas. | `app/agrocebada_app/frontend/vistas/analista/pestanas/ficha_tecnica.py:18-87` |
| Validación | Métricas de población principal y poblaciones auxiliares plegadas; error/confianza por municipio; regla de confianza; registrado contra estimado; simulación ocultando cosechas de un municipio con resumen antes/después y detalle por parcela. Si falta validación, muestra aviso y retorna. | `app/agrocebada_app/frontend/vistas/analista/pestanas/validacion.py:17-46`; `app/agrocebada_app/frontend/componentes/validacion/resultados.py:11-36`; `app/agrocebada_app/frontend/componentes/validacion/municipios.py:10-41`; `app/agrocebada_app/frontend/componentes/validacion/simulacion.py:20-47` |
| Evidencia | Introducción con conteos y decisión oficial; tres preguntas guía; explorador Vegetación/Clima/Combinaciones, Resultado, Gráfico/Tabla y complementarias; ficha de prueba y trazabilidad plegada; aprendizaje, ajuste del modelo consultado y catálogo completo con CSV. Estado sin catálogo o filtros sin resultados explícito. | `app/agrocebada_app/frontend/vistas/analista/pestanas/evidencia.py:13-23`; `app/agrocebada_app/frontend/componentes/evidencia/preguntas.py:10-59`; `app/agrocebada_app/frontend/componentes/evidencia/tabla.py:35-99`; `app/agrocebada_app/frontend/componentes/evidencia/aprendizaje.py:9-37` |
| Método y límites | Cuatro pasos del método oficial, resultados del modelo consultado, fuentes, tabla de alcance y límites. Las instrucciones del método usan oficial aun si se consulta media; las métricas sí reciben el modelo activo. | `app/agrocebada_app/frontend/vistas/analista/pestanas/metodo_limites.py:14-23`; `app/agrocebada_app/frontend/componentes/metodo/pasos.py:7-12`; `app/agrocebada_app/frontend/componentes/metodo/resultados.py:7-30`; `app/agrocebada_app/frontend/componentes/metodo/alcance.py:10-24` |
| Analizar tus datos | Requisitos, subida ZIP/CSV y plantilla; revisión/rechazo; resultado por parcela, mapa si hay geometría, tabla/CSV y detalle técnico. Se describe en §4. | `app/agrocebada_app/frontend/vistas/datos_propios/vista.py:11-43`; `app/agrocebada_app/frontend/vistas/datos_propios/resultado.py:98-156` |

**CONFIRMED.** El comparador de Ficha técnica sugiere la parcela de la ficha y dos vecinas; permite hasta tres IDs y elegir índice/sensor Sentinel-2 o Planet. Si faltan capturas muestra aviso. La curva responde a esos filtros; la tabla inferior calcula máximo NDVI con todas las series de cada parcela y lluvia abril–octubre, sin restringir ese resumen al sensor elegido (`app/agrocebada_app/frontend/vistas/analista/pestanas/comparar.py:16-59`). **PROPOSED.** Aclarar alcance del resumen evita interpretar sus cifras como filtradas por sensor.

**CONFIRMED.** Evidencia conserva el método oficial para describir la decisión histórica, mientras el bloque «ajuste del modelo consultado» sí recibe la selección activa. El gráfico de experimentos distingue pruebas complementarias, no inventa sus intervalos y agrega referencia cero y umbral mínimo (`app/agrocebada_app/frontend/vistas/analista/pestanas/evidencia.py:19-23`; `app/agrocebada_app/frontend/componentes/evidencia/comparacion.py:12-52`).

## 4. Datos propios y descargas

**CONFIRMED.** La carga admite un ZIP con tabla/shapefile o un CSV simple; exige entre otras reglas ≥10 parcelas con cosecha y al menos una por estimar. Limita a 50 MB, 5,000 parcelas y 200 MB descomprimidos. Los textos de formato y rechazo vienen del backend, no de inferencias del frontend (`app/agrocebada_app/backend/carga_segura/reglas.py:4-34`; `app/agrocebada_app/frontend/vistas/datos_propios/vista.py:20-26`).

**CONFIRMED.** Se obtiene el contenido completo, se calcula SHA-256 y se reutiliza revisión/error guardado en `carga_resultado` mientras la huella sea igual. El error esperado conserva motivo; el inesperado se sustituye por mensaje genérico. El resultado permanece en sesión, no se elimina explícitamente al terminar el análisis (`app/agrocebada_app/frontend/vistas/datos_propios/vista.py:27-43`). Esto matiza la frase «se borra al terminar» en requisitos (`app/agrocebada_app/backend/carga_segura/reglas.py:34`).

**CONFIRMED.** Tras aceptar el archivo se calculan predicción, validación dejando una fuera, métricas, confianza municipal sólo desde validaciones con fuente municipio y rangos propios. La pantalla presenta revisiones/avisos, selector de parcela reservada, cifra, producción, área, confianza, motivo, rango y explicación de Cebi. El mapa, sólo con geometrías, usa vista desde arriba y sin relieve real; el toggle Satélite común sigue aplicando. El detalle técnico explica que las métricas del archivo no se comparan directamente con el 5×5 del proyecto (`app/agrocebada_app/frontend/vistas/datos_propios/resultado.py:45-58,83-156`).

**CONFIRMED.** La tabla completa del archivo incluye estimación, área, MAE, fuente, confianza y rango; su CSV añade motivo y extremos de rango. La tabla municipal del detalle cambia a tarjetas en móvil, pero la tabla principal de todas las parcelas subidas no tiene esa alternativa en este componente (`app/agrocebada_app/frontend/vistas/datos_propios/resultado.py:61-80,134-153`; `app/assets/css/tema.css:79-92`).

| Descarga confirmada | Momento y contenido | Evidencia |
|---|---|---|
| Ficha PDF por parcela | Se genera bajo demanda con callable al descargar; cacheada por ID/modelo/confianza/calculadora. Puede incorporar las cuentas de la sesión. | `app/agrocebada_app/frontend/componentes/descargas/boton_ficha.py:8-12,19-46` |
| ZIP de cifras | Tres CSV compartidos con informe: parcelas, municipios, validación; caché sólo por modelo, contexto excluido del hash. | `app/agrocebada_app/frontend/componentes/descargas/boton_cifras.py:11-26` |
| CSV de Cartera | Tabla municipal completa, nombres de columnas de pantalla. | `app/agrocebada_app/frontend/vistas/analista/pestanas/cartera.py:84-98` |
| CSV de las 59 | Rendimiento y evidencia complementaria; modelo en nombre de archivo. | `app/agrocebada_app/frontend/vistas/analista/pestanas/estimaciones.py:62-67` |
| Libreta CSV | Datos anotados con ID/municipio; deshabilitada si está vacía. | `app/agrocebada_app/frontend/vistas/agricultor/bitacora.py:154-157`; `app/agrocebada_app/backend/dominio/bitacora.py:103-108` |
| Experimentos CSV | Catálogo completo independiente de filtros; UTF-8 con BOM. | `app/agrocebada_app/frontend/componentes/evidencia/tabla.py:93-99` |
| Plantilla/dataset propio | Ejemplo de entrada y estimaciones del archivo analizado. | `app/agrocebada_app/frontend/vistas/datos_propios/vista.py:24-26`; `app/agrocebada_app/frontend/vistas/datos_propios/resultado.py:146-153` |

## 5. Mapa y gráficas: semántica e interacción

**CONFIRMED.** La leyenda ofrece 3D/Desde arriba y Rendimiento/Confianza. Rendimiento usa escala paja→verde→menta, referencias 2.0, 3.8 y 5.6 t/ha; confianza usa verde/ámbar/rojo y avisa que no garantiza rendimiento (`app/agrocebada_app/frontend/componentes/paneles/leyenda.py:7-41`; `app/agrocebada_app/config.py:13`).

**CONFIRMED.** En 3D, la extrusión representa rendimiento; desde arriba los polígonos son planos. Confianza cambia relleno, mientras la altura 3D sigue representando rendimiento. Reservadas tienen borde blanco en 3D; registradas carecen de borde visible. Desde arriba, reservadas y registradas se distinguen por opacidad/grosor de borde. Seleccionar coloca borde blanco de 4 px; no asigna relleno naranja. Las parcelas sin confianza reciben gris (`app/agrocebada_app/frontend/componentes/mapa/mapa.py:24-69`; `app/agrocebada_app/frontend/componentes/mapa/colores.py:8-19`).

**CONFIRMED.** El controlador permite rueda, doble clic, pellizco, teclado y rotación sólo en 3D; mínimo de zoom se fija en zoom inicial −1.2, máximo 18.5. El tooltip muestra ID/municipio/detalle; la selección es de objeto único con callback por clave. La clave añade arriba/3d y depende del encuadre o filtros del llamador (`app/agrocebada_app/frontend/componentes/mapa/mapa.py:70-80`; `app/agrocebada_app/frontend/componentes/mapa/interaccion.py:5-11`). El comentario de `mapa.py:15-17` sobre rueda desactivada está desactualizado frente a `scrollZoom=True`; la ayuda pública sí dice que acerca con rueda (`app/agrocebada_app/config.py:28-29`).

**CONFIRMED.** Los fondos dependen de Terrain Tiles AWS, EOX Sentinel-2 cloudless **2021** y CARTO. La interfaz atribuye esos servicios y fecha de imagen. Apagar Satélite quita textura EOX pero puede mantener relieve si hay elevaciones; no es un modo completamente sin red (`app/agrocebada_app/config.py:23-27`; `app/agrocebada_app/frontend/componentes/mapa/mapa.py:18-22,58-64,78`). **UNKNOWN.** Disponibilidad actual de tiles, uso real de red, WebGL, contraste del terreno y selección por teclado.

**CONFIRMED.** `grafica_base` centraliza fondo transparente, ejes/rejilla/leyendas y colores categóricos por tema. La paleta convierte verde/cian/ámbar/azul y otros tonos a equivalentes oscuros en tema claro. Las curvas de índices usan puntos y tooltips; la de clima superpone lluvia y temperaturas en ejes independientes; dispersión agrupa por parcela y usa dominio fijo 2–6 (`app/agrocebada_app/frontend/componentes/graficas/base.py:7-18`; `app/agrocebada_app/frontend/tema/paleta.py:17-28`; `app/agrocebada_app/frontend/componentes/graficas/indices.py:16-29`; `app/agrocebada_app/frontend/componentes/graficas/clima.py:12-26`; `app/agrocebada_app/frontend/componentes/graficas/dispersion_validacion.py:20-33`).

## 6. Lenguaje visual real y reutilización

| Regla confirmada | Implementación vigente y evidencia |
|---|---|
| Oscuro | Fondo `#0A110E`, texto `#E7EFE9`, acento `#9BE15D`, vidrio `rgba(13,21,17,.58)` y bordes blancos a baja opacidad. `app/assets/css/tema.css:1-8`. |
| Claro inicial | Fondo `#F1F4EE`, texto `#293F2C`, texto fuerte `#203B26`, acento `#397523`, borde `#C9D4C4`, diálogo `#FFFEF8`; overrides para inputs, pestañas, menús fuera de `.stApp` y mapas. `app/assets/css/claro.css:1-73,87-101`. |
| Superficies | Contenedores con clave `glass_*`: radio 18 px, padding 14×16, borde fino/sombra discreta. Blur sólo en cabecera/paneles superpuestos al mapa; en claro los paneles del mapa tienen piso de opacidad .78 y blur 24 px. `app/assets/css/tema.css:15-20`; `app/assets/css/claro.css:14-24`. |
| Jerarquía | Inter configurada como fuente; marca 1.15rem, cifra principal 3.1rem, título común 1.02rem, KPI 1.45rem, notas .78rem, etiquetas mini .68rem; Validación/Evidencia/Método aumentan texto de lectura a .88rem. `app/.streamlit/config.toml:7`; `app/assets/css/tema.css:234-270,352-354,411-415,548-550`. |
| Ancho y espaciado | Contenedor máximo 1500 px, padding superior 1rem e inferior 2rem; gaps locales 8–32 px; no hay escala global formal de espaciado. `app/assets/css/tema.css:10,240-255,434-456`. |
| Patrones | `titulo`, `chips`, `.fila`, `.mini`, `.kpis`, `.nota`, `.aviso`, `.chk`, `.val-confianza`, artículos con `dl` y expanders para detalle. Tabla común añade Styler claro; gráfico común aplica tema explícito. `app/agrocebada_app/frontend/tema/html.py:15-21`; `app/agrocebada_app/frontend/tema/tablas.py:7-10`; `app/assets/css/tema.css:240-269,356-360`. |
| Cebi | SVG con nombre accesible, animaciones de entrada/pasos/parpadeo/brote/salto; reduced-motion detiene animaciones de mascota. `app/assets/mascota/cebi.svg:1`; `app/assets/css/tema.css:272-297`. |

**PROPOSED.** Una ampliación coherente puede reutilizar estos patrones y tokens de ambos temas, mantener cifras con unidades visibles, palabras además de iconos y detalle plegable. Conviene evitar introducir otra paleta o paneles flotantes en la sección de cuentas; las tarjetas existentes de temporada/dataset ya ofrecen una estructura adaptable sin depender de un mapa. Base observada: `app/assets/css/tema.css:15-20,240-269`; `app/agrocebada_app/frontend/vistas/agricultor/verdor_clima.py:15-26`.

## 7. Responsive y accesibilidad

**CONFIRMED.** A ≤900 px, los cinco paneles del hero dejan posición absoluta y pasan al flujo; en escritorio panel/KPIs miden 350 px, chips/filtros 280 y leyenda 300. Los mapas siguen solicitándose con 700 px; el panel agricultor conserva un máximo de 668 px y overflow vertical. El orden móvil proviene del orden del código: panel/filtros → leyenda → mapa → chips/KPIs (`app/assets/css/tema.css:197-231`; `app/agrocebada_app/frontend/vistas/agricultor/vista.py:27-37`; `app/agrocebada_app/frontend/vistas/analista/vista.py:32-83`).

**CONFIRMED.** A ≤700 px, las 59 y validación municipal ocultan tabla y muestran carruseles horizontales con tarjetas al 88%, scroll-snap y arrastre; evidencia usa tarjetas verticales y apila decisiones/preguntas/aprendizaje. Dataset propio municipal también tiene tarjetas. A ≤600 px, métricas de ficha, resultados y libreta pasan a dos columnas; a ≤900 px los pasos pasan a dos columnas y límites a una (`app/assets/css/tema.css:79-107,128-142,298-312,345-407,471-481,538-563,668-759`).

**CONFIRMED.** La cabecera se envuelve entre 641 y 1400 px y reserva 64 px al tema; a ≤600 aplica desplazamiento vertical −40 px y margen inferior −55 px a su última columna. Hay reglas superpuestas específicas de móvil para reducir huecos (`app/assets/css/tema.css:596-642`). **INFERRED.** Son puntos sensibles a cambios de etiquetas, zoom y estructura de columnas de Streamlit; no hay evidencia visual actual de un solapamiento.

**CONFIRMED.** Existen foco visible global y por Validación/Evidencia, control de tema táctil 44 px, texto/icono de confianza y cobertura, labels nativos y atributos ARIA en Cebi y barra de variación de evidencia. La mayoría de títulos comunes se generan como `div.tit`, no headings; la tabla visual de alcance usa `div/article` y no semántica de tabla. Carruseles sólo añaden overflow/scroll-snap y artículos; no controles anterior/siguiente ni `tabindex` propios (`app/assets/css/tema.css:395-396,467-470,565-595,668-759`; `app/agrocebada_app/frontend/tema/html.py:20-21`; `app/agrocebada_app/frontend/componentes/metodo/alcance.py:16-22`; `app/agrocebada_app/frontend/componentes/evidencia/aprendizaje.py:17-19`; `app/agrocebada_app/frontend/vistas/analista/pestanas/estimaciones.py:17-28`).

**UNKNOWN.** No se ha certificado accesibilidad: faltan navegación completa con teclado/lector, foco no oculto sobre paneles/carruseles, nombre y contraste de controles generados, zoom de texto, objetivos táctiles restantes, equivalentes a hover/tooltips y acceso a todas las cifras del mapa. Las pruebas de contraste existentes evalúan tokens claros sobre fondos predefinidos, no cada píxel del mapa o gráfico oscuro (`app/tests/frontend/test_tema.py:18-42`).

## 8. Hallazgos y riesgos para la experiencia actual

Las prioridades siguientes son impacto de lectura y continuidad de usuario, no autorización de correcciones.

| ID / prioridad | Hecho verificado e impacto | Evidencia y estado |
|---|---|---|
| F-01 Alta | La UI de libreta afirma «no se guarda en ningún servidor» y su comentario «Nada sale de su navegador», pero las entradas/archivo llegan al código Python y se conservan en `st.session_state`. Es una promesa más fuerte que «sin persistencia en disco»; no se puede asegurar ejecución exclusiva en navegador. | **CONFIRMED**: `app/agrocebada_app/frontend/vistas/agricultor/bitacora.py:6,26-32,118,159-163`. **UNKNOWN**: residencia física/retención del servidor desplegado. |
| F-02 Alta | Toda anotación del rango 2000–2100 recibe la misma estimación actual de campaña 2025, aunque la UI dice «lo que la app había estimado» para ese año y calcula «se equivocó por» como promedio histórico. No hay selección del pronóstico por año. | **CONFIRMED**: `app/agrocebada_app/frontend/vistas/agricultor/bitacora.py:18-21,79-80,111-114,131,142`; `app/agrocebada_app/backend/dominio/bitacora.py:18,52-55,79-84`. La interpretación como precisión multianual sería incorrecta. |
| F-03 Alta | El CSV de libreta exporta ID/municipio, pero el importador los descarta y la UI asigna sus filas a la parcela abierta sin validar coincidencia. Una libreta de A subida en B se atribuye a B, conservando rendimientos/diferencias de A. | **CONFIRMED**: `app/agrocebada_app/backend/dominio/bitacora.py:103-108,118-132`; `app/agrocebada_app/frontend/vistas/agricultor/bitacora.py:160-164`. |
| F-04 Media | El texto agricultor dice «Tu parcela en naranja», pero la selección conserva color de rendimiento/confianza y sólo cambia borde. Desde arriba la leyenda habla de borde grueso para reservadas, cuya diferencia programada es .7 frente a .5 px. | **CONFIRMED**: `app/agrocebada_app/frontend/vistas/agricultor/vista.py:38`; `app/agrocebada_app/frontend/componentes/mapa/mapa.py:36-55`; `app/agrocebada_app/frontend/componentes/paneles/leyenda.py:17-20`. **UNKNOWN**: discriminabilidad real del borde. |
| F-05 Media | Búsqueda activa establece un encuadre que omite filtro capa/municipio y dibuja vecinas; filtros y resumen total permanecen visibles. Puede interpretarse que mapa/resumen siguen el mismo filtro. | **CONFIRMED**: `app/agrocebada_app/frontend/vistas/analista/vista.py:38-41,60-83`. **PROPOSED**: explicitar alcance de filtros/encuadre, sin cambiar automáticamente el comportamiento. |
| F-06 Media | La explicación de rango en datos propios dice «de la más baja a la más alta», aunque con ≥10 cosechas se usa P10–P90. La calculadora llama «año bajo/alto» a percentiles espaciales de una sola campaña. | **CONFIRMED**: `app/agrocebada_app/frontend/vistas/datos_propios/resultado.py:27-34`; `app/agrocebada_app/backend/dominio/rangos.py:1-3,25-28`; `app/agrocebada_app/backend/dominio/calculadora.py:22-25`. **PROPOSED**: distinguir escenarios de cosechas de 2025 frente a variabilidad interanual. |
| F-07 Media | La plantilla CSV ofrecida contiene sólo dos parcelas de entrenamiento, pero el requisito mínimo es diez. Descargar y volver a subir el ejemplo sin ampliarlo es un caso rechazado. | **CONFIRMED**: `app/agrocebada_app/backend/carga_segura/reglas.py:9,32,37-42`. **PROPOSED**: aclarar que ilustra columnas y no es dataset válido completo. |
| F-08 Media | La UI ofrece precio/costo con mínimo cero, pero cero y vacío se tratan igual; al ingresar cero no aparece explicación junto al campo. Una cosecha perdida de cero toneladas tampoco es registrable en libreta. | **CONFIRMED**: `app/agrocebada_app/frontend/vistas/agricultor/calculadora.py:40-48`; `app/agrocebada_app/frontend/vistas/agricultor/bitacora.py:132,138-146`; `app/agrocebada_app/backend/dominio/bitacora.py:44-51`. Definir si esos casos son válidos es decisión de producto, no de CSS. |
| F-09 Media | La tabla ancha de 59 muestra motivo, MAE, fuente, área y soporte; las tarjetas móviles no conservan todos esos campos ni enlace a detalle de cada tarjeta. Similar reducción del motivo en tarjetas municipales de datos propios. | **CONFIRMED**: `app/agrocebada_app/frontend/vistas/analista/pestanas/estimaciones.py:17-28,69-86`; `app/agrocebada_app/frontend/vistas/datos_propios/resultado.py:69-80`; `app/assets/css/tema.css:89-92`. **PROPOSED**: revisar paridad informativa sin reintroducir tabla ancha. |
| F-10 Baja | Deduplicar libreta por nombre/tamaño no detecta contenido distinto del mismo tamaño/nombre para el mismo ID. Se guarda la firma antes de validar, así que reintentar el mismo archivo rechazado tampoco lo procesa de nuevo. | **CONFIRMED**: `app/agrocebada_app/frontend/vistas/agricultor/bitacora.py:160-166`. En contraste, datos propios usa SHA-256 (`app/agrocebada_app/frontend/vistas/datos_propios/vista.py:28-38`). |
| F-11 Por comprobar | Persistencia al alternar vistas: precio/costo/área son claves de widgets condicionales; el selector de modelo también desaparece en Agricultor. No existe copia de dominio separada ni restauración de esos valores fuera de los widgets. | **CONFIRMED**: `app/app.py:44`; `app/agrocebada_app/frontend/componentes/paneles/cabecera.py:19-23`; `app/agrocebada_app/frontend/vistas/agricultor/calculadora.py:39-44`. **INFERRED**: riesgo de limpieza de widgets al desmontarse. **UNKNOWN**: comportamiento efectivo en la versión instalada; no se ejecutó ida/vuelta. |

**PROPOSED.** No mezclar correcciones F-01/F-02/F-03 con una ampliación visual sin decidir alcance; sí conservarlas como deuda explícita porque afectan la credibilidad de una herramienta de planeación y la continuidad de sus registros.

## 9. Pruebas existentes: cobertura leída, sin ejecución

| Archivo | Qué afirma o verifica su código |
|---|---|
| `app/tests/frontend/test_app.py:30-96` | Municipios agricultor, dos modelos analista, checks, búsqueda/filtros, mapa superior, comparador, presencia de datos propios y PDF básico. |
| `app/tests/frontend/test_panel_parcela.py:43-74` | Modelo oficial para productor, nueve municipios, diferencias reservada/registrada, ecuación, confianza/rango y mismos valores dentro de municipio. |
| `app/tests/frontend/test_cartera.py:14-29` | Posición primera, KPIs, mezcla de confianza, advertencia y tabla. |
| `app/tests/frontend/test_estimaciones.py:15-43` | Checks por modelo, columnas y 59 tarjetas HTML. No comprueba carrusel en viewport real. |
| `app/tests/frontend/test_ficha_tecnica.py:23-35` | Nombre/cifra del modelo activo y rama registrada. |
| `app/tests/frontend/test_validacion.py:32-83` | Población principal 135/675, auxiliares, confianza municipal, simulación y cambio de modelo. |
| `app/tests/frontend/test_validacion_presentacion.py:18-67,91-104` | Vacíos, valores heterogéneos sin promedios engañosos, escape, representación de 135 puntos/dominio/tooltip. |
| `app/tests/frontend/test_evidencia.py:28-120` | Orden de pestaña, filtros, vacío/reset, complementarias, catálogo, cambio de modelo y caché sensible a datos/umbral. |
| `app/tests/frontend/test_metodo_limites.py:23-59` | Pasos oficiales, métricas activas, cinco situaciones de alcance y textos de límites. |
| `app/tests/frontend/test_datos_propios.py:37-108` | ZIP de reto, predicciones/rangos/confianza/métricas y componente resultado con cifra/tabla. No recorre carga rechazada en el widget completo. |
| `app/tests/frontend/test_bitacora.py:40-77` | Libreta vacía/prepoblada, renglones, progreso y tablero. No realiza importación A→B ni comparación de pronóstico por campaña. |
| `app/tests/frontend/test_descargas_ficha.py:18-102` | Callback de PDF con modelo/confianza/calculadora, ambas vistas, respaldo y una página. No mide layout visual final. |
| `app/tests/frontend/test_filtros_analista.py:46-93` | Restaurar filtro sin resultados y conservar clave/modo, toast único, repetir intento y limpiar buscador. |
| `app/tests/frontend/test_tema.py:18-68` | Contraste de tokens claros/cabecera, mismo dataset del gráfico entre temas y cambio de apariencia sin cambiar cifras/vista. |

**UNKNOWN.** Resultado actual de esos scripts, calidad visual real y regresiones de bienvenida, conversación Cebi, importación de libreta y transición entre vistas. No se ejecutaron; las afirmaciones de la tabla son cobertura presente en los archivos, no un reporte de pruebas aprobadas.

## 10. Encaje de la propuesta de planeador (recomendaciones, sin contrato futuro)

**CONFIRMED.** La propuesta habla de tres «pantallas» en sus mensajes guía, pero su cambio de navegación C6 define sólo dos modos dentro de Agricultor. C1 y C2 son bloques dentro de la calculadora, no páginas separadas (`context/planeador_campaña.md:32-40,159-161,185-208,274-283`). **PROPOSED.** Tratar consulta, escenarios y respuesta al faltante como etapas de lectura de un mismo flujo; añadir una tercera navegación sería una decisión nueva que el texto no especifica.

**CONFIRMED.** Consulta rápida pide hectáreas antes del resumen y luego llama a una calculadora base que vuelve a dibujar los campos, incluyendo área. Propone una clave `calc_area_rapida`, pero no explica cómo una sola edición alimenta resumen, producción, tarjetas y tabla (`context/planeador_campaña.md:259,270,291-313`). **PROPOSED.** Definir un único dato de superficie editable en ese modo y una sola unidad visible, antes de implementación. Evitar dos áreas que puedan contradecirse es más importante que elegir su distribución.

**CONFIRMED.** El default registrado se propone para conservar las pruebas actuales; la decisión sigue abierta, mientras el objetivo de consulta rápida es permitir uso sin ID. Agricultor hoy inicia forzosamente desde una parcela de Chignahuapan (`context/planeador_campaña.md:276-283,455`; `app/agrocebada_app/frontend/vistas/agricultor/panel_parcela.py:74-88`). **PROPOSED.** Elegir el default por audiencia de entrada y hacer que las pruebas del flujo registrado seleccionen ese modo explícitamente. Ni continuidad visual ni falta de pruebas constituyen evidencia de preferencia de los productores.

**PROPOSED.** Reutilizar `.mini`, `.nota`, `.aviso` y contenedores de vidrio con tokens claro/oscuro para tres escenarios. En móvil, apilar tarjetas o utilizar la cuadrícula ya aplicada a KPIs; una barra con cuatro marcas necesita alternativa textual y manejo de marcas coincidentes, valores iguales, equilibrio fuera del rango y cifras largas. La propuesta ajusta escala, pero no resuelve colisión de etiquetas (`context/planeador_campaña.md:136-161,165-173`; patrones reales en `app/assets/css/tema.css:240-255,340-349`). No ocultar la falta de rango detrás de una barra vacía.

**PROPOSED.** Mantener nombre de cada escenario, t/ha, toneladas e ingreso menos costo; acompañar posición/color con cifras en texto. La fecha 2025 debe quedar próxima al rango y los escenarios. «Año bajo/alto» necesita revisión de significado porque los límites son distribución de parcelas en una sola campaña, no observaciones de años buenos/malos (`app/agrocebada_app/backend/dominio/rangos.py:1-3,25-28`; `context/planeador_campaña.md:124,169-170,491`).

**PROPOSED.** En la variante con cosecha registrada, conservar «Con tu cosecha registrada» en lugar de renombrarla «Típico»: esa cifra puede quedar fuera del rango municipal y no equivale al estadístico municipal (`app/agrocebada_app/frontend/vistas/agricultor/calculadora.py:30-33`; `context/planeador_campaña.md:173`). El orden de las marcas debe responder a sus valores, sin asumir que referencia queda entre escenario bajo y alto.

**PROPOSED.** Antes de compartir `calc_precio`/`calc_costo` entre modos, verificar un recorrido completo: escribir → cambiar modo → volver → abrir Cebi → descargar ficha. Conservar el nombre de una clave no demuestra retención de un widget desmontado. La propuesta advierte claves pero no incluye esta transición en sus pruebas de frontend (`context/planeador_campaña.md:262-270,389-396`; puntos vigentes en F-11).

**PROPOSED.** Separar dos usos de «normal»: el promedio climático 2022–2024 y la franja municipal de verdor no son la misma referencia. El título propuesto «Tu temporada 2025 frente a un año normal» debe revisarse frente a las dos tarjetas, manteniendo su fecha y procedencia junto al contenido (`context/planeador_campaña.md:218-226`; `app/agrocebada_app/frontend/vistas/agricultor/verdor_clima.py:46-47,54-81`).

**PROPOSED.** Tras una implementación autorizada, validar los dos temas y anchos 320/375/600/700/900/1400 px, nombres largos, zoom de texto y teclado en modal, selector de modo, barra y desplegable. La inspección estática ya identifica los breakpoints y focos sensibles; no sustituye esa comprobación visual.

## 11. Límites y entrega

No se han modificado fuentes, datos, dependencias, configuración ni pruebas. Esta auditoría sólo escribe este informe y la sección de resultados de su contrato. No se han contrastado despliegue real, navegadores, tiempos de carga, respuestas externas ni accesibilidad asistida. Los hallazgos de lógica se sustentan en ramas y dependencias citadas; cualquier efecto visual o limpieza real de widgets se mantiene explícitamente **UNKNOWN/INFERRED** hasta ejecutar verificaciones autorizadas.
