"""
Stub versions of all 5 tools — return realistic fake data so the agent
loop can run end-to-end without any API keys.

Usage: set USE_STUBS=true in your .env to use these instead of real tools.
"""

def get_grid_demand() -> str:
    return (
        "Grid demand — New York Independent System Operator as of 2026-04-26T14:00:\n"
        "  Current demand: 14,820 MWh\n"
        "  5-hour avg: 11,200 MWh (32.3% above recent avg)"
    )

def get_generation_mix() -> str:
    return (
        "Generation mix — New York Independent System Operator as of 2026-04-26T14:00:\n"
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
        "  2026-04-26 14:00  97°F  Wind: 8 mph SW  Sunny\n"
        "  2026-04-26 15:00  98°F  Wind: 7 mph SW  Sunny\n"
        "  2026-04-26 16:00  97°F  Wind: 7 mph SW  Mostly Sunny\n"
        "  2026-04-26 17:00  95°F  Wind: 8 mph SW  Mostly Sunny\n"
        "  2026-04-26 18:00  93°F  Wind: 9 mph SW  Partly Cloudy\n"
        "  2026-04-26 19:00  90°F  Wind: 10 mph SW  Partly Cloudy\n"
        "  2026-04-26 20:00  87°F  Wind: 10 mph W  Mostly Clear\n"
        "  2026-04-26 21:00  84°F  Wind: 9 mph W  Clear\n"
        "  2026-04-26 22:00  81°F  Wind: 8 mph W  Clear\n"
        "  2026-04-26 23:00  79°F  Wind: 7 mph NW  Clear\n"
        "  2026-04-27 00:00  77°F  Wind: 6 mph NW  Clear\n"
        "  2026-04-27 01:00  75°F  Wind: 5 mph NW  Clear"
    )

def get_energy_news() -> str:
    return (
        "[Utility Dive] (Sun, 26 Apr 2026) NYISO issues conservation alert as heat wave drives record demand\n"
        "[OilPrice.com] (Sun, 26 Apr 2026) Natural gas prices spike 18% ahead of eastern seaboard heat event\n"
        "[Power Magazine] (Sat, 25 Apr 2026) Grid operators warn of tight capacity margins through Tuesday"
    )

def get_lmp_prices() -> str:
    return (
        "Day-ahead LMP — NYISO zones as of 2026-04-26T14:00 ET:\n"
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
