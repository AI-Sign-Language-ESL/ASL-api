# ==========================
# Base Image
# ==========================
FROM python:3.11-slim

# ==========================
# Environment
# ==========================
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV ENVIRONMENT=PROD
ENV SECRET_KEY=docker-build-secret
ENV ALLOWED_HOSTS=localhost

# ==========================
# System deps
# ==========================
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# ==========================
# Working directory
# ==========================
WORKDIR /app

# ==========================
# Install dependencies
# ==========================
COPY req.txt .
RUN pip install --upgrade pip && pip install -r req.txt

# ==========================
# Copy project
# ==========================
COPY . .

# ==========================
# Collect static files
# ==========================

# ==========================
# Expose port
# ==========================
EXPOSE 8000

# ==========================
# Run ASGI server
# ==========================
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "tafahom_api.asgi:application"]
