"""Oráculos matemáticos y pruebas de aislamiento; no resultados reales."""
import copy
import unittest
import tempfile
from pathlib import Path
import numpy as np
import pandas as pd
from scripts import t15_cuantilica_modelo as m
from scripts.t15_cuantilica_auditar import auditar_estado, primal_independiente


def fixture(n=32):
    rng=np.random.RandomState(17);idx=[f'fila{i:03d}' for i in range(n)]
    X=pd.DataFrame(rng.normal(size=(n,5)),columns=m.S['jun_oct'],index=idx)
    X['municipio']=['uno']*(n//2)+['dos']*(n-n//2);X['cultivo_origen']='Cebada'
    y=pd.Series(np.where(X.municipio=='uno',3.,6.)+.8*X.iloc[:,0]-.4*X.iloc[:,1],index=idx)
    return X,y


class CuantilicaTests(unittest.TestCase):
    def test_mediana_par_canonica_y_municipios_libres(self):
        X,y=fixture(8);y[:4]=[0.,1.,8.,9.];y[4:]=[100.,103.,104.,110.]
        q=m.CuantilicaMunicipal().fit(X,y)
        self.assertEqual(q.estado()['interceptos'],{'dos':103.5,'uno':4.5})
        self.assertTrue(np.all(q.predict(X)[:4]==4.5))

    def test_recupera_pendientes_y_oraculo_independiente(self):
        X,y=fixture();q=m.CuantilicaMunicipal(m.S['jun_oct'],.001).fit(X,y)
        self.assertLess(np.max(abs(q.predict(X)-y)),1e-6)
        detail=q.predict_with_details(X)
        audit=auditar_estado(q.estado(),X,y,X,[dict(id_parcela=i,**v.to_dict()) for i,v in detail.iterrows()])
        self.assertGreater(audit['comprobaciones'],30)

    def test_alpha_fuerte_cero_y_medianas(self):
        X,y=fixture();q=m.CuantilicaMunicipal(m.S['jun_oct'],1.).fit(X,y)
        self.assertLess(np.max(np.abs(q.estado()['beta'])),1e-8)
        np.testing.assert_allclose(q.predict(X),m.CuantilicaMunicipal().fit(X,y).predict(X),atol=1e-7,rtol=0)

    def test_H3_correccion_entreno_media_cero(self):
        X,y=fixture();q=m.CuantilicaMunicipal(m.S['jun_oct'],.001).fit(X,y)
        d=q.predict_with_details(X)
        for g in X.municipio.unique():self.assertAlmostEqual(d.loc[X.municipio==g].correccion_satelital.mean(),0.,12)

    def test_traslacion_municipal_objetivo_no_penalizada(self):
        X,y=fixture();a=m.CuantilicaMunicipal(m.S['jun_oct'],.01).fit(X,y)
        change=(X.municipio=='uno')*20.;b=m.CuantilicaMunicipal(m.S['jun_oct'],.01).fit(X,y+change)
        np.testing.assert_allclose(a.predict(X)+change,b.predict(X),atol=1e-6,rtol=0)

    def test_orden_filas_y_consulta_independiente(self):
        X,y=fixture();a=m.CuantilicaMunicipal(m.S['jun_oct'],.01).fit(X,y)
        b=m.CuantilicaMunicipal(m.S['jun_oct'],.01).fit(X.iloc[::-1],y.iloc[::-1])
        np.testing.assert_array_equal(a.predict(X),b.predict(X))
        p=a.predict(X.iloc[:1]);z=X.copy();z.iloc[1:,0]=1e15
        np.testing.assert_array_equal(p,a.predict(z.iloc[:1]))
        before=copy.deepcopy(a.estado());a.predict(z);self.assertEqual(before,a.estado())

    def test_singleton_y_respaldo_sin_correccion(self):
        X,y=fixture();X.loc[X.index[-1],'municipio']='solo'
        q=m.CuantilicaMunicipal(m.S['jun_oct'],.001).fit(X,y)
        self.assertAlmostEqual(q.estado()['interceptos']['solo'],y.iloc[-1],12)
        z=X.iloc[:2].copy();z.index=['nueva1','nueva2'];z.municipio='desconocido';z.iloc[:,0]=1e10
        d=q.predict_with_details(z)
        self.assertTrue((d.correccion_satelital==0.).all());self.assertTrue((d.fuente=='grupo').all())
        np.testing.assert_array_equal(d.prediccion,np.full(2,np.median(y)))

    def test_constantes_y_colinealidad_canonica(self):
        X,y=fixture();X.iloc[:,1]=X.iloc[:,0];X.iloc[:,2:5]=4.
        q=m.CuantilicaMunicipal(m.S['jun_oct'],.001).fit(X,y)
        audit=auditar_estado(q.estado(),X,y,X,[dict(id_parcela=i,**v.to_dict()) for i,v in q.predict_with_details(X).iterrows()])
        self.assertEqual(audit['resultado'] if 'resultado' in audit else 'ok','ok')
        X.iloc[:,:5]=2.;a=m.CuantilicaMunicipal(m.S['jun_oct'],.001).fit(X,y)
        np.testing.assert_allclose(a.predict(X),m.CuantilicaMunicipal().fit(X,y).predict(X),atol=1e-7,rtol=0)

    def test_no_factor_n_en_alpha(self):
        X,y=fixture();a=m.CuantilicaMunicipal(m.S['jun_oct'],.01).fit(X,y)
        z=pd.concat([X,X.rename(index=lambda x:x+'c')]);v=pd.concat([y,y.rename(index=lambda x:x+'c')])
        b=m.CuantilicaMunicipal(m.S['jun_oct'],.01).fit(z,v)
        np.testing.assert_allclose(a.predict(X),b.predict(X),atol=1e-6,rtol=0)

    def test_estado_prediccion_reproducible_y_protegido(self):
        X,y=fixture();a=m.CuantilicaMunicipal(m.S['jun_oct'],.01).fit(X,y)
        np.testing.assert_array_equal(a.predict(X),m.predecir_estado(a.estado(),X).prediccion.to_numpy())
        state=a.estado();state['beta'][0]=1e8;self.assertNotEqual(a.estado()['beta'][0],1e8)
        a.alpha=.1
        with self.assertRaises(ValueError):a.predict(X)

    def test_rechazo_entradas(self):
        X,y=fixture()
        for col,a in [(m.S['jun_oct'],True),(m.S['jun_oct'],0.),(['municipio'],.01),([],1.)]:
            with self.assertRaises(ValueError):m.CuantilicaMunicipal(col,a).fit(X,y)
        bad=X.copy();bad.iloc[0,0]=np.nan
        q=m.CuantilicaMunicipal(m.S['jun_oct'],.01).fit(X,y)
        with self.assertRaises(ValueError):q.fit(bad,y)
        with self.assertRaises(ValueError):q.predict(X)
        with self.assertRaises(ValueError):m.CuantilicaMunicipal().fit(X,y[::-1])
        with self.assertRaises(ValueError):m.CuantilicaMunicipal().fit(X,y>0)

    def test_sin_solapamiento_y_desempate(self):
        X,y=fixture()
        with self.assertRaises(ValueError):m.ajustar(X,y,X.iloc[:1],m.OPCIONES[0])
        options=[dict(nombre='jun_oct__alpha_1',alpha=1.,ventana='jun_oct',MAE=.3),
                 dict(nombre='referencia_sola',alpha=None,ventana='estatica',MAE=.30000001)]
        self.assertEqual(min(options,key=m.clave)['nombre'],'referencia_sola')

    def test_certificado_dual_oraculo_unidimensional(self):
        D=np.array([[-1.],[1.],[-1.],[1.]]);y=np.array([2.,4.,7.,9.]);groups=np.array(['a','a','b','b'])
        beta,inter,solver=m.resolver_primal(D,y,groups,.01)
        bi,obj,dual=primal_independiente(D,y,groups,.01)
        np.testing.assert_allclose(beta,[1.],atol=1e-7);np.testing.assert_allclose(beta,bi,atol=1e-7)
        self.assertAlmostEqual(obj,.01,8);self.assertAlmostEqual(obj,dual,8)

    def test_auditor_detecta_corrimiento_H3(self):
        X,y=fixture();q=m.CuantilicaMunicipal(m.S['jun_oct'],.001).fit(X,y);state=q.estado()
        state['centros']['uno'][0]+=.1
        with self.assertRaises(ValueError):auditar_estado(state,X,y,X,[])

    def test_auditor_detecta_intercepto_y_coeficiente_alterado(self):
        X,y=fixture();q=m.CuantilicaMunicipal(m.S['jun_oct'],.001).fit(X,y)
        detail=[dict(id_parcela=i,**v.to_dict()) for i,v in q.predict_with_details(X).iterrows()]
        for name in ['intercepto','beta']:
            s=q.estado()
            if name=='intercepto':s['interceptos']['uno']+=.1
            else:s['beta'][0]+=.1
            with self.assertRaises(ValueError):auditar_estado(s,X,y,X,detail)

    def test_ejecutor_rechaza_completa_sin_puerta(self):
        from scripts.t15_cuantilica_ejecutar import comprobar_puerta, reportes
        with self.assertRaises(ValueError):comprobar_puerta(Path('.'),None)
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):reportes([],{}, {},Path(tmp),{}, {})

    def test_auditor_detecta_prediccion_alterada(self):
        X,y=fixture();q=m.CuantilicaMunicipal().fit(X,y)
        detail=[dict(id_parcela=i,**v.to_dict()) for i,v in q.predict_with_details(X).iterrows()]
        detail[0]['prediccion']+=.1
        with self.assertRaises(ValueError):auditar_estado(q.estado(),X,y,X,detail)

    def test_regresion_cero_numerico_en_cara_optima(self):
        # Caso que antes falló: A/rep3/fold0/interna2, sin usar consulta ni MAE externo.
        from scripts.t15_comparaciones_contrato import cargar
        from scripts.evaluacion_comun_modelo import preparar_contexto,divisiones_internas
        _,e=cargar();X,y,_=preparar_contexto(e,'A',3,0);sp=divisiones_internas(X,'A')[2]
        X=X.loc[list(sp.entrenamiento)];y=y.loc[X.index]
        q=m.CuantilicaMunicipal(m.S['jun_oct'],.01).fit(X,y)
        self.assertEqual(q.estado()['beta'][:2],[0.,0.])
        auditar_estado(q.estado(),X,y,X,[dict(id_parcela=i,**v.to_dict()) for i,v in q.predict_with_details(X).iterrows()])


if __name__=='__main__':unittest.main()
