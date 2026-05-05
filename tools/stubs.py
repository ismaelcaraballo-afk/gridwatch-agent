"""
Stub versions of all tools — return realistic fake data so the agent
loop can run end-to-end without any API keys.

Usage: set USE_STUBS=true in your .env to use these instead of real tools.
"""

def get_grid_demand() -> str:
    return (
        "Grid demand — New York Independent System Operator as of 2026-05-06T14:00:\n"
        "  Current demand: 14,820 MWh\n"
        "  5-hour avg: 11,200 MWh (32.3% above recent avg)"
    )

def get_generation_mix() -> str:
    return (
        "Generation mix — New York Independent System Operator as of 2026-05-06T14:00:\n"
        "  Natural Gas: 7,410 MWh (50.0%)\n"
        "  Nuclear: 3,100 MWh (20.9%)\n"
        "  Wind: 1,950 MWh (13.2%)\n"
        "  Hydro: 1,480 MWh (10.0%)\n"
        "  Solar: 880 MWh (5.9%)\n"
        "  → Clean total: 50.0% | Fossil total: 50.0%"
    )

def get_weather_alerts() -> str:
    return (
        "Weather alerts — New York City:\n"
        "  [SEVERE] Excessive Heat Warning — Excessive Heat Warning until 8 PM EDT today"
    )

def get_weather_forecast() -> str:
    return (
        "12-hour forecast — New York City:\n"
        "  2026-05-06 14:00  97°F  Wind: 8 mph SW  Sunny\n"
        "  2026-05-06 15:00  98°F  Wind: 7 mph SW  Sunny\n"
        "  2026-05-06 16:00  97°F  Wind: 7 mph SW  Mostly Sunny\n"
        "  2026-05-06 17:00  95°F  Wind: 8 mph SW  Mostly Sunny\n"
        "  2026-05-06 18:00  93°F  Wind: 9 mph SW  Partly Cloudy\n"
        "  2026-05-06 19:00  90°F  Wind: 10 mph SW  Partly Cloudy\n"
        "  2026-05-06 20:00  87°F  Wind: 10 mph W  Mostly Clear\n"
        "  2026-05-06 21:00  84°F  Wind: 9 mph W  Clear\n"
        "  2026-05-06 22:00  81°F  Wind: 8 mph W  Clear\n"
        "  2026-05-06 23:00  79°F  Wind: 7 mph NW  Clear\n"
        "  2026-05-07 00:00  77°F  Wind: 6 mph NW  Clear\n"
        "  2026-05-07 01:00  75°F  Wind: 5 mph NW  Clear"
    )

def get_energy_news() -> str:
    return (
        "[Utility Dive] (Wed, 06 May 2026) NYISO issues conservation alert as heat wave drives record demand\n"
        "[OilPrice.com] (Wed, 06 May 2026) Natural gas prices spike 18% ahead of eastern seaboard heat event\n"
        "[Power Magazine] (Tue, 05 May 2026) Grid operators warn of tight capacity margins through Thursday"
    )

def get_lmp_prices() -> str:
    return (
        "Day-ahead LMP — NYISO zones as of 2026-05-06T14:00 ET:\n"
        "  N.Y.C.: $187.42/MWh\n"
        "  LONGIL: $172.18/MWh\n"
        "  HUD VL: $148.05/MWh\n"
        "  DUNWOD: $142.91/MWh\n"
        "  MILLWD: $138.60/MWh\n"
        "  CAPITL: $121.33/MWh\n"
        "  CENTRL: $108.74/MWh\n"
        "  MHK VL: $104.22/MWh\n"
        "  GENESE: $96.81/MWh\n"
        "  NORTH: $89.45/MWh\n"
        "  WEST: $84.10/MWh\n"
        "  → Zone avg: $126.71/MWh | Spread (max − min): $103.32/MWh"
    )

def get_henry_hub_price() -> str:
    return (
        "Henry Hub spot price as of 2026-05-06:\n"
        "  $3.84/MMBtu (▲ $0.22 vs prior day (2026-05-05))"
    )

def detect_anomaly(demand_mw: float, lmp_prices: dict) -> str:
    return (
        "Anomaly detection — NYISO:\n"
        "  Demand Z-score: +2.4  ← ANOMALY (threshold ±2.0)\n"
        "  LMP Z-score: +1.8     ← normal\n"
        "  Window size: 30 samples\n"
        f"  Detail: Demand {demand_mw:,.0f} MW is 2.4 std deviations above recent baseline."
    )

def get_demand_forecast() -> str:
    return (
        "24-hour demand forecast — NYISO:\n"
        "  2026-05-06 15:00  15,200 MW\n"
        "  2026-05-06 16:00  16,800 MW\n"
        "  2026-05-06 17:00  18,100 MW\n"
        "  2026-05-06 18:00  19,400 MW\n"
        "  2026-05-06 19:00  18,900 MW\n"
        "  2026-05-06 20:00  17,200 MW\n"
        "  2026-05-06 21:00  15,800 MW\n"
        "  2026-05-06 22:00  14,400 MW\n"
        "  2026-05-06 23:00  13,100 MW\n"
        "  2026-05-07 00:00  12,200 MW\n"
        "  ... (24 hours total)\n"
        "  Peak: 19,400 MW at 2026-05-06 18:00"
    )

def get_interconnection_flows() -> str:
    return (
        "NYISO interface flows — current hour:\n"
        "  NYISO → PJM:    -1,240 MW  (importing)\n"
        "  NYISO → ISO-NE:   +380 MW  (exporting)\n"
        "  Net position: importing 860 MW from neighbors\n"
        "  Detail: NYISO is drawing from PJM — regional supply dependency present."
    )

def trigger_demand_response(forecast_peak_mw: float, forecast_peak_time: str, current_mw: float) -> str:
    return (
        f"Demand response ACTIVATED — signal sent to enrolled customers via gridwatch-dr. "
        f"Forecast peak: {forecast_peak_mw:,.0f} MW at {forecast_peak_time}. "
        f"Load reduction requested immediately."
    )

def evaluate_maintenance_schedule(forecast_peak_mw: float, forecast_peak_time: str) -> str:
    return (
        "Maintenance schedule evaluation:\n"
        "  Ravenswood Unit 3 (2026-05-06 14:00–18:00) — POSTPONE\n"
        "    Capacity offline: 950 MW | forecast peak 19,400 MW at 2026-05-06 18:00 "
        "falls within this window. Recommend rescheduling to 23:00–06:00.\n"
        "    Task: Turbine blade inspection and cooling system flush\n"
        "  Astoria Energy II (2026-05-06 22:00–02:00) — APPROVE\n"
        "    Capacity offline: 500 MW | forecast peak does not overlap this window.\n"
        "  Summary: 1 window(s) APPROVED, 1 window(s) POSTPONED."
    )
