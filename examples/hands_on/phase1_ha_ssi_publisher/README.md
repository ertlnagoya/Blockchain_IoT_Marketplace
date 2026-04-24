# Phase 1 HA x SSI Publisher Hands-on Program

## Goal

Send a temperature event to `/simulate/publish` and confirm an `allowed` result.

## Files

- `problem_program.py`
- `answer_program.py`

## Run

```bash
python3 examples/hands_on/phase1_ha_ssi_publisher/problem_program.py --purpose research
```

Expected:

```json
{"status":"allowed","dataset_id":"home/env/temperature"}
```
