"""D.1: soporte del contraste NDWI 15–45 días después del máximo, sin modelos/y."""
from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from datetime import date, datetime, timedelta
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
from statistics import median
import tempfile

ROOT = Path(__file__).resolve().parents[1]
VERSION = "t15-D1-NDWI-v1"
VENTANAS = {"abr_oct": date(2025, 4, 1), "jun_oct": date(2025, 6, 1)}
CORTE = date(2025, 10, 31)
RAW = "Conjunto_datos_BASICO_AgroCebada2026.csv"
MISSING = {"", "nan", "na", "null", "none"}


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def number(value, name):
    text = str(value).strip()
    if text.lower() in MISSING:
        return None
    try:
        n = float(text)
    except ValueError as exc:
        raise ValueError(f"Valor no numérico: {name}") from exc
    if not math.isfinite(n):
        raise ValueError(f"Valor no finito: {name}")
    return n


def read_csv(path):
    with Path(path).open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames or len(reader.fieldnames) != len(set(reader.fieldnames)):
            raise ValueError("Cabecera vacía o duplicada")
        rows = list(reader)
    if any(None in row or any(v is None for v in row.values()) for row in rows):
        raise ValueError("CSV no rectangular")
    return rows


def catalogue(rows):
    out = {}
    for row in rows:
        # Lista explícita: nunca se accede al campo de rendimiento.
        pid = row["id_parcela"]
        if not pid or pid in out:
            raise ValueError("ID vacío o duplicado en catálogo")
        group = row["conjunto_origen"]
        if group not in {"ENTRENAMIENTO", "PREDICCION"}:
            raise ValueError("Conjunto desconocido")
        out[pid] = {"id_parcela": pid, "municipio": row["municipio"], "conjunto": group}
    return out


@dataclass(frozen=True)
class Obs:
    pid: str
    fecha: date
    ndvi: float | None
    ndwi: float | None
    nube: float | None


def observations(path, ids):
    groups = {pid: [] for pid in ids}
    seen = set()
    sensor_counts = {}
    with Path(path).open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        needed = {"ID_POLIGONO", "sensor", "fecha_captura", "ndvi_promedio",
                  "ndwi_promedio", "porcentaje_nubosidad"}
        fields = reader.fieldnames or []
        if not needed.issubset(fields) or len(fields) != len(set(fields)):
            raise ValueError("Esquema Básico inválido")
        for row in reader:
            if None in row or any(v is None for v in row.values()):
                raise ValueError("Fila no rectangular")
            sensor = row["sensor"]
            sensor_counts[sensor] = sensor_counts.get(sensor, 0) + 1
            if sensor not in {"Sentinel-2", "Landsat"}:
                raise ValueError("Sensor no esperado en Básico")
            if sensor != "Sentinel-2":
                continue
            pid = row["ID_POLIGONO"]
            if pid not in groups:
                raise ValueError("ID de serie ajeno al catálogo")
            try:
                d = datetime.strptime(row["fecha_captura"], "%d/%m/%Y").date()
            except ValueError as exc:
                raise ValueError("Fecha inválida") from exc
            if (pid, d) in seen:
                raise ValueError("ID/fecha duplicados")
            seen.add((pid, d))
            v, w, c = (number(row[k], k) for k in
                       ["ndvi_promedio", "ndwi_promedio", "porcentaje_nubosidad"])
            if c is not None and not 0 <= c <= 100:
                raise ValueError("Nubosidad fuera de 0–100")
            if any(x is not None and not -1 <= x <= 1 for x in [v, w]):
                raise ValueError("Índice normalizado fuera de [-1,1]")
            groups[pid].append(Obs(pid, d, v, w, c))
    if any(not rows for rows in groups.values()):
        raise ValueError("Parcela sin serie Sentinel-2")
    return {pid: sorted(rows, key=lambda o: o.fecha) for pid, rows in groups.items()}, sensor_counts


