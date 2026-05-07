import { useMemo, useState } from 'react'

/** Static gradient rows — original hourly heatmap look */
const HEATMAP_ROWS = [
  ['#aff5b4', '#79d297', '#56c878', '#34a853', '#f9e79f', '#f4d03f', '#f39c12', '#e74c3c'],
  ['#79d297', '#56c878', '#34a853', '#f9e79f', '#f4d03f', '#f39c12', '#e74c3c', '#c0392b'],
  ['#56c878', '#34a853', '#f9e79f', '#f4d03f', '#f39c12', '#e74c3c', '#c0392b', '#922b21'],
]

const ZONE_FALLBACK = [
  { ticker: 'NY-J' },
  { ticker: 'LI-M' },
  { ticker: 'W-A' },
]

/** Normalized spark polyline (matches prior demo path). Tooltip anchors sit on each vertex. */
const SPARK_VB = { w: 200, h: 64 }
const SPARK_POINTS = [
  [4, 18],
  [28, 22],
  [52, 14],
  [76, 28],
  [100, 36],
  [124, 44],
  [148, 52],
  [172, 58],
  [196, 62],
]

const SLOT_LABELS = ['04:00', '07:00', '10:00', '13:00', '16:00', '19:00', '21:00', '23:00']

function sparkPathD() {
  const [x0, y0] = SPARK_POINTS[0]
  let d = `M ${x0} ${y0}`
  for (let i = 1; i < SPARK_POINTS.length; i++) {
    d += ` L ${SPARK_POINTS[i][0]} ${SPARK_POINTS[i][1]}`
  }
  return d
}

function estPriceAtY(y, displaySpot, spread) {
  const ys = SPARK_POINTS.map((p) => p[1])
  const ymin = Math.min(...ys)
  const ymax = Math.max(...ys)
  const t = (ymax - y) / (ymax - ymin || 1)
  const pad =
    spread != null && spread > 0
      ? Math.min(spread * 1.15, displaySpot * 0.28)
      : Math.max(displaySpot * 0.12, 12)
  return Math.round(displaySpot - pad / 2 + t * pad)
}

function hexToRgb(hex) {
  const x = hex.replace('#', '')
  return [parseInt(x.slice(0, 2), 16), parseInt(x.slice(2, 4), 16), parseInt(x.slice(4, 6), 16)]
}

