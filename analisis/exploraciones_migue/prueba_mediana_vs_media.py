"""Prueba (no decide nada): ¿qué tan seguro es que la mediana municipal le gane a la media en la calificación real?

Usa las predicciones fuera del entrenamiento de T08 (media_mun__resp_grupo y mediana_mun__resp_grupo, subconjunto
sin_respaldo) y calcula, por escenario: parcelas que mejoran / empeoran, Wilcoxon por parcela (supone independencia),
probabilidad de mejora con bootstrap por celdas CHIRPS (20 000 réplicas) y ΔMAE por municipio. Además simula 20 000
"evaluaciones de FIRA" de 59 parcelas con la composición real por municipio (29/14/7/4/4 + Nanacamilpa, donde media y
mediana coinciden), eligiendo celdas al azar dentro de cada municipio y parcelas dentro de la celda.

Uso (desde la raíz del repo del equipo):
    python prueba_mediana_vs_media.py scripts RUTA/DATASET registro/t08 registro/t03/particiones.csv
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import wilcoxon

sys.path.insert(0, str(Path(sys.argv[1]).resolve()))
from t08_referencias import cargar  # noqa: E402

d = cargar(Path(sys.argv[2]))
T08 = Path(sys.argv[3])
celda = pd.read_csv(sys.argv[4]).drop_duplicates("ID_POLIGONO").set_index("ID_POLIGONO").celda_chirps
media = pd.read_csv(T08 / "predicciones_oof_referencias_media_mun__resp_grupo.csv")
mediana = pd.read_csv(T08 / "predicciones_oof_referencias_mediana_mun__resp_grupo.csv")
COMP = {"Chignahuapan": 29, "Calpulalpan": 14, "Singuilucan": 7, "Cuautepec de Hinojosa": 4, "Almoloya": 4}

for esc in ["A", "B"]:
    a = media[media.escenario == esc].set_index(["ID_POLIGONO", "repeticion"])
    b = mediana[mediana.escenario == esc].set_index(["ID_POLIGONO", "repeticion"]).loc[a.index]
    m = a.fuente == "municipio"
    dpar = ((b.prediccion - b.real).abs() - (a.prediccion - a.real).abs())[m].groupby(level=0).mean()
    g = pd.DataFrame({"d": dpar, "c": celda.reindex(dpar.index).values}).groupby("c").d
    s, n = g.sum().values, g.size().values
    k = np.random.RandomState(20261006).randint(0, len(s), (20000, len(s)))
    bs = s[k].sum(1) / n[k].sum(1)
    print(f"Escenario {esc}: ΔMAE {dpar.mean():+.4f} | mejoran {(dpar < 0).sum()}, empeoran {(dpar > 0).sum()} | "
          f"Wilcoxon p={wilcoxon(dpar[dpar != 0]).pvalue:.3f} | P(mediana mejor, celdas)={(bs < 0).mean():.0%} | "
          f"IC95 [{np.percentile(bs, 2.5):+.4f}, {np.percentile(bs, 97.5):+.4f}]")
    print("   por municipio:", dpar.groupby(d.municipio.reindex(dpar.index)).mean().round(3).to_dict())
    if esc == "A":
        mun, cel = d.municipio.reindex(dpar.index), celda.reindex(dpar.index)
        rng, sims = np.random.RandomState(1), []
        for _ in range(20000):
            tot = []
            for mm, nm in COMP.items():
                x, c = dpar[mun == mm], cel[mun == mm]
                elegidas = []
                while len(elegidas) < nm:
                    cc = rng.choice(c.unique())
                    elegidas += list(rng.choice(x[c == cc].values, size=min(nm - len(elegidas), int((c == cc).sum())), replace=True))
                tot += elegidas
            sims.append(np.mean(tot + [0.0]))
        sims = np.array(sims)
        print(f"   simulación FIRA (59): la mediana gana {(sims < 0).mean():.0%}, pierde {(sims > 0).mean():.0%} | "
              f"típico {np.median(sims):+.4f} | 90 % entre {np.percentile(sims, 5):+.4f} y {np.percentile(sims, 95):+.4f}")
