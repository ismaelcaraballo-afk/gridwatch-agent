import { useEffect, useId, useState } from 'react'

function FactorBar({ label, pct, variant }) {
  return (
    <div className="risk-factor">
      <div className="risk-factor__head">
        <span className="risk-factor__label">{label}</span>
        <span className="risk-factor__pct">{pct}%</span>
      </div>
      <div className="risk-factor__track">
        <div
          className={`risk-factor__fill risk-factor__fill--${variant}`}
          style={{ '--fill-pct': `${pct}%` }}
        />
      </div>
    </div>
  )
}

function needleCoords(cx, cy, r, value) {
  const clamped = Math.min(100, Math.max(0, value))
  const θ = Math.PI * (1 - clamped / 100)
  return {
    x: cx + r * Math.cos(θ),
    y: cy - r * Math.sin(θ),
  }
}

function scoreFromLevel(level) {
  const u = String(level || 'GREEN').toUpperCase()
  if (u === 'RED') return 88
  if (u === 'YELLOW') return 62
  return 36
}

function factorsForLevel(level) {
  const u = String(level || 'GREEN').toUpperCase()
  if (u === 'RED') {
    return [
      { label: 'Demand stress', pct: 92, variant: 'red' },
      { label: 'Weather risk', pct: 86, variant: 'red' },
      { label: 'Market volatility', pct: 78, variant: 'orange' },
      { label: 'Supply margin', pct: 36, variant: 'orange' },
      { label: 'Infrastructure', pct: 24, variant: 'green' },
    ]
  }
  if (u === 'YELLOW') {
    return [
      { label: 'Demand stress', pct: 71, variant: 'orange' },
      { label: 'Weather risk', pct: 68, variant: 'orange' },
      { label: 'Market volatility', pct: 58, variant: 'orange' },
      { label: 'Supply margin', pct: 48, variant: 'orange' },
      { label: 'Infrastructure', pct: 32, variant: 'green' },
    ]
  }
  return [
    { label: 'Demand stress', pct: 44, variant: 'green' },
    { label: 'Weather risk', pct: 38, variant: 'green' },
    { label: 'Market volatility', pct: 52, variant: 'orange' },
    { label: 'Supply margin', pct: 62, variant: 'green' },
    { label: 'Infrastructure', pct: 28, variant: 'green' },
  ]
}

function badgeFor(level) {
  const u = String(level || 'GREEN').toUpperCase()
  if (u === 'RED') return { cls: 'risk-badge-elevated', text: 'HIGH RISK' }
  if (u === 'YELLOW') return { cls: 'risk-badge-warn', text: 'ELEVATED RISK' }
  return { cls: 'risk-badge-normal', text: 'NORMAL RISK' }
}

export function RiskModule({ risk }) {
  const gid = useId().replace(/:/g, '')
  const level = risk?.level || 'GREEN'
  const target = scoreFromLevel(level)
  const badge = badgeFor(level)
  const factors = factorsForLevel(level)

  const [needleVal, setNeedleVal] = useState(0)
  const [displayScore, setDisplayScore] = useState(0)

  useEffect(() => {
    let frame
    let cancelled = false
    const start = performance.now()
    const dur = 1400
    function tick(now) {
      if (cancelled) return
      const p = Math.min((now - start) / dur, 1)
      const eased = 1 - (1 - p) ** 3
      const v = eased * target
      setNeedleVal(v)
      setDisplayScore(Math.round(v))
      if (p < 1) frame = requestAnimationFrame(tick)
    }
    frame = requestAnimationFrame(tick)
    return () => {
      cancelled = true
      cancelAnimationFrame(frame)
    }
  }, [target])

  const tip = needleCoords(100, 92, 62, needleVal)

  return (
    <section className="brief-section briefing-card">
      <div className="brief-section__head">
        <span className="brief-section__num">01</span>
        <span className="brief-section__name">RISK LEVEL</span>
      </div>
      <div className="brief-section__divider" />
      <div className="risk-layout">
        <div className="risk-gauge-wrap">
          <svg className="risk-gauge" viewBox="0 0 200 118" role="img" aria-label={`Composite risk ${displayScore}`}>
            <defs>
              <linearGradient id={`riskArcGrad-${gid}`} x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stopColor="#3fb950" />
                <stop offset="50%" stopColor="#d29922" />
                <stop offset="100%" stopColor="#f85149" />
              </linearGradient>
            </defs>
            <path
              d="M 28 92 A 72 72 0 0 1 172 92"
              fill="none"
              stroke={`url(#riskArcGrad-${gid})`}
              strokeWidth="14"
              strokeLinecap="round"
            />
            <text x="42" y="104" className="risk-gauge__tick-label">
              LOW
            </text>
            <text x="94" y="22" className="risk-gauge__tick-label">
              MED
            </text>
            <text x="154" y="104" className="risk-gauge__tick-label">
              HIGH
            </text>
            <line
              x1="100"
              y1="92"
              x2={tip.x}
              y2={tip.y}
              stroke="#f0f6fc"
              strokeWidth="2.5"
              strokeLinecap="round"
            />
            <circle cx="100" cy="92" r="5" fill="#f0f6fc" />
            <text x="100" y="76" textAnchor="middle" className="risk-gauge__score">
              {displayScore}
            </text>
          </svg>
          <div className={badge.cls}>{badge.text}</div>
        </div>
        <div className="risk-factors">
          {factors.map((f) => (
            <FactorBar key={f.label} label={f.label} pct={f.pct} variant={f.variant} />
          ))}
        </div>
      </div>
    </section>
  )
}
