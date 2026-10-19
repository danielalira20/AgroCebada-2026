"""Calidad del dato de una parcela, en frases simples para la Ficha técnica (M14).
Junta las imágenes despejadas y huecos del soporte de T03, la revisión de contornos de T07 y el escalón con que
vienen escritas las cosechas del municipio. Es contexto para el analista: no entra en la estimación."""
import pandas as pd

SENSORES = {"s2": "Sentinel-2", "pl": "Planet", "ls": "Landsat"}
ESCALONES = [0.5, 0.1, 0.01]      # de más grueso a más fino
MIN_PARCELAS_ESCALON = 3          # con menos parcelas con cosecha no se puede saber si vienen redondeadas


def imagenes(sop, pid):
    """Capturas despejadas por sensor y el sensor con el hueco más corto en junio–octubre. None si no hay soporte."""
    if sop is None or pid not in sop.index:
        return None
    s = sop.loc[pid]
    despejadas = {nombre: int(s[f"{k}_capturas_despejadas"]) for k, nombre in SENSORES.items()
                  if pd.notna(s.get(f"{k}_capturas_despejadas"))}
    huecos = {nombre: float(s[f"{k}_hueco_max_dias_jun_oct"]) for k, nombre in SENSORES.items()
              if pd.notna(s.get(f"{k}_hueco_max_dias_jun_oct"))}
    mejor = min(huecos, key=huecos.get) if huecos else None
    return {"despejadas": despejadas, "sensor_hueco": mejor, "hueco_dias": huecos.get(mejor)}


def contorno(cal, pid):
    """Si el dibujo de la parcela tiene alerta (revisión de contornos de T07) y por qué. None si no hay dato."""
    if cal is None or pid not in cal.index:
        return None
    c = cal.loc[pid]
    motivos = []
    categoria = str(c.contorno_categoria).strip().upper()
    if categoria == "B":
        motivos.append("el dibujo corta la orilla del campo o deja dentro algo que no es cultivo (casas, camino, árboles)")
    elif categoria == "C":
        motivos.append("un mismo dibujo junta varios campos separados por algo que no es cultivo")
    if str(c.contorno_angosta_o_muy_pequena).strip().lower() == "si":
        motivos.append("la parcela es muy angosta o muy pequeña (menos de unos 40 m de ancho o menos de 1 ha)")
    return {"alerta": str(c.alerta_contorno_t03_bis).strip().lower() == "si", "motivos": motivos}


def escalon(valores):
    """El escalón más grueso (0.5, 0.1 o 0.01) del que todas las cosechas son múltiplo.
    None si hay menos de MIN_PARCELAS_ESCALON valores o vienen más finos que 0.01."""
    v = [float(x) for x in valores if pd.notna(x)]
    if len(v) < MIN_PARCELAS_ESCALON:
        return None
    for paso in ESCALONES:
        if all(abs(x / paso - round(x / paso)) < 1e-6 for x in v):
            return paso
    return None


def frase_redondeo(d, municipio):
    """(hay_que_avisar, frase) sobre cómo vienen escritas las cosechas del municipio."""
    reales = d.loc[(d.municipio == municipio) & (d.CONJUNTO == "ENTRENAMIENTO"), "real"].dropna()
    n = len(reales)
    if n == 0:
        return False, f"{municipio} no tiene parcelas con cosecha registrada."
    if n < MIN_PARCELAS_ESCALON:
        cuantas = "1 parcela" if n == 1 else f"{n} parcelas"
        return False, f"{municipio} sólo tiene {cuantas} con cosecha: muy pocas para saber si vienen redondeadas."
    paso = escalon(reales)
    if paso is not None and paso >= 0.5:
        return True, (f"Las cosechas de {municipio} vienen redondeadas a {paso:g} t/ha: el dato registrado no distingue "
                      f"diferencias menores a {paso / 2:g} t/ha, así que ahí el error no puede ser más fino que eso.")
    if paso == 0.1:
        return False, f"Las cosechas de {municipio} vienen con un decimal ({paso:g} t/ha); ese redondeo casi no pesa en el error."
    return False, f"Las cosechas de {municipio} vienen con dos decimales o más; no hay redondeo que pese en el error."


def tarjeta(d, sop, cal, pid):
    """Líneas de la tarjeta: lista de dicts con estado ('ok', 'ojo' o 'info'), titulo y texto."""
    lineas = []
    im = imagenes(sop, pid)
    if im is not None:
        if im["despejadas"]:
            lineas.append(dict(estado="info", titulo="Imágenes sin nubes en la temporada",
                               texto=" · ".join(f"{s}: {n}" for s, n in im["despejadas"].items())))
        if im["sensor_hueco"] is not None:
            lineas.append(dict(estado="info", titulo="Hueco más largo sin imagen (junio–octubre)",
                               texto=f"{im['hueco_dias']:.0f} días con {im['sensor_hueco']}, "
                                     "el sensor con menos huecos para esta parcela."))
    co = contorno(cal, pid)
    if co is not None:
        if co["alerta"]:
            por_que = "; ".join(co["motivos"]) or "no coincide bien con el campo real"
            lineas.append(dict(estado="ojo", titulo="Dibujo de la parcela",
                               texto=f"No coincide bien con el campo: {por_que}. "
                                     "Lo que se mide de esta parcela (área e imágenes) es menos confiable."))
        else:
            lineas.append(dict(estado="ok", titulo="Dibujo de la parcela", texto="Sigue bien la orilla del campo."))
    avisar, frase = frase_redondeo(d, d.loc[pid, "municipio"])
    lineas.append(dict(estado="ojo" if avisar else "info", titulo="Cosechas registradas del municipio", texto=frase))
    return lineas