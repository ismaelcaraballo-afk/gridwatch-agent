import json
import os
import time
import requests

DR_TOPIC    = os.environ.get("DR_TOPIC", "gridwatch-dr")
DR_NTFY_URL = f"https://ntfy.sh/{DR_TOPIC}"

DR_THRESHOLD_MW = 18_000
DR_STATE_FILE   = os.path.join(os.sep + "tmp", f"gridwatch_dr_{os.getuid()}.json")
DR_COOLDOWN     = 2 * 60 * 60


def trigger_demand_response(
    forecast_peak_mw: float,
    forecast_peak_time: str,
    current_mw: float,
) -> str:
    """Fire a load-reduction signal when forecast peak exceeds the DR threshold.

    Sends a push notification to enrolled demand-response customers via ntfy.sh.
    Skips if peak is below threshold or cooldown window is active.
    """
    if forecast_peak_mw < DR_THRESHOLD_MW:
        return (
            f"Demand response not triggered — forecast peak {forecast_peak_mw:,.0f} MW "
            f"is below threshold ({DR_THRESHOLD_MW:,} MW)."
        )

    # Cooldown check
    try:
        with open(DR_STATE_FILE) as f:
            state = json.load(f)
        elapsed = time.time() - state.get("last_time", 0)
        if elapsed < DR_COOLDOWN:
            remaining = int((DR_COOLDOWN - elapsed) / 60)
            return (
                f"Demand response suppressed — already fired {int(elapsed/60)}m ago "
                f"({remaining}m cooldown remaining)."
            )
    except (FileNotFoundError, json.JSONDecodeError):
        pass

    safe_time = str(forecast_peak_time).replace("\n", "").replace("\r", "")[:30]
    delta_pct = ((forecast_peak_mw - current_mw) / current_mw) * 100 if current_mw > 0 else 100.0
    message = (
        f"REDUCE LOAD NOW — Forecast peak {forecast_peak_mw:,.0f} MW at {safe_time} "
        f"({delta_pct:.0f}% above current {current_mw:,.0f} MW). "
        f"Curtail non-essential systems immediately. GridWatch autonomous dispatch."
    )

    try:
        resp = requests.post(
            DR_NTFY_URL,
            data=message.encode("utf-8"),
            headers={
                "Title":    "GRIDWATCH — DEMAND RESPONSE ACTIVATED",
                "Priority": "urgent",
                "Tags":     "electric_plug,rotating_light",
            },
            timeout=10,
        )
    except requests.RequestException as e:
        return f"Demand response signal failed (network error): {e}"

    if resp.status_code != 200:
        return f"Demand response signal failed (HTTP {resp.status_code})."

    if os.path.islink(DR_STATE_FILE):
        os.unlink(DR_STATE_FILE)
    with open(DR_STATE_FILE, "w") as f:
        json.dump({"last_time": time.time(), "peak_mw": forecast_peak_mw}, f)

    return (
        f"Demand response ACTIVATED — signal sent to enrolled customers via {DR_TOPIC}. "
        f"Forecast peak: {forecast_peak_mw:,.0f} MW at {forecast_peak_time}. "
        f"Load reduction requested immediately."
    )
