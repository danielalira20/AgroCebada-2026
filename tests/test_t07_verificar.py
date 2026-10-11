"""El contraste debe detectar errores aunque se regeneren las huellas de salida."""
import json
from pathlib import Path
import shutil
import unittest

import tests.test_t07_integrar as fixture
from scripts.t07_fuentes import leer_csv, guardar_csv, sha
from scripts.t07_integrar import integrar
from scripts.t07_verificar import verificar
from scripts.t07_ventanas import agregar


class Verificacion(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixture.Integracion.setUpClass()
        cls.root=fixture.Integracion.root
        cls.clima=fixture.Integracion.clima
        cls.ref=fixture.Integracion.rev
        cls.original=cls.root/'original'
        integrar(cls.ref,cls.original,cls.clima,cls.ref,raiz=cls.root)

    @classmethod
    def tearDownClass(cls): fixture.Integracion.tearDownClass()

    def copia(self,nombre):
        out=self.root/nombre;shutil.copytree(self.original,out);return out

    def editar(self,out,nombre,transformar):
        p=out/nombre;campos,filas=leer_csv(p)
        transformar(filas);guardar_csv(p,campos,filas)
        m=json.loads((out/'manifest.json').read_text());m['archivos_sha256'][nombre]=sha(p)
        (out/'manifest.json').write_text(json.dumps(m))

    def test_verifica_entrega_real_con_1182_contrastes(self):
        r=verificar(self.original,self.clima,self.root)
        self.assertEqual((r['contrastes_climaticos'],r['valores_satelitales_literales']), (1182,8668))
        self.assertEqual(r['resultado'],'verificado')

    def test_error_temperatura_no_se_oculta_con_huellas_nuevas(self):
        out=self.copia('error_temp')
        def ancho(f):f[0]['tmin_media_c_abr_oct']='10'
        def largo(f):f[0]['tmin_media_c']='10'
        self.editar(out,'clima_variables.csv',ancho);self.editar(out,'tabla_comun.csv',ancho)
        self.editar(out,'clima_ventanas.csv',largo)
        with self.assertRaisesRegex(ValueError,'Decimal falló'):verificar(out,self.clima,self.root)

    def test_error_satelite_no_se_oculta_con_huella_nueva(self):
        out=self.copia('error_sat')
        self.editar(out,'tabla_comun.csv',lambda f:f[0].update(pl_ndvi_max_abr_oct='0.123456'))
        with self.assertRaisesRegex(ValueError,'satelital alterado'):verificar(out,self.clima,self.root)

    def test_error_etiqueta_no_se_oculta_con_huella_nueva(self):
        out=self.copia('error_etiqueta')
        self.editar(out,'tabla_comun.csv',lambda f:f[0].update(rendimiento_t_ha='123'))
        with self.assertRaisesRegex(ValueError,'Etiqueta o metadato'):verificar(out,self.clima,self.root)

    def test_no_aceptar_id_como_predictor(self):
        out=self.copia('error_rol')
        def cambiar(f):
            for r in f:
                if r['archivo']=='tabla_comun.csv' and r['columna']=='id_parcela':r['funcion']='predictor_candidato'
        self.editar(out,'diccionario_columnas.csv',cambiar)
        with self.assertRaisesRegex(ValueError,'no debe ser predictor'):verificar(out,self.clima,self.root)

    def test_grupo_conservado_para_referencia_y_evaluacion(self):
        _, filas = leer_csv(self.original/'tabla_comun.csv')
        _, fuente = leer_csv(self.root/'analisis/auditoria_catalogo_y_etiquetas/tablas/catalogo_parcelas.csv')
        self.assertEqual({r['id_parcela']: r['cultivo_origen'] for r in filas},
                         {r['id_parcela']: r['cultivo_origen'] for r in fuente})
        contrato = json.loads((self.original/'contrato_columnas.json').read_text())
        self.assertEqual(contrato['columnas_por_funcion']['referencia_y_evaluacion'], ['cultivo_origen'])
        self.assertNotIn('cultivo_origen', contrato['columnas_por_funcion']['predictor_candidato'])
        self.assertFalse(contrato['grupo_registro']['normalizar_texto_original'])
        self.assertTrue(contrato['grupo_registro']['referencia_aprendida_solo_en_entrenamiento'])

    def test_grupo_no_puede_descartarse_ni_ser_predictor_automatico(self):
        for rol in ('solo_auditoria', 'predictor_candidato'):
            out = self.copia('grupo_'+rol)
            def cambiar(filas):
                for r in filas:
                    if r['archivo']=='tabla_comun.csv' and r['columna']=='cultivo_origen':
                        r['funcion'] = rol
            self.editar(out, 'diccionario_columnas.csv', cambiar)
            with self.assertRaisesRegex(ValueError, 'Grupo de registro debe conservarse'):
                verificar(out, self.clima, self.root)

    def test_area_t10_declarada_no_es_entrada_automatica_t09(self):
        contrato=json.loads((self.original/'contrato_columnas.json').read_text())
        area=contrato['area_t10']
        self.assertEqual(area['candidata']['columna'],'area_ha_origen')
        self.assertEqual(area['candidata']['unidad'],'ha')
        self.assertFalse(area['predictor_automatico_t09'])
        self.assertIn('area_ha_origen',contrato['columnas_por_funcion']['metadato'])
        self.assertNotIn('area_ha_origen',contrato['columnas_por_funcion']['predictor_candidato'])
        self.assertEqual({r['columna'] for r in area['alternativas_solo_auditoria']},
                         {'area_ha_geodesica','area_parcela_6372_m2'})

    def test_area_candidata_alterada_detectada_aun_con_huella(self):
        out=self.copia('area_contrato_alterado')
        p=out/'contrato_columnas.json';c=json.loads(p.read_text())
        c['area_t10']['candidata']['columna']='area_ha_geodesica'
        p.write_text(json.dumps(c),encoding='utf-8')
        m=json.loads((out/'manifest.json').read_text());m['archivos_sha256'][p.name]=sha(p)
        (out/'manifest.json').write_text(json.dumps(m),encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'Contrato del área T10'):
            verificar(out,self.clima,self.root)

    def test_comentario_local_en_script_t02_no_invalida_entrega(self):
        p=self.root/'analisis/auditoria_catalogo_y_etiquetas/scripts/construir_catalogo.py'
        antes=p.read_bytes()
        try:
            p.write_bytes(antes+b'\n# comentario\n')
            self.assertEqual(verificar(self.original,self.clima,self.root)['resultado'],'verificado')
        finally:p.write_bytes(antes)

    def test_procedencia_archivada_alterada_se_detecta(self):
        out=self.copia('error_procedencia')
        p=out/'inventario_fuentes.json';inv=json.loads(p.read_text())
        audit=inv['bloques']['T02']['procedencia_sha256'];audit[next(iter(audit))]='0'*64
        p.write_text(json.dumps(inv))
        m=json.loads((out/'manifest.json').read_text());m['archivos_sha256'][p.name]=sha(p)
        (out/'manifest.json').write_text(json.dumps(m))
        with self.assertRaisesRegex(ValueError,'Procedencia T02 distinta'):verificar(out,self.clima,self.root)

    def test_sensibilidad_climatica_desde_fuentes_reales(self):
        _, q = leer_csv(self.original/'calidad_ventanas.csv')
        lluvia = [r for r in q if r['ventana']=='abr_oct' and r['variable']=='PREC']
        self.assertEqual(sum(int(r['celdas_lluvia_tocadas_t02'])>1 for r in lluvia), 31)
        self.assertEqual(sorted(r['id_parcela'] for r in lluvia if r['centroide_dentro_parcela']=='False'),
                         ['AGC_078','AGC_152','AGC_182'])
        self.assertTrue(all(r['estado_comparacion_centroide']=='comparable' for r in q))
        self.assertEqual(verificar(self.original,self.clima,self.root)['contrastes_centroide'],1182)

    def test_sensibilidad_alterada_detectada_aun_con_huella_nueva(self):
        for campo, valor, mensaje in [('celdas_lluvia_tocadas_t02','99','Conteo de celdas'),
                ('centroide_dentro_parcela','False','Bandera de centroide'),
                ('valor_centroide_ventana','999','Agregado del centroide'),
                ('diferencia_media_menos_centroide','999','Diferencia con centroide'),
                ('estado_comparacion_centroide','centroide_incompleto','Estado de sensibilidad')]:
            out=self.copia('sensibilidad_'+campo)
            self.editar(out,'calidad_ventanas.csv',lambda f:f[0].update({campo:valor}))
            with self.subTest(campo=campo), self.assertRaisesRegex(ValueError,mensaje):
                verificar(out,self.clima,self.root)

    def test_historia_real_fuera_de_ventanas_no_afecta_ningun_resumen(self):
        _,filas=leer_csv(self.clima/'clima_parcela_mes.csv')
        indice={(r['id_parcela'],r['periodo'],r['variable']):r for r in filas}
        ids=sorted({r['id_parcela'] for r in filas})
        antes=agregar(indice,ids)
        modificados=0
        for r in filas:
            if not '2025-04'<=r['periodo']<='2025-10':
                r['media_ponderada']='1000000';modificados+=1
        self.assertEqual(modificados,24231)
        self.assertEqual(agregar(indice,ids),antes)


if __name__=='__main__':unittest.main()
