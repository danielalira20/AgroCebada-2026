"""Calculadora «¿me alcanza?» en la vista del agricultor (M05). Orientativa; no es un dictamen de crédito.
Muestra primero la respuesta en una frase; la tabla completa queda plegada."""
import streamlit as st

from agrocebada_app.frontend.tema.tablas import tabla as tabla_visual

from agrocebada_app.backend.dominio.calculadora import (AGROCOSTOS, columnas, cuentas, equilibrio, frase_equilibrio,
                                                         rango_municipio)
from agrocebada_app.backend.dominio.rangos import ANIO
from agrocebada_app.frontend.tema.html import e, h, titulo

# cómo se nombra cada columna de la tabla dentro de una frase
_EN_FRASE = {"Año bajo en tu municipio": "en un año bajo de tu municipio",
             "Año alto en tu municipio": "en un año alto",
             "La más baja de tu municipio": "si te va como a la parcela más baja de tu municipio",
             "La más alta de tu municipio": "como a la más alta"}


def _dinero(x):
    return f"-${abs(x):,.0f}" if x < 0 else f"${x:,.0f}"


def _queda(dif):
    return f"te quedarían {_dinero(dif)}" if dif >= 0 else f"te faltarían {_dinero(-dif)}"


def calculadora(ctx, pid):
    d, pred = ctx.d, ctx.pred
    r = d.loc[pid]
    if r.CONJUNTO == "PREDICCION":
        rend, etiqueta, que = float(pred.loc[pid, "prediccion"]), "Con la estimación", "tu estimación"
    else:
        rend, etiqueta, que = float(r.real), "Con tu cosecha registrada", "tu cosecha registrada"
    with st.container(key="glass_calculadora"):
        titulo("¿Me alcanza?",
               "Escribe tu precio por tonelada y tu costo por hectárea. Orientativo; no es un dictamen de crédito.")
        c1, c2, c3 = st.columns(3)
        precio = c1.number_input("Precio por tonelada ($)", min_value=0.0, value=None, step=100.0,
                                 placeholder="tu precio", key="calc_precio")
        costo = c2.number_input("Costo por hectárea ($)", min_value=0.0, value=None, step=500.0,
                                placeholder="tu costo", key="calc_costo")
        area = c3.number_input("Área (ha)", min_value=0.01, value=float(r.AREA_HA), step=0.5, key=f"calc_area_{pid}")
        h(f"<div class='nota'>¿No tienes tu costo a la mano? Consulta los costos de producción por región en "
          f"<a href='{AGROCOSTOS}' target='_blank'>Agrocostos de FIRA</a>.</div>")
        if not precio or not costo:
            return
        rango = rango_municipio(d, r.municipio)
        t = cuentas(columnas(rend, etiqueta, rango), area, precio, costo)
        nombres = list(t.columns)

        # 1) la respuesta en una frase, con palabra e ícono
        dif = t.loc["Ingreso menos costo", nombres[0]]
        if t.loc["¿Cubre costos?", nombres[0]] == "Sí":
            h(f"<div style='font-size:1.15rem;font-weight:600;margin:10px 0 4px'>✔ Con {que} ({rend:.2f} t/ha en "
              f"{area:.2f} ha) sí cubres tus costos: te quedan {_dinero(dif)}.</div>")
        else:
            h(f"<div class='aviso' style='font-size:1.05rem;font-weight:600'>⚠ Con {que} ({rend:.2f} t/ha en "
              f"{area:.2f} ha) no cubres tus costos: te faltarían {_dinero(-dif)}.</div>")
        lineas = []
        if len(nombres) == 3:
            bajo, alto = nombres[1], nombres[2]
            lineas.append(f"{_EN_FRASE[bajo].capitalize()} {_queda(t.loc['Ingreso menos costo', bajo])}; "
                          f"{_EN_FRASE[alto]}, {_queda(t.loc['Ingreso menos costo', alto])[len('te quedarían '):] if t.loc['Ingreso menos costo', alto] >= 0 else _queda(t.loc['Ingreso menos costo', alto])}.")
        lineas.append(frase_equilibrio(d, r.municipio, equilibrio(precio, costo)))
        h("<div class='nota'>" + "<br>".join(e(x) for x in lineas) + "</div>")

        # 2) la cuenta completa, plegada
        with st.expander("Ver la cuenta completa"):
            vista = t.astype(object)
            for fila in ["Rendimiento (t/ha)", "Producción (t)"]:
                vista.loc[fila] = [f"{v:.2f}" for v in t.loc[fila]]
            for fila in ["Ingreso", "Costo", "Ingreso menos costo"]:
                vista.loc[fila] = [_dinero(v) for v in t.loc[fila]]
            tabla_visual(vista, width="stretch")
            if rango["tipo_rango"] == "sin rango":
                nota = f"{rango['texto']} Por eso sólo se muestra la cuenta con tu parcela."
            else:
                nota = (f"{rango['texto']} El año bajo y el alto suponen una temporada parecida a {ANIO}: "
                        "la estimación no ve el clima.")
            h(f"<div class='nota'>{e(nota)}</div>")