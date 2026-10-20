# AgroCebada 2026 · Estimación de rendimiento de cebada

Aplicación desarrollada con Streamlit para consultar estimaciones retrospectivas de la campaña 2025.

Utiliza información de 138 parcelas con rendimiento registrado para estimar el rendimiento de 59 parcelas reservadas, mediante el valor típico de su municipio.

Las estimaciones se verifican contra el archivo de referencia `predicciones_59_referencias.csv`, para comprobar que los resultados coincidan con los del procedimiento evaluado.

En **Agricultor** puedes elegir **Parcela del catálogo** o **Consulta rápida**. La consulta rápida permite elegir un municipio disponible y escribir tus hectáreas sin conocer un ID de parcela. Muestra su referencia histórica de 2025 y, al capturar precio y costo, compara tus cuentas en escenarios de rendimiento. El municipio y área de esta consulta se conservan separados de los de cada parcela; precio y costo se comparten entre ambos recorridos.

## Cómo correrla

La [validación del planeador](../docs/ai/planeador/fase-4/README.md) incluye evidencia funcional, capturas y límites. Desde la raíz puedes repetir sus comprobaciones con `.venv/Scripts/python.exe -B -X utf8 app/herramientas/verificar_planeador.py`; el ejecutor usa `app/` como directorio de trabajo para cargar su configuración.

La app lee el dataset del reto y las salidas de T03, T04 y T08 (no están en git; ver «Datos que usa»). Todos los comandos se dan desde la raíz del repo; en Windows (PowerShell) cambia `export X=...` por `$env:X = "..."` y `\` por `` ` ``.

### Sin Docker

1. **Python 3.12** (el mismo de la imagen de Docker y el que se probó).
2. **Entorno virtual** (`.venv/` ya está en `.gitignore`) e instalación:

   ```bash
   python3.12 -m venv .venv
   source .venv/bin/activate              # en PowerShell: .venv\Scripts\Activate.ps1
   pip install -r app/requirements.txt
   ```

3. **Dataset:** copia la carpeta `DATASET_RETO_AGRO_2026` a `data/` (queda en `data/DATASET_RETO_AGRO_2026/`; `data/` está ignorada por git). La app también la encuentra en `datos/` o en la raíz. Si está en otro lugar, fija `AGRO_DATOS` con la carpeta.
4. **Salidas de T03, T04 y T08:** la app las busca sola en `registro/t03`, `registro/t04` y `registro/t08` (las de T08, `predicciones_59_referencias.csv` y `predicciones_oof_referencias_*.csv`, hoy viven en `registro/t03/`). Si están en otro lugar, fija `AGRO_T03`, `AGRO_T04` y `AGRO_T08` con su carpeta; `AGRO_T04` acepta la carpeta o el archivo `clima_parcela_mes.csv`.
5. **Arrancar** (desde `app/`):

   ```bash
   cd app
   python herramientas/preparar_datos.py     # una vez: arma datos_app/ y la abre más rápido (opcional)
   streamlit run app.py
   ```

   Se abre en http://localhost:8501. Sin `datos_app/` la app lee directo las fuentes y sólo tarda un poco más en abrir. Si falta el dataset, muestra un mensaje que dice qué falta.

Variables de entorno (todas opcionales si las carpetas están donde la app las busca):

| Variable | Qué es |
|---|---|
| `AGRO_DATOS` | carpeta del dataset del reto |
| `AGRO_T03` | carpeta con `soporte_parcelas.csv` |
| `AGRO_T04` | carpeta o archivo `clima_parcela_mes.csv` |
| `AGRO_T08` | carpeta con `predicciones_59_referencias.csv` y `predicciones_oof_referencias_*.csv` |

**Voz en «Pregúntale a Cebi» (opcional).** Para que las preguntas habladas se pasen a texto hay que instalar el reconocimiento de voz, que no viene en `requirements.txt` porque pesa unos 300 MB y la app funciona sin él:

```sh
pip install faster-whisper
```

Corre en el mismo equipo que la app, sin clave ni internet. El modelo (~145 MB) se descarga la primera vez; con `AGRO_WHISPER` puede elegirse otro (`tiny`, `base`, `small`). Sin él no se dibuja el micrófono.