def profile(rows, ini, fin=CORTE):
    if len({o.pid for o in rows}) > 1:
        raise ValueError("No mezclar parcelas en una curva")
    keys = [(o.pid, o.fecha) for o in rows]
    if len(keys) != len(set(keys)):
        raise ValueError("Fechas duplicadas")
    valid = sorted((o for o in rows if ini <= o.fecha <= fin and o.ndvi is not None
                    and o.nube is not None and 0 <= o.nube <= 5), key=lambda o: o.fecha)
    r = dict(n_capturas=len(valid), fecha_maximo=None, ndvi_max=None, amplitud_ndvi=None,
             n_empates_maximo=0, maximo_en_borde=None, meseta_45_dias=None,
             ndwi_ancla=None, ndwi_mediana_mas_menos15=None, n_fechas_post=0,
             fechas_post="", primera_post=None, ultima_post=None, intervalo_truncado=None,
             amplitud_temporal_post_dias=None, hueco_max_post_con_bordes_dias=None,
             ndwi_media_post=None, contraste_ndwi=None, calculable=False,
             motivo="menos_5_capturas", faltante_ancla=None, faltante_post=None)
    if len(valid) < 5:
        return r
    smooth = [median([o.ndvi for o in valid[max(0, k-1):k+2]]) for k in range(len(valid))]
    maximum = max(smooth)
    k = smooth.index(maximum)
    anchor = valid[k]
    amp = maximum - min(smooth[:k+1])
    plateau = [o.fecha for o, v in zip(valid, smooth) if v >= maximum - .05*amp]
    near = [o.ndwi for o in valid if abs((o.fecha-anchor.fecha).days) <= 15]
    left, right = anchor.fecha + timedelta(days=15), anchor.fecha + timedelta(days=45)
    end = min(right, fin)
    post = [o for o in valid if left <= o.fecha <= end and o.ndwi is not None]
    mean = math.fsum(o.ndwi for o in post)/len(post) if post else None
    gaps = [((post[0].fecha-left).days), ((end-post[-1].fecha).days)] if post else []
    gaps += [(b.fecha-a.fecha).days for a, b in zip(post, post[1:])]
    r.update(fecha_maximo=anchor.fecha, ndvi_max=maximum, amplitud_ndvi=amp,
             n_empates_maximo=sum(v == maximum for v in smooth), maximo_en_borde=k in {0,len(valid)-1},
             meseta_45_dias=(max(plateau)-min(plateau)).days >= 45,
             ndwi_ancla=anchor.ndwi,
             ndwi_mediana_mas_menos15=median(near) if all(v is not None for v in near) else None,
             n_fechas_post=len(post), fechas_post=";".join(o.fecha.isoformat() for o in post),
             primera_post=post[0].fecha if post else None, ultima_post=post[-1].fecha if post else None,
             intervalo_truncado=right > fin,
             amplitud_temporal_post_dias=(post[-1].fecha-post[0].fecha).days if post else None,
             hueco_max_post_con_bordes_dias=max(gaps) if gaps else None,
             ndwi_media_post=mean, faltante_ancla=anchor.ndwi is None, faltante_post=len(post)<2)
    causes = []
    if anchor.ndwi is None:
        causes.append("ndwi_ancla_ausente")
    if len(post) < 2:
        causes.append("menos_2_fechas_post")
    r.update(motivo=";".join(causes) if causes else "ok", calculable=not causes,
             contraste_ndwi=mean-anchor.ndwi if not causes else None)
    return r


def summaries(rows, dimension):
    result = []
    categories = sorted({r[dimension] for r in rows})
    for window in VENTANAS:
        for cat in ["todas", *categories]:
            sub = [r for r in rows if r["ventana"] == window and (cat == "todas" or r[dimension] == cat)]
            good = [r for r in sub if r["calculable"]]
            result.append(dict(ventana=window, categoria=cat, n_parcelas=len(sub), n_calculables=len(good),
                               n_ausentes=len(sub)-len(good), n_ancla_ausente=sum(bool(r["faltante_ancla"]) for r in sub),
                               n_post_insuficiente=sum(bool(r["faltante_post"]) for r in sub),
                               n_intervalo_truncado=sum(bool(r["intervalo_truncado"]) for r in sub),
                               n_maximo_en_borde=sum(bool(r["maximo_en_borde"]) for r in sub),
                               n_meseta_45_dias=sum(bool(r["meseta_45_dias"]) for r in sub),
                               fechas_post_min=min((r["n_fechas_post"] for r in sub),default=None),
                               fechas_post_mediana=median([r["n_fechas_post"] for r in sub]) if sub else None,
                               contraste_min=min((r["contraste_ndwi"] for r in good),default=None),
                               contraste_mediana=median([r["contraste_ndwi"] for r in good]) if good else None,
                               contraste_max=max((r["contraste_ndwi"] for r in good),default=None)))
    return result


def variation(rows):
    out = []
    for window in VENTANAS:
        for field in ["contraste_ndwi", "ndwi_ancla", "ndwi_media_post", "ndwi_mediana_mas_menos15", "ndvi_max"]:
            sub = [r for r in rows if r["ventana"]==window and r[field] is not None]
            values = [r[field] for r in sub]
            mean = math.fsum(values)/len(values) if values else None
            total = math.fsum((v-mean)**2 for v in values) if values else 0
            within = 0.
            for mun in {r["municipio"] for r in sub}:
                v = [r[field] for r in sub if r["municipio"]==mun]
                m = math.fsum(v)/len(v)
                within += math.fsum((x-m)**2 for x in v)
            out.append(dict(ventana=window,variable=field,n=len(values),
                            minimo=min(values) if values else None, maximo=max(values) if values else None,
                            desviacion=math.sqrt(total/len(values)) if values else None,
                            fraccion_variacion_dentro_municipio=within/total if total else None,
                            uso_rendimiento=False))
    return out


