import csv
import io
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from tools.http import get_with_backoff

NYISO_OASIS_BASE = "https://mis.nyiso.com/public/csv/ExternalLimitsFlows"
HEADERS = {"User-Agent": "gridwatch-agent/1.0 (energy ops briefing tool)"}
ET = ZoneInfo("America/New_York")

# Verified interface names from NYISO OASIS ExternalLimitsFlows CSV
PJM_INTERFACES   = {"SCH - PJM_HTP", "SCH - PJM_NEPTUNE", "SCH - PJM_VFT"}
ISONE_INTERFACES = {"SCH - NPX_1385", "SCH - NPX_CSC"}


def get_interconnection_flows() -> str:
    """Get current MW flows on NYISO ↔ PJM and NYISO ↔ ISO-NE tie-lines.

    Positive = NYISO exporting. Negative = NYISO importing.
    Never raises — returns a clean error string on any failure.
    """
    now_et = datetime.now(ET)

    csv_text = _fetch_intercon_csv(now_et.strftime("%Y%m%d"))
    if csv_text is None:
        csv_text = _fetch_intercon_csv((now_et - timedelta(days=1)).strftime("%Y%m%d"))
    if csv_text is None:
        return "NYISO interface flows — data unavailable (OASIS feed unreachable)."

    try:
        return _parse_flows(csv_text, now_et)
    except Exception:
        return "NYISO interface flows — data unavailable (parse error)."


def _parse_flows(csv_text: str, now_et: datetime) -> str:
    rows = list(csv.DictReader(io.StringIO(csv_text)))
    if not rows:
        return "NYISO interface flows — data unavailable (empty response)."

    target = now_et.replace(second=0, microsecond=0)

    # For each interface, keep the latest 5-min reading at or before now
    latest: dict[str, tuple[datetime, float]] = {}

    for row in rows:
        name = (row.get("Interface Name") or "").strip()
        if name not in PJM_INTERFACES and name not in ISONE_INTERFACES:
            continue
        try:
            ts = datetime.strptime(row["Timestamp"].strip(), "%m/%d/%Y %H:%M").replace(tzinfo=ET)
            flow = float(row["Flow (MWH)"])
        except (ValueError, KeyError, TypeError):
            continue
        if ts > target:
            continue
        cur = latest.get(name)
        if cur is None or ts > cur[0]:
            latest[name] = (ts, flow)

    if not latest:
        return "NYISO interface flows — data unavailable (no interface data found)."

    pjm_total   = sum(flow for name, (_, flow) in latest.items() if name in PJM_INTERFACES)
    isone_total = sum(flow for name, (_, flow) in latest.items() if name in ISONE_INTERFACES)
    snapshot_ts = max(ts for ts, _ in latest.values())

    def direction(mw: float) -> str:
        return "exporting" if mw >= 0 else "importing"

    def fmt_mw(mw: float) -> str:
        sign = "+" if mw >= 0 else "-"
        return f"{sign}{abs(mw):,.0f} MW"

    net = pjm_total + isone_total
    net_abs = abs(net)

    if pjm_total < 0 and isone_total < 0:
        detail = "NYISO is drawing from both PJM and ISO-NE — significant regional supply dependency."
    elif pjm_total < 0:
        detail = "NYISO is drawing from PJM — regional supply dependency present."
    elif isone_total < 0:
        detail = "NYISO is drawing from ISO-NE — regional supply dependency present."
    elif pjm_total > 0 and isone_total > 0:
        detail = "NYISO is exporting to both PJM and ISO-NE — surplus generation conditions."
    else:
        detail = f"NYISO net {direction(net)} {net_abs:,.0f} MW across regional tie-lines."

    net_line = (
        f"  Net position: importing {net_abs:,.0f} MW from neighbors"
        if net < 0
        else f"  Net position: exporting {net_abs:,.0f} MW to neighbors"
    )

    return "\n".join([
        f"NYISO interface flows — {snapshot_ts.strftime('%Y-%m-%dT%H:%M ET')}:",
        f"  NYISO → PJM:    {fmt_mw(pjm_total):>10}  ({direction(pjm_total)})",
        f"  NYISO → ISO-NE: {fmt_mw(isone_total):>10}  ({direction(isone_total)})",
        net_line,
        f"  Detail: {detail}",
    ])


def _fetch_intercon_csv(yyyymmdd: str):
    url = f"{NYISO_OASIS_BASE}/{yyyymmdd}ExternalLimitsFlows.csv"
    try:
        resp = get_with_backoff(url, headers=HEADERS, timeout=30)
        return resp.text
    except Exception:
        return None


if __name__ == "__main__":
    print(get_interconnection_flows())
