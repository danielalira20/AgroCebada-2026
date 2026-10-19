"""Estilo de la app: CSS (assets/css/tema.css), mascota, ícono y marca de la barra superior."""
from agrocebada_app.config import APP
from agrocebada_app.frontend.tema.paleta import es_oscuro

ESTILO = (APP / "assets" / "css" / "tema.css").read_text(encoding="utf-8")
CLARO = (APP / "assets" / "css" / "claro.css").read_text(encoding="utf-8")


def estilo_actual():
    return ESTILO + ("" if es_oscuro() else CLARO)


MASCOTA = (APP / "assets" / "mascota" / "cebi.svg").read_text(encoding="utf-8") if (APP / "assets" / "mascota" / "cebi.svg").exists() else ""
ICONO = str(APP / "assets" / "mascota" / "cebi.png") if (APP / "assets" / "mascota" / "cebi.png").exists() else "🌾"
MARCA = """<div class="marca"><div class="cebi" style="width:44px;height:44px;flex:0 0 44px">""" + MASCOTA + """</div>
<div><div class="marca-t">AgroCebada</div><div class="marca-s">Estimación retrospectiva de la campaña 2025 ·
información al 31 de octubre de 2025</div></div></div>"""
