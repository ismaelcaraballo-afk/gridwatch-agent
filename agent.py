import argparse
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import anthropic
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

console = Console()

_PROJECT_ROOT = Path(__file__).resolve().parent
load_dotenv(_PROJECT_ROOT / ".env", override=True)

from prompts import SYSTEM_PROMPT

USE_STUBS = os.environ.get("USE_STUBS", "false").lower() == "true"

if USE_STUBS:
    from tools.stubs import get_grid_demand, get_generation_mix
    from tools.stubs import get_weather_alerts, get_weather_forecast
    from tools.stubs import get_energy_news
    from tools.stubs import get_lmp_prices
    from tools.stubs import get_henry_hub_price
    from tools.stubs import detect_anomaly, get_demand_forecast, get_interconnection_flows
    from tools.stubs import trigger_demand_response, evaluate_maintenance_schedule
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
    from tools.demand_response import trigger_demand_response
    from tools.scheduler import evaluate_maintenance_schedule

from tools.alert import send_alert

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "").strip()
MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6")
MAX_TOOL_WORKERS = 4

_openrouter_key = os.environ.get("OPENROUTER_API_KEY")
if _openrouter_key and os.environ.get("USE_OPENROUTER", "false").lower() == "true":
    client = anthropic.Anthropic(
        api_key=_openrouter_key,
        base_url="https://openrouter.ai/api/v1",
        default_headers={"HTTP-Referer": "gridwatch-agent"},
    )
else:
    if not ANTHROPIC_API_KEY:
        raise RuntimeError(
            "ANTHROPIC_API_KEY is missing. Add it to "
            f"{_PROJECT_ROOT / '.env'} (see README) or export it in your shell."
        )
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
    "get_interconnection_flows":    get_interconnection_flows,
    "trigger_demand_response":      trigger_demand_response,
    "evaluate_maintenance_schedule": evaluate_maintenance_schedule,
    "send_alert":                   send_alert,
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
        "name": "trigger_demand_response",
        "description": "Activate demand response — fire a load-reduction signal to enrolled customers when forecast peak exceeds 18,000 MW. Call this when get_demand_forecast shows a dangerous peak ahead. The agent decides whether to trigger; this tool executes the action.",
        "input_schema": {
            "type": "object",
            "properties": {
                "forecast_peak_mw": {
                    "type": "number",
                    "description": "Forecast peak demand in MW from get_demand_forecast.",
                },
                "forecast_peak_time": {
                    "type": "string",
                    "description": "ISO timestamp of forecast peak (e.g. '2026-05-04 18:00 UTC').",
                },
                "current_mw": {
                    "type": "number",
                    "description": "Current actual demand in MW from get_grid_demand.",
                },
            },
            "required": ["forecast_peak_mw", "forecast_peak_time", "current_mw"],
        },
    },
    {
        "name": "evaluate_maintenance_schedule",
        "description": "Evaluate planned maintenance windows against the demand forecast. Returns APPROVE or POSTPONE decisions for each scheduled unit outage, with reasoning. Call this after get_demand_forecast so you have the peak data.",
        "input_schema": {
            "type": "object",
            "properties": {
                "forecast_peak_mw": {
                    "type": "number",
                    "description": "Forecast peak demand in MW.",
                },
                "forecast_peak_time": {
                    "type": "string",
                    "description": "ISO timestamp of forecast peak.",
                },
            },
            "required": ["forecast_peak_mw", "forecast_peak_time"],
        },
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

_COST_PER_M_IN  = float(os.environ.get("COST_PER_M_IN",  "3.00"))
_COST_PER_M_OUT = float(os.environ.get("COST_PER_M_OUT", "15.00"))


def _print_token_usage(run_in: int, run_out: int):
    run_cost     = (run_in / 1_000_000) * _COST_PER_M_IN + (run_out / 1_000_000) * _COST_PER_M_OUT
    session_cost = (_session_input / 1_000_000) * _COST_PER_M_IN + (_session_output / 1_000_000) * _COST_PER_M_OUT
    console.print(
        f"[dim]tokens this run — input: {run_in:,}  output: {run_out:,}  cost: ${run_cost:.4f}  "
        f"| session — input: {_session_input:,}  output: {_session_output:,}  cost: ${session_cost:.4f}[/dim]"
    )

def _print_briefing(content: str):
    level = "GREEN"
    if "🔴" in content or re.search(r'\bRED\b', content, re.IGNORECASE):
        level = "RED"
    elif "🟡" in content or re.search(r'\bYELLOW\b', content, re.IGNORECASE):
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

def run_gridwatch(max_steps: int = 10, *, quiet: bool = False) -> dict:
    """Run one GridWatch agent cycle.

    Returns a dict: ``briefing`` (final text or empty), ``tool_calls`` (chronological
    ``name``/``result`` records), and ``error`` (API / max-steps message or None).
    When ``quiet`` is True, Rich console output is suppressed (for HTTP wrappers).
    """
    global _session_input, _session_output

    all_tool_calls: list[dict] = []

    if not quiet:
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
        if not quiet:
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
            if not quiet:
                console.print(f"[red]✗ API error: {e}[/red]")
            run_cost = (run_input / 1_000_000) * _COST_PER_M_IN + (run_output / 1_000_000) * _COST_PER_M_OUT
            return {
                "briefing": "",
                "tool_calls": all_tool_calls,
                "error": f"Agent stopped — API error: {e}",
                "usage": {"input_tokens": run_input, "output_tokens": run_output},
                "run_cost_usd": round(run_cost, 4),
            }

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
                    if not quiet:
                        console.print(f"[red]✗ Unknown tool: {b.name}[/red]")

            tool_results = []
            results      = {}
            # Avoid max_workers=0 when the model emits only unknown tool names.
            workers      = max(1, min(len(valid), MAX_TOOL_WORKERS))
            with ThreadPoolExecutor(max_workers=workers) as pool:
                futures = {pool.submit(_execute_tool, b): b for b in valid}
                for future in as_completed(futures):
                    call_id, result, fn_name, elapsed = future.result(timeout=45)
                    results[call_id] = result
                    tool_results.append((fn_name, result, elapsed))
                    all_tool_calls.append({"name": fn_name, "result": str(result)})

            if not quiet:
                _print_tool_table(sorted(tool_results, key=lambda x: x[0]))

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
            if not quiet:
                _print_briefing(text)
                _print_token_usage(run_input, run_output)
            run_cost = (run_input / 1_000_000) * _COST_PER_M_IN + (run_output / 1_000_000) * _COST_PER_M_OUT
            return {
                "briefing": text.strip(),
                "tool_calls": all_tool_calls,
                "error": None,
                "usage": {"input_tokens": run_input, "output_tokens": run_output},
                "run_cost_usd": round(run_cost, 4),
            }

    run_cost = (run_input / 1_000_000) * _COST_PER_M_IN + (run_output / 1_000_000) * _COST_PER_M_OUT
    return {
        "briefing": "",
        "tool_calls": all_tool_calls,
        "error": "Max steps reached.",
        "usage": {"input_tokens": run_input, "output_tokens": run_output},
        "run_cost_usd": round(run_cost, 4),
    }


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
