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


def resumen_estimacion(valores, fuentes, niveles):
    """Una cifra sólo si valor, fuente y confianza son comunes a todas las filas, sin promediar."""
    if valores.empty:
        return None
    uniforme = all(s.nunique(dropna=False) == 1 and s.notna().all() for s in (valores, fuentes, niveles))
    return {"valor": numero(valores.iloc[0], 2) if uniforme else "Varios valores",
            "unidad": "t/ha" if uniforme else "",
            "fuentes": sorted(fuentes.dropna().unique()), "niveles": sorted(niveles.dropna().unique())}
