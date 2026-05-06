const HEATMAP_ROWS = [
  ['#aff5b4', '#79d297', '#56c878', '#34a853', '#f9e79f', '#f4d03f', '#f39c12', '#e74c3c'],
  ['#79d297', '#56c878', '#34a853', '#f9e79f', '#f4d03f', '#f39c12', '#e74c3c', '#c0392b'],
  ['#56c878', '#34a853', '#f9e79f', '#f4d03f', '#f39c12', '#e74c3c', '#c0392b', '#922b21'],
]

export function MarketModule({ market }) {
  const m = market || {}
  const spot =
    typeof m.zone_avg_mwh === 'number' && m.zone_avg_mwh > 0 ? Math.round(m.zone_avg_mwh) : null
  const spread = typeof m.spread_mwh === 'number' && m.spread_mwh > 0 ? m.spread_mwh : null
  const displaySpot = spot ?? 142

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
          <svg className="market-spark" viewBox="0 0 200 64" preserveAspectRatio="none">
            <path
              className="market-spark__path"
              fill="none"
              stroke="#a371f7"
              strokeWidth="2.25"
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M 4 18 L 28 22 L 52 14 L 76 28 L 100 36 L 124 44 L 148 52 L 172 58 L 196 62"
            />
          </svg>
          <div className="market-hilo">
            <span className="market-hilo__high">
              {spot != null ? `Live avg $${spot}` : 'Demo curve'}
            </span>
            <span className="market-hilo__low">
              Henry ${typeof m.henry_hub_mmbtu === 'number' && m.henry_hub_mmbtu > 0 ? m.henry_hub_mmbtu : '—'}/MMBtu
            </span>
          </div>
        </div>
        <div className="market-heat">
          <p className="market-heat__title">Hourly Price Heatmap</p>
          <div className="heatmap">
            {HEATMAP_ROWS.map((row, ri) => (
              <div key={ri} className="heatmap__row">
                {row.map((c, ci) => (
                  <div
                    key={ci}
                    className="heatmap__cell"
                    style={{
                      background: c,
                      '--hm-delay': ri * 8 + ci,
                    }}
                  />
                ))}
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
