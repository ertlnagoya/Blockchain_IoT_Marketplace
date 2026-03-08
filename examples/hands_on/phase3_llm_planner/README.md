# Phase 3 LLM Planner Hands-on Program

## Goal

Send a request to `/assistant/plan` while the assistant is running in `llm` mode, then verify that a structured plan is returned.

This exercise is designed for the `codex/llm-planner-minimal` branch.

## Files

- `problem_program.py`
- `answer_program.py`

## Related example files

- `../../phase3_request_park_safety.json`
- `../../phase3_request_station_warning.json`
- `../../../.env.local.example`

## Recommended hands-on flow

1. Start the assistant with the stub provider:

```bash
ASSISTANT_PLANNER_MODE=llm \
ASSISTANT_PLANNER_NAME=llm-planner-stub-v1 \
ASSISTANT_LLM_PROVIDER=stub \
uvicorn assistant.app.main:app --host 0.0.0.0 --port 8090
```

Docker Compose example:

```bash
docker compose -f infra/docker-compose.yml --profile assistant up --build -d assistant
```

2. Run the problem program:

```bash
python3 examples/hands_on/phase3_llm_planner/problem_program.py
```

Expected:

```json
{
  "planner_name": "llm-planner-stub-v1",
  "target_area": "park-north",
  "watch_events": ["possible_littering", "suspicious_activity"],
  "planner_diagnostics": {
    "label": "OK",
    "color_hint": "green",
    "code": "llm_plan_generated",
    "category": "success",
    "user_message": "LLM planner generated a plan successfully."
  }
}
```

3. Try the English request:

```bash
python3 examples/hands_on/phase3_llm_planner/problem_program.py \
  --request-file examples/phase3_request_station_warning.json
```

Expected:

```json
{
  "planner_name": "llm-planner-stub-v1",
  "target_area": "station-front",
  "watch_events": ["suspicious_activity"],
  "planner_diagnostics": {
    "label": "OK",
    "color_hint": "green",
    "code": "llm_plan_generated",
    "category": "success",
    "user_message": "LLM planner generated a plan successfully."
  }
}
```

4. If needed, compare with the answer program:

```bash
python3 examples/hands_on/phase3_llm_planner/answer_program.py
```

## Real API path

To test with an actual OpenAI-compatible API:

```bash
cp .env.local.example .env.local
docker compose -f infra/docker-compose.yml --profile assistant-llm up --build -d assistant-llm
```

Then run the same program again.

## Local HTTP mock path

If you want to exercise the `openai_compatible` HTTP path without a real external API:

```bash
uvicorn examples.phase3_llm_mock_server:app --host 127.0.0.1 --port 18000
```

In another terminal:

```bash
source examples/phase3_llm_mock.env.example
uvicorn assistant.app.main:app --host 0.0.0.0 --port 8090
```

Docker Compose alternative:

```bash
docker compose -f infra/docker-compose.yml --profile llm-mock up --build -d llm-mock
source examples/phase3_llm_mock.env.example
uvicorn assistant.app.main:app --host 0.0.0.0 --port 8090
```

Then run:

```bash
python3 examples/hands_on/phase3_llm_planner/answer_program.py
```

Expected:

```json
{
  "planner_name": "llm-planner-mock-http-v1",
  "target_area": "park-north",
  "planner_diagnostics": {
    "label": "OK",
    "color_hint": "green",
    "code": "llm_plan_generated",
    "category": "success",
    "user_message": "LLM planner generated a plan successfully."
  }
}
```

## Pytest for the exercise

The repository includes a reusable pytest file for this exercise:

```bash
pytest -q tests/test_phase3_llm_hands_on_program.py
```

By default, it validates `answer_program.py`.

After completing the TODOs in `problem_program.py`, learners can run:

```bash
PHASE3_LLM_HANDS_ON_MODULE=examples.hands_on.phase3_llm_planner.problem_program \
pytest -q tests/test_phase3_llm_hands_on_program.py
```

## Troubleshooting

- `HTTP Error 500`:
  - check `ASSISTANT_LLM_API_KEY`
  - check `ASSISTANT_LLM_API_BASE_URL`
  - check `ASSISTANT_LLM_MODEL`
- plan is returned but `planner_name` is not the LLM planner:
  - fallback may have happened
  - check `planner_diagnostics.code`, `planner_diagnostics.category`, `planner_diagnostics.label`, `planner_diagnostics.color_hint`, and whether the model returned valid JSON
- `station-front` is not returned:
  - make sure you are on branch `codex/llm-planner-minimal`
