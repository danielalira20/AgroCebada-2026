"""Estado de las cuentas independiente de la vida de los widgets; admite un mapping de sesión."""


def iniciar_planeador(estado):
    if "planeador" not in estado:
        estado["planeador"] = {
            "precio_t": estado.get("calc_precio"), "costo_ha": estado.get("calc_costo"),
            "area_rapida_ha": estado.get("calc_area_rapida"), "municipio_rapido": None,
            "_area_rapida_inicializada": "calc_area_rapida" in estado,
            "areas_parcela_ha": {k[len("calc_area_"):]: estado[k] for k in estado
                                  if k.startswith("calc_area_") and k != "calc_area_rapida"},
        }
    return estado["planeador"]


def hidratar_compatibilidad(estado):
    """Restaura lectores legacy antes de dibujar cualquier widget de la página."""
    datos = iniciar_planeador(estado)
    estado["calc_precio"] = datos["precio_t"]
    estado["calc_costo"] = datos["costo_ha"]
    for pid, area in datos["areas_parcela_ha"].items():
        estado[f"calc_area_{pid}"] = area


def preparar_area(estado, clave, inicial, parcela=None):
    """Hidrata una sola área antes de montar su control, sin cambiar el catálogo."""
    datos = iniciar_planeador(estado)
    if parcela is None:
        if not datos.get("_area_rapida_inicializada", False):
            existente = datos["area_rapida_ha"]
            datos["area_rapida_ha"] = estado.get(clave, existente if existente is not None else inicial)
            datos["_area_rapida_inicializada"] = True
        estado[clave] = datos["area_rapida_ha"]
    else:
        areas = datos["areas_parcela_ha"]
        areas.setdefault(parcela, estado.get(clave, inicial))
        estado[clave] = areas[parcela]


def guardar_entrada(estado, clave, campo, parcela=None):
    """Callback: conserva también None al limpiar; no recupera un valor anterior."""
    datos = iniciar_planeador(estado)
    valor = estado[clave]
    if parcela is None:
        datos[campo] = valor
        if campo == "area_rapida_ha":
            datos["_area_rapida_inicializada"] = True
    else:
        datos["areas_parcela_ha"][parcela] = valor
