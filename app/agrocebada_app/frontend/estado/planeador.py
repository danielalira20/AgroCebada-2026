"""Estado de las cuentas independiente de la vida de los widgets; admite un mapping de sesión."""

MODOS_AGRICULTOR = ("Parcela del catálogo", "Consulta rápida")


def iniciar_planeador(estado):
    estado.setdefault("agri_modo", MODOS_AGRICULTOR[0])
    if "planeador" not in estado:
        estado["planeador"] = {
            "precio_t": estado.get("calc_precio"), "costo_ha": estado.get("calc_costo"),
            "area_rapida_ha": estado.get("calc_area_rapida"), "municipio_rapido": None,
            "_area_rapida_inicializada": "calc_area_rapida" in estado,
            "areas_parcela_ha": {k[len("calc_area_"):]: estado[k] for k in estado
                                  if k.startswith("calc_area_") and k != "calc_area_rapida"},
        }
    return estado["planeador"]


def preparar_modo(estado):
    """El selector es temporal; agri_modo conserva el recorrido al cambiar de vista."""
    iniciar_planeador(estado)
    if estado["agri_modo"] not in MODOS_AGRICULTOR:
        estado["agri_modo"] = MODOS_AGRICULTOR[0]
    estado["agri_modo_control"] = estado["agri_modo"]


def guardar_modo(estado):
    elegido = estado["agri_modo_control"]
    if elegido in MODOS_AGRICULTOR:
        estado["agri_modo"] = elegido


def preparar_municipio(estado, opciones):
    """Retira una referencia fuera de cobertura antes de montar el selector rápido."""
    datos = iniciar_planeador(estado)
    if datos["municipio_rapido"] not in opciones:
        datos["municipio_rapido"] = None
    estado["calc_municipio_rapido"] = datos["municipio_rapido"]


def preparar_catalogo(estado):
    datos = iniciar_planeador(estado)
    for clave, valor in datos.get("seleccion_catalogo", {}).items():
        estado.setdefault(clave, valor)


def guardar_catalogo(estado):
    datos = iniciar_planeador(estado)
    datos["seleccion_catalogo"] = {k: estado[k] for k in ("agri_muni", "agri_parcela", "encuadre_agri")
                                   if k in estado}


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
