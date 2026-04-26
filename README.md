# GridWatch

An AI agent for energy operations analysts. Runs at shift start, pulls real-time grid demand, weather alerts, and energy headlines, then delivers a prioritized briefing with a Red/Yellow/Green risk level — replacing the 30-minute manual morning routine.

## What it does

- Calls 5 tools in parallel: EIA grid demand, EIA generation mix, NOAA weather alerts, NOAA forecast, energy news RSS
- Reasons across all five data sources and produces a risk assessment
- **Human checkpoint**: if risk is RED, the agent pauses and asks the analyst to confirm before finalizing
- Outputs a structured briefing: risk level, grid status, weather flags, headlines, and a recommended action

## Team

| Member | File | Role |
|--------|------|------|
| Ismael | `agent.py` | Agent loop + human checkpoint |
| Michael | `prompts.py` | System prompt + risk logic |
| Edwin | `tools/grid.py` | EIA API — grid demand + generation mix |
| Christian | `tools/weather.py` | NOAA API — weather alerts + forecast |
| Juan | `tools/news.py` | RSS feeds — energy headlines |

## Setup

**1. Clone the repo**
```bash
git clone https://github.com/ismaelcaraballo-afk/gridwatch-agent
cd gridwatch-agent
```

**2. Create a virtual environment**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

**3. Install dependencies**
```bash
pip install -r requirements.txt
```

**4. Create a `.env` file in the root**
```
OPENROUTER_API_KEY=your_openrouter_key
EIA_API_KEY=your_eia_key
```

- **OpenRouter key**: [openrouter.ai](https://openrouter.ai) — free account
- **EIA key**: [eia.gov/opendata/register.php](https://www.eia.gov/opendata/register.php) — free, instant approval

## Run it

```bash
python agent.py
```

## How it works

```
python agent.py
      ↓
[step 1] thinking...
  → calling get_grid_demand...
  → calling get_generation_mix...
  → calling get_weather_alerts...
  → calling get_weather_forecast...
  → calling get_energy_news...

[step 2] thinking...
  → synthesizes all five data sources
  → outputs risk level + briefing

# If RED risk detected:
⚠️  HIGH RISK CONDITIONS DETECTED
Should I escalate this briefing? (yes/no):
```

## Data sources

| Source | API | Key required |
|--------|-----|-------------|
| EIA real-time grid demand | `api.eia.gov/v2/electricity/rto/demand/data` | Yes — free |
| EIA generation by fuel type | `api.eia.gov/v2/electricity/rto/fuel-type-data` | Yes — free |
| NOAA weather alerts | `api.weather.gov/alerts/active` | No |
| NOAA hourly forecast | `api.weather.gov/points/{lat},{lon}` | No |
| Energy news RSS | EIA Today in Energy, Reuters | No |

## Risk levels

| Level | Condition |
|-------|-----------|
| 🔴 RED | Demand spike >15% above average AND active severe weather alert |
| 🟡 YELLOW | Either condition alone |
| 🟢 GREEN | Normal demand, no active alerts |
