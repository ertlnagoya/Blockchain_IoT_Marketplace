FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml README.md ./
COPY publisher ./publisher
COPY schemas ./schemas
COPY policy ./policy
COPY audit ./audit

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir fastapi uvicorn pydantic pydantic-settings httpx paho-mqtt

EXPOSE 8080

CMD ["uvicorn", "publisher.app.main:app", "--host", "0.0.0.0", "--port", "8080"]