**El micrófono lo da el navegador, no la app.** Los navegadores sólo entregan el micrófono en un origen seguro: `localhost` o `https`. Abriendo la app por su URL de red (`http://192.168.x.x:8501`, la que Streamlit imprime para otros aparatos) el micrófono queda bloqueado por el navegador y no hay permiso que lo arregle; el chat sigue funcionando escribiendo. Para que la voz funcione hay que abrirla en el mismo equipo que la sirve, o servirla por `https`. En macOS además el navegador necesita estar habilitado en Ajustes del sistema → Privacidad y seguridad → Micrófono. Cuando el navegador no lo entrega, Cebi lo dice en español junto al micrófono.

**Versión de Streamlit:** `requirements.txt` pide `>=1.65,<1.66` para configurar el fondo y el texto de las cabeceras nativas de las tablas con contraste suficiente. Con 1.66 el mapa 3D dio errores de WebGL en el navegador.

### Con Docker

`app/Dockerfile` (Python 3.12, usuario sin privilegios) instala las dependencias y copia sólo el código. **Los datos nunca van dentro de la imagen**: `app/.dockerignore` deja fuera `datos_app/`, los CSV, los parquet y los shapefiles, y los datos se montan como carpetas de sólo lectura al correr el contenedor.

```bash
docker build -t agrocebada-app app

docker run --rm -p 8501:8501 \
  -v "$PWD/data/DATASET_RETO_AGRO_2026:/datos:ro" \
  -v "$PWD/registro:/registro:ro" \
  -e AGRO_DATOS=/datos -e AGRO_T03=/registro/t03 -e AGRO_T08=/registro/t03 -e AGRO_T04=/registro/t04 \
  agrocebada-app
```

Se abre en http://localhost:8501. (En PowerShell: `-v "${PWD}/data/DATASET_RETO_AGRO_2026:/datos:ro"` y el continuador de línea es `` ` ``.)

> **Estado de la prueba:** el `Dockerfile` y el `.dockerignore` **no se probaron** al escribirlos (la máquina donde se hicieron no tenía Docker). Lo que sí se comprobó: que `app/requirements.txt` instala en un entorno limpio de Python 3.12 y que con él pasan todas las pruebas y la app arranca desde la raíz del repo. Antes de usarlo, construir la imagen y abrir la app una vez.

La imagen del repo (`docker build -t agrocebada-entorno .` en la raíz) es otra: sirve para el trabajo de análisis, no trae Streamlit.

## Datos que usa

La app lee el **paquete compacto `datos_app/`** (0.4 MB, parquet): parcelas con su geometría, series de índices 2025, clima mensual, validación de los dos modelos, las 59 oficiales y el soporte por parcela. Así arranca rápido y no necesita el dataset completo (~40 MB).

Si cambian T08, T03, T04 o el dataset, se regenera con:

```bash
cd app && python herramientas/preparar_datos.py
```

**En el repo del equipo `datos_app/` no se sube** (el `.gitignore` excluye los datos del reto). Cada quien lo arma una vez en su compu con `python herramientas/preparar_datos.py`; si no lo arma, la app lee directo las fuentes y sólo tarda un poco más en abrir.

### La tabla única de cifras (M03) y el cierre del modelo (M17)

Las cifras que publican el informe, el video y la entrega **no se escriben a mano**: salen de una sola tabla, la
misma que descarga el botón «Descargar cifras» de la vista Analista. Se regenera con:

```bash
cd app && python herramientas/exportar_cifras.py
```

Escribe tres archivos en `registro/t17/`: `cifras_parcelas.csv` (una fila por cada una de las 197 parcelas, con
estimación, confianza, motivo, rango y producción), `cifras_municipios.csv` y `cifras_validacion.csv`. Toma el
modelo de `MODELO_OFICIAL` en `agrocebada_app/config.py`, así que **se vuelve a correr cada vez que cambie una
cifra o el modelo oficial**; si no, el informe y la app dejan de decir lo mismo. Acepta una carpeta de salida como
argumento si se quiere comparar sin sobrescribir el registro.