def reconcile(rows, t06, rasgos):
    lookup = {r["ID_POLIGONO"]:r for r in t06}
    if len(lookup)!=len(t06):
        raise ValueError("T06 duplicada")
    anchors = {r["ID_POLIGONO"]:r["fecha_maximo_observado"] for r in rasgos if r["sensor"]=="Sentinel-2"}
    out=[]
    for r in rows:
        pid,w=r["id_parcela"],r["ventana"]
        for key,col in [("ndvi_max",f"s2_ndvi_max_{w}"),
                        ("ndwi_mediana_mas_menos15",f"s2_ndwi_en_maximo_{w}"),
                        ("n_capturas",f"s2_capturas_{w}")]:
            actual=r[key];expected=number(lookup[pid][col],col)
            delta=abs(actual-expected) if actual is not None and expected is not None else None
            ok=(actual is None and expected is None) or (delta is not None and delta<=1e-9)
            out.append(dict(id_parcela=pid,ventana=w,variable=col,calculado=actual,publicado_T06=expected,
                            diferencia=delta,coincide=ok))
            if not ok:raise ValueError(f"No reproduce {col}: {pid}")
        if w=="abr_oct" and str(r["fecha_maximo"])!=anchors[pid]:
            raise ValueError("Fecha del máximo no reproduce T06")
    return out


def csv_write(path,rows):
    if not rows:raise ValueError("Entrega vacía")
    with Path(path).open("w",encoding="utf-8",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({k:(format(v,".17g") if isinstance(v,float) else v) for k,v in row.items()})


def json_write(path,obj):
    Path(path).write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+"\n",encoding="utf-8")


def validate_design(d):
    required={"schema":"t15_D1_ndwi_factibilidad_v1","sensor":"Sentinel-2",
              "nubosidad_max_pct":5,"min_capturas_NDVI":5,"post_dias_inclusivos":[15,45],
              "min_fechas_post_distintas":2,"interpolacion_NDWI":False,"seleccion_por_y":False,
              "ventanas":{w:[v.isoformat(),CORTE.isoformat()] for w,v in VENTANAS.items()}}
    for key,value in required.items():
        if d.get(key)!=value:raise ValueError("Diseño incompatible con implementación: "+key)


