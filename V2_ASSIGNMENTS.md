# GridWatch v2 — Team Assignment Map
*Sprint: 2026-05-02 → 2026-05-09 | Presentation: Saturday May 9*

---

## The Goal
Ship a fully autonomous grid risk agent with anomaly detection, 24hr demand
forecasting, cross-regional flow awareness, and a live React dashboard.
No human interaction at any step. LLM decides everything from live data.

---

## Assignment Map

```
SPRINT WEEK — MAY 2 TO MAY 9
─────────────────────────────────────────────────────────────────────────

     SAT 5/2   SUN 5/3   MON 5/4   TUE 5/5   WED 5/6   THU 5/7   FRI 5/8
     TODAY     BUILD     BUILD     GATE 1    GATE 2    INTEGRATE  DEMO
                                   (solo)    (wired)   TEST       REHEARSAL

JUAN  ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░[PR]
      detect_anomaly()
      tools/anomaly.py
      branch: feature/juan-anomaly

EDWIN ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░[PR]
      get_demand_forecast()
      tools/forecast.py
      branch: feature/edwin-forecast

CHRSN ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░[PR]
      get_interconnection_flows()
      tools/intercon.py
      branch: feature/christian-flows

MCHEL ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░[PR]
      server.py  (Wed 5/6)
      dashboard/ React 5 modules (Thu-Fri)
      branch: feature/michael-dashboard

ISMAL ──────────────── MERGE & INTEGRATE ────────────────────────[DEMO]
      reviews PRs, merges Tue-Wed, integration test Thu, rehearsal Fri
```

---

## Juan — Anomaly Detection

**Branch:** `feature/juan-anomaly`
**File:** `tools/anomaly.py`
**Due:** Tuesday May 5 (PR open by EOD)

```python
# Function signature
def detect_anomaly(demand_mw: float, lmp_prices: dict) -> str:
```

**What it does:**
- Maintains a rolling 30-sample window in memory (module-level list)
- Computes Z-score for current demand and average LMP vs. window
- Fires anomaly flag when |Z| > 2.0 on either signal
- Returns a plain string the LLM can read

**Return format:**
```
Anomaly detection — NYISO:
  Demand Z-score: +2.4  ← ANOMALY (threshold ±2.0)
  LMP Z-score: +1.8     ← normal
  Window size: 30 samples
  Detail: Demand 14,820 MWh is 2.4 std deviations above recent baseline.
```

**Gate 1 (Monday):** Call standalone, get a valid string back
```bash
cd gridwatch-agent && .venv/bin/python3 -c "
from tools.anomaly import detect_anomaly
print(detect_anomaly(25000, {'NYC': 187, 'LONGIL': 172}))
"
```

**Gate 2 (Tuesday):** Add to TOOL_SCHEMAS and TOOLS dict in agent.py — LLM
can call it and references it in the briefing text.

---

## Edwin — EIA 24-Hour Demand Forecast

**Branch:** `feature/edwin-forecast`
**File:** `tools/forecast.py`
**Due:** Tuesday May 5 (PR open by EOD)

```python
# Function signature
def get_demand_forecast() -> str:
```

**What it does:**
- Calls EIA v2 `/electricity/rto/region-sub-ba-data` endpoint
- Returns next 24 hours of hourly demand forecast for NYISO
- Uses `get_with_backoff` from `tools/http.py` (already in repo)

**Return format:**
```
24-hour demand forecast — NYISO:
  2026-05-02 15:00  14,200 MW
  2026-05-02 16:00  15,100 MW
  ...
  Peak: 18,400 MW at 2026-05-02 18:00
  Current demand vs forecast peak: +24% expected by 18:00
```

**Gate 1 (Monday):** Call standalone, get 24 values back
```bash
.venv/bin/python3 -c "from tools.forecast import get_demand_forecast; print(get_demand_forecast())"
```

**Gate 2 (Tuesday):** Wired into agent. LLM cites forecast peak in briefing:
> "Demand expected to peak at 18,400 MW at 18:00 — 24% above current."

**EIA endpoint reference:**
```
GET https://api.eia.gov/v2/electricity/rto/region-sub-ba-data/data/
  ?api_key={EIA_API_KEY}
  &frequency=hourly
  &data[0]=value
  &facets[subba][]=ZONA   ← NYISO sub-region
  &sort[0][column]=period
  &sort[0][direction]=asc
  &length=24
```
EIA_API_KEY is already in `.env`.

---

## Christian — Cross-Regional Interface Flows

**Branch:** `feature/christian-flows`
**File:** `tools/intercon.py`
**Due:** Tuesday May 5 (PR open by EOD)

```python
# Function signature
def get_interconnection_flows() -> str:
```

**What it does:**
- Calls NYISO OASIS interface flows endpoint (no key required)
- Returns current MW flows on NYISO ↔ PJM and NYISO ↔ ISO-NE tie-lines
- Positive = exporting, Negative = importing

**Return format:**
```
NYISO interface flows — current hour:
  NYISO → PJM:    -1,240 MW  (importing)
  NYISO → ISO-NE:   +380 MW  (exporting)
  Net position: importing 860 MW from neighbors
  Detail: NYISO is drawing from PJM — regional supply dependency present.
```

