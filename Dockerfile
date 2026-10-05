FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /proyecto
COPY requirements.txt .
RUN python -m pip install --no-cache-dir -r requirements.txt
COPY scripts/verificar_entorno.py scripts/verificar_entorno.py

CMD ["python", "scripts/verificar_entorno.py"]
