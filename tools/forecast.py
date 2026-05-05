import os

from tools.http import get_with_backoff

EIA_BASE = "https://api.eia.gov/v2/electricity/rto"

# Scoped to full NYISO region to match grid.py and market.py.
# Assignment spec references ZONA (West NY) but NYIS gives whole-region
# day-ahead forecast consistent with the rest of the build.
REGION = "NYIS"
REGION_NAME = "New York Independent System Operator"

# Hours within this % of peak are counted as part of the sustained demand window
SUSTAINED_THRESHOLD = 0.90


def get_demand_forecast() -> str:
    """Get the next 24-hour day-ahead demand forecast for NYISO from EIA."""
    key = os.environ["EIA_API_KEY"]

    try:
        forecast_resp = get_with_backoff(
            f"{EIA_BASE}/region-data/data",
            params={
                "api_key": key,
                "frequency": "hourly",
                "data[0]": "value",
                "facets[respondent][]": REGION,
                "facets[type][]": "DF",
                "sort[0][column]": "period",
                "sort[0][direction]": "desc",
                "length": 24,
            },
        )
    except Exception as e:
        return f"Demand forecast unavailable ({e}). Forward-looking risk assessment limited."

    forecast_data = forecast_resp.json().get("response", {}).get("data", [])
    if not forecast_data:
        return "No forecast data available."

    # Reverse so hours are in ascending order (earliest → latest)
    forecast_data = list(reversed(forecast_data))

    # Pull current actual demand for delta calculation
    try:
        actual_resp = get_with_backoff(
            f"{EIA_BASE}/region-data/data",
            params={
                "api_key": key,
                "frequency": "hourly",
                "data[0]": "value",
                "facets[respondent][]": REGION,
                "facets[type][]": "D",
                "sort[0][column]": "period",
                "sort[0][direction]": "desc",
                "length": 1,
            },
        )
        actual_data = actual_resp.json().get("response", {}).get("data", [])
        current_mw = int(actual_data[0]["value"]) if actual_data else None
    except Exception:
        current_mw = None

    # Find peak
    peak_row = max(forecast_data, key=lambda r: int(r["value"] or 0))
    peak_mw = int(peak_row["value"])
    peak_period = peak_row["period"]

    # Sustained demand window — consecutive hours at or above 90% of peak
    sustained_threshold_mw = peak_mw * SUSTAINED_THRESHOLD
    sustained_hours = [
        r for r in forecast_data if int(r["value"] or 0) >= sustained_threshold_mw
    ]
    sustained_count = len(sustained_hours)
    if sustained_hours:
        window_start = sustained_hours[0]["period"][11:16]
        window_end = sustained_hours[-1]["period"][11:16]
        window_str = f"{window_start}–{window_end} UTC ({sustained_count}hr)"
    else:
        window_str = "none"

    # Delta vs current actual
    if current_mw:
        delta_pct = ((peak_mw - current_mw) / current_mw) * 100
        direction = "above" if delta_pct >= 0 else "below"
        delta_str = f"{abs(delta_pct):.1f}% {direction} current actual ({current_mw:,} MWh)"
    else:
        delta_str = "current actual unavailable"

    lines = [f"24-hour demand forecast — {REGION_NAME}:"]
    for row in forecast_data:
        period = row["period"]
        mw = int(row["value"] or 0)
        hour = period[11:16]
        date = period[:10]
        lines.append(f"  {date} {hour}  {mw:,} MWh")

    lines.append(f"  Peak: {peak_mw:,} MWh at {peak_period} UTC")
    lines.append(f"  Sustained demand window (≥90% of peak): {window_str}")
    lines.append(f"  Forecast peak vs current: {delta_str}")
    return "\n".join(lines)


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    print(get_demand_forecast())
