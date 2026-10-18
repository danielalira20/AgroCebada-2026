"""Constantes de la app. No importa nada del resto del paquete."""
from pathlib import Path

# ---------------------------------------------------------------- ubicaciones
APP = Path(__file__).resolve().parents[1]         # carpeta app/
PAQ = APP / "datos_app"                           # paquete compacto que arma herramientas/preparar_datos.py
CLAVE_DATASET = "ID_area_rendimiento_70_30_Reto_AgroCebada.csv"

# ---------------------------------------------------------------- datos y procedimiento de T08
MODELOS_CANDIDATOS = ["media_mun__resp_grupo", "mediana_mun__resp_grupo"]
TEMPORADA = ("2025-04-01", "2025-10-31")
COLUMNAS_INDICES = ["ndvi_promedio", "evi_promedio", "lai_promedio"]
PALETA = [(2.0, (217, 164, 65)), (3.8, (140, 203, 94)), (5.6, (47, 224, 160))]   # t/ha: paja -> verde -> menta

# ---------------------------------------------------------------- interfaz
MODELO_OFICIAL = "media_mun__resp_grupo"          # cambiar aquí si T16 elige la mediana
MODELOS = {"media_mun__resp_grupo": "Media · oficial","mediana_mun__resp_grupo": "Mediana · en evaluación",}
CORTE_TXT = "31 de octubre de 2025"
INDICES = {"NDVI (verdor)": "ndvi_promedio", "EVI": "evi_promedio", "LAI (área foliar)": "lai_promedio"}
MESES = dict(enumerate(["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"], 1))
MESES_EJE = "['ene','feb','mar','abr','may','jun','jul','ago','sep','oct','nov','dic'][month(datum.value)]"

# Mapa 3D: relieve público (sin clave) e imagen Sentinel-2 sin nubes (sin clave; uso no comercial con atribución).
RELIEVE = "https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png"
SATELITE = "https://tiles.maps.eox.at/wmts/1.0.0/s2cloudless-2021_3857/default/g/{z}/{y}/{x}.jpg"
CREDITOS = ("Imagen: Sentinel-2 cloudless 2021 de EOX IT Services GmbH (s2maps.eu), contiene datos Copernicus Sentinel "
            "modificados, CC BY-NC-SA 4.0 · Relieve: Terrain Tiles, AWS Open Data · Mapa base: CARTO, OpenStreetMap")
AYUDA_MAPA = ("Clic en una parcela para seleccionarla · pasa el ratón para ver su detalle · rueda o pellizco para "
              "acercar (alejar tiene un límite) · arrastra para mover · en 3D, Shift + arrastrar para girar")
TOOLTIP = {"text": "{id} · {municipio}\n{detalle}",
           "style": {"backgroundColor": "rgba(12,20,16,0.92)", "color": "#E7EFE9", "fontSize": "12px",
                     "lineHeight": "1.5", "maxWidth": "330px", "borderRadius": "10px", "padding": "9px 11px",
                     "border": "1px solid rgba(255,255,255,0.14)"}}
