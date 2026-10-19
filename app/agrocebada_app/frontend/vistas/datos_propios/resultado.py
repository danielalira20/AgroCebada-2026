"""Resultado del análisis de un dataset propio (M16): la misma lectura que reciben las 59 —cifra, confianza y rango—
pero calculada con los datos que subió quien usa la app.

La página se lee en dos niveles, porque la sube tanto quien quiere la cifra de su parcela como quien quiere auditar
el método: arriba, una parcela a la vez en lenguaje llano con una explicación de qué significa cada cosa; abajo, en
un desplegable, el detalle técnico (MAE, RMSE y R² dejando una fuera, y la tabla por municipio).

Nada se recalcula aparte: la confianza sale de confianza.py (M01) y el rango de rangos.py (M02), alimentados con la
validación rápida que la propia app hace sobre el archivo subido. Por eso, subir el ZIP del reto devuelve las mismas
cifras, confianzas y rangos que la vista principal.
"""
import streamlit as st

from agrocebada_app.backend.dominio.confianza import confianza_de_parcelas, confianza_municipios
from agrocebada_app.backend.dominio.geometria import zoom_para
from agrocebada_app.backend.dominio.rangos import rango_de, rango_texto, rangos_municipio
from agrocebada_app.backend.modelo.estimador import predecir
from agrocebada_app.backend.modelo.metricas import metricas, validacion_dejando_uno
from agrocebada_app.config import MODELOS
from agrocebada_app.frontend.componentes.mapa.mapa import mapa
from agrocebada_app.frontend.componentes.validacion.formato import etiqueta_confianza, insignia, numero
from agrocebada_app.frontend.tema.estilos import MASCOTA
from agrocebada_app.frontend.tema.html import e, h, titulo

QUE_ES = [
    ("La cifra", "Tomamos las parcelas de tu archivo que ya tienen cosecha anotada y, para cada parcela sin cosecha, "
                 "usamos lo que dieron las de su mismo municipio."),
    ("La confianza", "Dice con cuánta evidencia se hizo esa cuenta. Alta no quiere decir «seguro»: quiere decir que "
                     "hubo más parcelas con qué compararla."),
    ("El rango", "Lo que de verdad dieron las parcelas de ese municipio, de la más baja a la más alta. La tuya puede "
                 "caer en cualquier punto."),
    ("Lo que no es", "No es una promesa de tu cosecha, ni una recomendación de qué sembrar o cuánto invertir."),
]


def _explicacion():
    """Tarjeta de Cebi: qué significan la cifra, la confianza y el rango, sin tecnicismos."""
    puntos = "".join(f"<div><b>{e(t)}:</b> {e(x)}</div>" for t, x in QUE_ES)
    h(f"<div class='mascota'><div class='cebi'>{MASCOTA}</div><div><div class='tit'>¿Qué estoy viendo?</div>"
      f"<div class='que-es'>{puntos}</div></div></div>")


def _parcela(pid, du, pu, cp, entrena):
    """Tarjeta grande de una sola parcela, con el lenguaje del panel del agricultor."""
    r, p = du.loc[pid], pu.loc[pid]
    c = cp.loc[pid]
    produccion = float(p.prediccion) * float(r.AREA_HA)
    kp = [("Producción estimada", f"{produccion:,.2f}", "t"), ("Área", f"{float(r.AREA_HA):.2f}", "ha"),
          ("Confianza", etiqueta_confianza(c.nivel), "")]
    h(f"<div class='eyebrow'>Rendimiento estimado · {e(pid)} · {e(r.municipio)}</div>"
      f"<div class='big'>{p.prediccion:.2f}<small>t/ha</small></div>"
      "<div class='fila'>" + "".join(
          f"<div class='mini'><span>{e(k)}</span><b class='kv'>{e(v)}<small>{e(u)}</small></b></div>"
          for k, v, u in kp) + "</div>"
      f"<div class='nota'>{e(c.motivo)}</div>"
      f"<div class='nota'>{e(rango_de(entrena, r.municipio)['texto'])}</div>")


def _tabla_municipios(conf, rangos):
    """Por municipio: cuántas parcelas con cosecha, su error, su confianza y su rango. Tabla ancha en escritorio y
    tarjetas en pantallas angostas, el mismo patrón de «Las 59 estimaciones»."""
    t = conf.assign(rango=[rango_texto(rangos.bajo.get(m), rangos.alto.get(m)) for m in conf.municipio],
                    confianza=conf.nivel.map(etiqueta_confianza),
                    mae=conf.mae_municipio.map(lambda x: numero(x, 2)))     # 2 decimales, igual que en las 59
    titulo("Por municipio", "De dónde sale la confianza de cada parcela.")
    with st.container(key="tabla_mun_subido"):
        st.dataframe(t[["municipio", "n_cosecha", "mae", "confianza", "rango", "motivo_detallado"]].rename(
            columns={"n_cosecha": "parcelas con cosecha", "mae": "MAE del municipio (t/ha)",
                     "motivo_detallado": "motivo de la confianza"}),
            hide_index=True, width="stretch", height=340, row_height=100,
            column_config={"municipio": st.column_config.TextColumn(pinned=True),
                           "motivo de la confianza": st.column_config.TextColumn(width=460)})
    filas = [f"<article class='est-tarjeta'><div class='est-tarjeta-titulo'><h3>{e(x.municipio)}</h3>"
             f"{insignia(x.nivel)}</div><dl>"
             f"<div><dt>Parcelas con cosecha</dt><dd>{int(x.n_cosecha)}</dd></div>"
             f"<div><dt>MAE del municipio</dt><dd>{e(x.mae)} t/ha</dd></div>"
             f"<div><dt>Rango</dt><dd>{e(x.rango)}</dd></div></dl></article>" for x in t.itertuples()]
    h("<div class='est-movil'>" + "".join(filas) + "</div>")


