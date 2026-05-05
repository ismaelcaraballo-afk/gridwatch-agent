import { useEffect, useState } from 'react'
import './App.css'
import { RiskModule } from './modules/RiskModule'
import { GridModule } from './modules/GridModule'
import { WeatherModule } from './modules/WeatherModule'
import { MarketModule } from './modules/MarketModule'
import { NewsModule } from './modules/NewsModule'
import { OpsFooter } from './modules/OpsFooter'

const emptyPayload = {
  risk: { level: 'GREEN', emoji: '🟢' },
  grid: {
    current_demand_mw: 0,
    region: 'NYISO',
    generation_mix: {
      natural_gas_pct: 0,
      nuclear_pct: 0,
      wind_pct: 0,
      hydro_pct: 0,
      solar_pct: 0,
    },
    renewable_pct: 0,
    forecast_peak_mw: 0,
    forecast_peak_time: '',
  },
  weather: { alerts: [], forecast: [] },
  market: {
    lmp_by_zone: {},
    zone_avg_mwh: 0,
    spread_mwh: 0,
    henry_hub_mmbtu: 0,
  },
  news: [],
  actions: { demand_response: '', maintenance: [] },
  recommendation: '',
  alert_sent: false,
  meta: { timestamp: '', model: '', run_cost_usd: 0 },
}

export default function App() {
  const [data, setData] = useState(emptyPayload)
  const [loading, setLoading] = useState(true)
  const [fetchError, setFetchError] = useState(null)

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      setLoading(true)
      setFetchError(null)
      try {
        const res = await fetch('/briefing')
        const json = await res.json()
        if (!cancelled) {
          setData({
            ...emptyPayload,
            ...json,
            risk: { ...emptyPayload.risk, ...json.risk },
            grid: { ...emptyPayload.grid, ...json.grid },
            weather: { ...emptyPayload.weather, ...json.weather },
            market: { ...emptyPayload.market, ...json.market },
            actions: {
              ...emptyPayload.actions,
              ...json.actions,
              maintenance: json.actions?.maintenance ?? [],
            },
            meta: { ...emptyPayload.meta, ...json.meta },
          })
          if (!res.ok) {
            setFetchError(`Briefing run incomplete (HTTP ${res.status}).`)
          }
        }
      } catch (e) {
        if (!cancelled) {
          setFetchError(e instanceof Error ? e.message : 'Request failed')
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [])

  return (
    <div className="dashboard">
      <header className="dashboard__header">
        <div>
          <h1 className="dashboard__title">GridWatch</h1>
          <p className="dashboard__subtitle">
            Contract load from <code>GET /briefing</code>
          </p>
        </div>
        {loading && <span className="dashboard__badge">Loading…</span>}
        {fetchError && !loading && (
          <span className="dashboard__badge dashboard__badge--warn" role="status">
            {fetchError}
          </span>
        )}
      </header>

      <section className="dashboard__grid">
        <RiskModule risk={data.risk} />
        <GridModule grid={data.grid} />
        <WeatherModule weather={data.weather} />
        <MarketModule market={data.market} />
        <NewsModule news={data.news} />
      </section>

      <OpsFooter
        recommendation={data.recommendation}
        alertSent={data.alert_sent}
        actions={data.actions}
        meta={data.meta}
      />
    </div>
  )
}
