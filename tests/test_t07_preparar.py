import hashlib
from pathlib import Path
import subprocess
import tempfile
import unittest

from scripts.t07_fuentes import BASE, CLIMA, guardar_csv, guardar_json, sha
from scripts.t07_preparar import preparar, preparar_sin_clima, comprobar_fuente, T02, T02_ARCHIVOS, T04_ARCHIVOS
from scripts.t07_diccionario import diccionario
from tests.test_t07_fuentes import parcela, mes


class Preparacion(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.tmp.name)
        def g(*args):
            return subprocess.check_output(['git', *args], cwd=cls.root, stderr=subprocess.PIPE)
        g('init', '-q'); g('config', 'user.email', 'prueba@example.invalid'); g('config', 'user.name', 'Prueba T07')
        catalogo = [parcela(f'AGC_{n:03d}', '3.5' if n <= 138 else '', 'ENTRENAMIENTO' if n <= 138 else 'PREDICCION') for n in range(1, 198)]
        for n in T02_ARCHIVOS:
            p = cls.root / T02 / n; p.parent.mkdir(parents=True, exist_ok=True)
            if n == 'tablas/catalogo_parcelas.csv': guardar_csv(p, [k for k in BASE if k != 'campania'], catalogo)
            else: p.write_text('referencia de prueba\n')
        pro = cls.root / 'docs/T03_protocolo_evaluacion.md'; pro.parent.mkdir(); pro.write_text('protocolo de prueba')
        (cls.root / 'docs/T06_satelite.md').write_text('inventario de prueba')
        s = cls.root / 'registro/t06'; s.mkdir(parents=True)
        guardar_csv(s / 'variables_satelitales.csv', ['ID_POLIGONO', 'ndvi_x'], [dict(ID_POLIGONO=r['id_parcela'], ndvi_x='0.5') for r in catalogo])
        guardar_csv(s / 'variables_satelitales_diccionario.csv', ['columna'], [dict(columna='ndvi_x')])
        cls.clima = cls.root / 'registro/t04'; cls.clima.mkdir()
        periodos = [f'{a}-{m:02d}' for a in range(2022, 2026) for m in range(1, 13)]
        filas = []
        for r in catalogo:
            for p in periodos:
                for v in ('PREC', 'Tmin', 'Tmax'):
                    x = mes(p, v, '20' if v == 'Tmax' else '10'); x['id_parcela'] = r['id_parcela']
                    x['posterior_al_corte'] = str(p > '2025-10'); filas.append(x)
        guardar_csv(cls.clima / 'clima_parcela_mes.csv', CLIMA, filas)
        from scripts.t07_fuentes import fin_mes, UNIDADES
        mapas = [dict(periodo=p, variable=v, unidad=UNIDADES[v], cuadricula_id='lluvia' if v == 'PREC' else 'temp',
                      etiquetas=dict(Agregacion='Suma de precipitación diaria' if v == 'PREC' else 'Promedio mensual',
                                     Periodo=p, Unidad=UNIDADES[v], Dias_acumulados=str(fin_mes(p).day)))
                 for p in periodos for v in UNIDADES]
        guardar_json(cls.clima / 'procedencia.json', dict(mapas=mapas, sha256_paquete='a'*64,
                     soportes=[dict(id_parcela=r['id_parcela'], cuadricula_id=q) for r in catalogo for q in ['lluvia', 'temp']]))
        guardar_json(cls.clima / 'conciliacion_t02.json', dict(estado='conciliada_con_referencia_identificada', ids_verificados=197,
                     revision_t02='referencia_de_prueba', archivos_t02_sha256={n: sha(cls.root / T02 / n) for n in T02_ARCHIVOS}))
        guardar_json(cls.clima / 'controles.json', dict(filas=28368, ids=197, periodos=48, estados=dict(cobertura_completa=28368),
                     filas_posteriores_al_corte=1182, filas_centroide_exterior=0))
        guardar_json(cls.clima / 'manifest.json', dict(schema='t04_entrega_compacta_v1', ids=[r['id_parcela'] for r in catalogo],
                     periodos=periodos, columnas=list(CLIMA), corte_observacional_provisional='2025-10-31', cierre_t04=False,
                     disponibilidad_historica_fira='no documentada', versiones_producto_fira='sin número documentado',
                     archivos_sha256={n: sha(cls.clima / n) for n in T04_ARCHIVOS if n != 'manifest.json'}))
        for n in ['t07_preparar.py','t07_fuentes.py','t07_ventanas.py','t07_diccionario.py','t07_preparar_insumos.py','t02_contrato.py']:
            p = cls.root / 'scripts' / n; p.parent.mkdir(exist_ok=True); p.write_text('código de prueba')
        g('add', '.'); g('commit', '-qm', 'fuentes identificadas')
        cls.rev = g('rev-parse', 'HEAD').decode().strip()
        guardar_json(cls.clima / 'origen_git.json', dict(schema='t07_copia_t04_v1', revision_git=cls.rev, prefijo_git='registro/t04',
                     estado_revision_declarado='aceptada', archivos_sha256={n: sha(cls.clima / n) for n in T04_ARCHIVOS}))

    @classmethod
    def tearDownClass(cls): cls.tmp.cleanup()

    def test_preparacion_completa_reproducible_sin_master(self):
        a, b = self.root / 'salida1', self.root / 'salida2'
        c = preparar(self.clima, self.rev, self.rev, a, self.root)
        preparar(self.clima, self.rev, self.rev, b, self.root)
        self.assertEqual(c['resumenes_completos'], 1182)
        self.assertEqual(c['etiquetas_ausentes'], 59)
        self.assertEqual({p.name: sha(p) for p in a.iterdir()}, {p.name: sha(p) for p in b.iterdir()})
        with self.assertRaisesRegex(ValueError, 'ya existe'): preparar(self.clima, self.rev, self.rev, a, self.root)

    def test_alteracion_de_entrada_detiene_sin_publicar(self):
        p = self.clima / 'clima_parcela_mes.csv'; original = p.read_bytes()
        try:
            p.write_bytes(original + b'alteracion\n')
            with self.assertRaisesRegex(ValueError, 'Copia T04 alterada'):
                preparar(self.clima, self.rev, self.rev, self.root / 'salida_alterada', self.root)
            self.assertFalse((self.root / 'salida_alterada').exists())
        finally: p.write_bytes(original)

    def test_catalogo_local_distinto_detiene(self):
        p = self.root / T02 / 'tablas/catalogo_parcelas.csv'; original = p.read_bytes()
        try:
            p.write_bytes(original.replace(b'3.5', b'9.9', 1))
            with self.assertRaisesRegex(ValueError, 'Fuente local distinta'):
                preparar(self.clima, self.rev, self.rev, self.root / 'salida_cat_alterada', self.root)
        finally: p.write_bytes(original)

    def test_referencia_t02_incompatible(self):
        with self.assertRaisesRegex(ValueError, 'Actualizar y revalidar T04'):
            comprobar_fuente(f'{T02}/tablas/catalogo_parcelas.csv', self.rev, '0'*64, self.root)

    def test_salida_en_raw_rechazada(self):
        with self.assertRaisesRegex(ValueError, 'Salida protegida'):
            preparar(self.clima, self.rev, self.rev, self.root / 'data/raw/error', self.root)

    def test_catalogo_sin_clima_no_lee_t04_ni_genera_valores(self):
        origen = self.clima / 'origen_git.json'; respaldo = origen.read_bytes()
        try:
            origen.unlink()
            out = self.root / 'catalogo_sin_clima'
            c = preparar_sin_clima(self.rev, out, self.root)
            self.assertEqual(c['parcelas'], 197)
            self.assertFalse(c['valores_climaticos_generados'])
            self.assertEqual({p.name for p in out.iterdir()}, {'catalogo_base.csv','diccionario_columnas.csv','inventario_fuentes.json','controles.json','manifest.json'})
        finally: origen.write_bytes(respaldo)

    def test_t04_provisional_rechazada(self):
        import json
        origen = self.clima / 'origen_git.json'; respaldo = origen.read_bytes()
        try:
            d = json.loads(respaldo); d['estado_revision_declarado'] = 'en_revision'; guardar_json(origen, d)
            out = self.root / 'provisional_rechazada'
            with self.assertRaisesRegex(ValueError, 'T04 pendiente de aceptación'):
                preparar(self.clima, self.rev, self.rev, out, self.root)
            self.assertFalse(out.exists())
        finally: origen.write_bytes(respaldo)

    def test_diccionario_roles_y_ausencias(self):
        d = diccionario(); pares = [(r['archivo'], r['columna']) for r in d]
        self.assertEqual(len(d), 36)
        self.assertEqual(len(set(pares)), 36)
        y = next(r for r in d if r['columna'] == 'rendimiento_t_ha')
        self.assertEqual(y['funcion'], 'objetivo')
        self.assertTrue(all(r['funcion'] != 'predictor_candidato' for r in d if r['columna'] in {'id_parcela','conjunto_origen','rendimiento_t_ha'}))


if __name__ == '__main__': unittest.main()
