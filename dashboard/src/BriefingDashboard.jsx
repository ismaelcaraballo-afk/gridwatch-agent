import { useCallback, useEffect, useId, useLayoutEffect, useMemo, useState } from 'react'
import './briefing-dashboard.css'

const HM_HOURS = ['1a', '2a', '3a', '4a', '5a', '6a', '7a', '8a', '9a', '10a', '11a', '12p']
const ARC_C = 2 * Math.PI * 36

const FALLBACK_BARS = [
  { key: 'gas', label: 'Gas', pct: 38, color: 'linear-gradient(180deg,#00d4ff,#0066ff)' },
  { key: 'nuc', label: 'Nuclear', pct: 22, color: 'linear-gradient(180deg,#7c3aed,#a855f7)' },
  { key: 'wnd', label: 'Wind', pct: 18, color: 'linear-gradient(180deg,#06d6a0,#34d399)' },
  { key: 'sol', label: 'Solar', pct: 12, color: 'linear-gradient(180deg,#f59e0b,#fbbf24)' },
  { key: 'coal', label: 'Other', pct: 7, color: 'linear-gradient(180deg,#ef4444,#f87171)' },
  { key: 'hyd', label: 'Hydro', pct: 3, color: 'linear-gradient(180deg,#06b6d4,#67e8f9)' },
]

const DEMO_HEATMAP = [
  [42, '+0.3', 1, 38, '-0.5', 1],
  [35, '-0.8', 1, 33, '-0.2', 1],
  [36, '+0.4', 1, 44, '+1.1', 2],
  [58, '+2.3', 2, 72, '+3.0', 3],
  [85, '+1.8', 3, 91, '+0.9', 3],
  [89, '+2.1', 3, 95, '+3.4', 4],
  [102, '+1.8', 4, 118, '+4.2', 5],
  [124, '+5.1', 5, 119, '-3.0', 5],
  [108, '-2.5', 4, 97, '-1.4', 4],
  [88, '-0.9', 3, 76, '-1.2', 3],
  [61, '-1.8', 2, 48, '-1.3', 2],
  [52, '-1.2', 2, 44, '-0.9', 2],
]

function riskScoreFromLevel(level) {
  const u = String(level || 'GREEN').toUpperCase()
  if (u === 'RED') return 88
  if (u === 'YELLOW') return 56
  return 34
}

function riskBadge(level) {
  const u = String(level || 'GREEN').toUpperCase()
  if (u === 'RED') return { className: 'bw-risk-badge--red', label: 'HIGH RISK' }
  if (u === 'YELLOW') return { className: 'bw-risk-badge--yellow', label: 'ELEVATED RISK' }
  return { className: 'bw-risk-badge--green', label: 'NORMAL RISK' }
}

function buildBarsFromMix(mix) {
  const defs = [
    { key: 'natural_gas_pct', label: 'Gas', color: 'linear-gradient(180deg,#00d4ff,#0066ff)' },
    { key: 'nuclear_pct', label: 'Nuclear', color: 'linear-gradient(180deg,#7c3aed,#a855f7)' },
    { key: 'wind_pct', label: 'Wind', color: 'linear-gradient(180deg,#06d6a0,#34d399)' },
    { key: 'solar_pct', label: 'Solar', color: 'linear-gradient(180deg,#f59e0b,#fbbf24)' },
    { key: 'hydro_pct', label: 'Hydro', color: 'linear-gradient(180deg,#06b6d4,#67e8f9)' },
  ]
  const out = defs.map((d) => ({ ...d, pct: Math.round(Number(mix?.[d.key]) || 0) }))
  const sum = out.reduce((s, b) => s + b.pct, 0)
  if (sum < 0.5) return FALLBACK_BARS
  const rest = Math.max(0, 100 - sum)
  if (rest > 0.5) out.push({ key: 'other_pct', label: 'Other', color: 'linear-gradient(180deg,#ef4444,#f87171)', pct: Math.round(rest) })
  return out
}

function priceTier(price, min, max) {
  if (max <= min) return 3
  const n = (price - min) / (max - min)
  if (n < 0.2) return 1
  if (n < 0.4) return 2
  if (n < 0.6) return 3
  if (n < 0.8) return 4
  return 5
}

function padEntries(entries, len) {
  if (!entries.length) return []
  const out = []
  for (let i = 0; i < len; i++) out.push(entries[i % entries.length])
  return out
}

