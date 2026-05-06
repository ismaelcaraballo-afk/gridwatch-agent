import { useMemo } from 'react'

const FALLBACK_MIX = [
  { key: 'H', h: 62, color: 'var(--blue)', pct: 62 },
  { key: 'S', h: 88, color: '#ff9f43', pct: 88 },
  { key: 'W', h: 38, color: 'var(--green)', pct: 38 },
  { key: 'G', h: 52, color: 'var(--grey-bar)', pct: 52 },
  { key: 'N', h: 71, color: 'var(--purple)', pct: 71 },
]

const CHART_X0 = 8
const CHART_X1 = 376
const CHART_Y_TOP = 16
const CHART_Y_BOT = 102

const FALLBACK_DEMAND_PATH =
  'M 8 52 Q 52 44 96 32 T 176 38 T 248 34 T 320 40 T 376 36'
const FALLBACK_SUPPLY_PATH =
  'M 8 60 Q 48 54 92 48 T 176 52 T 248 46 T 320 52 T 376 48'

function linearPath(pts) {
  if (!pts.length) return ''
  let d = `M ${pts[0][0].toFixed(1)} ${pts[0][1].toFixed(1)}`
  for (let i = 1; i < pts.length; i++) {
    d += ` L ${pts[i][0].toFixed(1)} ${pts[i][1].toFixed(1)}`
  }
  return d
}

/** Build demand / supply polylines + peak band from `get_demand_forecast` hourly rows. */
function curvesFromProfile(profile) {
  const n = profile.length
  if (n < 2) return null

  const mws = profile.map((p) => Number(p.mw) || 0)
  let lo = Math.min(...mws)
  let hi = Math.max(...mws)
  const span = hi - lo || hi * 0.05 || 1
  lo -= span * 0.08
  hi += span * 0.12

  const yFor = (mw) => {
    const t = (mw - lo) / (hi - lo)
    const c = Math.min(1, Math.max(0, t))
    return CHART_Y_BOT - c * (CHART_Y_BOT - CHART_Y_TOP)
  }

  const demandPts = profile.map((p, i) => {
    const x = CHART_X0 + (i / (n - 1)) * (CHART_X1 - CHART_X0)
    return [x, yFor(Number(p.mw) || 0)]
  })

  const supplyPts = profile.map((p, i) => {
    const x = CHART_X0 + (i / (n - 1)) * (CHART_X1 - CHART_X0)
    const dMw = Number(p.mw) || 0
    const sMw = dMw * 1.024
    return [x, yFor(sMw)]
  })

  let peakIdx = 0
  for (let i = 1; i < mws.length; i++) {
    if (mws[i] > mws[peakIdx]) peakIdx = i
  }

  const idxLo = Math.max(0, peakIdx - 1)
  const idxHi = Math.min(n - 1, peakIdx + 1)
  const xL = CHART_X0 + (idxLo / (n - 1)) * (CHART_X1 - CHART_X0)
  const xR = CHART_X0 + (idxHi / (n - 1)) * (CHART_X1 - CHART_X0)
  const margin = 10

  return {
    demandPath: linearPath(demandPts),
    supplyPath: linearPath(supplyPts),
    rect: {
      x: Math.max(CHART_X0, xL - margin),
      y: CHART_Y_TOP - 2,
      width: Math.min(CHART_X1 - CHART_X0 - 4, xR - xL + margin * 2),
      height: CHART_Y_BOT - CHART_Y_TOP + 12,
    },
    peakMwRounded: Math.round(mws[peakIdx]),
    peakTimeLabel: profile[peakIdx]?.time || '',
  }
}

