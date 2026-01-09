# ======================================================
# Base image (Python + uv)
# ======================================================
FROM ghcr.io/astral-sh/uv:alpine3.22 AS base

ENV UV_PYTHON_INSTALL_DIR="/usr/local/share/uv/python" \
    VIRTUAL_ENV="/usr/local/venv" \
    PATH="/usr/local/venv/bin:${PATH}"

# Create virtual environment (stable version for prod)
RUN uv venv -p 3.12 /usr/local/venv


# ======================================================
# Build stage
# ======================================================
FROM base AS build

WORKDIR /app

# Copy only dependency files first (better caching)
COPY pyproject.toml uv.lock MANIFEST.in ./

# Then copy source
COPY src src/

ARG VERSION=0.0.0
ENV SETUPTOOLS_SCM_PRETEND_VERSION="${VERSION}"

# Install deps, collect static, build wheel
RUN uv sync --frozen --active && \
    python src/manage.py collectstatic --noinput && \
    uv build


# ======================================================
# Runtime stage (small & secure)
# ======================================================
FROM base AS runtime

# -----------------------------
# Django runtime config
# -----------------------------
ENV DJANGO_SETTINGS_MODULE=tafahom.settings \
    DJANGO_ENV=production \
    PYTHONUNBUFFERED=1

# -----------------------------
# OCI labels (important for CI/CD)
# -----------------------------
ARG SOURCE_URL=https://github.com/your-org/tafahom-backend \
    VCS_REF=HEAD \
    VERSION=0.0.0 \
    LICENSE=MIT

LABEL org.opencontainers.image.title="TAFAHOM Backend" \
    org.opencontainers.image.description="TAFAHOM – Sign Language Translation Backend" \
    org.opencontainers.image.source="${SOURCE_URL}" \
    org.opencontainers.image.version="${VERSION}" \
    org.opencontainers.image.revision="${VCS_REF}" \
    org.opencontainers.image.licenses="${LICENSE}"

# -----------------------------
# Install runtime deps
# -----------------------------
RUN apk add --no-cache \
    tzdata \
    bash

# Install built wheel
COPY --from=build /app/dist /app/dist
RUN uv pip install /app/dist/tafahom-*.whl

# -----------------------------
# Create non-root user
# -----------------------------
RUN adduser -Ds /usr/bin/bash tafahom
USER tafahom:tafahom

# -----------------------------
# Expose ASGI port
# -----------------------------
EXPOSE 8000

# -----------------------------
# ASGI entrypoint (Channels)
# -----------------------------
ENTRYPOINT ["daphne"]
CMD ["tafahom.asgi:application", "-b", "0.0.0.0", "-p", "8000"]
