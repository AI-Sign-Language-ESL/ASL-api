FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/src

# System dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    curl \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# App directory
WORKDIR /app/src

# Install Python dependencies
COPY req.txt /app/
RUN pip install --upgrade pip && pip install -r /app/req.txt

# Copy project
COPY src/ /app/src/

# Default command (overridden by docker-compose)
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "tafahom_api.asgi:application"]
