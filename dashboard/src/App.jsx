import { useEffect, useState } from 'react'
import './App.css'
import './briefing-animations.css'
import { RiskModule } from './modules/RiskModule'
import { GridModule } from './modules/GridModule'
import { WeatherModule } from './modules/WeatherModule'
import { MarketModule } from './modules/MarketModule'
import { NewsModule } from './modules/NewsModule'

const emptyPayload = {
  risk: { level: 'GREEN', emoji: '🟢' },
  grid: {
    current_demand_mw: 0,
    region: 'NYISO',
    generation_mix: {},
    renewable_pct: 0,
    forecast_peak_mw: 0,
    forecast_peak_time: '',
    forecast_profile: [],
  },
  weather: { alerts: [], forecast: [] },
  market: {
    lmp_by_zone: {},
    zone_avg_mwh: 0,
    spread_mwh: 0,
    henry_hub_mmbtu: 0,
  },
  news: [],
  recommendation: '',
  meta: { timestamp: '' },
}

function formatBriefingDate(d) {
  const days = ['SUN', 'MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT']
  const months = [
    'JAN',
    'FEB',
    'MAR',
    'APR',
    'MAY',
    'JUN',
    'JUL',
    'AUG',
    'SEP',
    'OCT',
    'NOV',
    'DEC',
  ]
  return `${days[d.getDay()]} ${String(d.getDate()).padStart(2, '0')} ${months[d.getMonth()]} ${d.getFullYear()}`
}

export default function App() {
  const [data, setData] = useState(emptyPayload)
  const [motionOn, setMotionOn] = useState(false)

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        const json = await (await fetch('/briefing')).json()
        if (!cancelled) {
          setData({
            ...emptyPayload,
            ...json,
            risk: { ...emptyPayload.risk, ...json.risk },
            grid: { ...emptyPayload.grid, ...json.grid },
            weather: { ...emptyPayload.weather, ...json.weather },
            market: { ...emptyPayload.market, ...json.market },
            meta: { ...emptyPayload.meta, ...json.meta },
          })
        }
      } catch {
        /* briefing optional — static layout remains */
      }
    })()
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    const id = requestAnimationFrame(() => setMotionOn(true))
    return () => cancelAnimationFrame(id)
  }, [])

  const rec = String(data.recommendation || '').trim()

  return (
    <div className={`briefing ${motionOn ? 'briefing--animated' : ''}`}>
      <header className="briefing__header">
        <div className="briefing__brand">
          <div className="briefing__logo" aria-hidden>
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
              <path
                d="M13 2L3 14h8l-1 8 10-12h-8l1-8z"
                fill="currentColor"
                stroke="currentColor"
                strokeWidth="1.2"
                strokeLinejoin="round"
              />
            </svg>
          </div>
          <div>
            <h1 className="briefing__title">GRIDWATCH BRIEFING</h1>
            <p className="briefing__subtitle">
              Operations dashboard · {data.grid?.region || 'NYISO'}
            </p>
          </div>
        </div>
        <div className="briefing__header-meta">
          <time className="briefing__date" dateTime={new Date().toISOString()}>
            {formatBriefingDate(new Date())}
          </time>
          <span className="briefing__live">
            <span className="briefing__live-dot" aria-hidden />
            LIVE
          </span>
        </div>
      </header>

      <main className="briefing__main">
        <RiskModule risk={data.risk} />
        <GridModule grid={data.grid} />
        <WeatherModule weather={data.weather} grid={data.grid} />
        <MarketModule market={data.market} />
        <NewsModule news={data.news} />
      </main>

      <footer className="briefing__footer">
        <span className="briefing__footer-left">
          {rec
            ? rec
            : `GRIDWATCH BRIEFING · ${data.meta?.timestamp ? `Run ${data.meta.timestamp}` : 'Awaiting recommendation'}`}
        </span>
        <span className="briefing__footer-right">Page 1 of 1</span>
      </footer>
    </div>
  )
}
