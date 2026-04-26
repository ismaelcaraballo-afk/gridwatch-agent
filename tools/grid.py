import os
import requests

EIA_BASE = "https://api.eia.gov/v2/electricity/rto"

def get_grid_demand() -> str:
    """Get current real-time electricity demand by US grid region."""
    key = os.environ["EIA_API_KEY"]
    resp = requests.get(
        f"{EIA_BASE}/demand/data",
        params={
            "api_key": key,
            "frequency": "hourly",
            "data[0]": "value",
            "sort[0][column]": "period",
            "sort[0][direction]": "desc",
            "length": 10,
        },
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json().get("response", {}).get("data", [])
    if not data:
        return "No demand data available."
    lines = []
    for row in data[:5]:
        lines.append(f"{row.get('period')} | Region: {row.get('respondent')} | Demand: {row.get('value')} MWh | Type: {row.get('type')}")
    return "\n".join(lines)


def get_generation_mix() -> str:
    """Get current electricity generation by fuel type (solar, wind, gas, nuclear)."""
    key = os.environ["EIA_API_KEY"]
    resp = requests.get(
        f"{EIA_BASE}/fuel-type-data/data",
        params={
            "api_key": key,
            "frequency": "hourly",
            "data[0]": "value",
            "sort[0][column]": "period",
            "sort[0][direction]": "desc",
            "length": 20,
        },
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json().get("response", {}).get("data", [])
    if not data:
        return "No generation data available."
    # group by fuel type for the most recent period
    latest_period = data[0]["period"]
    by_fuel = {}
    for row in data:
        if row["period"] == latest_period:
            fuel = row.get("fueltype", "Unknown")
            val = row.get("value", 0) or 0
            by_fuel[fuel] = by_fuel.get(fuel, 0) + val
    total = sum(by_fuel.values()) or 1
    renewables = sum(v for f, v in by_fuel.items() if f in ("SUN", "WND", "WAT"))
    lines = [f"Generation mix as of {latest_period}:"]
    for fuel, mwh in sorted(by_fuel.items(), key=lambda x: -x[1]):
        pct = (mwh / total) * 100
        lines.append(f"  {fuel}: {mwh:,} MWh ({pct:.1f}%)")
    lines.append(f"  → Renewables total: {(renewables/total)*100:.1f}%")
    return "\n".join(lines)
