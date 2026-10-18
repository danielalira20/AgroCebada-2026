# Imagen de la app AgroCebada. Se construye desde la raíz del repo: docker build -t agrocebada-app app
# Los datos del reto NO van en la imagen: se montan como carpetas al correr el contenedor (ver README).
FROM python:3.12.15-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONUTF8=1

RUN useradd --create-home --uid 1000 agro
WORKDIR /app

COPY requirements.txt .
RUN python -m pip install --no-cache-dir --only-binary=:all: -r requirements.txt

COPY --chown=agro:agro . .
USER agro

EXPOSE 8501
CMD ["streamlit", "run", "app.py", "--server.address", "0.0.0.0", "--server.port", "8501"]
