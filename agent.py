import argparse
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import anthropic
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
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
    from tools.stubs import get_henry_hub_price
    from tools.stubs import detect_anomaly, get_demand_forecast, get_interconnection_flows
    from tools.stubs import get_security_alerts
    console.print("[yellow]⚠  STUB MODE — using fake data[/yellow]")
else:
    from tools.grid import get_grid_demand, get_generation_mix
    from tools.weather import get_weather_alerts, get_weather_forecast
    from tools.news import get_energy_news
    from tools.market import get_lmp_prices, get_henry_hub_price
    # v2 tools — import when available, stub until PR merges
    try:
        from tools.anomaly import detect_anomaly
    except ImportError:
        from tools.stubs import detect_anomaly
    try:
        from tools.forecast import get_demand_forecast
    except ImportError:
        from tools.stubs import get_demand_forecast
    try:
        from tools.intercon import get_interconnection_flows
    except ImportError:
        from tools.stubs import get_interconnection_flows
    try:
        from tools.security import get_security_alerts
    except ImportError:
        from tools.stubs import get_security_alerts

from tools.alert import send_alert

ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6")
MAX_TOOL_WORKERS = 12

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# ── Session token tracking ─────────────────────────────────────────────────────

_session_input  = 0
_session_output = 0

# ── Tool registry ──────────────────────────────────────────────────────────────

TOOLS = {
    "get_grid_demand":           get_grid_demand,
    "get_generation_mix":        get_generation_mix,
    "get_weather_alerts":        get_weather_alerts,
    "get_weather_forecast":      get_weather_forecast,
    "get_energy_news":           get_energy_news,
    "get_lmp_prices":            get_lmp_prices,
    "get_henry_hub_price":       get_henry_hub_price,
    "detect_anomaly":            detect_anomaly,
    "get_demand_forecast":       get_demand_forecast,
    "get_interconnection_flows": get_interconnection_flows,
    "get_security_alerts":       get_security_alerts,
    "send_alert":                send_alert,
}

