import argparse
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box

console = Console()

load_dotenv()

from prompts import SYSTEM_PROMPT

USE_STUBS = os.environ.get("USE_STUBS", "false").lower() == "true"

if USE_STUBS:
    from tools.stubs import get_grid_demand, get_generation_mix
    from tools.stubs import get_weather_alerts, get_weather_forecast
    from tools.stubs import get_energy_news
    from tools.stubs import get_lmp_prices
    console.print("[yellow]⚠  STUB MODE — using fake data[/yellow]")
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

def _execute_tool(call: dict) -> tuple[str, str, float]:
    fn_name = call["function"]["name"]
    raw_args = call["function"].get("arguments", "{}")
    try:
        kwargs = json.loads(raw_args) if raw_args else {}
    except json.JSONDecodeError:
        console.print(f"  [red]✗ Malformed args for {fn_name}[/red]")
        kwargs = {}
    t0 = time.time()
    try:
        result = TOOLS[fn_name](**kwargs) if kwargs else TOOLS[fn_name]()
    except Exception as e:
        result = f"Tool error ({fn_name}): {e}"
    elapsed = time.time() - t0
    return call["id"], result, fn_name, elapsed, kwargs


# ── Display helpers ────────────────────────────────────────────────────────────

RISK_STYLES = {
    "RED":    ("red",    "🔴"),
    "YELLOW": ("yellow", "🟡"),
    "GREEN":  ("green",  "🟢"),
}

def _print_banner():
    console.print()
    console.print(Panel.fit(
        "[bold white]GRIDWATCH[/bold white]  [dim]Autonomous Grid Risk Agent[/dim]",
        border_style="dim white",
        padding=(0, 2),
    ))
    console.print()

def _print_tool_table(tool_results: list):
    table = Table(box=box.SIMPLE, show_header=True, header_style="dim")
    table.add_column("tool", style="cyan", no_wrap=True)
    table.add_column("status", justify="center")
    table.add_column("time", justify="right", style="dim")
    for fn_name, result, elapsed in tool_results:
        ok = not result.startswith("Tool error")
        status = "[green]✓[/green]" if ok else "[red]✗[/red]"
        table.add_row(fn_name, status, f"{elapsed:.1f}s")
    console.print(table)

def _print_briefing(content: str):
    level = "GREEN"
    if "🔴" in content or "RED" in content.upper().split("RISK")[0][:20]:
        level = "RED"
    elif "🟡" in content or "YELLOW" in content.upper().split("RISK")[0][:20]:
        level = "YELLOW"

    color, emoji = RISK_STYLES.get(level, ("white", "⚪"))

    console.print()
    console.print(Panel(
        f"[bold {color}]{emoji}  {level}[/bold {color}]",
        box=box.HEAVY,
        border_style=color,
        padding=(0, 2),
        expand=False,
    ))
    console.print()
    console.print(Panel(
        content.strip(),
        title="[bold]GRIDWATCH BRIEFING[/bold]",
        border_style=color,
        padding=(1, 2),
    ))
    console.print()


# ── Agent loop ─────────────────────────────────────────────────────────────────

def run_gridwatch(max_steps: int = 10):
    _print_banner()

    trigger_time = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"AUTOMATED DISPATCH — {trigger_time} UTC. Execute full grid risk assessment now."},
    ]
    step = 0

    while step < max_steps:
        step += 1
        console.print(f"[dim][step {step}] thinking...[/dim]")

        try:
            resp = requests.post(
                API_URL,
                headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
                json={"model": MODEL, "messages": messages, "tools": TOOL_SCHEMAS},
                timeout=60,
            )
            resp.raise_for_status()
        except requests.RequestException as e:
            console.print(f"[red]✗ API error: {e}[/red]")
            return "Agent stopped — API error."

        body = resp.json()
        if "choices" not in body or not body["choices"]:
            console.print(f"[yellow]⚠  Bad response from API, retrying...[/yellow]")
            continue
        message = body["choices"][0]["message"]
        messages.append(message)

        if message.get("tool_calls"):
            valid_calls = [
                call for call in message["tool_calls"]
                if call["function"]["name"] in TOOLS
            ]
            for call in message["tool_calls"]:
                if call["function"]["name"] not in TOOLS:
                    console.print(f"[red]✗ Unknown tool: {call['function']['name']}[/red]")

            tool_results = []
            results = {}
            workers = min(len(valid_calls), MAX_TOOL_WORKERS)
            with ThreadPoolExecutor(max_workers=workers) as pool:
                futures = {pool.submit(_execute_tool, call): call for call in valid_calls}
                for future in as_completed(futures):
                    call_id, result, fn_name, elapsed, _ = future.result()
                    results[call_id] = result
                    tool_results.append((fn_name, result, elapsed))

            _print_tool_table(tool_results)

            for call in valid_calls:
                messages.append({
                    "role": "tool",
                    "tool_call_id": call["id"],
                    "content": results[call["id"]],
                })

        else:
            _print_briefing(message["content"])
            return message["content"]

    return "Max steps reached."


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="GridWatch — Autonomous Grid Risk Agent")
    parser.add_argument(
        "--interval", type=int, default=0, metavar="MINUTES",
        help="Run continuously on this interval (minutes). Omit for a single run."
    )
    args = parser.parse_args()

    if args.interval > 0:
        console.print(f"[dim]Scheduled mode — running every {args.interval} minute(s). Ctrl+C to stop.[/dim]")
        while True:
            run_gridwatch()
            console.print(f"[dim]Next run in {args.interval} minute(s)...[/dim]")
            time.sleep(args.interval * 60)
    else:
        run_gridwatch()