def run(raw_dir, output, root=ROOT):
    output=Path(output)
    if output.exists():raise FileExistsError("Destino existente; usar otro nombre")
    design_path=root/"registro/t15_d1/diseno.json"
    design=json.loads(design_path.read_text(encoding="utf-8"))
    validate_design(design)
    for rel,expected in design["fuentes_sha256"].items():
        p=Path(raw_dir)/Path(rel).name if rel.startswith("data/raw/") else root/rel
        if sha(p)!=expected:raise ValueError(f"Fuente distinta al diseño: {rel}")
    meta=catalogue(read_csv(root/"registro/t07/catalogo_base.csv"))
    if len(meta)!=197 or sum(m["conjunto"]=="ENTRENAMIENTO" for m in meta.values())!=138:
        raise ValueError("Población distinta de 197/138/59")
    groups,sensor_counts=observations(Path(raw_dir)/RAW,meta)
    rows=[]
    for pid in sorted(meta):
        for w,start in VENTANAS.items():
            rows.append(dict(**meta[pid],sensor="Sentinel-2",ventana=w,**profile(groups[pid],start)))
    conc=reconcile(rows,read_csv(root/"registro/t06/variables_satelitales.csv"),
                   read_csv(root/"registro/t06/rasgos_observables.csv"))
    result={"version":VERSION,"n_ids":len(meta),"n_perfiles":len(rows),"modelos_ajustados":0,
            "uso_rendimiento":False,"nuevas_predicciones_59":0,"sensores_inventario_basico":sensor_counts,
            "Planet_NDWI":"no_proporcionado_en_PRO","conciliacion_T06_comparaciones":len(conc),
            "max_delta_conciliacion_T06":max(r["diferencia"] or 0 for r in conc),
            "perfiles_calculables":sum(r["calculable"] for r in rows),
            "ambas_ventanas_contraste_exacto":sum(rows[k]["contraste_ndwi"]==rows[k+1]["contraste_ndwi"]
                                                and rows[k]["contraste_ndwi"] is not None for k in range(0,len(rows),2)),
            "estado":"factibilidad_descriptiva_revision_pendiente_no_promocion"}
    labels={"id_parcela":"ID original; no predictor", "municipio":"Metadato territorial original; no rendimiento",
            "conjunto":"Pertenencia original: ENTRENAMIENTO/PREDICCION; no usa el valor de la etiqueta",
            "sensor":"Sensor único del contraste: Sentinel-2", "ventana":"Periodo candidato, no etapa agronómica",
            "n_capturas":"Fechas con NDVI y nube<=5, dentro de la ventana/corte",
            "fecha_maximo":"Primera fecha del máximo de la mediana centrada de tres capturas",
            "ndvi_max":"Valor del máximo suavizado; no confirma pico agronómico",
            "amplitud_ndvi":"Máximo suavizado menos mínimo de curva anterior o igual al máximo",
            "n_empates_maximo":"Número de fechas empatadas exactamente en el máximo",
            "maximo_en_borde":"Máximo en primera/última captura válida",
            "meseta_45_dias":"Fechas a <=5% de amplitud del máximo separadas por >=45 días, regla T06",
            "ndwi_ancla":"NDWI original en fecha exacta del máximo; no mediana ±15",
            "ndwi_mediana_mas_menos15":"Control de reproducción T06; no un predictor nuevo elegible",
            "n_fechas_post":"Fechas distintas válidas con NDWI entre +15 y +45 días y <=corte",
            "fechas_post":"Fechas exactas utilizadas separadas por punto y coma",
            "primera_post":"Primera fecha utilizada en media posterior", "ultima_post":"Última fecha utilizada en media posterior",
            "intervalo_truncado":"Máximo+45 días posterior al corte; no observa intervalo nominal completo",
            "amplitud_temporal_post_dias":"Separación entre primera y última fecha posterior; una fecha: cero",
            "hueco_max_post_con_bordes_dias":"Mayor hueco incluyendo bordes [+15,min(+45,corte)]",
            "ndwi_media_post":"Media aritmética por observación; un valor diagnóstico puede existir con sólo una fecha",
            "contraste_ndwi":"Media posterior menos ancla, sólo si >=5 capturas NDVI, ancla y >=2 fechas post",
            "calculable":"Cumple soporte mínimo; no es confianza ni elegibilidad del modelo",
            "motivo":"ok o causa(s) explícitas; no se rellena un vacío",
            "faltante_ancla":"Ancla sin NDWI; ausente si no se define máximo",
            "faltante_post":"Menos de dos fechas posteriores; ausente si no se define máximo"}
    dictionary=[dict(columna=k,significado=labels[k],unidad=("días" if k.endswith("dias") else
                   "fecha ISO" if k.startswith("fecha") or k in {"primera_post","ultima_post"} else
                   "índice adimensional" if k.startswith("ndwi") or k in {"ndvi_max","amplitud_ndvi","contraste_ndwi"} else
                   "conteo" if k.startswith("n_") else "categoría/booleano"),
                   vacio="No aplicable o soporte insuficiente; nunca cero implícito") for k in rows[0]]
    output.parent.mkdir(parents=True,exist_ok=True)
    temp=Path(tempfile.mkdtemp(prefix=".d1-",dir=output.parent))
    try:
        csv_write(temp/"perfil_ndwi_postpico.csv",rows)
        csv_write(temp/"resumen_conjunto.csv",summaries(rows,"conjunto"))
        csv_write(temp/"resumen_municipio.csv",summaries(rows,"municipio"))
        csv_write(temp/"conciliacion_t06.csv",conc)
        csv_write(temp/"variacion_sin_y.csv",variation(rows))
        csv_write(temp/"diccionario.csv",dictionary)
        json_write(temp/"resumen.json",result)
        json_write(temp/"manifest.json",dict(version=VERSION,diseno_sha256=sha(design_path),
                   fuentes_sha256=design["fuentes_sha256"],
                   archivos_sha256={p.name:sha(p) for p in sorted(temp.iterdir())},
                   codigo_sha256={"scripts/t15_ndwi_factibilidad.py":sha(Path(__file__))},
                   estado="tecnico_por_verificar_revision_humana_pendiente",modelos_ajustados=0))
        if output.exists():raise FileExistsError("El destino apareció durante el cálculo")
        os.rename(temp,output)
    except BaseException:
        shutil.rmtree(temp,ignore_errors=True)
        raise
    return result


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--datos",type=Path,default=ROOT/"data/raw/DATASET_RETO_AGRO_2026")
    ap.add_argument("--salida",type=Path,required=True)
    args=ap.parse_args()
    print(json.dumps(run(args.datos,args.salida),ensure_ascii=False,indent=2))


if __name__=="__main__":
    main()
