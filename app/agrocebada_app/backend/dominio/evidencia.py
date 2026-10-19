"""Evidencia (M13): las tres preguntas guía del reto, la tabla de pruebas y lo que se aprendió. Es lógica sin
Streamlit: la pestaña la dibuja frontend/vistas/analista/pestanas/evidencia.py. Las cifras de las pruebas salen de
datos_estaticos/experimentos.csv (sólo resultados registrados, más tres pruebas marcadas como complementarias); lo que
depende del modelo vigente (su nombre, su error) se lee de la configuración y de la validación, nunca se escribe a mano."""
import numpy as np
import pandas as pd

from agrocebada_app.backend.dominio.desglose import NO_VE
from agrocebada_app.backend.dominio.validacion import poblaciones
from agrocebada_app.config import MODELO_OFICIAL, MODELOS

PREGUNTAS = {
    1: {"titulo": "¿Qué índice de vegetación pesa más?",
        "probado": "Cinco índices de vegetación y de agua (Planet, Sentinel-2 y Landsat), solos, juntos y quitando uno."},
    2: {"titulo": "¿Qué variable del clima pesa más?",
        "probado": "Lluvia acumulada y temperaturas mínima y máxima de la temporada, solas y juntas."},
    3: {"titulo": "¿Qué combinación funciona mejor?",
        "probado": "Clima, relieve y área, Planet y Sentinel-2, solos y combinados, y la mediana del municipio."},
}
CAUTELA = ("Esto no demuestra que el clima, el relieve o el satélite sean inútiles en cualquier modelo: sólo que, "
           "añadidos a este método y con estas parcelas, no mejoraron lo suficiente.")
REGLA = ("Una prueba se promueve si baja el error al menos 0.01 t/ha, su intervalo de confianza no incluye el cero y "
         "mejora en al menos 4 de 5 repeticiones, sin empeorar el RMSE (regla de promoción de T03 §4).")
FALTA = [("Fecha de siembra", "dos parcelas del mismo municipio pueden sembrarse con semanas de diferencia."),
         ("Variedad", "la base no dice qué cebada se sembró en cada parcela."),
         ("Manejo", "no hay datos de cómo se cuidó el cultivo, por ejemplo fertilización o riego.")]
MEDIANA = "mediana_mun__resp_grupo"
PAS, MEJ, SUBE, COMP = "✔ Pasó la regla", "▲ Mejora, pero no pasó la regla", "⚠ El error sube; no se promovió", "Prueba complementaria"


def _s(x):
    return "—" if pd.isna(x) else f"{x:+.4f}"


def marca(fila):
    """Resultado de una prueba con palabra e icono (nunca sólo color)."""
    if fila.estado == "complementaria":
        return COMP
    if bool(fila.pasa_regla):
        return PAS
    return MEJ if fila.delta_mae < 0 else SUBE


def _es_final(fila):
    return fila.tarea == "T16" and fila.estado == "registrada"


def etiqueta_prueba(fila, oficial=MODELO_OFICIAL):
    """Nombre de la prueba. La de T16 es «modelo final» sólo si la mediana es el modelo oficial."""
    if _es_final(fila):
        return "Mediana del municipio (modelo final)" if oficial == MEDIANA else "Mediana del municipio (alternativa evaluada)"
    return fila.prueba


def tabla(exp, pregunta=None, oficial=MODELO_OFICIAL):
    """Tabla lista para mostrar: una fila por prueba. Primero las registradas (de menor a mayor cambio de error) y
    después las complementarias. `pregunta=None` devuelve todas, ordenadas por pregunta."""
    x = exp if pregunta is None else exp[exp.pregunta == pregunta]
    x = x.assign(_c=(x.estado != "registrada").astype(int)).sort_values(["pregunta", "_c", "delta_mae"], kind="stable")
    filas = []
    for f in x.itertuples():
        reps = "—" if pd.isna(f.reps_mejoran) else f"{int(f.reps_mejoran)} de 5"
        ic = "—" if pd.isna(f.ic_inf) else f"[{_s(f.ic_inf)}, {_s(f.ic_sup)}]"
        filas.append({"pregunta": int(f.pregunta), "tarea": f.tarea, "prueba": etiqueta_prueba(f, oficial),
                      "estado": f.estado, "mae": f.mae, "cambio": f.delta_mae, "intervalo": ic, "repeticiones": reps,
                      "resultado": marca(f), "registro": "—" if pd.isna(f.registro) else f.registro, "fuente": f.fuente})
    return pd.DataFrame(filas)


