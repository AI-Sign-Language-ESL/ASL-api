FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# System deps
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# App directory (IMPORTANT)
WORKDIR /app/src

# Install Python dependencies
COPY req.txt /app/req.txt
RUN pip install --upgrade pip && pip install -r /app/req.txt

# Copy project
COPY src/ /app/src/

# Expose Daphne port
EXPOSE 8000

# Default command (can be overridden by docker-compose)
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "tafahom_api.asgi:application"]
