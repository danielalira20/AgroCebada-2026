"""Calculadora «¿me alcanza?» en la vista del agricultor (M05). Orientativa; no es un dictamen de crédito."""
import streamlit as st

from agrocebada_app.backend.dominio.calculadora import (AGROCOSTOS, columnas, cuentas, equilibrio, frase_equilibrio,
                                                         rango_municipio)
from agrocebada_app.frontend.tema.html import e, h, titulo
from agrocebada_app.backend.dominio.rangos import ANIO


def _dinero(x):
    return f"-${abs(x):,.0f}" if x < 0 else f"${x:,.0f}"


def calculadora(ctx, pid):
    d, pred = ctx.d, ctx.pred
    r = d.loc[pid]
    if r.CONJUNTO == "PREDICCION":
        rend, etiqueta = float(pred.loc[pid, "prediccion"]), "Con la estimación"
    else:
        rend, etiqueta = float(r.real), "Con tu cosecha registrada"
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
        vista = t.astype(object)
        for fila in ["Rendimiento (t/ha)", "Producción (t)"]:
            vista.loc[fila] = [f"{v:.2f}" for v in t.loc[fila]]
        for fila in ["Ingreso", "Costo", "Ingreso menos costo"]:
            vista.loc[fila] = [_dinero(v) for v in t.loc[fila]]
        st.dataframe(vista, width="stretch")
        notas = [frase_equilibrio(d, r.municipio, equilibrio(precio, costo))]
        if rango["tipo_rango"] == "sin rango":
            notas.append(f"{rango['texto']} Por eso sólo se muestra la cuenta con tu parcela.")
        else:
            notas.append(f"{rango['texto']} El año bajo y el alto suponen una temporada parecida a {ANIO}: "
                         "la estimación no ve el clima.")
        h("<div class='nota'>" + "<br>".join(e(n) for n in notas) + "</div>")