function buildHeatmapRows(lmp_by_zone, zone_avg_mwh) {
  const entries = Object.entries(lmp_by_zone || {}).sort((a, b) => a[0].localeCompare(b[0]))
  if (!entries.length) {
    return {
      rowLabels: ['Zone A', 'Zone B'],
      cellsA: DEMO_HEATMAP.map(([p, c, t]) => ({ price: p, change: `${c}%`, tier: t })),
      cellsB: DEMO_HEATMAP.map((row) => ({
        price: row[3],
        change: `${row[4]}%`,
        tier: row[5],
      })),
    }
  }

  const prices = entries.map(([, p]) => p)
  const min = Math.min(...prices)
  const max = Math.max(...prices)
  const avg =
    typeof zone_avg_mwh === 'number' && zone_avg_mwh > 0
      ? zone_avg_mwh
      : prices.reduce((a, b) => a + b, 0) / prices.length

  const sliceTo12 = padEntries(entries, 12)
  const rotateStart = Math.floor(entries.length / 2)
  const rotated = [...entries.slice(rotateStart), ...entries.slice(0, rotateStart)]
  const sliceB = padEntries(rotated, 12)

  const cell = ([zone, price]) => {
    const delta = avg ? ((price - avg) / avg) * 100 : 0
    const sign = delta >= 0 ? '+' : ''
    return {
      zone,
      price: Math.round(price),
      change: `${sign}${delta.toFixed(1)}%`,
      tier: priceTier(price, min, max),
    }
  }

  return {
    rowLabels: [
      String(sliceTo12[0]?.[0] ?? 'Zones').slice(0, 14),
      String(sliceB[0]?.[0] ?? 'Zones').slice(0, 14),
    ],
    cellsA: sliceTo12.map(cell),
    cellsB: sliceB.map(cell),
  }
}

function forecastDays(forecast, limit = 7) {
  const rows = forecast || []
  const short = ['SUN', 'MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT']
  const out = []
  for (let i = 0; i < rows.length && out.length < limit; i++) {
    const f = rows[i]
    const t = parseInt(String(f.temp_f ?? ''), 10)
    if (Number.isNaN(t)) continue
    const raw = String(f.time || '').replace(' ', 'T')
    const d = raw ? new Date(raw) : null
    const label = d && !Number.isNaN(d.getTime()) ? short[d.getDay()] : short[out.length % 7]
    out.push({ label, temp: t })
  }
  while (out.length < limit) {
    out.push({ label: short[out.length % 7], temp: 72 + out.length })
  }
  return out.slice(0, limit)
}

function pillClass(sev) {
  const s = String(sev || '').toLowerCase()
  if (s.includes('extreme') || s.includes('severe')) return 'bw-pill-red'
  if (s.includes('moderate') || s.includes('minor')) return 'bw-pill-amber'
  return 'bw-pill-green'
}

function animateGaugeScore(target, setDisplay) {
  const start = performance.now()
  const dur = 1400
  function step(ts) {
    const p = Math.min((ts - start) / dur, 1)
    const eased = 1 - (1 - p) ** 3
    setDisplay(Math.round(eased * target))
    if (p < 1) requestAnimationFrame(step)
  }
  requestAnimationFrame(step)
}

function readStoredTheme() {
  try {
    const saved = localStorage.getItem('gw-theme')
    if (saved === 'light' || saved === 'dark') return saved
  } catch {
    /* ignore */
  }
  return 'dark'
}

function formatClock() {
  return new Date().toLocaleTimeString('en-US', { hour12: false })
}

