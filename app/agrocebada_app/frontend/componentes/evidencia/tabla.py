"""Explorador de pruebas y catálogo completo: filtros, gráfico/tabla y trazabilidad bajo demanda."""
import pandas as pd
import streamlit as st

from agrocebada_app.backend.dominio.evidencia import etiqueta_prueba, filtrar_pruebas, marca, referencia, tabla
from agrocebada_app.frontend.componentes.evidencia.comparacion import comparacion
from agrocebada_app.frontend.tema.html import e, h, titulo

TEMAS = {1: "Vegetación", 2: "Clima", 3: "Combinaciones"}
RESULTADOS = {"Todos": "todas", "Bajan el error": "bajan", "No bajan el error": "no_bajan"}
COLUMNAS = {"pregunta": "Pregunta", "tarea": "Tarea", "prueba": "Prueba", "mae": "MAE (t/ha)", "cambio": "Cambio (t/ha)",
            "intervalo": "Intervalo 95 %", "repeticiones": "Repeticiones que mejoran", "resultado": "Resultado",
            "registro": "Registro", "fuente": "Fuente"}
FORMATOS = {"MAE (t/ha)": st.column_config.NumberColumn(format="%.4f"),
            "Cambio (t/ha)": st.column_config.NumberColumn(format="%+.4f")}


def _restablecer():
    st.session_state["evid_resultado"] = "Todos"
    st.session_state["evid_complementarias"] = False
    st.session_state.pop("evid_prueba", None)


def _tabla_resumen(x, oficial):
    t = tabla(x, None, oficial)[["prueba", "cambio", "resultado"]].rename(columns=COLUMNAS)
    with st.container(key="evid_tabla_desktop"):
        st.dataframe(t, hide_index=True, width="stretch", column_config=FORMATOS)
    filas = "".join(f"<article class='evid-fila'><h3>{e(etiqueta_prueba(f, oficial))}</h3>"
                    f"<b>{f.delta_mae:+.4f} t/ha</b><span>{e(marca(f))}</span></article>" for f in x.itertuples())
    h("<div class='evid-tabla-movil'>" + filas + "</div>")


def _detalle(x, oficial):
    ids = list(x.index)
    if st.session_state.get("evid_prueba") not in ids:
        st.session_state.pop("evid_prueba", None)
    elegido = st.selectbox("Consultar una prueba", ids, key="evid_prueba",
                          format_func=lambda i: f"{ids.index(i)+1:02d} · {x.loc[i, 'tarea']} · {etiqueta_prueba(x.loc[i], oficial)}")
    f = x.loc[elegido]
    estado = "complementaria" if f.estado == "complementaria" else "mejora" if f.delta_mae < 0 else "sin-mejora"
    h(f"<div class='evid-ficha'><div class='evid-ficha-titulo'><h3>{e(etiqueta_prueba(f, oficial))}</h3>"
      f"<span class='evid-estado evid-{estado}'>{e(marca(f))}</span></div><dl class='evid-cifras'>"
      f"<div><dt>MAE</dt><dd>{f.mae:.4f}<small>t/ha</small></dd></div>"
      f"<div><dt>Cambio frente a la media</dt><dd>{f.delta_mae:+.4f}<small>t/ha</small></dd></div></dl></div>")
    with st.expander("Cómo se evaluó y de dónde sale", expanded=False):
        if f.estado == "complementaria":
            st.info("Prueba complementaria: posterior a los resultados, sin registro formal ni intervalo. No cuenta para la regla.")
        else:
            st.caption(str(f.motivo))
        ic = "No disponible" if pd.isna(f.ic_inf) else f"[{f.ic_inf:+.4f}, {f.ic_sup:+.4f}] t/ha"
        reps = "No disponible" if pd.isna(f.reps_mejoran) else f"{int(f.reps_mejoran)} de 5"
        registro = "Sin registro formal" if pd.isna(f.registro) else f.registro
        h(f"<dl class='evid-traza'><div><dt>Intervalo del 95 %</dt><dd>{e(ic)}</dd></div>"
          f"<div><dt>Repeticiones que mejoran</dt><dd>{e(reps)}</dd></div>"
          f"<div><dt>Registro</dt><dd>{e(registro)}</dd></div>"
          f"<div><dt>Fuente</dt><dd>{e(f.fuente)}</dd></div></dl>")
        if pd.notna(f.nota):
            st.caption(str(f.nota))


def explorador(exp, oficial):
    with st.container(key="glass_evid_explora"):
        titulo("Explora las pruebas", "Elige una pregunta. Compara el error y consulta el detalle que necesites.")
        tema = st.segmented_control("Pregunta a explorar", list(TEMAS), default=3, format_func=TEMAS.get,
                                    key="evid_pregunta") or 3
        with st.container(key="evid_filtros"):
            c1, c2 = st.columns([1, 1])
            with c1:
                resultado = st.selectbox("Resultado", list(RESULTADOS), key="evid_resultado")
            with c2:
                modo = st.segmented_control("Ver como", ["Gráfico", "Tabla"], default="Gráfico", key="evid_modo") or "Gráfico"
            comp = st.checkbox("Incluir pruebas complementarias", key="evid_complementarias",
                               help="Se muestran aparte de las registradas; no tienen intervalo ni cuentan para la regla.")
        x = filtrar_pruebas(exp, tema, RESULTADOS[resultado], comp)
        total = len(filtrar_pruebas(exp, tema, complementarias=comp))
        ref = referencia(exp)
        contexto = f" · referencia histórica: media municipal, MAE {ref:.4f} t/ha" if ref is not None else ""
        st.caption(f"{len(x)} de {total} pruebas de {TEMAS[tema].lower()}{contexto}. Negativo significa menos error.")
        if x.empty:
            st.info("No hay pruebas con esta combinación. Cambia Resultado o restablece los filtros de esta pregunta.")
            st.button("Restablecer filtros", key="evid_restablecer", on_click=_restablecer)
        else:
            if modo == "Gráfico":
                comparacion(x, oficial)
            else:
                with st.container(key="evid_tabla_resumen"):
                    _tabla_resumen(x, oficial)
            _detalle(x, oficial)


def tabla_completa(exp, oficial):
    with st.expander(f"Catálogo completo y fuentes ({len(exp)} pruebas)", expanded=False):
        st.caption("Todas las preguntas, sin los filtros del explorador. El CSV conserva también motivos y notas.")
        t = tabla(exp, None, oficial)[list(COLUMNAS)].rename(columns=COLUMNAS)
        st.dataframe(t, hide_index=True, width="stretch", height=460, column_config=FORMATOS)
        st.download_button(f"Descargar las {len(exp)} pruebas (CSV)", exp.to_csv(index=False).encode("utf-8-sig"),
                           file_name="evidencia_experimentos.csv", mime="text/csv", key="evid_descarga", on_click="ignore")
