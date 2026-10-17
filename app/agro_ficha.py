"""FACHADA TEMPORAL de la refactorización: la ficha en PDF vive ahora en `agrocebada_app/backend/ficha_pdf/`.

Se borra al final de la refactorización, cuando `app.py` y las pruebas importen directamente del paquete.
"""
from agrocebada_app.backend.ficha_pdf.ficha import ficha_pdf  # noqa: F401
