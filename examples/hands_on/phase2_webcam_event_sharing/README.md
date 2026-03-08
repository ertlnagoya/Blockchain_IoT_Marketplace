# Phase 2 Webcam Event Sharing Hands-on Program

## Goal

Send a `possible_littering` event to `/simulate/publish` and compare `allowed` and `denied` by purpose.

## Run

```bash
python3 examples/hands_on/phase2_webcam_event_sharing/problem_program.py --purpose community_cleaning
```

Expected:

```json
{"status":"allowed","dataset_id":"home/event/possible_littering"}
```
