"""Flask API: GridWatch briefing — raw text (step 1) and dashboard JSON contract (step 2)."""

from __future__ import annotations

import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from flask import Flask, jsonify, request

load_dotenv(Path(__file__).resolve().parent / ".env")

from agent import run_gridwatch

app = Flask(__name__)

MODEL_NAME = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6")

FUEL_TO_CONTRACT = {
    "Natural Gas": "natural_gas_pct",
    "Nuclear": "nuclear_pct",
    "Wind": "wind_pct",
    "Hydro": "hydro_pct",
    "Solar": "solar_pct",
}


def _latest_by_tool(tool_calls: list[dict]) -> dict[str, str]:
    # Last call wins — intentional; tools called twice use the most recent result.
    out: dict[str, str] = {}
    for row in tool_calls:
        name = row.get("name") or ""
        out[name] = str(row.get("result") or "")
    return out


def _risk_level(briefing: str, alert_result: str = "") -> str:
    # Prefer the canonical level reported by send_alert over text-scanning the briefing.
    for level in ("RED", "YELLOW", "GREEN"):
        if re.search(rf"\b{level}\b", alert_result or ""):
            return level
    head = briefing or ""
    if re.search(r"\bRED\b|🔴", head, re.I):
        return "RED"
    if re.search(r"\bYELLOW\b|🟡", head, re.I):
        return "YELLOW"
    return "GREEN"


def _risk_emoji(level: str) -> str:
    return {"RED": "🔴", "YELLOW": "🟡", "GREEN": "🟢"}.get(level.upper(), "🟢")


def _parse_grid_demand_mw(text: str) -> int:
    m = re.search(r"Current demand:\s*([\d,]+)\s*MW", text or "")
    return int(m.group(1).replace(",", "")) if m else 0


def _parse_generation_mix_pct(text: str) -> dict[str, float]:
    """Parse tool lines → contract fuel keys (percent)."""
    found: dict[str, float] = {}
    for line in (text or "").splitlines():
        m = re.match(r"\s*([^:]+):\s*[\d,]+\s*MWh\s+\((\d+\.\d+)%\)", line.strip())
        if not m:
            continue
        label = m.group(1).strip()
        pct = float(m.group(2))
        key = FUEL_TO_CONTRACT.get(label)
        if key:
            found[key] = pct
    base = {
        "natural_gas_pct": 0.0,
        "nuclear_pct": 0.0,
        "wind_pct": 0.0,
        "hydro_pct": 0.0,
        "solar_pct": 0.0,
    }
    base.update(found)
    return base


def _renewable_pct(mix: dict[str, float]) -> float:
    s = mix.get("wind_pct", 0) + mix.get("hydro_pct", 0) + mix.get("solar_pct", 0)
    return round(s, 1)


def _parse_forecast_peak(text: str) -> tuple[int, str]:
    t = text or ""
    m = re.search(r"Peak:\s*([\d,]+)\s*MW\s+at\s+([^\n\r]+)", t, re.I)
    if m:
        return int(m.group(1).replace(",", "")), m.group(2).strip()
    m2 = re.search(r"peak[^\d]{0,12}([\d,]+)\s*MW", t, re.I)
    if m2:
        return int(m2.group(1).replace(",", "")), ""
    return 0, ""


def _parse_weather_alert_objs(text: str) -> list[dict[str, str]]:
    if not text or "No active alerts" in text:
        return []
    out: list[dict[str, str]] = []
    for line in text.splitlines():
        s = line.strip()
        m = re.match(r"^\[([^\]]+)\]\s*(.+)$", s)
        if m and "Weather alerts" not in s:
            out.append({"severity": m.group(1).strip().upper(), "event": m.group(2).strip()})
    return out[:20]


