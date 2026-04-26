import requests

NOAA_BASE = "https://api.weather.gov"

# Default coordinates: New York City (covers Con Edison / NY grid territory)
# Ismael can change these to any US city
DEFAULT_LAT = 40.7128
DEFAULT_LON = -74.0060

def get_weather_alerts() -> str:
    """Get active NOAA severe weather alerts for the grid service area."""
    resp = requests.get(
        f"{NOAA_BASE}/alerts/active",
        params={"point": f"{DEFAULT_LAT},{DEFAULT_LON}"},
        headers={"User-Agent": "gridwatch-agent/1.0"},
        timeout=15,
    )
    resp.raise_for_status()
    features = resp.json().get("features", [])
    if not features:
        return "No active weather alerts for this area."
    lines = []
    for f in features[:5]:
        props = f.get("properties", {})
        lines.append(
            f"[{props.get('severity', '?').upper()}] {props.get('event', '?')} — "
            f"{props.get('headline', 'No headline')}"
        )
    return "\n".join(lines)


def get_weather_forecast() -> str:
    """Get the 48-hour hourly forecast for the grid service area."""
    # Step 1: resolve grid point
    point_resp = requests.get(
        f"{NOAA_BASE}/points/{DEFAULT_LAT},{DEFAULT_LON}",
        headers={"User-Agent": "gridwatch-agent/1.0"},
        timeout=15,
    )
    point_resp.raise_for_status()
    forecast_url = point_resp.json()["properties"]["forecastHourly"]

    # Step 2: get hourly forecast
    forecast_resp = requests.get(
        forecast_url,
        headers={"User-Agent": "gridwatch-agent/1.0"},
        timeout=15,
    )
    forecast_resp.raise_for_status()
    periods = forecast_resp.json()["properties"]["periods"][:12]  # next 12 hours
    lines = ["Next 12-hour forecast:"]
    for p in periods:
        lines.append(
            f"  {p['startTime'][11:16]} — {p['temperature']}°{p['temperatureUnit']}, "
            f"{p['shortForecast']}, Wind: {p['windSpeed']} {p['windDirection']}"
        )
    return "\n".join(lines)
