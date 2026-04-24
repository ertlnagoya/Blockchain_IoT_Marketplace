FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml README.md ./
COPY publisher ./publisher
COPY schemas ./schemas
COPY policy ./policy
COPY audit ./audit
COPY examples ./examples

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
        fastapi \
        uvicorn \
        'pydantic>=2' \
        pydantic-settings \
        'httpx>=0.28' \
        paho-mqtt \
        'cryptography>=42' \
        python-multipart

EXPOSE 8080

CMD ["uvicorn", "publisher.app.main:app", "--host", "0.0.0.0", "--port", "8080"]
