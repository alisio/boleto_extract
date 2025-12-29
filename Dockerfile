FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        tesseract-ocr \
        tesseract-ocr-por \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY . /app

RUN mkdir -p /data
WORKDIR /data

VOLUME ["/data"]

ENTRYPOINT ["python", "/app/boleto_extract.py"]
CMD ["--path_arquivos", "/data", "--path_base_contas", "/data/dbcodigocontas.csv"]
