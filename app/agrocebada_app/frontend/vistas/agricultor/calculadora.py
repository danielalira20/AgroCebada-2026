"""Calculadora «¿me alcanza?» en la vista del agricultor (M05). Orientativa; no es un dictamen de crédito.
Muestra primero la respuesta en una frase; la tabla completa queda plegada."""
import streamlit as st

from agrocebada_app.frontend.tema.tablas import tabla as tabla_visual

from agrocebada_app.backend.dominio.calculadora import AGROCOSTOS, frase_equilibrio
from agrocebada_app.backend.dominio.planeador import (cobertura_saldo, escenarios_cuenta, evaluar_cuenta,
                                                     importe as _dinero, plan_si_sale_mal)
from agrocebada_app.frontend.componentes.escenarios.vista import mostrar_escenarios, mostrar_orientacion
from agrocebada_app.frontend.estado.planeador import (guardar_entrada, hidratar_compatibilidad, preparar_area)
from agrocebada_app.frontend.tema.html import e, h, titulo

def calculadora(ctx, pid):
    d, pred = ctx.d, ctx.pred
    r = d.loc[pid]
    if r.CONJUNTO == "PREDICCION":
        rend, etiqueta, que = float(pred.loc[pid, "prediccion"]), "Con la estimación", "tu estimación"
    else:
        rend, etiqueta, que = float(r.real), "Con tu cosecha registrada", "tu cosecha registrada"
    return calculadora_base(ctx, r.municipio, rend, etiqueta, float(r.AREA_HA), f"calc_area_{pid}",
                            parcela=pid, que=que,
                            etiqueta_escenario="Estimación de la parcela" if r.CONJUNTO == "PREDICCION" else
                            "Cosecha registrada 2025")


def calculadora_base(ctx, municipio, rendimiento, etiqueta, area_inicial, clave_area, *,
                     parcela=None, que="la referencia de tu municipio", area_editable=True,
                     etiqueta_escenario="Referencia del municipio"):
    """Dibuja la cuenta común; un flujo sin parcela puede aportar su única superficie ya capturada."""
    hidratar_compatibilidad(st.session_state)
    if area_editable:
        preparar_area(st.session_state, clave_area, area_inicial, parcela)
    h("<style>.st-key-glass_calculadora [data-testid='stNumberInput'] button:disabled"
      "{display:none !important}</style>")
    with st.container(key="glass_calculadora"):
        titulo("¿Me alcanza?",
               "Escribe tu precio por tonelada y tu costo por hectárea. Orientativo; no es un dictamen de crédito.")
        campos = st.columns(3 if area_editable else 2)
        c1, c2 = campos[:2]
        precio = c1.number_input("Precio por tonelada ($)", min_value=0.0, value=None, step=100.0,
                                 placeholder="tu precio", key="calc_precio",
                                 on_change=guardar_entrada, args=(st.session_state, "calc_precio", "precio_t"))
        costo = c2.number_input("Costo por hectárea ($)", min_value=0.0, value=None, step=500.0,
                                placeholder="tu costo", key="calc_costo",
                                on_change=guardar_entrada, args=(st.session_state, "calc_costo", "costo_ha"))
        area = area_inicial
        if area_editable:
            area = campos[2].number_input("Área (ha)", min_value=0.01, value=None, step=0.5, key=clave_area,
                                          on_change=guardar_entrada,
                                          args=(st.session_state, clave_area,
                                                "area_rapida_ha" if parcela is None else "area", parcela))
        h(f"<div class='nota'>¿No tienes tu costo a la mano? Consulta los costos de producción por región en "
          f"<a href='{AGROCOSTOS}' target='_blank'>Agrocostos de FIRA</a>.</div>")
        resultado = evaluar_cuenta(ctx.d, municipio, rendimiento, etiqueta, area, precio, costo)
        if resultado["estado"] != "calculada":
            for mensaje in resultado["errores"].values():
                st.warning(mensaje)
            return
        rango, t = resultado["rango"], resultado["tabla"]
        rend = rendimiento
        nombres = list(t.columns)

        # 1) la respuesta en una frase, con palabra e ícono
        dif = t.loc["Ingreso menos costo", nombres[0]]
        estado = cobertura_saldo(dif)
        if estado == "equilibrio":
            h(f"<div class='esc-respuesta'>= Con {e(que)} ({rend:.2f} t/ha en {area:.2f} ha) "
              "justo cubres tus costos.</div>")
        elif estado == "cubre":
            h(f"<div style='font-size:1.15rem;font-weight:600;margin:10px 0 4px'>✔ Con {e(que)} ({rend:.2f} t/ha en "
              f"{area:.2f} ha) sí cubres tus costos: te quedan {_dinero(dif)}.</div>")
        else:
            h(f"<div class='aviso' style='font-size:1.05rem;font-weight:600'>⚠ Con {e(que)} ({rend:.2f} t/ha en "
              f"{area:.2f} ha) no cubres tus costos: te faltarían {_dinero(-dif)}.</div>")
        escenarios = escenarios_cuenta(resultado, etiqueta_escenario)
        mostrar_escenarios(escenarios, resultado["umbral"],
                           frase_equilibrio(ctx.d, municipio, resultado["umbral"]), rango)
        mostrar_orientacion(plan_si_sale_mal(escenarios), clave_area)

        # 2) la cuenta completa, plegada
        with st.expander("Ver la cuenta completa"):
            vista = t.astype(object)
            for fila in ["Rendimiento (t/ha)", "Producción (t)"]:
                vista.loc[fila] = [f"{v:.2f}" for v in t.loc[fila]]
            for fila in ["Ingreso", "Costo", "Ingreso menos costo"]:
                vista.loc[fila] = [_dinero(v) for v in t.loc[fila]]
            etiquetas = {s["columna"]: s["etiqueta"] for s in escenarios}
            tabla_visual(vista.rename(columns=etiquetas), width="stretch")
            h("<div class='nota'>La tabla y las tarjetas usan las mismas cuentas. "
              "Los rendimientos son referencias históricas de 2025, no resultados prometidos.</div>")
