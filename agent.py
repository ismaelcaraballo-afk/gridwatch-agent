import os
import requests
from dotenv import load_dotenv

from prompts import SYSTEM_PROMPT
from tools.grid import get_grid_demand, get_generation_mix
from tools.weather import get_weather_alerts, get_weather_forecast
from tools.news import get_energy_news

load_dotenv()

API_KEY = os.environ["OPENROUTER_API_KEY"]
MODEL = "tencent/hy3-preview:free"
API_URL = "https://openrouter.ai/api/v1/chat/completions"

# ── Tool registry ──────────────────────────────────────────────────────────────

TOOLS = {
    "get_grid_demand": get_grid_demand,
    "get_generation_mix": get_generation_mix,
    "get_weather_alerts": get_weather_alerts,
    "get_weather_forecast": get_weather_forecast,
    "get_energy_news": get_energy_news,
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
]

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

        resp = requests.post(
            API_URL,
            headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
            json={"model": MODEL, "messages": messages, "tools": TOOL_SCHEMAS},
            timeout=60,
        )
        resp.raise_for_status()
        message = resp.json()["choices"][0]["message"]
        messages.append(message)

        if message.get("tool_calls"):
            for call in message["tool_calls"]:
                fn_name = call["function"]["name"]
                print(f"  → calling {fn_name}...")
                result = TOOLS[fn_name]()
                print(f"  ← got {len(result)} chars")
                messages.append({
                    "role": "tool",
                    "tool_call_id": call["id"],
                    "content": result,
                })

        # human checkpoint — agent flags RED and pauses for confirmation
        elif message.get("content") and "RED" in message["content"].upper() and "confirm" not in " ".join(m.get("content", "") for m in messages if m.get("role") == "user").lower():
            print("\n" + "="*50)
            print("⚠️  HIGH RISK CONDITIONS DETECTED")
            print("="*50)
            print(message["content"])
            confirm = input("\nShould I escalate this briefing? (yes/no): ").strip().lower()
            messages.append({"role": "user", "content": f"Analyst response: {confirm}. Finalize the briefing."})

        else:
            print("\n" + "="*50)
            print("GRIDWATCH BRIEFING")
            print("="*50)
            print(message["content"])
            return message["content"]

    return "Max steps reached."


if __name__ == "__main__":
    run_gridwatch()
