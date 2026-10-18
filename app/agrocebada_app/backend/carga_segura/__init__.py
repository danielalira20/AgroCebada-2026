"""Carga segura de un dataset propio para analizarlo con el mismo procedimiento de T08.

Sólo se aceptan dos formatos y todo lo demás se rechaza con un motivo concreto:
  1. ZIP con el formato del reto: una tabla CSV (ID_POLIGONO, AREA_HA, RENDIMIENTO_T_HA, CONJUNTO) y el shapefile de
     las parcelas (.shp, .shx, .dbf y .prj, sueltos o en un .zip dentro del ZIP) con los campos ID_POLIGON, Municipio y
     Cultivo.
  2. Un CSV simple (sin mapa): ID_POLIGONO, MUNICIPIO, GRUPO, AREA_HA, RENDIMIENTO_T_HA, CONJUNTO.

Seguridad: el archivo se trata sólo como datos (nada se ejecuta); se revisan tipo real, tamaño, cantidad de archivos,
tamaño descomprimido, compresión sospechosa, rutas, enlaces y cifrado antes de leer nada; los archivos se escriben con
nombres propios en una carpeta temporal que se borra al terminar, y el resultado vive sólo en la sesión de quien subió.
"""
from agrocebada_app.backend.carga_segura.errores import Rechazo, Resultado  # noqa: F401
from agrocebada_app.backend.carga_segura.reglas import (  # noqa: F401
    AREA, CAMPOS_SHP, COLS_SIMPLE, COLS_TABLA, EXT_PERMITIDAS, ID_VALIDO, IGNORAR, MAX_ARCHIVOS, MAX_COMPRESION,
    MAX_DESCOMPRIMIDO_MB, MAX_MB, MAX_PARCELAS, MEXICO, MIN_CON_COSECHA, RENDIMIENTO, REQUISITOS, plantilla_csv)
from agrocebada_app.backend.carga_segura.revisar import revisar  # noqa: F401
