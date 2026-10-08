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
