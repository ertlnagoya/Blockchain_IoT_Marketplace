# Hands-on Sample Programs

This directory contains exercise programs for the hands-on materials.

Each hands-on is organized in its own subdirectory and usually includes:

- `problem_program.py`
  - exercise version with `TODO`
- `answer_program.py`
  - reference solution
- `README.md`
  - what to run, in which order, and what output to expect

## Available hands-on sample programs

- `huskylens2_mock`
  - generate a mock HUSKYLENS2 event file
- `webcam_littering_mock`
  - generate a mock USB webcam event file
- `mobile_viewer`
  - build and verify the smartphone access URL
- `phase1_ha_ssi_publisher`
  - send a Phase 1 temperature event to `/simulate/publish`
- `phase2_environment_disaster`
  - send a `flood_risk_high` event to `/simulate/publish`
- `phase2_webcam_event_sharing`
  - send a `possible_littering` event to `/simulate/publish`
- `local_vlm_distribution`
  - analyze a webcam frame with a local model (`/semantic/analyze`) and distribute it
