"""Integración real en un Git temporal aislado; no publica ni aprueba entregas."""
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from scripts.t07_fuentes import leer_csv, sha
from scripts.t07_integrar import integrar, comprobar_protocolo, T06_ARCHIVOS, CODIGO
from scripts.t07_preparar import T02, T02_ARCHIVOS, T04_ARCHIVOS

RAIZ = Path(__file__).resolve().parents[1]


class Integracion(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.tmp.name)
        fuentes = [f'{T02}/{n}' for n in T02_ARCHIVOS] + list(T06_ARCHIVOS)
        fuentes += ['docs/T03_protocolo_evaluacion.md'] + [f'scripts/{n}' for n in CODIGO]
        fuentes += [f'registro/t04/{n}' for n in T04_ARCHIVOS]
        from scripts.t07_relieve import ARCHIVOS, AUXILIARES
        fuentes += list(ARCHIVOS) + list(AUXILIARES) + ['registro/decisiones.csv']
        for n in fuentes:
            p = cls.root / n; p.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(RAIZ/n, p)
        cls.clima = cls.root/'registro/t04'
        # Se construye deliberadamente una referencia v1 para comprobar también su migración
        # a v2. La fuente real ya puede ser v2: no mezclar sus tres huellas separadas con
        # las cinco huellas conjuntas de esta fixture. El repositorio real no se modifica.
        c = json.loads((cls.clima/'conciliacion_t02.json').read_text())
        c.pop('procedencia_t02_sha256', None)
        c['schema_referencia_t02'] = 't04_referencia_t02_v1'
        c['archivos_t02_sha256'] = {n: sha(cls.root/T02/n) for n in T02_ARCHIVOS}
        (cls.clima/'conciliacion_t02.json').write_text(json.dumps(c))
        m = json.loads((cls.clima/'manifest.json').read_text())
        m['archivos_sha256']['conciliacion_t02.json'] = sha(cls.clima/'conciliacion_t02.json')
        (cls.clima/'manifest.json').write_text(json.dumps(m))
        def g(*args): return subprocess.check_output(['git',*args],cwd=cls.root,stderr=subprocess.PIPE)
        g('init','-q');g('config','user.name','Prueba T07');g('config','user.email','prueba@example.invalid')
        g('add','.');g('commit','-qm','fixture aislada de fuentes reales')
        cls.rev = g('rev-parse','HEAD').decode().strip()
        cls.origen = dict(schema='t07_copia_t04_v1', revision_git=cls.rev, prefijo_git='registro/t04',
                          estado_revision_declarado='aceptada', archivos_sha256={n:sha(cls.clima/n) for n in T04_ARCHIVOS})
        cls.estado('aceptada')

    @classmethod
    def estado(cls, estado):
        o = dict(cls.origen, estado_revision_declarado=estado)
        (cls.clima/'origen_git.json').write_text(json.dumps(o))

    @classmethod
    def tearDownClass(cls): cls.tmp.cleanup()

    def ejecutar(self, nombre, revision=False, clima=True):
        return integrar(self.rev, self.root/nombre, self.clima if clima else None,
                        self.rev if clima else None, revision, self.root)

    def test_union_completa_reproducible_diccionario_unico(self):
        a=self.root/'a';b=self.root/'b'
        c=self.ejecutar('a');self.ejecutar('b')
        self.assertEqual((c['parcelas'],c['columnas_tabla_comun'],c['etiquetas_originales'],c['etiquetas_ausentes']), (197,58,138,59))
        self.assertEqual(c['resumenes_climaticos_completos'],1182)
        self.assertEqual({p.name:sha(p) for p in a.iterdir()}, {p.name:sha(p) for p in b.iterdir()})
        _, d=leer_csv(a/'diccionario_columnas.csv')
        self.assertEqual(len(d),109)
        self.assertEqual(len({(r['archivo'],r['columna']) for r in d}),109)
        ident=[r for r in d if r['archivo']=='tabla_comun.csv' and r['columna']=='id_parcela']
        self.assertEqual(len(ident),1)
        self.assertTrue(all(r['funcion']=='metadato' for r in ident))
        roles=json.loads((a/'contrato_columnas.json').read_text())['columnas_por_funcion']
        self.assertNotIn('rendimiento_t_ha',roles['predictor_candidato'])
        with self.assertRaisesRegex(ValueError,'ya existe'):self.ejecutar('a')

    def test_revision_pendiente_no_se_publica_fuera_de_reports(self):
        self.estado('en_revision')
        try:
            with self.assertRaisesRegex(ValueError,'sólo puede'):self.ejecutar('registro/publicar',revision=True)
            with self.assertRaisesRegex(ValueError,'pendiente de aceptación'):self.ejecutar('reports/sin_bandera')
            self.assertFalse((self.root/'registro/publicar').exists())
            self.assertFalse((self.root/'reports/sin_bandera').exists())
            c=self.ejecutar('reports/borrador',revision=True)
            m=json.loads((self.root/'reports/borrador/manifest.json').read_text())
            self.assertFalse(m['clima_aceptado']); self.assertFalse(m['cierre_t07'])
            self.assertEqual(c['estado_entrega'],'borrador_local_para_revision')
        finally:self.estado('aceptada')

    def test_sin_clima_no_lee_entrada_ni_genera_filas_climaticas(self):
        p=self.clima/'origen_git.json';original=p.read_bytes()
        try:
            p.unlink();c=self.ejecutar('sat',clima=False)
            self.assertEqual(c['columnas_tabla_comun'],52)
            self.assertFalse((self.root/'sat/clima_variables.csv').exists())
            m=json.loads((self.root/'sat/inventario_fuentes.json').read_text())
            self.assertFalse(m['bloques']['T04']['valores_generados'])
        finally:p.write_bytes(original)

    def test_fuente_satelital_alterada_no_publica(self):
        p=self.root/T06_ARCHIVOS[0];original=p.read_bytes()
        try:
            p.write_bytes(original+b'alteracion\n')
            with self.assertRaisesRegex(ValueError,'Fuente local distinta'):self.ejecutar('alterada')
            self.assertFalse((self.root/'alterada').exists())
        finally:p.write_bytes(original)

    def test_copia_climatica_alterada_no_publica(self):
        p=self.clima/'clima_parcela_mes.csv';original=p.read_bytes()
        try:
            p.write_bytes(original+b'alteracion\n')
            with self.assertRaisesRegex(ValueError,'Copia T04 alterada'):self.ejecutar('clima_alterada')
            self.assertFalse((self.root/'clima_alterada').exists())
        finally:p.write_bytes(original)

    def test_corte_ventana_nuevos_requieren_contrato(self):
        t=(RAIZ/'docs/T03_protocolo_evaluacion.md').read_text()
        comprobar_protocolo(t)
        for x in [t.replace('hasta el **31 de octubre de 2025**','hasta el **30 de noviembre de 2025**'),
                  t.replace('1 de junio–31 de octubre','1 de julio–31 de octubre')]:
            with self.assertRaisesRegex(ValueError,'Corte/ventanas'):comprobar_protocolo(x)

    def test_salidas_protegidas(self):
        for n in ['data/raw/error','registro/t04/error']:
            with self.assertRaisesRegex(ValueError,'Salida protegida'):self.ejecutar(n)

    def test_comentario_t02_en_nueva_base_no_reextrae_clima(self):
        anterior=self.root/'antes_comentario'
        integrar(self.rev,anterior,self.clima,self.rev,raiz=self.root)
        nombres=['scripts/construir_catalogo.py','scripts/diagnosticar_soporte.py']
        originales={n:(self.root/T02/n).read_bytes() for n in nombres}
        def g(*a):return subprocess.check_output(['git',*a],cwd=self.root,stderr=subprocess.PIPE)
        try:
            for n,v in originales.items():(self.root/T02/n).write_bytes(v+b'\n# comentario sin efecto en datos\n')
            g('add',*[str(Path(T02)/n) for n in nombres]);g('commit','-qm','comentario T02 en nueva base')
            nueva=g('rev-parse','HEAD').decode().strip()
            posterior=self.root/'despues_comentario'
            integrar(nueva,posterior,self.clima,self.rev,raiz=self.root)
            self.assertEqual((anterior/'tabla_comun.csv').read_bytes(),(posterior/'tabla_comun.csv').read_bytes())
            inv=json.loads((posterior/'inventario_fuentes.json').read_text())['bloques']['T02']
            self.assertEqual(len(inv['archivos_sha256']),2);self.assertEqual(len(inv['procedencia_sha256']),3)
            from scripts.t07_verificar import verificar
            self.assertEqual(verificar(posterior,self.clima,self.root)['contrastes_climaticos'],1182)
        finally:
            for n,v in originales.items():(self.root/T02/n).write_bytes(v)

    def test_entrega_v2_se_integra_con_el_mismo_resultado(self):
        nombres=['conciliacion_t02.json','manifest.json','origen_git.json']
        originales={n:(self.clima/n).read_bytes() for n in nombres}
        anterior=self.root/'v1_antes';integrar(self.rev,anterior,self.clima,self.rev,raiz=self.root)
        try:
            from scripts.t02_contrato import separar_huellas
            c=json.loads(originales['conciliacion_t02.json'])
            datos,audit=separar_huellas(c['archivos_t02_sha256'])
            c['archivos_t02_sha256']=datos;c['procedencia_t02_sha256']=audit
            c['schema_referencia_t02']='t04_referencia_t02_v2'
            (self.clima/'conciliacion_t02.json').write_text(json.dumps(c))
            m=json.loads(originales['manifest.json']);m['archivos_sha256']['conciliacion_t02.json']=sha(self.clima/'conciliacion_t02.json')
            (self.clima/'manifest.json').write_text(json.dumps(m))
            def g(*a):return subprocess.check_output(['git',*a],cwd=self.root,stderr=subprocess.PIPE)
            g('add','registro/t04/conciliacion_t02.json','registro/t04/manifest.json');g('commit','-qm','contrato v2 temporal')
            nueva=g('rev-parse','HEAD').decode().strip()
            o=dict(self.origen,revision_git=nueva,archivos_sha256={n:sha(self.clima/n) for n in T04_ARCHIVOS})
            (self.clima/'origen_git.json').write_text(json.dumps(o))
            posterior=self.root/'v2_despues';integrar(self.rev,posterior,self.clima,nueva,raiz=self.root)
            self.assertEqual((anterior/'tabla_comun.csv').read_bytes(),(posterior/'tabla_comun.csv').read_bytes())
            from scripts.t07_verificar import verificar
            self.assertEqual(verificar(posterior,self.clima,self.root)['contrastes_climaticos'],1182)
        finally:
            for n,v in originales.items():(self.clima/n).write_bytes(v)

    def test_integracion_relieve_completa_y_contraste_independiente(self):
        from scripts.t07_verificar import verificar
        a=self.root/'completa_relieve';b=self.root/'completa_relieve_b'
        for destino in (a,b):
            control=integrar(self.rev,destino,self.clima,self.rev,raiz=self.root,relieve=True)
            self.assertEqual(control['columnas_tabla_comun'],60)
            self.assertEqual(control['relieve']['pendiente_t10_ausente'],['AGC_023','AGC_170'])
        self.assertEqual({p.name:sha(p) for p in a.iterdir()},{p.name:sha(p) for p in b.iterdir()})
        self.assertEqual(len(list(a.iterdir())),12)
        _,dic=leer_csv(a/'diccionario_columnas.csv');self.assertEqual(len(dic),135)
        resultado=verificar(a,self.clima,self.root)
        self.assertEqual(resultado['relieve']['medias_recalculadas'],394)
        self.assertEqual(resultado['contrastes_climaticos'],1182)
        self.assertFalse(resultado['cierre_t07'])

    def test_entrega_relieve_corrupta_detectada_aun_con_nueva_huella(self):
        from scripts.t07_verificar import verificar
        from scripts.t07_fuentes import guardar_csv
        a=self.root/'corrupta_relieve'
        integrar(self.rev,a,self.clima,self.rev,raiz=self.root,relieve=True)
        campos,filas=leer_csv(a/'calidad_relieve.csv');filas[0]['cobertura_espacial']='0'
        guardar_csv(a/'calidad_relieve.csv',campos,filas)
        m=json.loads((a/'manifest.json').read_text())
        m['archivos_sha256']['calidad_relieve.csv']=sha(a/'calidad_relieve.csv')
        (a/'manifest.json').write_text(json.dumps(m))
        with self.assertRaisesRegex(ValueError,'calidad alterada'):verificar(a,self.clima,self.root)

    def test_relieve_fuente_alterada_no_publica(self):
        p=self.root/'registro/t05/relieve_parcela.csv';original=p.read_bytes()
        try:
            p.write_bytes(original+b'alteracion\n')
            with self.assertRaisesRegex(ValueError,'Fuente local distinta'):
                integrar(self.rev,self.root/'relieve_alterado',self.clima,self.rev,raiz=self.root,relieve=True)
            self.assertFalse((self.root/'relieve_alterado').exists())
        finally:p.write_bytes(original)

    def test_d020_utf8_explicito_con_predeterminado_windows(self):
        from scripts.t07_verificar import verificar
        original = Path.read_text
        decision = (self.root/'registro/decisiones.csv').resolve()
        lecturas = []

        def windows(ruta, *args, **kw):
            if ruta.resolve() == decision:
                lecturas.append(kw.get('encoding'))
                kw = {**kw, 'encoding': kw.get('encoding') or 'cp1252'}
            return original(ruta, *args, **kw)

        with patch.object(Path, 'read_text', windows):
            salida = self.root/'d020_windows'
            integrar(self.rev, salida, self.clima, self.rev, raiz=self.root, relieve=True)
            self.assertEqual(verificar(salida, self.clima, self.root)['resultado'], 'verificado')
        self.assertEqual(lecturas, ['utf-8', 'utf-8'])

    def test_parametros_incompletos(self):
        with self.assertRaisesRegex(ValueError,'conjuntamente'):
            integrar(self.rev,self.root/'parametros',self.clima,None,False,self.root)


if __name__=='__main__':unittest.main()
