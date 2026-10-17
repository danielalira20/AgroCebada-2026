"""Pestaña «Método y límites»."""
import streamlit as st

from agrocebada_app.backend.modelo.metricas import metricas
from agrocebada_app.frontend.tema.html import e, h, titulo


def metodo_limites(ctx):
    d = ctx.d
    modelo = ctx.modelo
    O = ctx.O
    mA = ctx.mA
    n_tr = int((d.CONJUNTO == "ENTRENAMIENTO").sum())
    n_mun = d[d.CONJUNTO == "ENTRENAMIENTO"].municipio.nunique()
    estad = "mediana" if modelo.startswith("mediana") else "media"
    with st.container(key="glass_metodo"):
        titulo("Cómo se calcula", "Es el mismo procedimiento de T08; la app lo ejecuta cada vez que se abre.")
        pasos = [("Datos", f"{n_tr} parcelas con cosecha registrada en 2025, de {n_mun} municipios."),
                 ("Valor típico del municipio", f"Para cada municipio se calcula la {estad} del rendimiento de "
                                                "esas parcelas."),
                 ("Asignación", "Cada parcela reservada recibe el valor de su municipio. Si no hubiera datos del "
                                "municipio, se usa el de su grupo de registro y, al final, el general."),
                 ("Validación", "Se repite el cálculo escondiendo parcelas conocidas: validación cruzada 5 × 5 "
                                "(escenario A) y por zonas de lluvia completas (escenario B), con la regla de T03 "
                                "escrita antes de ver resultados.")]
        h("<div class='pasos'>" + "".join(f"<div class='paso'><div class='n'>{i}</div><b>{e(t)}</b><p>{e(x)}</p></div>"
                                          for i, (t, x) in enumerate(pasos, 1)) + "</div>")
    r1, r2 = st.columns([3, 2])
    with r1, st.container(key="glass_resultados"):
        titulo("Qué tan bien funciona", "Error al estimar parcelas que el método no vio.")
        if O is not None:
            mB = metricas(O[O.escenario == "B"])
            kp = [("MAE · municipio conocido (A)", f"{mA.MAE:.3f}", "t/ha"), ("R² · escenario A", f"{mA.R2:.3f}", ""),
                  ("MAE · zona de lluvia nueva (B)", f"{mB.MAE:.3f}", "t/ha")]
            h("<div class='fila'>" + "".join(
                f"<div class='mini'><span>{e(k)}</span><b class='kv'>{v}<small>{u}</small></b></div>"
                for k, v, u in kp) + "</div>")
        h("<div class='nota'>Por qué un modelo simple: se probaron cerca de 20 variantes con satélite, clima, "
          "relieve, vecinas, árbol con poda, PCA y red neuronal, y ninguna redujo el error de forma confiable "
          "frente a este valor típico.</div>")
    with r2, st.container(key="glass_fuentes"):
        titulo("Fuentes")
        fuentes = [("FIRA", "polígonos y rendimientos"), ("Sentinel-2, Landsat y Planet", "índices por parcela"),
                   ("CHIRPS", "lluvia mensual"), ("Temperatura", "máxima y mínima mensual"),
                   ("INEGI", "elevación y pendiente"),
                   ("Mapa", "EOX Sentinel-2 cloudless, Terrain Tiles de AWS y CARTO, sólo como fondo")]
        h("<div class='etiquetas'>" + "".join(f"<div class='etiqueta'>{e(a)} <span>· {e(b)}</span></div>"
                                              for a, b in fuentes) + "</div>")
    with st.container(key="glass_limites"):
        titulo("Límites", "Lo que esta estimación no puede decir.")
        limites = ["Es el valor típico del municipio: dos parcelas vecinas del mismo municipio reciben la misma cifra.",
                   "Faltan fecha de siembra, variedad, manejo y suelo, que explican buena parte de las diferencias.",
                   "El clima viene en pixeles de ~5.5 km: no distingue parcelas cercanas.",
                   "Algunos rendimientos registrados vienen redondeados.",
                   "El rendimiento no indica calidad maltera ni capacidad de pago.",
                   "Los índices de satélite y el clima son contexto: no son mediciones de campo ni recomendaciones."]
        h("<div class='limites'>" + "".join(f"<div class='limite'>{e(x)}</div>" for x in limites) + "</div>")