function heatCellTextColor(bgHex) {
  const [r, g, b] = hexToRgb(bgHex)
  const lum = (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255
  return lum > 0.62 ? 'rgba(15, 18, 22, 0.92)' : 'rgba(255, 255, 255, 0.95)'
}

function abbrevTicker(name) {
  const s = String(name || '').trim()
  if (!s) return 'ZONE'
  const up = s.toUpperCase()
  if (up.length <= 6) return up
  const parts = s.split(/[\s_/]+/).filter(Boolean)
  if (parts.length >= 2) {
    const a = parts[0].replace(/[^A-Za-z]/g, '').slice(0, 3).toUpperCase()
    const b = parts[1].replace(/[^A-Za-z]/g, '').slice(0, 2).toUpperCase()
    return `${a}-${b}`.slice(0, 8)
  }
  return up.slice(0, 6)
}

function slotDelta(prev, cur) {
  if (cur > prev + 0.5) return 'up'
  if (cur < prev - 0.5) return 'down'
  return 'flat'
}

/** One synthetic $/MWh path per row — only used to pick ↑/↓ vs prior column */
function cellArrowDir(rowBase, spread, ci) {
  const prevCi = (ci + 7) % 8
  const cur = estPriceAtY(SPARK_POINTS[ci][1], rowBase, spread)
  const prev = estPriceAtY(SPARK_POINTS[prevCi][1], rowBase, spread)
  return slotDelta(prev, cur)
}

function rowTickersAndBases(market, displaySpot) {
  const lmp = market?.lmp_by_zone || {}
  const pairs = Object.entries(lmp).filter(([, v]) => typeof v === 'number' && v > 0)
  pairs.sort((a, b) => b[1] - a[1])
  const rows = []
  for (let ri = 0; ri < 3; ri++) {
    if (pairs[ri]) {
      rows.push({
        ticker: abbrevTicker(pairs[ri][0]),
        base: Math.round(pairs[ri][1]),
      })
    } else {
      rows.push({
        ticker: ZONE_FALLBACK[ri].ticker,
        base: Math.round(displaySpot * (1 + (ri - 1) * 0.038)),
      })
    }
  }
  return rows
}

export function MarketModule({ market }) {
  const m = market || {}
  const spot =
    typeof m.zone_avg_mwh === 'number' && m.zone_avg_mwh > 0 ? Math.round(m.zone_avg_mwh) : null
  const spread = typeof m.spread_mwh === 'number' && m.spread_mwh > 0 ? m.spread_mwh : null
  const displaySpot = spot ?? 142

  const henry =
    typeof m.henry_hub_mmbtu === 'number' && m.henry_hub_mmbtu > 0 ? m.henry_hub_mmbtu : null

  const pathD = useMemo(() => sparkPathD(), [])
  const [tip, setTip] = useState(null)
  const heatRows = useMemo(
    () => rowTickersAndBases(market ?? {}, displaySpot),
    [market, displaySpot],
  )

  return (
    <section className="brief-section briefing-card">
      <div className="brief-section__head">
        <span className="brief-section__num">04</span>
        <span className="brief-section__name">MARKET</span>
      </div>
      <div className="brief-section__divider" />
      <div className="market-layout">
        <div className="market-spot">
          <div className="market-spot__row">
            <span className="market-spot__price">${displaySpot} / MWh</span>
            <span className="market-spot__delta">
              {spread != null ? `spread $${Math.round(spread)}` : 'zone avg'}
            </span>
          </div>
          <div className="market-spark-wrap">
            <svg
              className="market-spark"
              viewBox={`0 0 ${SPARK_VB.w} ${SPARK_VB.h}`}
              preserveAspectRatio="none"
              aria-label="Illustrative LMP sparkline with hover detail"
            >
              <path
                className="market-spark__path"
                fill="none"
                stroke="#a371f7"
                strokeWidth="2.25"
                strokeLinecap="round"
                strokeLinejoin="round"
                d={pathD}
              />
              {SPARK_POINTS.map(([x, y], i) => (
                <circle
                  key={i}
                  className="market-spark__hit"
                  cx={x}
                  cy={y}
                  r={11}
                  fill="transparent"
                  tabIndex={0}
                  onMouseEnter={() =>
                    setTip({
                      i,
                      x,
                      y,
                      price: estPriceAtY(y, displaySpot, spread),
                      slot: SLOT_LABELS[i] ?? `Step ${i + 1}`,
                    })
                  }
                  onMouseLeave={() => setTip(null)}
                  onBlur={() => setTip(null)}
                  onFocus={() =>
                    setTip({
                      i,
                      x,
                      y,
                      price: estPriceAtY(y, displaySpot, spread),
                      slot: SLOT_LABELS[i] ?? `Step ${i + 1}`,
                    })
                  }
                />
              ))}
              {tip && (
                <circle
                  className="market-spark__vertex"
                  cx={tip.x}
                  cy={tip.y}
                  r={4}
                  fill="#a371f7"
                  stroke="var(--bg)"
                  strokeWidth={1.5}
                  opacity={1}
                />
              )}
            </svg>
            {tip && (
              <div
                className="market-spark-tip"
                style={{
                  left: `${(tip.x / SPARK_VB.w) * 100}%`,
                  top: `${(tip.y / SPARK_VB.h) * 100}%`,
                  transform: 'translate(-50%, calc(-100% - 10px))',
                }}
                role="tooltip"
              >
                <strong>${tip.price} / MWh (est.)</strong>
                <span className="market-spark-tip__row">Illustrative curve · {tip.slot} slot</span>
                <span className="market-spark-tip__row">
                  Zone avg ${displaySpot}
                  {spread != null ? ` · spread $${Math.round(spread)}` : ''}
                  {henry != null ? ` · Henry $${henry}/MMBtu` : ''}
                </span>
                <span className="market-spark-tip__row" style={{ marginTop: '0.25rem', opacity: 0.85 }}>
                  Power/LMP context — not equities. Swap tooltip copy when you wire stock APIs.
                </span>
              </div>
            )}
          </div>
          <div className="market-hilo">
            <span className="market-hilo__high">
              {spot != null ? `Live avg $${spot}` : 'Demo curve'}
            </span>
            <span className="market-hilo__low">
              Henry ${henry != null ? henry : '—'}/MMBtu
            </span>
          </div>
        </div>
        <div className="market-heat">
          <p className="market-heat__title">Hourly Price Heatmap</p>
          <div className="heatmap">
            {HEATMAP_ROWS.map((colors, ri) => (
              <div key={ri} className="heatmap__row">
                {colors.map((bg, ci) => {
                  const meta = heatRows[ri]
                  const dir = cellArrowDir(meta.base, spread, ci)
                  const fg = heatCellTextColor(bg)
                  return (
                    <div
                      key={ci}
                      className="heatmap__cell"
                      style={{
                        background: bg,
                        color: fg,
                        '--hm-delay': ri * 8 + ci,
                      }}
                    >
                      <span className="heatmap__cell-ticker">{meta.ticker}</span>
                      <span className={`heatmap__cell-arrow heatmap__cell-arrow--${dir}`} aria-hidden>
                        {dir === 'up' ? '↑' : dir === 'down' ? '↓' : '→'}
                      </span>
                    </div>
                  )
                })}
              </div>
            ))}
          </div>
          <div className="heatmap__legend">
            <span>Low cost</span>
            <div className="heatmap__gradient" />
            <span>High cost</span>
          </div>
        </div>
      </div>
    </section>
  )
}