Que las 59 estimaciones de la app sean idénticas a la entrega de T18 lo comprueba
`tests/backend/test_exportar.py`, parcela por parcela contra `registro/t18/predicciones_finales.csv`. Esa
comprobación no se salta: si el archivo falta, la prueba falla diciendo por qué.

`herramientas/preparar_datos.py` (y la app, si no hay `datos_app/`) lee las fuentes originales: el dataset del reto (en la raíz del repo, en `data/` o en `datos/`; o donde diga `AGRO_DATOS`), `registro/t08` (o `entregas/T08`), `registro/t03` (o `entregas/T03`) y `registro/t04/clima_parcela_mes.csv` (o `entregas/T04/...`). Ubica sola la raíz del repo; si las fuentes están en otro lugar, fíjalas con `AGRO_DATOS`, `AGRO_T08`, `AGRO_T03` y `AGRO_T04`. Si `datos_app/` no existe, la app lee directamente esas fuentes (más lento).

## Estructura de `app/`

```
app/
├── app.py                      # punto de entrada (38 líneas): arranca la página y elige la vista
├── requirements.txt
├── .streamlit/config.toml
├── agrocebada_app/             # paquete de la app
│   ├── config.py               # constantes: modelos, temporada, URLs del mapa, textos fijos
│   ├── backend/                # sin Streamlit; se prueba en aislado
│   │   ├── rutas/              #   dónde están el dataset, T08, T03 y T04
│   │   ├── datos/              #   lectura de las fuentes, del paquete datos_app/ y de la altitud
│   │   ├── modelo/             #   procedimiento de T08 (estimador) y métricas
│   │   ├── dominio/            #   avisos, resúmenes, notas, geometría y escala de color
│   │   ├── carga_segura/       #   revisión de un dataset propio (ZIP o CSV)
│   │   └── ficha_pdf/          #   la ficha de parcela en PDF
│   └── frontend/               # todo lo que usa Streamlit, pydeck o altair
│       ├── tema/               #   CSS, mascota y helpers de HTML
│       ├── estado/             #   caché de datos, sesión y el Contexto que comparten las vistas
│       ├── componentes/        #   mapa, gráficas, paneles y botón de la ficha
│       └── vistas/             #   agricultor, analista (una pestaña por archivo) y datos propios
├── assets/                     # mascota/ (Cebi, SVG y PNG) y css/tema.css
├── datos_estaticos/            # altitud de cada parcela (elevacion_parcelas.csv)
├── herramientas/               # scripts que se corren a mano: preparar_datos.py, exportar_cifras.py y preparar_elevacion.py
└── tests/                      # backend/test_carga_segura.py y frontend/test_app.py
```

Las dependencias van en un solo sentido: `frontend → backend → config`. Ningún módulo de `backend/` importa Streamlit.

## Diseño

