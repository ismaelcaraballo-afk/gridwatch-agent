# GridWatch v2 — Schematics & Team Assignments

*Authored: 2026-05-01 | Multi-LLM research synthesis: DS, GPT-4o, Llama, Pplx*

---

## System Architecture — v1 (Current)

```
┌────────────────────────────────────────────────────────────────────┐
│                      GRIDWATCH v1 AGENT                            │
│            OpenRouter → nvidia/nemotron-3-super-120b               │
└───────────────────────────┬────────────────────────────────────────┘
                            │  parallel tool dispatch (ThreadPoolExecutor)
     ┌──────────┬───────────┼───────────┬──────────┬──────────┐
     ▼          ▼           ▼           ▼          ▼          ▼
┌─────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌──────────┐
│   EIA   │ │  EIA   │ │ NOAA   │ │ NOAA   │ │  RSS   │ │  NYISO   │
│ demand  │ │gen mix │ │weather │ │forecast│ │ news   │ │   LMP    │
│         │ │        │ │ alerts │ │ 48hr   │ │        │ │ day-ahd  │
└────┬────┘ └───┬────┘ └───┬────┘ └───┬────┘ └───┬────┘ └────┬─────┘
     └──────────┴───────────┴───────────┴──────────┴───────────┘
                                   │
                       LLM synthesizes all 6 results
                                   │
                        ┌──────────▼──────────┐
                        │   Risk Assessment    │
                        │  RED / YELLOW / GREEN│
                        └──────────┬──────────┘
                                   │
                 ┌─────────────────┴──────────────────┐
                 ▼                                     ▼
         ┌──────────────┐                    ┌──────────────────┐
         │  send_alert  │  (RED/YELLOW only) │  Rich Terminal   │
         │  ntfy.sh     │                    │  Briefing Panel  │
         │  push notify │                    │  (analyst reads) │
         └──────────────┘                    └──────────────────┘
```

---

## System Architecture — v2 (Target)

