# HUSKYLENS2 Mock Hands-on Program

## Goal

Create a mock HUSKYLENS2 event file under `mediator-owner/raw_data/output`.

## Files

- `problem_program.py`
- `answer_program.py`

## Run

```bash
python3 examples/hands_on/huskylens2_mock/problem_program.py \
  --output-dir mediator-owner/raw_data/output
```

Expected:

- a file like `301_huskylens_mock_*.txt` is created
- the file contains a JSON event for HUSKYLENS2 detection
