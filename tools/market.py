import csv
import io
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import requests
from tools.http import get_with_backoff

# NYISO OASIS publishes day-ahead zonal LMPs as a daily CSV (no key required).
# Index of feeds: http://mis.nyiso.com/public/P-2Alist.htm
NYISO_OASIS_BASE = "http://mis.nyiso.com/public/csv/damlbmp"
HEADERS = {"User-Agent": "gridwatch-agent/1.0 (energy ops briefing tool)"}

# NYISO timestamps in OASIS CSVs are wall-clock Eastern (no offset in the field).
ET = ZoneInfo("America/New_York")

EIA_BASE = "https://api.eia.gov/v2"

# NYC borough counties — scopes EIA-860 fleet to plants serving New York City
NYC_COUNTIES = {"New York", "Kings", "Queens", "Bronx", "Richmond"}

# Typical heat rates by technology (BTU/kWh) — EIA Annual Energy Outlook defaults.
# Used when plant-specific heat rates are unavailable via API.
# To override with actual plant heat rates, replace values per plantid.
HEAT_RATES = {
    "CC":  6905,   # Combined Cycle
    "GT":  10845,  # Combustion Turbine
    "ST":  13000,  # Steam Turbine
    "IC":  10000,  # Internal Combustion
    "OT":  10000,  # Other
}

PRIME_MOVER_TO_TECH = {
    "CA": "CC", "CS": "CC", "CT": "CC",
    "GT": "GT",
    "ST": "ST",
    "IC": "IC",
}


def get_lmp_prices() -> str:
    """Get current-hour NYISO day-ahead Locational Marginal Prices ($/MWh) by zone."""
    now_et = datetime.now(ET)

    # Day-ahead clearing for date D is published ~11:00 ET on D-1, so today's file
    # is normally available; fall back to yesterday's if not yet posted.
    csv_text = _fetch_dam_csv(now_et.strftime("%Y%m%d"))
    if csv_text is None:
        csv_text = _fetch_dam_csv((now_et - timedelta(days=1)).strftime("%Y%m%d"))
    if csv_text is None:
        return "No LMP data available — NYISO OASIS feed unreachable."

    rows = list(csv.DictReader(io.StringIO(csv_text)))
    if not rows:
        return "No LMP data available."

    target_hour = now_et.replace(minute=0, second=0, microsecond=0)
    by_zone: dict[str, tuple[datetime, float]] = {}

    for row in rows:
        zone = (row.get("Name") or "").strip()
        ts_str = (row.get("Time Stamp") or "").strip()
        try:
            ts = datetime.strptime(ts_str, "%m/%d/%Y %H:%M").replace(tzinfo=ET)
            price = float(row["LBMP ($/MWHr)"])
        except (ValueError, KeyError, TypeError):
            continue
        if not zone:
            continue
        # Pick the latest hour at or before "now" per zone.
        cur = by_zone.get(zone)
        if ts <= target_hour and (cur is None or ts > cur[0]):
            by_zone[zone] = (ts, price)

    # If everything is in the future (e.g. CSV is for tomorrow), fall back to the earliest hour.
    if not by_zone:
        for row in rows:
            zone = (row.get("Name") or "").strip()
            ts_str = (row.get("Time Stamp") or "").strip()
            try:
                ts = datetime.strptime(ts_str, "%m/%d/%Y %H:%M").replace(tzinfo=ET)
                price = float(row["LBMP ($/MWHr)"])
            except (ValueError, KeyError, TypeError):
                continue
            if not zone:
                continue
            cur = by_zone.get(zone)
            if cur is None or ts < cur[0]:
                by_zone[zone] = (ts, price)

    if not by_zone:
        return "No LMP data available."

    snapshot_ts = max(ts for ts, _ in by_zone.values()).strftime("%Y-%m-%dT%H:%M ET")
    prices = [p for _, p in by_zone.values()]
    avg_price = sum(prices) / len(prices)
    spread = max(prices) - min(prices)

    lines = [f"Day-ahead LMP — NYISO zones as of {snapshot_ts}:"]
    for zone, (_, price) in sorted(by_zone.items(), key=lambda kv: -kv[1][1]):
        lines.append(f"  {zone}: ${price:.2f}/MWh")
    lines.append(
        f"  → Zone avg: ${avg_price:.2f}/MWh | Spread (max − min): ${spread:.2f}/MWh"
    )
    return "\n".join(lines)


