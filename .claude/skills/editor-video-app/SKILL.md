---
name: "editor-video-app"
description: "Arma videos de presentación de una app o plataforma web con Remotion a partir de grabaciones de pantalla: pantalla en laptop o celular inclinada en 3D, acercamientos a lo importante, textos animados, contadores, clics resaltados, transiciones y cortes al ritmo de la música, en 16:9 y 9:16. Primero propone el guion escena por escena. Úsala siempre que pidan editar, montar o armar un video, demo, tráiler o video promocional de una app o plataforma (por ejemplo AgroCebada), aunque no mencionen Remotion."
---

# Editor de video de app (presentación de una plataforma)

Convierte grabaciones de pantalla de una app o plataforma web en un video tipo lanzamiento: la pantalla dentro de una laptop o celular, acercamientos a lo importante, textos animados entre escenas, clics resaltados y cortes al ritmo de la música. Salen dos versiones: **16:9 (1920x1080)** para jurado, web o presentación, y **9:16 (1080x1920)** para TikTok o Reels.

Responder en español, conciso. Entregar versiones numeradas (v1, v2…) sin sobrescribir las anteriores.

Requisitos: Node 18+, ffmpeg y Python 3. Remotion usa Chrome o Chromium para renderizar.

## Índice
1. Qué pedir y revisar antes de editar
2. Guion (storyboard)
3. Estilo por defecto
4. Preparar los clips
5. Composición en Remotion
6. Versión vertical
7. Audio
8. Revisión y entrega
9. Ejemplo: AgroCebada

## 1. Qué pedir y revisar antes de editar
- **Clips:** una carpeta con grabaciones numeradas (`01_mapa.mov`, `02_parcela.mov`…), una acción por clip. Si están todas en un solo archivo largo, cortar por cambios de pantalla (§4).
- **Para qué es:** jurado, redes, demo interna. Define duración y tono. Si es para un concurso, preguntar si las bases fijan duración, formato o idioma, y respetarlas.
- **Marca:** logo, mascota, colores y nombre del producto. Buscarlos en el repo (`assets/`, SVG/PNG) antes de pedirlos.
- **Voz:** ¿lleva voz en off? Si sí, se graba aparte y se limpia antes de montar: quitar silencios largos, trabas y tomas repetidas (`silencedetect` de ffmpeg; transcribir con Whisper si está disponible para alinear subtítulos).
- **Estilo de referencia:** si pasan un enlace de TikTok, YouTube o Instagram, desde aquí no se puede ver el video. Pedir 3 a 6 capturas (inicio, una transición, un texto, un acercamiento y el cierre) o que describan qué les gusta. Traducirlo a las decisiones de §3 (marco, inclinación, textos, transiciones, ritmo) y anotar en el guion qué se tomó de la referencia.
- **Música:** pedir la pista o usar una libre de derechos. Avisar que una canción con copyright puede silenciarse en redes.

Revisar cada clip con `ffprobe` (resolución, fps, duración, códec) y una hoja de contacto (§4). Si un clip se ve entrecortado (por ejemplo, un mapa 3D que tartamudea), no se arregla en edición: pedir que se vuelva a grabar con la aceleración por hardware del navegador encendida.

## 2. Guion (storyboard)
Antes de tocar Remotion, escribir el guion como tabla o JSON y mostrárselo al usuario. Así se corrige el orden barato, antes de renderizar.

Estructura que funciona (45–90 s):
1. **Gancho (0–3 s):** la toma más impresionante, sin texto o con 2–4 palabras. Nada de logos lentos al inicio.
2. **El problema (1 tarjeta de texto):** una frase de quién lo usa y qué necesita.
3. **3 a 5 funciones:** una escena cada una. Patrón: tarjeta de texto corta, clip con acercamiento al detalle y clic resaltado.
4. **Prueba o confianza:** una cifra o resultado real tomado de la pantalla.
5. **Cierre:** toma abierta y quieta del producto, logo o mascota, nombre del equipo, y enlace o QR si existe.

Reglas:
- **Escenas cortas:** 2–4 s por toma, hasta 6 s si se lee algo.
- **Una idea por escena.**
- **Texto en pantalla de 6 palabras o menos.**
- **Honestidad:** todo lo que diga un texto debe ser verdad de la app. Las cifras se copian de la pantalla, nunca se inventan ni se redondean distinto. Nada de prometer funciones que no existen. Si la app es una estimación o tiene límites, el texto no la vende como certeza. En un video para jurado, exagerar resta.

Formato del guion (`storyboard.json`):
```json
{
  "fps": 60,
  "escenas": [
    {"id": "gancho", "clip": "01_mapa.mov", "in": 2.0, "out": 6.5, "vel": 1.0,
     "camara": [{"t": 0, "roi": [0, 0, 1, 1]}, {"t": 4.5, "roi": [0.30, 0.25, 0.45, 0.45]}],
     "clics": [], "texto": null, "transicion": "fade"},
    {"id": "t_confianza", "tarjeta": "¿Qué tanto confiar?", "dur": 1.6, "transicion": "slide"}
  ]
}
```
- **`roi`** es la zona a encuadrar en fracciones del clip original: `[x, y, ancho, alto]`, entre 0 y 1. `[0, 0, 1, 1]` es la pantalla completa.
- **`t`** está en segundos dentro de la escena.
- **`vel`** acelera la escena (2–4) en partes aburridas, como esperas o al escribir.

