"""Integridad de fase0 y rechazos concretos; no entrena ni inventa entregas."""
import copy
import hashlib
import math
import os
from pathlib import Path
import tempfile
import unittest

from scripts import diagnostico_fase0 as d
from scripts.diagnostico_fuentes import json_estricto,ruta_segura,preparar


class DiagnosticoFase0(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.design,cls.manifest=d.configuracion(d.RAIZ)
        cls.temp=tempfile.TemporaryDirectory()
        if os.environ.get('AGRO_DIAG_FUENTES'):cls.root=Path(os.environ['AGRO_DIAG_FUENTES'])
        else:
            cls.root=Path(cls.temp.name)/'entradas';preparar(d.RAIZ,cls.manifest,cls.root)
        cls.table,cls.known,cls.reserved,cls.qc,cls.parts=d.cargar_base(cls.root)
        cls.contexts=d.contextos(cls.table,cls.known,cls.parts,cls.root)
        cls.raw=d.csv_completo(cls.root/'base'/d.OOF_BASE)
        cls.base,_=d.normalizar(cls.raw,'T08','base',d.OOF_BASE,cls.table,cls.contexts)

    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()

    def normalizar(self,rows):return d.normalizar(rows,'T08','base',d.OOF_BASE,self.table,self.contexts)

    def test_censo_y_unidad_real(self):
        self.assertEqual((len(self.table),len(self.known),len(self.reserved)),(197,138,59))
        self.assertFalse(self.known&self.reserved)
        self.assertTrue(all(self.table[i]['rendimiento_t_ha']=='' for i in self.reserved))

    def test_referencia_y_mascaras(self):
        self.assertEqual(len(self.base),1380)
        for esc,n in [('A',675),('B',659)]:self.assertEqual(sum(r['escenario']==esc and r['sin_respaldo'] for r in self.base),n)
        self.assertEqual(sum(k[0]=='C' for k in self.contexts),138)

    def test_snapshot_inventario_completo(self):
        inventory=d.validar_fuentes(self.root,self.manifest)
        self.assertEqual(len(inventory),154)
        self.assertTrue(all(not row['metodo_comun_acreditado'] for row in inventory))
        empty=[r for r in inventory if r['filas_csv']==0]
        self.assertEqual([r['archivo'] for r in empty],['registro/t10/control_revuelto_t10.csv'])

    def test_vacio_permitido_solo_inventario(self):
        p=self.root/'t10/registro/t10/control_revuelto_t10.csv'
        self.assertEqual(d.csv_completo(p,permitir_vacio=True),[])
        with self.assertRaisesRegex(ValueError,'vacío obligatorio'):d.csv_completo(p)

    def test_vacio_no_oculta_control_que_si_se_activa(self):
        d.validar_control_inactivo([{'candidata_a_promover':'False'}])
        with self.assertRaisesRegex(ValueError,'lo activa'):d.validar_control_inactivo([{'candidata_a_promover':'True'}])
        with self.assertRaisesRegex(ValueError,'no declarada'):d.validar_control_inactivo([{'candidata_a_promover':''}])

    def test_d020_no_imputa_ni_elimina(self):
        missing=[r for r in self.table.values() if r['pendiente_media_t10_grados']=='']
        self.assertEqual(len(missing),2)
        self.assertTrue(all(r['id_parcela'] in self.known|self.reserved for r in missing))

    def test_duplicado_y_fila_perdida_rechazados(self):
        for rows in [self.raw+[self.raw[0]],self.raw[:-1]]:
            with self.assertRaises(ValueError):self.normalizar(rows)

    def test_etiqueta_un_bit_diferente_rechazada(self):
        rows=copy.deepcopy(self.raw);rows[0]['real']=repr(math.nextafter(float(rows[0]['real']),math.inf))
        with self.assertRaisesRegex(ValueError,'etiqueta'):self.normalizar(rows)

    def test_objetivo_reservado_no_entra_en_oof(self):
        rows=copy.deepcopy(self.raw);rows[0]['ID_POLIGONO']=min(self.reserved)
        with self.assertRaisesRegex(ValueError,'reservada'):self.normalizar(rows)

    def test_contexto_fuente_o_prediccion_referencia_alterados(self):
        for col,val in [('particion','9'),('fuente','global'),('prediccion','100'),('prediccion','nan'),('version',''),('candidato','')]:
            rows=copy.deepcopy(self.raw);rows[0][col]=val
            with self.subTest(col=col),self.assertRaises(ValueError):self.normalizar(rows)

    def test_versiones_mezcladas_no_se_particionan_en_silencio(self):
        rows=copy.deepcopy(self.raw);rows[0]['version']='otra'
        with self.assertRaisesRegex(ValueError,'Versiones mezcladas'):self.normalizar(rows)

    def test_alias_id_incompatible_no_se_corrige_en_silencio(self):
        rows=copy.deepcopy(self.raw);rows[0]['id_parcela']='otra_parcela'
        with self.assertRaisesRegex(ValueError,'Alias'):self.normalizar(rows)

    def test_seleccion_determinista_por_id_no_por_orden_archivo(self):
        a,b=d.seleccionar_casos(self.base,self.table,self.qc)
        c,e=d.seleccionar_casos(self.base[::-1],self.table,self.qc)
        self.assertEqual((a,b),(c,e));self.assertEqual(len(a),10)
        self.assertEqual(len({r['control'] for r in b}),10)
        self.assertFalse({r['control'] for r in b}&{r['id_parcela'] for r in a})

    def test_controles_no_consultan_errores_ni_rendimiento(self):
        cases,controls=d.seleccionar_casos(self.base,self.table,self.qc)
        other=copy.deepcopy(self.base)
        for r in other:r['real']=9999.;r['prediccion']=-9999.
        table=copy.deepcopy(self.table)
        for r in table.values():r['rendimiento_t_ha']='9999'
        self.assertEqual(controls,d.seleccionar_controles(cases,other,table,self.qc))

    def test_control_sin_municipio_comparable_queda_ausente(self):
        cases,_=d.seleccionar_casos(self.base,self.table,self.qc);one=cases[:1];pid=one[0]['id_parcela']
        b=[r for r in self.base if r['id_parcela']==pid]
        out=d.seleccionar_controles(one,b,self.table,self.qc)
        self.assertEqual(out[0]['control'],'');self.assertIn('sin_control',out[0]['estado'])

    def test_promediar_predicciones_no_cancela_ranking_de_errores(self):
        # Ejemplo unitario aislado, nunca escrito como una entrega del reto.
        pid=min(self.known)
        base=[dict(id_parcela=i,escenario='A',sin_respaldo=True,prediccion=float(self.table[i]['rendimiento_t_ha']),real=float(self.table[i]['rendimiento_t_ha'])) for i in sorted(self.known)]
        base=[r for r in base if r['id_parcela']!=pid];y=float(self.table[pid]['rendimiento_t_ha'])
        base+=[dict(id_parcela=pid,escenario='A',sin_respaldo=True,prediccion=y+5,real=y),dict(id_parcela=pid,escenario='A',sin_respaldo=True,prediccion=y-5,real=y)]
        cases,_=d.seleccionar_casos(base,self.table,self.qc)
        self.assertEqual(cases[0]['id_parcela'],pid);self.assertEqual(cases[0]['criterio_media_error_absoluto'],5)

    def test_disponibilidad_no_se_infiere_de_observacion(self):
        rows=d.temporal(self.root,self.table)
        self.assertEqual(len(rows),60)
        self.assertTrue(all(r['disponible_al_corte']=='no_acreditado' for r in rows))
        self.assertEqual(sum(r['unidad_fisica_pendiente'] for r in rows),4)

    def test_oof_no_demuestra_metodo_comun(self):
        _,rows=self.normalizar(self.raw)
        self.assertTrue(rows[0]['compatibilidad_de_datos'])
        self.assertFalse(rows[0]['metodos_equivalentes']);self.assertFalse(rows[0]['modelo_nuevo_acreditado'])

    def test_json_duplicado_nan_csv_no_rectangular_rechazados(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'mal.json'
            for content in ['{"a":1,"a":2}','{"a":NaN}']:
                p.write_text(content)
                with self.assertRaises(ValueError):json_estricto(p)
            p=Path(tmp)/'mal.csv'
            for content in ['a,a\n1,2\n','a,b\n1\n','a,b\n1,2,3\n']:
                p.write_text(content)
                with self.assertRaises(ValueError):d.csv_completo(p)

    def test_paths_y_symlinks_fuera_de_root_rechazados(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'root';root.mkdir()
            with self.assertRaises(ValueError):ruta_segura(root,'../fuera')
            (root/'link').symlink_to(Path(tmp))
            with self.assertRaises(ValueError):ruta_segura(root,'link/dato.csv')

    def test_fallo_integridad_no_publica_salida_parcial(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'fuentes';src=self.manifest['fuentes']['base']['archivos'][0]
            f=root/'base'/src['ruta'];f.parent.mkdir(parents=True);f.write_text('alterado')
            target=Path(tmp)/'resultado'
            with self.assertRaisesRegex(ValueError,'Fuente distinta'):d.ejecutar(root,self.design,self.manifest,target)
            self.assertFalse(target.exists())

    def test_destino_existente_no_se_sobreescribe(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError,'Salida nueva'):d.ejecutar(self.root,self.design,self.manifest,Path(tmp))

    def test_disenos_y_fuentes_fijados(self):
        self.assertEqual(hashlib.sha256((d.RAIZ/d.DISENO).read_bytes()).hexdigest(),d.DISENO_SHA)
        self.assertEqual(hashlib.sha256((d.RAIZ/d.FUENTES).read_bytes()).hexdigest(),d.FUENTES_SHA)
        self.assertFalse(self.design['antecedentes']['analisis_ciego'])


if __name__=='__main__':unittest.main()
