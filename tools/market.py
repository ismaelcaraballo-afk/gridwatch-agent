import csv
import io
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import requests

# NYISO OASIS publishes day-ahead zonal LMPs as a daily CSV (no key required).
# Index of feeds: http://mis.nyiso.com/public/P-2Alist.htm
NYISO_OASIS_BASE = "http://mis.nyiso.com/public/csv/damlbmp"
HEADERS = {"User-Agent": "gridwatch-agent/1.0 (energy ops briefing tool)"}

# NYISO timestamps in OASIS CSVs are wall-clock Eastern (no offset in the field).
ET = ZoneInfo("America/New_York")


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
    print(get_lmp_prices())