def _parse_hourly_forecast_rows(text: str, limit: int = 12) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for raw in (text or "").splitlines():
        line = raw.strip()
        if not re.match(r"\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}", line):
            continue
        m = re.match(
            r"^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})\s+(\d+)°[Ff]\s+Wind:\s*(.+?)\s{2,}(.+)$",
            line,
        )
        if m:
            rows.append(
                {
                    "time": m.group(1),
                    "temp_f": int(m.group(2)),
                    "condition": m.group(4).strip(),
                }
            )
        else:
            parts = re.split(r"\s{2,}", line)
            if len(parts) >= 4:
                t = parts[0]
                temp_m = re.match(r"(\d+)°[Ff]", parts[1])
                if temp_m:
                    rows.append(
                        {
                            "time": t,
                            "temp_f": int(temp_m.group(1)),
                            "condition": parts[-1].strip(),
                        }
                    )
        if len(rows) >= limit:
            break
    return rows


def _parse_lmp_zones(text: str) -> dict[str, float]:
    zones: dict[str, float] = {}
    for zm in re.finditer(r"^\s*([^:\n]+?):\s*\$(\d+(?:\.\d+)?)/MWh", text or "", re.MULTILINE):
        name = zm.group(1).strip()
        if name.startswith("→") or "avg" in name.lower():
            continue
        zones[name] = float(zm.group(2))
    return zones


def _parse_zone_avg_spread(text: str) -> tuple[float, float]:
    t = text or ""
    avg_m = re.search(r"Zone avg:\s*\$(\d+(?:\.\d+)?)", t)
    spr_m = re.search(r"Spread[^\$]*\$(\d+(?:\.\d+)?)", t)
    avg = float(avg_m.group(1)) if avg_m else 0.0
    spread = float(spr_m.group(1)) if spr_m else 0.0
    return round(avg, 2), round(spread, 2)


def _parse_henry_hub(text: str) -> float:
    m = re.search(r"\$(\d+(?:\.\d+)?)/MMBtu", text or "")
    return round(float(m.group(1)), 2) if m else 0.0


def _parse_news_items(text: str) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    if not text or text.startswith("No energy"):
        return out
    for line in text.splitlines():
        s = line.strip()
        if not s:
            continue
        m = re.match(r"^\[([^\]]+)\](?:\s*\([^)]*\))?\s*(.+)$", s)
        if m:
            out.append({"source": m.group(1).strip(), "headline": m.group(2).strip()})
        else:
            out.append({"source": "Feed", "headline": s})
    return out[:20]


def _parse_maintenance(text: str) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    lines = (text or "").splitlines()
    i = 0
    while i < len(lines):
        m = re.match(
            r"^\s{2}(.+?)\s+\(\d{4}-\d{2}-\d{2}.+\)\s*—\s*(APPROVE|POSTPONE)",
            lines[i],
        )
        if m:
            unit = m.group(1).strip()
            decision = m.group(2)
            reason_parts: list[str] = []
            i += 1
            while i < len(lines) and lines[i].startswith("    "):
                reason_parts.append(lines[i].strip())
                i += 1
            items.append(
                {
                    "unit": unit,
                    "decision": decision,
                    "reason": " ".join(reason_parts) if reason_parts else "",
                }
            )
            continue
        i += 1
    return items


def _demand_response_summary(text: str) -> str:
    s = (text or "").strip()
    return s if s else "Demand response not invoked this run."


def _alert_sent_flag(send_alert_text: str) -> bool:
    s = send_alert_text or ""
    if "No alert sent" in s or not s.strip():
        return False
    if "suppressed" in s.lower() or "delivery failed" in s.lower():
        return False
    return "Alert sent" in s or ("ntfy.sh" in s and "failed" not in s.lower())


def _extract_recommendation(briefing: str) -> str:
    b = briefing or ""
    m = re.search(
        r"(?is)\*{0,2}\s*Recommendation\s*:?\*{0,2}\s*(.+?)(?:\n\s*\n|\Z)",
        b,
    )
    if m:
        return " ".join(m.group(1).split())
    lines = [ln.strip() for ln in b.splitlines() if ln.strip()]
    return lines[-1] if lines else "No recommendation extracted."


