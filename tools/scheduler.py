import json
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

SCHEDULE_FILE = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "maintenance_schedule.json"
)
ET = ZoneInfo("America/New_York")

# A maintenance window overlapping peak demand loses this much capacity —
# flag it for postponement when forecast is above this threshold
POSTPONE_THRESHOLD_MW = 15_000


def evaluate_maintenance_schedule(
    forecast_peak_mw: float,
    forecast_peak_time: str,
) -> str:
    """Evaluate planned maintenance windows against the demand forecast.

    For each scheduled window, decide APPROVE or POSTPONE based on whether
    it overlaps with forecast peak demand. Returns decisions with reasoning.
    """
    try:
        with open(SCHEDULE_FILE) as f:
            schedule = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        return f"Maintenance schedule unavailable: {e}"

    windows = schedule.get("windows", [])
    if not windows:
        return "No maintenance windows scheduled."

    # Parse forecast peak time
    try:
        peak_dt = datetime.fromisoformat(forecast_peak_time.replace(" UTC", "+00:00"))
    except (ValueError, AttributeError):
        peak_dt = None

    lines = ["Maintenance schedule evaluation:"]
    decisions = {"APPROVE": 0, "POSTPONE": 0}

    for w in windows:
        unit       = w.get("unit", "Unknown unit")
        cap_mw     = w.get("capacity_mw", 0)
        date_str   = w.get("date", "")
        start_str  = w.get("start_time", "00:00")
        end_str    = w.get("end_time", "23:59")
        desc       = w.get("description", "")

        # Parse window times
        try:
            start_dt = datetime.fromisoformat(f"{date_str}T{start_str}").replace(tzinfo=ET)
            end_dt   = datetime.fromisoformat(f"{date_str}T{end_str}").replace(tzinfo=ET)
            # Handle overnight windows
            if end_dt <= start_dt:
                end_dt += timedelta(days=1)
        except ValueError:
            lines.append(f"  {unit} — SKIP (could not parse schedule times)")
            continue

        # Decision logic: postpone if forecast peak is high AND window overlaps peak hour
        overlaps_peak = (
            peak_dt is not None
            and start_dt <= peak_dt.astimezone(ET) <= end_dt
        )
        high_demand = forecast_peak_mw >= POSTPONE_THRESHOLD_MW

        if high_demand and overlaps_peak:
            decision = "POSTPONE"
            reason = (
                f"forecast peak {forecast_peak_mw:,.0f} MW at {forecast_peak_time} "
                f"falls within this window — taking {cap_mw:,} MW offline is unsafe. "
                f"Recommend rescheduling to off-peak hours (23:00–06:00)."
            )
        elif high_demand and not overlaps_peak:
            decision = "APPROVE"
            reason = (
                f"forecast peak {forecast_peak_mw:,.0f} MW does not overlap this window. "
                f"Proceed as scheduled."
            )
        else:
            decision = "APPROVE"
            reason = f"demand forecast nominal ({forecast_peak_mw:,.0f} MW). Proceed as scheduled."

        decisions[decision] += 1
        lines.append(
            f"  {unit} ({date_str} {start_str}–{end_str}) — {decision}\n"
            f"    Capacity offline: {cap_mw:,} MW | {reason}"
        )
        if desc:
            lines.append(f"    Task: {desc}")

    summary = (
        f"  Summary: {decisions['APPROVE']} window(s) APPROVED, "
        f"{decisions['POSTPONE']} window(s) POSTPONED."
    )
    lines.append(summary)
    return "\n".join(lines)
