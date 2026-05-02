import os
import requests

from tools.http import get_with_backoff

EIA_BASE = "https://api.eia.gov/v2/electricity/rto"

# Scoped to New York Independent System Operator — matches weather tool coordinates (NYC)
REGION = "NYIS"
REGION_NAME = "New York Independent System Operator"

FUEL_LABELS = {
    "COL": "Coal",
    "NG":  "Natural Gas",
    "NUC": "Nuclear",
    "OIL": "Petroleum",
    "OTH": "Other",
    "SUN": "Solar",
    "WAT": "Hydro",
    "WND": "Wind",
}
CLEAN_FUELS = {"SUN", "WND", "WAT", "NUC"}


def _get_with_retry(url, params, retries=2, timeout=30) -> requests.Response:
    return get_with_backoff(url, params=params, timeout=timeout, max_retries=retries)


def get_grid_demand() -> str:
    """Get current real-time electricity demand for the NYISO grid region."""
    key = os.environ["EIA_API_KEY"]
    try:
        resp = _get_with_retry(
            f"{EIA_BASE}/region-data/data",
            params={
                "api_key": key,
                "frequency": "hourly",
                "data[0]": "value",
                "facets[respondent][]": REGION,
                "facets[type][]": "D",
                "sort[0][column]": "period",
                "sort[0][direction]": "desc",
                "length": 5,
            },
        )
    except requests.RequestException as e:
        return f"EIA demand data unavailable ({e}). Grid status unknown — use caution."
    data = resp.json().get("response", {}).get("data", [])
    if not data:
        return "No demand data available."

    latest = data[0]
    period = latest.get("period", "unknown")
    demand = int(latest.get("value") or 0)

    lines = [f"Grid demand — {REGION_NAME} as of {period}:"]
    lines.append(f"  Current demand: {demand:,} MWh")

    if len(data) >= 5:
        avg = sum(int(r.get("value") or 0) for r in data) // len(data)
        pct_diff = ((demand - avg) / avg * 100) if avg else 0
        direction = "above" if pct_diff >= 0 else "below"
        lines.append(f"  5-hour avg: {avg:,} MWh ({abs(pct_diff):.1f}% {direction} recent avg)")

    return "\n".join(lines)


def get_generation_mix() -> str:
    """Get current electricity generation breakdown by fuel type for NYISO."""
    key = os.environ["EIA_API_KEY"]
    try:
        resp = _get_with_retry(
            f"{EIA_BASE}/fuel-type-data/data",
            params={
                "api_key": key,
                "frequency": "hourly",
                "data[0]": "value",
                "facets[respondent][]": REGION,
                "sort[0][column]": "period",
                "sort[0][direction]": "desc",
                "length": 20,
            },
        )
    except requests.RequestException as e:
        return f"EIA generation data unavailable ({e}). Fuel mix unknown."
    data = resp.json().get("response", {}).get("data", [])
    if not data:
        return "No generation data available."

    latest_period = data[0]["period"]
    by_fuel = {}
    for row in data:
        if row["period"] != latest_period:
            break
        fuel = row.get("fueltype", "OTH")
        by_fuel[fuel] = int(row.get("value") or 0)

    total = sum(by_fuel.values()) or 1
    clean = sum(v for f, v in by_fuel.items() if f in CLEAN_FUELS)
    fossil = total - clean

    lines = [f"Generation mix — {REGION_NAME} as of {latest_period}:"]
    for fuel, mwh in sorted(by_fuel.items(), key=lambda x: -x[1]):
        label = FUEL_LABELS.get(fuel, fuel)
        pct = (mwh / total) * 100
        lines.append(f"  {label}: {mwh:,} MWh ({pct:.1f}%)")
    lines.append(f"  → Clean total: {(clean/total)*100:.1f}% | Fossil total: {(fossil/total)*100:.1f}%")
    return "\n".join(lines)


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    print(get_grid_demand())
    print()
    print(get_generation_mix())
