# Phase 2 Hands-on Sample Program

This directory contains two small programs for the `Environment and Disaster Event Sharing` hands-on.

## Files

- `problem_program.py`
  - exercise version with `TODO` sections
- `answer_program.py`
  - reference solution

## Goal

The programs send a `flood_risk_high` event to the local Publisher and check whether it becomes `allowed` or `denied` depending on `purpose`.

## Related example files

- `../../consent_flood_risk_high.json`
- `../../payload_flood_risk_high.json`

## Recommended hands-on flow

1. Start the publisher stack:

```bash
docker compose -f infra/docker-compose.yml up --build -d
```

2. Register the consent:

```bash
curl -X POST http://localhost:8080/consents \
  -H 'Content-Type: application/json' \
  -d @examples/consent_flood_risk_high.json
```

3. Read `problem_program.py` and complete the `TODO` sections.

4. Run the program:

```bash
python3 examples/hands_on/phase2_environment_disaster/problem_program.py --purpose disaster_response
```

Expected result:

```json
{"status":"allowed","dataset_id":"home/event/flood_risk_high"}
```

5. Try a denied case:

```bash
python3 examples/hands_on/phase2_environment_disaster/problem_program.py --purpose advertising
```

Expected result:

```json
{"status":"denied","dataset_id":"home/event/flood_risk_high","reason":"no_matching_consent"}
```

6. If needed, compare with the reference solution:

```bash
python3 examples/hands_on/phase2_environment_disaster/answer_program.py --purpose disaster_response
```

## What learners should understand

- how a Phase 2 event is represented as JSON
- how `topic`, `payload`, and `purpose` are combined for `/simulate/publish`
- how the same event becomes `allowed` or `denied` depending on Consent VC