def get_henry_hub_price() -> str:
    """Get the most recent Henry Hub natural gas spot price ($/MMBtu) from EIA."""
    key = os.environ["EIA_API_KEY"]
    try:
        resp = get_with_backoff(
            f"{EIA_BASE}/natural-gas/pri/fut/data",
            params={
                "api_key": key,
                "frequency": "daily",
                "data[0]": "value",
                "facets[series][]": "RNGWHHD",
                "sort[0][column]": "period",
                "sort[0][direction]": "desc",
                "length": 5,
            },
        )
    except Exception as e:
        return f"Henry Hub price unavailable ({e})."
    data = resp.json().get("response", {}).get("data", [])
    if not data:
        return "Henry Hub price unavailable."

    latest = data[0]
    price = float(latest["value"])
    period = latest["period"]

    # 5-day trend for context
    if len(data) >= 2:
        prev = float(data[1]["value"])
        change = price - prev
        direction = "▲" if change >= 0 else "▼"
        trend = f"{direction} ${abs(change):.2f} vs prior day ({data[1]['period']})"
    else:
        trend = "no prior day available"

    lines = [
        f"Henry Hub spot price as of {period}:",
        f"  ${price:.2f}/MMBtu ({trend})",
    ]
    return "\n".join(lines)


def get_fleet_data() -> str:
    """Get NYC-area natural gas generator fleet from EIA-860 (capacity + heat rate).

    Scoped to the 5 NYC boroughs (New York, Kings, Queens, Bronx, Richmond counties)
    within NYISO. Heat rates are typical values by technology type (EIA AEO defaults)
    since plant-specific rates are not available via the EIA v2 API.
    To use actual plant heat rates, replace HEAT_RATES with a plantid-keyed lookup.
    """
    key = os.environ["EIA_API_KEY"]
    try:
        resp = get_with_backoff(
            f"{EIA_BASE}/electricity/operating-generator-capacity/data",
            params={
                "api_key": key,
                "frequency": "monthly",
                "data[0]": "nameplate-capacity-mw",
                "data[1]": "net-summer-capacity-mw",
                "data[2]": "county",
                "facets[stateid][]": "NY",
                "facets[energy_source_code][]": "NG",
                "facets[balancing_authority_code][]": "NYIS",
                "facets[status][]": "OP",
                "sort[0][column]": "period",
                "sort[0][direction]": "desc",
                "length": 200,
            },
        )
    except Exception as e:
        return f"NYC fleet data unavailable ({e})."
    rows = resp.json().get("response", {}).get("data", [])
    if not rows:
        return "No fleet data available."

    # Filter to most recent period and NYC counties only
    latest_period = rows[0]["period"]
    nyc_rows = [
        r for r in rows
        if r.get("county") in NYC_COUNTIES and r.get("period") == latest_period
    ]
    if not nyc_rows:
        return "No NYC fleet data available."

    # Roll up generators to plant level
    plants: dict[str, dict] = {}
    for r in nyc_rows:
        pid = r["plantid"]
        if pid not in plants:
            plants[pid] = {
                "name": r["plantName"],
                "county": r.get("county", "Unknown"),
                "capacity_mw": 0.0,
                "summer_mw": 0.0,
                "technologies": set(),
                "generators": 0,
            }
        plants[pid]["capacity_mw"] += float(r.get("nameplate-capacity-mw") or 0)
        plants[pid]["summer_mw"] += float(r.get("net-summer-capacity-mw") or 0)
        plants[pid]["technologies"].add(r.get("prime_mover_code", "OT"))
        plants[pid]["generators"] += 1

    total_capacity = sum(p["capacity_mw"] for p in plants.values())
    lines = [f"NYC natural gas fleet — {len(plants)} plants as of {latest_period}:"]

    for pid, p in sorted(plants.items(), key=lambda kv: -kv[1]["capacity_mw"]):
        # Use the most efficient (lowest heat rate) technology at the plant
        tech_codes = p["technologies"]
        mapped = [PRIME_MOVER_TO_TECH.get(t, "OT") for t in tech_codes]
        heat_rate = min(HEAT_RATES.get(t, 10000) for t in mapped)
        tech_label = "/".join(sorted(tech_codes))
        lines.append(
            f"  {p['name']} ({p['county']}) — "
            f"{p['capacity_mw']:,.0f} MW nameplate | "
            f"{p['summer_mw']:,.0f} MW summer | "
            f"Heat rate: {heat_rate:,} BTU/kWh | "
            f"Tech: {tech_label} | "
            f"{p['generators']} unit(s)"
        )

    lines.append(f"  → Total NYC NG fleet: {total_capacity:,.0f} MW nameplate")
    return "\n".join(lines)


def _fetch_dam_csv(yyyymmdd: str):
    url = f"{NYISO_OASIS_BASE}/{yyyymmdd}damlbmp_zone.csv"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        if resp.status_code != 200:
            return None
        return resp.text
    except requests.RequestException:
        return None


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    print(get_henry_hub_price())
    print()
    print(get_fleet_data())
    print()
    print(get_lmp_prices())
