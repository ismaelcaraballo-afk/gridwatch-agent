import { useEffect, useState } from 'react'
import './App.css'
import { RiskModule } from './modules/RiskModule'
import { GridModule } from './modules/GridModule'
import { WeatherModule } from './modules/WeatherModule'
import { MarketModule } from './modules/MarketModule'
import { NewsModule } from './modules/NewsModule'

const emptyPayload = {
  risk: { level: 'GREEN', factors: [] },
  grid: { demand_mw: 0, gen_mix: {} },
  weather: { active_alerts: [], forecast_12h: '' },
  market: {
    lmp_avg: 0,
    lmp_peak_zone: '—',
    lmp_peak: 0,
    spread: 0,
  },
  news: { headlines: [] },
  alert: { sent: false, level: 'GREEN', confirmation: '' },
  meta: { agent_error: null, briefing_excerpt: '' },
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
          setData({ ...emptyPayload, ...json })
          if (!res.ok && json?.meta?.agent_error) {
            setFetchError(json.meta.agent_error)
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
            Live briefing — single load from <code>/briefing</code>
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
        <RiskModule risk={data.risk} alert={data.alert} />
        <GridModule grid={data.grid} />
        <WeatherModule weather={data.weather} />
        <MarketModule market={data.market} />
        <NewsModule news={data.news} />
      </section>

      {data.meta?.briefing_excerpt ? (
        <footer className="dashboard__footer">
          <strong>Briefing excerpt:</strong> {data.meta.briefing_excerpt}
        </footer>
      ) : null}
    </div>
  )
}
