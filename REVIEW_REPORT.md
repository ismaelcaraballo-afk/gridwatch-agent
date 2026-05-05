# GridWatch Code & Security Review
_Reviewed: 2026-05-04_

---

## Critical

**CORS wildcard allows any origin to call the agent and trigger autonomous actions**
`server.py:322` — `Access-Control-Allow-Origin: *` on every response means any webpage can call `/briefing` and force a full agent run (which can trigger demand response and push ntfy alerts); restrict to the known dashboard origin or add rate-limiting at minimum.

**`get_henry_hub_price` has no exception handling — a network error crashes the tool and propagates up**
`tools/market.py:111-124` — `requests.get(...).raise_for_status()` is called bare with no try/except, unlike every other tool in the codebase; wrap in try/except and return an error string the way `get_grid_demand` does.

**`get_weather_alerts` has no exception handling — network failure raises uncaught exception**
`tools/weather.py:17-19` — `get_with_backoff` can raise `requests.RequestException` on final retry, but the call is not wrapped; the exception bubbles to `_execute_tool` which catches it and returns a tool-error string, but this masks the failure silently from the operator; add a try/except and return a human-readable string as every other tool does.

**`get_weather_forecast` crashes with `KeyError` if NOAA `/points` response is missing `forecastHourly`**
`tools/weather.py:50` — `points_resp.json()["properties"]["forecastHourly"]` has no guard; if the field is absent (e.g., coordinates not in NWS coverage or API change) the whole tool call raises unhandled; use `.get()` with a fallback error string.

---

## High

**`SCHEDULE_FILE` path is constructed from `__file__` without sanitization and loaded with `open()` — path traversal risk if the env is ever overridden**
`tools/scheduler.py:6-8` — currently hardcoded but the pattern (`os.path.dirname(__file__)` + join) means a symlink or relocated file could point outside the repo; validate the resolved path stays within the project root with `Path.resolve().is_relative_to(...)`.

**`get_grid_demand` labels the unit "MWh" when the value is actually MW demand**
`tools/grid.py:57` — `"Current demand: {demand:,} MWh"` — EIA's `region-data` type `D` returns MW, not MWh; `server.py:53` parses this string and stores it in `current_demand_mw`, so the unit label is wrong in both the briefing and the dashboard; change to `MW`.

**`get_demand_forecast` also mislabels MW as MWh throughout output**
`tools/forecast.py:97,99,100,101,88` — same EIA `DF` series returns MW; every `MWh` label in the output string is incorrect; fix to `MW`.

**`detect_anomaly` uses population variance (divide by N) instead of sample variance (divide by N-1) for Z-score, producing inflated Z-scores on small windows**
`tools/anomaly.py:38` — `variance = sum(...) / len(history)` should be `/ (len(history) - 1)` for an unbiased estimator; with 3-5 readings this causes anomalies to be under-detected at the 2.0σ threshold.

**`_latest_by_tool` in `server.py` only keeps the last result per tool name — if the agent calls a tool twice (which the prompt allows for detect_anomaly), the first result is silently discarded**
`server.py:31-36` — the loop overwrites `out[name]` on each iteration; this is the "duplicate call" pattern from the brief; fix by either keeping a list or always using the last and documenting the choice explicitly.

**Flask server binds to `0.0.0.0` with no authentication**
`server.py:328` — `app.run(host="0.0.0.0", port=5000)` exposes the agent endpoint (which fires real ntfy push notifications and can trigger DR signals) to the local network; add a secret header check or bind to `127.0.0.1` unless external access is intentional.

**`detect_anomaly` history file is written to the project root as a dotfile with no integrity check**
`tools/anomaly.py:5,28-29` — `.demand_history.json` is world-readable in the repo directory; if tampered with, it can shift the rolling mean and suppress or manufacture anomaly alerts; write to a user-only temp directory (mode 0o600) or validate the contents on load.

---

## Medium

**`get_news_sentiment()` calls `get_energy_news()` internally, causing a duplicate RSS fetch if the agent also calls `get_energy_news` in the same run**
`tools/news.py:55` — `get_news_sentiment` re-fetches all four feeds; it is not registered as an agent tool so it won't double-fire in normal operation, but it will if called in tests or future tools; accept raw headlines as a parameter or cache the result.

