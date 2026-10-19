"""Cálculos, persistencia y modos limitados; no ejecuta T15 completa."""
import copy
import csv
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from scripts import evaluacion_comun_contrato as comun
from scripts import evaluacion_comun_centrado_loo as v3
from scripts import t15_comparaciones_contrato as contrato
from scripts import t15_comparaciones_traza as traza
from scripts import t15_ejecutar as runner
from scripts import t15_ejecutor_reportes as reportes
from scripts import t15_registro_operativo as registro
from scripts.evaluacion_comun_modelo import preparar_contexto


class Reportes(unittest.TestCase):
    def test_metricas_a_mano_y_sin_cancelar_errores(self):
        rows=[dict(ID_POLIGONO='a',repeticion=1,real=1,prediccion=2),
              dict(ID_POLIGONO='a',repeticion=2,real=1,prediccion=0),
              dict(ID_POLIGONO='b',repeticion=1,real=3,prediccion=3),
              dict(ID_POLIGONO='b',repeticion=2,real=3,prediccion=3)]
        m=reportes.resumen_grupo(rows)
        self.assertEqual(m['MAE_por_parcela'],.5)
        self.assertAlmostEqual(m['RMSE_igual_peso_parcela'],np.sqrt(.5))
        self.assertEqual(m['R2_igual_peso_parcela'],.5)
        self.assertEqual(m['sesgo_por_parcela'],0)

    def test_B_igual_peso_ID_no_confunde_registros(self):
        rows=[dict(ID_POLIGONO='a',repeticion=i,real=1,prediccion=1) for i in range(1,6)]
        rows.append(dict(ID_POLIGONO='b',repeticion=1,real=2,prediccion=4))
        m=reportes.resumen_grupo(rows)
        self.assertEqual(m['MAE_por_parcela'],1)
        self.assertNotEqual(m['MAE_por_parcela'],2/6)
        self.assertEqual((m['n_parcelas'],m['n_predicciones']),(2,6))

    def test_R2_constante_decimal_indefinido(self):
        rows=[dict(ID_POLIGONO=str(i),repeticion=1,real=2.3,prediccion=2.4) for i in range(13)]
        m=reportes.resumen_grupo(rows)
        self.assertIsNone(m['R2_igual_peso_parcela'])
        self.assertIsNone(m['R2_media_repeticiones'])

    def test_grupo_vacio_explicito(self):
        m=reportes.resumen_grupo([])
        self.assertEqual(m['n_parcelas'],0);self.assertIsNone(m['MAE_por_parcela'])

    def test_no_sobrescribir_csv(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'a.csv'
            reportes.csv_guardar(p,[dict(a=1)])
            with self.assertRaises(FileExistsError):reportes.csv_guardar(p,[dict(a=2)])


class Ejecutor(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.c,cls.e=contrato.cargar()
        cls.pre=contrato.preflight(cls.e)
        cls.operativo=registro.cargar(comun.RAIZ,cls.c)
        cls.g=next(p for p in cls.c['principal']['procedimientos'] if p['bloques']==['G'])

    def test_registro_usuario_sin_aprobaciones_inventadas(self):
        self.assertFalse(self.operativo['cierre']['revision_externa_requerida'])
        self.assertFalse(self.operativo['cierre']['aprobacion_Daf_atribuida'])
        self.assertFalse(self.operativo['cierre']['aprobacion_Migue_atribuida'])
        self.assertFalse(self.operativo['evaluacion_completa_en_esta_solicitud'])
        self.assertEqual(self.operativo['extensiones_activadas'],[])

    def test_registro_alterado_rechazado(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);p=root/registro.RUTA;p.parent.mkdir(parents=True)
            p.write_text('{}')
            with self.assertRaisesRegex(ValueError,'alterado'):registro.cargar(root,self.c)

    def test_completa_sin_confirmacion_no_entrena_ni_crea_salida(self):
        with tempfile.TemporaryDirectory() as d,patch.object(runner,'ejecutar_contexto') as mock:
            out=Path(d)/'salida'
            with self.assertRaisesRegex(ValueError,'confirmación'):
                runner.ejecutar(comun.RAIZ,out,'completa')
            mock.assert_not_called();self.assertFalse(out.exists())

    def test_confirmacion_fuera_de_completa_rechazada(self):
        with self.assertRaises(ValueError):runner.ejecutar(comun.RAIZ,'no_usar','prueba',confirmar_completa=True)

    def test_verificar_cero_modelos(self):
        with tempfile.TemporaryDirectory() as d,patch.object(runner,'ejecutar_contexto',side_effect=AssertionError('no entrenar')):
            with patch.object(contrato,'preflight',return_value=self.pre):
                m=runner.ejecutar(comun.RAIZ,Path(d)/'v','verificar')
            self.assertEqual(m['estado'],'verificado_sin_modelos')
            self.assertEqual(sum(m['contadores'].values()),0)

    def test_destino_fuentes_y_existente_rechazados(self):
        with self.assertRaises(ValueError):runner.validar_salida(comun.RAIZ/'scripts'/'nuevo',comun.RAIZ)
        with self.assertRaises(ValueError):runner.validar_salida(comun.RAIZ/'README.md',comun.RAIZ)
        with self.assertRaises(ValueError):runner.validar_salida(comun.RAIZ.parent,comun.RAIZ)

    def test_extensiones_no_pueden_entrar_como_prueba(self):
        with tempfile.TemporaryDirectory() as d,patch.object(contrato,'preflight',return_value=self.pre):
            with self.assertRaisesRegex(ValueError,'principal'):
                runner.ejecutar(comun.RAIZ,Path(d)/'sg','prueba',codigo='SG')

    def test_prueba_real_G_A_guarda_seleccion_estados_trazas(self):
        with tempfile.TemporaryDirectory() as d,patch.object(contrato,'preflight',return_value=self.pre):
            out=Path(d)/'prueba'
            m=runner.ejecutar(comun.RAIZ,out,'prueba',codigo='G')
            self.assertEqual(m['estado'],'comprobacion_funcional_parcial')
            self.assertFalse(m['evaluacion_completa']);self.assertEqual(m['contextos_ejecutados'],1)
            self.assertEqual(m['contadores']['ajustes_internos'],20)
            trazas=[json.loads(l) for l in (out/'trazas_ajustes.jsonl').read_text().splitlines()]
            self.assertEqual(len(trazas),22)
            self.assertEqual(len((out/'selecciones.jsonl').read_text().splitlines()),1)
            self.assertEqual(len((out/'estados_modelos.jsonl').read_text().splitlines()),2)
            rows=comun.leer_csv(out/'oof_parcial_prueba.csv')[1]
            self.assertEqual(len(rows),56)
            self.assertFalse((out/'contrastes.csv').exists())
            X,y,te=preparar_contexto(self.e,'A',1,0)
            opts=[dict(o,nombre=f"{o['ventana']}__lambda_{o['lambda_reg']:g}") for o in self.g['opciones']]
            esperada=v3.seleccionar(X,y,opts,'A')
            sel=json.loads((out/'selecciones.jsonl').read_text())
            self.assertEqual(sel['nombre_opcion'],esperada['elegida']['nombre'])
            for r in rows:
                self.assertNotIn(r['ID_POLIGONO'],self.e['reservados'])
            for name,h in m['archivos_sha256'].items():self.assertEqual(comun.sha(out/name),h)

    def test_fallo_persistido_y_no_entrega_completa(self):
        with tempfile.TemporaryDirectory() as d,patch.object(contrato,'preflight',return_value=self.pre):
            out=Path(d)/'fallo'
            def falla(e,procs,s,r,p,emitir,**kw):
                emitir(dict(estado='fallido',etapa='interna',error='fallo controlado'))
                raise ValueError('fallo controlado')
            with patch.object(runner,'ejecutar_contexto',side_effect=falla):
                with self.assertRaisesRegex(ValueError,'controlado'):runner.ejecutar(comun.RAIZ,out,'prueba')
            m=json.loads((out/'manifest.json').read_text())
            self.assertEqual(m['estado'],'fallido');self.assertFalse(m['evaluacion_completa'])
            self.assertIn('fallo controlado',(out/'trazas_ajustes.jsonl').read_text())

    def test_fallo_interno_conserva_trazas_previas(self):
        X,y,_=preparar_contexto(self.e,'A',1,0);opts=[dict(self.g['opciones'][0],nombre='G')]
        eventos=[];real=traza.ajustar_y_trazar;n=0
        def control(*a,**kw):
            nonlocal n
            n+=1
            if n==3:raise traza.ErrorAjuste('fallo controlado',dict(estado='fallido'))
            return real(*a,**kw)
        with patch.object(traza,'ajustar_y_trazar',side_effect=control):
            with self.assertRaises(traza.ErrorAjuste):
                traza.seleccionar_con_traza(X,y,opts,'A',al_ajuste=eventos.append)
        self.assertEqual([t['estado'] for t in eventos],['correcto','correcto','fallido'])

    def test_callback_no_modifica_la_seleccion(self):
        X,y,_=preparar_contexto(self.e,'A',1,0)
        opts=[dict(self.g['opciones'][0],nombre='G')]
        def alterar(t):t['MAE']=99999;t['ids_entrenamiento'].clear()
        a=traza.seleccionar_con_traza(X,y,opts,'A')
        b=traza.seleccionar_con_traza(X,y,opts,'A',al_ajuste=alterar)
        self.assertEqual(a,b)

    def test_etiquetas_externas_no_cambian_seleccion_ni_predicciones(self):
        eventos=[]
        a,sa,_=runner.ejecutar_contexto(self.e,[self.g],'B',1,0,eventos.append)
        e=copy.deepcopy(self.e)
        for k,v in e['contextos'].items():
            if k[0]=='B' and k[1]==1 and v['particion']==0:v['real']+=1000
        b,sb,_=runner.ejecutar_contexto(e,[self.g],'B',1,0,lambda t:None)
        self.assertEqual(sa,sb)
        self.assertEqual([r['prediccion'] for r in a],[r['prediccion'] for r in b])
        self.assertNotEqual([r['real'] for r in a],[r['real'] for r in b])

    def test_reportes_integrales_desde_control_historico_sin_entrenamiento(self):
        # Fixture de software: referencia histórica copiada como controles numéricos
        # idénticos, sólo en memoria/tmp. Nunca se publica como evaluación de bloques.
        original=comun.leer_csv(comun.RAIZ/'registro/t03/predicciones_oof_referencias_media_mun__resp_grupo.csv')[1]
        nombres=[runner.REFERENCIA]+[p['candidato'] for p in self.c['principal']['procedimientos']]
        rows=[dict(r,candidato=n,version=v3.VERSION) for n in nombres for r in original]
        calidad={r['id_parcela']:r for r in comun.leer_csv(comun.RAIZ/'registro/t07/calidad_parcelas.csv')[1]}
        tabla={k[0]:v for k,v in self.e['tabla'].items()}
        real_check=runner.subprocess.check_output
        def git_limpio(cmd,**kw):
            return '' if cmd[:2]==['git','status'] else real_check(cmd,**kw)
        def contexto_control(e,procedimientos,esc,rep,fold,emitir,**kw):
            # Dobles de prueba para orquestación: ningún fit ni nueva predicción.
            sel=[];estados=[]
            for proc in procedimientos:
                for lam in [None]+[o['lambda_reg'] for o in proc['opciones']]:
                    for _ in range(4):emitir(dict(estado='correcto',etapa='interna',lambda_reg=lam,fixture=True))
                s=dict(candidato=proc['candidato'],escenario=esc,repeticion=rep,particion=fold,
                    version=v3.VERSION,nombre_opcion='referencia_sola',referencia_sola=True,lambda_reg=None)
                sel.append(s);kw['al_seleccionar'](s)
            for nombre in nombres:
                emitir(dict(estado='correcto',etapa='externa',lambda_reg=None,fixture=True))
                estado=dict(candidato=nombre,fixture='control_historico_sin_ajuste')
                estados.append(estado);kw['al_estado'](estado)
            rr=[r for r in rows if r['escenario']==esc and int(r['repeticion'])==rep and int(r['particion'])==fold]
            return rr,sel,estados
        with tempfile.TemporaryDirectory() as d:
            destino=Path(d)/'flujo_control'
            with patch.object(runner,'ejecutar_contexto',side_effect=contexto_control) as call, \
                 patch.object(runner.subprocess,'check_output',side_effect=git_limpio), \
                 patch.object(contrato,'preflight',return_value=self.pre):
                manifest=runner.ejecutar(comun.RAIZ,destino,'completa',confirmar_completa=True)
            self.assertEqual(call.call_count,50)
            self.assertEqual(manifest['contadores']['ajustes_internos'],13600)
            self.assertEqual(manifest['contadores']['Ridge_internos'],12000)
            m=manifest['reportes']
            self.assertEqual((m['metricas_resumen'],m['metricas_por_repeticion'],m['contrastes']),(36,180,72))
            contrasts=comun.leer_csv(destino/'contrastes.csv')[1]
            self.assertTrue(all(float(r['dMAE'])==0 and r['elegible_para_promocion_principal']=='False' for r in contrasts))
            resumen=comun.leer_csv(destino/'metricas_resumen.csv')[1]
            a=next(r for r in resumen if r['candidato']==runner.REFERENCIA and r['escenario']=='A' and r['subconjunto']=='sin_respaldo')
            self.assertAlmostEqual(float(a['MAE_por_parcela']),.32048971038707885,places=12)
            before=set(destino.iterdir())
            with self.assertRaises(ValueError):reportes.producir(rows[:-1],self.e['contextos'],self.c,calidad,tabla,destino)
            self.assertEqual(before,set(destino.iterdir()))


if __name__=='__main__':unittest.main()
