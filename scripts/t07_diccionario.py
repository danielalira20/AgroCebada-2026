"""Diccionario completo de las cuatro tablas de T07, construido junto al contrato."""
from scripts.t07_fuentes import BASE
from scripts.t07_ventanas import LARGA, ANCHA, CALIDAD, VARIABLES

AREA_T10 = dict(
    candidata=dict(columna='area_ha_origen', archivo='tabla_comun.csv', unidad='ha',
        fuente='analisis/auditoria_catalogo_y_etiquetas/tablas/catalogo_parcelas.csv',
        criterio='Superficie declarada original del dataset; no sustituir por un área calculada'),
    rol_en_t07='metadato', frente_candidato='T10', predictor_automatico_t09=False,
    alternativas_solo_auditoria=[
        dict(columna='area_ha_geodesica', unidad='ha',
             fuente='analisis/auditoria_catalogo_y_etiquetas/tablas/catalogo_parcelas.csv'),
        dict(columna='area_parcela_6372_m2', unidad='m²', fuente='calidad_relieve.csv',
             disponible_solo_con_relieve=True)],
    alternativa_en_modelo_requiere_experimento_explicito=True,
    rendimiento_por_area_no_es_produccion_confirmada=True)

GRUPO_REGISTRO = dict(
    columna='cultivo_origen', equivalencia_t03='grupo_registro',
    funcion='referencia_y_evaluacion',
    usos=['respaldo_por_grupo_T03_D019', 'desgloses_de_error_por_grupo'],
    referencia_aprendida_solo_en_entrenamiento=True,
    predictor_automatico=False, normalizar_texto_original=False,
    estratificacion_interna_t03='municipio u otros; no cultivo_origen')

CAMPOS = ("archivo", "columna", "definicion", "unidad", "funcion", "producto",
          "periodo", "agregacion", "significado_vacio", "procedencia")


def diccionario():
    descripcion = {
        "id_parcela": ("Clave única original de parcela; equivalencia ID_POLIGONO", "sin unidad", "metadato"),
        "campania": ("Campaña de la etiqueta: 2025; no crea observaciones para otros años", "año", "metadato"),
        "rendimiento_t_ha": ("Rendimiento original; texto conservado sin redondear, ajustar o imputar", "t/ha", "objetivo"),
        "area_ha_origen": ("Superficie declarada original en ha: candidata explícita de T10; metadato en T07, no entrada automática T09; no sustituir por área geodésica o plana", "ha", "metadato"),
        "municipio": ("Municipio declarado; uso sujeto al escenario de evaluación T03", "categoría", "predictor_candidato"),
        "estado": ("Estado declarado de la parcela", "categoría", "metadato"),
        "cultivo_origen": ("Grupo de registro original (grupo_registro en T03); respaldo calculado sólo con el entrenamiento y desgloses de error; no predictor automático ni estrato interno", "categoría", "referencia_y_evaluacion"),
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
        "celdas_lluvia_tocadas_t02": ("Celdas intersectadas en la cuadrícula de lluvia, según T02; atributo de parcela repetido por ventana/variable, no conteo de temperatura ni de celdas válidas", "celdas", "calidad"),
        "centroide_dentro_parcela": ("Bandera geométrica climática T04; False conserva el centroide exterior sin desplazarlo", "booleano", "calidad"),
        "meses_centroide_validos": ("Meses presentes con valor finito en el centroide, independientemente de la cobertura parcelaria", "meses", "calidad"),
        "dias_centroide_validos": ("Días de los meses con valor finito en el centroide; no certifica ventana completa", "días", "calidad"),
        "periodos_sin_centroide": ("Meses ausentes o cuyo centroide no tiene valor, separados por punto y coma", "YYYY-MM", "calidad"),
        "valor_centroide_ventana": ("Agregado temporal del valor del centroide: PREC suma, Tmin/Tmax ponderadas por días; sólo con todos los meses", "unidad de la variable indicada en la fila", "solo_auditoria"),
        "diferencia_media_menos_centroide": ("Media espacial agregada en la ventana menos agregado del centroide con idénticos meses y pesos; sensibilidad espacial, no error de predicción", "unidad de la variable indicada en la fila", "solo_auditoria"),
        "estado_comparacion_centroide": ("comparable, centroide_incompleto o ventana_no_completa; comparable no afirma que el centroide esté dentro del polígono", "categoría", "calidad"),
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
                if columna == 'celdas_lluvia_tocadas_t02':
                    producto, agregado = 'soporte de lluvia T02', 'selección literal por id_parcela'
                elif columna in {'valor_centroide_ventana', 'diferencia_media_menos_centroide'}:
                    agregado = 'PREC suma; Tmin/Tmax sum(valor mensual × días_mes) / días_ventana; comparación sobre iguales meses y pesos'

                vacio = ("Etiqueta no disponible en las 59 parcelas PREDICCION; no se imputa" if columna == "rendimiento_t_ha" else
                         "Sin meses presentes; no equivale a cero" if columna == "cobertura_minima" else
                         "Ningún problema detectado" if columna in {"motivo", "periodos_con_problema", "periodos_sin_centroide"} else
                         "Falta al menos un mes de centroide; nunca equivale a cero" if columna == "valor_centroide_ventana" else
                         "Ventana principal no completa o centroide incompleto; consultar estado_comparacion_centroide" if columna == "diferencia_media_menos_centroide" else
                         "Sin meses presentes; no se inventa pertenencia geométrica" if columna == "centroide_dentro_parcela" else
                         "No permitido por el contrato")
            out.append(dict(archivo=archivo, columna=columna, definicion=d, unidad=u, funcion=rol,
                            producto=producto, periodo=w or ("campaña 2025" if archivo == "catalogo_base.csv" else "ventana indicada en cada fila"),
                            agregacion=agregado, significado_vacio=vacio,
                            procedencia="analisis/auditoria_catalogo_y_etiquetas/tablas/soporte_por_parcela.csv; inventario_fuentes.json" if columna == "celdas_lluvia_tocadas_t02" else
                            "registro/t04/clima_parcela_mes.csv; inventario_fuentes.json" if archivo == "calidad_ventanas.csv" else
                            "inventario_fuentes.json; calidad_ventanas.csv" if campo else "inventario_fuentes.json"))
    return out
