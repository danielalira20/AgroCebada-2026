FROM python:3.12.15-slim-bookworm

# PYTHONUTF8=1: Python lee y escribe texto en UTF-8 en cualquier equipo,
# sin depender de la codificación del sistema (evita el problema cp1252 de Windows).
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONUTF8=1

WORKDIR /proyecto

# git: los scripts de T04 y T07 comprueban fuentes contra la revisión identificada.
# safe.directory: permite usar git sobre la carpeta del proyecto montada desde
# Windows o Mac, cuyo dueño no coincide con el usuario del contenedor.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libexpat1 git \
    && rm -rf /var/lib/apt/lists/* \
    && git config --system --add safe.directory '*'

COPY requirements.txt .
RUN python -m pip install --no-cache-dir --only-binary=:all: -r requirements.txt \
    && python -m pip check
COPY scripts/verificar_entorno.py scripts/verificar_entorno.py

# Sin argumentos ejecuta la comprobación del entorno de T01.
# Para trabajar con el proyecto se monta la carpeta en /proyecto (ver README).
CMD ["python", "scripts/verificar_entorno.py"]
