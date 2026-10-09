from __future__ import annotations

from assistant.app.models import ActionCommand


class ActionActuator:
    def execute(self, actions: list[ActionCommand]) -> list[ActionCommand]:
        # Phase 3 minimal sample:
        # keep actions as-is and treat them as executed commands.
        return actions