- **Modo claro predeterminado**, con marfil y verde bosque. El interruptor compacto de sol/luna, al final de la barra superior, cambia la apariencia sin perder filtros ni cifras. La elección se conserva durante la sesión; una sesión nueva empieza en claro. El oscuro mantiene los paneles de vidrio y su paleta original.
- Los estilos compartidos viven en `assets/css/tema.css`; `claro.css` cambia sus variables de color y adapta los controles nativos. Las tarjetas del mapa conservan un vidrio blanco translúcido con desenfoque y texto oscuro. Las gráficas usan `frontend/tema/paleta.py`, y `frontend/tema/tablas.py` adapta las celdas sin perder las tablas interactivas. Las cabeceras usan fondo salvia y texto bosque, configurados en `.streamlit/config.toml` y compartidos por ambos modos. La bienvenida y Cebi usan las mismas variables. El PDF y los colores que representan rendimiento o confianza en el mapa conservan sus escalas.
- El **mapa 3D es el protagonista**: cada parcela es un bloque con su forma real; la altura y el color son las t/ha (paja → verde → menta). Las parcelas por estimar llevan borde blanco y la elegida va en naranja.
- Las parcelas se apoyan sobre el **relieve real** (Terrain Tiles de AWS) con **imagen Sentinel-2 sin nubes** (EOX). El botón «Satélite» la apaga si la conexión es lenta.
- Dos vistas del mapa (junto a la leyenda): **3D** y **Desde arriba** (polígonos de color sobre la imagen, como un mapa de cultivos).
- **Al pasar el ratón por una parcela** aparece su detalle: estimación y error típico, área y producción, de dónde sale la cifra y sus avisos (o, si tiene cosecha, el valor registrado y lo que estimó el método sin conocerla).
- **Seleccionar:** clic en una parcela del mapa y pasa a ser la elegida: se pinta de naranja, las demás se atenúan y el panel cambia a ella. El mapa no se recarga ni se mueve: conserva el zoom y la posición. Al pasar el ratón, la parcela se pinta de amarillo claro. Elegir una parcela en los selectores sí centra el mapa en ella.
- **Zoom:** rueda del ratón o pellizco del trackpad (acerca hacia donde apuntas, hasta muy cerca), botones + y − o doble clic. Alejar tiene un límite para no perder las parcelas. Para bajar en la página, pon el cursor fuera del mapa. En 3D, girar con Shift (o Ctrl/Cmd) + arrastrar.
- Gráficas y tablas se abren a pantalla completa.
- Mascota: **Cebi**, un grano de cebada que brota. Está animado sólo con CSS: llega al abrir la página, parpadea, mece el brote y da saltitos; en la tarjeta «Cómo leer» llega caminando. Si el sistema pide reducir el movimiento, se queda quieto.
- En celular los paneles se acomodan debajo del mapa.

**Necesita internet para el fondo del mapa** (imagen, relieve y el componente que lo dibuja, que deck.gl carga de unpkg.com). Sin conexión, todo lo demás funciona y las parcelas se ven sobre fondo liso.

## Dos vistas (barra superior)

### Agricultor

| Bloque | Qué muestra |
|---|---|
| Panel «Tu parcela» | Municipio y parcela, rendimiento estimado (t/ha), producción estimada (t/ha × ha), error típico del municipio, de dónde sale la cifra, avisos y el botón **Descargar ficha (PDF)**. |
| Mapa | La parcela en naranja y sus vecinas a ~6 km; panel con área, altitud, lluvia de la temporada, verdor máximo y fecha de corte. |
| Verdor y clima | Curva de NDVI 2025 por sensor y lluvia/temperatura del mes, como contexto. |
| Pregúntale a Cebi | Mascota flotante sin fondo abajo a la derecha: salta y parpadea al pasar el mouse y abre una conversación con accesos breves a las preguntas originales. Conserva los últimos cuatro intercambios por parcela y permite empezar de nuevo. Usa los mismos datos y valores de la calculadora. Se cierra con la **✕** del encabezado, con Escape o al pulsar fuera; la ✕ está porque las otras dos no se ven. Streamlit no deja cerrar un popover desde Python, así que la ✕ le cambia la llave y vuelve a nacer cerrado —la conversación no se pierde, vive en la sesión y no en el popover—. Al abrirla pregunta qué quieres explorar, con dos pastillas: **Mi parcela** y **Mi cuenta**; al escoger salen las preguntas de ese tema y «Cambiar de tema» vuelve a las dos. **Mi parcela** trae nueve accesos en las parcelas por estimar y siete en las que ya tienen cosecha: de dónde sale la cifra, cuántas toneladas son en toda la parcela, los vecinos, la confianza, de cuánto puede fallar, los costos, el satélite, el clima y qué la haría más precisa. **Mi cuenta** trae tres, que salen de la misma cuenta que la calculadora «¿Me alcanza?» (`backend/dominio/planeador.py`, sin recalcular ni redactar nada aparte): cuánto necesitas sacar para no perder, qué pasa si el año sale bajo o alto y qué hacer si no alcanza; sin precio y costo piden escribirlos. Si se borra la superficie de la calculadora, Cebi también deja la cuenta pendiente. Además de los accesos, acepta preguntas escritas y habladas: el enrutador (`backend/dominio/enrutador.py`) empareja lo que se dice con una de las respuestas que ya calcula del dato y, si no la reconoce, lo admite en vez de inventar —Cebi elige, nunca redacta, así que no puede afirmar lo que el método no hace—. El micrófono va junto al campo de escribir, no escondido, y se encoge al botón redondo mientras no se graba. La voz se transcribe en el equipo que sirve la app (`backend/dominio/transcribir.py`), no en el navegador, para que funcione igual en cualquier teléfono; es **opcional**: sin `faster-whisper` instalado el micrófono no se dibuja y todo lo demás sigue funcionando. Respeta movimiento reducido. Estilos en `assets/css/cebi.css`, adaptados a ambos temas. |
| Tu libreta | El productor anota lo que de verdad cosechó cada año —año, toneladas de toda la parcela y una nota— y cada renglón le muestra por cuánto le atinó o le falló la app. Debajo, sólo cuando ya hay algo escrito: cuántos vecinos le faltan a su municipio para subir de confianza (la regla de M01 leída hacia adelante) y un tablero plegado con promedio, mejor año y gráfica. La nota se puede **dictar**: el micrófono vive fuera del formulario a propósito, porque dentro Streamlit no entrega el audio hasta enviarlo y la transcripción se guardaría sin que nadie pudiera corregirla; así cae en el campo y se revisa antes de anotar. La grabación se queda con su año y se vuelve a oír desde su renglón, de modo que grabar la del año siguiente no borra la anterior. **Nada sale del navegador**: la libreta vive en la sesión y se descarga como un CSV suyo, que puede volver a subir para seguir anotando. El CSV lleva lo escrito, no el audio: un minuto de grabación pesa más que toda la bitácora y volvería el archivo inservible para abrirlo en otro lado, así que las notas de voz viven sólo mientras la pantalla siga abierta, y la pantalla lo dice. Reglas y cuentas en `backend/dominio/bitacora.py`. |
| Cómo leer | Tarjeta con Cebi que explica qué es y qué no es la cifra. |