/** When no hourly profile, center ~3h band on clock parsed from `forecast_peak_time`. */
function fallbackPeakBand(peakTimeStr) {
  const matches = [...String(peakTimeStr || '').matchAll(/\b(\d{2}):(\d{2})\b/g)]
  const hit = matches.length ? matches[matches.length - 1] : null
  let cx = (CHART_X0 + CHART_X1) / 2
  if (hit) {
    const hr = parseInt(hit[1], 10) + parseInt(hit[2], 10) / 60
    const frac = (hr % 24) / 24
    cx = CHART_X0 + frac * (CHART_X1 - CHART_X0)
  }
  const hourWidth = (CHART_X1 - CHART_X0) / 24
  return {
    x: Math.max(CHART_X0, cx - hourWidth * 1.5),
    y: CHART_Y_TOP - 2,
    width: Math.min(CHART_X1 - CHART_X0 - 8, hourWidth * 3),
    height: CHART_Y_BOT - CHART_Y_TOP + 12,
  }
}

function SparkFreq() {
  const pts =
    '0,38 18,36 36,34 54,33 72,35 90,42 108,48 126,44 144,38 162,36 180,37'
  return (
    <svg className="grid-mini-chart" viewBox="0 0 180 48" preserveAspectRatio="none">
      <polyline fill="none" stroke="#3fb950" strokeWidth="2" points={pts} />
    </svg>
  )
}

function mixFromGrid(grid) {
  const g = grid?.generation_mix || {}
  const rows = [
    { key: 'G', label: 'G', pct: Number(g.natural_gas_pct) || 0, color: 'var(--grey-bar)' },
    { key: 'S', label: 'S', pct: Number(g.solar_pct) || 0, color: '#ff9f43' },
    { key: 'W', label: 'W', pct: Number(g.wind_pct) || 0, color: 'var(--green)' },
    { key: 'H', label: 'H', pct: Number(g.hydro_pct) || 0, color: 'var(--blue)' },
    { key: 'N', label: 'N', pct: Number(g.nuclear_pct) || 0, color: 'var(--purple)' },
  ]
  const nonzero = rows.filter((r) => r.pct >= 0.5)
  const base = nonzero.length ? nonzero : FALLBACK_MIX.map((m) => ({ ...m, pct: m.h }))
  const max = Math.max(...base.map((b) => b.pct), 1)
  return base.map((b) => ({
    ...b,
    h: Math.max(14, Math.round((b.pct / max) * 90)),
  }))
}

