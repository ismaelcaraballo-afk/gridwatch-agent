import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from dotenv import load_dotenv

load_dotenv()

from prompts import SYSTEM_PROMPT

USE_STUBS = os.environ.get("USE_STUBS", "false").lower() == "true"

if USE_STUBS:
    from tools.stubs import get_grid_demand, get_generation_mix
    from tools.stubs import get_weather_alerts, get_weather_forecast
    from tools.stubs import get_energy_news
    from tools.stubs import get_lmp_prices
    print("[STUB MODE] Using fake data — set USE_STUBS=false to use real APIs")
else:
    from tools.grid import get_grid_demand, get_generation_mix
    from tools.weather import get_weather_alerts, get_weather_forecast
    from tools.news import get_energy_news
    from tools.market import get_lmp_prices

from tools.alert import send_alert

API_KEY = os.environ["OPENROUTER_API_KEY"]
MODEL = os.environ.get("OPENROUTER_MODEL", "nvidia/nemotron-3-super-120b-a12b:free")
API_URL = "https://openrouter.ai/api/v1/chat/completions"
MAX_TOOL_WORKERS = 8

# ── Tool registry ──────────────────────────────────────────────────────────────

TOOLS = {
    "get_grid_demand": get_grid_demand,
    "get_generation_mix": get_generation_mix,
    "get_weather_alerts": get_weather_alerts,
    "get_weather_forecast": get_weather_forecast,
    "get_energy_news": get_energy_news,
    "get_lmp_prices": get_lmp_prices,
    "send_alert": send_alert,
}

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "get_grid_demand",
            "description": "Get current real-time electricity demand by US grid region.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_generation_mix",
            "description": "Get current electricity generation breakdown by fuel type (solar, wind, gas, nuclear).",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather_alerts",
            "description": "Get active NOAA severe weather alerts for the grid service area.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather_forecast",
            "description": "Get the 48-hour hourly weather forecast for the grid service area.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_energy_news",
            "description": "Get recent energy industry headlines from public RSS feeds.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_lmp_prices",
            "description": "Get current-hour NYISO day-ahead Locational Marginal Prices ($/MWh) by zone, plus zone average and spread.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "send_alert",
            "description": "Push a risk alert notification to the on-call analyst via ntfy.sh. Call this after forming your risk assessment — before outputting the final briefing. GREEN risk skips the push; RED and YELLOW fire immediately.",
            "parameters": {
                "type": "object",
                "properties": {
                    "risk_level": {
                        "type": "string",
                        "enum": ["RED", "YELLOW", "GREEN"],
                        "description": "Risk level determined from the grid and weather data.",
                    },
                    "summary": {
                        "type": "string",
                        "description": "One-sentence briefing summary to include in the notification body.",
                    },
                },
                "required": ["risk_level", "summary"],
            },
        },
    },
]

# ── Tool execution ─────────────────────────────────────────────────────────────

def _execute_tool(call: dict) -> tuple[str, str]:
    fn_name = call["function"]["name"]
    raw_args = call["function"].get("arguments", "{}")
    try:
        kwargs = json.loads(raw_args) if raw_args else {}
    except json.JSONDecodeError:
        print(f"  ✗ Malformed args for {fn_name}: {raw_args}")
        kwargs = {}
    label = f"{fn_name}({', '.join(f'{k}={v!r}' for k, v in kwargs.items()) if kwargs else ''})"
    print(f"  → calling {label}...")
    try:
        result = TOOLS[fn_name](**kwargs) if kwargs else TOOLS[fn_name]()
    except Exception as e:
        result = f"Tool error ({fn_name}): {e}"
    print(f"  ← {result[:80]!r}" if len(result) > 80 else f"  ← {result!r}")
    return call["id"], result


# ── Agent loop ─────────────────────────────────────────────────────────────────

def run_gridwatch(max_steps: int = 10):
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": "Run the morning grid briefing. Check demand, weather, and news. Give me the risk level and what I need to know right now."}
    ]
    step = 0

    while step < max_steps:
        step += 1
        print(f"\n[step {step}] thinking...")

        try:
            resp = requests.post(
                API_URL,
                headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
                json={"model": MODEL, "messages": messages, "tools": TOOL_SCHEMAS},
                timeout=60,
            )
            resp.raise_for_status()
        except requests.RequestException as e:
            print(f"  ✗ API error: {e}")
            return "Agent stopped — API error."

        message = resp.json()["choices"][0]["message"]
        messages.append(message)

        if message.get("tool_calls"):
            valid_calls = [
                call for call in message["tool_calls"]
                if call["function"]["name"] in TOOLS
            ]
            for call in message["tool_calls"]:
                if call["function"]["name"] not in TOOLS:
                    print(f"  ✗ Unknown tool requested: {call['function']['name']} — skipping")

            results = {}
            workers = min(len(valid_calls), MAX_TOOL_WORKERS)
            with ThreadPoolExecutor(max_workers=workers) as pool:
                futures = {pool.submit(_execute_tool, call): call for call in valid_calls}
                for future in as_completed(futures):
                    call_id, result = future.result()
                    results[call_id] = result

            for call in valid_calls:
                messages.append({
                    "role": "tool",
                    "tool_call_id": call["id"],
                    "content": results[call["id"]],
                })

        else:
            print("\n" + "="*50)
            print("GRIDWATCH BRIEFING")
            print("="*50)
            print(message["content"])
            return message["content"]

    return "Max steps reached."


if __name__ == "__main__":
    run_gridwatch()
