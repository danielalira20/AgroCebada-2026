"""Pruebas de la tabla única de cifras (M03):  python tests/backend/test_exportar.py  (desde app/)."""
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from agrocebada_app.backend.datos import lectura, paquete  # noqa: E402
from agrocebada_app.backend.datos.exportar import (  # noqa: E402
    COLUMNAS_PARCELAS, cifras_municipios, cifras_parcelas, cifras_validacion, exportar_todo)
from agrocebada_app.backend.dominio.cartera import cartera_municipios  # noqa: E402
from agrocebada_app.backend.dominio.confianza import confianza_municipios  # noqa: E402
from agrocebada_app.backend.dominio.rangos import rangos_municipio  # noqa: E402
from agrocebada_app.backend.dominio.validacion import COLUMNAS_POBLACIONES  # noqa: E402
from agrocebada_app.backend.modelo.estimador import predecir  # noqa: E402
from agrocebada_app.backend.rutas.localizador import rutas  # noqa: E402

p = lectura.leer_parcelas(rutas()["datos"])
O_media = paquete.validacion("media_mun__resp_grupo", p.municipio)
assert O_media is not None, "no encontré la validación de media_mun__resp_grupo (ni en datos_app/ ni en registro/t08)"
OA_media = O_media[(O_media.escenario == "A") & (O_media.fuente == "municipio")]
conf_media = confianza_municipios(p, OA_media)
pred_media = predecir(p, "media_mun__resp_grupo")

# --- cifras_parcelas: 197 filas, columnas y conteos correctos
cp = cifras_parcelas(p, pred_media, conf_media, "media_mun__resp_grupo")
assert list(cp.columns) == COLUMNAS_PARCELAS, list(cp.columns)
assert len(cp) == 197, len(cp)
assert cp.ID_POLIGONO.is_unique
pre = cp[cp.conjunto == "PREDICCION"]
tr = cp[cp.conjunto == "ENTRENAMIENTO"]
assert len(pre) == 59 and len(tr) == 138, (len(pre), len(tr))
assert pre.confianza.notna().all() and pre.motivo.notna().all()           # las 59 siempre traen confianza (M01)
assert tr.confianza.isna().all() and tr.fuente.isna().all()               # las 138 no son una estimación
assert np.isfinite(pre.estimacion).all() and np.isfinite(pre.produccion_t).all()
# AGC_011 (Chignahuapan) con la media da 4.48 t/ha, igual que en la ficha de cada módulo
f11 = cp.set_index("ID_POLIGONO").loc["AGC_011"]
assert abs(f11.estimacion - 4.48) < 0.005 and f11.municipio == "Chignahuapan", dict(f11)
assert abs(f11.produccion_t - f11.estimacion * f11.area_ha) < 1e-9
# producción con escenario: dentro de rango_bajo/alto × área, o la propia estimación si no hay rango
con_rango = pre.rango_bajo.notna()
assert (abs(pre[con_rango].produccion_baja_t - pre[con_rango].rango_bajo * pre[con_rango].area_ha) < 1e-6).all()
sin_rango = pre[~con_rango]
if len(sin_rango):
    assert (abs(sin_rango.produccion_baja_t - sin_rango.produccion_t) < 1e-9).all()
# una parcela con cosecha: su "estimación" es el valor registrado, no una del modelo
alguna_tr = tr.iloc[0]
assert alguna_tr.estimacion == p.loc[alguna_tr.ID_POLIGONO, "real"]

# --- cifras_municipios: la misma tabla que ya usa la pestaña Cartera (M10)
rangos = rangos_municipio(p[p.CONJUNTO == "ENTRENAMIENTO"])
esperado_cartera = cartera_municipios(p, pred_media, rangos, conf_media)
cm = cifras_municipios(p, pred_media, conf_media)
pd.testing.assert_frame_equal(cm, esperado_cartera)

# --- cifras_validacion: columnas y cifra principal comprobada (A · sin respaldo)
cv = cifras_validacion(O_media)
assert list(cv.columns) == COLUMNAS_POBLACIONES, list(cv.columns)
principal = cv[cv.principal].iloc[0]
assert principal.poblacion.startswith("A ·") and abs(principal.MAE - 0.3205) < 0.001, dict(principal)
# sin validación: tabla vacía con las mismas columnas, no un error
vacia = cifras_validacion(None)
assert vacia.empty and list(vacia.columns) == COLUMNAS_POBLACIONES

# --- cifras_parcelas con el modelo oficial (mediana) coincide exacto con el CSV de entrega de T18 (PR #41)
t18 = Path(__file__).resolve().parents[3] / "registro" / "t18" / "predicciones_finales.csv"
if t18.exists():
    pred_mediana = predecir(p, "mediana_mun__resp_grupo")
    O_mediana = paquete.validacion("mediana_mun__resp_grupo", p.municipio)
    OA_mediana = O_mediana[(O_mediana.escenario == "A") & (O_mediana.fuente == "municipio")]
    conf_mediana = confianza_municipios(p, OA_mediana)
    cp_mediana = cifras_parcelas(p, pred_mediana, conf_mediana, "mediana_mun__resp_grupo")
    pre_mediana = cp_mediana[cp_mediana.conjunto == "PREDICCION"].set_index("ID_POLIGONO")
    entrega = pd.read_csv(t18, encoding="utf-8-sig").set_index("ID_POLIGONO")
    assert set(entrega.index) == set(pre_mediana.index), set(entrega.index) ^ set(pre_mediana.index)
    dif = (entrega.RENDIMIENTO_T_HA - pre_mediana.loc[entrega.index, "estimacion"]).abs()
    assert dif.max() < 1e-9, f"cifras_parcelas no coincide con registro/t18/predicciones_finales.csv: {dif.max()}"

# --- exportar_todo: escribe los tres CSV y correr dos veces da archivos idénticos
with tempfile.TemporaryDirectory() as tmp:
    carpeta = Path(tmp) / "salida"
    rutas1 = exportar_todo(p, pred_media, conf_media, "media_mun__resp_grupo", O_media, carpeta)
    assert set(rutas1) == {"cifras_parcelas.csv", "cifras_municipios.csv", "cifras_validacion.csv"}
    assert all(r.exists() for r in rutas1.values())
    contenido1 = {n: r.read_bytes() for n, r in rutas1.items()}
    carpeta2 = Path(tmp) / "salida2"
    rutas2 = exportar_todo(p, pred_media, conf_media, "media_mun__resp_grupo", O_media, carpeta2)
    contenido2 = {n: r.read_bytes() for n, r in rutas2.items()}
    assert contenido1 == contenido2
    shutil.rmtree(carpeta, ignore_errors=True)
    shutil.rmtree(carpeta2, ignore_errors=True)

print("OK")