def resumen(exp, pregunta, oficial=MODELO_OFICIAL):
    """Respuesta corta a una pregunta guía, con las cifras de sus pruebas registradas."""
    x = exp[(exp.pregunta == pregunta) & (exp.estado == "registrada")]
    n, pasan = len(x), int(x.pasa_regla.astype(bool).sum())
    mejor, peor = x.loc[x.delta_mae.idxmin()], x.loc[x.delta_mae.idxmax()]
    if pasan:
        frase = f"{pasan} de {n} pruebas registradas pasaron la regla."
    elif mejor.delta_mae >= 0:
        frase = (f"Ninguna de las {n} pruebas registradas bajó el error: el cambio va de {_s(mejor.delta_mae)} a "
                 f"{_s(peor.delta_mae)} t/ha. Por eso no se promovieron.")
    else:
        bajan = int((x.delta_mae < 0).sum())
        frase = (f"Ninguna de las {n} pruebas registradas pasó la regla. {bajan} bajaron el error; la que más, "
                 f"{etiqueta_prueba(mejor, oficial)}: {_s(mejor.delta_mae)} t/ha, con un intervalo que incluye el cero.")
    return {"pregunta": pregunta, "n": n, "pasan": pasan, "frase": frase,
            "mejor": etiqueta_prueba(mejor, oficial), "cambio_mejor": float(mejor.delta_mae)}


def referencia(exp):
    """MAE de la referencia (promedio del municipio) en la población de las pruebas registradas."""
    return float(exp.loc[exp.estado == "registrada", "mae_referencia"].round(4).mode().iloc[0])


def cierre_modelo_final(exp, oficial=MODELO_OFICIAL):
    """Cómo cierra la pregunta 3 según el modelo oficial. Sale de la fila de T16 y de la configuración."""
    f = exp[(exp.tarea == "T16") & (exp.estado == "registrada")].iloc[0]
    cifras = (f"La mediana del municipio bajó el error de {f.mae_referencia:.4f} a {f.mae:.4f} t/ha "
              f"({_s(f.delta_mae)}), en {int(f.reps_mejoran)} de 5 repeticiones, pero su intervalo "
              f"[{_s(f.ic_inf)}, {_s(f.ic_sup)}] incluye el cero y no llega a 0.01: no pasó la regla.")
    if oficial == MEDIANA:
        return (f"{cifras} Se adoptó como modelo final por tener el menor error; es una excepción explícita a la regla, "
                f"no una mejora confirmada.")
    return f"{cifras} Se conserva el promedio del municipio como modelo."


def ajuste_final(O, modelo=MODELO_OFICIAL):
    """Error del modelo vigente en la población principal de la validación (parcelas con cosecha estimadas sin usar su
    propia cosecha). None si no hay validación."""
    if O is None or O.empty:
        return None
    p = poblaciones(O).iloc[0]
    return {"modelo": MODELOS.get(modelo, modelo), "mae": float(p.MAE), "rmse": float(p.RMSE),
            "parcelas": int(p.parcelas), "predicciones": int(p.predicciones), "poblacion": p.poblacion}


def variacion_ubicacion(d):
    """Qué parte de las diferencias de rendimiento entre las parcelas con cosecha se reparte entre municipios
    (suma de cuadrados entre municipios sobre la total). Es descriptivo: se calcula con las mismas cosechas."""
    t = d[(d.CONJUNTO == "ENTRENAMIENTO") & d.real.notna()]
    y = t.real.astype(float)
    total = float(((y - y.mean()) ** 2).sum())
    entre = float(((t.groupby("municipio").real.transform("mean") - y.mean()) ** 2).sum())
    parte = entre / total if total > 0 else float("nan")
    pct = int(round(100 * parte)) if not np.isnan(parte) else None
    frase = ("" if pct is None else
             f"Saber el municipio explica cerca del {pct} % de las diferencias de rendimiento entre las {len(t)} parcelas "
             f"con cosecha de {t.municipio.nunique()} municipios; el {100 - pct} % restante ocurre dentro de cada municipio.")
    return {"parte": parte, "pct": pct, "parcelas": len(t), "municipios": int(t.municipio.nunique()), "frase": frase}


def lo_que_falta():
    """Información que el método no ve (siembra, variedad y manejo), con una línea de por qué importa."""
    return list(FALTA)
