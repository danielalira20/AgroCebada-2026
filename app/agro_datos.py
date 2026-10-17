"""FACHADA TEMPORAL de la refactorización: reexporta con los mismos nombres lo que ahora vive en `agrocebada_app/`.

Se borra al final de la refactorización, cuando `app.py` y las pruebas importen directamente del paquete.
"""
from agrocebada_app.backend.datos.elevacion import elevaciones  # noqa: F401
from agrocebada_app.backend.datos.lectura import (  # noqa: F401
    con_centroides, leer_clima, leer_oficial, leer_parcelas, leer_series, leer_soporte, leer_validacion)
from agrocebada_app.backend.datos.paquete import (  # noqa: F401
    clima, hay_datos, oficial, parcelas, series, soporte, usar_paquete, validacion)
from agrocebada_app.backend.dominio.colores import color_rgb  # noqa: F401
from agrocebada_app.backend.modelo.estimador import estadistico, predecir  # noqa: F401
from agrocebada_app.backend.modelo.metricas import metricas, validacion_dejando_uno  # noqa: F401
from agrocebada_app.backend.rutas.localizador import buscar, buscar_dataset, raiz, rutas  # noqa: F401
from agrocebada_app.config import (  # noqa: F401
    APP as AQUI, CLAVE_DATASET, COLUMNAS_INDICES, MODELOS_CANDIDATOS as MODELOS, PALETA, PAQ, TEMPORADA)
