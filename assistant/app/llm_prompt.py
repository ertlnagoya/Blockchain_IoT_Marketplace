from __future__ import annotations

from assistant.app.plan_validator import ALLOWED_ACTIONS, ALLOWED_AREAS, ALLOWED_EVENTS


def build_system_prompt() -> str:
    allowed_events = ", ".join(sorted(ALLOWED_EVENTS))
    allowed_actions = ", ".join(sorted(ALLOWED_ACTIONS))
    allowed_areas = ", ".join(sorted(ALLOWED_AREAS))

    return f"""
You are the planner component of an IoT public-safety assistant.
Return JSON only.
Do not include markdown, commentary, or explanation.

The JSON must be compatible with this structure:
{{
  "intent": "monitor_public_safety",
  "target_area": "<allowed area or unknown-area>",
  "time_window_minutes": 30,
  "watch_events": ["<allowed event>"],
  "thresholds": {{"<allowed event>": <integer>}},
  "actions": [
    {{
      "action_type": "<allowed action>",
      "target": "<string>",
      "parameters": {{}}
    }}
  ]
}}

Allowed events: {allowed_events}
Allowed actions: {allowed_actions}
Allowed areas: {allowed_areas}

Constraints:
- output JSON only
- use integers for thresholds
- never invent event names, action names, or areas outside the allow lists
- use "unknown-area" when the request does not specify a supported area
- prefer the smallest valid plan that satisfies the request
- if the request asks to notify someone, use action_type "send_notification"
- if the request asks to turn on lights, use action_type "light_on"
- if the request asks to display a warning, use action_type "show_warning"
""".strip()


def build_user_prompt(request_text: str) -> str:
    return f"""
Convert the following human request into the required JSON plan.

request_text:
{request_text}
""".strip()
