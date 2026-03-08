# Phase 3 Assistant UI

A minimal React frontend for the IW3IP Phase 3 Regional Safety Assistant.

## What it shows

- natural-language request input
- `POST /assistant/plan`
- `POST /assistant/execute`
- `GET /assistant/executions`
- `planner_diagnostics` rendered as a badge and alert panel

## Local run

```bash
cd assistant-ui
npm install
npm run dev -- --host 0.0.0.0 --port 5173
```

Open:

- http://localhost:5173

Default API base URL:

- `http://localhost:8090`

## Docker Compose run

Start the assistant API:

```bash
docker compose -f infra/docker-compose.yml --profile assistant up --build -d assistant
```

Start the UI:

```bash
docker compose -f infra/docker-compose.yml --profile assistant-ui up --build -d assistant-ui
```

Open:

- http://localhost:4173

## One-command demo

If you also want the local mock LLM, use:

```bash
docker compose -f infra/docker-compose.yml --profile assistant-demo up --build -d
```

This starts:

- `assistant-demo`
- `llm-mock`
- `assistant-ui`

Open:

- http://localhost:4173

Stop:

```bash
docker compose -f infra/docker-compose.yml --profile assistant-demo down
```

## Notes

- The assistant API enables CORS for `localhost:5173`, `127.0.0.1:5173`, `localhost:4173`, and `127.0.0.1:4173` by default.
- If you run the UI from another origin, set `ASSISTANT_CORS_ORIGINS` for the assistant service.
