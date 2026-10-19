"""Ejecuta la descarga de ambas vistas: python tests/frontend/test_descargas_ficha.py (desde app/)."""
import os
import re
import sys
from pathlib import Path

APP = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(APP))

from streamlit.testing.v1 import AppTest

from agrocebada_app.backend.datos import paquete
from agrocebada_app.backend.dominio.confianza import confianza_parcela
from agrocebada_app.config import MODELO_OFICIAL, MODELOS
from agrocebada_app.frontend.estado.contexto import calcular


def pantalla(perfil, modelo, pid, respaldo=False, calc=False):
    from unittest.mock import patch

    import streamlit as st

    from agrocebada_app.backend.datos import paquete
    from agrocebada_app.backend.ficha_pdf import armado
    from agrocebada_app.config import MODELO_OFICIAL
    from agrocebada_app.frontend.componentes.descargas import boton_ficha as descarga
    from agrocebada_app.frontend.estado.contexto import calcular
    from agrocebada_app.frontend.vistas.agricultor.panel_parcela import panel_parcela
    from agrocebada_app.frontend.vistas.analista.pestanas.ficha_tecnica import ficha_tecnica

    d = paquete.parcelas()
    ctx = calcular(d, paquete.soporte(), paquete.series(), paquete.clima(),
                   MODELO_OFICIAL if perfil == 'Agricultor' else modelo, False)
    if respaldo:
        ctx.pred.loc[pid, 'fuente'] = 'grupo'  # sólo memoria: verifica que la fuente mande sobre el municipio
    if calc:
        st.session_state['calc_precio'], st.session_state['calc_costo'] = 5000.0, 15000.0
    st.session_state.pop('ficha_info', None)
    st.session_state.pop('ficha_pdf', None)
    descarga.ficha_bytes.clear()
    pdf_real, boton_real = armado.ficha_pdf, st.download_button

    def generar(info, *args, **kwargs):
        st.session_state['ficha_info'] = info
        pdf = pdf_real(info, *args, **kwargs)
        st.session_state['ficha_pdf'] = pdf
        return pdf

    def descargar(*args, **kwargs):
        if kwargs.get('key') in ('ficha_agricultor', 'ficha_analista'):
            data = kwargs['data']
            kwargs['data'] = data() if callable(data) else data
        return boton_real(*args, **kwargs)

    with patch.object(armado, 'ficha_pdf', side_effect=generar), patch.object(st, 'download_button', side_effect=descargar):
        if perfil == 'Agricultor':
            st.session_state['agri_muni'] = d.loc[pid, 'municipio']
            st.session_state['agri_parcela'] = pid
            panel_parcela(ctx)
        else:
            ficha_tecnica(ctx)


def comprobar(perfil, modelo, pid, ctx, respaldo=False, calc=False):
    at = AppTest.from_function(pantalla, args=(perfil, modelo, pid, respaldo, calc), default_timeout=90).run()
    assert not at.exception, (perfil, pid, at.exception)
    if perfil == 'Analista':
        at.selectbox[0].set_value(pid).run()
        assert not at.exception, (perfil, pid, at.exception)
    info, pdf = at.session_state['ficha_info'], at.session_state['ficha_pdf']
    assert info['id'] == pid and info['modelo'] == MODELOS[ctx.modelo], (perfil, modelo, info)
    if pid in ctx.pred.index:
        p = ctx.pred.loc[pid]
        esperado = confianza_parcela(ctx.conf, p.municipio, 'grupo' if respaldo else p.fuente)
        assert info['confianza'] == esperado, (perfil, pid, info['confianza'], esperado)
        assert abs(info['valor'] - p.prediccion) < 1e-9
    else:
        assert info['tipo'] == 'registrado' and info['confianza'] is None
    if calc and perfil == 'Agricultor':      # lo que llenó en la calculadora llega solo a la ficha
        filas = dict(info['calculadora'])
        assert len(filas) == 3 and any(k.startswith('Ingreso menos costo') for k in filas), info['calculadora']
        assert filas[f'Producción en {ctx.d.loc[pid, "AREA_HA"]:.2f} ha'] == f'{info["produccion"]:.1f} t'
    else:
        assert info['calculadora'] is None, info['calculadora']
    assert pdf.startswith(b'%PDF-') and len(re.findall(rb'/Type\s*/Page(?!s)', pdf)) == 1
    if os.environ.get('AGRO_FICHAS'):
        out = Path(os.environ['AGRO_FICHAS'])
        out.mkdir(parents=True, exist_ok=True)
        (out / f'{perfil.lower()}_{modelo}_{pid}{"_respaldo" if respaldo else ""}{"_calculadora" if calc else ""}.pdf').write_bytes(pdf)
    print(f'{perfil} · {MODELOS[ctx.modelo]} · {pid}: modelo, confianza y PDF de una página')


d, S, C = paquete.parcelas(), paquete.series(), paquete.clima()
alta = d.index[(d.municipio == 'Calpulalpan') & (d.CONJUNTO == 'PREDICCION')][0]
casos = [alta, 'AGC_011', 'AGC_120', 'AGC_002']
for perfil, modelo in [('Agricultor', MODELO_OFICIAL), *[('Analista', m) for m in MODELOS]]:
    ctx = calcular(d, paquete.soporte(), S, C, modelo, False)
    for pid in casos:
        comprobar(perfil, modelo, pid, ctx)
    comprobar(perfil, modelo, alta, ctx, respaldo=True)
    if perfil == 'Agricultor':
        comprobar(perfil, modelo, 'AGC_011', ctx, calc=True)
print('OK: ambas vistas; confianza alta/media/baja, registrado y respaldo por grupo; ambos modelos en Analista')
