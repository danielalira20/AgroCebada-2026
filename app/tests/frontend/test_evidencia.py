"""Evidencia: filtros reales, trazabilidad, ambos modelos y estados vacíos. Ejecutar desde app/."""
import sys
from pathlib import Path

APP = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(APP))

import pandas as pd
from streamlit.testing.v1 import AppTest

from agrocebada_app.backend.datos.experimentos import experimentos
from agrocebada_app.backend.dominio.evidencia import PREGUNTAS, REDUCCION_MINIMA, filtrar_pruebas, tabla
from agrocebada_app.config import MODELO_OFICIAL, MODELOS
from agrocebada_app.frontend.componentes.evidencia.comparacion import datos_grafica, especificacion

exp = experimentos()
PROHIBIDAS = ['no sirve', 'tu parcela dará', 'de cada 10']


def textos(tab):
    return ' '.join(m.value for m in [*tab.markdown, *tab.caption])


def pestana(at):
    return next(t for t in at.tabs if t.label == 'Evidencia')


for modelo in MODELOS:
    at = AppTest.from_file(str(APP / 'app.py'), default_timeout=300)
    at.session_state['vista'] = 'Analista'
    at.session_state['modelo'] = modelo
    at.run()
    assert not at.exception, (modelo, at.exception)
    etiquetas = [t.label for t in at.tabs]
    assert etiquetas.index('Validación') + 1 == etiquetas.index('Evidencia') == etiquetas.index('Método y límites') - 1
    tab = pestana(at)
    texto = textos(tab)
    assert all(info['titulo'] in texto for info in PREGUNTAS.values())
    assert 'Ninguna prueba registrada superó la regla' in texto and 'excepción explícita' in texto
    assert 'no demuestra que el clima' in texto and '0.3205 a 0.3126' in texto
    assert all(n in texto for n in ['Lo que aprendimos', 'Fecha de siembra', 'Variedad', 'Manejo'])
    assert '≈ 69<' in texto and MODELOS[modelo] in texto
    assert len(tab.dataframe) == 1, 'No repetir la tabla completa en cada pregunta'
    pd.testing.assert_frame_equal(tab.dataframe[0].value, tabla(exp, None, MODELO_OFICIAL).drop(columns='estado').rename(columns={
        'pregunta':'Pregunta','tarea':'Tarea','prueba':'Prueba','mae':'MAE (t/ha)','cambio':'Cambio (t/ha)',
        'intervalo':'Intervalo 95 %','repeticiones':'Repeticiones que mejoran','resultado':'Resultado',
        'registro':'Registro','fuente':'Fuente'}))
    assert len(at.selectbox(key='evid_prueba').options) == 15
    assert any('Mediana del municipio' in x for x in at.selectbox(key='evid_prueba').options)
    at.segmented_control(key='evid_pregunta').set_value(1).run()
    assert not at.exception, at.exception
    assert len(at.selectbox(key='evid_prueba').options) == 8
    at.selectbox(key='evid_resultado').set_value('Bajan el error').run()
    assert not at.exception, at.exception
    assert any('No hay pruebas con esta combinación' in x.value for x in pestana(at).info)
    assert not any(x.key == 'evid_prueba' for x in at.selectbox)
    next(b for b in at.button if b.key == 'evid_restablecer').click().run()
    assert not at.exception, at.exception
    assert len(at.selectbox(key='evid_prueba').options) == 8
    at.checkbox(key='evid_complementarias').check().run()
    assert not at.exception, at.exception
    assert len(at.selectbox(key='evid_prueba').options) == 10
    x = filtrar_pruebas(exp, 1, complementarias=True)
    elegido = x[x.estado == 'complementaria'].index[0]
    at.selectbox(key='evid_prueba').set_value(int(elegido)).run()
    assert not at.exception, at.exception
    t = textos(pestana(at))
    assert exp.loc[elegido, 'fuente'] in t and 'Sin registro formal' in t and 'No disponible' in t
    assert any('Prueba complementaria' in x.value for x in pestana(at).info)
    at.segmented_control(key='evid_modo').set_value('Tabla').run()
    assert not at.exception, at.exception
    tablas = [df.value for df in pestana(at).dataframe]
    assert [len(t) for t in tablas] == [10, 30]
    assert list(tablas[0].columns) == ['Prueba', 'Cambio (t/ha)', 'Resultado']
    otro = next(m for m in MODELOS if m != modelo)
    at.segmented_control(key='modelo').set_value(otro).run()
    assert not at.exception, at.exception
    assert MODELOS[otro] in textos(pestana(at))
    at.segmented_control(key='evid_pregunta').set_value(2).run()
    assert not at.exception, at.exception
    assert len(at.selectbox(key='evid_prueba').options) == 4
    assert not any(p in textos(pestana(at)).lower() for p in PROHIBIDAS)
    print(modelo, 'OK: preguntas, filtros, vacío, reinicio, complementarias, tabla y cambio de modelo')

# Datos del gráfico: ni intervalos inventados ni modificación del registro original.
antes = exp.copy(deep=True)
for tema in [1, 2, 3]:
    x = filtrar_pruebas(exp, tema, complementarias=True)
    datos = datos_grafica(x, MODELO_OFICIAL)
    pd.testing.assert_series_equal(datos.delta_mae, x.delta_mae)
    assert datos[datos.estado == 'complementaria'].ic_inf.isna().all()
    assert datos.etiqueta.is_unique and 'Pasó la regla' not in set(datos.tipo)
pd.testing.assert_frame_equal(exp, antes)
seleccion = filtrar_pruebas(exp, 1, complementarias=True)
spec = especificacion(seleccion, MODELO_OFICIAL, REDUCCION_MINIMA)
assert len(spec['layer']) == 4
assert spec['layer'][0]['transform'] == [{'filter': "datum.estado === 'registrada'"}]
assert 'Pasó la regla' not in spec['layer'][3]['encoding']['color']['scale']['domain']
alterada = seleccion.copy()
alterada.loc[alterada.index[0], 'delta_mae'] -= .02
assert especificacion(alterada, MODELO_OFICIAL, REDUCCION_MINIMA) != spec, 'Cambiar los datos debe invalidar la caché de la gráfica'
assert especificacion(seleccion, MODELO_OFICIAL, REDUCCION_MINIMA) == spec
assert especificacion(seleccion, MODELO_OFICIAL, REDUCCION_MINIMA * 2) != spec


def sin_catalogo(vacio):
    from types import SimpleNamespace
    from unittest.mock import patch

    from agrocebada_app.backend.datos.experimentos import experimentos
    from agrocebada_app.frontend.vistas.analista.pestanas import evidencia as modulo

    with patch.object(modulo, 'experimentos', return_value=experimentos().iloc[:0] if vacio else None):
        modulo.evidencia(SimpleNamespace())


for vacio in [False, True]:
    at = AppTest.from_function(sin_catalogo, args=(vacio,)).run()
    assert not at.exception and len(at.info) == 1 and not at.selectbox
print('OK: catálogo ausente o vacío, sin cifras inventadas')
