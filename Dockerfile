FROM python:3.12.15-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /proyecto
RUN apt-get update \
    && apt-get install -y --no-install-recommends libexpat1 \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN python -m pip install --no-cache-dir --only-binary=:all: -r requirements.txt \
    && python -m pip check
COPY scripts/verificar_entorno.py scripts/verificar_entorno.py

CMD ["python", "scripts/verificar_entorno.py"]
