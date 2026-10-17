"""Conexión E2: datos reales congelados; perturbaciones sólo en copias de prueba."""
import ast
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
from scripts import t15_e2_ejecutar as run
from scripts import t15_e2_reportes as reports
from scripts.t15_e2_auditar_evaluacion import AuditorEvaluacionE2
from scripts.t15_e1_auditar import sha
from scripts.evaluacion_comun_contrato import leer_csv

ROOT=Path(__file__).resolve().parents[1]


class IntegracionE2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg,cls.auth,cls.data=run.cargar(ROOT)
        cls.temp=tempfile.TemporaryDirectory();cls.folder=Path(cls.temp.name)
        cls.pilot=cls.folder/'pilot'
        cls.manifest=run.ejecutar(ROOT,cls.pilot,'prueba')
        cls.audit=AuditorEvaluacionE2(ROOT).audit_evaluacion(cls.pilot,cls.folder/'audit.json')

    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()

    def test_auth_separate_previous_untouched(self):
        self.assertEqual(sha(ROOT/run.REGISTRO),run.REGISTRO_SHA)
        self.assertFalse(self.cfg['evaluacion_completa_autorizada']);self.assertTrue(self.auth['evaluacion_completa_autorizada'])
        self.assertFalse(self.auth['predicciones_finales59_autorizadas'])

    def test_exact_partial_counts(self):
        self.assertEqual(self.manifest['contadores']['ajustes_internos'],216)
        self.assertEqual(self.manifest['contadores']['Ridge_internos'],192)
        self.assertEqual(self.manifest['contadores']['ajustes_externos'],6)
        self.assertEqual(self.audit['trazas'],222);self.assertEqual(self.audit['ajustes_externos'],6)
        self.assertFalse(self.audit['evaluacion_completa'])

    def test_partial_has_no_global_performance_reports(self):
        for name in ['metricas_resumen.csv','contrastes.csv','decision_E2.json']:
            self.assertFalse((self.pilot/name).exists())

    def test_only_held_out_known_rows(self):
        rows=leer_csv(self.pilot/'oof_parcial_prueba.csv')[1]
        self.assertFalse(set(r['ID_POLIGONO'] for r in rows)&self.data['entradas']['reservados'])
        self.assertEqual({r['candidato'] for r in rows},{reports.NOMBRES[k] for k in ['E2','E12','E2Q']})

    def test_existing_destination_kept(self):
        with self.assertRaises(ValueError):run.ejecutar(ROOT,self.pilot,'prueba')
        self.assertTrue((self.pilot/'manifest.json').exists())

    def test_full_requires_confirmation(self):
        with self.assertRaises(ValueError):run.ejecutar(ROOT,self.folder/'no','completa')

    def test_full_requires_proof(self):
        with self.assertRaises(ValueError):run.ejecutar(ROOT,self.folder/'no','completa',confirmar_completa=True)
        self.assertFalse((self.folder/'no').exists())

    def test_gate_rejects_different_code(self):
        gate=dict(schema='E2_integracion_verificada_v1',resultado='aprobado',registro_sha256=sha(ROOT/run.REGISTRO),
                  autorizacion_sha256=sha(ROOT/run.AUTORIZACION),codigo_sha256={})
        path=self.folder/'badgate.json';path.write_text(json.dumps(gate))
        with self.assertRaises(ValueError):run.comprobar_puerta(ROOT,path)

    def test_report_contract_exact(self):
        r=reports.contrato_reportes(self.cfg)
        self.assertEqual(len(r['principal']['procedimientos']),5)
        self.assertEqual(len(r['principal']['contrastes_planificados']),7)
        self.assertEqual(sum(p['tipo']=='promocion' for p in r['principal']['contrastes_planificados']),2)

    def test_held_out_target_cannot_change_selection(self):
        changed=copy.deepcopy(self.data)
        q=run.entrada.contexto(self.data,'A',1,0)[2]
        for row in changed['entradas']['tabla'].values():
            if row['id_parcela'] in q.index:row['rendimiento_t_ha']='987654321'
        a=run.entrada.contexto(self.data,'A',1,0);b=run.entrada.contexto(changed,'A',1,0)
        import pandas as pd
        pd.testing.assert_frame_equal(a[0],b[0]);pd.testing.assert_series_equal(a[1],b[1]);pd.testing.assert_frame_equal(a[2],b[2])

    def test_all_menu_options_shared_and_reference_present(self):
        selections=[json.loads(x) for x in (self.pilot/'selecciones.jsonl').read_text().splitlines()]
        for r in selections:
            self.assertEqual(len(r['puntuaciones']),9)
            self.assertEqual(sum(s['referencia_sola'] for s in r['puntuaciones']),1)

    def test_auditor_no_producer_or_sklearn(self):
        tree=ast.parse((ROOT/'scripts/t15_e2_auditar_evaluacion.py').read_text())
        modules=[n.module for n in ast.walk(tree) if isinstance(n,ast.ImportFrom)]
        self.assertFalse(any(m and ('sklearn' in m or m.endswith(('t15_e2_ejecutar','t15_e2_reportes','t15_e2_modelo'))) for m in modules))

    def test_tampered_results_rejected(self):
        import shutil
        bad=self.folder/'bad';shutil.copytree(self.pilot,bad)
        path=bad/'oof_parcial_prueba.csv';path.write_text(path.read_text().replace('AGC_','MAL_',1))
        with self.assertRaises(ValueError):AuditorEvaluacionE2(ROOT).audit_evaluacion(bad,self.folder/'bad_audit.json')

    def test_reports_and_guard_from_controlled_copy_of_real_oof(self):
        # These aliases test report plumbing only; never count them as E2 evaluation.
        previous=self.data['fuentes_reutilizadas'];rows=list(previous)
        source=[r for r in previous if r['candidato']==reports.REF]
        for k in ['E2','E12','E2Q']:
            rows.extend([dict(r,candidato=reports.NOMBRES[k]) for r in source])
        table={k[0]:r for k,r in self.data['entradas']['tabla'].items()}
        quality={r['id_parcela']:r for r in leer_csv(ROOT/'registro/t07/calidad_parcelas.csv')[1]}
        out=self.folder/'reports';out.mkdir()
        result=reports.producir(rows,self.data['entradas']['contextos'],self.cfg,quality,table,out)
        AuditorEvaluacionE2(ROOT).auditar_reportes(out,rows,self.cfg)
        self.assertEqual(result['metricas_resumen'],24);self.assertEqual(result['contrastes_guardia'],28)
        self.assertEqual(result['decision']['procedimiento_recomendado_por_regla'],reports.REF)
        self.assertFalse(result['decision']['E2Q_promovible'])
        contrasts=leer_csv(out/'contrastes_E2_con_guardia.csv')[1]
        self.assertTrue(all(r['elegible_E2_con_guardia']=='False' for r in contrasts))

    def test_numeric_inner_tamper_rejected_after_rehash(self):
        import shutil
        bad=self.folder/'bad_numeric';shutil.copytree(self.pilot,bad)
        path=bad/'trazas_ajustes.jsonl';lines=path.read_text().splitlines()
        row=json.loads(lines[0]);row['MAE']+=.2;lines[0]=json.dumps(row)
        path.write_text('\n'.join(lines)+'\n')
        m=json.loads((bad/'manifest.json').read_text());m['archivos_sha256'][path.name]=sha(path)
        (bad/'manifest.json').write_text(json.dumps(m))
        with self.assertRaisesRegex(ValueError,'MAE interno'):
            AuditorEvaluacionE2(ROOT).audit_evaluacion(bad,self.folder/'bad_numeric_audit.json')

    def test_numeric_h3_tamper_rejected_after_rehash(self):
        import shutil
        bad=self.folder/'bad_h3';shutil.copytree(self.pilot,bad)
        path=bad/'estados_modelos.jsonl';lines=path.read_text().splitlines()
        row=json.loads(lines[0]);row['consulta'][0]['correccion']+=.1;row['consulta'][0]['prediccion']+=.1
        lines[0]=json.dumps(row);path.write_text('\n'.join(lines)+'\n')
        m=json.loads((bad/'manifest.json').read_text());m['archivos_sha256'][path.name]=sha(path)
        (bad/'manifest.json').write_text(json.dumps(m))
        with self.assertRaisesRegex(ValueError,'Predicción independiente E2'):
            AuditorEvaluacionE2(ROOT).audit_evaluacion(bad,self.folder/'bad_h3_audit.json')

    def test_diagnostic_cannot_promote_even_on_numeric_pass(self):
        r=dict(candidato=reports.NOMBRES['E2Q'],frente_a=reports.REF,escenario='A',subconjunto='sin_respaldo',
               tipo_contraste='promocion',cumple_regla_T03=True,IC95_celdas_MAE=[-.1,-.02])
        with patch.object(reports,'intervalo_familiar',return_value=[-.11,-.01]):
            self.assertFalse(reports.aplicar_guardia([r],[],{})[0]['elegible_E2_con_guardia'])

    def test_family_can_veto_usual_interval_pass(self):
        r=dict(candidato=reports.NOMBRES['E2'],frente_a=reports.REF,escenario='A',subconjunto='sin_respaldo',
               tipo_contraste='promocion',cumple_regla_T03=True,IC95_celdas_MAE=[-.1,-.001])
        with patch.object(reports,'intervalo_familiar',return_value=[-.11,.001]):
            self.assertFalse(reports.aplicar_guardia([r],[],{})[0]['elegible_E2_con_guardia'])

    def test_sensitivity_cannot_replace_main_decision(self):
        r=dict(candidato=reports.NOMBRES['E2'],frente_a=reports.REF,escenario='B',subconjunto='sin_respaldo',
               tipo_contraste='promocion',cumple_regla_T03=True,IC95_celdas_MAE=[-.1,-.02])
        with patch.object(reports,'intervalo_familiar',return_value=[-.11,-.01]):
            self.assertFalse(reports.aplicar_guardia([r],[],{})[0]['elegible_E2_con_guardia'])


if __name__=='__main__':unittest.main()
