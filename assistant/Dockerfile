FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml README.md ./
COPY assistant ./assistant
COPY examples ./examples

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir fastapi uvicorn pydantic pydantic-settings httpx

EXPOSE 8090

CMD ["uvicorn", "assistant.app.main:app", "--host", "0.0.0.0", "--port", "8090"]
