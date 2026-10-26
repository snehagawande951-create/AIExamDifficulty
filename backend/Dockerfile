# ==============================================================================
# Production Dockerfile for AI Exam Analyzer Backend (FastAPI + Python 3.11)
# ==============================================================================
FROM python:3.11-slim AS builder

WORKDIR /build

# Install build dependencies for C-extensions (PyMuPDF, Argon2, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Final Runtime Image
FROM python:3.11-slim AS runner

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    PORT=8000 \
    HOST=0.0.0.0

# Install runtime shared libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed Python packages from builder
COPY --from=builder /install /usr/local

# Create non-root application user
RUN groupadd -r appgroup && useradd -r -g appgroup -u 1001 appuser

# Create necessary persistent runtime directories
RUN mkdir -p /app/data /app/backend/uploads /app/backend/reports /app/models/registry \
    && chown -R appuser:appgroup /app

# Copy application source code and models
COPY backend /app/backend
COPY models /app/models
COPY data /app/data
COPY research /app/research

RUN chown -R appuser:appgroup /app

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; sys_exit = 0 if urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health').getcode() == 200 else 1; exit(sys_exit)"

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
