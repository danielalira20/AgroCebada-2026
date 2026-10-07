"""Diccionario completo de las cuatro tablas de T07, construido junto al contrato."""
from scripts.t07_fuentes import BASE
from scripts.t07_ventanas import LARGA, ANCHA, CALIDAD, VARIABLES

CAMPOS = ("archivo", "columna", "definicion", "unidad", "funcion", "producto",
          "periodo", "agregacion", "significado_vacio", "procedencia")


def diccionario():
    descripcion = {
        "id_parcela": ("Clave única original de parcela; equivalencia ID_POLIGONO", "sin unidad", "metadato"),
        "campania": ("Campaña de la etiqueta: 2025; no crea observaciones para otros años", "año", "metadato"),
        "rendimiento_t_ha": ("Rendimiento original; texto conservado sin redondear, ajustar o imputar", "t/ha", "objetivo"),
        "area_ha_origen": ("Superficie declarada de origen; no es superficie geodésica recalculada", "ha", "metadato"),
        "municipio": ("Municipio declarado; uso sujeto al escenario de evaluación T03", "categoría", "predictor_candidato"),
        "estado": ("Estado declarado de la parcela", "categoría", "metadato"),
        "cultivo_origen": ("Texto original Cultivo; su contraste requiere el experimento explícito T03", "categoría", "solo_auditoria"),
        "conjunto_origen": ("ENTRENAMIENTO o PREDICCION; procedencia, nunca predictor", "categoría", "metadato"),
        "ventana": ("Ventana calendario candidata abr_oct o jun_oct; no fecha de cultivo confirmada", "categoría", "metadato"),
        "inicio": ("Primer día calendario incluido", "fecha ISO", "metadato"),
        "fin": ("Último día observado incluido; no prueba disponibilidad histórica", "fecha ISO", "metadato"),
        "dias_esperados": ("Días naturales de todos los meses de la ventana", "días", "calidad"),
        "variable": ("PREC, Tmin o Tmax del resumen controlado", "categoría", "metadato"),
        "unidad": ("Unidad del resumen de ventana", "categoría", "metadato"),
        "meses_esperados": ("Meses requeridos: 7 para abr_oct y 5 para jun_oct", "meses", "calidad"),
        "meses_presentes": ("Meses con fila de entrada, incluso sin media", "meses", "calidad"),
        "meses_validos": ("Meses con media finita; incluye cobertura parcial", "meses", "calidad"),
        "dias_validos": ("Días de los meses con media finita; no certifica soporte completo", "días", "calidad"),
        "cobertura_minima": ("Mínimo de cobertura_valida T04 entre meses presentes, incluso NoData=0; no cobertura conjunta", "fracción 0–1", "calidad"),
        "motivo": ("Causas separadas por punto y coma: mes_ausente, mes_sin_media, cobertura_parcial_sin_extrapolacion", "categoría", "calidad"),
        "periodos_con_problema": ("Meses ausentes, sin media o de cobertura parcial, separados por punto y coma", "YYYY-MM", "calidad"),
    }
    out = []
    for archivo, columnas in [("catalogo_base.csv", BASE), ("clima_ventanas.csv", LARGA),
                              ("clima_variables.csv", ANCHA), ("calidad_ventanas.csv", CALIDAD)]:
        for columna in columnas:
            campo = next((c for c in VARIABLES.values() if columna == c or columna.startswith(c + "_")), None)
            w = next((w for w in ("abr_oct", "jun_oct") if columna.endswith("_" + w)), None)
            if campo:
                lluvia = campo == "prec_acumulada_mm"
                d = ("Precipitación acumulada: suma temporal de medias espaciales mensuales" if lluvia else
                     "Media temporal de " + ("Tmin" if campo == "tmin_media_c" else "Tmax") +
                     " mensual, ponderada por días; no extremo absoluto ni reconstrucción diaria")
                u, rol = ("mm" if lluvia else "grados Celsius"), "predictor_candidato"
                producto = "CHIRPS" if lluvia else "CHIRTS-ERA5"
                agregado = "suma mensual" if lluvia else "sum(media_mensual × días_mes) / días_ventana"
                vacio = "Ventana incompleta o cobertura parcial: consultar calidad_ventanas.csv; nunca equivale a cero"
            else:
                if columna == "estado" and archivo == "calidad_ventanas.csv":
                    d, u, rol = "completa, incompleta o cobertura_parcial; no es estado geográfico", "categoría", "calidad"
                else:
                    d, u, rol = descripcion[columna]
                producto, agregado = ("catálogo T02", "selección literal") if archivo == "catalogo_base.csv" else ("T04", "control temporal")
                vacio = ("Etiqueta no disponible en las 59 parcelas PREDICCION; no se imputa" if columna == "rendimiento_t_ha" else
                         "Sin meses presentes; no equivale a cero" if columna == "cobertura_minima" else
                         "Ningún problema detectado" if columna in {"motivo", "periodos_con_problema"} else
                         "No permitido por el contrato")
            out.append(dict(archivo=archivo, columna=columna, definicion=d, unidad=u, funcion=rol,
                            producto=producto, periodo=w or ("campaña 2025" if archivo == "catalogo_base.csv" else "ventana indicada en cada fila"),
                            agregacion=agregado, significado_vacio=vacio,
                            procedencia="inventario_fuentes.json; calidad_ventanas.csv" if campo else "inventario_fuentes.json"))
    return out
