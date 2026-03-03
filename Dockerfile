# syntax=docker/dockerfile:1.4
# Enable BuildKit features
# Usar para build multi-plataforma: docker buildx build --platform linux/amd64,linux/arm64 -t usuario/imagem:latest .

# ============================================================================
# Stage 1: Builder - instala dependências Python
# ============================================================================
FROM --platform=$BUILDPLATFORM python:3.11-slim AS builder

ARG TARGETARCH
ARG TARGETOS

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Copia apenas requirements primeiro para aproveitar cache
COPY requirements.txt /app/requirements.txt

# Instala dependências em diretório separado
RUN pip install --target=/install -r /app/requirements.txt

# ============================================================================
# Stage 2: Runtime - imagem final otimizada
# ============================================================================
FROM python:3.11-slim

# Definir plataforma de runtime (para imagens multi-arch)
ARG TARGETARCH
ARG TARGETOS

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Instala dependências do sistema (tesseract)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        tesseract-ocr \
        tesseract-ocr-por \
        # Fonts para rendering de PDFs
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copia dependências Python do stage builder
COPY --from=builder /install /usr/local/lib/python3.11/site-packages

WORKDIR /app

# Copia código da aplicação
COPY . /app

# Cria diretório de dados e define permissões
RUN mkdir -p /data && \
    chown -R nobody:nogroup /data && \
    chown -R nobody:nogroup /app

WORKDIR /data

VOLUME ["/data"]

USER nobody

ENTRYPOINT ["python", "/app/boleto_extract.py"]
CMD ["--path_arquivos", "/data", "--path_base_contas", "/data/dbcodigocontas.csv"]