**Ficha PDF** (una página A4, se arma al hacer clic): parcela, cifra grande, producción, error típico, nota, avisos, mapa con la parcela y sus vecinas (con escala de 1 km), verdor y clima.

### Analista

Mapa de las 197 parcelas con panel de resumen (59, promedio, MAE y R²) y filtros (todas / las 59 / las 138, municipio y buscador por ID). Pestañas:

| Pestaña | Contenido |
|---|---|
| Las 59 estimaciones | Verificaciones (59 IDs, sin duplicados, valores finitos y coincidencia con el archivo de referencia), descarga del CSV y tabla completa. |
| Ficha técnica | Estimación, referencia territorial, MAE del municipio, ficha PDF, disponibilidad de datos por sensor, curva NDVI/EVI/LAI, clima y **Comparar parcelas** (hasta 3: curvas juntas y tabla con rendimiento, área, NDVI máximo y lluvia). |
| Validación | MAE, RMSE, sesgo y R² de los escenarios A y B, resultados por municipio, registrado contra estimado e información insuficiente. |
| Método y límites | Cómo se calcula (4 pasos), qué tan bien funciona, fuentes y límites. |
| Analizar tus datos | Subir un dataset propio y aplicarle el mismo procedimiento (ver abajo). |

**Selector de modelo:** Mediana · oficial (MAE 0.313, R² 0.661 en A · sin respaldo) o Media · referencia (MAE 0.320, R² 0.659 en A · sin respaldo). El modelo oficial se configura mediante `MODELO_OFICIAL` en `agrocebada_app/config.py`.

## Analizar tus datos (carga segura)

Se aceptan **sólo dos formatos**:

1. **ZIP como el del reto (con mapa):** una tabla `.csv` (UTF-8, comas) con `ID_POLIGONO`, `AREA_HA`, `RENDIMIENTO_T_HA` y `CONJUNTO` (`ENTRENAMIENTO` con rendimiento entre 0.1 y 15 t/ha, o `PREDICCION` con el rendimiento vacío), más el shapefile de las parcelas (`.shp`, `.shx`, `.dbf`, `.prj`, sueltos o en un `.zip` interno) con `ID_POLIGON`, `Municipio` y `Cultivo`.
2. **CSV simple (sin mapa):** `ID_POLIGONO`, `MUNICIPIO`, `GRUPO`, `AREA_HA`, `RENDIMIENTO_T_HA`, `CONJUNTO`. Hay una plantilla para descargar.

