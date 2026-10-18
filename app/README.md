# AgroCebada 2026 · Estimación de rendimiento de cebada

Aplicación desarrollada con Streamlit para consultar estimaciones retrospectivas de la campaña 2025.

Utiliza información de 138 parcelas con rendimiento registrado para estimar el rendimiento de 59 parcelas reservadas, mediante el valor típico de su municipio.

Las estimaciones se verifican contra el archivo de referencia `predicciones_59_referencias.csv`, para comprobar que los resultados coincidan con los del procedimiento evaluado.sed -n '100,145p' README.md

## Arrancar

Desde la carpeta `app/` del repo:

```bash
pip install -r requirements.txt
python herramientas/preparar_datos.py     # una vez: arma datos_app/ (ver abajo)
streamlit run app.py
```

Se abre en http://localhost:8501. Si no encuentra el dataset del reto, fija su ruta con `AGRO_DATOS` (en PowerShell: `$env:AGRO_DATOS = "C:\ruta\al\repo\data\raw\DATASET_RETO_AGRO_2026"`).

**Versión de Streamlit:** `requirements.txt` pide `>=1.56,<1.66`. La descarga diferida de la ficha necesita 1.52 o más, las pruebas (`AppTest`) 1.56 o más, y con 1.66 el mapa 3D dio errores de WebGL en el navegador.

### Con Docker

La imagen del repo (`docker build -t agrocebada-entorno .` desde la raíz) trae Python 3.12 pero no Streamlit. Desde la raíz del repo, en PowerShell:

```powershell
docker run --rm -it -p 8501:8501 `
  -v "${PWD}:/proyecto" -w /proyecto/app `
  -e AGRO_DATOS=/proyecto/data/raw/DATASET_RETO_AGRO_2026 `
  agrocebada-entorno `
  bash -c "pip install -r requirements.txt && python herramientas/preparar_datos.py && streamlit run app.py --server.address 0.0.0.0"
```

## Datos que usa

La app lee el **paquete compacto `datos_app/`** (0.4 MB, parquet): parcelas con su geometría, series de índices 2025, clima mensual, validación de los dos modelos, las 59 oficiales y el soporte por parcela. Así arranca rápido y no necesita el dataset completo (~40 MB).

Si cambian T08, T03, T04 o el dataset, se regenera con:

```bash
cd app && python herramientas/preparar_datos.py
```

**En el repo del equipo `datos_app/` no se sube** (el `.gitignore` excluye los datos del reto). Cada quien lo arma una vez en su compu con `python herramientas/preparar_datos.py`; si no lo arma, la app lee directo las fuentes y sólo tarda un poco más en abrir.

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
├── herramientas/               # scripts que se corren a mano: preparar_datos.py y preparar_elevacion.py
└── tests/                      # backend/test_carga_segura.py y frontend/test_app.py
```

Las dependencias van en un solo sentido: `frontend → backend → config`. Ningún módulo de `backend/` importa Streamlit.

## Diseño

- Tema oscuro con paneles de vidrio flotando sobre el mapa.
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

**Selector de modelo:** Media · oficial (MAE 0.320, R² 0.659 en A · sin respaldo) o Mediana · en evaluación (MAE 0.313, R² 0.661 en A · sin respaldo). El modelo oficial se configura mediante `MODELO_OFICIAL` en `agrocebada_app/config.py`.

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

Streamlit necesita un servidor encendido con conexión permanente (WebSocket), así que **no corre en Vercel** (sus funciones se apagan al terminar cada petición). Opciones que sí funcionan directo desde el repo de GitHub: **Streamlit Community Cloud** (gratis; permite repo privado y limitar quién la ve), Hugging Face Spaces, Render o Railway. Antes de publicarla hay que confirmar que las reglas de FIRA permiten subir los datos del reto (`datos_app/` incluye polígonos y rendimientos).