def build_dashboard_contract(agent_result: dict) -> dict[str, Any]:
    """Exact field names for React dashboard (team contract)."""
    briefing = agent_result.get("briefing") or ""
    tool_calls = agent_result.get("tool_calls") or []
    by = _latest_by_tool(tool_calls)

    grid_d = by.get("get_grid_demand", "")
    grid_m = by.get("get_generation_mix", "")
    forecast_txt = by.get("get_demand_forecast", "")
    wx_a = by.get("get_weather_alerts", "")
    wx_f = by.get("get_weather_forecast", "")
    lmp = by.get("get_lmp_prices", "")
    henry = by.get("get_henry_hub_price", "")
    news = by.get("get_energy_news", "")
    dr = by.get("trigger_demand_response", "")
    maint = by.get("evaluate_maintenance_schedule", "")
    alert_txt = by.get("send_alert", "")

    level = _risk_level(briefing, by.get("send_alert", ""))
    gen_mix = _parse_generation_mix_pct(grid_m)
    peak_mw, peak_time = _parse_forecast_peak(forecast_txt)
    lmp_by_zone = _parse_lmp_zones(lmp)
    zone_avg, spread = _parse_zone_avg_spread(lmp)

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    return {
        "risk": {"level": level, "emoji": _risk_emoji(level)},
        "grid": {
            "current_demand_mw": _parse_grid_demand_mw(grid_d),
            "region": "NYISO",
            "generation_mix": gen_mix,
            "renewable_pct": _renewable_pct(gen_mix),
            "forecast_peak_mw": peak_mw,
            "forecast_peak_time": peak_time or "",
        },
        "weather": {
            "alerts": _parse_weather_alert_objs(wx_a),
            "forecast": _parse_hourly_forecast_rows(wx_f, 12),
        },
        "market": {
            "lmp_by_zone": lmp_by_zone,
            "zone_avg_mwh": zone_avg,
            "spread_mwh": spread,
            "henry_hub_mmbtu": _parse_henry_hub(henry),
        },
        "news": _parse_news_items(news),
        "actions": {
            "demand_response": _demand_response_summary(dr),
            "maintenance": _parse_maintenance(maint),
        },
        "recommendation": _extract_recommendation(briefing),
        "alert_sent": _alert_sent_flag(alert_txt),
        "meta": {
            "timestamp": ts,
            "model": MODEL_NAME,
            "run_cost_usd": float(agent_result.get("run_cost_usd") or 0),
        },
    }


_briefing_cache: dict = {"result": None, "ts": 0.0}
_BRIEFING_TTL = 5 * 60  # 5 minutes


def _get_cached_result() -> dict:
    if _briefing_cache["result"] and time.time() - _briefing_cache["ts"] < _BRIEFING_TTL:
        return _briefing_cache["result"]
    result = run_gridwatch(quiet=True)
    _briefing_cache.update({"result": result, "ts": time.time()})
    return result


@app.get("/briefing/raw")
def briefing_raw():
    """Step 1 gate: run agent once, return only briefing text (+ error if any)."""
    result = _get_cached_result()
    payload = {
        "briefing": result.get("briefing") or "",
        "error": result.get("error"),
    }
    status = 200 if not result.get("error") else 503
    return jsonify(payload), status


@app.get("/briefing")
def briefing():
    """Step 2: full dashboard JSON contract."""
    result = _get_cached_result()
    payload = build_dashboard_contract(result)
    status = 200 if not result.get("error") else 503
    return jsonify(payload), status


_BRIEFING_TOKEN = os.environ.get("BRIEFING_TOKEN", "").strip()

_ALLOWED_ORIGINS = {
    "http://localhost:5173",  # Vite dev
    "http://localhost:3000",  # alt dev port
}


@app.before_request
def require_token():
    if request.path.startswith("/briefing"):
        if not _BRIEFING_TOKEN:
            return jsonify({"error": "server misconfigured — BRIEFING_TOKEN not set"}), 500
        auth = request.headers.get("Authorization", "")
        if auth != f"Bearer {_BRIEFING_TOKEN}":
            return jsonify({"error": "unauthorized"}), 401


@app.after_request
def add_cors(resp):
    origin = request.environ.get("HTTP_ORIGIN", "")
    if origin in _ALLOWED_ORIGINS:
        resp.headers["Access-Control-Allow-Origin"] = origin
    return resp


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
