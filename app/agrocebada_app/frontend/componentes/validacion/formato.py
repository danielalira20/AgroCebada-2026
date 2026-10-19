"""Formato de confianza y números; no decide niveles ni calcula métricas."""
import pandas as pd

from agrocebada_app.frontend.tema.html import e

NIVELES = {"alta": ("✔", "Alta"), "media": ("▲", "Media"), "baja": ("◆", "Baja")}


def etiqueta_confianza(nivel):
    simbolo, nombre = NIVELES.get(str(nivel).lower(), ("—", "Sin información"))
    return f"{simbolo} {nombre}"


def insignia(nivel):
    clave = str(nivel).lower()
    clase = clave if clave in NIVELES else "sin-datos"
    return f"<span class='val-confianza val-{clase}'>{e(etiqueta_confianza(nivel))}</span>"


def numero(valor, decimales=3):
    return f"{valor:.{decimales}f}" if pd.notna(valor) else "—"
