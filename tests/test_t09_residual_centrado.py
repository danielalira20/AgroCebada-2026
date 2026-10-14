"""Controles esenciales de fit/predict R centrado; no evaluación externa completa."""
import json
import tempfile
import unittest
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.exceptions import NotFittedError

from scripts.t09_entradas import cargar_entradas, contexto_externo
from scripts.t09_estimadores import (CLIMA, MediaTerritorial, RidgeClimatico,
                                    columnas_clima, crear_estimador)
from scripts.t09_residual_centrado import RidgeResidualCentrado, VERSION
from scripts.t09_seleccion import ajustar_particion, particiones_internas, elegir_configuracion


def referencia_directa(X, y, fila):
    mun = y[X.municipio.eq(fila.municipio)]
    grupo = y[X.cultivo_origen.eq(fila.cultivo_origen)]
    return float(mun.mean() if len(mun) else grupo.mean() if len(grupo) else y.mean())


def solucion_directa(X, y, te, ventana, intensidad):
    """NumPy sin Ridge ni StandardScaler; LOO por eliminación explícita."""
    cols = columnas_clima(ventana)
    raw = X[cols].to_numpy(float)
    mu, sd = raw.mean(0), raw.std(0)
    sd = np.where(sd == 0, 1., sd)
    z, zt = (raw-mu)/sd, (te[cols].to_numpy(float)-mu)/sd
    mun = {m: z[X.municipio.eq(m).to_numpy()].mean(0) for m in X.municipio.unique()}
    grupo = {g: z[X.cultivo_origen.eq(g).to_numpy()].mean(0) for g in X.cultivo_origen.unique()}
    d = z - np.array([mun[m] for m in X.municipio])
    r = np.array([y.loc[pid]-referencia_directa(X.drop(index=pid),
                  y.drop(index=pid), fila) for pid, fila in X.iterrows()])
    beta = np.linalg.lstsq(np.vstack([d, np.sqrt(len(X)*intensidad)*np.eye(3)]),
                          np.r_[r, np.zeros(3)], rcond=None)[0]
    center = np.array([mun.get(row.municipio, grupo.get(row.cultivo_origen, z.mean(0)))
                       for row in te.itertuples()])
    base = np.array([referencia_directa(X,y,row) for row in te.itertuples()])
    return base+(zt-center)@beta, beta, mu, sd