export function GridModule({ grid }) {
  const g = grid || {}
  const mixKey = JSON.stringify(g.generation_mix ?? {})
  // eslint-disable-next-line react-hooks/exhaustive-deps -- mixKey fingerprints generation_mix
  const mix = useMemo(() => mixFromGrid(g), [mixKey])

  const demandMw = Number(g.current_demand_mw) || 0
  const renew = Number(g.renewable_pct) || 0
  const loadPct = Math.round(Math.min(94, Math.max(46, 52 + renew * 0.28 + demandMw / 900)))
  const peakMw = Number(g.forecast_peak_mw) || 0
  const peakHint = g.forecast_peak_time || ''

  const fpKey = JSON.stringify(g.forecast_profile ?? [])
  const forecastProfile = useMemo(() => {
    try {
      const parsed = JSON.parse(fpKey)
      return Array.isArray(parsed) ? parsed : []
    } catch {
      return []
    }
  }, [fpKey])

  const chart = useMemo(() => {
    const fromApi = curvesFromProfile(forecastProfile)
    if (fromApi) {
      return {
        demandPath: fromApi.demandPath,
        supplyPath: fromApi.supplyPath,
        rect: fromApi.rect,
        title: 'FORECAST PEAK WINDOW',
        subPrimary: `${fromApi.peakMwRounded.toLocaleString()} MW`,
        subSecondary: fromApi.peakTimeLabel || peakHint || 'Peak hour from profile',
        caption: '24h demand forecast vs modeled supply (from briefing tools)',
      }
    }
    return {
      demandPath: FALLBACK_DEMAND_PATH,
      supplyPath: FALLBACK_SUPPLY_PATH,
      rect: fallbackPeakBand(peakHint),
      title: 'FORECAST PEAK WINDOW',
      subPrimary: peakMw ? `${Math.round(peakMw).toLocaleString()} MW` : 'Peak TBD',
      subSecondary: peakHint || 'Run agent with demand forecast for hourly curve',
      caption: '24h demand vs supply (illustrative — hourly forecast unavailable)',
    }
  }, [forecastProfile, peakMw, peakHint])

  const demandLabel =
    demandMw >= 100 ? `${(demandMw / 1000).toFixed(2)} GW` : demandMw > 0 ? `${Math.round(demandMw)} MW` : '—'

  return (
    <section className="brief-section briefing-card briefing-card--flush">
      <div className="brief-section__head">
        <span className="brief-section__num">02</span>
        <span className="brief-section__name">GRID STATUS</span>
      </div>
      <div className="brief-section__divider" />
      <div className="grid-top-row">
        <div className="grid-kpi">
          <span className="grid-kpi__label">Load ({g.region || 'NYISO'})</span>
          <div className="grid-kpi__value">{demandLabel}</div>
          <SparkFreq />
          <span className={`pill ${demandMw > 0 ? 'pill--warn' : 'pill--danger'}`}>
            {demandMw > 0 ? 'LIVE EIA' : 'NO DATA'}
          </span>
        </div>
        <div className="grid-kpi">
          <span className="grid-kpi__label">Load vs capacity (proxy)</span>
          <div className="grid-kpi__value">
            {renew >= 0.5 ? `${loadPct}` : '—'}
            <span className="grid-kpi__suffix">% utilized</span>
          </div>
          <div className="load-bar">
            <div className="load-bar__fill" style={{ '--load-pct': `${loadPct}%` }} />
          </div>
          <span className={`pill ${loadPct > 82 ? 'pill--danger' : 'pill--warn'}`}>
            {renew >= 0.5 ? 'MODELED' : 'ESTIMATE'}
          </span>
        </div>
        <div className="grid-kpi grid-kpi--mix">
          <span className="grid-kpi__label">Generation mix</span>
          <div className="gen-vbars">
            {mix.map((m) => (
              <div key={m.key} className="gen-vbars__col">
                <div
                  className="gen-vbars__bar"
                  style={{
                    '--bar-height-pct': `${m.h}%`,
                    background: m.color,
                  }}
                />
                <span className="gen-vbars__key">{m.label}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
      <div className="grid-chart-wrap">
        <span className="grid-chart__caption">{chart.caption}</span>
        <svg className="grid-chart" viewBox="0 0 384 120" preserveAspectRatio="xMidYMid meet">
          <text x="8" y="112" className="grid-chart__axis">
            12am
          </text>
          <text x="96" y="112" className="grid-chart__axis" textAnchor="middle">
            6am
          </text>
          <text x="288" y="112" className="grid-chart__axis" textAnchor="middle">
            6pm
          </text>
          <text x="376" y="112" className="grid-chart__axis" textAnchor="end">
            12am
          </text>
          <path
            className="grid-chart__curve grid-chart__curve--demand"
            fill="none"
            stroke="#58a6ff"
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
            d={chart.demandPath}
          />
          <path
            className="grid-chart__curve grid-chart__curve--supply"
            fill="none"
            stroke="#3fb950"
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
            d={chart.supplyPath}
          />
          <rect
            x={chart.rect.x}
            y={chart.rect.y}
            width={chart.rect.width}
            height={chart.rect.height}
            fill="none"
            stroke="#d29922"
            strokeWidth="1.5"
            strokeDasharray="5 4"
            rx="3"
          />
          <text x="192" y="36" textAnchor="middle" className="grid-chart__stress-title">
            {chart.title}
          </text>
          <text x="192" y="52" textAnchor="middle" className="grid-chart__stress-sub">
            {chart.subPrimary}
            {chart.subSecondary ? ` · ${chart.subSecondary}` : ''}
          </text>
        </svg>
        <div className="grid-chart__legend">
          <span className="grid-chart__key grid-chart__key--demand">DEMAND (forecast)</span>
          <span className="grid-chart__key grid-chart__key--supply">SUPPLY (modeled)</span>
        </div>
      </div>
    </section>
  )
}
