from __future__ import annotations

from datetime import UTC, datetime, timedelta

from assistant.app.models import EvaluationResult, EventRecord, ExecutionPlan


class EventEvaluator:
    def evaluate(self, plan: ExecutionPlan, events: list[EventRecord], now: datetime | None = None) -> EvaluationResult:
        now = now or datetime.now(UTC)
        earliest = now - timedelta(minutes=plan.time_window_minutes)

        matched_counts = {event_name: 0 for event_name in plan.watch_events}

        for event in events:
            if event.location != plan.target_area:
                continue
            if event.event_type not in matched_counts:
                continue
            if event.ts < earliest:
                continue
            matched_counts[event.event_type] += 1

        triggered = False
        reasons: list[str] = []
        for event_name, required in plan.thresholds.items():
            count = matched_counts.get(event_name, 0)
            if count >= required:
                triggered = True
                reasons.append(f"{event_name}={count} >= {required}")

        if not reasons:
            reasons.append("threshold_not_met")

        return EvaluationResult(
            triggered=triggered,
            matched_counts=matched_counts,
            reason=", ".join(reasons),
        )