class ImplementacionCentrada(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        e = cargar_entradas()
        cls.a, cls.ya, cls.b, _ = contexto_externo(e, 'A', 1, 0)

    def test_fabrica_separa_variantes_y_selector_v1_no_adopta_v2(self):
        self.assertIsInstance(crear_estimador('R'), RidgeClimatico)
        self.assertIsInstance(crear_estimador('R_centrado'), RidgeResidualCentrado)
        with self.assertRaises(ValueError):
            elegir_configuracion(self.a, self.ya, 'R_centrado')

    def test_matrices_independientes_ambas_ventanas_y_cuatro_lambdas(self):
        for w in ['abr_oct','jun_oct']:
            for intensidad in [.01,.1,1.,10.]:
                m = crear_estimador('R_centrado',w,intensidad).fit(self.a,self.ya)
                pred,beta,mu,sd = solucion_directa(self.a,self.ya,self.b,w,intensidad)
                with self.subTest(ventana=w,lambda_reg=intensidad):
                    np.testing.assert_allclose(m.predict(self.b),pred,rtol=0,atol=1e-9)
                    np.testing.assert_allclose(m.coef_estandarizados_,beta,rtol=0,atol=1e-10)
                    np.testing.assert_allclose(m.preprocesado_['escala'].mean_,mu,rtol=0,atol=1e-12)
                    np.testing.assert_allclose(m.preprocesado_['escala'].scale_,sd,rtol=0,atol=1e-12)

    def test_media_municipal_correccion_cero_y_fila_en_centro_reproduce_T(self):
        m = crear_estimador('R_centrado').fit(self.a,self.ya)
        d = m.predict_with_details(self.a)
        self.assertLess(d.correccion.groupby(self.a.municipio).mean().abs().max(),1e-12)
        medio = self.a.copy()
        for col in columnas_clima('jun_oct'):
            medio[col] = self.a.municipio.map(self.a.groupby('municipio')[col].mean())
        base = MediaTerritorial().fit(self.a,self.ya).predict(medio)
        np.testing.assert_allclose(m.predict(medio),base,rtol=0,atol=1e-10)

    def test_respaldos_municipio_nuevo_grupo_y_global_con_matrices(self):
        q = self.b.copy();q['municipio']='municipio no observado'
        q.loc[q.index[0],'cultivo_origen']='grupo no observado'
        m = crear_estimador('R_centrado').fit(self.a,self.ya)
        pred,_,_,_ = solucion_directa(self.a,self.ya,q,'jun_oct',.1)
        d = m.predict_with_details(q)
        np.testing.assert_allclose(d.prediccion,pred,rtol=0,atol=1e-9)
        self.assertEqual(d.fuente.iloc[0],'global')
        self.assertTrue(d.fuente.iloc[1:].eq('grupo').all())
        np.testing.assert_array_equal(d.fuente,d.fuente_centrado)

    def test_predict_no_aprende_y_cambiar_y_validacion_no_afecta_fit(self):
        part = particiones_internas(self.a,'A')[0]
        m,p = ajustar_particion(self.a,self.ya,part,'R_centrado','jun_oct',.1)
        altered = self.ya.copy();altered.loc[list(part.validacion)] += 1000
        m2,p2 = ajustar_particion(self.a,altered,part,'R_centrado','jun_oct',.1)
        self.assertEqual(m.estado(),m2.estado())
        np.testing.assert_array_equal(p,p2)
        before = json.dumps(m.estado(),sort_keys=True)
        q = self.b.copy();q.loc[:,list(CLIMA)] *= 100
        m.predict(q)
        self.assertEqual(json.dumps(m.estado(),sort_keys=True),before)

    def test_clone_serializacion_y_reordenamiento(self):
        m = crear_estimador('R_centrado').fit(self.a,self.ya)
        m2 = clone(m).fit(self.a.iloc[::-1],self.ya.iloc[::-1])
        self.assertEqual(m.estado(),m2.estado())
        with tempfile.TemporaryDirectory() as tmp:
            file=Path(tmp)/'modelo.joblib';joblib.dump(m,file)
            loaded=joblib.load(file)
            self.assertEqual(loaded.estado()['version_modelo'],VERSION)
            np.testing.assert_array_equal(m.predict(self.b),loaded.predict(self.b))
        state=m.estado();first=next(iter(state['centros_Z_municipio']))
        state['centros_Z_municipio'][first][0] += 100
        self.assertEqual(m.estado(),m2.estado())

    def test_fit_fallido_y_cambio_parametros_invalidan_aplicacion(self):
        m = crear_estimador('R_centrado').fit(self.a,self.ya)
        with self.assertRaises(ValueError):m.fit(self.a,self.ya*np.nan)
        with self.assertRaises(NotFittedError):m.predict(self.b)
        m.fit(self.a,self.ya);m.set_params(ventana='abr_oct')
        with self.assertRaises(ValueError):m.predict(self.b)
        with self.assertRaises(ValueError):m.estado()

    def test_clima_solo_territorial_y_municipios_unicos_no_crean_senal(self):
        a = self.a.copy()
        for c in CLIMA:a[c]=a.municipio.map(a.groupby('municipio')[c].mean())
        m=crear_estimador('R_centrado').fit(a,self.ya)
        np.testing.assert_allclose(m.predict_with_details(a).correccion,0,rtol=0,atol=1e-10)
        unique=self.a.copy();unique['municipio']=['m_'+pid for pid in unique.index]
        m=crear_estimador('R_centrado').fit(unique,self.ya)
        self.assertEqual(m.n_entrenamiento_,len(unique))
        np.testing.assert_array_equal(m.coef_estandarizados_,np.zeros(3))
        np.testing.assert_allclose(m.predict_with_details(unique).correccion,0,rtol=0,atol=1e-12)


if __name__=='__main__':unittest.main()
