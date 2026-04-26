# GridWatch — One-Page Spec
**Cycle 3 Agent Project | Energy/Utilities Operations Analyst**
**Date:** April 26, 2026

---

## Problem Statement

Energy operations analysts start every shift the same way — opening three separate tabs (EIA dashboard, NOAA weather, internal reports), reading each one manually, and building a picture of what happened overnight. There is no system that connects these sources. When a demand spike occurred at 3 AM during a thunderstorm, the analyst doesn't find out until 6:30 AM when they sit down and manually piece it together. By then, the window to act has already narrowed.

**One sentence:** An agent that runs at shift start, pulls overnight EIA demand data, cross-references active NOAA weather alerts, flags anything that deviated from baseline, and delivers a prioritized briefing — so the analyst walks in knowing exactly what happened instead of spending 30 minutes figuring it out.

---

## Agent Design

**Core decision:** Is the grid at risk right now, and what should the analyst do about it?

**Risk logic:**
| Level | Condition |
|-------|-----------|
| 🔴 RED | Demand exceeds day-ahead forecast by ≥10% AND active SEVERE/EXTREME weather alert |
| 🟡 YELLOW | Either condition alone, OR forecast shows extreme temps (>95°F or <14°F) |
| 🟢 GREEN | Normal demand, no active alerts |

**Human checkpoint:** If risk is RED, the agent pauses and asks the analyst to confirm before finalizing the briefing. This is the moment where the agent hands control back to the human.

---

## Tools

| Tool | Function | API | Key Required |
|------|----------|-----|-------------|
| Grid Demand | `get_grid_demand()` | EIA v2 RTO region-data | Yes — free |
| Generation Mix | `get_generation_mix()` | EIA v2 fuel-type-data | Yes — free |
| Weather Alerts | `get_weather_alerts()` | NOAA api.weather.gov | No |
| Weather Forecast | `get_weather_forecast()` | NOAA api.weather.gov | No |
| Energy News | `get_energy_news()` | RSS — OilPrice, Power Magazine, Utility Dive | No |

**Validation status:**
- NOAA alerts — ✅ tested live, 200
- NOAA forecast — ✅ tested live, 200, returning hourly data
- RSS feeds — ✅ tested live, 3 of 4 feeds returning data
- EIA API — ✅ key obtained, server temporarily down at time of submission, endpoint confirmed valid

---

## Architecture

```
python agent.py
      ↓
[step 1] agent calls all 5 tools
  → get_grid_demand()      EIA — current demand + 5-hr avg + deviation %
  → get_generation_mix()   EIA — solar/wind/gas/nuclear breakdown
  → get_weather_alerts()   NOAA — active severe weather alerts
  → get_weather_forecast() NOAA — next 12-hour hourly forecast
  → get_energy_news()      RSS — top energy headlines

[step 2] agent reasons across all 5 sources
  → assigns 🔴 🟡 🟢 risk level
  → if 🔴: PAUSE → human checkpoint → analyst confirms → finalize
  → outputs structured briefing with recommendation
```

---

## Output Format

```
🔴 / 🟡 / 🟢

RISK LEVEL: [emoji] [RED|YELLOW|GREEN]
GRID STATUS: latest demand, region, top fuels, renewable %
WEATHER: active alerts + 12-hour forecast highlights
NEWS: 2–3 headline bullets
RECOMMENDATION: one specific immediate action for the analyst
```

---

## Team

| Member | GitHub | Component | File |
|--------|--------|-----------|------|
| Ismael Caraballo | ismaelcaraballo-afk | Agent loop + human checkpoint | `agent.py` |
| Michael Fehdrau | MichaelFehdrau0205 | System prompt + risk logic | `prompts.py` |
| Edwin | edpursuing | EIA API — grid demand + generation mix | `tools/grid.py` |
| Christian Almonte | christianalmonte112 | NOAA API — weather alerts + forecast | `tools/weather.py` |
| Juan Franco | m1lestones | RSS feeds — energy headlines | `tools/news.py` |

---

## Repo

`https://github.com/ismaelcaraballo-afk/gridwatch-agent`

---

## v2.0 Path

Add day-ahead commit recommendation — agent pulls EIA wholesale electricity prices and natural gas spot prices, calculates spark spreads, and produces a generation commit memo. This is the capability that requires a frontier model (Anthropic API) — the free model can summarize data, but reasoning across competing price signals to produce a defensible commit decision is where Claude Opus separates itself.
