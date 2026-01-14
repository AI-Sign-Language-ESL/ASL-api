FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV ENVIRONMENT=PROD
ENV SECRET_KEY=docker-build-secret
ENV ALLOWED_HOSTS=localhost
ENV PYTHONPATH=/app/src

RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    curl \
    ffmpeg \  
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY req.txt .
RUN pip install --upgrade pip && pip install -r req.txt

COPY src/ /app/src/

EXPOSE 8000

CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "tafahom_api.asgi:application"]