La aplicación muestra la revisión del archivo, las estimaciones calculadas con el procedimiento del modelo seleccionado, una validación rápida dejando una parcela fuera, el mapa (cuando el archivo incluye información geográfica) y la descarga del CSV.

**Se rechaza con un motivo concreto:** cualquier otro tipo de archivo (Excel, PDF, imágenes, programas, scripts), contenido que no corresponde a su extensión, más de 50 MB, ZIP con más de 30 archivos, más de 200 MB descomprimido, compresión sospechosa (bomba zip), contraseña, rutas que salen de la carpeta, enlaces, más de 5,000 parcelas, menos de 10 con cosecha o ninguna por estimar, IDs repetidos, con caracteres raros o que no coinciden entre tabla y polígonos, valores fuera de rango y polígonos inválidos o fuera de México.

Nada del archivo se ejecuta: se lee como datos, los archivos se escriben con nombres propios en una carpeta temporal que se borra al terminar, y el resultado vive sólo en la sesión de quien lo subió.

## Cómo se probó

```bash
cd app
python tests/frontend/test_app.py            # termina en «OK»
python tests/backend/test_carga_segura.py   # termina en «OK»
for t in tests/*/test_*.py; do python "$t" || break; done     # todas, una por una; cada una termina en «OK»
```

- `tests/frontend/test_app.py`: vista agricultor con los 9 municipios; vista analista con los dos modelos (4 verificaciones en verde y métricas de validación A · sin respaldo); buscador, filtro por municipio, información insuficiente, mapa desde arriba, comparación de parcelas, pestaña de datos propios y ficha PDF de 3 parcelas.
- `tests/backend/test_carga_segura.py`: el ZIP del reto produce las mismas 59 estimaciones que el archivo de referencia; ZIP con shapefile suelto y CSV simple aceptados; 17 archivos malos rechazados (Excel, imagen, ZIP falso, PDF renombrado, CSV cualquiera, programa y script dentro del ZIP, ruta tramposa, bomba zip, demasiados archivos, tabla sin polígonos, IDs que no coinciden, rendimientos fuera de rango, IDs repetidos, ID con código, plantilla sola y archivo de más de 50 MB).
- Navegador (Chromium): capturas de las dos vistas, descarga de la ficha, recuadro del mapa, comparación y subida de un archivo bueno y uno malo.

## Créditos del mapa

