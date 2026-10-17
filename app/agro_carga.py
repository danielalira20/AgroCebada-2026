"""FACHADA TEMPORAL de la refactorización: la carga segura vive ahora en `agrocebada_app/backend/carga_segura/`.

Se borra al final de la refactorización, cuando `app.py` y las pruebas importen directamente del paquete.
"""
from agrocebada_app.backend.carga_segura import *  # noqa: F401,F403
from agrocebada_app.backend.carga_segura import Rechazo, Resultado, plantilla_csv, revisar  # noqa: F401