## 3. Estilo por defecto
Limpio, sin filtros y con colores naturales.
- **Fondo:** degradado oscuro con el color de la marca o la misma app muy desenfocada detrás, nunca negro plano.
- **Marco:**
  - **Laptop o navegador:** la grabación dentro de un marco con esquinas redondeadas (~18 px a 1080p), barra superior mínima y sombra suave grande.
  - **Celular:** marco con esquinas de ~60 px.
  - Sin modelos 3D pesados: un marco hecho con divs y CSS basta.
- **Inclinación 3D:**
  - Al entrar una escena, la pantalla llega inclinada (rotateX 8–12°, rotateY −10–15°, perspectiva ~1600 px) y se endereza con spring.
  - Mientras hay que leer algo, queda plana.
  - Cambiar el ángulo entre escenas, sin repetir el mismo dos veces seguidas.
- **Cámara:**
  - Acercamientos suaves a la ROI con `Easing.bezier(0.65, 0, 0.35, 1)`, de 0.6–0.9 s, y luego quieta 1.5–3 s.
  - Máximo ~1.5x si la grabación está a la misma resolución que la salida; hasta ~2.2x si se grabó en Retina (2x). Más que eso se ve borroso.
- **Clics:** un anillo que crece y se desvanece (~0.4 s, blanco al 80 % o color de la marca) donde se dio clic. Opcional: un leve "pulso" (escala 0.98→1) de la pantalla en el clic.
- **Tarjetas de texto:**
  - Inter 900, palabras grandes que entran una por una con spring.
  - Palabra clave en el color de la marca.
  - Opcional: placa "glass" (vidrio translúcido: relleno blanco al 17 %, borde blanco al 55 %, sombra suave y lo de atrás desenfocado) con un ícono de líneas que se dibuja solo.
  - De 1.2 a 2 s en pantalla.
- **Contadores:** cuando la app muestra una cifra clave (por ejemplo 1,550 t), se puede repetir grande junto a la pantalla contando desde 0 hasta el valor exacto que se ve en el clip, en ~0.8 s.
- **Transiciones:** rápidas (8–12 cuadros), elegidas entre barrido con desenfoque de movimiento, escala a través, deslizamiento o fade. Nada de transiciones de plantilla (estrellas, cubos).
- **Ritmo:** los cortes caen en los tiempos fuertes de la música (§7).
- **Datos sensibles:** antes de renderizar, revisar que no salgan correos, rutas personales, tokens, pestañas privadas ni notificaciones. Si salen, desenfocar esa zona o recortar.

## 4. Preparar los clips
Las grabaciones de pantalla de macOS suelen venir a 60 fps variables y en Retina (por ejemplo, 2880x1800).
1. **Normalizar** a fps constante sin perder nitidez:
   `ffmpeg -i in.mov -vf fps=60 -c:v libx264 -crf 14 -preset slow -pix_fmt yuv420p -colorspace bt709 -color_primaries bt709 -color_trc bt709 -an norm/01.mp4`
   Comparar un cuadro con el original. Si se ve lavado o más oscuro, revisar las etiquetas de color.
2. **Hojas de contacto** con cuadrícula para elegir ROIs: un cuadro cada 0.5 s, `tile`, y encima líneas cada 10 % con etiquetas, para leer coordenadas en fracciones. Usarlas para escribir `roi` y `clics` en el guion.
3. **Encontrar esperas y momentos clave:**
   - Esperas y pantallas congeladas, para cortarlas o acelerarlas: `ffmpeg -i norm/01.mp4 -vf freezedetect=n=0.003:d=0.8 -f null -`.
   - Cambios de pantalla, que suelen ser justo después de un clic: `ffmpeg -i norm/01.mp4 -vf "select='gt(scene,0.02)',showinfo" -f null -`. Confirmar viendo los cuadros.
4. **Quedarse con la mejor toma** de cada acción (la más fluida y sin titubeos del ratón) y descartar el resto.

## 5. Composición en Remotion
Proyecto dirigido por datos: los componentes leen `storyboard.json`. Para corregir algo casi siempre basta con editar el JSON y volver a renderizar.
- **Composiciones:** `Promo` (1920x1080, 60 fps) y `PromoVertical` (1080x1920, 60 fps). Usan las mismas escenas con distinto acomodo.
- **Escenas:** con `TransitionSeries` de `@remotion/transitions` (presentaciones `fade`, `slide` y `wipe`; timing con `springTiming` o `linearTiming`).
- **Video:**
  - `<OffthreadVideo>` con recorte de inicio y fin: `startFrom`/`endAt`, o `trimBefore`/`trimAfter` según la versión instalada.
  - `playbackRate` para la velocidad, `muted`.
  - Copiar los clips normalizados a `public/` y llamarlos con `staticFile()`.