def _detalle_tecnico(m, conf, rangos, mA):
    """Métricas de la validación rápida del archivo subido y, como referencia, las del proyecto."""
    kp = [("MAE", f"{m.MAE:.3f}", "t/ha"), ("RMSE", f"{m.RMSE:.3f}", "t/ha"), ("R²", f"{m.R2:.3f}", ""),
          ("Sesgo", f"{m.sesgo:+.3f}", "t/ha")]
    h("<div class='eyebrow'>Tu archivo · dejando una parcela fuera</div><div class='fila'>" + "".join(
        f"<div class='mini'><span>{e(k)}</span><b class='kv'>{e(v)}<small>{e(u)}</small></b></div>"
        for k, v, u in kp) + "</div>")
    if mA is not None:
        h(f"<div class='nota'>Como referencia, el proyecto obtuvo MAE {mA.MAE:.3f} t/ha, RMSE {mA.RMSE:.3f} t/ha y "
          f"R² {mA.R2:.3f} con las 138 parcelas etiquetadas. No son comparables de frente: aquí se deja una parcela "
          "fuera por vez y allá se repite una validación de 5 × 5 por bloques. Sirve para ubicarte, no para declarar "
          "un ganador.</div>")
    _tabla_municipios(conf, rangos)


def analizar_subido(res, modelo, satelite, mA=None):
    du = res.datos
    entrena = du[du.CONJUNTO == "ENTRENAMIENTO"]
    pu = predecir(du, modelo)
    v = validacion_dejando_uno(du, modelo)
    m = metricas(v)                                     # todas las predicciones del archivo, con y sin respaldo
    # La confianza se mide sólo con las que se estimaron desde su propio municipio, igual que el «A · sin respaldo»
    # de la vista principal: si una parcela se estimó con el grupo, su error no habla de su municipio.
    conf = confianza_municipios(du, v[v.fuente == "municipio"])

    rangos = rangos_municipio(entrena).set_index("municipio")       # M02, con las cosechas del propio archivo
    cp = confianza_de_parcelas(pu, conf)
    pu["error_tipico"] = pu.municipio.map(conf.set_index("municipio").mae_municipio)

    with st.container(key="glass_revision"):
        titulo("Revisión del archivo", "El archivo pasó todas las reglas de formato y seguridad.")
        h("".join(f"<span class='chk ok'>✓ {e(x)}</span>" for x in res.revisiones))
        for a in res.avisos:
            h(f"<div class='aviso'>{e(a)}</div>")

    with st.container(key="glass_resultado_subido"):
        titulo("Tu resultado, parcela por parcela",
               f"Se usó el mismo procedimiento del proyecto: {MODELOS[modelo]}. Si un municipio no tiene cosechas "
               "suficientes, se usa el valor de su grupo de registro y, como última opción, el de toda la región.")
        pid = st.selectbox("¿Cuál de tus parcelas quieres ver?", sorted(pu.index), key="parcela_subida")
        _parcela(pid, du, pu, cp, entrena)
        _explicacion()

    if res.con_mapa:
        with st.container(key="glass_mapa_subido"):
            titulo("Tus parcelas en el mapa")
            det = {i: (f"Estimación: {pu.prediccion[i]:.2f} t/ha · área {du.AREA_HA[i]:.2f} ha" if i in pu.index
                       else f"Registrado: {du.real[i]:.2f} t/ha · área {du.AREA_HA[i]:.2f} ha") for i in du.index}
            mapa(du, pu, list(du.index), (du.lon_c.mean(), du.lat_c.mean()), zoom_para(du), altura=480,
                 satelite=satelite, arriba=True, detalle=det, con_relieve=False, clave="mapa-subido")

    with st.container(key="glass_tabla_subido"):
        titulo("Todas tus parcelas por estimar", "La misma lectura que reciben las 59 del proyecto.")
        tabla = pu.reset_index()[["ID_POLIGONO", "municipio", "prediccion", "area_ha", "error_tipico", "fuente"]]
        tabla["confianza"] = cp.nivel.map(etiqueta_confianza).to_numpy()
        tabla["rango"] = [rango_texto(rangos.bajo.get(x), rangos.alto.get(x)) for x in tabla.municipio]
        st.dataframe(tabla.rename(columns={"prediccion": "estimación (t/ha)", "area_ha": "área (ha)",
                                           "error_tipico": "MAE del municipio (t/ha)",
                                           "rango": "rango del municipio"}), hide_index=True,
                     width="stretch", height=320,
                     column_config={"ID_POLIGONO": st.column_config.TextColumn(pinned=True),
                                    **{c: st.column_config.NumberColumn(format="%.2f")
                                       for c in ["estimación (t/ha)", "área (ha)", "MAE del municipio (t/ha)"]}})
        descarga = pu.reset_index()[["ID_POLIGONO", "prediccion"]].rename(columns={"prediccion": "RENDIMIENTO_T_HA"})
        descarga["confianza"] = cp.nivel.to_numpy()
        descarga["motivo"] = cp.motivo_detallado.to_numpy()
        descarga["rango_municipio_bajo"] = [rangos.bajo.get(x) for x in pu.municipio]
        descarga["rango_municipio_alto"] = [rangos.alto.get(x) for x in pu.municipio]
        st.download_button("Descargar estimaciones (CSV)", descarga.to_csv(index=False).encode("utf-8"),
                           file_name="estimaciones_dataset_propio.csv", mime="text/csv", type="primary",
                           on_click="ignore", key="descarga_subido")

    with st.expander("Ver el detalle técnico"):
        _detalle_tecnico(m, conf, rangos, mA)