```
┌────────────────────────────────────────────────────────────────────────────┐
│                          GRIDWATCH v2 AGENT                                │
│                  OpenRouter / Anthropic Claude (upgrade path)              │
└───────────────────────────────────┬────────────────────────────────────────┘
                                    │
              ┌─────────────────────┴──────────────────────┐
              │              TOOL DISPATCH LAYER            │
              │         (parallel, ThreadPoolExecutor)       │
              └──┬───────┬──────────┬──────────┬────────────┘
                 │       │          │          │
     ┌───────────┼───────┼──────────┼──────────┼──────────────┐
     │           │       │          │          │              │
     ▼           ▼       ▼          ▼          ▼              ▼
┌─────────┐ ┌───────┐ ┌───────┐ ┌───────┐ ┌──────────┐ ┌─────────┐
│  DATA   │ │FORECAST│ │ANOMALY│ │MARKET │ │REGIONAL  │ │ ALERTS  │
│ TOOLS   │ │ TOOLS  │ │DETECT │ │TOOLS  │ │  FLOWS   │ │  PUSH   │
│ (v1)    │ │ (NEW)  │ │ (NEW) │ │ (v1+) │ │  (NEW)   │ │  (v1)   │
│         │ │        │ │       │ │       │ │          │ │         │
│demand   │ │EIA 24h │ │Z-score│ │LMP    │ │NYISO     │ │ntfy.sh  │
│gen_mix  │ │demand  │ │on     │ │prices │ │tie-lines │ │RED/YLW  │
│weather  │ │forecast│ │demand │ │spark  │ │→ PJM     │ │only     │
│alerts   │ │        │ │& LMP  │ │spread │ │→ ISO-NE  │ │         │
│news     │ │        │ │rolling│ │gas $  │ │import    │ │         │
│         │ │        │ │window │ │       │ │dependency│ │         │
└────┬────┘ └───┬───┘ └───┬───┘ └───┬───┘ └────┬─────┘ └────┬────┘
     └──────────┴──────────┴─────────┴──────────┴────────────┘
                                    │
                          ┌─────────▼──────────┐
                          │   LLM REASONING     │
                          │                    │
                          │  v1: Nemotron free  │
                          │  v2: Claude Opus   │
                          │  (upgrade trigger: │
                          │   fleet commit,    │
                          │   causal forecast) │
                          └─────────┬──────────┘
                                    │
              ┌─────────────────────┴──────────────────────┐
              ▼                                             ▼
    ┌──────────────────┐                       ┌───────────────────────────────────┐
    │  ALERT LAYER     │                       │   OUTPUT LAYER                    │
    │                  │                       │                                   │
    │  send_alert()    │                       │  A) Rich Terminal Panel           │
    │  ntfy.sh push    │                       │     (v1 — analyst CLI)            │
    │  RED / YELLOW    │                       │                                   │
    └──────────────────┘                       │  B) server.py  GET /briefing      │
                                               │     Flask/FastAPI → JSON          │
                                               │     (Michael builds — GREENLIT)   │
                                               │                                   │
                                               │     └── React Dashboard           │
                                               │         ┌─────────────────────┐  │
                                               │         │ Module 01           │  │
                                               │         │ RISK LEVEL          │  │
                                               │         │ 🟡 YELLOW           │  │
                                               │         │ · cited factors     │  │
                                               │         │ (LLM verdict)       │  │
                                               │         ├─────────────────────┤  │
                                               │         │ Module 02           │  │
                                               │         │ GRID STATUS         │  │
                                               │         │ demand, gen mix,    │  │
                                               │         │ capacity curves     │  │
                                               │         ├─────────────────────┤  │
                                               │         │ Module 03           │  │
                                               │         │ WEATHER             │  │
                                               │         │ alerts, hourly      │  │
                                               │         │ forecast, renewable │  │
                                               │         ├─────────────────────┤  │
                                               │         │ Module 04           │  │
                                               │         │ MARKET              │  │
                                               │         │ LMP by zone,        │  │
                                               │         │ spark spread,       │  │
                                               │         │ Henry Hub gas $     │  │
                                               │         ├─────────────────────┤  │
                                               │         │ Module 05           │  │
                                               │         │ NEWS + SENTIMENT    │  │
                                               │         │ headlines, impact   │  │
                                               │         │ tags, bear/bull     │  │
                                               │         └─────────────────────┘  │
                                               └───────────────────────────────────┘
```

---

## Data Flow Detail — v2

```
EIA v2 API
  ├── /electricity/rto/region-data          → get_grid_demand()       [v1]
  ├── /electricity/rto/fuel-type-data       → get_generation_mix()    [v1]
  ├── /electricity/rto/region-sub-ba-data   → get_demand_forecast()   [NEW - Edwin]
  └── /natural-gas/pri/sum/                 → get_gas_price()         [NEW - Edwin Tier 2]

NYISO OASIS
  ├── /getbiddata?ptid=...                  → get_lmp_prices()        [v1]
  └── /getinterfaceflows                    → get_interconnection_flows() [NEW - Christian]

NOAA NWS
  ├── /alerts/active?area=NY               → get_weather_alerts()    [v1]
  └── /points/{lat},{lon}/forecast/hourly  → get_weather_forecast()  [v1]

RSS / NewsAPI
  └── feeds                                → get_energy_news()       [v1]

Internal (computed)
  ├── rolling Z-score on demand/LMP        → detect_anomaly()        [NEW - Juan]
  └── weighted sub-factor scores           → score_risk_factors()    [NEW - Ismael]
```

---

## Team Assignments

### The User We Are Building For
An **on-call grid analyst** who checks the briefing at 6 AM before the trading window opens.
They need:
- One clear risk verdict (RED/YELLOW/GREEN) they can act on in under 30 seconds
- The 2–3 specific factors driving that verdict — not just "demand is high," but "demand is 18% above 30-day same-hour baseline and rising"
- A push notification if RED or YELLOW fires so they do not have to babysit the terminal
- Confidence that the data is fresh, not stale

---

### Sprint 1 — Tier 1 (Buildable now, existing API access)

---

#### JUAN — Anomaly Detection
**Branch:** `feature/juan-anomaly`
**New function:** `tools/anomaly.py` → `detect_anomaly(demand_mw, lmp_prices)`