**Gate 1 (Monday):** Call standalone, get valid flow data back (or graceful
"data unavailable" string — do not raise an exception)

**Gate 2 (Tuesday):** Wired into agent. LLM references import dependency:
> "NYISO importing 1,240 MW from PJM — if PJM tightens, that supply disappears."

**NYISO OASIS endpoint:**
```
http://mis.nyiso.com/public/csv/ExternalLimitsFlows/{YYYYMMDD}ExternalLimitsFlows.csv
```
Same CSV pattern as the LMP tool already in `tools/market.py` — look at
`_fetch_dam_csv()` for the pattern to follow.

---

## Michael — server.py + React Dashboard

**Branch:** `feature/michael-dashboard`
**Files:** `server.py`, `dashboard/` (React app)
**Due:** server.py Wednesday May 6, full dashboard Friday May 8

### Part 1 — server.py (Wed May 6)

Thin Flask/FastAPI wrapper. One endpoint. Runs the agent loop once and
returns structured JSON instead of printing to terminal.

```python
# GET /briefing → runs agent, returns:
{
  "risk":    { "level": "YELLOW", "factors": ["LMP NYC $187/MWh", "Heat Warning active", "Demand +32% above avg"] },
  "grid":    { "demand_mw": 14820, "gen_mix": { "Natural Gas": 50.0, "Nuclear": 20.9, "Wind": 13.2, "Hydro": 10.0, "Solar": 5.9 } },
  "weather": { "active_alerts": ["[SEVERE] Excessive Heat Warning — until 8 PM EDT"], "forecast_12h": "97°F peak at 15:00, clearing by 21:00" },
  "market":  { "lmp_avg": 126.71, "lmp_peak_zone": "N.Y.C.", "lmp_peak": 187.42, "spread": 103.32 },
  "news":    { "headlines": ["NYISO issues conservation alert...", "Natural gas prices spike 18%..."] },
  "alert":   { "sent": true, "level": "YELLOW", "confirmation": "Alert sent → ntfy.sh/gridwatch-ismael" }
}
```

**Gate (Wed):** `curl http://localhost:5000/briefing` returns valid JSON
matching the shape above.

### Part 2 — React Dashboard (Thu-Fri)

5 modules, single `GET /briefing` call on load. No direct EIA/NYISO calls
from the frontend — everything comes through server.py.

| Module | Data field | What it shows |
|--------|-----------|--------------|
| 01 RISK LEVEL | `risk.level` + `risk.factors` | RED/YELLOW/GREEN + bullet list of cited factors |
| 02 GRID STATUS | `grid.demand_mw` + `grid.gen_mix` | Demand number + fuel breakdown (bar or donut) |
| 03 WEATHER | `weather.active_alerts` + `weather.forecast_12h` | Alert badge + forecast summary |
| 04 MARKET | `market.lmp_peak` + `market.lmp_avg` + `market.spread` | Price numbers by zone |
| 05 NEWS | `news.headlines` | Headline list |

**Gate (Fri):** All 5 modules populate from a single `/briefing` call.
Dashboard works in browser. No blank panels.

---

## Ismael — Integration Lead

**No new tool file.** Your job this week is to keep the build moving.

| Day | Task |
|-----|------|
| Sat-Sun | Send assignments, answer questions |
| Mon | Check in — is everyone unblocked? |
| Tue | Review Juan/Edwin/Christian PRs as they open |
| Wed | Merge all three tool PRs into main, verify agent runs with new tools |
| Thu | Review Michael's server.py PR, help with React if needed |
| Fri | Full integration test: agent runs → push fires → dashboard populates |
| Fri | Demo rehearsal — full run-through with the team |

---

## Dependencies

```
Juan (anomaly)     ──┐
Edwin (forecast)   ──┼──► main merge (Wed) ──► Michael dashboard (Thu-Fri)
Christian (flows)  ──┘

Michael server.py (Wed) ──► React modules feed from /briefing (Thu-Fri)
```

Michael can build modules 02-05 before the tool PRs merge — he can stub
the JSON in server.py for now. Module 01 (RISK LEVEL) just needs the
briefing text parsed, no dependency on the new tools.

---

## How to Submit

1. Branch off main: `git checkout -b feature/your-name-feature`
2. Build your file in `tools/`
3. Test Gate 1 standalone
4. Wire into `agent.py` (TOOLS dict + TOOL_SCHEMAS list)
5. Test Gate 2 with agent
6. Open PR against main — tag Ismael for review

**Pattern to follow:** look at `tools/market.py` (LMP tool) — same structure,
same `get_with_backoff` import from `tools/http.py`, same string return format.

---

## What the Demo Looks Like

```
1. Terminal: python3 agent.py --interval 60  (agent starts, no human needed)
2. Agent fires — tool table appears, briefing prints
3. Phone receives ntfy.sh push notification (if RED or YELLOW)
4. Browser: open dashboard → all 5 modules populated from /briefing
5. Story: "It ran itself. It decided. It told us."
```

---

*GridWatch v2 | Pursuit Cycle 4 | Ismael Caraballo (lead)*
*Teammates: Juan · Edwin · Christian · Michael*
