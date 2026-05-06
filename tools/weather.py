import requests

from tools.http import get_with_backoff

# Hardcoded to NYC (40.7128° N, 74.0060° W)
# To change location: update LAT and LON below
LAT = 40.7128
LON = -74.0060
LOCATION_LABEL = "New York City"

NOAA_BASE = "https://api.weather.gov"
HEADERS = {"User-Agent": "gridwatch-agent/1.0 (energy ops briefing tool)"}


def get_weather_alerts() -> str:
    """Get active NWS severe weather alerts for the NYC area."""
    try:
        resp = get_with_backoff(
            f"{NOAA_BASE}/alerts/active",
            params={"point": f"{LAT},{LON}"},
            headers=HEADERS,
            timeout=30,
        )
        features = resp.json().get("features", [])
    except Exception:
        return f"Weather alerts unavailable for {LOCATION_LABEL}."

    if not features:
        return f"Weather alerts — {LOCATION_LABEL}:\n  No active alerts."

    lines = [f"Weather alerts — {LOCATION_LABEL}:"]
    for feature in features:
        props = feature.get("properties", {})
        event = props.get("event", "Unknown")
        headline = props.get("headline", "")
        severity = props.get("severity", "")
        ends = props.get("ends") or props.get("expires", "unknown")
        lines.append(f"  [{severity.upper()}] {event}")
        if headline:
            lines.append(f"    {headline}")
        lines.append(f"    Expires: {ends}")

    return "\n".join(lines)


def get_weather_forecast() -> str:
    """Get the next 48-hour hourly weather forecast for NYC from NOAA."""
    try:
        points_resp = get_with_backoff(
            f"{NOAA_BASE}/points/{LAT},{LON}",
            headers=HEADERS,
            timeout=30,
        )
        forecast_hourly_url = points_resp.json().get("properties", {}).get("forecastHourly")
        if not forecast_hourly_url:
            return f"Weather forecast unavailable for {LOCATION_LABEL}."

        forecast_resp = get_with_backoff(
            forecast_hourly_url,
            headers=HEADERS,
            timeout=30,
        )
        periods = forecast_resp.json().get("properties", {}).get("periods", [])[:48]
        if not periods:
            return f"Weather forecast unavailable for {LOCATION_LABEL}."

        lines = [f"48-hour forecast — {LOCATION_LABEL}:"]
        for period in periods:
            temp = period.get("temperature", "?")
            unit = period.get("temperatureUnit", "F")
            wind_speed = period.get("windSpeed", "")
            wind_dir = period.get("windDirection", "")
            short = period.get("shortForecast", "")
            start = period.get("startTime", "")[:16].replace("T", " ")
            lines.append(f"  {start}  {temp}°{unit}  Wind: {wind_speed} {wind_dir}  {short}")

        return "\n".join(lines)
    except Exception:
        return f"Weather forecast unavailable for {LOCATION_LABEL}."


if __name__ == "__main__":
    print(get_weather_alerts())
    print()
    print(get_weather_forecast())