**What it does:**
- Maintains a rolling 30-sample window of demand and LMP values (in-memory)
- Computes Z-score for current value vs. window mean/stddev
- Returns a dict: `{ "demand_z": float, "lmp_z": float, "anomaly": bool, "detail": str }`
- Anomaly fires when |Z| > 2.0 on either signal

**Acceptance gates:**
1. Call `detect_anomaly(25000, {"NYC": 145, "LONGIL": 132})` standalone, get a valid dict back
2. Function wired into agent.py TOOL_SCHEMAS, LLM can call it
3. LLM uses anomaly output to strengthen or weaken risk verdict in briefing text

**Why this matters for the analyst:**
> "LMP is 2.4 standard deviations above recent baseline — price spike is statistically abnormal, not just high."

---

#### EDWIN — EIA 24-Hour Demand Forecast
**Branch:** `feature/edwin-forecast`
**New function:** `tools/forecast.py` → `get_demand_forecast()`

**What it does:**
- Calls EIA v2 `/electricity/rto/region-sub-ba-data` endpoint
- Returns next 24 hours of hourly demand forecast for NYISO region
- Returns a dict: `{ "forecast_mw": [list of 24 ints], "peak_hour": str, "peak_mw": int }`

**Acceptance gates:**
1. Call `get_demand_forecast()` standalone, get 24 values back
2. Function wired into agent TOOL_SCHEMAS
3. LLM cites forecast peak in briefing: "Demand expected to peak at 28,400 MW at 4 PM"

**Why this matters for the analyst:**
> "Current demand is nominal but forecast peaks at 28k by afternoon — analyst gets early warning, not a surprise."

---

#### CHRISTIAN — Cross-Regional Interface Flows
**Branch:** `feature/christian-flows`
**New function:** `tools/intercon.py` → `get_interconnection_flows()`

**What it does:**
- Calls NYISO OASIS interface flows endpoint
- Returns current MW flows on NYISO → PJM and NYISO → ISO-NE tie-lines
- Positive = exporting, Negative = importing
- Returns: `{ "PJM_MW": int, "ISONE_MW": int, "net_import_MW": int, "detail": str }`

**Acceptance gates:**
1. Call `get_interconnection_flows()` standalone, get valid flow data (or graceful stub)
2. Wired into TOOL_SCHEMAS
3. LLM uses import dependency to contextualize supply risk: "NYISO importing 1,200 MW from PJM — supply is regionally dependent"

**Why this matters for the analyst:**
> "If NYISO is importing heavily and PJM has a stress event, that import lifeline disappears. The analyst needs to know that dependency."

---

#### ISMAEL — ~~Risk Sub-Factor Scoring~~ REMOVED
Greg feedback: scoring as a decision model is out. The LLM reasons directly
from raw tool outputs and applies the RED/YELLOW/GREEN classification rules
in prompts.py. No formula. No computed number. The agent decides.

Ismael's Tier 1 slot is freed — can pick up a Tier 2 item (cron scheduler
or spark spread) once Edwin and Christian's tools are in.

---

### Sprint 2 — Tier 2 (After Tier 1 gates pass)

---

#### MICHAEL — Web Dashboard (GREENLIT by Greg)
**Branch:** `feature/michael-dashboard`
**New files:**
- `server.py` — Flask/FastAPI thin wrapper, `GET /briefing` endpoint
- `dashboard/` — React app, 5 module components

**What it does:**
- `server.py` runs the agent loop once and returns structured JSON instead of a formatted string
- React dashboard consumes `GET /briefing` and renders 5 live modules

**JSON contract — `GET /briefing` response:**
```json
{
  "risk":   { "level": "YELLOW", "factors": ["LMP NYC $187/MWh", "Heat Warning active", "Demand +32% above avg"] },
  "grid":   { "demand_mw": 24800, "capacity_mw": 33000, "gen_mix": { "gas": 48, "nuclear": 22, "hydro": 14, "wind": 9, "solar": 7 } },
  "weather":{ "active_alerts": ["Heat Advisory — NYC"], "hourly_forecast": [...], "renewable_potential": "low" },
  "market": { "lmp_avg": 148.50, "lmp_by_zone": { "NYC": 155, "LONGIL": 142 }, "spread": 38 },
  "news":   { "headlines": [...], "sentiment": "bearish", "impact_tags": ["demand", "fuel-price"] },
  "alert":  { "sent": true, "priority": "high" }
}
```

