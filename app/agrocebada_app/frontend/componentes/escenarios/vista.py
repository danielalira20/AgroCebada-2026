"""Presentación de escenarios; recibe cuentas preparadas, sin acceder al catálogo."""
import streamlit as st

from agrocebada_app.backend.dominio.planeador import importe, posiciones_barra
from agrocebada_app.frontend.tema.html import e, h


def _tarjeta(escenario):
    s = escenario
    estado = s["cobertura"]
    mensaje = {"falta": "⚠ Te faltarían", "cubre": "✔ Te quedarían", "equilibrio": "= Justo cubre"}[estado]
    return (f"<article class='esc-tarjeta esc-tarjeta--{e(s['id'])}' role='listitem'>"
            f"<h3>{e(s['etiqueta'])}</h3>"
            f"<p class='esc-rendimiento'>{s['rendimiento_t_ha']:.2f}<span>t/ha</span></p>"
            f"<dl><div><dt>Producción</dt><dd>{s['produccion_t']:,.2f} t</dd></div>"
            f"<div><dt>Ingreso</dt><dd>{e(importe(s['ingreso']))}</dd></div>"
            f"<div><dt>Costo</dt><dd>{e(importe(s['costo']))}</dd></div></dl>"
            f"<div class='esc-saldo esc-saldo--{e(estado)}'><span>{e(mensaje)}</span>"
            f"<strong>{e(importe(abs(s['saldo'])))}</strong></div></article>")


def _barra(escenarios, umbral):
    barra = posiciones_barra(escenarios, umbral)
    if barra is None:
        return ""
    if not barra["legible"]:
        return ("<div class='esc-barra esc-barra--compacta' aria-hidden='true'>"
                "Las marcas coinciden o quedan muy cerca en esta escala. Compara las cifras de las tarjetas.</div>")
    marcas = "".join(
        f"<span class='esc-marca {'esc-marca--equilibrio' if m['id'] == 'equilibrio' else ''}' "
        f"style='left:{m['posicion']:.6f}%'>{m['numero']}</span>" for m in barra["marcas"])
    leyenda = "".join(f"<li><b>{m['numero']}</b><span>{e(m['etiqueta'])} · {m['valor']:.2f} t/ha</span></li>"
                      for m in barra["marcas"])
    return (f"<div class='esc-barra' aria-hidden='true'><div class='esc-pista'>{marcas}</div>"
            f"<ul class='esc-marcas-lista'>{leyenda}</ul></div>")


def mostrar_escenarios(escenarios, umbral, frase_equilibrio, rango):
    if not escenarios:
        return
    h(f"<section class='esc-resumen' aria-label='Punto de equilibrio y escenarios'>"
      f"<div class='esc-equilibrio'><div><span class='esc-rotulo'>Punto de equilibrio</span>"
      f"<p class='esc-umbral'>{umbral:.2f}<span>t/ha</span></p></div>"
      f"<p class='esc-contexto'>{e(frase_equilibrio)}</p></div>"
      "<p class='esc-historia'>Referencias basadas en parcelas con cosecha de 2025. "
      "Sirven para comparar tus cuentas; no pronostican tu cosecha.</p>"
      f"{_barra(escenarios, umbral)}<div class='esc-tarjetas' role='list' aria-label='Escenarios de rendimiento'>"
      + "".join(_tarjeta(s) for s in escenarios) + "</div>"
      f"<p class='esc-contexto esc-soporte'>{e(rango['texto'])}</p></section>")


def mostrar_orientacion(plan, clave):
    if plan is None:
        return
    with st.expander(plan["titulo"], expanded=plan["abierto"],
                     key=f"orientacion_{clave}_{plan['estado']}_{plan['escenario_id']}"):
        h(f"<div class='esc-orientacion'><p>{e(plan['apertura'])}</p><ol>"
          + "".join(f"<li>{e(paso)}</li>" for paso in plan["pasos"]) + "</ol>"
          f"<p class='esc-contexto'>{e(plan['nota'])}</p></div>")
