# ------------------------------
# Base image
# ------------------------------
FROM python:3.11-slim

# ------------------------------
# Environment
# ------------------------------
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# ------------------------------
# System dependencies
# ------------------------------
RUN apt-get update && apt-get install -y \
    ffmpeg \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# ------------------------------
# Work directory
# ------------------------------
WORKDIR /app

# ------------------------------
# Install Python dependencies
# ------------------------------
COPY req.txt /app/req.txt
RUN pip install --upgrade pip && \
    pip install -r req.txt

# ------------------------------
# Copy project
# ------------------------------
COPY . /app

# ------------------------------
# Expose port
# ------------------------------
EXPOSE 8000

# ------------------------------
# Run ASGI server (WebSocket ✅)
# ------------------------------
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "tafahom_api.asgi:application"]