export function BriefingDashboard({ data }) {
  const gid = useId().replace(/:/g, '')
  const risk = data?.risk || {}
  const grid = data?.grid || {}
  const weather = data?.weather || {}
  const market = data?.market || {}
  const news = data?.news || []

  const riskScore = riskScoreFromLevel(risk.level)
  const badge = riskBadge(risk.level)

  const [themeMode, setThemeMode] = useState(readStoredTheme)
  const [clock, setClock] = useState(formatClock)
  const [gaugeNum, setGaugeNum] = useState(0)
  const [needleDeg, setNeedleDeg] = useState(-130)
  const [barsAnimated, setBarsAnimated] = useState(false)
  const [barShow, setBarShow] = useState([])
  const [arcPct, setArcPct] = useState([0, 0, 0])
  const [hmRevealA, setHmRevealA] = useState(-1)
  const [hmRevealB, setHmRevealB] = useState(-1)

  const mixBars = useMemo(() => buildBarsFromMix(grid.generation_mix), [grid.generation_mix])
  const heatmap = useMemo(
    () => buildHeatmapRows(market.lmp_by_zone, market.zone_avg_mwh),
    [market.lmp_by_zone, market.zone_avg_mwh],
  )
  const waveDays = useMemo(() => forecastDays(weather.forecast), [weather.forecast])

  const demandGw = (Number(grid.current_demand_mw) || 0) / 1000
  const renew = Number(grid.renewable_pct) || 0
  const utilPct = Math.round(Math.min(94, Math.max(48, 52 + renew * 0.35 + demandGw * 2)))
  const lmp = Number(market.zone_avg_mwh) || 0
  const henry = Number(market.henry_hub_mmbtu) || 0

  const arcDefs = useMemo(
    () => [
      { label: 'Load', pct: utilPct, color: '#00d4ff' },
      { label: 'Renew', pct: Math.round(Math.min(100, renew)), color: '#a855f7' },
      {
        label: 'Stability',
        pct: risk.level === 'RED' ? 88 : risk.level === 'YELLOW' ? 94 : 99,
        color: '#06d6a0',
      },
    ],
    [utilPct, renew, risk.level],
  )

  useLayoutEffect(() => {
    document.documentElement.setAttribute('data-theme', themeMode)
  }, [themeMode])

  useEffect(() => {
    const id = setInterval(() => setClock(formatClock()), 1000)
    return () => clearInterval(id)
  }, [])

  const toggleTheme = useCallback(() => {
    setThemeMode((m) => {
      const next = m === 'dark' ? 'light' : 'dark'
      try {
        localStorage.setItem('gw-theme', next)
      } catch {
        /* ignore */
      }
      return next
    })
  }, [])

  useEffect(() => {
    let cancelled = false
    const raf = requestAnimationFrame(() => {
      if (cancelled) return
      setGaugeNum(0)
      setNeedleDeg(-130)
    })
    const t1 = setTimeout(() => {
      if (cancelled) return
      setNeedleDeg(-130 + (riskScore / 100) * 260)
      animateGaugeScore(riskScore, setGaugeNum)
    }, 120)
    return () => {
      cancelled = true
      cancelAnimationFrame(raf)
      clearTimeout(t1)
    }
  }, [riskScore])

  useEffect(() => {
    let cancelled = false
    requestAnimationFrame(() => {
      if (cancelled) return
      setBarsAnimated(false)
      setBarShow(mixBars.map(() => false))
    })
    const t = setTimeout(() => {
      if (!cancelled) setBarsAnimated(true)
    }, 80)
    const shows = mixBars.map((_, i) =>
      setTimeout(() => {
        if (cancelled) return
        setBarShow((prev) => {
          const n = [...prev]
          n[i] = true
          return n
        })
      }, 500 + i * 110 + 900),
    )
    return () => {
      cancelled = true
      clearTimeout(t)
      shows.forEach(clearTimeout)
    }
  }, [mixBars])

  useEffect(() => {
    let cancelled = false
    requestAnimationFrame(() => {
      if (cancelled) return
      setArcPct([0, 0, 0])
    })
    const timers = arcDefs.map((a, i) =>
      setTimeout(() => {
        if (cancelled) return
        setArcPct((prev) => {
          const n = [...prev]
          n[i] = a.pct
          return n
        })
      }, 700 + i * 180),
    )
    return () => {
      cancelled = true
      timers.forEach(clearTimeout)
    }
  }, [arcDefs])

  useEffect(() => {
    let cancelled = false
    requestAnimationFrame(() => {
      if (cancelled) return
      setHmRevealA(-1)
      setHmRevealB(-1)
    })
    const timers = []
    for (let col = 0; col < 12; col++) {
      timers.push(
        setTimeout(() => {
          if (!cancelled) setHmRevealA(col)
        }, 900 + col * 110),
        setTimeout(() => {
          if (!cancelled) setHmRevealB(col)
        }, 900 + col * 110 + 70),
      )
    }
    return () => {
      cancelled = true
      timers.forEach(clearTimeout)
    }
  }, [heatmap])

  const ts = data?.meta?.timestamp || ''
  const recText = String(data?.recommendation ?? '').trim()
  const hasRecommendation =
    recText.length > 0 &&
    recText !== '—' &&
    !/^no recommendation extracted\.?$/i.test(recText)

  return (
    <div className="bw-dash">
      <nav className="bw-topnav">
        <div className="bw-nav-brand">
          <div className="bw-logo-dot" aria-hidden />
          <div>
            <h1>GRIDWATCH</h1>
            <span>ENERGY RISK BRIEFING</span>
          </div>
        </div>
        <div className="bw-nav-right">
          <div className="bw-nav-time">{clock}</div>
          <div
            className="bw-theme-toggle"
            onClick={toggleTheme}
            onKeyDown={(e) => e.key === 'Enter' && toggleTheme()}
            role="button"
            tabIndex={0}
            title="Switch day / night mode"
          >
            <span className="bw-theme-icon" aria-hidden>
              🌙
            </span>
            <div className="bw-toggle-track">
              <div className="bw-toggle-thumb" />
            </div>
            <span className="bw-theme-icon" aria-hidden>
              ☀️
            </span>
            <span className="bw-toggle-label">{themeMode === 'dark' ? 'Night' : 'Day'}</span>
          </div>
        </div>
      </nav>

      <div className="bw-page">
        <div className="bw-card bw-col-3">
          <div className="bw-card-tag">01 — Risk Level</div>
          <div className="bw-card-title">Grid Risk Index</div>
          <div className="bw-gauge-wrap">
            <svg className="bw-gauge-svg" viewBox="0 0 180 108" overflow="visible">
              <defs>
                <linearGradient id={`gArc-${gid}`} x1="0%" y1="0%" x2="100%" y2="0%">
                  <stop offset="0%" stopColor="#ef4444" />
                  <stop offset="45%" stopColor="#f59e0b" />
                  <stop offset="100%" stopColor="#06d6a0" />
                </linearGradient>
              </defs>
              <path
                d="M15 90 A75 75 0 0 1 165 90"
                fill="none"
                stroke="var(--bg3)"
                strokeWidth="11"
                strokeLinecap="round"
              />
              <path
                d="M15 90 A75 75 0 0 1 165 90"
                fill="none"
                stroke={`url(#gArc-${gid})`}
                strokeWidth="11"
                strokeLinecap="round"
                opacity="0.85"
              />
              <text x="12" y="104" fill="#ef4444" fontSize="7" fontFamily="DM Mono, monospace">
                LOW
              </text>
              <text x="82" y="22" fill="#f59e0b" fontSize="7" fontFamily="DM Mono, monospace" textAnchor="middle">
                MID
              </text>
              <text x="168" y="104" fill="#06d6a0" fontSize="7" fontFamily="DM Mono, monospace" textAnchor="end">
                HIGH
              </text>
              <g className="bw-gauge-needle" style={{ transform: `rotate(${needleDeg}deg)` }}>
                <line x1="90" y1="90" x2="90" y2="24" stroke="var(--text)" strokeWidth="2" strokeLinecap="round" opacity="0.9" />
                <polygon points="85,90 95,90 90,22" fill="var(--text)" opacity="0.12" />
              </g>
              <circle cx="90" cy="90" r="6" fill="var(--bg2)" stroke="var(--accent1)" strokeWidth="1.5" />
              <circle cx="90" cy="90" r="2.5" fill="var(--accent1)" />
            </svg>
            <div className="bw-gauge-val">{gaugeNum}</div>
            <div className="bw-gauge-label">RISK SCORE / 100</div>
            <div className={`bw-risk-badge ${badge.className}`}>
              <div className="bw-risk-dot" aria-hidden />
              {badge.label}
            </div>
          </div>
        </div>

        <div className="bw-card bw-col-3">
          <div className="bw-card-tag">02 — Grid Status</div>
          <div className="bw-card-title">Live KPIs</div>
          <div className="bw-kpi-grid">
            <div className="bw-kpi-item">
              <div className="bw-kpi-label">Load (GW)</div>
              <div className="bw-kpi-value" style={{ color: 'var(--accent1)' }}>
                {demandGw >= 0.01 ? demandGw.toFixed(2) : '—'}
              </div>
              <div className="bw-kpi-delta bw-up">NYISO · live pull</div>
            </div>
            <div className="bw-kpi-item">
              <div className="bw-kpi-label">Renewables %</div>
              <div className="bw-kpi-value" style={{ color: 'var(--amber)' }}>
                {renew >= 0.5 ? `${Math.round(renew)}%` : '—'}
              </div>
              <div className="bw-kpi-delta bw-up">mix snapshot</div>
            </div>
            <div className="bw-kpi-item">
              <div className="bw-kpi-label">Peak forecast</div>
              <div className="bw-kpi-value" style={{ color: 'var(--green)' }}>
                {grid.forecast_peak_mw ? `${Math.round(Number(grid.forecast_peak_mw))}` : '—'}
              </div>
              <div className="bw-kpi-delta bw-up">{grid.forecast_peak_time || 'MW window'}</div>
            </div>
            <div className="bw-kpi-item">
              <div className="bw-kpi-label">LMP avg · Henry</div>
              <div className="bw-kpi-value" style={{ color: 'var(--red)' }}>
                {lmp ? `$${Math.round(lmp)}` : '—'}
                {henry ? ` · $${henry}` : ''}
              </div>
              <div className="bw-kpi-delta bw-down">zone avg · gas</div>
            </div>
          </div>
        </div>

        <div className="bw-card bw-col-6">
          <div className="bw-card-tag">03 — Generation Mix</div>
          <div className="bw-card-title">Source breakdown (%)</div>
          <div className="bw-bar-chart">
            {mixBars.map((b, i) => (
              <div key={b.key} className="bw-bar-col">
                <div className={`bw-bar-val ${barShow[i] ? 'bw-bar-val--show' : ''}`}>{b.pct}%</div>
                <div className="bw-bar-track">
                  <div
                    className="bw-bar-fill"
                    style={{
                      height: barsAnimated ? `${b.pct}%` : '0%',
                      background: b.color,
                      transitionDelay: barsAnimated ? `${i * 110}ms` : '0ms',
                    }}
                  />
                </div>
                <div className="bw-bar-lbl">{b.label}</div>
              </div>
            ))}
          </div>
        </div>

        <div className="bw-card bw-col-4">
          <div className="bw-card-tag">04 — Resource signals</div>
          <div className="bw-card-title">System metrics</div>
          <div className="bw-arcs-wrap">
            {arcDefs.map((a, i) => (
              <div key={a.label} className="bw-arc-item">
                <svg viewBox="0 0 100 100">
                  <circle className="bw-arc-track" cx="50" cy="50" r="36" />
                  <circle
                    className="bw-arc-fill"
                    cx="50"
                    cy="50"
                    r="36"
                    stroke={a.color}
                    style={{
                      strokeDasharray: ARC_C,
                      strokeDashoffset: ARC_C - (ARC_C * arcPct[i]) / 100,
                    }}
                  />
                </svg>
                <div className="bw-arc-center">
                  <div className="bw-arc-pct" style={{ color: a.color }}>
                    {arcPct[i]}%
                  </div>
                  <div className="bw-arc-name">{a.label}</div>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="bw-card bw-col-4">
          <div className="bw-card-tag">05 — Weather</div>
          <div className="bw-card-title">Hourly outlook (°F)</div>
          <div className="bw-wave-box">
            <svg viewBox="0 0 1400 90" preserveAspectRatio="none" xmlns="http://www.w3.org/2000/svg">
              <defs>
                <linearGradient id={`wGrad-${gid}`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="var(--accent1)" stopOpacity="0.5" />
                  <stop offset="100%" stopColor="var(--accent1)" stopOpacity="0" />
                </linearGradient>
              </defs>
              <path
                fill={`url(#wGrad-${gid})`}
                opacity="0.2"
                d="M0,45 C87,30 175,60 262,45 C350,30 437,60 525,45 C612,30 700,60 787,45
                   C875,30 962,60 1050,45 C1137,30 1225,60 1312,45 C1356,30 1400,58 1400,45
                   L1400,90 L0,90 Z"
              />
              <path
                fill="none"
                stroke="var(--accent2)"
                strokeWidth="1.5"
                opacity="0.45"
                d="M0,50 C87,35 175,65 262,50 C350,35 437,65 525,50 C612,35 700,65 787,50
                   C875,35 962,65 1050,50 C1137,35 1225,65 1312,50 C1356,35 1400,62 1400,50"
              />
              <path
                fill="none"
                stroke="var(--accent1)"
                strokeWidth="2.5"
                d="M0,45 C87,30 175,60 262,45 C350,30 437,60 525,45 C612,30 700,60 787,45
                   C875,30 962,60 1050,45 C1137,30 1225,60 1312,45 C1356,30 1400,58 1400,45"
              />
              <circle cx="262" cy="45" r="3" fill="var(--accent1)" opacity="0.9" />
              <circle cx="525" cy="45" r="3" fill="var(--accent1)" opacity="0.9" />
              <circle cx="787" cy="45" r="3" fill="var(--accent1)" opacity="0.9" />
              <circle cx="1050" cy="45" r="3" fill="var(--accent1)" opacity="0.9" />
              <circle cx="1312" cy="45" r="3" fill="var(--accent1)" opacity="0.9" />
            </svg>
          </div>
          <div className="bw-wave-temps">
            {waveDays.map((d, i) => (
              <div key={`${d.label}-${i}`} className="bw-wave-day">
                {d.label}
                <strong>{d.temp}°</strong>
              </div>
            ))}
          </div>
        </div>

        <div className="bw-card bw-col-4">
          <div className="bw-card-tag">06 — Alerts</div>
          <div className="bw-card-title">Active weather · incidents</div>
          <table className="bw-alert-table">
            <thead>
              <tr>
                <th>Severity</th>
                <th>Event</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {(weather.alerts || []).length === 0 ? (
                <tr>
                  <td colSpan={3} style={{ color: 'var(--muted)' }}>
                    No active alerts in briefing payload.
                  </td>
                </tr>
              ) : (
                weather.alerts.slice(0, 8).map((row, i) => (
                  <tr key={i}>
                    <td>{row.severity || '—'}</td>
                    <td>{row.event || '—'}</td>
                    <td>
                      <span className={`bw-pill ${pillClass(row.severity)}`}>ACTIVE</span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        <div className="bw-card bw-col-12">
          <div className="bw-card-tag">07 — Market heatmap</div>
          <div className="bw-card-title">
            Hourly-style LMP grid · {Object.keys(market.lmp_by_zone || {}).length || 'demo'} zones · reveals left → right
          </div>
          <div className="bw-heatmap-outer">
            <div className="bw-hm-row-labels">
              <div className="bw-hm-row-label">{heatmap.rowLabels[0]}</div>
              <div className="bw-hm-row-label">{heatmap.rowLabels[1]}</div>
            </div>
            <div className="bw-hm-grid">
              {HM_HOURS.map((h) => (
                <div key={h} className="bw-hm-hour">
                  {h}
                </div>
              ))}
              {heatmap.cellsA.map((c, col) => (
                <div
                  key={`a-${col}`}
                  className={`bw-hm-cell bw-hm-t${c.tier} ${col <= hmRevealA ? 'bw-hm-cell--revealed' : ''}`}
                  data-row="a"
                  data-col={col}
                >
                  <div className="bw-hm-price">${c.price}</div>
                  <div className={`bw-hm-change ${c.change.startsWith('+') ? 'bw-up' : 'bw-down'}`}>{c.change}</div>
                </div>
              ))}
              {heatmap.cellsB.map((c, col) => (
                <div
                  key={`b-${col}`}
                  className={`bw-hm-cell bw-hm-t${c.tier} ${col <= hmRevealB ? 'bw-hm-cell--revealed' : ''}`}
                  data-row="b"
                  data-col={col}
                >
                  <div className="bw-hm-price">${c.price}</div>
                  <div className={`bw-hm-change ${c.change.startsWith('+') ? 'bw-up' : 'bw-down'}`}>{c.change}</div>
                </div>
              ))}
            </div>
          </div>
          <div className="bw-legend">
            <span className="bw-legend-label">Low</span>
            <div className="bw-legend-bar" />
            <span className="bw-legend-label">Peak</span>
          </div>
        </div>

        {hasRecommendation && (
          <div className="bw-card bw-col-12">
            <div className="bw-card-tag">08 — Recommendation</div>
            <div className="bw-card-title">Analyst action</div>
            <p className="bw-rec">{recText}</p>
          </div>
        )}

        <div className="bw-card bw-col-12">
          <div className="bw-card-tag">09 — News</div>
          <div className="bw-card-title">Energy headlines</div>
          {news.length > 0 ? (
            <ul className="bw-news-list">
              {news.slice(0, 12).map((n, i) => (
                <li key={i}>
                  <strong>{n.source}:</strong> {n.headline}
                </li>
              ))}
            </ul>
          ) : (
            <p className="bw-rec" style={{ marginTop: 0 }}>
              No headlines in this briefing yet. When the agent run completes with RSS data, items appear here.
            </p>
          )}
          {ts && <div className="bw-meta">Briefing timestamp · {ts}</div>}
        </div>
      </div>
    </div>
  )
}
