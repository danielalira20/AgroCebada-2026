"""Pruebas de area_geodesica, la función que mide superficies en diagnosticar_soporte.py.

Uso (con el mismo entorno, desde la carpeta de la auditoría):
    python scripts/probar_area_geodesica.py

No lee el dataset ni escribe ningún archivo. Comprueba que un contacto sin superficie
(un punto o una línea) vale 0 en lugar de detener el programa, y que las piezas con
superficie se siguen sumando igual que antes.
"""
import sys

sys.dont_write_bytecode = True

from shapely.geometry import GeometryCollection, LineString, MultiLineString, MultiPoint, MultiPolygon, Point, Polygon, box

from diagnosticar_soporte import area_geodesica

CUADRO = box(-98.50, 19.50, -98.49, 19.51)           # unas 116 hectáreas
OTRO = box(-98.40, 19.50, -98.39, 19.51)


def test_vacia_vale_cero():
    assert area_geodesica(Polygon()) == 0.0
    assert area_geodesica(GeometryCollection()) == 0.0


def test_punto_y_linea_valen_cero():
    assert area_geodesica(Point(-98.5, 19.5)) == 0.0
    assert area_geodesica(MultiPoint([(-98.5, 19.5), (-98.4, 19.5)])) == 0.0
    assert area_geodesica(LineString([(-98.5, 19.5), (-98.4, 19.5)])) == 0.0
    assert area_geodesica(MultiLineString([[(-98.5, 19.5), (-98.4, 19.5)]])) == 0.0


def test_contorno_que_solo_toca_una_celda():
    celda_al_lado = box(-98.49, 19.50, -98.48, 19.51)      # comparte un lado con CUADRO
    celda_en_esquina = box(-98.49, 19.51, -98.48, 19.52)   # comparte solo una esquina
    assert CUADRO.intersection(celda_al_lado).geom_type == "LineString"
    assert CUADRO.intersection(celda_en_esquina).geom_type == "Point"
    assert area_geodesica(CUADRO.intersection(celda_al_lado)) == 0.0
    assert area_geodesica(CUADRO.intersection(celda_en_esquina)) == 0.0


def test_una_pieza_tiene_la_superficie_esperada():
    superficie = area_geodesica(CUADRO)
    assert 1_150_000 < superficie < 1_170_000          # cerca de 116 hectáreas
    invertido = Polygon(list(CUADRO.exterior.coords)[::-1])
    assert area_geodesica(invertido) == superficie     # no depende del sentido del trazo


def test_un_hueco_se_descuenta():
    hueco = box(-98.498, 19.502, -98.492, 19.508)
    con_hueco = Polygon(CUADRO.exterior.coords, [hueco.exterior.coords])
    assert abs(area_geodesica(con_hueco) - (area_geodesica(CUADRO) - area_geodesica(hueco))) < 0.01


def test_varias_piezas_se_suman():
    suma = area_geodesica(CUADRO) + area_geodesica(OTRO)
    assert area_geodesica(MultiPolygon([CUADRO, OTRO])) == suma


def test_mezcla_de_piezas_cuenta_solo_las_superficies():
    suma = area_geodesica(CUADRO) + area_geodesica(OTRO)
    mezcla = GeometryCollection([CUADRO, LineString([(-98.5, 19.5), (-98.4, 19.5)]), Point(-98.3, 19.5),
                                 MultiPolygon([OTRO])])
    assert area_geodesica(mezcla) == suma


if __name__ == "__main__":
    pruebas = [(nombre, f) for nombre, f in sorted(globals().items()) if nombre.startswith("test_")]
    for nombre, prueba in pruebas:
        prueba()
        print(f"cumple  {nombre}")
    print(f"{len(pruebas)} de {len(pruebas)} pruebas cumplen")