- **Cámara:**
  - Un contenedor del tamaño del clip original con `transform: scale(s) translate(...)`, calculado con `interpolate` entre los puntos `camara` del guion.
  - La ROI se convierte a escala y desplazamiento para que llene el marco sin bordes vacíos.
- **Componentes:**
  - `MarcoLaptop` y `MarcoCelular`.
  - `Inclinacion` (spring a 0° en la entrada).
  - `Clic` (anillo).
  - `Tarjeta` (texto por palabras; placa glass opcional).
  - `Contador`.
  - `Logo`: si la mascota es SVG, animarla con CSS o spring, como la intro de Cebi.
- **Instalación:** `npm i remotion @remotion/cli @remotion/transitions @remotion/renderer @remotion/bundler react react-dom`, más la fuente Inter (`https://raw.githubusercontent.com/google/fonts/main/ofl/inter/Inter%5Bopsz%2Cwght%5D.ttf`).
- **Fotos fijas antes del render:** `npx remotion still Promo` en 8–12 tiempos clave, armar una hoja de contacto y revisarla (texto legible, nada cortado ni borroso, ROI correcta) antes del render completo.
- **Render:** `npx remotion render Promo out/promo_v1.mp4 --codec=h264 --crf=16` (y lo mismo con `PromoVertical`). Si Remotion no encuentra el navegador, pasar `--browser-executable` con la ruta de Chrome o Chromium.

## 6. Versión vertical
No es recortar el 16:9 al centro: la app de escritorio se volvería ilegible.
- La mitad de abajo muestra la ROI ampliada (el panel o la cifra importante) dentro de un marco con esquinas redondeadas. Arriba van el texto grande y la palabra clave.
- Las tomas de pantalla completa (el mapa, por ejemplo) pueden ir como 16:9 dentro del 9:16 con fondo desenfocado de la misma toma.
- Si hay clips grabados en celular, se usan completos dentro de `MarcoCelular`.
- Subtítulos de la voz en off: en la parte media-baja, en estilo karaoke: palabra por palabra, con las que faltan por decir al 55 % de opacidad.

## 7. Audio
- **Sin voz:**
  - Música a ~-14 LUFS integrado.
  - Fade-in de 1 s y fade-out de 2–3 s sobre el logo.
  - Un "whoosh" suave opcional en las transiciones, a -20 dB respecto a la música.
- **Con voz:** la voz va al frente. Voz con `highpass=f=70` y `acompressor`, a ~-19 LUFS. La música baja sola cuando hay voz con `sidechaincompress=threshold=0.04:ratio=3:attack=25:release=450` (voz como sidechain). Mezcla final con `amix=normalize=0` y `alimiter=limit=0.89`, a ~-14 LUFS.
- **Cortes al ritmo:**
  - Detectar los tiempos fuertes con `librosa` (`pip install librosa`; `librosa.beat.beat_track`) y guardar `beats.json`.
  - Ajustar el inicio de cada escena al tiempo fuerte más cercano (±4 cuadros) y las tarjetas de texto a tiempos fuertes enteros.

## 8. Revisión y entrega
- Revisar la hoja de contacto del render final:
  - textos legibles,
  - cifras iguales a las de la app,
  - nada con datos sensibles,
  - ritmo sin escenas eternas.
- **Duración:** que cumpla lo que piden las bases o el destino. Si sobra tiempo, quitar escenas en lugar de acelerar todo.
- **Entrega:**
  - **En la computadora del usuario:** escribir directo en la carpeta del proyecto (por ejemplo `~/Movies/<proyecto>_video/`). No hace falta partir archivos.
  - **En la nube:** entregar los archivos con la herramienta de envío de archivos disponible.
- Entregar `promo_v1.mp4` (16:9) y `promo_vertical_v1.mp4` (9:16), más `storyboard.json` para pedir cambios fácil.

## 9. Ejemplo: AgroCebada (app de estimación de rendimiento de cebada)
Hilo del video: las cuatro preguntas que responde la app.
1. Gancho: mapa 3D girando sobre las parcelas, con satélite y relieve.
2. "¿Cuánto va a rendir?" → elegir parcela, cifra grande, ROI al número.
3. "¿Qué tanto confiar?" → etiqueta de confianza y rango del municipio, ROI al panel.
4. "¿Te alcanza?" → calculadora de costos llenándose y "¿cubre costos?".
5. "Para FIRA: la cartera" → pestaña Cartera, contador hasta la producción total que se ve en pantalla.
6. Mapa coloreado por confianza.
7. Ficha PDF descargándose y abriéndose.
8. Carga segura: archivo bueno aceptado y uno cualquiera rechazado.
9. Cierre: mapa abierto y quieto, Cebi animado, nombre del equipo.

Cuidado con los textos: es una **estimación retrospectiva de la campaña 2025** hecha con el valor típico del municipio. Nada de "predice tu cosecha con IA" ni de decir que usa clima o satélite para la cifra.