**`_fetch_dam_csv` uses a plain `requests.get` without the backoff wrapper, making it susceptible to transient NYISO OASIS failures**
`tools/market.py:231-237` — every other HTTP call in the codebase goes through `get_with_backoff`; this one does not; swap in `get_with_backoff` for consistency.

**`get_fleet_data` uses a plain `requests.get` without the backoff wrapper**
`tools/market.py:158-175` — same issue as above; not an agent tool but shares the module; apply `get_with_backoff`.

**`_print_briefing` in `agent.py` infers risk level from the first 60 characters of raw LLM text**
`agent.py:277-279` — `re.search(r'\bRED\b', content[:60])` will false-positive if the LLM opens with a sentence like "No RED conditions today"; the authoritative level is already returned by `send_alert` in tool_calls — use that instead of re-parsing the briefing narrative.

**`_risk_level` in `server.py` scans only the first 1200 characters of briefing — if the LLM puts the risk keyword later it silently defaults to GREEN**
`server.py:40-45` — same fragility; prefer using the result of `send_alert` from `tool_calls` which is the canonical level the agent chose.

**`send_alert` state file uses `tempfile.gettempdir()` which is shared on multi-user systems; another user could pre-create the file to manipulate cooldown state**
`tools/alert.py:9` — the filename includes `os.getuid()` which mitigates this on Unix, but the symlink check (`os.path.islink`) only fires on write, not read; validate on `_load_state` too or use a user-private directory.

**`urllib3>=1.26,<2` in requirements.txt pins to urllib3 v1 which is EOL and has known CVEs**
`requirements.txt:2` — urllib3 v2 has been stable since 2023; the constraint was likely added for an old `requests` compat issue that no longer exists; drop the upper bound and test with v2.

**`get_demand_forecast` makes two sequential EIA HTTP calls (forecast + actual) in a tool that's already called from the agent's parallel thread pool — the second call is not guarded against the executor shutting down**
`tools/forecast.py:47-63` — if the agent's `ThreadPoolExecutor` times out or cancels while the first call is in flight, the second blocking call will still run; this is low-risk in practice but the pattern should be documented.

---

## Low

**`get_fleet_data` is defined in `market.py` but never imported or registered as an agent tool — dead code in the production path**
`tools/market.py:149-227` — the function is complete and tested (has `if __name__ == "__main__"` usage) but the agent has no schema entry for it; either add it to `TOOL_SCHEMAS` or move it to a separate dev/analysis script.

**`_SENTIMENT_KEYWORDS` and `get_news_sentiment` in `news.py` are defined but never called by the agent**
`tools/news.py:34-80` — dead code in the agent flow; the sentiment classification exists but has no tool schema entry; document intent or remove until it's wired up.

**`agent.py` token cost constants (lines 268-269) are hardcoded to Sonnet pricing and will silently miscalculate if `ANTHROPIC_MODEL` is changed to Opus or Haiku**
`agent.py:268-269` — `$3.00/M input, $15.00/M output` are Sonnet 4 rates; extract as env-configurable constants or add a model→rate lookup table.

**`tool_results` list in `agent.py` is built in completion order (as futures complete), but `results` dict preserves call_id mapping — the table display order is non-deterministic across runs**
`agent.py:379-383` — cosmetic, but the tool timing table can appear in different orders each run making logs hard to compare; sort by tool name before passing to `_print_tool_table`.

**`maintenance_schedule.json` dates are hardcoded to 2026-05-06/07 and will never match after those dates pass**
`maintenance_schedule.json` — the scheduler will always return APPROVE for all windows once the dates are in the past since `overlaps_peak` will never be true; this is test/demo data, but there's no comment or warning making that clear.

**Dashboard `WeatherModule` uses array index `i` as React key for both alert list and forecast table**
`dashboard/src/modules/WeatherModule.jsx:12,34` — index keys cause stale rendering bugs when the list order changes between refreshes; use a stable field like `a.event` for alerts and `row.time` for forecast rows.

**Dashboard `NewsModule` uses array index `i` as React key**
`dashboard/src/modules/NewsModule.jsx:22` — same issue; use `n.source + n.headline` as the key.

**`OpsFooter` uses array index `i` as React key for maintenance items**
`dashboard/src/modules/OpsFooter.jsx:28` — use `row.unit` as the key.
