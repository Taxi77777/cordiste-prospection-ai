FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    TZ=Europe/Paris

WORKDIR /app

# Dépendances (couche cache)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Code applicatif
COPY app ./app
COPY scripts ./scripts

# Volume pour la base SQLite persistante
RUN mkdir -p /app/data
VOLUME ["/app/data"]

EXPOSE 8000

# Démarre l'API + le tableau de bord (le scheduler interne tourne dedans)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