- Imagen: Sentinel-2 cloudless 2021 de EOX IT Services GmbH (https://s2maps.eu), contiene datos Copernicus Sentinel modificados. Licencia CC BY-NC-SA 4.0: uso no comercial con atribución (la app la muestra bajo el mapa).
- Relieve: Terrain Tiles, AWS Open Data. Mapa base: CARTO y OpenStreetMap.

## Seguridad

- **El código no llega al navegador.** Streamlit ejecuta `app.py` y los módulos en el servidor; el navegador sólo recibe la interfaz genérica de Streamlit y los resultados que se muestran (cifras, tablas, gráficas y polígonos del mapa). No hay forma de ver el código Python ni el procedimiento desde «Inspeccionar». Lo que sí se ve es lo que la página muestra, como en cualquier sitio web.
- Errores: `showErrorDetails = "none"`; si algo falla, el navegador sólo ve un aviso genérico, sin rutas, código ni trazas (quedan en la consola del servidor).
- Sin claves ni secretos; las fuentes del mapa no piden token.
- Subida de archivos: límite de 50 MB en Streamlit y en la app, protección XSRF activa y las reglas de la sección anterior.
- No se sirve ningún archivo de la carpeta (`enableStaticServing = false`), no hay menú de desarrollador ni botón Deploy (`toolbarMode = "viewer"`) y no se vigilan cambios de código en producción.
- El HTML propio (estilos, paneles y leyenda) es fijo; los textos que vienen de los datos se escapan antes de mostrarse y los IDs subidos sólo pueden tener letras, números, `_`, `.`, `-` y espacio.

## Publicarla en internet

**Todavía no está publicada: falta que FIRA autorice subir los datos del reto** (`datos_app/` incluye polígonos y rendimientos). Hasta entonces no se sube nada.

Streamlit necesita un servidor encendido con conexión permanente (WebSocket), así que **no corre en Vercel** (sus funciones se apagan al terminar cada petición). Opciones que sí funcionan directo desde el repo de GitHub: **Streamlit Community Cloud** (gratis; permite repo privado y limitar quién la ve), Hugging Face Spaces, Render o Railway.

### Streamlit Community Cloud: revisión

| Punto | Estado |
|---|---|
| Dependencias | `app/requirements.txt` sirve. Community Cloud busca el archivo primero junto al archivo principal y después en la raíz, así que gana el de `app/` sobre el `requirements.txt` de la raíz (el del entorno de análisis). Instala en un entorno limpio de Python 3.12 y con él pasan las pruebas. |
| Versión de Python | Se elige al desplegar (en «Advanced settings»). Elegir **3.12**, la que se probó. |
| `config.toml` | **Falta mover algo.** Community Cloud lee `.streamlit/config.toml` de la **raíz del repo**, aunque el archivo principal esté en una subcarpeta, y hoy está en `app/.streamlit/config.toml`. Sin copiarlo a la raíz no se aplicarían el tema, `toolbarMode = "viewer"` ni `showErrorDetails = "none"` (que oculta rutas y trazas). |
| Carpeta de trabajo | La raíz del repo. La app ubica sus archivos con rutas absolutas desde el código, así que no depende de ella (se probó arrancándola desde la raíz). |
| Claves | No usa; no hace falta configurar secretos. |

### Pasos para publicarla (cuando FIRA autorice)

1. Confirmar por escrito con FIRA que se pueden subir los datos y con qué condiciones. Si no, usar la ejecución local o Docker.
2. Copiar `app/.streamlit/config.toml` a `.streamlit/config.toml` en la raíz del repo (un PR aparte).
3. Resolver los datos (ver abajo) antes de desplegar.
4. En https://share.streamlit.io: «Create app» → repositorio `danielalira20/AgroCebada-2026`, la rama que decida el equipo, archivo principal `app/app.py`.
5. En «Advanced settings»: Python 3.12; no hay secretos que agregar.
6. Elegir quién la ve: repo privado y, en el panel de la app, compartirla sólo con las personas autorizadas.
7. Al abrirla, revisar que cargue el mapa y las dos vistas, y descargar una ficha.

### Datos que necesitaría la nube

El repo no trae los datos del reto (`.gitignore`), así que sin ellos la app sólo muestra el aviso de que falta el dataset. El mínimo es el paquete compacto **`datos_app/`** (unos 0.4 MB: parcelas con geometría, series de índices 2025, clima, validación de los dos modelos, las 59 oficiales, soporte y, si se arma con `preparar_datos.py`, el clima 2022–2024). Se genera en una computadora que tenga el dataset (`python herramientas/preparar_datos.py`). Dos formas de llevarlo a la nube:

- **En un repo privado**, agregándolo con `git add -f app/datos_app` (el `.gitignore` lo excluye a propósito). Sólo si FIRA lo autoriza; es lo más simple.
- **Fuera de git**, en un almacenamiento privado, y que la app lo descargue al arrancar con una dirección guardada en los secretos de Streamlit. Requiere un cambio en el código que hoy no existe.

### Fondo del mapa

La app pide al navegador, sin clave: imagen Sentinel-2 de EOX (`tiles.maps.eox.at`), relieve de AWS (`s3.amazonaws.com/elevation-tiles-prod`), estilo de CARTO y, para el mapa, bibliotecas desde `unpkg.com`. EOX es CC BY-NC-SA: uso no comercial con atribución (la app la muestra). Si alguna de estas fuentes se cae, el mapa pierde el fondo pero las cifras no cambian.
