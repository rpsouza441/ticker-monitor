# Multi-stage Dockerfile otimizado para desenvolvimento

# Stage 1: Builder - compila dependências
FROM python:3.11-slim as builder

WORKDIR /app

# Instalar build essentials
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements
COPY requirements.txt .

# Criar venv e instalar dependências
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --upgrade pip setuptools wheel && \
    pip install -r requirements.txt

# Stage 2: Runtime - imagem final pequena
FROM python:3.11-slim

WORKDIR /app

# Instalar apenas dependências de runtime (não build)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copiar venv do builder
COPY --from=builder /opt/venv /opt/venv

# Ativar venv
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app

# Copiar código da aplicação
COPY . .

# Criar pastas necessárias
RUN mkdir -p logs && \
    chmod +x /app/src/scheduler/consumer.py

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "from src.main import health_check; import json; result = health_check(); exit(0 if result.get('healthy') else 1)" || exit 1

# Executar consumer por padrão
CMD ["python", "-m", "src.scheduler.consumer"]
