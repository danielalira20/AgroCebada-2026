"""Pruebas de invariantes de T13 común sobre entradas reales; no predicciones ficticias."""
import copy
import unittest
from unittest.mock import patch
import numpy as np
from scripts import t15_t13_ejecutar as run
from scripts import t15_t13_datos as data
from scripts.t15_t13_auditar import AuditorT13
from scripts.evaluacion_comun_modelo import preparar_contexto,divisiones_internas
from scripts.evaluacion_comun_centrado_loo import CorreccionComunCentradaLOO,seleccionar
from scripts.t15_comparaciones_traza import ajustar_y_trazar


class T13Comun(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.c,cls.e,cls.side,_=run.cargar();cls.X,cls.y,cls.q=preparar_contexto(cls.e,'A',1,0)
        cls.X=run.unir_side(cls.X,cls.side,cls.c['variables_nuevas']);cls.q=run.unir_side(cls.q,cls.side,cls.c['variables_nuevas'])
        cls.p=cls.c['procedimientos'][1];cls.o=run.opciones(cls.p)[2]

    def test_datos_cotejados_con_ZIP_sin_etiquetas(self):
        a=data.auditar();self.assertEqual(a['parcelas'],197);self.assertEqual(a['comparaciones'],1576);self.assertFalse(a['lee_rendimientos'])

    def test_union_1a1_no_depende_del_orden(self):
        clean=self.X.drop(columns=self.c['variables_nuevas'])
        a=run.unir_side(clean,self.side.iloc[::-1],self.c['variables_nuevas']);self.assertTrue(a.equals(self.X))

    def test_union_rechaza_ID_ausente(self):
        with self.assertRaises(ValueError):run.unir_side(self.X.drop(columns=self.c['variables_nuevas']),self.side.drop(self.X.index[0]),self.c['variables_nuevas'])

    def test_union_rechaza_ID_duplicado(self):
        import pandas as pd
        with self.assertRaises(ValueError):run.unir_side(self.X.drop(columns=self.c['variables_nuevas']),pd.concat([self.side,self.side.iloc[:1]]),self.c['variables_nuevas'])

    def test_union_rechaza_faltantes_y_colision(self):
        side=self.side.copy();side.loc[self.X.index[0],self.c['variables_nuevas'][0]]=np.nan
        with self.assertRaises(ValueError):run.unir_side(self.X.drop(columns=self.c['variables_nuevas']),side,self.c['variables_nuevas'])
        with self.assertRaises(ValueError):run.unir_side(self.X,self.side,self.c['variables_nuevas'])

    def test_ninguna_reservada_en_particiones_internas(self):
        for esc in ['A','B']:
            X,_,q=preparar_contexto(self.e,esc,1,0)
            for d in divisiones_internas(X,esc):
                self.assertFalse((set(d.entrenamiento)|set(d.validacion)|set(q.index))&self.e['reservados'])
                if esc=='B':self.assertFalse(set(X.loc[list(d.entrenamiento),'celda_chirps'])&set(X.loc[list(d.validacion),'celda_chirps']))

    def test_escalado_y_pools_solo_entrenamiento(self):
        m=CorreccionComunCentradaLOO(self.o['columnas'],self.o['lambda_reg']).fit(self.X,self.y);s=m.estado()
        np.testing.assert_allclose(s['media'],self.X[self.o['columnas']].mean().to_numpy(),atol=1e-12,rtol=0)
        for pid,pool in s['pools_sin_fila'].items():
            self.assertNotIn(pid,pool['ids']);self.assertFalse(set(pool['ids'])&set(self.q.index))

    def test_H3_corrimiento_municipal_cero(self):
        m=CorreccionComunCentradaLOO(self.o['columnas'],self.o['lambda_reg']).fit(self.X,self.y)
        d=m.predict_with_details(self.X)
        self.assertLess(d.correccion.groupby(self.X.municipio).mean().abs().max(),1e-12)

    def test_consulta_no_reaprende_escala_ni_centro(self):
        m=CorreccionComunCentradaLOO(self.o['columnas'],self.o['lambda_reg']).fit(self.X,self.y);state=copy.deepcopy(m.estado())
        q=self.q.copy();q.loc[:,self.o['columnas']]=1e6;m.predict(q)
        self.assertEqual(state,m.estado())

    def test_etiqueta_inyectada_en_consulta_no_cambia_prediccion(self):
        m=CorreccionComunCentradaLOO(self.o['columnas'],self.o['lambda_reg']).fit(self.X,self.y)
        q=self.q.copy();q['rendimiento_t_ha']=99999.;np.testing.assert_array_equal(m.predict(q),m.predict(self.q))

    def test_no_admite_rendimiento_como_predictor(self):
        X=self.X.copy();X['rendimiento_t_ha']=self.y
        with self.assertRaises(ValueError):CorreccionComunCentradaLOO(['rendimiento_t_ha'],.1).fit(X,self.y)

    def test_selector_coincide_con_nucleo_inmutable(self):
        _,expected=run.seleccionar(self.X,self.y,self.p,'A',lambda t:None,dict(candidato=self.p['candidato'],escenario='A',repeticion=1,particion=0))
        other=seleccionar(self.X,self.y,run.opciones(self.p)[1:],'A')
        self.assertEqual(expected,other['puntuaciones'])

    def test_oraculo_recalcula_estado_y_rechaza_H3_quitado(self):
        elig=tuple(bool(v) for v in self.q.municipio.isin(self.X.municipio));m,d,t=ajustar_y_trazar(self.X,self.y,self.q,self.o,elig)
        t.update(estado_modelo=m.estado(),consulta=[dict(id_parcela=i,**v.to_dict()) for i,v in d.iterrows()],candidato=self.p['candidato'],escenario='A',repeticion=1,particion=0,etapa='externa')
        AuditorT13(run.RAIZ).record(t)
        bad=copy.deepcopy(t);s=m.estado();beta=np.array(s['coeficientes']);z=(self.q[self.o['columnas']].to_numpy()-s['media'])/s['escala'];cor=z@beta
        for r,v in zip(bad['consulta'],cor):r['correccion']=float(v);r['prediccion']=r['referencia']+float(v)
        with self.assertRaises(ValueError):AuditorT13(run.RAIZ).record(bad)

    def test_ref_sola_y_respaldo_grupo_global(self):
        q=self.q.iloc[:2].copy();q['municipio']='nuevo';m=CorreccionComunCentradaLOO().fit(self.X,self.y)
        d=m.predict_with_details(q);self.assertTrue((d.correccion==0).all());self.assertTrue((d.fuente=='grupo').all())
        # El grupo desconocido se rechaza explícitamente: el contrato de origen sólo admite dos grupos.
        q['cultivo_origen']='nuevo'
        with self.assertRaises(ValueError):m.predict(q)

    def test_puerta_no_se_puede_omitir(self):
        with self.assertRaises(ValueError):run.comprobar_puerta(run.RAIZ,None)

    def test_selector_ignora_cambios_de_y_externa(self):
        # No recibe y externa; centinela en la tabla no altera las X/y de entrenamiento.
        e=copy.deepcopy(self.e)
        for pid in self.q.index:e['tabla'][(pid,)]['rendimiento_t_ha']='99999'
        X,y,q=preparar_contexto(e,'A',1,0)
        self.assertTrue(y.equals(self.y));self.assertTrue(X.equals(self.X.drop(columns=self.c['variables_nuevas'])))

    def test_reportes_admiten_mediana_sin_cambiar_version_original(self):
        import tempfile
        from pathlib import Path
        c,e,side,old=run.cargar()
        table={k[0]:v for k,v in e['tabla'].items()};quality={r['id_parcela']:r for r in run.leer_csv(run.RAIZ/'registro/t07/calidad_parcelas.csv')[1]}
        ctr=dict(principal=dict(procedimientos=[dict(candidato=n) for n in c['comparadores_reutilizados'] if n!=run.REF],contrastes_planificados=[dict(candidato='comun_centrado_loo_v3_S',frente_a=run.REF,tipo='descriptivo')]))
        original=copy.deepcopy(old)
        with tempfile.TemporaryDirectory() as d:
            run.tablas(old,e['contextos'],ctr,quality,table,Path(d))
            self.assertEqual(len(run.leer_csv(Path(d)/'metricas_resumen.csv')[1]),12)
        self.assertEqual(old,original)

    def test_reportes_rechazan_reetiquetar_version_de_mediana(self):
        import tempfile
        from pathlib import Path
        c,e,side,old=run.cargar()
        for row in old:
            if row['candidato']=='mediana_mun__resp_grupo':row['version']='comun-centrado-loo-v3'
        ctr=dict(principal=dict(procedimientos=[dict(candidato=n) for n in c['comparadores_reutilizados'] if n!=run.REF],contrastes_planificados=[dict(candidato='comun_centrado_loo_v3_S',frente_a=run.REF,tipo='descriptivo')]))
        with tempfile.TemporaryDirectory() as d,self.assertRaises(ValueError):run.tablas(old,e['contextos'],ctr,{}, {},Path(d))


if __name__=='__main__':unittest.main()