# Anthropic tool schema format (input_schema, not parameters)
TOOL_SCHEMAS = [
    {
        "name": "get_grid_demand",
        "description": "Get current real-time electricity demand by US grid region.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "get_generation_mix",
        "description": "Get current electricity generation breakdown by fuel type (solar, wind, gas, nuclear).",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "get_weather_alerts",
        "description": "Get active NOAA severe weather alerts for the grid service area.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "get_weather_forecast",
        "description": "Get the 48-hour hourly weather forecast for the grid service area.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "get_energy_news",
        "description": "Get recent energy industry headlines from public RSS feeds.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "get_lmp_prices",
        "description": "Get current-hour NYISO day-ahead Locational Marginal Prices ($/MWh) by zone, plus zone average and spread.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "get_henry_hub_price",
        "description": "Get the current Henry Hub natural gas spot price ($/MMBtu) and day-over-day change.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "detect_anomaly",
        "description": "Run Z-score anomaly detection on current demand (MW) and LMP prices. Flags when |Z| > 2.0.",
        "input_schema": {
            "type": "object",
            "properties": {
                "demand_mw": {
                    "type": "number",
                    "description": "Current grid demand in megawatts.",
                },
                "lmp_prices": {
                    "type": "object",
                    "description": "Dict of zone → price ($/MWh), e.g. {\"NYC\": 187.42, \"LONGIL\": 172.18}.",
                },
            },
            "required": ["demand_mw", "lmp_prices"],
        },
    },
    {
        "name": "get_demand_forecast",
        "description": "Get the EIA 24-hour hourly demand forecast for NYISO, including peak hour and MW.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "get_interconnection_flows",
        "description": "Get current MW flows on NYISO ↔ PJM and NYISO ↔ ISO-NE tie-lines. Positive = exporting, negative = importing.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "get_security_alerts",
        "description": "Get active CISA ICS-CERT advisories and E-ISAC threat bulletins relevant to the electric grid. Returns current cyber threat level and any active vulnerability disclosures.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "send_alert",
        "description": "Push a risk alert notification to the on-call analyst via ntfy.sh. Call this after forming your risk assessment — before outputting the final briefing. GREEN risk skips the push; RED and YELLOW fire immediately.",
        "input_schema": {
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
]

# ── Tool execution ─────────────────────────────────────────────────────────────

def _execute_tool(block) -> tuple:
    fn_name = block.name
    kwargs  = block.input or {}
    t0 = time.time()
    try:
        result = TOOLS[fn_name](**kwargs) if kwargs else TOOLS[fn_name]()
    except Exception as e:
        result = f"Tool error ({fn_name}): {e}"
    elapsed = time.time() - t0
    return block.id, result, fn_name, elapsed


# ── Display helpers ────────────────────────────────────────────────────────────

RISK_STYLES = {
    "RED":    ("red",    "🔴"),
    "YELLOW": ("yellow", "🟡"),
    "GREEN":  ("green",  "🟢"),
}

def _print_banner():
    console.print()
    console.print(Panel.fit(
        "[bold white]GRIDWATCH[/bold white]  [dim]Autonomous Grid Risk Agent[/dim]  "
        f"[dim]{MODEL}[/dim]",
        border_style="dim white",
        padding=(0, 2),
    ))
    console.print()

def _print_tool_table(tool_results: list):
    table = Table(box=box.SIMPLE, show_header=True, header_style="dim")
    table.add_column("tool",   style="cyan", no_wrap=True)
    table.add_column("status", justify="center")
    table.add_column("time",   justify="right", style="dim")
    for fn_name, result, elapsed in tool_results:
        ok     = not str(result).startswith("Tool error")
        status = "[green]✓[/green]" if ok else "[red]✗[/red]"
        table.add_row(fn_name, status, f"{elapsed:.1f}s")
    console.print(table)

def _print_token_usage(run_in: int, run_out: int):
    run_cost     = (run_in / 1_000_000) * 3.00 + (run_out / 1_000_000) * 15.00
    session_cost = (_session_input / 1_000_000) * 3.00 + (_session_output / 1_000_000) * 15.00
    console.print(
        f"[dim]tokens this run — input: {run_in:,}  output: {run_out:,}  cost: ${run_cost:.4f}  "
        f"| session — input: {_session_input:,}  output: {_session_output:,}  cost: ${session_cost:.4f}[/dim]"
    )

def _print_briefing(content: str):
    level = "GREEN"
    if "🔴" in content or re.search(r'\bRED\b', content[:60], re.IGNORECASE):
        level = "RED"
    elif "🟡" in content or re.search(r'\bYELLOW\b', content[:60], re.IGNORECASE):
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
    global _session_input, _session_output

    _print_banner()

    trigger_time = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    messages = [
        {
            "role": "user",
            "content": f"AUTOMATED DISPATCH — {trigger_time} UTC. Execute full grid risk assessment now.",
        }
    ]

    step       = 0
    run_input  = 0
    run_output = 0

    while step < max_steps:
        step += 1
        console.print(f"[dim][step {step}] thinking...[/dim]")

        try:
            response = client.messages.create(
                model=MODEL,
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                messages=messages,
                tools=TOOL_SCHEMAS,
            )
        except anthropic.APIError as e:
            console.print(f"[red]✗ API error: {e}[/red]")
            return "Agent stopped — API error."

        # Track tokens
        run_input       += response.usage.input_tokens
        run_output      += response.usage.output_tokens
        _session_input  += response.usage.input_tokens
        _session_output += response.usage.output_tokens

        # Append assistant turn
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "tool_use":
            tool_blocks = [b for b in response.content if b.type == "tool_use"]
            valid       = [b for b in tool_blocks if b.name in TOOLS]

            for b in tool_blocks:
                if b.name not in TOOLS:
                    console.print(f"[red]✗ Unknown tool: {b.name}[/red]")

            tool_results = []
            results      = {}
            workers      = min(len(valid), MAX_TOOL_WORKERS)
            with ThreadPoolExecutor(max_workers=workers) as pool:
                futures = {pool.submit(_execute_tool, b): b for b in valid}
                for future in as_completed(futures):
                    call_id, result, fn_name, elapsed = future.result()
                    results[call_id] = result
                    tool_results.append((fn_name, result, elapsed))

            _print_tool_table(tool_results)

            # Anthropic tool_result format
            messages.append({
                "role": "user",
                "content": [
                    {
                        "type":        "tool_result",
                        "tool_use_id": b.id,
                        "content":     results[b.id],
                    }
                    for b in valid
                ],
            })

        else:
            text = " ".join(
                b.text for b in response.content if hasattr(b, "text")
            )
            _print_briefing(text)
            _print_token_usage(run_input, run_output)
            return text

    return "Max steps reached."


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="GridWatch — Autonomous Grid Risk Agent")
    parser.add_argument(
        "--interval", type=int, default=0, metavar="MINUTES",
        help="Run continuously on this interval (minutes). Omit for a single run.",
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
