# GridWatch v2 Plans

Research sourced from internal planning + multi-LLM panel (DeepSeek, GPT-4, Llama).

---

## From Our Own Planning

**1. Day-Ahead Commit Recommendation (GridPilot)**
Add EIA wholesale electricity prices + natural gas spot prices. Agent calculates spark spreads and produces a generation commit memo. This is the upgrade that requires the Anthropic frontier model — a free model summarizes data, Claude Opus reasons across competing price signals and produces a defensible financial recommendation.

**2. 7-Day Baseline for Real Spike Detection**
Replace Edwin's 5-hour rolling average with same-hour demand from the last 7 days. Makes spike detection genuinely seasonal — a hot Monday afternoon gets compared to last Monday, not the last 5 hours of the same day. More accurate RED/YELLOW triggers.

**3. True Blocking Gate**
Right now yes/no at the checkpoint just changes a header. In v2 — "no" actually stops the briefing from being distributed. Real human-in-the-loop, not just a confirmation log.

**4. Multi-Region Coverage**
Currently hardcoded to NYISO. v2 lets the analyst specify a region at runtime — CAISO (California), ERCOT (Texas), PJM (Mid-Atlantic). Same agent, broader coverage.

**5. Scheduled Auto-Run**
Agent runs automatically at shift start (6 AM) via cron. Briefing is waiting when the analyst arrives. No manual trigger.

**6. Outage Correlator**
When a demand spike happens, cross-reference EIA disturbance events (Form OE-417) to check if an outage is causing it, not just weather. Adds a third cause vector to RED analysis.

**7. Restoration Estimator**
If an outage is detected, pull Census population data for the affected zip code. Give estimated customers-affected count plus restoration window.

**8. Fuel Price Alert**
EIA publishes natural gas spot prices. If gas spikes while gas generation is carrying 50%+ of the load, that's a cost alert alongside the demand alert.

**9. Generation Gap Detector**
If solar/wind drops suddenly mid-day, flag the renewable gap and which fossil fuel is compensating.

**10. 72-Hour Risk Window**
Instead of 12-hour forecast, look 3 days out. If a heat dome is building, analyst gets early warning before the RED condition hits.

**11. Wind Ramp Warning**
Sudden wind speed changes affect wind generation. Flag if forecast shows wind dropping >50% in a 2-hour window.

**12. News-to-Risk Linker**
Agent reads headlines and flags only those directly relevant to the current grid region. Generic energy news stays in the briefing. Regional disruption news bumps the risk level.

**13. Confidence Scoring**
Agent rates its own confidence in the risk level (HIGH/MEDIUM/LOW) based on data quality. If EIA is down and running on stubs, confidence is LOW. Analyst knows to treat it differently.

---

## From Multi-LLM Panel

**14. Predictive Load Forecasting** *(DS + GPT + Llama — top pick)*
EIA historical hourly demand + NOAA temperature forecasts. Agent reasons across both to produce a day-ahead demand prediction with confidence range. Why frontier model: causal inference — "heat dome building + Monday industrial load + low wind forecast = 15% spike by 3 PM." Not retrieval. Prediction.
- APIs: EIA v2, NOAA NWS

**15. Renewable Generation Shortfall Detection** *(DS + GPT)*
Cross-reference EIA solar/wind output with NOAA cloud cover and wind speed forecast. Agent flags when renewable generation is about to drop and which fossil fuel will compensate.
- APIs: EIA v2 fuel-type-data, NOAA forecast, NREL (free)

**16. Wildfire/Flood Risk on Transmission Lines** *(DS)*
Cross-reference active fires or floods with grid infrastructure geography. Flag transmission lines at risk before the event hits.
- APIs: NASA FIRMS fire detection (free), USGS water alerts (free)
- Why frontier model: spatial reasoning — "fire 5 miles from substation X + southwest winds = RED in 6 hours"

**17. Energy Market Price Volatility** *(GPT + DS)*
Agent predicts wholesale price volatility from demand + weather + news signals. Produces a cost alert alongside the risk briefing.
- APIs: EIA wholesale prices (free)
- Why frontier model: non-linear market reasoning across multiple signals

**18. Geopolitical Risk Scoring** *(DS)*
Scan energy headlines for pipeline disruptions, sanctions, supply shocks. Agent assigns a risk score and explains the probable grid impact.
- APIs: NewsAPI free tier
- Why frontier model: entity recognition + probabilistic reasoning ("X pipeline shutdown → 70% chance of Y price surge in 3 days")

**19. USGS Earthquake Risk** *(Llama)*
Cross-reference earthquake activity with grid infrastructure. Relevant for California/Pacific Northwest utilities.
- APIs: USGS Earthquake API (free)

---

## Priority Ranking for Next Sprint

| Priority | Idea | Effort | Frontier Model Required |
|----------|------|--------|------------------------|
| 1 | Day-Ahead Commit Recommendation | High | Yes — Anthropic API upgrade |
| 2 | Predictive Load Forecasting | Medium | Yes |
| 3 | Wildfire/Flood Risk on Transmission | Medium | Yes |
| 4 | 7-Day Baseline | Low | No |
| 5 | Multi-Region Coverage | Low | No |
| 6 | True Blocking Gate | Low | No |
| 7 | Renewable Shortfall Detection | Medium | Yes |
| 8 | Geopolitical Risk Scoring | Medium | Yes |
