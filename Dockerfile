FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt ./requirements.txt
RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir -r requirements.txt

COPY src ./src
COPY dashboard ./dashboard
COPY scripts ./scripts
COPY migrations ./migrations
COPY alembic.ini ./alembic.ini
COPY artifacts/models/gameguard-if-v1 ./artifacts/models/gameguard-if-v1
RUN mkdir -p /app/data

EXPOSE 8000
CMD ["sh", "-c", "python -m gameguard.migrate && uvicorn gameguard.api:app --host 0.0.0.0 --port ${PORT:-8000}"]
