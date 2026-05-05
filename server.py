"""Flask API: run GridWatch once and expose structured JSON for the dashboard."""

from __future__ import annotations

import re
from typing import Any

from dotenv import load_dotenv
from flask import Flask, jsonify

load_dotenv()

from agent import run_gridwatch

app = Flask(__name__)


def _latest_by_tool(tool_calls: list[dict]) -> dict[str, str]:
    """Last result wins per tool name (execution order)."""
    out: dict[str, str] = {}
    for row in tool_calls:
        name = row.get("name") or ""
        out[name] = str(row.get("result") or "")
    return out


def _parse_risk_level(briefing: str) -> str:
    head = (briefing or "")[:1200]
    if re.search(r"\bRED\b|🔴", head, re.I):
        return "RED"
    if re.search(r"\bYELLOW\b|🟡", head, re.I):
        return "YELLOW"
    return "GREEN"


def _parse_risk_factors(briefing: str) -> list[str]:
    factors: list[str] = []
    for raw in (briefing or "").splitlines():
        s = raw.strip()
        m = re.match(r"^[-•*]\s+(.+)", s) or re.match(r"^\d+[.)]\s+(.+)", s)
        if m:
            factors.append(m.group(1).strip())
    dedup = []
    seen = set()
    for f in factors:
        if f and f not in seen:
            seen.add(f)
            dedup.append(f)
    return dedup[:12]


def _parse_grid_demand(text: str) -> int | None:
    m = re.search(r"Current demand:\s*([\d,]+)\s*MWh", text or "")
    if not m:
        return None
    return int(m.group(1).replace(",", ""))


def _parse_gen_mix(text: str) -> dict[str, float]:
    mix: dict[str, float] = {}
    for line in (text or "").splitlines():
        m = re.match(r"\s*([^:]+):\s*[\d,]+\s*MWh\s+\((\d+\.\d+)%\)", line.strip())
        if m:
            mix[m.group(1).strip()] = float(m.group(2))
    return mix


def _parse_weather_alerts(text: str) -> list[str]:
    if not text or "No active alerts" in text:
        return []
    items: list[str] = []
    cur: str | None = None
    for line in text.splitlines():
        s = line.strip()
        if not s or "Weather alerts —" in s:
            continue
        if re.match(r"^\[", s):
            if cur:
                items.append(cur)
            cur = s
        elif cur:
            cur = f"{cur} {s}"
    if cur:
        items.append(cur)
    return items[:20]



def _forecast_12h(text: str) -> str:
    lines = [ln.strip() for ln in (text or "").splitlines() if ln.strip()]
    if not lines:
        return "Forecast unavailable."
    body = lines[1:] if len(lines) > 1 else lines
    hourly = [ln for ln in body if re.match(r"^\d{4}-\d{2}-\d{2}", ln) or "°" in ln][:12]
    if not hourly:
        return " ".join(body[:3]) if body else "Forecast unavailable."
    return " ".join(hourly[:12])


def _parse_market(text: str) -> dict[str, Any]:
    out = {
        "lmp_avg": None,
        "lmp_peak_zone": None,
        "lmp_peak": None,
        "spread": None,
    }
    if not text:
        return out
    avg_m = re.search(r"Zone avg:\s*\$(\d+(?:\.\d+)?)", text)
    spr_m = re.search(r"Spread[^\$]*\$(\d+(?:\.\d+)?)", text)
    if avg_m:
        out["lmp_avg"] = float(avg_m.group(1))
    if spr_m:
        out["spread"] = float(spr_m.group(1))
    zones: list[tuple[str, float]] = []
    for zm in re.finditer(r"^\s*([^:\n]+?):\s*\$(\d+(?:\.\d+)?)/MWh", text, re.MULTILINE):
        name = zm.group(1).strip()
        if name.startswith("→") or "avg" in name.lower():
            continue
        zones.append((name, float(zm.group(2))))
    if zones:
        peak_name, peak_price = max(zones, key=lambda z: z[1])
        out["lmp_peak_zone"] = peak_name
        out["lmp_peak"] = peak_price
    return out


def _parse_news_headlines(text: str) -> list[str]:
    if not text or text.startswith("No energy"):
        return []
    lines = []
    for ln in text.splitlines():
        s = ln.strip()
        if not s:
            continue
        lines.append(s)
    return lines[:15]


def _parse_alert(text: str) -> dict[str, Any]:
    s = (text or "").strip()
    if not s:
        return {"sent": False, "level": "GREEN", "confirmation": "send_alert not invoked in this run."}

    sent = False
    level = "GREEN"

    if "No alert sent" in s:
        level = "GREEN"
        sent = False
    elif "suppressed" in s.lower() or "delivery failed" in s.lower():
        sent = False
        m = re.search(r"\b(RED|YELLOW|GREEN)\b", s)
        if m:
            level = m.group(1)
    elif "Alert sent" in s or ("ntfy.sh" in s and "failed" not in s.lower()):
        sent = True
        tail = re.search(r"\|\s*(RED|YELLOW|GREEN)\s*\Z", s)
        if tail:
            level = tail.group(1)
        else:
            m = re.search(r"\b(RED|YELLOW|GREEN)\b", s)
            if m:
                level = m.group(1)

    return {"sent": sent, "level": level, "confirmation": s or "No alert data."}


def build_briefing_payload(agent_result: dict) -> dict[str, Any]:
    """Map agent run output to the V2 dashboard JSON contract."""
    briefing = agent_result.get("briefing") or ""
    tool_calls = agent_result.get("tool_calls") or []
    err = agent_result.get("error")
    by = _latest_by_tool(tool_calls)

    grid_d = by.get("get_grid_demand", "")
    grid_m = by.get("get_generation_mix", "")
    wx_a = by.get("get_weather_alerts", "")
    wx_f = by.get("get_weather_forecast", "")
    lmp = by.get("get_lmp_prices", "")
    news = by.get("get_energy_news", "")
    alert_t = by.get("send_alert", "")

    demand = _parse_grid_demand(grid_d)
    gen_mix = _parse_gen_mix(grid_m)

    market = _parse_market(lmp)
    payload = {
        "risk": {
            "level": _parse_risk_level(briefing),
            "factors": _parse_risk_factors(briefing)
            or (["See GRIDWATCH briefing narrative."] if briefing else ["Briefing unavailable."]),
        },
        "grid": {
            "demand_mw": demand if demand is not None else 0,
            "gen_mix": gen_mix if gen_mix else {},
        },
        "weather": {
            "active_alerts": _parse_weather_alerts(wx_a),
            "forecast_12h": _forecast_12h(wx_f),
        },
        "market": {
            "lmp_avg": round(market["lmp_avg"], 2) if market["lmp_avg"] is not None else 0.0,
            "lmp_peak_zone": market["lmp_peak_zone"] or "—",
            "lmp_peak": round(market["lmp_peak"], 2) if market["lmp_peak"] is not None else 0.0,
            "spread": round(market["spread"], 2) if market["spread"] is not None else 0.0,
        },
        "news": {"headlines": _parse_news_headlines(news)},
        "alert": _parse_alert(alert_t),
        "meta": {
            "agent_error": err,
            "briefing_excerpt": (briefing[:280] + "…") if len(briefing) > 280 else briefing,
        },
    }
    return payload


@app.get("/briefing")
def briefing():
    result = run_gridwatch(quiet=True)
    payload = build_briefing_payload(result)
    status = 200 if not result.get("error") else 503
    return jsonify(payload), status


@app.after_request
def add_cors(resp):
    resp.headers["Access-Control-Allow-Origin"] = "*"
    return resp


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
