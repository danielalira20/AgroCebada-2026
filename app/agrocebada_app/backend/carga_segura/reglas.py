"""Límites y reglas de la carga segura, texto de requisitos y plantilla."""
import re

MAX_MB = 50
MAX_DESCOMPRIMIDO_MB = 200
MAX_ARCHIVOS = 30
MAX_COMPRESION = 100                 # descomprimido / comprimido por archivo (más que esto parece bomba zip)
MAX_PARCELAS = 5000
MIN_CON_COSECHA = 10
EXT_PERMITIDAS = {".csv", ".shp", ".shx", ".dbf", ".prj", ".cpg", ".zip"}
IGNORAR = re.compile(r"(^|/)(__MACOSX/|\.DS_Store$|Thumbs\.db$)")
COLS_TABLA = ["ID_POLIGONO", "AREA_HA", "RENDIMIENTO_T_HA", "CONJUNTO"]
COLS_SIMPLE = ["ID_POLIGONO", "MUNICIPIO", "GRUPO", "AREA_HA", "RENDIMIENTO_T_HA", "CONJUNTO"]
CAMPOS_SHP = {"ID_POLIGON": "ID_POLIGONO", "Municipio": "municipio", "Cultivo": "grupo_registro"}
RENDIMIENTO = (0.1, 15.0)            # t/ha aceptados en parcelas con cosecha
AREA = (0.01, 10000.0)               # ha
MEXICO = (-118.5, 14.0, -86.5, 33.0)
ID_VALIDO = re.compile(r"^[A-Za-z0-9_.\- ]{1,40}$")

REQUISITOS = f"""**Formato 1 · ZIP como el del reto (con mapa).** Un `.zip` que contenga:
- **Tabla de parcelas** (`.csv`, UTF-8, separada por comas) con las columnas `ID_POLIGONO`, `AREA_HA`,
  `RENDIMIENTO_T_HA` y `CONJUNTO`. `CONJUNTO` vale `ENTRENAMIENTO` (parcelas con cosecha, con rendimiento entre
  {RENDIMIENTO[0]} y {RENDIMIENTO[1]:.0f} t/ha) o `PREDICCION` (parcelas a estimar, con el rendimiento vacío).
- **Polígonos de las parcelas** en shapefile: `.shp`, `.shx`, `.dbf` y `.prj` (sueltos o dentro de otro `.zip`), con
  los campos `ID_POLIGON` (los mismos IDs de la tabla), `Municipio` y `Cultivo` (grupo de registro).

**Formato 2 · CSV simple (sin mapa).** Un `.csv` con las columnas `ID_POLIGONO`, `MUNICIPIO`, `GRUPO`, `AREA_HA`,
`RENDIMIENTO_T_HA` y `CONJUNTO`, con las mismas reglas.

**Se rechaza** cualquier otra cosa: otros tipos de archivo (Excel, PDF, imágenes, programas, etc.), archivos de más de
{MAX_MB} MB, ZIP con más de {MAX_ARCHIVOS} archivos, más de {MAX_DESCOMPRIMIDO_MB} MB descomprimido, con contraseña, con
rutas raras o enlaces, más de {MAX_PARCELAS:,} parcelas, menos de {MIN_CON_COSECHA} parcelas con cosecha o ninguna por
estimar, IDs repetidos o que no coinciden entre tabla y polígonos, valores fuera de rango y polígonos inválidos o fuera
de México. El archivo no se guarda: se analiza en memoria, se borra al terminar y nadie más lo ve."""


def plantilla_csv():
    """CSV de ejemplo del formato simple (IDs y valores inventados, sólo para mostrar las columnas)."""
    return ("ID_POLIGONO,MUNICIPIO,GRUPO,AREA_HA,RENDIMIENTO_T_HA,CONJUNTO\n"
            "P_001,Mi municipio,CEBADA,5.20,4.10,ENTRENAMIENTO\n"
            "P_002,Mi municipio,CEBADA,3.75,3.60,ENTRENAMIENTO\n"
            "P_003,Mi municipio,CEBADA,8.10,,PREDICCION\n").encode("utf-8")