**Module → data mapping:**
| Module | Feeds from |
|--------|-----------|
| 01 Risk Level | `risk.level` + `risk.factors` ← LLM briefing text parsed by server.py |
| 02 Grid Status | `grid.demand_mw`, `grid.gen_mix` ← `get_grid_demand()`, `get_generation_mix()` |
| 03 Weather | `weather.active_alerts`, `weather.hourly_forecast` ← `get_weather_alerts()`, `get_weather_forecast()` |
| 04 Market | `market.lmp_by_zone`, `market.spread` ← `get_lmp_prices()` |
| 05 News + Sentiment | `news.headlines`, `news.sentiment` ← `get_energy_news()` |

**Acceptance gates:**
1. `GET /briefing` returns valid JSON matching the contract above
2. Module 01 gauge renders and updates when composite score changes
3. All 5 modules populate from a single API call — no direct EIA/NYISO calls from the frontend
4. Works alongside the terminal output — both A and B outputs run from the same agent loop

**Why server.py first:**
Michael builds `server.py` before touching React. The JSON contract is the stable interface — dashboard components can be built and tested against it independently.

---

| Feature | Owner | Depends On |
|---------|-------|-----------|
| Web Dashboard (server.py + React) | Michael | Tier 1 complete (esp. score_risk_factors for Module 01) |
| Spark Spread / Fleet Commit | Edwin | EIA gas price endpoint |
| Historical 30-Day Baseline | Juan | SQLite store of past EIA pulls |
| Scheduled Auto-Run (cron) | Ismael | All Tier 1 gates complete |

---

### Upgrade Trigger: When to Switch to Claude Opus

The free Nemotron tier handles data retrieval + summarization fine.
Switch to Claude Opus (Anthropic API) when:
- Fleet commit logic is added — spark spread reasoning across competing price signals requires causal inference, not pattern matching
- Probabilistic risk (Bayesian) scoring is added — non-linear multi-variable weighting
- 72-hour forecast window is added — sequential reasoning across extended time series

Cost gate: Anthropic API upgrade requires Greg's sign-off. Document the capability gap first, then request.

---

## v2 Feature Summary Table

| # | Feature | Tier | Owner | API/Source | Status |
|---|---------|------|-------|-----------|--------|
| 1 | Anomaly Detection (Z-score) | 1 | Juan | Internal | Unstarted |
| 2 | EIA 24hr Demand Forecast | 1 | Edwin | EIA v2 | Unstarted |
| 3 | Cross-Regional Flows | 1 | Christian | NYISO OASIS | Unstarted |
| 4 | Risk Sub-Factor Scoring | — | — | REMOVED — LLM decides directly | Greg feedback |
| 5 | Spark Spread / Fleet Commit | 2 | Edwin | EIA gas prices | Unstarted |
| 6 | Historical 30-Day Baseline | 2 | Juan | SQLite | Unstarted |
| 7 | Web Dashboard (server.py + React) | 2 | Michael | Flask/FastAPI + React | Unstarted — GREENLIT |
| 8 | Spark Spread / Fleet Commit | 2 | Edwin | EIA gas prices | Unstarted |
| 9 | Historical 30-Day Baseline | 2 | Juan | SQLite | Unstarted |
| 10 | Scheduled Auto-Run | 2 | Ismael | cron / APScheduler | Unstarted |
| 11 | Wildfire/Flood on Transmission | 3 | TBD | NASA FIRMS / USGS | Research |
| 12 | Probabilistic Risk (Bayesian) | 3 | TBD | Internal | Research |
| 13 | Carbon Intensity | 3 | Michael | WattTime/ElecMaps | After dashboard ships |

---

*Saved 2026-05-01. Cross-reference: V2_PLANS.md for full research notes, SPEC.md for v1 API details.*
